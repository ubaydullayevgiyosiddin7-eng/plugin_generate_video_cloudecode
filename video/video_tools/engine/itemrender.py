"""Render one EDL item to a graded 1080x1920 (or preview) 30 fps intermediate + a WAV of its sound.

Pipeline (video):  ffmpeg [decode 4K HEVC -> speed/fps (or 60 fps CFR for time-mapped items) ->
crop union-bbox in raw orientation -> lanczos prescale -> transpose/flip -> rgb24 (explicit
BT.709)]  ==pipe==>  python/OpenCV [frame pick/blend for speed ramps; per-frame sub-pixel
warpAffine (bicubic) incl. tilt + stabilisation; box/fit blurred-fill composite]  ==pipe==>
ffmpeg [3D-LUT grade (rgb48, tetrahedral) -> BT.709 yuv420p -> x264 crf 13]  -> cache/<id>_<key>.mkv
"""
import io
import math
import os
import time
import traceback

import numpy as np

from common import (FFMPEG, YUV2RGB, RGB2YUV, TAGS709, SETPARAMS709, FrameReader, FrameWriter, run, log,
                    rotation_filters, upright_rect_to_raw, probe, atomic_replace)
import framing

CLIP_HIGHPASS_HZ = 120  # wind rumble / handling noise on iPhone clips


def _cv2(threads):
    import cv2
    cv2.setNumThreads(max(1, threads))
    return cv2


# ----------------------------------------------------------------------------------------------
# timing helpers
# ----------------------------------------------------------------------------------------------

def output_times(job):
    """Source time (seconds) of every output frame."""
    if job.get("speed_map"):
        t, n = framing.time_map(job["in"], job["out"], job["speed_map"], job["fps"])
        if n != job["n"]:
            raise RuntimeError(f"{job['id']}: time map frame count mismatch {n} != {job['n']}")
        return t
    return job["in"] + np.arange(job["n"]) * job["speed"] / job["fps"]


def _speed_chain(job):
    if job.get("timemap"):
        # constant-rate source frames; python picks/blends the ones each output frame needs
        return ["setpts=PTS-STARTPTS", f"fps={job['src_fps']}:round=near"]
    return [f"setpts=(PTS-STARTPTS)/{job['speed']:.6f}", f"fps={job['fps']}:round=near"]


def _decode_base(job):
    cmd = [FFMPEG, "-nostdin", "-hide_banner", "-v", "error"]
    if job.get("hwaccel") and job["hwaccel"] != "none":
        cmd += ["-hwaccel", job["hwaccel"]]
    if job.get("dec_threads"):
        cmd += ["-threads", str(min(4, job["dec_threads"]))]
    if job.get("timemap"):
        read_dur = job["out"] - job["in"] + 0.5
    else:
        read_dur = job["n"] / job["fps"] * job["speed"] + 0.6
    cmd += ["-noautorotate", "-ss", f"{job['in']:.6f}", "-t", f"{read_dur:.6f}", "-i", job["decode_src"],
            "-map", "0:v:0", "-an", "-sn", "-dn", "-filter_threads", "2"]
    return cmd


def _src_geometry(job):
    """raw size, total clockwise rotation, flip, and upright size of the decode source."""
    info = probe(job["decode_src"])
    total = (info["auto_cw"] + job.get("rotate", 0)) % 360
    W, H = (info["h"], info["w"]) if total in (90, 270) else (info["w"], info["h"])
    return info, total, bool(job.get("hflip")), W, H


class _TimePicker:
    """Serve output frame k from a CFR source stream: nearest frame, or a blend of the two
    neighbours when the wanted instant falls between source frames (no cadence judder)."""

    def __init__(self, reader, times, t_in, src_fps, blend, cv2):
        self.rd, self.cv2 = reader, cv2
        self.pos = (np.asarray(times) - t_in) * src_fps
        self.blend = blend
        self.idx = -1
        self.cur = None
        self.nxt = None
        self.missing = 0

    def _advance_to(self, i):
        while self.idx < i:
            f = self.rd.read()
            if f is None:
                self.missing += 1
                return False
            self.cur, self.idx = f, self.idx + 1
        return True

    def frame(self, k):
        p = max(0.0, float(self.pos[k]))
        i0 = int(math.floor(p + 1e-6))
        f = p - i0
        if not self.blend or f < 0.12 or f > 0.88:
            i = i0 if f <= 0.5 else i0 + 1
            if not self._advance_to(i) and self.cur is None:
                raise RuntimeError("decoder produced no frames")
            return self.cur
        if not self._advance_to(i0):
            return self.cur
        a = self.cur
        if not self._advance_to(i0 + 1):
            return a
        return self.cv2.addWeighted(a, 1.0 - f, self.cur, f, 0.0)


def analyse_stabilisation(job, cv2):
    """Decode a small grey upright copy with the exact same frame timing as the render, estimate
    motion. Cached as .npz (keyed by source/in/out/speed/rotation)."""
    path = job["stab_cache"]
    if os.path.exists(path):
        d = np.load(path)
        return dict(Ts=list(d["Ts"]), fps=float(d["fps"]), stats=list(d["stats"]))
    info, total, hflip, W, H = _src_geometry(job)
    aw = 960 if W >= H else 540  # analysis width (upright); ~0.05 px LK precision -> <0.2 px at 4K
    ah = int(round(H * aw / W / 2)) * 2
    rw, rh = (ah, aw) if total in (90, 270) else (aw, ah)
    chain = _speed_chain(job) + [f"scale={rw}:{rh}:flags=area"] + rotation_filters(total, hflip) + ["format=gray"]
    cmd = _decode_base(job) + ["-vf", ",".join(chain), "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    rd = FrameReader(cmd, (ah, aw))
    frames = []
    try:
        if job.get("timemap"):
            tp = _TimePicker(rd, output_times(job), job["in"], job["src_fps"], False, cv2)
            for k in range(job["n"]):
                frames.append(tp.frame(k).copy())
        else:
            for _ in range(job["n"]):
                f = rd.read()
                if f is None:
                    break
                frames.append(f)
    finally:
        rd.close()
    if len(frames) < 2:
        raise RuntimeError(f"{job['id']}: stabilisation analysis got {len(frames)} frames\n{rd.stderr_text()}")
    while len(frames) < job["n"]:
        frames.append(frames[-1])
    Ts, stats = framing.estimate_motion(frames, W / aw)
    np.savez(path + ".tmp.npz", Ts=np.array(Ts), fps=job["fps"], stats=np.array(stats))
    atomic_replace(path + ".tmp.npz", path)
    return dict(Ts=Ts, fps=float(job["fps"]), stats=stats)


def vidstab_detect(job):
    """Optional ffmpeg/libvidstab path (stabilize.method = 'vidstab'): pass 1 at full resolution."""
    trf = job["stab_cache"].replace(".npz", ".trf")
    if os.path.exists(trf):
        return trf
    sm = job["stabilize"]
    chain = _speed_chain(job) + [
        f"vidstabdetect=shakiness={int(sm.get('shakiness', 6))}:accuracy=15:stepsize=6:result="
        f"{os.path.basename(trf)}.tmp"]
    cmd = _decode_base(job) + ["-vf", ",".join(chain), "-f", "null", "-"]
    run(cmd, cwd=os.path.dirname(trf))
    atomic_replace(trf + ".tmp", trf)
    return trf


# ----------------------------------------------------------------------------------------------
# photos
# ----------------------------------------------------------------------------------------------

def _load_photo(path, rotate=0, hflip=False):
    from PIL import Image, ImageOps, ImageCms
    if path.lower().endswith(".heic"):
        import pillow_heif
        pillow_heif.register_heif_opener()
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    icc = im.info.get("icc_profile")
    note = "no ICC (assumed sRGB)"
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            desc = ImageCms.getProfileDescription(src).strip()
            note = f"ICC '{desc}'"
            if "srgb" not in desc.lower():
                im = ImageCms.profileToProfile(im.convert("RGB"), src, ImageCms.createProfile("sRGB"),
                                               renderingIntent=ImageCms.Intent.PERCEPTUAL, outputMode="RGB")
                note += " -> converted to sRGB"
        except Exception as e:  # broken profile: keep pixels as-is
            note = f"ICC unreadable ({e})"
    arr = np.asarray(im.convert("RGB"))
    if rotate % 360:
        arr = np.rot90(arr, -(rotate // 90))  # clockwise
    if hflip:
        arr = arr[:, ::-1]
    return np.ascontiguousarray(arr), note


# ----------------------------------------------------------------------------------------------
# box / fit compositor
# ----------------------------------------------------------------------------------------------

def _rounded_cov(xs, ys, box, r):
    """Anti-aliased coverage of a rounded rectangle at pixel centres xs (W,), ys (H,)."""
    bx0, by0, bx1, by1 = box
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    hx, hy = (bx1 - bx0) / 2 - r, (by1 - by0) / 2 - r
    qx = np.abs(xs[None, :] + 0.5 - cx) - hx
    qy = np.abs(ys[:, None] + 0.5 - cy) - hy
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
    return np.clip(0.5 - d, 0, 1).astype(np.float32)


class _BoxCompositor:
    """frame.mode box/fit: the window shown in a (rounded) box over a blurred, darkened,
    scaled-to-fill copy of the same frame that follows the window's motion."""

    def __init__(self, plan, cv2, fr):
        self.p, self.cv2 = plan, cv2
        lay = plan.lay
        OW, OH = plan.OW, plan.OH
        k = OH / 1920.0
        self.dim = float(fr.get("bg_dim", 0.62))
        self.desat = float(fr.get("bg_saturation", 0.85))
        sigma = float(fr.get("bg_blur", 40.0)) * k
        self.sw, self.sh = max(16, OW // 8), max(16, OH // 8)
        sc = self.sw / OW
        self.sig_small = sigma * sc
        bg_w_pre = plan.bg["w"] * plan.prescale
        q = max(1.0, bg_w_pre / self.sw)
        self.small_size = (max(2, int(round(plan.PW / q))), max(2, int(round(plan.PH / q))))
        self.qx, self.qy = plan.PW / self.small_size[0], plan.PH / self.small_size[1]
        rx0, ry0, rx1, ry1 = lay.region
        self.reg = (rx0, ry0, rx1, ry1)
        self.mask = _rounded_cov(np.arange(rx0, rx1, dtype=np.float64), np.arange(ry0, ry1, dtype=np.float64),
                                 lay.box, lay.radius)[..., None]
        self.full = bool(self.mask.min() > 0.999 and (rx0, ry0, rx1, ry1) == (0, 0, OW, OH))
        # soft drop shadow of the box, applied to the small background (smooth -> low res is fine)
        if lay.shadow > 0:
            us = (np.arange(self.sw) + 0.5) / sc - 0.5
            vs = (np.arange(self.sh) + 0.5) / sc - 0.5
            bx0, by0, bx1, by1 = lay.box
            off = 12 * k
            box_s = (bx0, by0 + off, bx1, by1 + off)
            m = _rounded_cov(us * sc, vs * sc, tuple(v * sc for v in box_s), lay.radius * sc)
            m = cv2.GaussianBlur(m, (0, 0), 26 * k * sc)
            self.shade = (1.0 - lay.shadow * m)[..., None].astype(np.float32)
        else:
            self.shade = None
        self._plan_blend()

    def _plan_blend(self):
        """Split the box region into fully covered rects (plain copy) and partial bands (blend)."""
        m = self.mask[..., 0]
        rh, rw = m.shape
        band = int(math.ceil(self.p.lay.radius)) + 2
        t1, b0 = min(rh, band), max(0, rh - band)
        self.partial, self.copy = [], []
        if b0 <= t1:
            self.partial.append((0, rh, 0, rw))
            return
        self.partial += [(0, t1, 0, rw), (b0, rh, 0, rw)]
        mid = m[(t1 + b0) // 2]
        full = np.nonzero(mid >= 0.999)[0]
        if len(full) == 0:
            self.partial.append((t1, b0, 0, rw))
            return
        c0, c1 = int(full[0]), int(full[-1]) + 1
        if c0 > 0:
            self.partial.append((t1, b0, 0, c0))
        if c1 < rw:
            self.partial.append((t1, b0, c1, rw))
        self.copy.append((t1, b0, c0, c1))

    def compose(self, pre, fg, k):
        cv2, p = self.cv2, self.p
        if self.full:
            return fg
        small_pre = cv2.resize(pre, self.small_size, interpolation=cv2.INTER_AREA)
        M = p.bg_matrix(k, self.sw, self.sh, 1.0)
        M = np.diag([1 / self.qx, 1 / self.qy]) @ (M + np.array([[0, 0, 0.5], [0, 0, 0.5]])) - np.array([[0, 0, 0.5], [0, 0, 0.5]])
        small = cv2.warpAffine(small_pre, M, (self.sw, self.sh), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                               borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        small = cv2.GaussianBlur(small, (0, 0), self.sig_small)
        luma = small @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        small = luma[..., None] + (small - luma[..., None]) * self.desat
        if self.shade is not None:
            small = small * self.shade
        small = np.clip(small * self.dim + 0.5, 0, 255).astype(np.uint8)
        out = cv2.resize(small, (p.OW, p.OH), interpolation=cv2.INTER_CUBIC)
        rx0, ry0, rx1, ry1 = self.reg
        for y0, y1, x0, x1 in self.copy:
            out[ry0 + y0:ry0 + y1, rx0 + x0:rx0 + x1] = fg[y0:y1, x0:x1]
        for y0, y1, x0, x1 in self.partial:
            bb = out[ry0 + y0:ry0 + y1, rx0 + x0:rx0 + x1].astype(np.float32)
            ff = fg[y0:y1, x0:x1].astype(np.float32)
            mm = self.mask[y0:y1, x0:x1]
            out[ry0 + y0:ry0 + y1, rx0 + x0:rx0 + x1] = np.clip(bb + (ff - bb) * mm + 0.5, 0, 255).astype(np.uint8)
        return out


# ----------------------------------------------------------------------------------------------
# main entry: render one item (runs in a worker process)
# ----------------------------------------------------------------------------------------------

def render_item(job):
    t0 = time.time()
    cv2 = _cv2(job.get("cv_threads", 4))
    res = dict(id=job["id"], out=job["out_path"], audio=job.get("audio_path"), warnings=[])
    try:
        if not os.path.exists(job["out_path"]):
            _render_video(job, cv2, res) if job["type"] == "video" else _render_photo(job, cv2, res)
        else:
            res["cached"] = True
        if job.get("audio_path") and not os.path.exists(job["audio_path"]):
            extract_audio(job)
        res["seconds"] = time.time() - t0
        res["ok"] = True
    except Exception as e:
        res["ok"] = False
        res["error"] = f"{e}\n{traceback.format_exc()}"
    return res


def _encoder(job, tmp_name):
    OW, OH = job["OW"], job["OH"]
    vf = (f"format=rgb48le,lut3d=file={os.path.basename(job['lut'])}:interp=tetrahedral,"
          f"scale={RGB2YUV},format=yuv420p,{SETPARAMS709}")
    cmd = [FFMPEG, "-nostdin", "-hide_banner", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{OW}x{OH}", "-framerate", str(job["fps"]), "-thread_queue_size", "4", "-i", "-", "-vf", vf,
           "-c:v", "libx264", "-preset", job.get("int_preset", "veryfast"), "-crf", str(job.get("int_crf", 13)),
           "-threads", str(min(3, job.get("enc_threads", 3))), "-x264-params", "rc-lookahead=8",
           *TAGS709, "-an", tmp_name]
    return FrameWriter(cmd, qsize=3, cwd=os.path.dirname(job["out_path"]))


def _warp_loop(job, cv2, plan, next_frame, res):
    tmp = os.path.basename(job["out_path"]) + ".tmp.mkv"
    tmp_full = os.path.join(os.path.dirname(job["out_path"]), tmp)
    enc = _encoder(job, tmp)
    comp = _BoxCompositor(plan, cv2, job["frame"]) if plan.mode != "crop" else None
    interp = cv2.INTER_CUBIC if job.get("interp", "cubic") == "cubic" else cv2.INTER_LANCZOS4
    t_warp = 0.0
    try:
        for k in range(job["n"]):
            src = next_frame(k)
            tw = time.time()
            sig = plan.blur_sigma(k)
            s2 = cv2.GaussianBlur(src, (0, 0), sig) if sig > 0 else src
            out = cv2.warpAffine(s2, plan.cv_mats[k], plan.region_size, flags=interp | cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_REPLICATE)
            if comp is not None:
                out = comp.compose(src, out, k)
            t_warp += time.time() - tw
            enc.write(out)
        enc.close()
    except BaseException:
        enc.abort()
        try:
            enc.proc.wait(timeout=10)
            if os.path.exists(tmp_full):
                os.remove(tmp_full)
        except Exception:
            pass
        raise
    atomic_replace(tmp_full, job["out_path"])
    res["warp_s"] = round(t_warp, 2)


def _render_video(job, cv2, res):
    info, total, hflip, W, H = _src_geometry(job)
    stab_raw = None
    st = job.get("stabilize")
    method = None
    if st:
        st = st if isinstance(st, dict) else {}
        method = st.get("method", "cv")
        if method == "cv":
            stab_raw = analyse_stabilisation(job, cv2)
    times = output_times(job)  # source time of each output frame (keys are in source time)
    plan = framing.Plan(W, H, job["OW"], job["OH"], job["frame"], job["n"], times=times, stab=stab_raw,
                        stab_opts=st or {}, tilt_deg=job.get("tilt_deg", 0.0), fps=job["fps"])
    res["plan"] = plan.describe()
    res["warnings"] += plan.warnings
    x, y, w, h = plan.crop
    rx, ry, rw, rh = upright_rect_to_raw((x, y, w, h), info["w"], info["h"], total, hflip)
    pw, ph = (plan.PH, plan.PW) if total in (90, 270) else (plan.PW, plan.PH)
    chain = _speed_chain(job)
    if method == "vidstab":
        trf = vidstab_detect(job)
        sm = int(round(float(st.get("smooth", 0.6)) * job["fps"]))
        chain.append(f"vidstabtransform=input={os.path.basename(trf)}:smoothing={sm}:optzoom=1:zoomspeed=0.2:"
                     f"interpol=bicubic:crop=black")
    if (rx, ry, rw, rh) != (0, 0, info["w"], info["h"]):
        chain.append(f"crop={rw}:{rh}:{rx}:{ry}:exact=1")
    flags = "lanczos" if plan.prescale < 0.999 else "bicubic"
    chain.append(f"scale={pw}:{ph}:{YUV2RGB.replace('flags=', 'flags=' + flags + '+')}")
    chain += rotation_filters(total, hflip)
    chain.append("format=rgb24")
    cmd = _decode_base(job) + ["-vf", ",".join(chain), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    rd = FrameReader(cmd, (plan.PH, plan.PW, 3), qsize=3, cwd=os.path.dirname(job["stab_cache"]))
    state = {"last": None, "missing": 0}
    if job.get("timemap"):
        fb = job.get("frame_blend", "auto")
        picker = _TimePicker(rd, times, job["in"], job["src_fps"], fb in ("auto", True, "blend"), cv2)

        def next_frame(k):
            return picker.frame(k)
    else:
        picker = None

        def next_frame(k):
            f = rd.read()
            if f is None:
                if state["last"] is None:
                    raise RuntimeError(f"decoder produced no frames: {rd.stderr_text()[-1500:]}")
                state["missing"] += 1
                return state["last"]
            state["last"] = f
            return f

    try:
        _warp_loop(job, cv2, plan, next_frame, res)
    finally:
        rd.close()
    missing = picker.missing if picker else state["missing"]
    if missing:
        msg = f"source ended early: last frame held for {missing} frame(s)"
        res["warnings"].append(msg)
    if stab_raw is not None:
        st_ = stab_raw["stats"]
        res["stab"] = f"inliers median {int(np.median(st_)) if len(st_) else 0}, zoom {plan.extra_zoom:.3f}"


def _render_photo(job, cv2, res):
    arr, note = _load_photo(job["decode_src"], job.get("rotate", 0), job.get("hflip", False))
    H, W = arr.shape[:2]
    plan = framing.Plan(W, H, job["OW"], job["OH"], job["frame"], job["n"], times=np.arange(job["n"]) / job["fps"],
                        tilt_deg=job.get("tilt_deg", 0.0), fps=job["fps"])
    res["plan"] = plan.describe() + f" | {note}"
    res["warnings"] += plan.warnings
    x, y, w, h = plan.crop
    region = arr[y:y + h, x:x + w]
    if (plan.PW, plan.PH) != (w, h):
        pre = cv2.resize(region, (plan.PW, plan.PH), interpolation=cv2.INTER_AREA)
    else:
        pre = np.ascontiguousarray(region)
    del arr, region
    _warp_loop(job, cv2, plan, lambda k: pre, res)


# ----------------------------------------------------------------------------------------------
# audio
# ----------------------------------------------------------------------------------------------

def _atempo_chain(speed):
    f = []
    s = speed
    while s < 0.5:
        f.append("atempo=0.5"); s /= 0.5
    while s > 2.0:
        f.append("atempo=2.0"); s /= 2.0
    f.append(f"atempo={s:.6f}")
    return f


def extract_audio(job):
    """Clip sound for exactly n frames (n*48000/fps samples), float WAV, 120 Hz high-pass.
    Uniform speed != 1: mute (default) | pitch-preserving | natural.  speed_map: 1x segments keep
    their sound, slowed/sped-up segments are faded out (0.12 s fades)."""
    from audio import write_wav_f32, read_wav
    out = job["audio_path"]
    sr = 48000
    nsamp = int(round(job["n"] * sr / job["fps"]))
    info = probe(job["src"]) if job["type"] == "video" else None
    mode = job.get("speed_audio", "mute")
    tmp = out + ".tmp.wav"
    hp = f"highpass=f={CLIP_HIGHPASS_HZ}:poles=2"
    silent = (job["type"] != "video" or not info["has_audio"] or
              (not job.get("speed_map") and abs(job["speed"] - 1.0) > 1e-6 and mode == "mute"))
    if silent:
        write_wav_f32(tmp, np.zeros((nsamp, 2), np.float32))
    elif job.get("speed_map"):
        dur = job["out"] - job["in"] + 0.2
        p = run([FFMPEG, "-nostdin", "-v", "error", "-ss", f"{job['in']:.6f}", "-t", f"{dur:.6f}", "-i", job["src"],
                 "-map", "0:a:0", "-vn", "-af", f"aresample={sr},{hp}", "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"])
        x = np.frombuffer(p.stdout, np.float32).reshape(-1, 2)
        src_t, spd = framing.time_map_audio(job["in"], job["out"], job["speed_map"], sr, nsamp)
        pos = (src_t - job["in"]) * sr
        i0 = np.clip(np.floor(pos).astype(np.int64), 1, len(x) - 3)
        f = (pos - i0)[:, None].astype(np.float32)
        xm1, x0, x1, x2 = x[i0 - 1], x[i0], x[i0 + 1], x[i0 + 2]
        y = x0 + 0.5 * f * (x1 - xm1 + f * (2 * xm1 - 5 * x0 + 4 * x1 - x2 + f * (3 * (x0 - x1) + x2 - xm1)))
        g = (np.abs(spd - 1.0) < 0.03).astype(np.float32)
        w = int(0.12 * sr)
        g = np.convolve(g, np.ones(w, np.float32) / w, mode="same")
        y = y * np.sin(g * np.pi / 2)[:, None]
        write_wav_f32(tmp, y.astype(np.float32))
    else:
        af = []
        if abs(job["speed"] - 1.0) > 1e-6:
            af += _atempo_chain(job["speed"]) if mode == "pitch" else \
                [f"asetrate={sr * job['speed']:.3f}", f"aresample={sr}"]
        af += [f"aresample={sr}", hp, f"apad=whole_len={nsamp}", f"atrim=end_sample={nsamp}"]
        dur = job["n"] / job["fps"] * job["speed"] + 0.3
        cmd = [FFMPEG, "-nostdin", "-hide_banner", "-v", "error", "-y", "-ss", f"{job['in']:.6f}", "-t", f"{dur:.6f}",
               "-i", job["src"], "-map", "0:a:0", "-vn", "-af", ",".join(af), "-ac", "2", "-ar", str(sr),
               "-c:a", "pcm_f32le", tmp]
        run(cmd)
    atomic_replace(tmp, out)

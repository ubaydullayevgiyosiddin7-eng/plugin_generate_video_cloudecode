"""Verify a rendered film against its EDL.

  python test/verify.py test/test_edl.json [--film path.mp4] [--preview] [--outdir DIR]
                         [--video-dir D --photo-dir D --music-dir D]   (same overrides as render.py)

Checks: stream format, frame count / duration vs timeline, loudness (ebur128), unexpected black or
frozen frames, clicks at cuts, motion smoothness of photo/pan items (measured vs planned camera
path), and writes contact sheets around every transition and text to test/out/verify/ (or --outdir).
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from common import FFMPEG, FFPROBE, YUV2RGB, run  # noqa: E402
import edl as edlmod  # noqa: E402

TW, TH = 270, 480  # thumbnail size


def ffprobe_json(path):
    p = run([FFPROBE, "-v", "error", "-count_packets", "-show_streams", "-show_format", "-of", "json", path])
    return json.loads(p.stdout)


def decode_frames(path, want, w, h):
    """Decode the whole film at w x h and keep frames whose index is in `want` (and all if want None)."""
    cmd = [FFMPEG, "-nostdin", "-v", "error", "-i", path, "-vf", f"scale={w}:{h}:{YUV2RGB.replace('flags=', 'flags=area+')},format=rgb24",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = w * h * 3
    out, i = {}, 0
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        if want is None or i in want:
            out[i] = np.frombuffer(b, np.uint8).reshape(h, w, 3)
        i += 1
    p.wait()
    return out, i


def strip(frames, labels, path, safe=False):
    w, h = frames[0].shape[1], frames[0].shape[0]
    im = Image.new("RGB", (w * len(frames), h + 22), (20, 20, 20))
    d = ImageDraw.Draw(im)
    for i, (f, lab) in enumerate(zip(frames, labels)):
        im.paste(Image.fromarray(f), (i * w, 22))
        d.text((i * w + 4, 4), lab, fill=(255, 220, 80))
        if safe:  # Reels safe zone guide
            y0, y1 = 22 + int(0.14 * h), 22 + int(0.78 * h)
            x0, x1 = i * w + int(0.06 * w), i * w + int(0.94 * w)
            d.rectangle([x0, y0, x1, y1], outline=(0, 255, 255))
    im.save(path, quality=88)


def ebur128(path):
    p = subprocess.run([FFMPEG, "-nostdin", "-hide_banner", "-i", path, "-map", "0:a:0", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    t = p.stderr.decode("utf-8", "replace")
    summ = t[t.rfind("Summary:"):]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1))
    LRA = float(re.search(r"LRA:\s+(-?[\d.]+) LU", summ).group(1))
    pk = re.search(r"Peak:\s+(-?[\d.inf]+) dBFS", summ)
    return I, LRA, float(pk.group(1)) if pk else None


def detect(path, filt, key):
    p = subprocess.run([FFMPEG, "-nostdin", "-hide_banner", "-i", path, "-map", "0:v:0", "-vf", filt, "-f", "null", "-"],
                       stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    t = p.stderr.decode("utf-8", "replace")
    return t


def black_intervals(path):
    t = detect(path, "blackdetect=d=0.03:pic_th=0.97:pix_th=0.08", "black")
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", t)]


def freeze_intervals(path):
    t = detect(path, "freezedetect=n=-60dB:d=0.35", "freeze")
    st = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", t)]
    en = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", t)]
    return list(zip(st, en + [None] * (len(st) - len(en))))


def audio_clicks(path, cut_times, sr=48000):
    p = run([FFMPEG, "-nostdin", "-v", "error", "-i", path, "-map", "0:a:0", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"])
    x = np.frombuffer(p.stdout, np.float32)
    d2 = np.abs(np.diff(x, 2))
    res = []
    for t in cut_times:
        c = int(t * sr)
        win = d2[max(0, c - int(0.006 * sr)):c + int(0.006 * sr)]
        ctx = d2[max(0, c - int(0.25 * sr)):c + int(0.25 * sr)]
        if len(win) == 0 or len(ctx) == 0:
            continue
        res.append((t, float(win.max() / (np.percentile(ctx, 99.5) + 1e-9))))
    return res


def motion_track(frames):
    """Per consecutive pair: similarity (scale, dx, dy) via ECC on the central area (sub-pixel)."""
    import cv2
    out = []
    prev = None
    for f in frames:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32)
        if prev is not None:
            warp = np.eye(2, 3, dtype=np.float32)
            try:
                _, warp = cv2.findTransformECC(prev, g, warp, cv2.MOTION_AFFINE,
                                               (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-7), None, 5)
            except cv2.error:
                warp = np.full((2, 3), np.nan, np.float32)
            s = math.sqrt(abs(np.linalg.det(warp[:, :2].astype(np.float64))))
            out.append((s, float(warp[0, 2]), float(warp[1, 2])))
        prev = g
    return np.array(out)


def expected_track(item, n, OW, OH, fps, w, h):
    """Planned camera path of a photo item -> expected inter-frame (scale, dx, dy) at w x h."""
    import framing
    from PIL import Image as _I
    from PIL import ImageOps
    im = ImageOps.exif_transpose(_I.open(item["_src"]))
    W, H = im.size
    if item.get("rotate", 0) % 180:
        W, H = H, W
    plan = framing.Plan(W, H, OW, OH, item["frame"], n, times=np.arange(n) / fps)
    S = np.diag([w / OW, h / OH, 1.0])
    out = []
    for k in range(n - 1):
        # output_k -> source -> output_{k+1}, expressed at thumbnail scale (warp maps frame k+1 -> k
        # coordinates in ECC's convention: prev(x) ~ cur(W x) ; we report cur->prev)
        T = S @ np.linalg.inv(plan.mats[k]) @ plan.mats[k + 1] @ np.linalg.inv(S)
        s = math.sqrt(abs(np.linalg.det(T[:2, :2])))
        out.append((s, T[0, 2], T[1, 2]))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl")
    ap.add_argument("--film", help="rendered film (default: the EDL's output path)")
    ap.add_argument("--preview", action="store_true", help="the film is a --preview render (half size)")
    ap.add_argument("--outdir", default=os.path.join(HERE, "out", "verify"), help="report/contact-sheet folder")
    for k in ("video", "photo", "proxy", "music"):
        ap.add_argument(f"--{k}-dir")
    a = ap.parse_args()
    edl = edlmod.load(a.edl, preview=a.preview,
                      path_overrides={k: getattr(a, f"{k}_dir") for k in ("video", "photo", "proxy", "music")})
    film = a.film or edl["output"]["path"]
    tl = edl["timeline"]
    fps = tl["fps"]
    OW, OH = edl["output"]["w"], edl["output"]["h"]
    vd = a.outdir
    os.makedirs(vd, exist_ok=True)
    rep = {"film": film}
    ok = True

    # ---------------- format
    j = ffprobe_json(film)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    au = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    nfr = int(v.get("nb_read_packets", 0))
    rep["video"] = dict(codec=v["codec_name"], profile=v.get("profile"), pix_fmt=v["pix_fmt"],
                        size=f"{v['width']}x{v['height']}", r=v["r_frame_rate"], avg=v["avg_frame_rate"],
                        color=(v.get("color_primaries"), v.get("color_transfer"), v.get("color_space"), v.get("color_range")),
                        frames=nfr, expected_frames=tl["total_f"])
    if au:
        rep["audio"] = dict(codec=au["codec_name"], sr=au["sample_rate"], ch=au["channels"],
                            bitrate=au.get("bit_rate"), duration=float(au.get("duration", 0)))
    rep["duration"] = float(j["format"]["duration"])
    if nfr != tl["total_f"]:
        ok = False
        rep["FAIL_frames"] = f"{nfr} frames, timeline says {tl['total_f']}"

    # ---------------- loudness
    I, LRA, pk = ebur128(film)
    rep["loudness"] = dict(I=I, LRA=LRA, true_peak=pk, target=edl["audio"]["target_lufs"], tp_max=edl["audio"]["true_peak"])
    if abs(I - edl["audio"]["target_lufs"]) > 1.0 or (pk is not None and pk > edl["audio"]["true_peak"] + 0.2):
        ok = False
        rep["FAIL_loudness"] = True

    # ---------------- black / frozen
    dips = []
    for r in tl["rows"]:
        if r["t_out"] == "dip_black":
            dips.append((r["end_f"] - r["o_out"]) / fps)
    blacks = black_intervals(film)
    unexpected = [b for b in blacks if not any(d - 0.1 <= (b[0] + b[1]) / 2 <= d + r_["o_out"] / fps + 0.1
                                               for d, r_ in [(dd, rr) for dd, rr in zip(dips, [x for x in tl["rows"] if x["t_out"] == "dip_black"])])]
    rep["black"] = dict(all=blacks, unexpected=unexpected)
    if unexpected:
        ok = False
    rep["frozen"] = freeze_intervals(film)

    # ---------------- clicks at cuts / transitions
    cuts = [r["start_f"] / fps for r in tl["rows"][1:]] + [r["end_f"] / fps for r in tl["rows"][:-1]]
    clicks = audio_clicks(film, sorted(set(round(c, 4) for c in cuts)))
    rep["click_ratio_max"] = max(c[1] for c in clicks) if clicks else None
    rep["clicks"] = [(round(t, 3), round(r, 2)) for t, r in clicks]

    # ---------------- contact sheets
    want = set()
    tsheets = []
    for i, r in enumerate(tl["rows"][1:], 1):
        s = r["start_f"]
        o = r["o_in"]
        if o:
            idx = [s - 3, s, s + o // 4, s + o // 2, s + (3 * o) // 4, s + o - 1, s + o + 2]
        else:
            idx = [s - 2, s - 1, s, s + 1]
        idx = [min(tl["total_f"] - 1, max(0, x)) for x in idx]
        want.update(idx)
        tsheets.append((i, r, idx))
    xsheets = []
    for i, tx in enumerate(edl["texts"]):
        f0, f1 = int(round(tx["start"] * fps)), int(round(tx["end"] * fps))
        idx = [f0 + 3, f0 + 8, f0 + 15, (f0 + f1) // 2, f1 - 8, f1 - 2]
        idx = [min(tl["total_f"] - 1, max(0, x)) for x in idx]
        want.update(idx)
        xsheets.append((i, tx, idx))
    frames, total_dec = decode_frames(film, want, TW, TH)
    for i, r, idx in tsheets:
        strip([frames[x] for x in idx], [f"f{x} {x / fps:.2f}s" for x in idx],
              os.path.join(vd, f"trans_{i:02d}_{r['t_in']}_{r['id']}.jpg"))
    for i, tx, idx in xsheets:
        strip([frames[x] for x in idx], [f"f{x} {x / fps:.2f}s" for x in idx],
              os.path.join(vd, f"text_{i:02d}_{tx['style']}.jpg"), safe=True)

    # ---------------- smoothness: photo items (static content -> camera path fully known)
    sm = {}
    for r, it in zip(tl["rows"], edl["items"]):
        if it["type"] != "photo":
            continue
        a0, a1 = r["start_f"] + r["o_in"] + 1, r["end_f"] - r["o_out"] - 1
        idx = list(range(a0, a1))
        fr, _ = decode_frames(film, set(idx), 540, 960)
        meas = motion_track([fr[x] for x in idx])
        exp_full = expected_track(it, r["n"], OW, OH, fps, 540, 960)
        exp = exp_full[a0 - r["start_f"]:a1 - r["start_f"] - 1]
        # ECC warp maps cur->prev coordinates; expected T maps out_k -> out_{k+1}: compare inverse
        inv = []
        for s, dx, dy in exp:
            inv.append((1 / s, -dx / s, -dy / s))
        exp = np.array(inv)
        err = meas - exp
        vx = meas[:, 1]
        jitter = np.diff(vx, 2)
        sm[it["id"]] = dict(frames=len(idx), mean_dx=float(np.mean(np.abs(exp[:, 1]))),
                            rms_err_dx=float(np.sqrt(np.nanmean(err[:, 1] ** 2))),
                            rms_err_dy=float(np.sqrt(np.nanmean(err[:, 2] ** 2))),
                            rms_err_scale=float(np.sqrt(np.nanmean(err[:, 0] ** 2))),
                            accel_rms_measured=float(np.sqrt(np.nanmean(jitter ** 2))),
                            accel_rms_planned=float(np.sqrt(np.mean(np.diff(exp[:, 1], 2) ** 2))))
        np.savetxt(os.path.join(vd, f"motion_{it['id']}.csv"), np.hstack([meas, exp]), delimiter=",",
                   header="meas_scale,meas_dx,meas_dy,plan_scale,plan_dx,plan_dy", fmt="%.5f")
    rep["smoothness_photo"] = sm
    rep["PASS"] = ok
    with open(os.path.join(vd, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, default=str)
    print(json.dumps(rep, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

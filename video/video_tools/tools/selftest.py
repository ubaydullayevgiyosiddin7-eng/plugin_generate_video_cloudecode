"""One-command smoke test of the whole kit (engine + every tool) on synthetic media.

  python tools/selftest.py            run everything, print PASS/FAIL/WARN/SKIP per check, clean up
  python tools/selftest.py --quick    skip the slow checks (preview render, export, proxies)
  python tools/selftest.py --keep     keep the work folder (video_tools/_test/selftest_<time>/) for inspection
  python tools/selftest.py --only music_beats,edl_builder     run a subset (dependencies run automatically)

Never touches real footage: make_test_media.py synthesises clips (incl. an iPhone-style rotation tag),
a photo and a 100 BPM bed; synthetic HEICs (front-camera EXIF, IMG_E edit pair, .AAE sidecar) are
generated for heic_convert / probe_media.  Everything is written under video_tools/_test/ and deleted
at the end (the _test folder too, if it is then empty).  Free disk is checked first: below 1.5 GB the
heavy checks (video media, render, export, proxies) are skipped with a WARN.  Exit code 1 if any check
FAILs (WARN/SKIP do not fail).  Typical run: 2-5 minutes on a quiet 8 GB laptop.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import ENGINE_DIR, FFMPEG, FFPROBE, KIT_DIR, TOOLS_DIR, free_gb, safe_console  # noqa: E402

PY = sys.executable
TOOLS = ["probe_media", "heic_convert", "make_proxies", "contact_sheet", "reframe_preview", "measure_motion",
         "final_check", "music_beats", "music_bed", "edl_builder", "export", "picks_check", "music_catalog"]
ENGINE_SCRIPTS = ["render.py", "test/make_test_media.py", "test/verify.py", "test/path_test.py",
                  "test/smooth_test.py", "test/font_sheet.py", "test/grade_sheet.py"]
HEAVY_MIN_GB = 1.5


class Fail(Exception):
    pass


class Skip(Exception):
    pass


def sh(args, timeout=900, cwd=None, ok_codes=(0,), env_extra=None):
    """Run a command, return combined stdout+stderr text; raise Fail with the tail on a bad exit code."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", **(env_extra or {}))
    try:
        p = subprocess.run([str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd,
                           stdin=subprocess.DEVNULL, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        raise Fail(f"timeout after {timeout}s: {' '.join(map(str, args))[:200]}")
    out = p.stdout.decode("utf-8", "replace")
    if p.returncode not in ok_codes:
        raise Fail(f"exit {p.returncode}: {' '.join(map(str, args))[:160]}\n" + "\n".join(out.strip().splitlines()[-12:]))
    return out


def tool(name):
    return os.path.join(TOOLS_DIR, name + ".py")


def eng(script):
    return os.path.join(ENGINE_DIR, script)


def need(cond, msg):
    if not cond:
        raise Fail(msg)


class Ctx:
    def __init__(self, work, heavy, quick):
        self.work, self.heavy, self.quick = work, heavy, quick
        self.media = os.path.join(work, "media")
        self.out = os.path.join(work, "out")
        self.cache = os.path.join(work, "cache")
        self.has_video = False
        self.has_audio_media = False
        self.has_vmaf = False
        self.preview_film = None
        os.makedirs(self.out, exist_ok=True)

    def dirs(self):
        return ["--video-dir", self.media, "--photo-dir", self.media, "--music-dir", self.media]


# ---------------------------------------------------------------------------------------------- checks

def c_env(c):
    need(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} (need 3.10+, tested 3.11)")
    for exe in (FFMPEG, FFPROBE):
        need(shutil.which(exe) or os.path.exists(exe), f"{exe} not found on PATH")
    enc = sh([FFMPEG, "-hide_banner", "-encoders"])
    fil = sh([FFMPEG, "-hide_banner", "-filters"])
    need("libx264" in enc, "ffmpeg lacks libx264")
    miss = []
    for mod in ("numpy", "cv2", "PIL", "pillow_heif", "scipy", "fontTools", "librosa"):
        try:
            __import__(mod)
        except Exception as e:
            miss.append(f"{mod} ({e.__class__.__name__})")
    need(not miss, "missing Python modules: " + ", ".join(miss) + "  -> pip install -r requirements.txt")
    c.has_vmaf = "libvmaf" in fil
    notes = [] if "libx265" in enc else ["no libx265 (export hevc45 unavailable)"]
    if not c.has_vmaf:
        notes.append("no libvmaf (export --vmaf unavailable)")
    ver = sh([FFMPEG, "-hide_banner", "-version"]).splitlines()[0]
    return ("WARN" if notes else "PASS"), f"{ver[:60]}; " + ("; ".join(notes) or "x264/x265/vmaf ok")


def c_help(c):
    bad = []
    for t in TOOLS + ["selftest"]:
        try:
            out = sh([PY, tool(t), "--help"], timeout=120)
            if "usage" not in out.lower():
                bad.append(t)
        except Fail as e:
            bad.append(f"{t}: {str(e).splitlines()[0]}")
    for s in ENGINE_SCRIPTS:
        try:
            sh([PY, eng(s), "--help"], timeout=120)
        except Fail as e:
            bad.append(f"engine/{s}: {str(e).splitlines()[0]}")
    need(not bad, "--help failed: " + "; ".join(bad))
    return "PASS", f"{len(TOOLS) + 1} tools + {len(ENGINE_SCRIPTS)} engine scripts"


def c_media(c):
    args = [PY, eng("test/make_test_media.py"), "--out", c.media]
    if not c.heavy:
        args.append("--skip-video")
    sh(args, timeout=600)
    c.has_audio_media = os.path.exists(os.path.join(c.media, "music_bed_test.wav"))
    c.has_video = c.heavy and all(os.path.exists(os.path.join(c.media, f))
                                  for f in ("clip_land.mp4", "clip_portrait.mov", "clip_shaky.mp4"))
    need(c.has_audio_media and os.path.exists(os.path.join(c.media, "test_photo.jpg")), "test media missing")
    mb = sum(os.path.getsize(os.path.join(c.media, f)) for f in os.listdir(c.media)) / 1e6
    return ("PASS" if c.heavy else "WARN"), f"{len(os.listdir(c.media))} files, {mb:.0f} MB" + \
        ("" if c.heavy else " (photo + music only: low disk)")


def c_timeline(c):
    if not c.has_video:
        raise Skip("no video test media")
    out = sh([PY, eng("render.py"), eng("test/test_edl.json"), "--timeline", *c.dirs()])
    need("TOTAL 0:34.933" in out and "1048 frames" in out, "unexpected test timeline total:\n" + out[-400:])
    return "PASS", "test_edl.json: 10 items, 34.933 s, 1048 frames"


def _short_edl(c):
    e = json.load(open(eng("test/test_edl.json"), encoding="utf-8"))
    keep = ["v01", "v02", "v08", "p01"]
    e["items"] = [it for it in e["items"] if it["id"] in keep]
    for it in e["items"]:
        if it["id"] == "v08":       # first key (t=3.3) now 0.3 s outside the used range -> one summary NOTE (R24)
            it["in"] = 3.6
            it["speed_map"][0]["in"] = 3.6
    e["transitions"] = [{"after": "v01", "type": "crossfade", "dur": 0.5},
                        {"after": "v02", "type": "whip", "dur": 0.25, "dir": "left"},
                        {"after": "v08", "type": "dip_white", "dur": 0.6}]
    e["texts"] = [{"text": "Selftest", "start": 0.3, "end": 3.0, "style": "title"},
                  {"text": "oʻynoqi · label", "start": 6.5, "end": 8.5, "style": "label"},
                  {"text": "Credit line\nsecond line", "start": 11.0, "end": 12.5, "style": "credit", "y": 0.6}]
    e["paths"] = {"video": os.path.relpath(c.media, c.out), "photo": os.path.relpath(c.media, c.out),
                  "music": os.path.relpath(c.media, c.out)}
    e["output"]["path"] = "short.mp4"
    e["music"]["fade_out"] = 1.0
    p = os.path.join(c.out, "short_edl.json")
    json.dump(e, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return p


def c_render_preview(c):
    if not c.has_video:
        raise Skip("no video test media")
    if c.quick:
        raise Skip("--quick")
    edl = _short_edl(c)
    # VT_RAM_GB_OVERRIDE fakes a RAM-starved machine: the engine must fall back to 1 worker (R4)
    out = sh([PY, eng("render.py"), edl, "--preview", "--jobs", "2", "--cache-root", c.cache], timeout=1800,
             env_extra={"VT_RAM_GB_OVERRIDE": "1.2"})
    film = os.path.join(c.out, "short_preview.mp4")
    need(os.path.exists(film) and "DONE" in out, "no preview film:\n" + out[-600:])
    c.preview_film = film
    need("WARNING RAM" in out and "--jobs 1 instead of 2" in out and "with 1 worker(s)" in out,
         "low-RAM guard did not force --jobs 1:\n" + "\n".join(l for l in out.splitlines() if "RAM" in l or "worker" in l))
    need("RAM: 1.20 GB available" in out, "RAM line missing")
    need("NOTE 1 item(s) have frame keys up to 1 s outside" in out and "WARNING v08: key times" not in out,
         "key-range NOTE (R24) missing:\n" + "\n".join(l for l in out.splitlines() if "key" in l))
    need("preview from the original sources" in out, "no-proxy NOTE missing")
    m = re.search(r"film ([\d.]+)s .* total (\d+)s", out)
    return "PASS", f"{os.path.getsize(film) / 1e6:.1f} MB" + (f", {m.group(1)} s film in {m.group(2)} s" if m else "") + \
        "; low-RAM -> 1 worker, key NOTE, no-proxy NOTE"


def c_final_check(c):
    if not c.preview_film:
        raise Skip("no preview film")
    out = sh([PY, tool("final_check"), c.preview_film, os.path.join(c.out, "short_edl.json"), "--preview"])
    need(out.strip().splitlines()[-1].startswith("PASS"), out[-500:])
    j = [l for l in out.splitlines() if l.startswith(("PASS  jitter", "WARN  jitter"))]
    need(j and "vs plan" in j[0], "photo motion not compared with the planned path:\n" + "\n".join(j))
    need(j[0].startswith("PASS") and "under text skipped" in j[0], "p01 (Ken Burns, credit text over its end): " + j[0])
    return "PASS", "format/duration/loudness ok; " + (j[0].split("vs plan")[1].strip()[:44] if j else "")


def c_designed_pan(c):
    """R12: a fast designed pan (hold, then ~1.1 frame widths in 1.6 s, bell-shaped speed) rendered with the
    engine's framing code: the old residual meter false-alarms, measured-vs-planned must stay small."""
    import numpy as np
    import cv2
    sys.path.insert(0, TOOLS_DIR)
    sys.path.insert(0, ENGINE_DIR)
    import framing
    import final_check as fc
    import measure_motion as mm
    from itemrender import _load_photo
    photo = os.path.join(c.media, "test_photo.jpg")
    OW, OH, fps, n = 540, 960, 30, 75
    fr = {"mode": "crop", "ease": "inout", "cx0": 0.5, "cx1": 0.5, "cy0": 0.5, "cy1": 0.5, "zoom0": 1.0, "zoom1": 1.0,
          "keys": [{"t": 0.6, "cx": 0.24, "cy": 0.5, "zoom": 1.6}, {"t": 2.2, "cx": 0.76, "cy": 0.5, "zoom": 1.6}]}
    arr, _ = _load_photo(photo)
    H, W = arr.shape[:2]
    plan = framing.Plan(W, H, OW, OH, fr, n, times=np.arange(n) / fps, fps=fps)
    x, y, w, h = plan.crop
    pre = cv2.resize(arr[y:y + h, x:x + w], (plan.PW, plan.PH), interpolation=cv2.INTER_AREA)
    clip = os.path.join(c.out, "designed_pan.mp4")
    enc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                            "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "veryfast",
                            "-pix_fmt", "yuv420p", clip], stdin=subprocess.PIPE)
    for k in range(n):
        enc.stdin.write(cv2.warpAffine(pre, plan.cv_mats[k], plan.region_size, flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                                       borderMode=cv2.BORDER_REPLICATE).tobytes())
    enc.stdin.close()
    enc.wait()
    meas = mm.motion(clip, None, 0.1, (n - 3) / fps)
    old = mm.stats(meas)
    vp = fc.vs_plan(meas, fc.planned_motion({"_src": photo, "frame": fr, "rotate": 0}, n, OW, OH, fps), 3)
    need(vp is not None and vp["rms"] < 0.15 and vp["max"] < 0.6,
         f"measured-vs-plan too high on a clean designed pan: {vp}")
    need(old["jitter_max"] > 0.6 or old["jitter_rms"] > 0.15,
         f"test pan not demanding enough (old residual {old['jitter_rms']:.3f}/{old['jitter_max']:.3f}) - test invalid")
    return "PASS", (f"fast pan {vp['plan_speed_max']:.0f} px/frame: old residual {old['jitter_rms']:.2f}/"
                    f"{old['jitter_max']:.2f} px (would WARN) vs plan {vp['rms']:.3f}/{vp['max']:.3f} px")


def c_measure_motion(c):
    if not c.preview_film:
        raise Skip("no preview film")
    tl = json.loads(sh([PY, eng("render.py"), os.path.join(c.out, "short_edl.json"), "--timeline", "--timeline-json",
                        os.path.join(c.out, "tl.json")]) and open(os.path.join(c.out, "tl.json")).read())
    row = next(r for r in tl["items"] if r["id"] == "p01")
    out = sh([PY, tool("measure_motion"), c.preview_film, "--start", f"{row['start'] + row['overlap_in'] + 0.05:.3f}",
              "--end", f"{row['end'] - row['overlap_out'] - 0.05:.3f}", "--json"])
    s = json.loads(out.strip().splitlines()[-1])
    need(s.get("jitter_rms", 9) < 0.15, f"photo jitter rms {s.get('jitter_rms')} px (expected < 0.15)")
    return "PASS", f"photo Ken Burns jitter rms {s['jitter_rms']:.3f} px, max {s['jitter_max']:.3f} px"


def c_path_smooth(c):
    msg = ""
    if not c.quick:   # ~1-2.5 min: 90 frames of feature tracking at 1080x1920
        sh([PY, eng("test/smooth_test.py"), "--photo", os.path.join(c.media, "test_photo.jpg"), "--outdir", c.out])
        rep = json.load(open(os.path.join(c.out, "smooth_report.json")))
        ours, naive = rep["ours"]["rms_err_vs_plan"], rep["naive_integer_crop"]["rms_err_vs_plan"]
        need(ours < 0.1 and ours < naive, f"sub-pixel pan error {ours:.3f} px (naive {naive:.3f})")
        msg = f"smooth_test: engine {ours:.3f} px vs integer crop {naive:.3f} px"
    elif not c.has_video:
        raise Skip("--quick and no video test media")
    if c.has_video:
        out = sh([PY, eng("test/path_test.py"), eng("test/test_edl.json"), "p01", "--outdir", c.out, *c.dirs()[:4]])
        m = re.search(r"rms ([\d.]+) px, max ([\d.]+) px", out)
        need(m and float(m.group(1)) < 0.1, "path_test measured vs planned:\n" + out[-300:])
        msg += ("; " if msg else "") + f"path_test p01 {m.group(1)} px rms"
    return "PASS", msg


def _make_heics(d):
    """IMG_0001 front-camera (left half red), IMG_0002 + IMG_E0002 pair, IMG_0002.AAE sidecar."""
    import numpy as np
    import pillow_heif
    from PIL import Image
    pillow_heif.register_heif_opener()
    os.makedirs(d, exist_ok=True)

    def img(color_left, color_right, w=640, h=480):
        a = np.zeros((h, w, 3), np.uint8)
        a[:, :w // 2] = color_left
        a[:, w // 2:] = color_right
        return Image.fromarray(a)

    def exif(lens):
        ex = Image.Exif()
        ex[271], ex[272] = "Apple", "iPhone selftest"
        sub = ex.get_ifd(0x8769)
        sub[0xA434] = lens
        sub[0x9003] = "2026:10:03 12:00:00"
        return ex.tobytes()
    img((220, 30, 30), (30, 30, 220)).save(os.path.join(d, "IMG_0001.HEIC"), quality=90,
                                           exif=exif("iPhone 13 Pro front camera 2.71mm f/2.2"))
    img((30, 200, 30), (30, 200, 30), 480, 640).save(os.path.join(d, "IMG_0002.HEIC"), quality=90,
                                                     exif=exif("iPhone 13 Pro back camera 5.7mm f/1.5"))
    img((240, 240, 30), (240, 240, 30), 480, 640).save(os.path.join(d, "IMG_E0002.HEIC"), quality=90,
                                                       exif=exif("iPhone 13 Pro back camera 5.7mm f/1.5"))
    open(os.path.join(d, "IMG_0002.AAE"), "w").write("<plist>selftest</plist>")


def c_heic_convert(c):
    import numpy as np
    from PIL import Image
    src = os.path.join(c.work, "heic")
    _make_heics(src)
    dst = os.path.join(c.work, "photos")
    sh([PY, tool("heic_convert"), src, dst, "--jobs", "1"])
    a = np.asarray(Image.open(os.path.join(dst, "IMG_0001.jpg")).convert("RGB")).astype(int)
    need(a[:, :a.shape[1] // 4, 2].mean() > a[:, :a.shape[1] // 4, 0].mean(), "front-camera photo was not un-mirrored")
    b = np.asarray(Image.open(os.path.join(dst, "IMG_0002.jpg")).convert("RGB")).astype(int)
    need(b[..., 0].mean() > 150, "IMG_0002.jpg was not made from the edited IMG_E0002")
    meta = json.load(open(os.path.join(dst, "convert_meta.json"), encoding="utf-8"))
    need(set(meta) == {"IMG_0001", "IMG_0002"}, f"unexpected outputs {sorted(meta)}")
    sh([PY, tool("heic_convert"), src, os.path.join(c.work, "photos_orig"), "--prefer", "original", "--keep-mirror",
        "--jobs", "1"])
    o = np.asarray(Image.open(os.path.join(c.work, "photos_orig", "IMG_0002.jpg")).convert("RGB")).astype(int)
    need(o[..., 1].mean() > 150 and o[..., 0].mean() < 100, "--prefer original did not use IMG_0002")
    return "PASS", "edited version chosen, selfie un-mirrored, --prefer original / --keep-mirror ok"


def c_probe_media(c):
    hd = os.path.join(c.work, "heic")
    if not os.path.isdir(hd):
        _make_heics(hd)
    js = os.path.join(c.out, "probe_heic.json")
    sh([PY, tool("probe_media"), hd, "--json", js])
    r = json.load(open(js, encoding="utf-8"))
    need(r["totals"]["photos"] == 3 and r["totals"]["junk"] == 1, f"photo/junk counts {r['totals']}")
    need(r["totals"]["front_camera_photos"] == 1 and r["totals"]["edited_pairs"] == 1, f"pair/front flags {r['totals']}")
    msg = "HEIC: pair, front camera, .AAE junk detected"
    if c.has_video:
        js2 = os.path.join(c.out, "probe_media.json")
        sh([PY, tool("probe_media"), c.media, "--json", js2])
        r2 = json.load(open(js2, encoding="utf-8"))
        v = {x["file"]: x for x in r2["videos"]}
        need(v["clip_portrait.mov"]["orientation"] == "portrait" and v["clip_portrait.mov"]["rotation"] == -90,
             f"rotation tag not detected: {v['clip_portrait.mov']}")
        need(r2["totals"]["videos"] == 3 and not r2["junk"], f"video totals {r2['totals']} junk {r2['junk']}")
        msg += "; video: rotation tag -> portrait, no junk"
    return "PASS", msg


def c_contact_sheet(c):
    if not c.has_video:
        raise Skip("no video test media")
    out = os.path.join(c.out, "sheet.jpg")
    sh([PY, tool("contact_sheet"), os.path.join(c.media, "clip_portrait.mov"), "--count", "6", "--grid", "--out", out])
    from PIL import Image
    im = Image.open(out)
    need(im.height > im.width * 0.5, f"sheet size {im.size}")
    sh([PY, tool("contact_sheet"), c.media, "--fps", "0.5", "--out-dir", os.path.join(c.out, "sheets")])
    need(len(os.listdir(os.path.join(c.out, "sheets"))) == 3, "batch mode did not write 3 sheets")
    msg = f"single {im.size[0]}x{im.size[1]} + batch of 3"
    if c.preview_film:     # R13: film review sheets
        tlj = os.path.join(c.out, "tl_sheet.json")
        sh([PY, eng("render.py"), os.path.join(c.out, "short_edl.json"), "--timeline", "--timeline-json", tlj])
        pages = os.path.join(c.out, "film_sheet.jpg")
        o = sh([PY, tool("contact_sheet"), c.preview_film, "--timeline", tlj, "--fps", "8", "--per-page", "40",
                "--out", pages])
        need("pages)" in o and os.path.exists(os.path.join(c.out, "film_sheet_p01.jpg")), "no paginated film sheet:\n" + o)
        cuts = os.path.join(c.out, "film_cuts.jpg")
        o = sh([PY, tool("contact_sheet"), c.preview_film, "--timeline", tlj, "--cuts", "--out", cuts])
        need(os.path.exists(cuts) and "(24 frames)" in o, "cut-boundary sheet: " + o)
        at = os.path.join(c.out, "film_at.jpg")
        sh([PY, tool("contact_sheet"), c.preview_film, "--timeline", tlj, "--at", "1.0,5.5", "--out", at])
        need(os.path.exists(at), "no --at sheet")
        msg += f"; film: {o.split('(')[-1].strip(') ').strip()} at cuts (4 items), paginated --timeline, --at"
    return "PASS", msg


def c_reframe_preview(c):
    if not c.has_video:
        raise Skip("no video test media")
    res = []
    for iid in ("v05", "v09", "p01"):
        out = os.path.join(c.out, f"reframe_{iid}.jpg")
        txt = sh([PY, tool("reframe_preview"), eng("test/test_edl.json"), iid, "--n", "4", "--texts", "--out", out,
                  *c.dirs()])
        need(os.path.exists(out), f"{iid}: no output")
        if iid == "v09":
            need("zoom auto-raised" in txt, "tilt NOTE missing for v09")
        res.append(iid)
    # R14: straight from a picks file (no scratch EDL), with --write-back on a copy
    pk = _synthetic_picks(c)
    out = os.path.join(c.out, "reframe_pick_a4.jpg")
    txt = sh([PY, tool("reframe_preview"), "--picks", pk, "--id", "a4", "--n", "3", "--out", out, "--write-back",
              "--video-dir", c.media, "--photo-dir", c.media])
    need(os.path.exists(out), "--picks: no strip:\n" + txt[-300:])
    back = {p["id"]: p for p in json.load(open(pk, encoding="utf-8"))["picks"]}
    need(back["a4"].get("verify_strip", "").endswith("reframe_pick_a4.jpg"), "--write-back did not store verify_strip")
    sh([PY, tool("reframe_preview"), "--picks", pk, "--id", "a2", "--dur", "2.0", "--n", "2", "--no-source", "--out",
        os.path.join(c.out, "reframe_pick_a2.jpg"), "--video-dir", c.media, "--photo-dir", c.media])
    return "PASS", "box (v05), tilt (v09), photo (p01); --picks video + photo, --write-back"


def _synthetic_picks(c):
    """Two reviewer picks files on the synthetic media (sections a = 'location 1', b = 'location 2')."""
    for name in ("photo_a2.jpg", "photo_a5.jpg", "photo_b2.jpg"):      # distinct photo files (no SAME-SRC flag)
        if not os.path.exists(os.path.join(c.media, name)):
            shutil.copyfile(os.path.join(c.media, "test_photo.jpg"), os.path.join(c.media, name))
    pa = {"picks": [
        {"id": "a1", "type": "video", "src": "clip_land.mp4", "in": 1.0, "out": 4.0, "speed": 1, "highlight_t": 2.0,
         "dur_suggest": 2.4, "order": 1, "place": "gate", "intent": "moving pattern opening"},
        {"id": "a2", "type": "photo", "src": "photo_a2.jpg", "dur_suggest": 2.0, "order": 2, "place": "lawn",
         "frame": {"mode": "crop", "keys": [{"t": 0, "cx": 0.5, "cy": 0.45, "zoom": 1.0},
                                           {"t": 2.0, "cx": 0.5, "cy": 0.5, "zoom": 1.08}]}},
        {"id": "a3", "type": "video", "src": "clip_portrait.mov", "in": 2.0, "out": 3.0, "speed": 0.5,
         "highlight_t": 2.6, "dur_suggest": 2.0, "order": 3, "place": "pond"},
        {"id": "a4", "type": "video", "src": "clip_shaky.mp4", "in": 5.0, "out": 9.5, "speed": 1, "highlight_t": 8.8,
         "dur_suggest": 3.0, "order": 4, "place": "lake",
         "frame": {"mode": "crop", "keys": [{"t": 5.0, "cx": 0.4, "cy": 0.5, "zoom": 1.0},
                                           {"t": 9.5, "cx": 0.6, "cy": 0.5, "zoom": 1.05}]}},
        {"id": "a5", "type": "photo", "src": "photo_a5.jpg", "dur_suggest": 2.0, "order": 5, "place": "bench",
         "intent": "posed portrait"}]}
    pb = {"picks": [
        {"id": "b1", "type": "video", "src": "clip_land.mp4", "in": 8.0, "out": 12.0, "speed": 1, "dur_suggest": 3.0,
         "order": 1, "place": "tower"},
        {"id": "b2", "type": "photo", "src": "photo_b2.jpg", "dur_suggest": 2.4, "order": 2, "place": "museum"},
        {"id": "b3", "type": "video", "src": "clip_portrait.mov", "in": 4.5, "out": 7.5, "speed": 0.5,
         "dur_suggest": 4.0, "order": 3, "place": "deck"},
        {"id": "e1", "type": "photo", "src": "test_photo.jpg", "dur_suggest": 4.0, "order": 99, "role": "end_card_bg"}]}
    d = os.path.join(c.work, "picks")
    os.makedirs(d, exist_ok=True)
    for name, obj in (("picks_a.json", pa), ("picks_b.json", pb)):
        json.dump(obj, open(os.path.join(d, name), "w", encoding="utf-8"), indent=1)
    return os.path.join(d, "picks_a.json")


def _synthetic_plan(c, scene_change=12.0):
    """Music plan of the 100 BPM test bed (beat 0.6 s, bar 2.4 s) with a 'scene change'."""
    return {"beats": [round(0.6 * k, 3) for k in range(0, 60)], "downbeats": [round(2.4 * k, 3) for k in range(0, 15)],
            "join": {"scene_change": scene_change}, "final_accent": 26.4, "recommended_end": 28.8,
            "bar_length": 2.4, "render": {"file": os.path.join(c.media, "music_bed_test.wav")}}


def c_layout(c):
    """R3: auto layout - caps never exceeded (incl. transition overlaps), every cut on a beat (engine timeline),
    shortfall = error, local --drop keeps the other items byte-identical; regression on the real Kuzgi picks."""
    sys.path.insert(0, TOOLS_DIR)
    import edl_builder as eb
    from _picks import load_durations
    # 1) the real Kuzgi picks/plan in examples/ (no media needed): v2 settings -> no errors, every video in range
    kz = os.path.join(KIT_DIR, "examples", "kuzgi_sayr")
    spec = json.load(open(os.path.join(kz, "layout_kuzgi90.json"), encoding="utf-8"))
    spec["limits"] = {"g09": {"max": 1.5}, "g07": {"max": 5.55}}
    r = eb.auto_layout(spec, kz, durations=load_durations(os.path.join(kz, "probe.json")))
    need(not r["errors"] and not r["warnings"], f"kuzgi regression: {r['errors'] + r['warnings']}")
    for row in r["rows"]:
        if row["type"] == "video":
            need(row["lo"] - 1e-3 <= row["used_in"] and row["used_out"] <= row["hi"] + 1e-3, f"kuzgi {row['id']} overruns")
        need(row["D"] <= row["cap"] + 0.031, f"kuzgi {row['id']} {row['D']} > cap {row['cap']}")
    msg = f"kuzgi 27 items on-grid inside caps (g17 {[x['D'] for x in r['rows'] if x['id'] == 'g17'][0]:.2f} s, v2 had 6.02)"
    if not c.has_video:
        return "PASS", msg + "; synthetic film skipped (no video media)"
    # 2) synthetic film on the test media
    pk = _synthetic_picks(c)
    d = os.path.dirname(pk)
    plan = os.path.join(d, "plan.json")
    json.dump(_synthetic_plan(c), open(plan, "w"))
    lay = {"picks": ["picks_a.json", "picks_b.json"], "plan": "plan.json",
           "paths": {"video": os.path.relpath(c.media, d), "photo": os.path.relpath(c.media, d)},
           "output": {"path": "auto.mp4"}, "limits": {"a5": {"max": 1.5}},
           "sections": [{"name": "one", "prefix": "a", "start": 0, "end": "scene_change", "transition_out": ["dip_white", 0.6]},
                        {"name": "two", "prefix": "b", "start": "prev",
                         "end": {"ref": "final_accent", "offset": -1.8, "snap": "downbeat_before"},
                         "grid": {"period": 0.6, "from": "scene_change"}, "transition_out": ["crossfade", 0.6]},
                        {"name": "end", "ids": ["e1"], "start": "prev", "end": "recommended_end", "photo_cap": None}],
           "texts": [{"text": "Auto", "start": 0.3, "end": "a1.end-0.15", "style": "title"}]}
    sp = os.path.join(d, "layout.json")
    json.dump(lay, open(sp, "w"), indent=1)
    edl = os.path.join(c.out, "auto.json")
    out = sh([PY, tool("edl_builder"), "--layout", sp, "--out", edl])
    need("off-grid cuts: none" in out, "auto layout has off-grid cuts:\n" + out[-600:])
    tl = sh([PY, eng("render.py"), edl, "--timeline"])
    m = re.search(r"Cut points.*\n\s+([\d., ]+)", tl)
    need(m and "TOTAL 0:28.800" in tl, "engine timeline:\n" + tl[-600:])
    cuts = [float(x) for x in m.group(1).split(",")]
    need(all(abs(x / 0.6 - round(x / 0.6)) * 0.6 < 0.02 for x in cuts), f"engine cut points off the beat: {cuts}")
    e = json.load(open(edl, encoding="utf-8"))
    need(e["paths"].get("cache") == "cache", "build_edl did not write paths.cache")
    picks = {}
    for f in ("picks_a.json", "picks_b.json"):
        picks.update({p["id"]: p for p in json.load(open(os.path.join(d, f)))["picks"]})
    for it in e["items"]:
        p = picks[it["id"]]
        if it["type"] == "video":
            need(p["in"] - 1e-3 <= it["in"] and it["out"] <= p["out"] + 1e-3,
                 f"{it['id']}: EDL uses {it['in']}-{it['out']}, pick allows {p['in']}-{p['out']}")
    a4 = next(it for it in e["items"] if it["id"] == "a4")
    need(a4["in"] <= 8.8 <= a4["out"], f"a4 highlight 8.8 not inside {a4['in']}-{a4['out']}")
    a5 = next(it for it in e["items"] if it["id"] == "a5")
    need(a5["dur"] <= 1.5 + 0.6 / 2 + 0.031, f"a5 limit 1.5 s exceeded: {a5['dur']}")
    # 3) shortfall -> exit 2, nothing written
    json.dump(_synthetic_plan(c, scene_change=21.6), open(plan, "w"))
    short_edl = os.path.join(c.out, "short_material.json")
    o = sh([PY, tool("edl_builder"), "--layout", sp, "--out", short_edl], ok_codes=(2,))
    need("SHORT by" in o and not os.path.exists(short_edl), "shortfall not reported as an error:\n" + o[-400:])
    o = sh([PY, tool("edl_builder"), "--layout", sp, "--out", short_edl, "--stretch-photos"])
    need(os.path.exists(short_edl), "--stretch-photos did not write the EDL")
    json.dump(_synthetic_plan(c), open(plan, "w"))
    # 4) local drop: only a small window re-renders, the other EDL items stay identical (cache reuse)
    before = {it["id"]: it for it in e["items"]}
    o = sh([PY, tool("edl_builder"), "--layout", sp, "--out", edl, "--drop", "a3"])
    after = {it["id"]: it for it in json.load(open(edl, encoding="utf-8"))["items"]}
    same = [k for k in after if before.get(k) == after[k]]
    need("a3" not in after and len(same) >= len(after) - 3, f"--drop changed too much: same {same}\n{o[-300:]}")
    tl = sh([PY, eng("render.py"), edl, "--timeline"])
    need("TOTAL 0:28.800" in tl, "film length changed after --drop")
    return "PASS", msg + f"; synthetic 3-section film: caps/limits/highlight ok, beats ok, shortfall=exit 2, " \
                         f"--drop a3 kept {len(same)}/{len(after)} items identical"


def c_picks_check(c):
    """R9: budget + repetition flags."""
    pk = _synthetic_picks(c)
    d = os.path.dirname(pk)
    o = sh([PY, tool("picks_check"), pk, os.path.join(d, "picks_b.json"), "--bar", "2.4"])
    need("PASS (no flags)" in o, "clean picks flagged:\n" + o[-500:])
    bad = json.load(open(pk, encoding="utf-8"))
    bad["picks"].append({"id": "a6", "type": "video", "src": "clip_land.mp4", "in": 4.3, "out": 6.0,
                         "dur_suggest": 1.5, "order": 6, "place": "lake"})          # same take as a1, 3rd... lake twice
    bad["picks"].append({"id": "a7", "type": "photo", "src": "test_photo.jpg", "order": 4.5, "place": "lake",
                         "dur_suggest": 2.0})                                          # lake back to back with a4
    badp = os.path.join(d, "picks_bad.json")
    json.dump(bad, open(badp, "w"), indent=1)
    o = sh([PY, tool("picks_check"), badp, "--mode", "reels"], ok_codes=(1,))
    for flag in ("SAME-SRC a1/a6", "PLACE lake", "ADJACENT a4 -> a7"):
        need(flag in o, f"missing flag {flag}:\n{o[-600:]}")
    kz = os.path.join(KIT_DIR, "examples", "kuzgi_sayr")
    o = sh([PY, tool("picks_check"), os.path.join(kz, "picks_bog.json"), os.path.join(kz, "picks_minora.json")])
    need("g13 -> g04 both mention ['stork']" in o, "kuzgi stork pair not hinted:\n" + o[-400:])
    return "PASS", "clean set passes; same take / place count / back-to-back flagged (exit 1); kuzgi storks hinted"


def c_music_rubato(c):
    """R11: a rubato track is detected and cut on tracked bar lines; the click-locked bed stays 'steady'."""
    if not c.has_audio_media or not os.path.exists(os.path.join(c.media, "music_rubato_test.wav")):
        raise Skip("no rubato test media")
    js = os.path.join(c.out, "rubato.json")
    sh([PY, tool("music_beats"), os.path.join(c.media, "music_rubato_test.wav"), "--json", js], timeout=600)
    r = json.load(open(js, encoding="utf-8"))
    truth = json.load(open(os.path.join(c.media, "music_rubato_test.json")))["bar_starts"]
    need(r["tempo_mode"].startswith("rubato") and r.get("bar_starts"), f"not detected as rubato: {r.get('tempo_mode')}")
    err = sorted(min(abs(b - t) for b in r["bar_starts"]) for t in truth)
    good = sum(e < 0.06 for e in err)
    need(good >= 0.8 * len(truth), f"tracked bars: only {good}/{len(truth)} within 60 ms ({[round(e, 2) for e in err]})")
    steady = json.load(open(os.path.join(c.out, "beats.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(c.out, "beats.json")) else None
    if steady:
        need(steady["tempo_mode"].startswith("steady"), f"100 BPM bed called {steady['tempo_mode']}")
    # music_bed with the measured bar lines (bar_starts spec)
    spec = {"track": {"file": os.path.join(c.media, "music_rubato_test.wav")}, "bar_starts": r["bar_starts"],
            "phrase_bars": 4, "segments": [{"src_in": r["bar_starts"][1], "src_out": r["bar_starts"][9]}]}
    sp = os.path.join(c.out, "rubato_bed.json")
    json.dump(spec, open(sp, "w"))
    sh([PY, tool("music_bed"), sp, "--out", os.path.join(c.out, "rubato_bed.wav")])
    plan = json.load(open(os.path.join(c.out, "rubato_bed_plan.json"), encoding="utf-8"))
    need(len(plan["downbeats"]) == 8 and plan["downbeats"][0] == 0.0, f"bar_starts bed downbeats {plan['downbeats']}")
    return "PASS", (f"residual {r['analysis']['constant_grid_residual_ms']} ms -> rubato; {good}/{len(truth)} bars "
                    f"within 60 ms (median {1000 * err[len(err) // 2]:.0f} ms); bar_starts bed ok")


def c_music_catalog(c):
    """R15 (offline): seeded cache in the work folder, filters, scan -> candidates with attribution."""
    cat = [{"title": "Calm Koto", "filename": "Calm Koto.mp3", "length": "00:02:10", "instruments": "Koto, Flute",
            "genre": "25", "bpm": "80", "description": "gentle", "feel": "Calming, Relaxed", "isrc": "X1"},
           {"title": "Sung Song", "filename": "Sung Song.mp3", "length": "00:03:00", "instruments": "Vocals, Piano",
            "genre": "16", "bpm": "100", "description": "", "feel": "Calming", "isrc": "X2"},
           {"title": "Fast Rock", "filename": "Fast Rock.mp3", "length": "00:00:40", "instruments": "Guitar",
            "genre": "19", "bpm": "160", "description": "", "feel": "Driving", "isrc": "X3"}]
    cj = os.path.join(c.out, "pieces.json")
    json.dump(cat, open(cj, "w"))
    env = {"VT_MUSIC_CACHE": os.path.join(c.work, "music_cache")}
    sh([PY, tool("music_catalog"), "fetch", "--from-file", cj], env_extra=env)
    o = sh([PY, tool("music_catalog"), "search", "--feel", "calm", "--no-vocals", "--min-len", "60", "--bpm", "70-110"],
           env_extra=env)
    need("Calm Koto" in o and "Sung Song" not in o and "Fast Rock" not in o, "search filters:\n" + o)
    if not c.has_audio_media:
        return "PASS", "fetch --from-file + search filters (scan skipped)"
    js = os.path.join(c.out, "candidates.json")
    sh([PY, tool("music_catalog"), "scan", os.path.join(c.media, "music_bed_test.wav"), "--json", js],
       env_extra=env, timeout=600)
    r = json.load(open(js, encoding="utf-8"))["candidates"][0]
    need(abs(r["tempo_est"] - 100) < 3 and r["lufs"] is not None and r["energy_8s_db"], f"scan {r}")
    return "PASS", f"cache in work folder, filters ok (vocals/BPM/length), scan {r['tempo_est']} BPM {r['lufs']} LUFS {r['key']}"


def c_music_beats(c):
    if not c.has_audio_media:
        raise Skip("no music test media")
    js = os.path.join(c.out, "beats.json")
    sh([PY, tool("music_beats"), os.path.join(c.media, "music_bed_test.wav"), "--json", js, "--suggest-jumps", "2"],
       timeout=600)
    r = json.load(open(js, encoding="utf-8"))
    need(abs(r["bpm"] - 100) < 0.5, f"BPM {r['bpm']} (expected 100)")
    ph = min(r["beats"][0] % 0.6, 0.6 - r["beats"][0] % 0.6)
    need(ph < 0.02, f"beat phase off by {ph * 1000:.0f} ms")
    for k in ("beats", "downbeats", "phrase_starts", "sections", "final_accent", "recommended_end", "energy"):
        need(k in r, f"missing field {k}")
    need(len(r.get("jump_suggestions", [])) == 2, "no jump suggestions")
    return "PASS", f"{r['bpm']} BPM, phase error {ph * 1000:.0f} ms, {len(r['downbeats'])} bars"


def c_music_bed(c):
    if not c.has_audio_media:
        raise Skip("no music test media")
    spec = {"name": "selftest bed", "track": {"file": os.path.join(c.media, "music_bed_test.wav")},
            "beat0": 0.0, "period": 0.6, "segments": [
                {"src_in": 0.0, "src_out": 4.8, "fade_in": 0.1},
                {"src_in": 9.6, "src_out": 14.4},
                {"src_in": 19.2, "src_out": 24.0, "fade_out": 0.5}],
            "sections": [{"name": "all", "start": 0, "end": None, "energy": "mid"}]}
    sp = os.path.join(c.out, "bed_spec.json")
    json.dump(spec, open(sp, "w"))
    wav = os.path.join(c.out, "bed.wav")
    sh([PY, tool("music_bed"), sp, "--out", wav])
    plan = json.load(open(os.path.join(c.out, "bed_plan.json"), encoding="utf-8"))
    import wave
    with wave.open(wav) as w:
        n, sr, ch, sw = w.getnframes(), w.getframerate(), w.getnchannels(), w.getsampwidth()
    need((sr, ch, sw) == (48000, 2, 3) and abs(n - 14.4 * 48000) <= 1, f"WAV {n} frames {sr} Hz {ch} ch {sw * 8} bit")
    need(len(plan["beats"]) == 24 and plan["downbeats"][:3] == [0.0, 2.4, 4.8], f"plan beats {plan['beats'][:6]}")
    need(plan["render"]["true_peak_dbtp"] <= -0.95, f"true peak {plan['render']['true_peak_dbtp']}")
    # R10: two parts joined at a scene change (part 2 enters on its bar-9 downbeat at 9.6 s) + end-anchored --length
    p1 = {"track": {"file": os.path.join(c.media, "music_bed_test.wav")}, "beat0": 0.0, "period": 0.6,
          "segments": [{"src_in": 0.0, "src_out": 10.2, "fade_out": 0.6}]}
    p2 = {"track": {"file": os.path.join(c.media, "music_bed_test.wav")}, "beat0": 0.0, "period": 0.6,
          "segments": [{"src_in": 19.2, "src_out": 40.8, "fade_out": 0.5}], "final_accent_src": 38.4}
    multi = {"name": "selftest two-part", "parts": [{"spec": p1}, {"spec": p2, "scene_change": 9.6}]}
    mp = os.path.join(c.out, "multi_bed.json")
    json.dump(multi, open(mp, "w"))
    sh([PY, tool("music_bed"), mp, "--out", os.path.join(c.out, "multi.wav")])
    mpl = json.load(open(os.path.join(c.out, "multi_plan.json"), encoding="utf-8"))
    need(abs(mpl["total_duration"] - 31.2) < 0.01 and mpl["join"]["scene_change"] == 9.6 and 9.6 in mpl["downbeats"],
         f"multi-part plan: total {mpl['total_duration']}, join {mpl['join']}")
    need(abs(mpl["final_accent"] - 28.8) < 0.01 and len(mpl["tracks"]) == 2, f"final accent {mpl['final_accent']}")
    gaps = [b - a for a, b in zip(mpl["beats"], mpl["beats"][1:])]
    need(max(gaps) < 0.61 and min(gaps) > 0.59, f"beat grid broken at the join: {sorted(set(round(g, 3) for g in gaps))}")
    o = sh([PY, tool("music_bed"), mp, "--out", os.path.join(c.out, "multi20.wav"), "--length", "22"])
    l20 = json.load(open(os.path.join(c.out, "multi20_plan.json"), encoding="utf-8"))
    need(abs(l20["total_duration"] - 21.6) < 0.01 and "chosen: bar" in o, f"--length 22 -> {l20['total_duration']}")
    return "PASS", (f"14.4 s 24-bit bed, 24 beats, TP {plan['render']['true_peak_dbtp']} dBTP; two-part bed 31.2 s "
                    f"(join 9.6, continuous beats); --length 22 -> 21.6 s")


def c_edl_builder(c):
    if not c.has_video:
        raise Skip("no video test media")
    edl = os.path.join(c.out, "example_edl.json")
    out = sh([PY, tool("edl_builder"), "--example", edl, "--media", c.media])
    need("off-beat: none" in out, "example has off-beat cuts:\n" + out[-300:])
    tl = sh([PY, eng("render.py"), edl, "--timeline"])
    need("2.400, 4.800, 6.000, 9.600, 12.000, 15.600" in tl and "TOTAL 0:18.600" in tl,
         "engine timeline does not match the beat grid:\n" + tl[-500:])
    sys.path.insert(0, TOOLS_DIR)
    import edl_builder as eb
    sm = eb.fit_speed_map([(4.0, 4.6, 0.5), (4.6, 6.0, 1.0)], 3.0)
    need(abs(sum((q["out"] - q["in"]) / q["speed"] for q in sm) - 3.0) < 1e-3, f"fit_speed_map {sm}")
    return "PASS", "example EDL cuts land on the 0.6 s beat grid (engine --timeline), 18.6 s"


def c_proxies(c):
    if not c.has_video:
        raise Skip("no video test media")
    if c.quick:
        raise Skip("--quick")
    pd = os.path.join(c.work, "proxy")
    out = sh([PY, tool("make_proxies"), c.media, pd, "--only", "clip_portrait"], timeout=900)
    need("1080x1920 rot 0" in out, "proxy not upright 1080x1920:\n" + out[-300:])
    return "PASS", "rotation-tagged clip -> upright 1080x1920 proxy"


def c_export(c):
    if not c.preview_film:
        raise Skip("no preview film" if not c.quick else "--quick")
    out = os.path.join(c.out, "export_small20.mp4")
    js = os.path.join(c.out, "export.json")
    args = [PY, tool("export"), c.preview_film, "--preset", "small20", "--target-mb", "1", "--t", "5",
            "--out", out, "--json", js]
    if c.has_vmaf:
        args += ["--vmaf", "--vmaf-subsample", "10"]
    sh(args, timeout=1200)
    r = json.load(open(js, encoding="utf-8"))
    need(r["size_ok"] and r["resolution"] == "720x1280", f"export report {r}")
    need("keyint=60" in r.get("x264_options", "") and "aq=3:0.80" in r.get("x264_options", ""),
         "x264 settings not as preset")
    st = os.popen(f'"{FFPROBE}" -v error -show_entries stream=color_primaries,color_transfer -of csv=p=0 "{out}"').read()
    need("bt709" in st, f"colour tags {st}")
    v = r.get("vmaf")
    if v:
        need(v["mean"] > 60, f"VMAF {v['mean']}")
    return "PASS", f"{r['mib']} MiB 720x1280" + (f", VMAF {v['mean']}" if v else ", VMAF skipped (no libvmaf)")


CHECKS = [
    ("env", c_env, False), ("help", c_help, False), ("media", c_media, False),
    ("timeline", c_timeline, False), ("render_preview", c_render_preview, True),
    ("final_check", c_final_check, True), ("measure_motion", c_measure_motion, True),
    ("smooth_path", c_path_smooth, False), ("heic_convert", c_heic_convert, False),
    ("probe_media", c_probe_media, False), ("contact_sheet", c_contact_sheet, False),
    ("reframe_preview", c_reframe_preview, False), ("music_beats", c_music_beats, False),
    ("music_bed", c_music_bed, False), ("edl_builder", c_edl_builder, False),
    ("layout", c_layout, False), ("picks_check", c_picks_check, False), ("designed_pan", c_designed_pan, False),
    ("music_rubato", c_music_rubato, False), ("music_catalog", c_music_catalog, False),
    ("proxies", c_proxies, True), ("export", c_export, True),
]
DEPENDS = {"final_check": ["media", "render_preview"], "measure_motion": ["media", "render_preview"],
           "export": ["env", "media", "render_preview"], "render_preview": ["media"], "timeline": ["media"],
           "smooth_path": ["media"], "contact_sheet": ["media"], "reframe_preview": ["media"],
           "music_beats": ["media"], "music_bed": ["media"], "edl_builder": ["media"], "proxies": ["media"],
           "layout": ["media"], "picks_check": ["media"], "designed_pan": ["media"],
           "music_rubato": ["media", "music_beats"], "music_catalog": ["media"]}


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="skip the slow checks (preview render, export, proxies)")
    ap.add_argument("--keep", action="store_true", help="keep the work folder")
    ap.add_argument("--only", help="comma list of checks: " + ",".join(n for n, _, _ in CHECKS))
    ap.add_argument("--list", action="store_true", help="list the checks and exit")
    ap.add_argument("--min-free-gb", type=float, default=HEAVY_MIN_GB,
                    help=f"skip the heavy checks below this much free disk (default {HEAVY_MIN_GB})")
    a = ap.parse_args()
    if a.list:
        for n, f, h in CHECKS:
            print(f"{n:<16}{'heavy' if h else ''}")
        return 0
    sel = None
    if a.only:
        sel = set(s.strip() for s in a.only.split(","))
        unknown = sel - {n for n, _, _ in CHECKS}
        if unknown:
            sys.exit(f"unknown checks {sorted(unknown)}")
        for s in list(sel):
            sel.update(DEPENDS.get(s, []))
        sel.add("env")
    test_root = os.path.join(KIT_DIR, "_test")
    existed = os.path.isdir(test_root)
    work = os.path.join(test_root, "selftest_" + time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(work, exist_ok=True)
    gb = free_gb(work)
    heavy = gb >= a.min_free_gb
    print(f"kit {KIT_DIR}\nwork {work}\nfree disk {gb:.2f} GB" +
          ("" if heavy else f"  -> WARN: < {a.min_free_gb:g} GB, heavy checks skipped"), flush=True)
    c = Ctx(work, heavy, a.quick)
    results = []
    t_all = time.time()
    try:
        for name, fn, is_heavy in CHECKS:
            if sel is not None and name not in sel:
                continue
            t0 = time.time()
            try:
                if is_heavy and not heavy:
                    raise Skip(f"< {a.min_free_gb:g} GB free disk")
                st, msg = fn(c)
            except Skip as e:
                st, msg = ("WARN" if "disk" in str(e) else "SKIP"), str(e)
            except Fail as e:
                st, msg = "FAIL", str(e)
            except Exception as e:  # a bug in the check itself counts as a failure
                st, msg = "FAIL", f"{e.__class__.__name__}: {e}"
            dt = time.time() - t0
            results.append((name, st, dt, msg))
            first, *rest = msg.splitlines() or [""]
            print(f"{st:<5} {name:<16}{dt:7.1f}s  {first}", flush=True)
            for line in rest[:14]:
                print(f"{'':<30}{line}")
    finally:
        if not a.keep:
            shutil.rmtree(work, ignore_errors=True)
            try:
                if not existed or not os.listdir(test_root):
                    os.rmdir(test_root)
            except OSError:
                pass
    nf = sum(1 for r in results if r[1] == "FAIL")
    nw = sum(1 for r in results if r[1] == "WARN")
    ns = sum(1 for r in results if r[1] == "SKIP")
    print(f"\n{'FAIL' if nf else 'PASS'}: {len(results) - nf - nw - ns} passed, {nf} failed, {nw} warnings, {ns} skipped "
          f"in {time.time() - t_all:.0f} s" + (f"  (kept {work})" if a.keep else "  (work folder deleted)"))
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())

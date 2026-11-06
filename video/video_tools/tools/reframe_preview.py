"""What will the 9:16 viewer see?  Strip of an EDL item's framing at N moments, rendered with the
engine's own geometry (framing.Plan: keys, eases, key projection, tilt, rotate/hflip, box/fit
composite) - plus the source frames with the window drawn in, so frame keys can be checked
before a render.

  python tools/reframe_preview.py EDL.json s02                  6 moments -> reframe_s02.jpg
  python tools/reframe_preview.py EDL.json s02 --n 10 --texts   10 moments, EDL texts burned in
  python tools/reframe_preview.py EDL.json s02 --at 0,0.5,1.2   seconds from the item's start
  python tools/reframe_preview.py EDL.json p01 --video-dir D:/footage --photo-dir D:/photos
Straight from a reviewer's picks file (no scratch EDL needed):
  python tools/reframe_preview.py --picks picks_bog.json --id g06 --video-dir D:/raw --photo-dir photos
  python tools/reframe_preview.py --picks picks_bog.json --id g06 --dur 3.2 --write-back --video-dir D:/raw
    builds the one-item EDL internally (dur = --dur, else dur_suggest; video placed like edl_builder --layout:
    from `in`, highlight inside, never past `out`), --write-back stores the strip path as the pick's
    "verify_strip" in the picks file.

Panels: magenta lines = Reels safe zone (top 14 %, bottom 22 %), label = film time / source time.
Source row: red = the window (output frame) in the upright source; yellow = blurred-fill window
(box/fit).  Engine NOTEs (keys moved into the valid region, tilt zoom, edge push) are printed.
Not simulated: stabilisation (adds a small extra zoom), the colour grade.
"""
import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import font, safe_console, use_engine  # noqa: E402

use_engine()
import edl as edlmod  # noqa: E402
import framing  # noqa: E402
from common import FFMPEG, YUV2RGB, probe, rotation_filters  # noqa: E402
from itemrender import _BoxCompositor, _load_photo, output_times  # noqa: E402


def source_frame(src, t, total_cw, hflip):
    info = probe(src)
    W, H = (info["h"], info["w"]) if total_cw in (90, 270) else (info["w"], info["h"])
    vf = ",".join(rotation_filters(total_cw, hflip) + [f"scale={YUV2RGB}", "format=rgb24"])
    t = min(max(0.0, t), max(0.0, info["duration"] - 0.04))
    p = subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-noautorotate", "-ss", f"{t:.4f}", "-i", src,
                        "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-"], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if len(p.stdout) < W * H * 3:
        raise RuntimeError(f"could not decode {src} at {t:.3f}s: {p.stderr.decode('utf-8', 'replace')[-300:]}")
    return np.frombuffer(p.stdout[:W * H * 3], np.uint8).reshape(H, W, 3)


def edl_from_pick(picks_path, pid, dur, out_dir, video_dir=None, photo_dir=None):
    """One-item EDL (written to out_dir) for pick `pid`.  Returns (edl path, D seconds)."""
    import json
    from _picks import dur_want, is_photo, load_picks, pick_cap, place_video
    import edl_builder as eb
    picks, _ = load_picks([picks_path])
    if pid not in picks:
        sys.exit(f"pick {pid!r} not in {picks_path} (have {', '.join(picks)})")
    p = picks[pid]
    cap = pick_cap(p, photo_cap=None, video_max=None)
    D = float(dur) if dur else dur_want(p, cap)
    if is_photo(p):
        spec = dict(src=p["src"], type="photo", frame_id=pid)
        for k in ("rotate", "hflip", "tilt_deg"):
            if p.get(k):
                spec[k] = p[k]
    else:
        if D > cap + 0.03:
            print(f"NOTE {pid}: {D:.2f} s is longer than the pick's usable {cap:.2f} s -> clamped")
            D = cap
        spec = dict(src=p["src"], type="video", speed=p["speed"], rotate=p["rotate"], hflip=p["hflip"], frame_id=pid)
        if p.get("speed_map"):
            spec["speed_map"] = p["speed_map"]
        else:
            spec["a"] = place_video(p, D)[0]
        for k in ("tilt_deg", "stabilize", "frame_extra", "mirror_keys"):
            if p.get(k) not in (None, False):
                spec[k] = p[k]
    base = os.path.dirname(os.path.abspath(picks_path))
    item = eb.build_item(pid, D, spec, 0.0, frames=picks)
    edl = {"title": f"reframe check {pid}", "output": {"w": 1080, "h": 1920, "fps": 30},
           "paths": {"video": os.path.abspath(video_dir or base), "photo": os.path.abspath(photo_dir or base)},
           "items": [item], "transitions": [], "texts": []}
    path = os.path.join(out_dir, f"_reframe_{pid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(edl, f, ensure_ascii=False, indent=1)
    return path, D


def write_back(picks_path, pid, strip):
    import json
    d = json.load(open(picks_path, encoding="utf-8"))
    lst = d.get("picks", []) if isinstance(d, dict) else d
    rel = os.path.relpath(os.path.abspath(strip), os.path.dirname(os.path.abspath(picks_path))).replace("\\", "/")
    for p in lst:
        if p.get("id") == pid:
            p["verify_strip"] = rel
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(f"{picks_path}: {pid}.verify_strip = {rel}")


def main():
    import tempfile
    tmp = tempfile.TemporaryDirectory(prefix="vt_reframe_")
    try:
        return _main(tmp.name)
    finally:
        tmp.cleanup()


def _main(tmpdir):
    safe_console()
    import cv2
    from PIL import Image, ImageDraw
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl", nargs="?", help="EDL JSON (or use --picks/--id)")
    ap.add_argument("item", nargs="?", help="item id in the EDL")
    ap.add_argument("--picks", help="reviewer picks JSON: preview one pick without writing an EDL")
    ap.add_argument("--id", help="pick id (with --picks)")
    ap.add_argument("--dur", type=float, help="with --picks: on-screen seconds (default the pick's dur_suggest)")
    ap.add_argument("--write-back", action="store_true", help="with --picks: store the strip as the pick's verify_strip")
    ap.add_argument("--n", type=int, default=6, help="number of evenly spaced moments (default 6)")
    ap.add_argument("--at", help="comma list of seconds from the item's start (overrides --n)")
    ap.add_argument("--width", type=int, default=270, help="panel width px (default 270)")
    ap.add_argument("--texts", action="store_true", help="burn in the EDL texts active at those moments")
    ap.add_argument("--no-source", action="store_true", help="panels only, no source row")
    ap.add_argument("--out", help="output JPG (default reframe_<item>.jpg in the CWD)")
    for k in ("video", "photo", "proxy", "music"):
        ap.add_argument(f"--{k}-dir", help=f"override the EDL's paths.{k}")
    a = ap.parse_args()
    if a.picks:
        if not a.id:
            ap.error("--picks needs --id")
        a.edl, D = edl_from_pick(a.picks, a.id, a.dur, tmpdir, a.video_dir, a.photo_dir)
        a.item = a.id
        print(f"{a.id}: one-item EDL from {os.path.basename(a.picks)}, {D:.2f} s on screen")
    elif not (a.edl and a.item):
        ap.error("give EDL + item, or --picks + --id")

    try:
        e = edlmod.load(a.edl, path_overrides={k: getattr(a, f"{k}_dir") for k in ("video", "photo", "proxy", "music")})
    except edlmod.EDLError as ex:
        sys.exit(f"EDL ERROR: {ex}" + ("  (pass --video-dir / --photo-dir)" if a.picks else ""))
    try:
        idx = [it["id"] for it in e["items"]].index(a.item)
    except ValueError:
        sys.exit(f"item {a.item!r} not in the EDL (have {', '.join(it['id'] for it in e['items'])})")
    it, row = e["items"][idx], e["timeline"]["rows"][idx]
    fps, n = e["output"]["fps"], row["n"]
    OW = a.width
    OH = int(round(OW * e["output"]["h"] / e["output"]["w"]))
    if it["type"] == "video":
        info = probe(it["_src"])
        total = (info["auto_cw"] + it.get("rotate", 0)) % 360
        W, H = (info["h"], info["w"]) if total in (90, 270) else (info["w"], info["h"])
        times = output_times({"speed_map": it.get("speed_map"), "in": it["in"], "out": it["out"], "fps": fps,
                              "n": n, "speed": it["speed"], "id": it["id"]})
        photo = None
    else:
        photo, note = _load_photo(it["_src"], it.get("rotate", 0), it.get("hflip", False))
        H, W = photo.shape[:2]
        times = np.arange(n) / fps
    plan = framing.Plan(W, H, OW, OH, it["frame"], n, times=times, tilt_deg=it.get("tilt_deg", 0.0), fps=fps)
    for w in plan.warnings:
        print(f"NOTE {it['id']}: {w}")
    if it.get("stabilize"):
        print(f"NOTE {it['id']}: stabilisation is not simulated (the render adds a small extra zoom)")
    if a.at:
        ks = [min(n - 1, max(0, int(round(float(s) * fps)))) for s in a.at.split(",")]
    else:
        m = max(1, a.n)
        ks = sorted({int(round(i * (n - 1) / max(1, m - 1))) for i in range(m)})
    tr = None
    if a.texts and e["texts"]:
        from textfx import TextRenderer
        tr = TextRenderer(e["texts"], OW, OH, fps)
    comp = None
    panels, sources = [], []
    fsm, fbig = font(max(10, OW // 22)), font(16)
    x, y, w, h = plan.crop
    for k in ks:
        arr = photo if photo is not None else source_frame(it["_src"], float(times[k]), total, it.get("hflip", False))
        pre = cv2.resize(arr[y:y + h, x:x + w], (plan.PW, plan.PH), interpolation=cv2.INTER_AREA)
        sig = plan.blur_sigma(k)
        src_for_warp = cv2.GaussianBlur(pre, (0, 0), sig) if sig > 0 else pre
        out = cv2.warpAffine(src_for_warp, plan.cv_mats[k], plan.region_size,
                             flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        if plan.mode != "crop":
            comp = comp or _BoxCompositor(plan, cv2, it["frame"])
            out = comp.compose(pre, out, k)
        out = np.ascontiguousarray(out)
        if tr is not None:
            tr.apply(out, row["start_f"] + k)
        P = Image.fromarray(out)
        d = ImageDraw.Draw(P)
        for yy in (0.14 * OH, 0.78 * OH):
            d.line([(0, yy), (OW, yy)], fill=(255, 0, 255), width=1)
        lab = f"{(row['start_f'] + k) / fps:.2f}s | src {times[k]:.2f}" if photo is None else \
              f"{(row['start_f'] + k) / fps:.2f}s | +{k / fps:.2f}"
        d.rectangle([0, 0, OW, fsm.size + 8], fill=(0, 0, 0))
        d.text((4, 3), lab, fill=(255, 230, 0), font=fsm)
        panels.append(P)
        if not a.no_source:
            fw = 320 if W >= H else 200
            sc = fw / W
            S = Image.fromarray(arr).resize((fw, max(1, round(H * sc))), Image.BILINEAR)
            ds = ImageDraw.Draw(S)
            C = plan.lay.corners()
            Q = (plan.mats[k] @ C)[:2] * sc
            ds.polygon([(Q[0, 0], Q[1, 0]), (Q[0, 1], Q[1, 1]), (Q[0, 3], Q[1, 3]), (Q[0, 2], Q[1, 2])],
                       outline=(255, 40, 40), width=2)
            if plan.bg is not None:
                bx, by = plan.bg["centres"][k]
                bw2, bh2 = plan.bg["w"] / 2, plan.bg["h"] / 2
                ds.rectangle([(bx - bw2) * sc, (by - bh2) * sc, (bx + bw2) * sc, (by + bh2) * sc], outline=(255, 220, 0))
            ds.text((4, 3), f"t={times[k]:.2f}" if photo is None else f"+{k / fps:.2f}s", fill=(255, 255, 0), font=fsm)
            sources.append(S)
    gap, head = 4, 26
    strip_w = len(panels) * (OW + gap) - gap
    src_h = 0
    if sources:
        sw = sources[0].width
        cols = max(1, (strip_w + gap) // (sw + gap))
        rows = (len(sources) + cols - 1) // cols
        src_h = rows * (sources[0].height + gap) + 6
        strip_w = max(strip_w, min(len(sources), cols) * (sw + gap) - gap)
    sheet = Image.new("RGB", (strip_w, head + OH + src_h), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    flags = [it["frame"]["mode"]] + ([f"rotate {it['rotate']}"] if it.get("rotate") else []) + \
            (["hflip"] if it.get("hflip") else []) + ([f"tilt {it['tilt_deg']:+g}"] if it.get("tilt_deg") else []) + \
            ([f"{len(it['frame']['keys'])} keys"] if it["frame"].get("keys") else []) + \
            (["NOTE: " + "; ".join(plan.warnings)] if plan.warnings else [])
    d.text((6, 5), f"{it['id']}  {os.path.basename(it['_src'])}  film {row['start']:.2f}-{row['end']:.2f}s  "
                   + "  ".join(flags), fill=(255, 255, 255), font=fbig)
    for i, P in enumerate(panels):
        sheet.paste(P, (i * (OW + gap), head))
    if sources:
        sw, sh = sources[0].width, sources[0].height
        for i, S in enumerate(sources):
            sheet.paste(S, ((i % cols) * (sw + gap), head + OH + 6 + (i // cols) * (sh + gap)))
    out = a.out or f"reframe_{it['id']}.jpg"
    sheet.save(out, quality=88)
    print(out)
    if a.picks and a.write_back:
        write_back(a.picks, a.id, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

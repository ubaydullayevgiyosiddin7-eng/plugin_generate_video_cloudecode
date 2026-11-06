"""Labelled frame grid (contact sheet) of a clip or a finished film, for reviewing footage (in/out points,
frame keys) and for checking a film (critic, final QC, the manager's overview).  Frames are upright
(autorotated), timestamps (source / film seconds) burned in.

  python tools/contact_sheet.py clip.MOV                       2 frames/s -> clip_sheet.jpg next to the CWD
  python tools/contact_sheet.py clip.MOV --fps 4 --start 2 --end 6 --grid
  python tools/contact_sheet.py clip.MOV --count 12             12 evenly spaced frames
  python tools/contact_sheet.py D:/footage --out-dir sheets     batch: one sheet per video in the folder
Film review (tl.json from: python engine/render.py film.json --timeline --timeline-json tl.json):
  python tools/contact_sheet.py film.mp4 --timeline tl.json --fps 2      every 0.5 s, labels "12.40s g18",
                                                                         multi-page (film_sheet_p01.jpg ...)
  python tools/contact_sheet.py film.mp4 --timeline tl.json --cuts       first + last 0.1 s of EVERY item, one
                                                                         row per item (whip blur / empty tails at
                                                                         shot boundaries that a 2.5 s sheet misses)
  python tools/contact_sheet.py film.mp4 --at 9.45,9.6,13.2 --timeline tl.json   big frames at these moments

--grid draws normalised 0.1 ticks (the cx/cy coordinates used by EDL frame keys); --nine16 outlines
the largest centred 9:16 window (what a zoom-1.0 crop would show).  Without --timeline / --paginate a
sheet holds at most --max-frames (fps is lowered to fit); with them, sheets are split into pages of
--per-page frames at the fixed fps.
"""
import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import CREATE_FLAGS, FFMPEG, VIDEO_EXT, font, fmt_t, run, safe_console, video_info  # noqa: E402

YUV2RGB = "in_color_matrix=bt709:in_range=tv:out_range=pc"


def grab(path, times, tw, th, info):
    """Frames at the given source times, tw x th RGB, decoded with one ffmpeg per frame (seek)."""
    out = []
    for t in times:
        t = min(max(0.0, t), max(0.0, info["duration"] - 0.05))
        p = run([FFMPEG, "-nostdin", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                 "-vf", f"scale={tw}:{th}:flags=area:{YUV2RGB},format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                check=False)
        n = tw * th * 3
        out.append(np.frombuffer(p.stdout[:n], np.uint8).reshape(th, tw, 3) if len(p.stdout) >= n
                   else np.zeros((th, tw, 3), np.uint8))
    return out


def stream(path, start, end, fps, tw, th):
    """Decode a time range once at `fps` (cheaper than seeking for dense sampling)."""
    vf = f"fps={fps}:start_time={start:.3f}:round=near,scale={tw}:{th}:flags=area:{YUV2RGB},format=rgb24"
    p = run([FFMPEG, "-nostdin", "-v", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-copyts", "-i", path,
             "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=False)
    n = tw * th * 3
    k = len(p.stdout) // n
    frames = [np.frombuffer(p.stdout[i * n:(i + 1) * n], np.uint8).reshape(th, tw, 3) for i in range(k)]
    return frames, [start + i / fps for i in range(k)]


def frames_by_index(path, wanted, tw, th):
    """One decoding pass over the whole file; keep only the frame numbers in `wanted` (exact frames,
    no seeking) -> {index: RGB array}.  Memory = only the kept thumbnails."""
    wanted = set(int(i) for i in wanted)
    if not wanted:
        return {}
    last = max(wanted)
    cmd = [FFMPEG, "-nostdin", "-v", "error", "-i", path, "-frames:v", str(last + 1),
           "-vf", f"scale={tw}:{th}:flags=area:{YUV2RGB},format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                         creationflags=CREATE_FLAGS)
    n = tw * th * 3
    out, i = {}, 0
    try:
        while i <= last:
            b = p.stdout.read(n)
            if len(b) < n:
                break
            if i in wanted:
                out[i] = np.frombuffer(b, np.uint8).reshape(th, tw, 3).copy()
            i += 1
    finally:
        p.stdout.close()
        p.kill()
        p.wait()
    return out


def load_timeline(path):
    """render.py --timeline-json -> items with the cut-centre span [c0, c1) (where each item is the main picture)."""
    tl = json.load(open(path, encoding="utf-8"))
    items = []
    for r in tl["items"]:
        items.append(dict(r, c0=r["start"] + r["overlap_in"] / 2, c1=r["end"] - r["overlap_out"] / 2))
    return tl, items


def item_at(items, t):
    for r in items:
        if r["c0"] - 1e-6 <= t < r["c1"] - 1e-6:
            return r["id"]
    return items[-1]["id"] if items and t >= items[-1]["c0"] else ""


def draw_grid(d, x0, y0, w, h, f):
    for i in range(1, 10):
        c = (255, 230, 0) if i == 5 else (0, 230, 255)
        x, y = x0 + w * i / 10, y0 + h * i / 10
        d.line([(x, y0), (x, y0 + 7)], fill=c, width=2)
        d.line([(x, y0 + h - 7), (x, y0 + h)], fill=c, width=2)
        d.line([(x0, y), (x0 + 7, y)], fill=c, width=2)
        d.line([(x0 + w - 7, y), (x0 + w, y)], fill=c, width=2)
        if i % 2 == 0 or i == 5:
            d.text((x + 2, y0 + 8), f".{i}", fill=c, font=f)
            d.text((x0 + 9, y - 7), f".{i}", fill=c, font=f)


def _label(d, x, y, tw, th, text, fs, color=(255, 90, 90)):
    bx = d.textbbox((0, 0), text, font=fs)
    d.rectangle([x, y + th - (bx[3] - bx[1]) - 8, x + bx[2] - bx[0] + 8, y + th], fill=(0, 0, 0))
    d.text((x + 4, y + th - (bx[3] - bx[1]) - 6), text, fill=color, font=fs)


def compose(frames, labels, tw, th, title, cols, args, info):
    from PIL import Image, ImageDraw
    rows = int(math.ceil(len(frames) / cols))
    head, gap = 34, 4
    S = Image.new("RGB", (cols * tw + (cols - 1) * gap, head + rows * (th + gap)), (24, 24, 24))
    d = ImageDraw.Draw(S)
    fb, fs = font(18), font(max(11, tw // 22))
    d.text((8, 7), title, fill=(255, 255, 255), font=fb)
    W, H = info["upright_w"], info["upright_h"]
    for i, (fr, lab) in enumerate(zip(frames, labels)):
        x, y = (i % cols) * (tw + gap), head + (i // cols) * (th + gap)
        S.paste(Image.fromarray(fr), (x, y))
        if args.grid:
            draw_grid(d, x, y, tw, th, fs)
        if args.nine16 and W / H > 9 / 16:
            ww = th * 9 / 16
            d.rectangle([x + (tw - ww) / 2, y, x + (tw + ww) / 2, y + th - 1], outline=(255, 60, 200), width=1)
        _label(d, x, y, tw, th, lab, fs)
    return S


def page_paths(out, pages):
    if pages <= 1:
        return [out]
    root, ext = os.path.splitext(out)
    return [f"{root}_p{k + 1:02d}{ext}" for k in range(pages)]


def sheet(path, out, args):
    """The classic sheet (one clip), plus --timeline labels / pagination / --at.  Returns (paths, frames)."""
    info = video_info(path)
    W, H = info["upright_w"], info["upright_h"]
    items = load_timeline(args.timeline)[1] if args.timeline else None
    tw = args.width or (540 if args.at else 320)
    th = int(round(tw * H / W / 2)) * 2
    start = max(0.0, args.start or 0.0)
    end = min(info["duration"], args.end) if args.end else info["duration"]
    paginate = args.paginate or bool(items)
    if args.at:
        times = [float(x) for x in args.at.split(",") if x.strip()]
        frames = grab(path, times, tw, th, info)
    elif args.count:
        n = max(1, args.count)
        times = [start + (end - start) * (i + 0.5) / n for i in range(n)]
        frames = grab(path, times, tw, th, info)
    else:
        fps = args.fps
        if not paginate and (end - start) * fps > args.max_frames:
            fps = args.max_frames / max(0.1, end - start)
            print(f"  {os.path.basename(path)}: {args.fps} fps would give > {args.max_frames} frames; using {fps:.2f} fps "
                  f"(--paginate keeps {args.fps} fps on several pages)")
        frames, times = stream(path, start, end, fps, tw, th)
        if not frames:
            times = [start]
            frames = grab(path, times, tw, th, info)
    labels = [f"{t:.2f}s" + (f" {item_at(items, t)}" if items else "") for t in times]
    rot = f" rot {info['rotation']:+.0f}" if info["rotation"] else ""
    title = (f"{os.path.basename(path)}  {fmt_t(info['duration'])}  {info['w']}x{info['h']}{rot} -> {W}x{H}  "
             f"{info['fps']:g} fps  {'audio' if info['has_audio'] else 'NO audio'}")
    per = len(frames) if (args.at or not paginate) else max(1, args.per_page)
    chunks = [(frames[k:k + per], labels[k:k + per]) for k in range(0, len(frames), per)] or [([], [])]
    outs = page_paths(out, len(chunks))
    for k, ((fr, lab), o) in enumerate(zip(chunks, outs)):
        cols = args.cols or max(1, min(8 if not args.at else 4, int(math.ceil(math.sqrt(len(fr) * th / tw)))))
        t = title + (f"  page {k + 1}/{len(chunks)}" if len(chunks) > 1 else "")
        compose(fr, lab, tw, th, t, cols, args, info).save(o, quality=86)
    return outs, len(frames)


def cuts_sheet(path, out, args):
    """--cuts: for every timeline item the first and the last --cut-frames frames where it is fully on screen
    (after/before its transitions), one row per item -> pages of --rows-per-page rows."""
    from PIL import Image, ImageDraw
    if not args.timeline:
        raise SystemExit("--cuts needs --timeline tl.json (render.py EDL --timeline --timeline-json tl.json)")
    info = video_info(path)
    tl, items = load_timeline(args.timeline)
    fps = float(tl.get("fps") or info["fps"] or 30)
    W, H = info["upright_w"], info["upright_h"]
    tw = args.width or 150
    th = int(round(tw * H / W / 2)) * 2
    k = max(1, args.cut_frames)
    plan = []
    for r in items:
        f0 = int(round((r["start"] + r["overlap_in"]) * fps))
        f1 = int(round((r["end"] - r["overlap_out"]) * fps))          # exclusive
        first = [f for f in range(f0, f0 + k) if f < f1]
        last = [f for f in range(max(f0, f1 - k), f1)]
        plan.append((r, first, last))
    got = frames_by_index(path, {f for _, a, b in plan for f in a + b}, tw, th)
    blank = np.zeros((th, tw, 3), np.uint8)
    per = max(1, args.rows_per_page)
    pages = [plan[i:i + per] for i in range(0, len(plan), per)]
    outs = page_paths(out, len(pages))
    gap, head, lab_w = 4, 34, 120
    fb, fs = font(18), font(max(11, tw // 13))
    for pi, (pg, o) in enumerate(zip(pages, outs)):
        Wd = lab_w + (2 * k) * (tw + gap) + 16
        S = Image.new("RGB", (Wd, head + len(pg) * (th + gap)), (24, 24, 24))
        d = ImageDraw.Draw(S)
        d.text((8, 7), f"{os.path.basename(path)}  cut boundaries: first | last {k} frame(s) of each item"
                       + (f"  page {pi + 1}/{len(pages)}" if len(pages) > 1 else ""), fill=(255, 255, 255), font=fb)
        for row, (r, first, last) in enumerate(pg):
            y = head + row * (th + gap)
            d.text((6, y + 4), r["id"], fill=(255, 230, 0), font=fb)
            d.text((6, y + 28), f"{r['start']:.2f}-{r['end']:.2f}s", fill=(200, 200, 200), font=fs)
            for j, f in enumerate(first + [None] * (k - len(first))):
                x = lab_w + j * (tw + gap)
                S.paste(Image.fromarray(got.get(f, blank) if f is not None else blank), (x, y))
                if f is not None:
                    _label(d, x, y, tw, th, f"{f / fps:.2f}", fs, (120, 255, 120))
            for j, f in enumerate([None] * (k - len(last)) + last):
                x = lab_w + (k + j) * (tw + gap) + 16
                S.paste(Image.fromarray(got.get(f, blank) if f is not None else blank), (x, y))
                if f is not None:
                    _label(d, x, y, tw, th, f"{f / fps:.2f}", fs, (255, 120, 120))
        S.save(o, quality=86)
    return outs, sum(len(a) + len(b) for _, a, b in plan)


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video file or folder (batch)")
    ap.add_argument("--fps", type=float, default=2.0, help="frames per second of source (default 2)")
    ap.add_argument("--count", type=int, help="N evenly spaced frames instead of --fps")
    ap.add_argument("--start", type=float, help="first source second")
    ap.add_argument("--end", type=float, help="last source second")
    ap.add_argument("--width", type=int, help="thumbnail width px (default 320; --at 540; --cuts 150)")
    ap.add_argument("--cols", type=int, help="columns (default: auto)")
    ap.add_argument("--max-frames", type=int, default=60, help="cap per sheet without --paginate (fps is lowered to fit)")
    ap.add_argument("--grid", action="store_true", help="normalised 0.1 coordinate ticks (for frame keys)")
    ap.add_argument("--nine16", action="store_true", help="outline the centred 9:16 window")
    ap.add_argument("--timeline", metavar="TL_JSON", help="film timeline (render.py --timeline-json): labels get the "
                                                          "item id; implies --paginate")
    ap.add_argument("--paginate", action="store_true", help="keep --fps and split into pages instead of capping")
    ap.add_argument("--per-page", type=int, default=60, help="frames per page with --paginate/--timeline (default 60)")
    ap.add_argument("--at", help="comma list of seconds: big frames at exactly these moments (zoom check)")
    ap.add_argument("--cuts", action="store_true", help="with --timeline: first + last frames of every item")
    ap.add_argument("--cut-frames", type=int, default=3, help="--cuts: frames per side (3 = 0.1 s at 30 fps)")
    ap.add_argument("--rows-per-page", type=int, default=14, help="--cuts: items per page (default 14)")
    ap.add_argument("--out", help="output JPG (single video; pages get _p01, _p02 ...)")
    ap.add_argument("--out-dir", help="output folder (default: CWD)")
    a = ap.parse_args()
    if os.path.isdir(a.input):
        vids = [os.path.join(a.input, f) for f in sorted(os.listdir(a.input)) if f.lower().endswith(VIDEO_EXT)]
    else:
        vids = [a.input]
    out_dir = a.out_dir or "."
    os.makedirs(out_dir, exist_ok=True)
    bad = 0
    for v in vids:
        suffix = "_cuts.jpg" if a.cuts else ("_at.jpg" if a.at else "_sheet.jpg")
        out = a.out if (a.out and len(vids) == 1) else \
            os.path.join(out_dir, os.path.splitext(os.path.basename(v))[0] + suffix)
        try:
            outs, n = cuts_sheet(v, out, a) if a.cuts else sheet(v, out, a)
            print(f"{outs[0]}" + (f" ... {outs[-1]} ({len(outs)} pages)" if len(outs) > 1 else "") + f"  ({n} frames)")
        except SystemExit:
            raise
        except Exception as e:
            bad += 1
            print(f"{v}: ERROR {str(e).splitlines()[0][:200]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

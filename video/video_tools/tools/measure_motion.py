"""Measure frame-to-frame motion smoothness (Ken Burns / pan jitter) of a rendered clip.

  python tools/measure_motion.py clip.mp4 [clip2.mp4 ...]
  python tools/measure_motion.py film.mp4 --start 26.9 --end 30.4            one item of a film
  python tools/measure_motion.py film.mp4 --roi 40,480,1040,1300             pixel ROI x0,y0,x1,y1
  python tools/measure_motion.py film.mp4 --box 0.8 --box-y 0.5               ROI = inside a box-mode box
  python tools/measure_motion.py clip.mp4 --csv motion.csv --json

For each consecutive frame pair: track features (LK optical flow), fit a similarity transform
(scale + translation), then compare the per-frame motion with a 7-frame moving average of itself.
Smooth Ken Burns => tiny residual (well under 0.1 px).  Integer-stepping zoompan => large, spiky
residual.  JITTER = sqrt(res_x^2 + res_y^2 + res_zoom_edge^2) where zoom-edge is the displacement of
a point 400 px from the centre due to the zoom alone.  Note: intentional accelerations of fast keyed
pans also show up as residual (use engine/test/path_test.py to separate engine error from path design).
Importable: motion(path, roi=None, start=None, end=None), residual(x), report(path, roi=None, ...).
"""
import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import FFMPEG, video_info  # noqa: E402


def frames(path, start=None, end=None):
    info = video_info(path)
    w, h = info["upright_w"], info["upright_h"]
    cmd = [FFMPEG, "-nostdin", "-v", "error"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    if end is not None:
        cmd += ["-to", f"{end:.3f}"]
    cmd += ["-i", path, "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    n = w * h
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n:
                break
            yield np.frombuffer(b, np.uint8).reshape(h, w)
    finally:
        p.stdout.close()
        p.kill()
        p.wait()


def motion(path, roi=None, start=None, end=None):
    """rows: (scale, dx, dy, zoom_edge_px) per consecutive frame pair."""
    out = []
    prev = None
    for f in frames(path, start, end):
        g = f if roi is None else f[roi[1]:roi[3], roi[0]:roi[2]]
        if prev is not None:
            pts = cv2.goodFeaturesToTrack(prev, 600, 0.01, 12)
            M = None
            if pts is not None and len(pts) >= 6:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None, winSize=(31, 31), maxLevel=3,
                                                      criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.001))
                ok = st.ravel() == 1
                if ok.sum() >= 6:
                    M, _ = cv2.estimateAffinePartial2D(pts[ok], nxt[ok], method=cv2.RANSAC, ransacReprojThreshold=0.5)
            if M is None:  # featureless frame (e.g. a dip to white): no measurement
                out.append((np.nan, np.nan, np.nan, np.nan))
            else:
                s = float(np.hypot(M[0, 0], M[1, 0]))
                h, w = g.shape
                # motion of the frame centre (px) - captures both pan and zoom drift
                cx, cy = w / 2, h / 2
                dx = M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx
                dy = M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy
                out.append((s, dx, dy, (s - 1) * 400))
        prev = g
    return np.array(out).reshape(-1, 4)


def residual(x, win=7):
    k = np.ones(win) / win
    pad = np.pad(x, win // 2, mode="edge")
    sm = np.convolve(pad, k, mode="valid")
    return x - sm


def stats(m):
    if len(m) < 8:
        return None
    m = m[~np.isnan(m).any(axis=1)]
    if len(m) < 8:
        return None
    r_zoom = residual(m[:, 3])[3:-3]
    r_x = residual(m[:, 1])[3:-3]
    r_y = residual(m[:, 2])[3:-3]
    j = np.sqrt(r_zoom ** 2 + r_x ** 2 + r_y ** 2)
    return dict(frames=len(m) + 1, zoom_per_frame_pct=float(np.mean(m[:, 0] - 1) * 100),
                pan_px_per_frame=float(np.mean(np.hypot(m[:, 1], m[:, 2]))),
                jitter_rms=float(np.sqrt(np.mean(j ** 2))), jitter_max=float(j.max()),
                max_x=float(np.abs(r_x).max()), max_y=float(np.abs(r_y).max()), max_zoom_edge=float(np.abs(r_zoom).max()))


def report(path, roi=None, start=None, end=None, label=None):
    s = stats(motion(path, roi, start, end))
    name = label or os.path.basename(path)
    if s is None:
        return f"{name}: too short"
    return (f"{name:<28} frames={s['frames']:4d}  zoom/frame={s['zoom_per_frame_pct']:+.3f}%  "
            f"JITTER rms={s['jitter_rms']:.3f}px  max={s['jitter_max']:.3f}px  "
            f"(x {s['max_x']:.2f}, y {s['max_y']:.2f}, zoom-edge {s['max_zoom_edge']:.2f})")


def box_roi(W, H, aspect, box_y=0.5, margin=None):
    """ROI inside a box-mode box (full width, height W/aspect, centred at box_y*H), inset by margin."""
    margin = int(round(40 * W / 1080)) if margin is None else margin
    bh = W / float(aspect)
    cy = float(box_y) * H
    cy = min(max(cy, bh / 2), H - bh / 2)
    return (margin, int(cy - bh / 2 + margin), W - margin, int(cy + bh / 2 - margin))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--start", type=float, help="first second to analyse")
    ap.add_argument("--end", type=float, help="last second to analyse")
    ap.add_argument("--roi", help="x0,y0,x1,y1 in pixels of the (upright) video")
    ap.add_argument("--box", type=float, metavar="ASPECT", help="measure inside a box-mode box of this aspect (w/h)")
    ap.add_argument("--box-y", type=float, default=0.5, help="box vertical centre (0..1, default 0.5)")
    ap.add_argument("--csv", help="write per-frame (scale, dx, dy, zoom_edge) of the first video")
    ap.add_argument("--json", action="store_true", help="print JSON stats instead of the text line")
    a = ap.parse_args()
    rc = 0
    for i, p in enumerate(a.videos):
        roi = None
        if a.roi:
            roi = tuple(int(v) for v in a.roi.split(","))
        elif a.box:
            info = video_info(p)
            roi = box_roi(info["upright_w"], info["upright_h"], a.box, a.box_y)
        m = motion(p, roi, a.start, a.end)
        if a.csv and i == 0:
            np.savetxt(a.csv, m, delimiter=",", header="scale,dx,dy,zoom_edge_px", fmt="%.5f")
        s = stats(m)
        if a.json:
            print(json.dumps(dict(video=p, roi=roi, start=a.start, end=a.end, **(s or {"error": "too short"}))))
        elif s is None:
            print(f"{os.path.basename(p)}: too short")
            rc = 1
        else:
            print(f"{os.path.basename(p):<28} frames={s['frames']:4d}  zoom/frame={s['zoom_per_frame_pct']:+.3f}%  "
                  f"JITTER rms={s['jitter_rms']:.3f}px  max={s['jitter_max']:.3f}px  "
                  f"(x {s['max_x']:.2f}, y {s['max_y']:.2f}, zoom-edge {s['max_zoom_edge']:.2f})"
                  + (f"  roi={roi}" if roi else ""), flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())

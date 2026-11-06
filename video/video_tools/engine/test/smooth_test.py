"""Sub-pixel smoothness proof for slow pans / Ken Burns.

Renders a very slow pan (~0.3 px/frame) and a slow zoom on a static 4K photo with the engine's
own Plan + warp code, then measures the frame-to-frame motion of the output with phase
correlation.  A naive integer-pixel crop (what ffmpeg crop/zoompan expressions do) is measured the
same way for comparison: it moves in 0/1-px steps (visible stutter), ours tracks the planned
sub-pixel path.  Writes smooth_report.json and smooth_plot.png to test/out/ (or --outdir).

  python test/smooth_test.py [--photo PATH] [--outdir DIR]
  (default photo: test/media/test_photo.jpg from make_test_media.py; any large detailed photo works)
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import framing  # noqa: E402
from itemrender import _load_photo  # noqa: E402

PHOTO = os.path.join(HERE, "media", "test_photo.jpg")


def render_frames(arr, fr, n, OW=1080, OH=1920):
    import cv2
    H, W = arr.shape[:2]
    plan = framing.Plan(W, H, OW, OH, fr, n, times=np.arange(n) / 30)
    x, y, w, h = plan.crop
    pre = cv2.resize(arr[y:y + h, x:x + w], (plan.PW, plan.PH), interpolation=cv2.INTER_AREA)
    out = []
    for k in range(n):
        o = cv2.warpAffine(pre, plan.cv_mats[k], plan.region_size, flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                           borderMode=cv2.BORDER_REPLICATE)
        out.append(cv2.cvtColor(o, cv2.COLOR_RGB2GRAY))
    return out, plan


def naive_frames(arr, fr, n, OW=1080, OH=1920):
    """Integer-pixel crop of the same path, then resize (what crop=x:y with rounded expressions does)."""
    import cv2
    H, W = arr.shape[:2]
    cx, cy, zoom = framing.frame_curves(fr, n, np.arange(n) / 30)
    ww0, wh0 = framing.base_window(W, H, OW / OH)
    out = []
    for k in range(n):
        ww, wh = ww0 / zoom[k], wh0 / zoom[k]
        x0 = int(round(cx[k] * W - ww / 2))
        y0 = int(round(cy[k] * H - wh / 2))
        crop = arr[y0:y0 + int(round(wh)), x0:x0 + int(round(ww))]
        o = cv2.resize(crop, (OW, OH), interpolation=cv2.INTER_AREA)
        out.append(cv2.cvtColor(o, cv2.COLOR_RGB2GRAY))
    return out


def phase_dx(frames):
    """Per-frame motion of the frame centre (px): LK features + RANSAC similarity (sub-pixel,
    unbiased - phase correlation is biased towards integer shifts)."""
    import cv2
    d = []
    for a, b in zip(frames, frames[1:]):
        pts = cv2.goodFeaturesToTrack(a, 800, 0.01, 10)
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, None, winSize=(31, 31), maxLevel=3,
                                              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.001))
        ok = st.ravel() == 1
        M, _ = cv2.estimateAffinePartial2D(pts[ok], nxt[ok], method=cv2.RANSAC, ransacReprojThreshold=0.5)
        h, w = a.shape
        c = np.array([w / 2, h / 2, 1.0])
        q = M @ c
        d.append((q[0] - c[0], q[1] - c[1]))
    return np.array(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--photo", default=PHOTO)
    ap.add_argument("--outdir", default=os.path.join(HERE, "out"))
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    arr, _ = _load_photo(args.photo)
    n = 90
    pan = dict(mode="crop", cx0=0.45, cx1=0.46, cy0=0.5, cy1=0.5, zoom0=1.0, zoom1=1.0, ease="linear")
    ours, plan = render_frames(arr, pan, n)
    naive = naive_frames(arr, pan, n)
    d_ours, d_naive = phase_dx(ours), phase_dx(naive)
    # planned per-frame motion in output px (content moves opposite to the window)
    exp = -np.diff([M[0, 2] for M in plan.mats]) / np.array([framing.mat_scale(M) for M in plan.mats[1:]])
    rep = {"pan_speed_px_per_frame": float(np.mean(np.abs(exp))),
           "ours": {"dx_mean": float(d_ours[:, 0].mean()), "dx_std": float(d_ours[:, 0].std()),
                    "rms_err_vs_plan": float(np.sqrt(np.mean((d_ours[:, 0] - exp) ** 2))),
                    "dx_min": float(d_ours[:, 0].min()), "dx_max": float(d_ours[:, 0].max())},
           "naive_integer_crop": {"dx_mean": float(d_naive[:, 0].mean()), "dx_std": float(d_naive[:, 0].std()),
                                  "rms_err_vs_plan": float(np.sqrt(np.mean((d_naive[:, 0] - exp) ** 2))),
                                  "dx_min": float(d_naive[:, 0].min()), "dx_max": float(d_naive[:, 0].max())}}
    # slow zoom: measure scale per frame with ECC on the centre
    import cv2
    zoomfr = dict(mode="crop", cx0=0.5, cx1=0.5, cy0=0.5, cy1=0.5, zoom0=1.0, zoom1=1.03, ease="linear")
    zo, zplan = render_frames(arr, zoomfr, 60)
    sc = []
    for a, b in zip(zo, zo[1:]):
        A = cv2.resize(a, (540, 960), interpolation=cv2.INTER_AREA).astype(np.float32)
        B = cv2.resize(b, (540, 960), interpolation=cv2.INTER_AREA).astype(np.float32)
        w = np.eye(2, 3, dtype=np.float32)
        _, w = cv2.findTransformECC(A, B, w, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-8), None, 5)
        sc.append(float(np.sqrt(abs(np.linalg.det(w[:, :2])))))
    sc = np.array(sc)
    z_exp = np.array([framing.mat_scale(zplan.mats[k]) / framing.mat_scale(zplan.mats[k + 1]) for k in range(59)])
    rep["zoom"] = {"per_frame_scale_mean": float(sc.mean()), "per_frame_scale_std": float(sc.std()),
                   "expected": float(z_exp.mean()), "rms_err": float(np.sqrt(np.mean((1 / sc - z_exp) ** 2)))}
    out = os.path.join(args.outdir, "smooth_report.json")
    with open(out, "w") as f:
        json.dump(rep, f, indent=2)
    try:
        from PIL import Image, ImageDraw
        Wp, Hp = 900, 300
        im = Image.new("RGB", (Wp, Hp), (255, 255, 255))
        d = ImageDraw.Draw(im)
        def ys(v):
            return Hp - 20 - (v + 0.2) / 1.4 * (Hp - 40)
        for arrv, col in ((d_naive[:, 0], (220, 60, 60)), (d_ours[:, 0], (30, 120, 220)), (exp, (0, 0, 0))):
            pts = [(10 + i * (Wp - 20) / len(arrv), ys(-v)) for i, v in enumerate(arrv)]
            d.line(pts, fill=col, width=2)
        d.text((12, 6), "per-frame motion (px): red = integer crop, blue = engine, black = planned", fill=(0, 0, 0))
        im.save(os.path.join(args.outdir, "smooth_plot.png"))
    except Exception:
        pass
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()

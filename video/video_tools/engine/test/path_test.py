"""Isolate the camera path of one EDL item: apply its planned per-frame warps (keys, clamps,
tilt, speed map...) to a single STATIC frame of its source, so any jitter in the output comes from
the engine's path, not from the footage.  Writes test/out/path_<id>.mp4 (or --outdir), then compares
the measured motion (tools/measure_motion.py) with the planned path.

  python test/path_test.py <edl.json> <item id> [source time for the still] [--outdir DIR]
                           [--video-dir D --photo-dir D]
"""
import argparse
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import edl as E  # noqa: E402
import framing as F  # noqa: E402
from common import FFMPEG, YUV2RGB, probe, rotation_filters  # noqa: E402
from itemrender import _load_photo, output_times  # noqa: E402


def main():
    import cv2
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl")
    ap.add_argument("item")
    ap.add_argument("t", nargs="?", type=float, help="source time of the still (default: middle of in..out)")
    ap.add_argument("--outdir", default=os.path.join(HERE, "out"))
    ap.add_argument("--video-dir")
    ap.add_argument("--photo-dir")
    a = ap.parse_args()
    path, iid = a.edl, a.item
    e = E.load(path, path_overrides={"video": a.video_dir, "photo": a.photo_dir})
    it = next(x for x in e["items"] if x["id"] == iid)
    r = next(x for x in e["timeline"]["rows"] if x["id"] == iid)
    n, fps = r["n"], e["output"]["fps"]
    if it["type"] == "photo":
        arr, _ = _load_photo(it["_src"], it.get("rotate", 0), it.get("hflip", False))
        times = np.arange(n) / fps
    else:
        info = probe(it["_src"])
        tot = (info["auto_cw"] + it.get("rotate", 0)) % 360
        W, H = (info["h"], info["w"]) if tot in (90, 270) else (info["w"], info["h"])
        t = a.t if a.t is not None else (it["in"] + it["out"]) / 2
        vf = ",".join(rotation_filters(tot, it.get("hflip", False)) + [f"scale={YUV2RGB}", "format=rgb24"])
        raw = subprocess.run([FFMPEG, "-v", "error", "-noautorotate", "-ss", str(t), "-i", it["_src"], "-frames:v", "1",
                              "-vf", vf, "-f", "rawvideo", "-"], stdout=subprocess.PIPE).stdout
        arr = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        job = {"speed_map": it.get("speed_map"), "in": it["in"], "out": it["out"], "fps": fps, "n": n,
               "speed": it["speed"], "id": iid}
        times = output_times(job)
    H, W = arr.shape[:2]
    OW, OH = e["output"]["w"], e["output"]["h"]
    plan = F.Plan(W, H, OW, OH, it["frame"], n, times=times, tilt_deg=it.get("tilt_deg", 0.0), fps=fps)
    print(plan.describe(), plan.warnings)
    x, y, w, h = plan.crop
    pre = cv2.resize(arr[y:y + h, x:x + w], (plan.PW, plan.PH), interpolation=cv2.INTER_AREA)
    os.makedirs(a.outdir, exist_ok=True)
    out = os.path.join(a.outdir, f"path_{iid}.mp4")
    rw, rh = plan.region_size
    enc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{rw}x{rh}",
                            "-framerate", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "10", "-preset", "veryfast",
                            "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for k in range(n):
        o = cv2.warpAffine(pre, plan.cv_mats[k], (rw, rh), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                           borderMode=cv2.BORDER_REPLICATE)
        enc.stdin.write(o.tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
    # compare measured motion (QA tool) with the analytic plan: same quantity, same convention
    import importlib.util
    qa = os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools", "measure_motion.py")
    if os.path.exists(qa):
        spec = importlib.util.spec_from_file_location("mm", qa)
        mm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mm)
        meas = mm.motion(out.replace("\\", "/"))
        cxo, cyo = rw / 2, rh / 2
        plan_d = []
        for k in range(n - 1):
            T = np.linalg.inv(plan.mats[k + 1]) @ plan.mats[k]  # output_k -> output_k+1
            # region offset: mats map full-frame output coords; the clip is the box region
            rx0, ry0 = plan.lay.region[:2]
            c = np.array([cxo + rx0, cyo + ry0, 1.0])
            q = T @ c
            plan_d.append((float(np.hypot(T[0, 0], T[1, 0])), q[0] - c[0], q[1] - c[1]))
        plan_d = np.array(plan_d)
        err = meas[:, 1:3] - plan_d[:, 1:3]
        qa_plan = []
        for arr_ in (plan_d[:, 1], plan_d[:, 2]):
            qa_plan.append(np.abs(mm.residual(arr_)[3:-3]).max())
        print(f"measured vs planned per-frame motion: rms {np.sqrt(np.mean(err ** 2)):.3f} px, "
              f"max {np.abs(err).max():.3f} px  (planned path alone scores QA residual x {qa_plan[0]:.2f}, y {qa_plan[1]:.2f} px)")


if __name__ == "__main__":
    main()

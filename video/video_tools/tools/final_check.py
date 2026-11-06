"""Acceptance checks of a finished film against its EDL: format, duration, loudness, photo jitter.

  python tools/final_check.py FILM.mp4 EDL.json
  python tools/final_check.py FILM_preview.mp4 EDL.json --preview          a --preview render
  python tools/final_check.py FILM.mp4 EDL.json --timeline-json tl.json    no sources needed
                              (tl.json from: python engine/render.py EDL.json --timeline --timeline-json tl.json)
  python tools/final_check.py FILM.mp4 EDL.json --video-dir D:/footage --photo-dir D:/photos
  python tools/final_check.py FILM_ig.mp4 EDL.json --size 1080x1920 --no-motion --json report.json

Checks (FAIL = exit code 1, WARN = printed only):
  format    H.264 High / HEVC Main, yuv420p, W x H and fps of the EDL, BT.709 tags, AAC 48 kHz stereo,
            +faststart (moov before mdat)
  duration  frame count vs the EDL timeline (+-1 frame)
  loudness  integrated loudness within +-1 LU of audio.target_lufs, true peak <= audio.true_peak + 0.3
  jitter    Ken Burns smoothness of every photo item, measured away from its transitions (inside the box
            for box/fit items) with tools/measure_motion.py and compared with the PLANNED camera path
            (the engine's own framing code, as engine/test/path_test.py does): WARN when measured-minus-
            planned motion exceeds --jitter-rms / --jitter-max px.  The old residual (motion vs its own
            7-frame average) is shown as info only - it false-alarmed on fast designed pans with a bell-shaped
            speed curve (0 -> 20 -> 0 px/frame).  Frames under an EDL text are left out of the comparison
            (static letters over a moving photo bias the tracker).  Without sources (--timeline-json), or with
            text over the whole item, the residual is judged.
"""
import argparse
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import FFMPEG, ffprobe, run, safe_console, use_engine  # noqa: E402
import measure_motion as mm  # noqa: E402


def planned_motion(it, n, OW, OH, fps):
    """Per-frame planned motion (scale, dx, dy) of a photo item's virtual camera at the centre of its output
    region (the box for box/fit), from the engine's framing code - same convention as measure_motion."""
    import numpy as np
    use_engine()
    import framing
    from PIL import Image, ImageOps
    src = it["_src"]
    if src.lower().endswith((".heic", ".heif")):
        import pillow_heif
        pillow_heif.register_heif_opener()
    W, H = ImageOps.exif_transpose(Image.open(src)).size
    if int(it.get("rotate", 0)) % 180:
        W, H = H, W
    plan = framing.Plan(W, H, OW, OH, it["frame"], n, times=np.arange(n) / fps, tilt_deg=it.get("tilt_deg", 0.0),
                        fps=fps)
    rx0, ry0 = plan.lay.region[:2]
    rw, rh = plan.region_size
    c = np.array([rx0 + rw / 2, ry0 + rh / 2, 1.0])
    out = []
    for k in range(n - 1):
        T = np.linalg.inv(plan.mats[k + 1]) @ plan.mats[k]      # output_k -> output_k+1 for the same content
        q = T @ c
        out.append((float(np.hypot(T[0, 0], T[1, 0])), q[0] - c[0], q[1] - c[1]))
    return np.array(out).reshape(-1, 3)


def vs_plan(meas, plan_d, k0, max_lag=3, skip=None):
    """Measured minus planned per-frame motion (dx, dy and the zoom's displacement 400 px from the centre),
    at the best alignment within +-max_lag frames.  skip: bool per measured frame pair to ignore (e.g. under an
    on-screen text: static letters over a zooming photo bias the tracker towards 'no motion').
    -> dict(rms, max, lag, frames, plan_speed_max) or None."""
    import numpy as np
    best = None
    good = ~np.isnan(meas).any(axis=1)
    if skip is not None:
        good &= ~np.asarray(skip, bool)[:len(good)]
    for L in range(-max_lag, max_lag + 1):
        idx = np.arange(len(meas)) + k0 + L
        ok = good & (idx >= 0) & (idx < len(plan_d))
        if ok.sum() < 8:
            continue
        p = plan_d[idx[ok]]
        e = np.c_[meas[ok, 1] - p[:, 1], meas[ok, 2] - p[:, 2], (meas[ok, 0] - p[:, 0]) * 400]
        j = np.sqrt((e ** 2).sum(1))
        rms = float(np.sqrt(np.mean(j ** 2)))
        if best is None or rms < best["rms"]:
            best = dict(rms=rms, max=float(j.max()), lag=L, frames=int(ok.sum()),
                        plan_speed_max=float(np.hypot(p[:, 1], p[:, 2]).max()))
    return best


def atoms_order(path):
    """Top-level MP4 atom types in file order."""
    out = []
    with open(path, "rb") as f:
        size_total = os.path.getsize(path)
        pos = 0
        while pos < size_total and len(out) < 64:
            f.seek(pos)
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            sz, typ = struct.unpack(">I4s", hdr)
            if sz == 1:
                sz = struct.unpack(">Q", f.read(8))[0]
            elif sz == 0:
                sz = size_total - pos
            out.append(typ.decode("latin1"))
            if sz < 8:
                break
            pos += sz
    return out


def ebur128(path):
    p = run([FFMPEG, "-nostdin", "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0",
             "-af", "ebur128=peak=true", "-f", "null", "-"], check=False, text=True)
    t = p.stderr
    summ = t[t.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    LRA = re.search(r"LRA:\s+(-?[\d.]+) LU", summ)
    pk = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summ)
    return (float(I.group(1)) if I else None, float(LRA.group(1)) if LRA else None,
            float(pk.group(1)) if pk and pk.group(1) != "-inf" else None)


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("film")
    ap.add_argument("edl")
    ap.add_argument("--preview", action="store_true", help="film is a --preview render (half size)")
    ap.add_argument("--size", help="expected WxH (overrides the EDL, e.g. for a downscaled export)")
    ap.add_argument("--timeline-json", help="timeline from render.py --timeline-json (sources then not needed)")
    for k in ("video", "photo", "proxy", "music"):
        ap.add_argument(f"--{k}-dir", help=f"override the EDL's paths.{k}")
    ap.add_argument("--no-motion", action="store_true", help="skip the photo jitter measurement")
    ap.add_argument("--jitter-rms", type=float, default=0.15, help="WARN above this rms jitter (px)")
    ap.add_argument("--jitter-max", type=float, default=0.6, help="WARN above this max jitter (px)")
    ap.add_argument("--json", help="write the report as JSON")
    a = ap.parse_args()

    raw = json.load(open(a.edl, encoding="utf-8"))
    e = None
    if a.timeline_json:
        tl = json.load(open(a.timeline_json, encoding="utf-8"))
        out = dict(raw.get("output", {}))
        out.setdefault("w", 1080)
        out.setdefault("h", 1920)
        out.setdefault("fps", 30)
        if a.preview:
            out["w"], out["h"] = (out["w"] // 2) // 2 * 2, (out["h"] // 2) // 2 * 2
        audio = dict(raw.get("audio", {}))
    else:
        use_engine()
        import edl as edlmod
        try:
            e = edlmod.load(a.edl, preview=a.preview,
                            path_overrides={k: getattr(a, f"{k}_dir") for k in ("video", "photo", "proxy", "music")})
        except Exception as ex:
            sys.exit(f"cannot load the EDL ({ex}).\nPass --video-dir/--photo-dir, or --timeline-json from render.py --timeline-json.")
        tl = edlmod.timeline_json(e)
        out, audio = e["output"], e["audio"]
    target_I = float(audio.get("target_lufs", -14.0))
    tp_max = float(audio.get("true_peak", -1.5))
    W, H = (int(v) for v in a.size.lower().split("x")) if a.size else (out["w"], out["h"])
    fps = int(out.get("fps", tl.get("fps", 30)))

    res = {"film": os.path.abspath(a.film), "checks": []}

    def check(name, status, msg):
        res["checks"].append(dict(check=name, status=status, detail=msg))
        print(f"{status:<5} {name:<10} {msg}", flush=True)

    j = ffprobe(a.film, ["-count_packets"])
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        check("format", "FAIL", "no video stream")
        return 1
    probs, warns = [], []
    if v["codec_name"] == "h264":
        if (v.get("profile") or "").lower() != "high":
            warns.append(f"H.264 profile {v.get('profile')} (expected High)")
    elif v["codec_name"] == "hevc":
        if v.get("codec_tag_string") != "hvc1":
            warns.append(f"HEVC tag {v.get('codec_tag_string')} (Apple/Instagram want hvc1)")
    else:
        probs.append(f"codec {v['codec_name']}")
    if v.get("pix_fmt") != "yuv420p":
        probs.append(f"pix_fmt {v.get('pix_fmt')}")
    if (int(v["width"]), int(v["height"])) != (W, H):
        probs.append(f"size {v['width']}x{v['height']} != {W}x{H}")
    n_, _, d_ = v.get("r_frame_rate", "0/1").partition("/")
    rfps = float(n_) / float(d_ or 1)
    if abs(rfps - fps) > 0.01:
        probs.append(f"fps {rfps:g} != {fps}")
    col = (v.get("color_primaries"), v.get("color_transfer"), v.get("color_space"))
    if col != ("bt709", "bt709", "bt709"):
        warns.append(f"colour tags {col} (expected bt709 x3)")
    if au is None:
        probs.append("no audio")
    else:
        if au.get("codec_name") != "aac" or au.get("sample_rate") != "48000" or int(au.get("channels", 0)) != 2:
            warns.append(f"audio {au.get('codec_name')} {au.get('sample_rate')} Hz {au.get('channels')} ch (expected AAC 48 kHz stereo)")
    order = atoms_order(a.film)
    if "moov" in order and "mdat" in order and order.index("moov") > order.index("mdat"):
        probs.append("no +faststart (moov after mdat)")
    size_mb = os.path.getsize(a.film) / 1e6
    fmt = (f"{v['codec_name']} {v.get('profile')} {v['width']}x{v['height']} {rfps:g} fps {v.get('pix_fmt')} | "
           f"{(au or {}).get('codec_name')} {(au or {}).get('sample_rate')} Hz | {size_mb:.1f} MB, "
           f"{float(j['format'].get('bit_rate', 0)) / 1e6:.2f} Mbit/s")
    check("format", "FAIL" if probs else ("WARN" if warns else "PASS"), fmt + ("  !! " + "; ".join(probs + warns) if probs or warns else ""))

    nfr = int(v.get("nb_read_packets") or v.get("nb_frames") or round(float(j["format"]["duration"]) * fps))
    want = int(tl["total_frames"])
    check("duration", "PASS" if abs(nfr - want) <= 1 else "FAIL",
          f"{nfr} frames ({nfr / fps:.3f} s), timeline {want} frames ({want / fps:.3f} s)")

    if au is not None:
        I, LRA, pk = ebur128(a.film)
        bad = I is None or abs(I - target_I) > 1.0 or (pk is not None and pk > tp_max + 0.3)
        check("loudness", "FAIL" if bad else "PASS",
              f"I {I} LUFS (target {target_I}), LRA {LRA} LU, true peak {pk} dBTP (max {tp_max})")
        res["loudness"] = dict(I=I, LRA=LRA, true_peak=pk)

    if not a.no_motion:
        items = {it["id"]: it for it in (e["items"] if e else raw.get("items", []))}
        res["jitter"] = {}
        for row in tl["items"]:
            it = items.get(row["id"], {})
            if it.get("type") != "photo":
                continue
            t0 = row["start"] + row["overlap_in"] + 0.05
            t1 = row["end"] - row["overlap_out"] - 0.05
            fr = it.get("frame") or {}
            roi = None
            if fr.get("mode") in ("box", "fit"):
                asp = float(fr.get("aspect", 0.8)) if fr.get("mode") == "box" else None
                if asp is None:  # fit: aspect of the photo itself (needs the resolved source)
                    try:
                        from PIL import Image, ImageOps
                        im = ImageOps.exif_transpose(Image.open(it["_src"]))
                        asp = im.width / im.height
                        if int(it.get("rotate", 0)) % 180:
                            asp = 1 / asp
                    except Exception:
                        asp = 1.0
                roi = mm.box_roi(int(v["width"]), int(v["height"]), max(asp, int(v["width"]) / int(v["height"])),
                                 float(fr.get("box_y", fr.get("box_cy", 0.5))))
            # start just after a frame boundary: an -ss exactly half-way between two frames made ffmpeg emit one
            # frame twice (a fake 0-motion pair); the first pair is dropped anyway
            f0 = int(-(-round(t0 * fps * 1000) // 1000))                          # first film frame >= t0
            meas = mm.motion(a.film, roi, (f0 + 0.25) / fps, t1)[1:]
            f0 += 1
            s = mm.stats(meas)
            if s is None:
                check("jitter", "WARN", f"{row['id']}: too short to measure ({t1 - t0:.2f} s)")
                continue
            vp, why, n_text = None, "no sources (--timeline-json)", 0
            if e is not None and it.get("_src"):
                try:
                    pd = planned_motion(it, int(row["frames"]), int(v["width"]), int(v["height"]), fps)
                    k0 = f0 - int(row["start_frame"])
                    spans = [(float(tx["start"]) - 0.05, float(tx["end"]) + 0.05) for tx in e.get("texts", [])]
                    skip = [any(a0 <= (f0 + i + 1) / fps and (f0 + i) / fps <= b0 for a0, b0 in spans)
                            for i in range(len(meas))]
                    n_text = sum(skip)
                    vp = vs_plan(meas, pd, k0, skip=skip)
                    why = ("text on screen during the whole item" if n_text >= len(meas) - 8 else "alignment failed") \
                        if vp is None else ""
                except Exception as ex:      # never let the comparison break the acceptance check
                    why = f"plan not computed ({ex.__class__.__name__}: {str(ex)[:80]})"
            s["vs_plan"] = vp
            res["jitter"][row["id"]] = s
            resid = f"residual rms {s['jitter_rms']:.3f} / max {s['jitter_max']:.3f} px"
            if vp is not None:
                st = "WARN" if vp["rms"] > a.jitter_rms or vp["max"] > a.jitter_max else "PASS"
                msg = (f"{row['id']:<8} {t0:7.2f}-{t1:7.2f}s  vs plan rms {vp['rms']:.3f} px, max {vp['max']:.3f} px "
                       f"(planned pan up to {vp['plan_speed_max']:.1f} px/frame"
                       + (f"; {n_text} frames under text skipped" if n_text else "") + f") | info: {resid}")
            else:
                st = "WARN" if s["jitter_rms"] > a.jitter_rms or s["jitter_max"] > a.jitter_max else "PASS"
                msg = f"{row['id']:<8} {t0:7.2f}-{t1:7.2f}s  {resid} ({why}; fast designed pans can read high)"
            check("jitter", st, msg + f", zoom/frame {s['zoom_per_frame_pct']:+.3f}%" + (f"  roi={roi}" if roi else ""))
        if not res["jitter"]:
            print("      jitter     (no photo items)")
    fails = [c for c in res["checks"] if c["status"] == "FAIL"]
    res["PASS"] = not fails
    print(("PASS" if not fails else f"FAIL ({len(fails)} check(s))") +
          f" - {sum(c['status'] == 'WARN' for c in res['checks'])} warning(s)")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())

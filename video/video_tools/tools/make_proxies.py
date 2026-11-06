"""Make preview proxies for the engine's --preview mode (render.py looks for <proxy dir>/<stem>.mp4).

  python tools/make_proxies.py D:/footage D:/project/proxy
  python tools/make_proxies.py D:/footage D:/project/proxy --only IMG_4348,IMG_4357 --jobs 2

Proxy format (the Magic Safari proxies): upright pixels (autorotated, no rotation metadata), Lanczos
scaled into a 1920x1080 / 1080x1920 box, H.264 CRF 16 preset medium, yuv420p, GOP 30, BT.709 tags,
60 fps CFR, AAC 192k 48 kHz stereo, first video + first audio stream only, +faststart.
4K HEVC -> 1080p H.264 makes previews ~3-4x faster; ~40 MB per minute of footage.  Existing proxies
are skipped.  Note: the engine treats a proxy like the source (same normalised framing), so proxies
must keep the full frame - never crop them.
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import FFMPEG, VIDEO_EXT, free_gb, run, safe_console, video_info  # noqa: E402


def proxy(src, dst, fps):
    info = video_info(src)
    portrait = info["upright_h"] > info["upright_w"]
    bw, bh = (1080, 1920) if portrait else (1920, 1080)
    vf = (f"scale={bw}:{bh}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,"
          f"format=yuv420p")
    tmp = dst + ".tmp.mp4"
    cmd = [FFMPEG, "-nostdin", "-hide_banner", "-v", "warning", "-y", "-i", src, "-map", "0:v:0", "-map", "0:a:0?",
           "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-g", "30", "-pix_fmt", "yuv420p",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-fps_mode", "cfr", "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-map_metadata", "-1", "-movflags", "+faststart", tmp]
    p = run(cmd, check=False, text=True)
    if p.returncode != 0:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(p.stderr[-500:])
    os.replace(tmp, dst)
    o = video_info(dst)
    return f"{os.path.basename(dst)} {o['w']}x{o['h']} rot {o['rotation']:g} {o['duration']:.2f}s " \
           f"(src {info['duration']:.2f}s) {os.path.getsize(dst) / 1e6:.1f} MB" + (f"  WARN: {p.stderr.strip()[:120]}" if p.stderr.strip() else "")


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_folder")
    ap.add_argument("out_folder")
    ap.add_argument("--only", help="comma list of file stems")
    ap.add_argument("--fps", type=int, default=60, help="proxy frame rate (default 60 = iPhone source rate)")
    ap.add_argument("--jobs", type=int, default=1, help="parallel encodes (default 1; 4K HEVC decode is RAM-heavy)")
    a = ap.parse_args()
    os.makedirs(a.out_folder, exist_ok=True)
    only = {s.strip().lower() for s in (a.only or "").split(",") if s.strip()}
    srcs = [os.path.join(a.in_folder, f) for f in sorted(os.listdir(a.in_folder)) if f.lower().endswith(VIDEO_EXT)
            and (not only or os.path.splitext(f)[0].lower() in only)]
    todo = [(s, os.path.join(a.out_folder, os.path.splitext(os.path.basename(s))[0] + ".mp4")) for s in srcs]
    todo = [(s, d) for s, d in todo if not os.path.exists(d)]
    print(f"{len(srcs)} video(s), {len(srcs) - len(todo)} proxies exist, making {len(todo)}")
    bad = 0

    def one(sd):
        if free_gb(a.out_folder) < 1.0:
            return f"{os.path.basename(sd[0])}: SKIPPED (< 1 GB free)"
        try:
            return proxy(sd[0], sd[1], a.fps)
        except Exception as e:
            return f"{os.path.basename(sd[0])}: ERROR {str(e).strip()[:300]}"
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for msg in ex.map(one, todo):
            bad += ("ERROR" in msg or "SKIPPED" in msg)
            print(" ", msg, flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

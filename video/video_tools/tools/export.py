"""Size-targeted 2-pass delivery encodes of a finished master (the Magic Safari delivery settings).

  python tools/export.py master.mp4 --preset instagram45                 -> master_instagram45.mp4
  python tools/export.py master.mp4 --preset hevc45 --out film_hevc.mp4 --vmaf
  python tools/export.py master.mp4 --preset small20 --ss 30 --t 10      encode only a 10 s cut (tests)
  python tools/export.py master.mp4 --preset high100 --target-mb 80 --dry-run   print the commands only
  python tools/export.py master.mp4 --preset share                       the owner's sharing file (~3.45 Mbit/s)
  python tools/export.py master.mp4 --preset share --target-mb 50        same, but never above 50 MiB
  python tools/export.py master.mp4 --preset instagram45 --mbps 3.0      any preset at a total rate instead of a size

Presets (sizes in MiB = what Windows Explorer calls "MB"; video bitrate is computed from the duration
so the file lands ~3 % under the target, and pass 2 is re-run with a lower rate if it overshoots):
  instagram45  H.264 High@4.1, x264 veryslow, 2-pass, aq-mode 3 / 0.8, VBV 10/20 Mbit, GOP 2 s (min 0.5 s),
               1080x1920, AAC 160k.  Byte-for-byte the settings of Magic_Safari_Instagram_45MB.mp4
               (3360 kbit/s for the 103.4 s film, VMAF 91.6 vs the CRF 17 master).
  small20      H.264 High@4.0, x264 slow, 720x1280 lanczos, ref 5, aq 3 / 0.8, VBV 5/10 Mbit, AAC 128k
               (Telegram / WhatsApp sharing).
  high100      H.264 High@4.1, x264 veryslow, 1080x1920, aq 3 / 0.8, VBV 25/40 Mbit, AAC 256k (archive / YouTube).
  hevc45       HEVC Main@4.1, x265 slow, 2-pass, closed GOP 2 s, VBV 15/20 Mbit, hvc1 tag (plays on Apple
               devices / Instagram), AAC 192k, metadata stripped.
  share        = instagram45 settings at 3.45 Mbit/s TOTAL (size follows the length: 45.6 MB / 103 s and 38.4 MB /
               88.7 s were both accepted by the owner - "50 mb atrofi ... bo'lsa bo'ldi"); --target-mb caps it.
--mbps R: target size = duration x R Mbit/s (video + audio), capped by --target-mb when both are given.
All: yuv420p, BT.709 primaries/transfer/matrix + limited range tags, AAC 48 kHz stereo, +faststart.
--vmaf scores the result against the master (libvmaf, every --vmaf-subsample-th frame; a downscaled
encode is upscaled bicubic to the master size first).
"""
import argparse
import json
import math
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import FFMPEG, free_gb, run, safe_console, video_info  # noqa: E402

MIB = 1048576
COLOR = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
PRESETS = {
    "instagram45": dict(codec="x264", target_mib=45, preset="veryslow", level="4.1", audio_k=160, scale=None,
                        params="aq-mode=3:aq-strength=0.8:vbv-maxrate=10000:vbv-bufsize=20000"),
    "small20": dict(codec="x264", target_mib=20, preset="slow", level="4.0", audio_k=128, scale=(720, 1280),
                    params="ref=5:aq-mode=3:aq-strength=0.8:vbv-maxrate=5000:vbv-bufsize=10000"),
    "high100": dict(codec="x264", target_mib=100, preset="veryslow", level="4.1", audio_k=256, scale=None,
                    params="aq-mode=3:aq-strength=0.8:vbv-maxrate=25000:vbv-bufsize=40000"),
    "hevc45": dict(codec="x265", target_mib=45, preset="slow", level="41", audio_k=192, scale=None,
                   params="no-open-gop=1:vbv-maxrate=15000:vbv-bufsize=20000"),
    "share": dict(codec="x264", target_mib=None, total_mbps=3.45, preset="veryslow", level="4.1", audio_k=160,
                  scale=None, params="aq-mode=3:aq-strength=0.8:vbv-maxrate=10000:vbv-bufsize=20000"),
}


def video_kbps(target_bytes, dur, audio_k, margin):
    """Video bitrate that makes video + AAC + MP4 overhead land `margin` under the target size."""
    total_bps = target_bytes * (1 - margin) * 8 / dur
    v = (total_bps - audio_k * 1000 * 1.03) * 0.996        # AAC runs ~3 % over nominal; ~0.4 % mux overhead
    return max(100, int(math.floor(v / 1000 / 10) * 10))


def x264_cmds(src, out, p, vk, fps, threads, cut, has_audio, passlog):
    vf = "format=yuv420p" if not p["scale"] else \
        f"scale={p['scale'][0]}:{p['scale'][1]}:flags=lanczos+accurate_rnd+full_chroma_int,format=yuv420p"
    gop = f"keyint={int(round(2 * fps))}:min-keyint={max(1, int(round(fps / 2)))}"
    common = ["-c:v", "libx264", "-preset", p["preset"], "-b:v", f"{vk}k", "-profile:v", "high", "-level:v", p["level"],
              "-threads", str(threads), "-pix_fmt", "yuv420p", *COLOR,
              "-x264-params", f"threads={threads}:{gop}:{p['params']}"]
    head = [FFMPEG, "-hide_banner", "-nostats", "-nostdin", "-y", *cut, "-i", src]
    p1 = head + ["-map", "0:v:0", "-an", "-vf", vf, *common, "-pass", "1", "-passlogfile", passlog, "-f", "null", "-"]
    p2 = head + ["-map", "0:v:0"] + (["-map", "0:a:0"] if has_audio else []) + \
        ["-vf", vf, *common, "-pass", "2", "-passlogfile", passlog] + \
        (["-c:a", "aac", "-b:a", f"{p['audio_k']}k", "-ar", "48000", "-ac", "2"] if has_audio else []) + \
        ["-movflags", "+faststart", out]
    return p1, p2


def x265_cmds(src, out, p, vk, fps, threads, cut, has_audio, stats):
    vf = "format=yuv420p" if not p["scale"] else \
        f"scale={p['scale'][0]}:{p['scale'][1]}:flags=lanczos+accurate_rnd+full_chroma_int,format=yuv420p"
    xp = (f"pools={threads}:frame-threads=2:keyint={int(round(2 * fps))}:min-keyint=6:level-idc={p['level']}:"
          f"{p['params']}:colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited:repeat-headers=0")
    head = [FFMPEG, "-hide_banner", "-nostats", "-nostdin", "-y", "-threads", "1", *cut, "-i", src]
    common = ["-vf", vf, "-c:v", "libx265", "-preset", p["preset"], "-b:v", f"{vk}k", "-pix_fmt", "yuv420p",
              "-profile:v", "main", *COLOR]
    p1 = head + ["-map", "0:v:0", "-an", *common, "-x265-params", f"{xp}:pass=1:stats={stats}", "-f", "null", "-"]
    p2 = head + ["-map", "0:v:0"] + (["-map", "0:a:0"] if has_audio else []) + common + \
        ["-x265-params", f"{xp}:pass=2:stats={stats}", "-tag:v", "hvc1"] + \
        (["-c:a", "aac", "-b:a", f"{p['audio_k']}k", "-ar", "48000", "-ac", "2"] if has_audio else []) + \
        ["-map_metadata", "-1", "-map_chapters", "-1", "-movflags", "+faststart", out]
    return p1, p2


def x264_settings(path, nbytes=4_000_000):
    """The 'x264 - core ... options: ...' SEI string x264 writes into the stream (None for x265)."""
    with open(path, "rb") as f:
        data = f.read(nbytes)
    i = data.find(b"x264 - core")
    if i < 0:
        return None
    s = data[i:i + 4000]
    return s[:s.find(b"\x00")].decode("latin1")


def vmaf(dist, master, workdir, cut, subsample, threads, size):
    W, H = size
    info = video_info(dist)
    up = f",scale={W}:{H}:flags=bicubic" if (info["upright_w"], info["upright_h"]) != (W, H) else ""
    lavfi = (f"[0:v]setpts=PTS-STARTPTS{up},format=yuv420p[d];[1:v]setpts=PTS-STARTPTS,format=yuv420p[r];"
             f"[d][r]libvmaf=n_threads={threads}:n_subsample={subsample}:log_fmt=json:log_path=vmaf.json")
    run([FFMPEG, "-hide_banner", "-nostats", "-nostdin", "-i", dist, *cut, "-i", master, "-lavfi", lavfi,
         "-f", "null", "-"], cwd=workdir)
    j = json.load(open(os.path.join(workdir, "vmaf.json")))
    pm = j["pooled_metrics"]["vmaf"]
    vals = sorted(f["metrics"]["vmaf"] for f in j["frames"])
    return dict(mean=round(pm["mean"], 2), harmonic_mean=round(pm["harmonic_mean"], 2), min=round(pm["min"], 2),
                p5=round(vals[max(0, int(len(vals) * 0.05) - 1)], 2) if vals else None, frames_scored=len(vals),
                subsample=subsample, upscaled=bool(up))


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("master")
    ap.add_argument("--preset", required=True, choices=sorted(PRESETS))
    ap.add_argument("--out", help="output (default <master>_<preset>.mp4 next to the master)")
    ap.add_argument("--target-mb", type=float, help="override the preset's target size (MiB); with --mbps / share: a cap")
    ap.add_argument("--mbps", type=float, help="total rate (Mbit/s, video + audio): size = duration x rate")
    ap.add_argument("--margin", type=float, default=0.03, help="aim this fraction under the target (default 0.03)")
    ap.add_argument("--ss", type=float, help="start second (encode a cut, e.g. for tests)")
    ap.add_argument("--t", type=float, help="duration of the cut (s)")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--vmaf", action="store_true", help="score the result against the master")
    ap.add_argument("--vmaf-subsample", type=int, default=5, help="score every Nth frame (default 5)")
    ap.add_argument("--dry-run", action="store_true", help="print the ffmpeg commands and exit")
    ap.add_argument("--json", help="write a report JSON")
    a = ap.parse_args()
    p = dict(PRESETS[a.preset])
    src = os.path.abspath(a.master)
    info = video_info(src)
    dur = info["duration"] - (a.ss or 0.0)
    if a.t:
        dur = min(dur, a.t)
    mbps = a.mbps or p.get("total_mbps")
    if mbps:
        by_rate = dur * mbps * 1e6 / 8 / MIB
        p["target_mib"] = round(min(by_rate, a.target_mb) if a.target_mb else by_rate, 2)
        print(f"{dur:.2f} s x {mbps:g} Mbit/s = {by_rate:.2f} MiB" +
              (f" (capped at {a.target_mb:g} MiB)" if a.target_mb and a.target_mb < by_rate else ""))
    elif a.target_mb:
        p["target_mib"] = a.target_mb
    cut = (["-ss", f"{a.ss:.3f}"] if a.ss else []) + (["-t", f"{a.t:.3f}"] if a.t else [])
    fps = info["fps"] or 30.0
    out = os.path.abspath(a.out or os.path.splitext(src)[0] + f"_{a.preset}.mp4")
    if out == src:
        sys.exit("output would overwrite the master")
    target = p["target_mib"] * MIB
    vk = video_kbps(target, dur, p["audio_k"] if info["has_audio"] else 0, a.margin)
    work = out + ".export_tmp"
    print(f"{a.preset}: {os.path.basename(src)} {dur:.2f} s -> target {p['target_mib']:g} MiB: video {vk} kbit/s + "
          f"AAC {p['audio_k']}k ({p['codec']} {p['preset']}{', scale %dx%d' % p['scale'] if p['scale'] else ''})")
    builder = x264_cmds if p["codec"] == "x264" else x265_cmds
    logname = "pass" if p["codec"] == "x264" else "x265.stats"
    if a.dry_run:
        for c in builder(src, out, p, vk, fps, a.threads, cut, info["has_audio"], os.path.join(work, logname)):
            print(" ".join(f'"{x}"' if " " in str(x) else str(x) for x in c))
        return 0
    need = target * 1.2 / 1e9 + 0.2
    if free_gb(os.path.dirname(out)) < need:
        sys.exit(f"not enough free disk on the output drive (need ~{need:.1f} GB)")
    os.makedirs(work, exist_ok=True)
    rep = dict(preset=a.preset, master=src, out=out, duration=round(dur, 3), target_mib=p["target_mib"],
               total_mbps=mbps)
    try:
        t0 = time.time()
        stats = os.path.join(work, logname) if p["codec"] == "x264" else logname
        p1, p2 = builder(src, out, p, vk, fps, a.threads, cut, info["has_audio"], stats)
        run(p1, cwd=work)
        t1 = time.time()
        for attempt in range(3):
            run(p2, cwd=work)
            size = os.path.getsize(out)
            if size <= target:
                break
            vk = int(math.floor(vk * (target * (1 - a.margin)) / size / 10) * 10)
            print(f"  {size / MIB:.2f} MiB > {p['target_mib']:g} MiB: pass 2 again at {vk} kbit/s")
            _, p2 = builder(src, out, p, vk, fps, a.threads, cut, info["has_audio"], stats)
        t2 = time.time()
        size = os.path.getsize(out)
        oi = video_info(out)
        rep.update(bytes=size, mib=round(size / MIB, 2), mb=round(size / 1e6, 2), video_kbps=vk,
                   size_ok=size <= target, codec=oi["codec"], resolution=f"{oi['w']}x{oi['h']}",
                   pass1_s=round(t1 - t0, 1), pass2_s=round(t2 - t1, 1))
        sei = x264_settings(out)
        if sei:
            rep["x264_options"] = sei.split("options: ", 1)[-1]
        print(f"  -> {out}\n     {size / MIB:.2f} MiB ({size / 1e6:.2f} MB) {'OK' if size <= target else 'OVER TARGET'} | "
              f"{oi['codec']} {oi['w']}x{oi['h']} | video {vk} kbit/s | pass 1 {t1 - t0:.0f} s, pass 2 {t2 - t1:.0f} s")
        if a.vmaf:
            tv = time.time()
            rep["vmaf"] = vmaf(out, src, work, cut, a.vmaf_subsample, a.threads, (info["upright_w"], info["upright_h"]))
            v = rep["vmaf"]
            print(f"     VMAF mean {v['mean']} (harmonic {v['harmonic_mean']}, p5 {v['p5']}, min {v['min']}; "
                  f"{v['frames_scored']} frames, every {v['subsample']}th{', upscaled' if v['upscaled'] else ''}) "
                  f"in {time.time() - tv:.0f} s")
    finally:
        shutil.rmtree(work, ignore_errors=True)
        for f in ("x264_2pass.log", "x264_2pass.log.mbtree"):
            if os.path.exists(f):
                os.remove(f)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2)
    return 0 if rep.get("size_ok") else 1


if __name__ == "__main__":
    sys.exit(main())

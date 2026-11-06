"""Create synthetic test inputs for the engine test EDL (test_edl.json) - no real footage needed.

  python test/make_test_media.py                  -> test/media/
  python test/make_test_media.py --out D:/tmp/m   -> another folder (then render with --video-dir/
                                                     --photo-dir/--music-dir pointing there)
  python test/make_test_media.py --heic IMG.HEIC  -> use a real iPhone HEIC as the test photo
                                                     (keeps its Display-P3 ICC, so the engine's
                                                     colour-management path is exercised)

Writes (all small, ~25 MB total):
  clip_land.mp4      1920x1080 60 fps 14 s, moving test pattern + 1 kHz beeps (landscape iPhone-like)
  clip_portrait.mov  coded 1920x1080 with a -90 deg display-rotation tag -> upright 1080x1920, 8 s
                     (exactly how iPhones store portrait video)
  clip_shaky.mp4     1920x1080 60 fps 14 s, test pattern with simulated hand shake (stabilisation)
  test_photo.jpg     3024x4032 synthetic photo (sRGB ICC), or the converted --heic
  music_bed_test.wav 75 s, 100 BPM synthetic bed (kick on beats, chords per bar), -16 LUFS
  music_rubato_test.wav 48 s 'live' track (plucks, bars drifting 2.6-3.35 s) + .json with the true bars
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from audio import write_wav_f32, lufs, SR  # noqa: E402
from common import FFMPEG  # noqa: E402

X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
AAC = ["-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]


def _ff(args):
    subprocess.run([FFMPEG, "-nostdin", "-hide_banner", "-v", "error", "-y"] + args, check=True)


def _beeps(seconds, freq):
    # beep every second + a little pink noise so loudness measurement is meaningful
    return ["-f", "lavfi", "-i", f"sine=frequency={freq}:beep_factor=3:sample_rate=48000:duration={seconds}",
            "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.04:sample_rate=48000:duration={seconds}"]


def make_videos(out):
    # landscape, moving pattern
    p = os.path.join(out, "clip_land.mp4")
    _ff(["-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=60:duration=14"] + _beeps(14, 1000) +
        ["-filter_complex", "[1:a][2:a]amix=inputs=2:normalize=0[a]", "-map", "0:v", "-map", "[a]"] + X264 + AAC + [p])
    print("video", p)
    # portrait: render upright 1080x1920, store it rotated CCW and tag it -90 (= iPhone portrait)
    tmp = os.path.join(out, "_coded_tmp.mp4")
    _ff(["-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=60:duration=8"] + _beeps(8, 660) +
        ["-filter_complex", "[0:v]transpose=cclock[v];[1:a][2:a]amix=inputs=2:normalize=0[a]",
         "-map", "[v]", "-map", "[a]"] + X264 + AAC + [tmp])
    p = os.path.join(out, "clip_portrait.mov")
    _ff(["-display_rotation:v:0", "-90", "-i", tmp, "-c", "copy", p])
    os.remove(tmp)
    print("video", p, "(rotation tag -90 -> upright 1080x1920)")
    # hand-held shake: a crop window wobbling over a larger pattern (several frequencies)
    p = os.path.join(out, "clip_shaky.mp4")
    shake = ("crop=1920:1080:"
             "96+38*sin(2*PI*t*1.3)+16*sin(2*PI*t*4.7+1):"
             "54+26*sin(2*PI*t*1.7+2)+11*sin(2*PI*t*5.3)")
    _ff(["-f", "lavfi", "-i", "testsrc2=size=2112x1188:rate=60:duration=14"] + _beeps(14, 440) +
        ["-filter_complex", f"[0:v]{shake}[v];[1:a][2:a]amix=inputs=2:normalize=0[a]",
         "-map", "[v]", "-map", "[a]"] + X264 + AAC + [p])
    print("video", p)


def synthetic_photo(dst, W=3024, H=4032):
    """Portrait 'photo' with fine detail everywhere (so Ken Burns jitter is measurable)."""
    from PIL import Image, ImageCms, ImageDraw
    rng = np.random.default_rng(3)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.stack([90 + 80 * np.sin(x / 400.0) + 40 * (y / H),
                    110 + 60 * np.cos(y / 520.0),
                    140 + 70 * np.sin((x + y) / 700.0)], -1)
    del x, y
    img += rng.normal(0, 6, img.shape).astype(np.float32)          # grain = trackable texture
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    del img
    d = ImageDraw.Draw(im)
    for _ in range(260):
        cx, cy, r = int(rng.integers(0, W)), int(rng.integers(0, H)), int(rng.integers(20, 160))
        col = tuple(int(c) for c in rng.integers(30, 250, 3))
        if rng.random() < 0.5:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col, outline=(20, 20, 20), width=6)
        else:
            d.rectangle([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=col, outline=(250, 250, 250), width=5)
    for gx in range(0, W, 252):
        d.line([(gx, 0), (gx, H)], fill=(255, 255, 255), width=2)
    for gy in range(0, H, 252):
        d.line([(0, gy), (W, gy)], fill=(255, 255, 255), width=2)
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    im.save(dst, quality=92, icc_profile=srgb, subsampling=0)
    print("photo", dst, im.size, "synthetic (sRGB ICC)")


def heic_to_jpg(src, dst):
    import pillow_heif
    from PIL import Image, ImageOps
    pillow_heif.register_heif_opener()
    im = Image.open(src)
    icc = im.info.get("icc_profile")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.save(dst, quality=95, icc_profile=icc, subsampling=0)
    print("photo", dst, im.size, "ICC" if icc else "no ICC")


def music_bed(dst, seconds=75, bpm=100):
    rng = np.random.default_rng(7)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    beat = 60.0 / bpm
    out = np.zeros((n, 2), np.float64)
    # pad: I-V-vi-IV in C major, soft saw-ish chords with slow attack
    chords = [[261.63, 329.63, 392.00], [196.00, 246.94, 293.66], [220.00, 261.63, 329.63], [174.61, 220.00, 261.63]]
    bar = 4 * beat
    for i in range(int(seconds / bar) + 1):
        a, b = int(i * bar * SR), min(n, int((i + 1) * bar * SR))
        if a >= n:
            break
        tt = t[a:b] - t[a]
        env = np.minimum(1, tt / 0.4) * np.minimum(1, (bar - tt) / 0.3)
        for f in chords[i % 4]:
            for h, amp in ((1, 1.0), (2, 0.35), (3, 0.15)):
                ph = rng.uniform(0, 6.28)
                out[a:b, 0] += 0.045 * amp * env * np.sin(2 * np.pi * f * h * tt + ph)
                out[a:b, 1] += 0.045 * amp * env * np.sin(2 * np.pi * f * h * 1.002 * tt + ph)
    # kick on every beat, hat on off-beats
    nb = int(seconds / beat)
    for k in range(nb):
        s = int(k * beat * SR)
        L = int(0.25 * SR)
        e = min(n, s + L)
        tt = np.arange(e - s) / SR
        kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
        out[s:e] += 0.55 * kick[:, None]
        hs = int((k + 0.5) * beat * SR)
        he = min(n, hs + int(0.05 * SR))
        if hs < n:
            hat = rng.standard_normal(he - hs) * np.exp(-np.arange(he - hs) / SR * 90)
            hat = np.diff(np.concatenate([[0], hat]))
            out[hs:he, 0] += 0.10 * hat
            out[hs:he, 1] += 0.08 * hat
    out = out.astype(np.float32)
    g = 10 ** ((-16 - lufs(out)) / 20)
    write_wav_f32(dst, out * g)
    print("music", dst, f"{seconds}s @ {bpm} BPM, {lufs(out * g):.1f} LUFS")


def rubato_bed(dst, seconds=48):
    """A 'live' (rubato) track: no click - plucked notes on every beat (a bass pluck on the downbeat), a pad
    that changes chord every bar, bar lengths drifting smoothly between ~2.6 and ~3.35 s (like the koto piece
    Senbazuru, whose bars measured 2.67-3.32 s).  The true bar starts go to <dst>.json (test truth)."""
    rng = np.random.default_rng(11)
    n = int(seconds * SR)
    out = np.zeros((n, 2), np.float64)
    bars, t, k = [], 0.5, 0
    while t < seconds - 1.0:
        bars.append(round(t, 4))
        t += 2.97 + 0.33 * np.sin(k * 0.9) + rng.uniform(-0.05, 0.05)
        k += 1
    chords = [[220.00, 261.63, 329.63], [174.61, 220.00, 261.63], [196.00, 246.94, 293.66], [164.81, 196.00, 246.94]]
    scale = [329.63, 392.00, 440.00, 493.88, 587.33, 659.25]
    for i, b0 in enumerate(bars):
        b1 = bars[i + 1] if i + 1 < len(bars) else min(seconds, b0 + 3.0)
        a, e = int(b0 * SR), min(n, int(b1 * SR))
        tt = np.arange(e - a) / SR
        env = np.minimum(1, tt / 0.3) * np.minimum(1, (b1 - b0 - tt) / 0.3)
        for f in chords[i % 4]:
            out[a:e, 0] += 0.03 * env * np.sin(2 * np.pi * f * tt)
            out[a:e, 1] += 0.03 * env * np.sin(2 * np.pi * f * 1.003 * tt)
        for j in range(4):                       # plucks on the 4 beats of this bar
            s = int((b0 + j * (b1 - b0) / 4) * SR)
            L = min(n - s, int(0.6 * SR))
            if L <= 0:
                continue
            tp = np.arange(L) / SR
            f = 110.0 if j == 0 else scale[rng.integers(len(scale))]
            pl = sum(np.sin(2 * np.pi * f * h * tp) / h for h in (1, 2, 3)) * np.exp(-tp * (6 if j == 0 else 9))
            amp = 0.55 if j == 0 else 0.28
            out[s:s + L, 0] += amp * pl
            out[s:s + L, 1] += amp * 0.9 * pl
    out = out.astype(np.float32)
    g = 10 ** ((-16 - lufs(out)) / 20)
    write_wav_f32(dst, out * g)
    with open(os.path.splitext(dst)[0] + ".json", "w") as f:
        json.dump({"bar_starts": bars, "note": "synthetic rubato test track: true bar lines (s)"}, f)
    print("music", dst, f"{seconds}s rubato, {len(bars)} bars {min(np.diff(bars)):.2f}-{max(np.diff(bars)):.2f} s")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, "media"), help="output folder (default test/media)")
    ap.add_argument("--heic", help="convert this HEIC as the test photo instead of the synthetic one")
    ap.add_argument("--skip-video", action="store_true", help="only (re)make the photo and the music")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if not shutil.which(FFMPEG) and not os.path.exists(FFMPEG):
        sys.exit("ffmpeg not found on PATH")
    if not a.skip_video:
        make_videos(a.out)
    photo = os.path.join(a.out, "test_photo.jpg")
    heic_to_jpg(a.heic, photo) if a.heic else synthetic_photo(photo)
    music_bed(os.path.join(a.out, "music_bed_test.wav"))
    rubato_bed(os.path.join(a.out, "music_rubato_test.wav"))


if __name__ == "__main__":
    main()

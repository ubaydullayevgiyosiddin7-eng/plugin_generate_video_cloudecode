"""Render the title style with several candidate fonts over a background frame -> font_sheet.jpg

  python test/font_sheet.py [--bg VIDEO_OR_IMAGE] [--t 5.2] [--text "My Title"] [--sub "Subtitle"]
                            [--fonts A.ttf,B.ttf:800,...] [--out test/out/font_sheet.jpg]
Default background: test/media/clip_land.mp4 (make_test_media.py).  Any of your clips/photos works.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from common import FFMPEG, YUV2RGB, run  # noqa: E402
import textfx  # noqa: E402

CANDS = "LilitaOne-Regular.ttf,TitanOne-Regular.ttf,LuckiestGuy-Regular.ttf,Bungee-Regular.ttf,Baloo2[wght].ttf:800," \
        "Chewy-Regular.ttf,BowlbyOne-Regular.ttf,Fredoka[wdth,wght].ttf:700,Pacifico-Regular.ttf"


def background(src, t, tmp):
    """1080x1920 RGB array: centre 9:16 crop of a video frame / image."""
    vf = f"crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=1080:1920:{YUV2RGB.replace('flags=', 'flags=lanczos+')},format=rgb24"
    cmd = [FFMPEG, "-v", "error", "-y"]
    if not src.lower().endswith((".jpg", ".jpeg", ".png")):
        cmd += ["-ss", str(t)]
    run(cmd + ["-i", src, "-frames:v", "1", "-vf", vf, tmp])
    bg = np.asarray(Image.open(tmp).convert("RGB"))
    os.remove(tmp)
    return bg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bg", default=os.path.join(HERE, "media", "clip_land.mp4"))
    ap.add_argument("--t", type=float, default=5.2, help="time of the background frame (video)")
    ap.add_argument("--text", default="Magic Safari")
    ap.add_argument("--sub", default="Oilaviy sayohat · 03.10.2026")
    ap.add_argument("--fonts", default=CANDS, help="comma list of font files in engine/fonts, optional :weight")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "font_sheet.jpg"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    bg = background(a.bg, a.t, os.path.abspath(a.out) + ".bg.png")
    tiles = []
    for c in a.fonts.split(","):
        font, _, wt = c.partition(":")
        fr = bg.copy()
        spec = dict(text=a.text, style="title", start=0, end=6, font=font)
        if wt:
            spec["weight"] = int(wt)
        sub = dict(text=a.sub, style="subtitle", start=0, end=6)
        tr = textfx.TextRenderer([spec, sub], 1080, 1920, 30)
        tr.apply(fr, 75)  # 2.5 s: after the pop-in, sparkles active
        im = Image.fromarray(fr[300:1000]).resize((540, 350), Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 6), font, fill="white")
        tiles.append(im)
    cols = 3
    sheet = Image.new("RGB", (540 * cols, 350 * ((len(tiles) + cols - 1) // cols)))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 540, (i // cols) * 350))
    sheet.save(a.out, quality=90)
    print(a.out)


if __name__ == "__main__":
    main()

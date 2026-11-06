"""Grade preset comparison: the same frames through every preset's LUT (exactly the engine's path:
rgb48 -> lut3d tetrahedral) -> grade_compare.jpg (rows = shots, columns = presets).

  python test/grade_sheet.py [SHOT ...] [--out test/out/grade_compare.jpg]
  SHOT = path[@seconds][#cx]   e.g.  D:/clips/IMG_1.MOV@2.5#0.45   photo.jpg#0.5
Default shots: the make_test_media.py clips/photo in test/media.
"""
import argparse
import os
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from common import FFMPEG, YUV2RGB, run  # noqa: E402
from grade import write_cube  # noqa: E402

M = os.path.join(HERE, "media")
DEFAULT = [os.path.join(M, "clip_land.mp4") + "@2.5#0.45", os.path.join(M, "clip_portrait.mov") + "@3#0.5",
           os.path.join(M, "test_photo.jpg") + "#0.5"]
PRE = ["none", "natural", "warm_pop", "cinematic_soft"]
TW, TH = 300, 533


def parse(shot):
    path, cx = shot, 0.5
    if "#" in path:
        path, c = path.rsplit("#", 1)
        cx = float(c)
    t = None
    if "@" in os.path.basename(path):
        path, tt = path.rsplit("@", 1)
        t = float(tt)
    return os.path.splitext(os.path.basename(path))[0], path, t, cx


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shots", nargs="*", default=DEFAULT)
    ap.add_argument("--out", default=os.path.join(HERE, "out", "grade_compare.jpg"))
    a = ap.parse_args()
    work = tempfile.mkdtemp(prefix="grade_", dir=os.path.dirname(os.path.abspath(a.out)) if
                            os.path.isdir(os.path.dirname(os.path.abspath(a.out))) else None)
    try:
        for p in PRE:
            write_cube(os.path.join(work, f"{p}.cube"), p)
        rows = []
        for i, shot in enumerate(a.shots):
            name, src, t, cx = parse(shot)
            base = os.path.join(work, f"s{i}_src.png")
            crop = f"crop=ih*9/16:ih:(iw-ih*9/16)*{cx}:0"
            if t is None:
                run([FFMPEG, "-v", "error", "-y", "-i", src, "-vf", f"{crop},scale={TW}:{TH}:flags=area,format=rgb24", base])
            else:
                run([FFMPEG, "-v", "error", "-y", "-ss", str(t), "-i", src, "-frames:v", "1", "-vf",
                     f"{crop},scale={TW}:{TH}:{YUV2RGB.replace('flags=', 'flags=area+')},format=rgb24", base])
            row = []
            for p in PRE:
                o = f"s{i}_{p}.png"
                run([FFMPEG, "-v", "error", "-y", "-i", os.path.basename(base), "-vf",
                     f"format=rgb48le,lut3d=file={p}.cube:interp=tetrahedral,format=rgb24", o], cwd=work)
                row.append(Image.open(os.path.join(work, o)).convert("RGB"))
            rows.append((name, row))
        sheet = Image.new("RGB", (TW * len(PRE), 24 + TH * len(rows)), (16, 16, 16))
        d = ImageDraw.Draw(sheet)
        for j, p in enumerate(PRE):
            d.text((j * TW + 8, 6), p, fill=(255, 220, 80))
        for i, (name, row) in enumerate(rows):
            for j, im in enumerate(row):
                sheet.paste(im, (j * TW, 24 + i * TH))
            d.text((6, 24 + i * TH + 6), name, fill=(255, 255, 255))
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        sheet.save(a.out, quality=90)
        print(a.out)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()

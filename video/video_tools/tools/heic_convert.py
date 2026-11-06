"""Convert iPhone photos (HEIC, also JPG/PNG) into upright sRGB JPGs ready for the engine.

  python tools/heic_convert.py D:/footage D:/project/photos
  python tools/heic_convert.py IN OUT --prefer original          use IMG_1234 even when IMG_E1234 exists
  python tools/heic_convert.py IN OUT --original-for 4454,4455   per-photo exceptions to --prefer edited
  python tools/heic_convert.py IN OUT --keep-mirror              keep front-camera selfies mirrored
  python tools/heic_convert.py IN OUT --max-side 0 --only 4349,4353

What it does (the Magic Safari photo pipeline):
  * iPhone edited versions: IMG_E1234.HEIC is used instead of IMG_1234.HEIC by default (--prefer
    original to switch); the output is always named after the original: IMG_1234.jpg.
  * pixels made upright (HEIF irot/imir via libheif, EXIF orientation for JPG/PNG) and the EXIF
    orientation tag is reset to 1, so nothing downstream rotates twice.
  * colour: embedded ICC (iPhone = Display P3) -> sRGB (relative colorimetric); sRGB ICC embedded.
  * front-camera selfies (EXIF LensModel contains "front", read from the ORIGINAL file) are stored
    mirrored by the iPhone; they are un-mirrored by default (--keep-mirror to keep them as shot).
  * long side limited to --max-side px (default 3840; 0 = keep), JPEG q92 4:4:4.
  * minimal EXIF kept: Make, Model, capture time.  convert_meta.json records every decision.
The input folder is only read.  .AAE sidecars and videos are ignored.
"""
import argparse
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import safe_console  # noqa: E402

IN_EXT = (".heic", ".heif", ".jpg", ".jpeg", ".png")
EDIT_RE = re.compile(r"^(?P<pre>[A-Za-z]+_)E(?P<num>\d+)$")
ORIG_RE = re.compile(r"^(?P<pre>[A-Za-z]+_)(?P<num>\d+)$")


def _open(path):
    """-> (PIL RGB image upright, icc bytes|None, Exif)"""
    from PIL import Image, ImageOps
    ext = os.path.splitext(path)[1].lower()
    if ext in (".heic", ".heif"):
        from pillow_heif import open_heif
        h = open_heif(path)            # libheif applies the HEIF transforms (irot/imir) -> upright pixels
        im = h.to_pillow()
        icc = h.info.get("icc_profile")
        ex = Image.Exif()
        if h.info.get("exif"):
            try:
                ex.load(h.info["exif"])
            except Exception:
                pass
        return im.convert("RGB"), icc, ex
    im = Image.open(path)
    ex = im.getexif()
    icc = im.info.get("icc_profile")
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB"), icc, ex


def _exif_only(path):
    from PIL import Image
    try:
        if path.lower().endswith((".heic", ".heif")):
            from pillow_heif import open_heif
            h = open_heif(path)
            ex = Image.Exif()
            if h.info.get("exif"):
                ex.load(h.info["exif"])
            return ex
        return Image.open(path).getexif()
    except Exception:
        return Image.Exif()


def _sub(ex):
    try:
        return ex.get_ifd(0x8769)
    except Exception:
        return {}


def convert_one(job):
    from PIL import Image, ImageCms, ImageOps
    src, orig, dst, args = job["src"], job["orig"], job["dst"], job["args"]
    t0 = time.time()
    im, icc, ex = _open(src)
    note = "no ICC (assumed sRGB)"
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    if icc:
        try:
            prof = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            desc = ImageCms.getProfileDescription(prof).strip()
            if "srgb" in desc.lower():
                note = f"ICC '{desc}' (kept)"
            else:
                im = ImageCms.profileToProfile(im, prof, srgb, renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
                                               outputMode="RGB")
                note = f"ICC '{desc}' -> sRGB"
        except Exception as e:
            note = f"ICC unreadable ({e}); pixels kept"
    ex0 = _exif_only(orig) if orig != src else ex   # lens info from the ORIGINAL capture
    sub0 = _sub(ex0)
    lens = str(sub0.get(0xA434, "") or "")
    front = "front" in lens.lower()
    mirrored_fix = False
    if front and not args["keep_mirror"]:
        im = ImageOps.mirror(im)
        mirrored_fix = True
    W, H = im.size
    ms = args["max_side"]
    if ms and max(W, H) > ms:
        s = ms / max(W, H)
        im = im.resize((round(W * s), round(H * s)), Image.LANCZOS)
    out_ex = Image.Exif()
    out_ex[274] = 1
    for tag in (271, 272):
        if ex0.get(tag):
            out_ex[tag] = ex0.get(tag)
    when = sub0.get(0x9003) or ex0.get(306)
    if when:
        out_ex[306] = when
    tmp = dst + ".tmp.jpg"
    im.save(tmp, "JPEG", quality=args["quality"], icc_profile=srgb.tobytes(), exif=out_ex.tobytes(), subsampling=0)
    os.replace(tmp, dst)
    return dict(out=os.path.basename(dst), source=os.path.basename(src), original=os.path.basename(orig),
                version=job["version"], has_edit=job["has_edit"], front_camera=front, unmirrored=mirrored_fix,
                lens=lens or None, w=im.width, h=im.height, time=str(when) if when else None, color=note,
                seconds=round(time.time() - t0, 2))


def plan(in_dir, out_dir, args):
    files = sorted(f for f in os.listdir(in_dir) if f.lower().endswith(IN_EXT))
    by_stem = {}
    for f in files:
        by_stem.setdefault(os.path.splitext(f)[0], f)   # HEIC sorts before JPG for the same stem
    keep_orig = {s.strip() for s in (args.original_for or "").split(",") if s.strip()}
    only = {s.strip() for s in (args.only or "").split(",") if s.strip()}
    jobs, seen = [], set()
    for stem, f in by_stem.items():
        m = EDIT_RE.match(stem)
        if m:
            base = m.group("pre") + m.group("num")
            if base in by_stem:
                continue                        # handled with its original
            num, out_stem, orig, edit = m.group("num"), base, f, f   # edit without original
        else:
            mo = ORIG_RE.match(stem)
            num = mo.group("num") if mo else stem
            out_stem = stem
            orig = f
            edit = by_stem.get(mo.group("pre") + "E" + mo.group("num")) if mo else None
        if only and not any(o == num or o in stem for o in only):
            continue
        use_edit = edit is not None and edit != orig and args.prefer == "edited" and num not in keep_orig
        src = edit if (use_edit or (edit == orig)) else orig
        version = "edited" if src != orig or EDIT_RE.match(os.path.splitext(src)[0]) else "original"
        dst = os.path.join(out_dir, out_stem + ".jpg")
        if out_stem in seen:
            continue
        seen.add(out_stem)
        jobs.append(dict(src=os.path.join(in_dir, src), orig=os.path.join(in_dir, orig), dst=dst, version=version,
                         has_edit=bool(edit and edit != orig)))
    return jobs


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_folder")
    ap.add_argument("out_folder")
    ap.add_argument("--prefer", choices=["edited", "original"], default="edited",
                    help="which iPhone version to use when IMG_E#### exists (default edited)")
    ap.add_argument("--original-for", help="comma list of photo numbers that use the original anyway (e.g. 4454,4455)")
    ap.add_argument("--keep-mirror", action="store_true", help="do NOT un-mirror front-camera selfies")
    ap.add_argument("--max-side", type=int, default=3840, help="limit the long side in px (default 3840; 0 = keep)")
    ap.add_argument("--quality", type=int, default=92)
    ap.add_argument("--only", help="comma list of photo numbers / name parts to convert")
    ap.add_argument("--overwrite", action="store_true", help="re-convert even if the JPG exists")
    ap.add_argument("--jobs", type=int, default=2, help="parallel conversions (default 2; ~0.3 GB RAM each)")
    a = ap.parse_args()
    in_dir, out_dir = os.path.abspath(a.in_folder), os.path.abspath(a.out_folder)
    if in_dir == out_dir:
        sys.exit("out_folder must differ from in_folder")
    os.makedirs(out_dir, exist_ok=True)
    jobs = plan(in_dir, out_dir, a)
    todo = [j for j in jobs if a.overwrite or not os.path.exists(j["dst"])]
    for j in todo:
        j["args"] = dict(keep_mirror=a.keep_mirror, max_side=a.max_side, quality=a.quality)
    print(f"{len(jobs)} photo(s), {len(jobs) - len(todo)} already converted, converting {len(todo)} -> {out_dir}")
    meta_path = os.path.join(out_dir, "convert_meta.json")
    meta = {}
    if os.path.exists(meta_path):
        try:
            meta = json.load(open(meta_path, encoding="utf-8"))
        except Exception:
            meta = {}
    errors = 0
    if todo:
        if a.jobs > 1 and len(todo) > 1:
            with ProcessPoolExecutor(max_workers=a.jobs) as ex:
                futs = [(j, ex.submit(convert_one, j)) for j in todo]
                results = []
                for j, fu in futs:
                    try:
                        results.append(fu.result())
                    except Exception as e:
                        results.append(dict(out=os.path.basename(j["dst"]), error=str(e)))
        else:
            results = []
            for j in todo:
                try:
                    results.append(convert_one(j))
                except Exception as e:
                    results.append(dict(out=os.path.basename(j["dst"]), error=str(e)))
        for r in results:
            if r.get("error"):
                errors += 1
                print(f"  {r['out']}: ERROR {r['error']}")
                continue
            meta[os.path.splitext(r["out"])[0]] = r
            flags = [r["version"]] + (["FRONT un-mirrored"] if r["unmirrored"] else
                                      ["front (kept mirrored)"] if r["front_camera"] else [])
            print(f"  {r['out']:<16} <- {r['source']:<16} {r['w']}x{r['h']}  {' '.join(flags)}  {r['color']}")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=1, ensure_ascii=False)
    print(f"done ({errors} error(s)); decisions in {meta_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

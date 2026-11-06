"""Inventory a footage folder (iPhone MOV/HEIC dumps etc.) before editing.

  python tools/probe_media.py D:/footage                    table + probe_<folder>.json in the CWD
  python tools/probe_media.py D:/footage --json out.json    JSON elsewhere
  python tools/probe_media.py D:/footage --json -           JSON to stdout instead of the table
  python tools/probe_media.py D:/footage --decode full      fully decode every video (slow, thorough)

Per video: duration, fps, coded size, rotation tag, orientation after autorotate, has_audio,
codec, HDR transfer, capture time; junk flags: too short (< --min-dur, default 1 s), unreadable,
decode errors (quick check = first and last second decoded; --decode full = whole file).
Per photo: format, upright size/orientation, iPhone edited pair (IMG_E1234 <-> IMG_1234),
front camera (stored mirrored), capture time.  .AAE sidecars (iOS edit recipes) are flagged junk.
Live-Photo companion clips (MOV with the same name as a photo) are noted.
Totals: count, size, video minutes, portrait vs landscape.  The folder is only read, never written.
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import (FFMPEG, PHOTO_EXT, VIDEO_EXT, orientation, run, safe_console, video_info)  # noqa: E402

SIDECAR_EXT = (".aae", ".xmp", ".thm", ".lrf", ".ds_store", ".ini", ".db")
EDIT_RE = re.compile(r"^(IMG_)E(\d+)$", re.I)


def decode_errors(path, dur, mode):
    if mode == "none":
        return []
    if mode == "full":
        spans = [[]]
    else:  # quick: first and last second
        spans = [["-t", "1"]]
        if dur > 2.5:
            spans.append(["-ss", f"{max(0.0, dur - 1.2):.3f}"])
    errs = []
    for sp in spans:
        cmd = [FFMPEG, "-nostdin", "-hide_banner", "-v", "error", "-xerror"] + \
              (sp if sp[:1] == ["-ss"] else []) + ["-i", path] + (sp if sp[:1] == ["-t"] else []) + \
              ["-map", "0:v:0", "-f", "null", "-"]
        p = run(cmd, check=False, text=True)
        msg = (p.stderr or "").strip()
        if p.returncode != 0 or msg:
            errs.append(msg.splitlines()[0][:160] if msg else f"exit {p.returncode}")
    return errs


def probe_video(path, args):
    rec = {"file": os.path.basename(path), "kind": "video", "bytes": os.path.getsize(path), "junk": [], "notes": []}
    try:
        info = video_info(path)
    except Exception as e:
        rec["junk"].append("unreadable")
        rec["error"] = str(e).splitlines()[0][:200]
        return rec
    tags = (info["raw"].get("format", {}).get("tags") or {})
    created = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
    rec.update(duration=round(info["duration"], 3), fps=info["fps"], avg_fps=info["avg_fps"],
               coded=f"{info['w']}x{info['h']}", rotation=info["rotation"],
               upright=f"{info['upright_w']}x{info['upright_h']}",
               orientation=orientation(info["upright_w"], info["upright_h"]),
               codec=info["codec"], pix_fmt=info["pix_fmt"], transfer=info["transfer"],
               has_audio=info["has_audio"], created=created,
               model=tags.get("com.apple.quicktime.model"))
    if info["transfer"] in ("arib-std-b67", "smpte2084"):
        rec["notes"].append("HDR " + ("HLG" if info["transfer"] == "arib-std-b67" else "PQ"))
    if info["duration"] < args.min_dur:
        rec["junk"].append(f"short<{args.min_dur:g}s")
    if not info["has_audio"]:
        rec["notes"].append("no audio")
    errs = decode_errors(path, info["duration"], args.decode)
    if errs:
        rec["junk"].append("decode_errors")
        rec["decode_errors"] = errs
    return rec


def _exif_photo(path):
    """(width, height upright, exif dict-ish) without decoding pixels."""
    from PIL import Image
    ext = os.path.splitext(path)[1].lower()
    if ext in (".heic", ".heif"):
        import pillow_heif
        h = pillow_heif.open_heif(path)  # lazy; libheif applies irot/imir -> size is upright
        w, hh = h.size
        ex = Image.Exif()
        if h.info.get("exif"):
            try:
                ex.load(h.info["exif"])
            except Exception:
                pass
        return w, hh, ex, bool(h.info.get("icc_profile")), "HEIC"
    im = Image.open(path)
    w, hh = im.size
    ex = im.getexif()
    if ex.get(274) in (5, 6, 7, 8):
        w, hh = hh, w
    return w, hh, ex, bool(im.info.get("icc_profile")), (im.format or ext[1:].upper())


def probe_photo(path, names):
    stem, ext = os.path.splitext(os.path.basename(path))
    rec = {"file": os.path.basename(path), "kind": "photo", "bytes": os.path.getsize(path), "junk": [], "notes": []}
    try:
        w, h, ex, icc, fmt = _exif_photo(path)
    except Exception as e:
        rec["junk"].append("unreadable")
        rec["error"] = str(e)[:200]
        return rec
    sub = {}
    try:
        sub = ex.get_ifd(0x8769)
    except Exception:
        pass
    lens = str(sub.get(0xA434, "") or "")
    rec.update(format=fmt, size=f"{w}x{h}", orientation=orientation(w, h), icc=icc,
               created=str(sub.get(0x9003) or ex.get(306) or "") or None, lens=lens or None,
               front_camera="front" in lens.lower())
    m = EDIT_RE.match(stem)
    if m:
        orig = f"{m.group(1)}{m.group(2)}"
        rec["edited_version_of"] = orig if orig.lower() in names else None
        rec["notes"].append("iPhone edited version" + ("" if rec["edited_version_of"] else " (original missing)"))
    else:
        m2 = re.match(r"^(IMG_)(\d+)$", stem, re.I)
        if m2:
            e = f"{m2.group(1)}E{m2.group(2)}"
            if e.lower() in names:
                rec["edited_version"] = next(n for n in names.values() if os.path.splitext(n)[0].lower() == e.lower()
                                             and os.path.splitext(n)[1].lower() in PHOTO_EXT)
    if rec["front_camera"]:
        rec["notes"].append("front camera (stored mirrored)")
    return rec


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--json", help="JSON output path ('-' = stdout instead of the table; default probe_<folder>.json in the CWD)")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--decode", choices=["quick", "full", "none"], default="quick",
                    help="decode-error check: first/last second (default), whole file, or skip")
    ap.add_argument("--min-dur", type=float, default=1.0, help="videos shorter than this are junk (s)")
    ap.add_argument("--jobs", type=int, default=4, help="parallel probes (default 4)")
    args = ap.parse_args()
    root = os.path.abspath(args.folder)
    if not os.path.isdir(root):
        sys.exit(f"not a folder: {root}")
    files = []
    for dp, dn, fn in os.walk(root):
        files += [os.path.join(dp, f) for f in sorted(fn)]
        if not args.recursive:
            break
    names = {os.path.splitext(os.path.basename(f))[0].lower(): os.path.basename(f) for f in files}
    stems_photo = {os.path.splitext(os.path.basename(f))[0].lower() for f in files
                   if f.lower().endswith(PHOTO_EXT)}
    vids = [f for f in files if f.lower().endswith(VIDEO_EXT)]
    phos = [f for f in files if f.lower().endswith(PHOTO_EXT)]
    side = [f for f in files if f.lower().endswith(SIDECAR_EXT) or os.path.basename(f).startswith("._")]
    other = [f for f in files if f not in vids and f not in phos and f not in side]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        vrec = list(ex.map(lambda f: probe_video(f, args), vids))
        prec = list(ex.map(lambda f: probe_photo(f, names), phos))
    for f, r in zip(vids, vrec):
        if os.path.splitext(os.path.basename(f))[0].lower() in stems_photo:
            r["notes"].append("Live-Photo companion clip")
        if args.recursive:
            r["file"] = os.path.relpath(f, root)
    junk = [dict(file=os.path.relpath(f, root), kind="sidecar", bytes=os.path.getsize(f),
                 reason="iOS edit sidecar (.AAE)" if f.lower().endswith(".aae") else "sidecar/system file")
            for f in side]
    junk += [dict(file=r["file"], kind=r["kind"], bytes=r["bytes"], reason=", ".join(r["junk"]))
             for r in vrec + prec if r["junk"]]
    good_v = [r for r in vrec if not r["junk"]]
    orient = {}
    for r in vrec + prec:
        if r.get("orientation"):
            k = f"{r['kind']}_{r['orientation']}"
            orient[k] = orient.get(k, 0) + 1
    totals = dict(files=len(files), bytes=sum(os.path.getsize(f) for f in files),
                  videos=len(vids), photos=len(phos), junk=len(junk), other=len(other),
                  video_seconds=round(sum(r.get("duration", 0) for r in good_v), 1),
                  portrait=sum(v for k, v in orient.items() if k.endswith("portrait")),
                  landscape=sum(v for k, v in orient.items() if k.endswith("landscape")),
                  by_orientation=orient,
                  edited_pairs=sum(1 for r in prec if r.get("edited_version")),
                  front_camera_photos=sum(1 for r in prec if r.get("front_camera")),
                  probe_seconds=round(time.time() - t0, 1))
    rep = dict(folder=root, generated=time.strftime("%Y-%m-%d %H:%M:%S"), totals=totals, videos=vrec, photos=prec,
               junk=junk, other=[os.path.relpath(f, root) for f in other])
    if args.json == "-":
        print(json.dumps(rep, indent=1, ensure_ascii=False))
        return 0
    out = args.json or f"probe_{os.path.basename(root.rstrip(os.sep)) or 'media'}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)

    print(f"{'video':<22}{'dur':>7}{'fps':>7} {'coded':<10}{'rot':>5} {'upright':<10}{'orient':<10}{'aud':<4}{'codec':<6}flags")
    for r in vrec:
        if "duration" not in r:
            print(f"{r['file']:<22}  UNREADABLE  {r.get('error', '')}")
            continue
        flags = " ".join(r["junk"] + r["notes"])
        print(f"{r['file'][:21]:<22}{r['duration']:>7.2f}{r['fps']:>7.2f} {r['coded']:<10}{r['rotation']:>5.0f} "
              f"{r['upright']:<10}{r['orientation']:<10}{'yes' if r['has_audio'] else 'NO':<4}{r['codec'] or '':<6}{flags}")
    print()
    print(f"{'photo':<22}{'fmt':<6}{'size':<11}{'orient':<10}{'pair':<22}flags")
    for r in prec:
        pair = ("edit: " + r["edited_version"]) if r.get("edited_version") else \
               ("orig: " + r["edited_version_of"]) if r.get("edited_version_of") else ""
        print(f"{r['file'][:21]:<22}{r.get('format', '?'):<6}{r.get('size', '?'):<11}{r.get('orientation', '?'):<10}"
              f"{pair[:21]:<22}{' '.join(r['junk'] + r['notes'])}")
    if junk:
        print()
        print("JUNK:")
        for j in junk:
            print(f"  {j['file']:<26}{j['reason']}")
    if other:
        print("OTHER (ignored):", ", ".join(rep["other"][:20]) + (" ..." if len(other) > 20 else ""))
    t = totals
    print()
    print(f"TOTAL {t['files']} files, {t['bytes'] / 1e9:.2f} GB | {t['videos']} videos ({t['video_seconds'] / 60:.1f} min usable) "
          f"| {t['photos']} photos ({t['edited_pairs']} with an IMG_E edit, {t['front_camera_photos']} front-camera) "
          f"| {t['junk']} junk | portrait {t['portrait']} vs landscape {t['landscape']}  {t['by_orientation']}")
    print(f"JSON: {os.path.abspath(out)}  ({t['probe_seconds']} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

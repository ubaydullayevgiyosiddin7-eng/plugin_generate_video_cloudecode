"""Royalty-free music catalogue (incompetech.com, Kevin MacLeod, CC BY 4.0): cached search, download, scan.
Replaces the per-project catalogue fetch + screening scripts (both projects fetched the same 881 KB file).

  python tools/music_catalog.py fetch                              download the catalogue once (cached)
  python tools/music_catalog.py fetch --from-file pieces.json      seed the cache from a saved copy (offline)
  python tools/music_catalog.py search --feel calm,relaxed --bpm 70-110 --min-len 60 --no-vocals
  python tools/music_catalog.py search --instruments koto,flute --genre world --text japanese --top 15
  python tools/music_catalog.py get "Senbazuru" "Fretless" --out music/          download MP3s (cached)
  python tools/music_catalog.py scan music/Senbazuru.mp3 music/Fretless.mp3 --json candidates.json
  python tools/music_catalog.py shortlist --feel uplifting --bpm 95-130 --min-len 90 --no-vocals \
                                          --get 5 --out music/ --json candidates.json     search + get + scan

search prints title, length, catalogue BPM, genre, feel, instruments (sorted by how many --feel/--instruments/
--text words match, then by BPM distance to the middle of --bpm).  scan: duration, integrated loudness / true
peak (ffmpeg ebur128), key (ROUGH: CQT chroma vs Krumhansl profiles - relative keys / pentatonic music are often
confused, check by ear before matching keys at a join), tempo estimate, energy per 8 s (RMS dB - shows the
shape: intro, build, breakdown, ending) and where the sound ends.  candidates.json has, per track, a
music_bed.py "track" block incl. the CC BY attribution text (goes into the post caption, not on screen).
Cache: $VT_MUSIC_CACHE, else %LOCALAPPDATA%/video_tools/music (never inside the kit or a project folder):
catalogue.json + mp3/ (downloads are reused across projects; delete the folder to free space).
Licence: CC BY 4.0 - every use needs the attribution text (the owner wants it in the caption only).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import FFMPEG, safe_console  # noqa: E402

CATALOG_URL = "https://incompetech.com/music/royalty-free/pieces.json"
MP3_URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/{}"
PAGE_URL = "https://incompetech.com/music/royalty-free/index.html?isrc={}"
LICENSE = "CC BY 4.0 (Creative Commons Attribution 4.0 International)"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
GENRES = {2: "African", 3: "Blues", 4: "Classical", 5: "Contemporary", 6: "Disco", 7: "Electronica", 8: "Funk",
          9: "Holiday", 10: "Horror", 11: "Jazz", 12: "Latin", 13: "Modern", 14: "Musical", 15: "Polka", 16: "Pop",
          18: "Reggae", 19: "Rock", 20: "Silent Film Score", 21: "Ska", 22: "Soundtrack", 23: "Stings",
          24: "Unclassifiable", 25: "World", 26: "Urban"}
VOCAL_WORDS = ("vocal", "voice", "choir", "singer", "sung", "sings", "lyric", "chant", "rap")
UA = {"User-Agent": "Mozilla/5.0 (video_tools music_catalog)"}
MAJ = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MIN = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
NOTES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def cache_dir():
    d = os.environ.get("VT_MUSIC_CACHE") or os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                                                          "video_tools", "music")
    os.makedirs(os.path.join(d, "mp3"), exist_ok=True)
    return d


def catalog_path():
    return os.path.join(cache_dir(), "catalogue.json")


def http_get(url, dst, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    tmp = dst + ".part"
    with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    os.replace(tmp, dst)
    return os.path.getsize(dst)


def fetch(from_file=None, max_age_days=30, force=False):
    p = catalog_path()
    if from_file:
        d = json.load(open(from_file, encoding="utf-8"))
        if not isinstance(d, list) or not d or "title" not in d[0]:
            raise SystemExit(f"{from_file}: not an incompetech pieces.json (list of pieces with title/filename/...)")
        shutil.copyfile(from_file, p)
        print(f"catalogue: {len(d)} pieces copied from {from_file} -> {p}")
        return p
    if os.path.exists(p) and not force and time.time() - os.path.getmtime(p) < max_age_days * 86400:
        print(f"catalogue cached ({len(load_catalog())} pieces, {(time.time() - os.path.getmtime(p)) / 86400:.0f} days old): {p}")
        return p
    n = http_get(CATALOG_URL, p)
    print(f"catalogue downloaded: {n / 1e3:.0f} kB, {len(load_catalog())} pieces -> {p}")
    return p


def load_catalog():
    p = catalog_path()
    if not os.path.exists(p):
        raise SystemExit("no cached catalogue - run: python tools/music_catalog.py fetch   (or fetch --from-file F)")
    return json.load(open(p, encoding="utf-8"))


def seconds(length):
    try:
        parts = [float(x) for x in str(length).split(":")]
    except ValueError:
        return None
    s = 0.0
    for x in parts:
        s = s * 60 + x
    return s


def piece_info(p):
    try:
        g = GENRES.get(int(p.get("genre") or 0), str(p.get("genre")))
    except ValueError:
        g = str(p.get("genre"))
    try:
        bpm = float(p.get("bpm") or 0) or None
    except ValueError:
        bpm = None
    return dict(title=p.get("title", ""), filename=p.get("filename", ""), seconds=seconds(p.get("length")), bpm=bpm,
                genre=g, feel=p.get("feel") or "", instruments=p.get("instruments") or "",
                description=p.get("description") or "", isrc=p.get("isrc") or "")


def has_vocals(q):
    blob = " ".join([q["instruments"], q["feel"], q["description"]]).lower()
    return any(w in blob for w in VOCAL_WORDS)


def _words(s):
    return [w.strip().lower() for w in (s or "").split(",") if w.strip()]


def search(cat, a):
    feel, inst, text, genre = _words(a.feel), _words(a.instruments), _words(a.text), _words(a.genre)
    bpm = None
    if a.bpm:
        lo, _, hi = a.bpm.partition("-")
        bpm = (float(lo), float(hi or lo))
    out = []
    for p in cat:
        q = piece_info(p)
        if a.no_vocals and has_vocals(q):
            continue
        if a.min_len and (q["seconds"] or 0) < a.min_len:
            continue
        if a.max_len and (q["seconds"] or 1e9) > a.max_len:
            continue
        if genre and q["genre"].lower() not in genre:
            continue
        if bpm and not q["bpm"]:
            continue
        if bpm:
            # catalogue BPMs are sometimes half/double the felt tempo (Senbazuru: 48 listed, ~81 felt)
            if not any(bpm[0] <= q["bpm"] * m <= bpm[1] for m in (1, 2, 0.5)):
                continue
        hits = sum(w in q["feel"].lower() for w in feel) * 2 + sum(w in q["instruments"].lower() for w in inst) * 2
        blob = " ".join([q["title"], q["description"], q["feel"], q["instruments"]]).lower()
        hits += sum(w in blob for w in text)
        need = (1 if feel else 0) + (1 if inst else 0) + (1 if text else 0)
        if need and hits == 0:
            continue
        mid = (bpm[0] + bpm[1]) / 2 if bpm else 0
        dist = min(abs(q["bpm"] * m - mid) for m in (1, 2, 0.5)) if bpm and q["bpm"] else 0
        out.append((hits, -dist, q))
    out.sort(key=lambda r: (-r[0], -r[1], r[2]["title"]))
    return [q for _, _, q in out[:a.top]]


def print_table(rows):
    print(f"{'title':<34}{'len':>6}{'bpm':>6}  {'genre':<12}{'feel':<34}instruments")
    for q in rows:
        ln = f"{int(q['seconds'] // 60)}:{int(q['seconds'] % 60):02d}" if q["seconds"] else "?"
        print(f"{q['title'][:33]:<34}{ln:>6}{(q['bpm'] or 0):>6.0f}  {q['genre'][:11]:<12}{q['feel'][:33]:<34}"
              f"{q['instruments'][:60]}")


def attribution(title):
    return (f"\"{title}\" Kevin MacLeod (incompetech.com)\nLicensed under Creative Commons: By Attribution 4.0 License\n"
            f"http://creativecommons.org/licenses/by/4.0/")


def track_block(q, path):
    return {"file": os.path.abspath(path), "title": q["title"], "artist": "Kevin MacLeod",
            "source_url": PAGE_URL.format(q["isrc"]) if q.get("isrc") else "https://incompetech.com",
            "download_url": MP3_URL.format(urllib.parse.quote(q["filename"])), "license": LICENSE,
            "license_url": LICENSE_URL, "attribution_text": attribution(q["title"])}


def find(cat, name):
    infos = [piece_info(p) for p in cat]
    for q in infos:
        if q["title"].lower() == name.lower() or q["filename"].lower() == name.lower():
            return q
    hits = [q for q in infos if name.lower() in q["title"].lower()]
    if len(hits) == 1:
        return hits[0]
    raise SystemExit(f"'{name}': {'no match' if not hits else 'ambiguous: ' + ', '.join(h['title'] for h in hits[:8])}")


def get(cat, names, out_dir):
    """Download (or reuse the cached copy) and copy into out_dir.  -> [(info, path)]"""
    os.makedirs(out_dir, exist_ok=True)
    res = []
    for name in names:
        q = find(cat, name)
        cached = os.path.join(cache_dir(), "mp3", q["filename"])
        if not os.path.exists(cached):
            n = http_get(MP3_URL.format(urllib.parse.quote(q["filename"])), cached, timeout=180)
            print(f"downloaded {q['filename']} ({n / 1e6:.1f} MB)")
        dst = os.path.join(out_dir, q["filename"])
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(cached):
            shutil.copyfile(cached, dst)
        print(f"{dst}")
        res.append((q, dst))
    return res


def ebur(path):
    r = subprocess.run([FFMPEG, "-nostdin", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    s = r[r.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", s)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", s)
    return (float(I.group(1)) if I else None, float(tp.group(1)) if tp and tp.group(1) != "-inf" else None)


def scan(path):
    """Loudness, key, tempo estimate, 8-s energy curve, end of sound."""
    import numpy as np
    sr = 22050
    raw = subprocess.run([FFMPEG, "-nostdin", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le",
                          "-"], capture_output=True, check=True).stdout
    y = np.frombuffer(raw, np.float32).astype(np.float64)
    dur = len(y) / sr
    import librosa
    ch = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=2048).mean(1)
    best = max(((float(np.corrcoef(ch, np.roll(pr, i))[0, 1]), NOTES[i] + (" major" if nm == "maj" else " minor"))
                for i in range(12) for nm, pr in (("maj", MAJ), ("min", MIN))))
    tempo = librosa.beat.beat_track(y=y, sr=sr, hop_length=512)[0]
    win = 8
    energy = []
    for a in np.arange(0, dur, win):
        seg = y[int(a * sr):int((a + win) * sr)]
        energy.append(round(float(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)), 1) if len(seg) else -120.0)
    env = np.array([np.sqrt(np.mean(y[i:i + 2048] ** 2)) for i in range(0, max(1, len(y) - 2048), 1024)])
    db = 20 * np.log10(env + 1e-9)
    loud = np.where(db > -60)[0]
    end = float(loud[-1] * 1024 / sr) if len(loud) else dur
    I, tp = ebur(path)
    return dict(duration=round(dur, 2), lufs=I, true_peak_dbtp=tp, key=best[1], key_confidence=round(best[0], 2),
                tempo_est=round(float(np.atleast_1d(tempo)[0]), 1), energy_8s_db=energy, sound_ends=round(end, 2))


def scan_many(paths, cat=None, infos=None):
    infos = infos or {}
    res = []
    for p in paths:
        t0 = time.time()
        s = scan(p)
        q = infos.get(os.path.abspath(p))
        if q is None and cat is not None:
            fn = os.path.basename(p).lower()
            q = next((piece_info(x) for x in cat if (x.get("filename") or "").lower() == fn), None)
        rec = dict(file=os.path.abspath(p), **s)
        if q:
            rec.update(title=q["title"], bpm_catalog=q["bpm"], genre=q["genre"], feel=q["feel"],
                       instruments=q["instruments"], track=track_block(q, p), attribution_text=attribution(q["title"]))
        res.append(rec)
        print(f"{os.path.basename(p):<34}{s['duration']:7.1f}s  {s['lufs']} LUFS  TP {s['true_peak_dbtp']}  "
              f"{s['key']} ({s['key_confidence']})  ~{s['tempo_est']} BPM  ends {s['sound_ends']}s  "
              f"energy/8s {' '.join(str(int(e)) for e in s['energy_8s_db'])}  ({time.time() - t0:.0f}s)")
    return res


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download / refresh / seed the catalogue cache")
    f.add_argument("--from-file", help="use a saved pieces.json instead of downloading")
    f.add_argument("--force", action="store_true", help="re-download even if the cache is fresh (< 30 days)")

    def filters(p):
        p.add_argument("--feel", help="comma words matched in the catalogue 'feel' (calm,relaxed,uplifting,bright ...)")
        p.add_argument("--instruments", help="comma words (koto,piano,ukulele ...)")
        p.add_argument("--genre", help="comma genre names (world,pop,soundtrack ...)")
        p.add_argument("--text", help="comma words anywhere in title/description/feel/instruments")
        p.add_argument("--bpm", help="range LO-HI (catalogue BPM; x2 / x0.5 also accepted)")
        p.add_argument("--min-len", type=float, help="minimum length (s)")
        p.add_argument("--max-len", type=float, help="maximum length (s)")
        p.add_argument("--no-vocals", action="store_true", help="drop pieces mentioning vocals/voice/choir")
        p.add_argument("--top", type=int, default=20, help="rows to show (default 20)")
    s = sub.add_parser("search", help="filter the cached catalogue")
    filters(s)
    s.add_argument("--json", help="write the hits as JSON")
    g = sub.add_parser("get", help="download pieces (by title or file name) into --out")
    g.add_argument("names", nargs="+")
    g.add_argument("--out", required=True, help="destination folder (e.g. the project's music folder)")
    sc = sub.add_parser("scan", help="loudness / key / tempo / energy of audio files -> candidates JSON")
    sc.add_argument("files", nargs="+")
    sc.add_argument("--json", help="write candidates JSON")
    sh = sub.add_parser("shortlist", help="search + download the top N + scan -> candidates JSON")
    filters(sh)
    sh.add_argument("--get", type=int, default=5, help="how many of the hits to download and scan (default 5)")
    sh.add_argument("--out", required=True, help="destination folder for the MP3s")
    sh.add_argument("--json", required=True, help="candidates JSON")
    a = ap.parse_args()
    if a.cmd == "fetch":
        fetch(a.from_file, force=a.force)
        return 0
    if a.cmd == "scan":
        cat = load_catalog() if os.path.exists(catalog_path()) else None
        res = scan_many(a.files, cat)
        if a.json:
            json.dump({"generated": time.strftime("%Y-%m-%d"), "candidates": res}, open(a.json, "w", encoding="utf-8"),
                      indent=1, ensure_ascii=False)
            print("wrote", a.json)
        return 0
    cat = load_catalog()
    if a.cmd == "get":
        get(cat, a.names, a.out)
        return 0
    hits = search(cat, a)
    print_table(hits)
    print(f"{len(hits)} hit(s) of {len(cat)} pieces")
    if a.cmd == "search":
        if a.json:
            json.dump(hits, open(a.json, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        return 0 if hits else 1
    if not hits:
        return 1
    got = get(cat, [q["title"] for q in hits[:a.get]], a.out)
    res = scan_many([p for _, p in got], cat, {os.path.abspath(p): q for q, p in got})
    json.dump({"generated": time.strftime("%Y-%m-%d"), "query": {k: v for k, v in vars(a).items() if k != "cmd"},
               "candidates": res}, open(a.json, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

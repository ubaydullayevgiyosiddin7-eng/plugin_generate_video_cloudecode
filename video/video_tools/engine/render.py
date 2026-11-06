"""EDL render engine - EDL (JSON) -> finished 9:16 film (built for the "Magic Safari" film).

  python render.py EDL.json                 full-quality render (4K sources, CRF 17 slow)
  python render.py EDL.json --timeline      dry run: print the frame-accurate output timeline
  python render.py EDL.json --preview --no-proxy --hwaccel d3d11va   half resolution from the 4K sources
  python render.py EDL.json --only v03,p01  (re)render just these items -> <out>_<id>.mp4 each
  python render.py EDL.json --clean-cache   delete this EDL's cached intermediates (also an old engine/cache copy)
Source folders come from --video-dir/--photo-dir/--proxy-dir/--music-dir, else the EDL's "paths"
block, else VT_VIDEO_DIR/VT_PHOTO_DIR/VT_PROXY_DIR/VT_MUSIC_DIR, else defaults relative to the EDL.
The cache defaults to <EDL folder>/cache/<edl name>[_preview] (never inside the kit).  The log shows free
disk AND free RAM; below 1.5 GB RAM the render falls back to --jobs 1.
See README.md for the EDL schema.
"""
import argparse
import json
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (ENGINE_DIR, ENGINE_VERSION, FFMPEG, file_sig, key_of, log, run, free_gb, free_ram_gb)  # noqa: E402
import edl as edlmod  # noqa: E402

MIN_FREE_GB = 1.0
HEADROOM_GB = 0.3         # always leave this much for the other jobs on the machine
MB_PER_FRAME_OUT = 0.11   # final CRF 17 slow, grainy 4K-derived 1080x1920 (~25 Mbit/s) + audio
RAM_WARN_GB = 2.5         # below: warn (a RAM-starved final ran 4-10x slower: 43.6 s of film in 989 s)
RAM_SERIAL_GB = 1.5       # below: force --jobs 1 (each 4K item render needs ~1-1.3 GB)
KEY_NOTE_MAX_S = 1.0      # frame keys this close outside an item's source range are normal (reframers key +-0.5 s)
LEGACY_CACHE_ROOT = os.path.join(ENGINE_DIR, "cache")   # kit 0.1 default (inside the kit) - still read if present


def mb_per_frame_int(crf, preview=False):
    """Measured: x264 veryfast yuv420p 1080x1920 of this footage ~0.19 MB/frame at CRF 13, -9 %/CRF."""
    return 0.19 * (0.91 ** (crf - 13)) * (0.3 if preview else 1.0)


def build_jobs(edl, cache_dir, args):
    from grade import write_cube
    jobs = []
    out = edl["output"]
    preset = args.grade or edl["grade"]["preset"]
    cores = os.cpu_count() or 4
    per = max(2, cores // max(1, args.jobs))
    held = []
    for r, it in zip(edl["timeline"]["rows"], edl["items"]):
        adj = it.get("grade_adjust", {}) or {}
        lut_key = key_of(["lut", preset, adj, 2])
        lut = os.path.join(cache_dir, f"lut_{lut_key}.cube")
        if not os.path.exists(lut):
            write_cube(lut, preset, adj)
        src_sig = file_sig(it["_decode_src"])
        geo = dict(v=ENGINE_VERSION, type=it["type"], src=src_sig, n=r["n"], fps=out["fps"],
                   rotate=it.get("rotate", 0), hflip=it.get("hflip", False))
        if it["type"] == "video":
            geo.update(t_in=it["in"], t_out=it["out"], speed=it["speed"], speed_map=it.get("speed_map"))
        st = it.get("stabilize")
        st_key = key_of(["stab", geo, (st if isinstance(st, dict) else {}).get("method", "cv"), 3])
        vkey = key_of([geo, it["frame"], st, preset, adj, out["w"], out["h"], edl["_preview"], args.interp,
                       it.get("tilt_deg", 0.0), it.get("frame_blend", "auto")])
        job = dict(id=it["id"], type=it["type"], src=it["_src"], decode_src=it["_decode_src"],
                   n=r["n"], fps=out["fps"], OW=out["w"], OH=out["h"], frame=it["frame"],
                   rotate=it.get("rotate", 0), hflip=it.get("hflip", False), tilt_deg=it.get("tilt_deg", 0.0),
                   stabilize=st, lut=lut,
                   out_path=os.path.join(cache_dir, f"{it['id']}_{vkey}.mkv"),
                   stab_cache=os.path.join(cache_dir, f"stab_{st_key}.npz"),
                   hwaccel=args.hwaccel, dec_threads=per, enc_threads=per, cv_threads=max(2, per),
                   int_preset="ultrafast" if edl["_preview"] else "veryfast",
                   int_crf=20 if edl["_preview"] else 13, interp=args.interp)
        if it["type"] == "video":
            job.update({"in": it["in"], "out": it["out"], "speed": it["speed"], "speed_map": it.get("speed_map"),
                        "timemap": it.get("_timemap", False), "src_fps": it.get("_src_fps", 60),
                        "frame_blend": it.get("frame_blend", "auto"),
                        "speed_audio": it.get("speed_audio", "mute")})
            akey = key_of(["a2", ENGINE_VERSION, file_sig(it["_src"]), it["in"], it["out"], r["n"], it["speed"],
                           it.get("speed_map"), out["fps"], it.get("speed_audio", "mute"), "hp120"])
            job["audio_path"] = os.path.join(cache_dir, f"{it['id']}_a_{akey}.wav")
            keys = (it["frame"].get("keys") or [])
            dist = [(k["t"], max(it["in"] - float(k["t"]), float(k["t"]) - it["out"])) for k in keys]
            far = [t for t, d in dist if d > KEY_NOTE_MAX_S]
            if far:
                log(f"WARNING {it['id']}: key times {far} more than {KEY_NOTE_MAX_S:g} s outside the source range "
                    f"{it['in']}-{it['out']} (held - is the key time in source seconds?)")
            elif any(d > 0.05 for _, d in dist):
                held.append(it["id"])
        else:
            job.update({"in": 0.0, "out": r["n"] / out["fps"], "speed": 1.0, "timemap": False})
        if args.force and (not args.only or it["id"] in args.only):
            for p in (job["out_path"], job.get("audio_path"), job["stab_cache"]):
                if p and os.path.exists(p):
                    os.remove(p)
        jobs.append(job)
    if held:
        log(f"NOTE {len(held)} item(s) have frame keys up to {KEY_NOTE_MAX_S:g} s outside their used source range "
            f"(held; normal - reframers key +-0.5 s around the pick): {', '.join(held)}")
    return jobs


def _pending(jobs):
    return [j for j in jobs if not os.path.exists(j["out_path"]) or
            (j.get("audio_path") and not os.path.exists(j["audio_path"]))]


def render_items(jobs, nworkers):
    from itemrender import render_item
    todo = _pending(jobs)
    results = {j["id"]: dict(id=j["id"], out=j["out_path"], audio=j.get("audio_path"), ok=True, cached=True)
               for j in jobs if j not in todo}
    if todo:
        log(f"rendering {len(todo)} item(s) ({len(jobs) - len(todo)} cached) with {nworkers} worker(s)")
        todo.sort(key=lambda j: -j["n"] * (2 if j.get("stabilize") else 1))
        t0 = time.time()
        if nworkers <= 1:
            for j in todo:
                res = render_item(j)
                _report(res, t0)
                results[j["id"]] = res
        else:
            with ProcessPoolExecutor(max_workers=nworkers) as ex:
                futs = {ex.submit(render_item, j): j for j in todo}
                for fu in as_completed(futs):
                    try:
                        res = fu.result()
                    except Exception as e:  # worker process died (e.g. out of memory)
                        j = futs[fu]
                        res = dict(id=j["id"], ok=False, error=f"worker crashed: {e}")
                    _report(res, t0)
                    results[res["id"]] = res
    else:
        log(f"all {len(jobs)} items cached")
    bad = [r for r in results.values() if not r.get("ok")]
    if bad:  # transient failures (out of memory on a busy machine, stalls): retry one at a time
        for r in bad:
            first = (r.get("error") or "").strip().splitlines()
            log(f"  {r['id']}: failed ({first[0][:200] if first else '?'}) - retrying alone")
            j = next(j for j in jobs if j["id"] == r["id"])
            res = render_item(j)
            _report(res, time.time())
            results[j["id"]] = res
    bad = [r for r in results.values() if not r.get("ok")]
    if bad:
        for r in bad:
            log(f"ERROR item {r['id']}:\n{r.get('error')}")
        raise SystemExit(2)
    return results


def _report(res, t0):
    if not res.get("ok"):
        log(f"  {res['id']}: FAILED")
        return
    extra = f" | {res['plan']}" if res.get("plan") else ""
    if res.get("stab"):
        extra += f" | stab {res['stab']}"
    log(f"  {res['id']}: done in {res.get('seconds', 0):.1f}s (warp {res.get('warp_s', 0)}s){extra}")
    for w in res.get("warnings", []):
        log(f"  {res['id']}: NOTE {w}")


def only_clips(edl, jobs, results):
    """--only: write each selected item (graded, with its own sound) for review."""
    root, ext = os.path.splitext(edl["output"]["path"])
    for j in jobs:
        res = results[j["id"]]
        out = f"{root}_{j['id']}.mp4"
        cmd = [FFMPEG, "-nostdin", "-v", "error", "-y", "-i", res["out"]]
        if res.get("audio") and os.path.exists(res["audio"]):
            cmd += ["-i", res["audio"], "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k",
                    "-af", "loudnorm=I=-16:TP=-2"]
        cmd += ["-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                "-movflags", "+faststart", out]
        run(cmd)
        log(f"  wrote {out}")


def gc_cache(cache_dir, jobs):
    """Delete intermediates that the current EDL no longer references (stale versions, removed
    items, temp files).  Stabilisation analyses (.npz, tiny) and LUTs are kept."""
    keep = set()
    for j in jobs:
        for k in ("out_path", "audio_path", "lut", "stab_cache"):
            if j.get(k):
                keep.add(os.path.basename(j[k]))
                keep.add(os.path.basename(j[k]).replace(".npz", ".trf"))
    freed = 0
    for f in os.listdir(cache_dir):
        p = os.path.join(cache_dir, f)
        if ".tmp" in f or (f.endswith((".mkv", ".wav")) and f not in keep):
            try:
                freed += os.path.getsize(p)
                os.remove(p)
            except OSError:
                pass
    if freed:
        log(f"cache: removed {freed / 1e6:.0f} MB of stale intermediates")


def _cache_root(edl_path, overrides):
    """Cache root without validating the EDL (used by --clean-cache)."""
    try:
        with open(edl_path, "r", encoding="utf-8") as f:
            ep = (json.load(f) or {}).get("paths")
    except (OSError, ValueError):
        ep = None
    p = edlmod.resolve_paths(ep, os.path.dirname(os.path.abspath(edl_path)), overrides)
    return p.get("cache") or os.path.join(os.path.dirname(os.path.abspath(edl_path)), "cache")


def _same(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def resolve_cache_dir(root, name, preview, forced_root=False):
    """<root>/<name>[_preview].  Backward compatible: unless the root was forced (--cache-root / VT_CACHE_DIR),
    an existing kit-0.1 cache engine/cache/<name> is reused while the new folder does not exist yet, so a
    project started before the change does not re-render everything.  Returns (dir, note or None)."""
    sub = name + ("_preview" if preview else "")
    new = os.path.join(root, sub)
    legacy = os.path.join(LEGACY_CACHE_ROOT, sub)
    if not forced_root and not _same(new, legacy) and not os.path.isdir(new) and os.path.isdir(legacy) \
            and any(f.endswith(".mkv") for f in os.listdir(legacy)):
        return legacy, (f"NOTE cache: reusing the old in-kit cache {legacy} (the default is now <EDL folder>/cache); "
                        f"free it with `render.py <EDL> --clean-cache` when this project is done")
    return new, None


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # never crash on a cp1252 console (Uzbek/emoji texts)
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="EDL render engine: EDL (JSON) -> finished 9:16 film. See README.md.")
    ap.add_argument("edl")
    ap.add_argument("--timeline", action="store_true", help="dry run: print the output timeline and exit")
    ap.add_argument("--timeline-json", metavar="PATH", help="also write the timeline as JSON")
    ap.add_argument("--preview", action="store_true",
                    help="half resolution, fast encodes; uses proxies only if they exist in paths.proxy")
    ap.add_argument("--no-proxy", action="store_true", help="preview from the 4K sources anyway")
    ap.add_argument("--only", help="comma-separated item ids: render just these and write <out>_<id>.mp4")
    ap.add_argument("--force", action="store_true", help="re-render (ignore cached intermediates)")
    ap.add_argument("--jobs", type=int, default=2, help="parallel item renders (default 2 = max sensible on 8 GB RAM)")
    ap.add_argument("--hwaccel", default="none", choices=["none", "d3d11va"],
                    help="HEVC decode on the GPU (bit-exact on this machine, frees CPU)")
    ap.add_argument("--interp", default="cubic", choices=["cubic", "lanczos"])
    ap.add_argument("--grade", help="override grade preset (natural|warm_pop|cinematic_soft|none)")
    ap.add_argument("--out", help="override output path")
    ap.add_argument("--cache", help="exact cache directory for this render (default <cache root>/<edl name>[_preview])")
    ap.add_argument("--cache-root", help="cache root (default: EDL paths.cache, env VT_CACHE_DIR, else <EDL folder>/cache)")
    ap.add_argument("--video-dir", help="raw footage folder (overrides the EDL's paths.video)")
    ap.add_argument("--photo-dir", help="photo folder (overrides paths.photo)")
    ap.add_argument("--proxy-dir", help="preview proxy folder (overrides paths.proxy)")
    ap.add_argument("--music-dir", help="folder the music path is looked up in (overrides paths.music)")
    ap.add_argument("--keep-cache", action="store_true", help="don't delete stale intermediates")
    ap.add_argument("--clean-cache", action="store_true", help="delete this EDL's cache (full + preview) and exit")
    ap.add_argument("--consume-cache", action="store_true",
                    help="delete each intermediate right after assembly used it (automatic when disk is tight)")
    args = ap.parse_args(argv)
    args.only = [s.strip() for s in args.only.split(",")] if args.only else None

    overrides = {"video": args.video_dir, "photo": args.photo_dir, "proxy": args.proxy_dir,
                 "music": args.music_dir, "cache": args.cache_root}
    t_start = time.time()
    if args.clean_cache:
        name = os.path.splitext(os.path.basename(args.edl))[0]
        root = _cache_root(args.edl, overrides)
        freed = 0
        dirs = [args.cache] if args.cache else \
            [os.path.join(r, name + s) for r in (root, LEGACY_CACHE_ROOT) for s in ("", "_preview")]
        for d in dirs:
            if d and os.path.isdir(d):
                for droot, _, files in os.walk(d):
                    freed += sum(os.path.getsize(os.path.join(droot, f)) for f in files)
                shutil.rmtree(d, ignore_errors=True)
                log(f"  removed {d}")
        log(f"cache cleaned ({freed / 1e6:.0f} MB freed)")
        return 0
    try:
        edl = edlmod.load(args.edl, preview=args.preview, use_proxy=(args.preview and not args.no_proxy),
                          path_overrides=overrides)
    except edlmod.EDLError as e:
        log(f"EDL ERROR: {e}")
        return 2
    if args.out:
        edl["output"]["path"] = os.path.abspath(args.out)
    if args.grade:
        edl["grade"]["preset"] = args.grade
    print(edlmod.timeline_report(edl), flush=True)
    if args.timeline_json:
        with open(args.timeline_json, "w", encoding="utf-8") as f:
            json.dump(edlmod.timeline_json(edl), f, indent=2)
    if args.timeline:
        return 0

    if args.preview and not args.no_proxy:
        vids = [it for it in edl["items"] if it["type"] == "video"]
        if vids and not any(it["_decode_src"] != it["_src"] for it in vids):
            log(f"NOTE preview from the original sources (no proxies in {edl['paths'].get('proxy')}) - fine for "
                f"films up to ~3 min (~17 s of film per minute with --hwaccel d3d11va)")
    if args.cache:
        cache_dir, note = os.path.abspath(args.cache), None
    else:
        root = edl["paths"].get("cache") or os.path.join(os.path.dirname(edl["_path"]), "cache")
        cache_dir, note = resolve_cache_dir(root, edl["_name"], args.preview,
                                            forced_root=bool(args.cache_root or os.environ.get("VT_CACHE_DIR")))
    if note:
        log(note)
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(os.path.dirname(edl["output"]["path"]) or ".", exist_ok=True)
    jobs = build_jobs(edl, cache_dir, args)
    sel = [j for j in jobs if not args.only or j["id"] in args.only]
    if args.only and len(sel) != len(args.only):
        log(f"unknown ids for --only: {sorted(set(args.only) - {j['id'] for j in jobs})}")
        return 2
    if not args.keep_cache and not args.only:
        gc_cache(cache_dir, jobs)  # free space first

    # ---- disk guard: abort < 1 GB; if tight, consume intermediates during assembly; then raise CRF
    pend = _pending(sel)
    pend_frames = sum(j["n"] for j in pend)
    out_gb = 0.0 if args.only else edl["timeline"]["total_f"] * MB_PER_FRAME_OUT / 1000 + 0.06
    free = free_gb(cache_dir)
    crf = pend[0]["int_crf"] if pend else 13
    consume = args.consume_cache
    int_gb = pend_frames * mb_per_frame_int(crf, args.preview) / 1000
    if free < MIN_FREE_GB:
        log(f"ABORT: only {free:.2f} GB free on the cache/output drive (engine requires >= {MIN_FREE_GB:.1f} GB). "
            f"Free some space (e.g. `python render.py <old EDL> --clean-cache`) and retry.")
        return 3
    if not args.only and not consume and int_gb + out_gb + HEADROOM_GB > free:
        consume = True
        log("disk is tight: intermediates will be deleted as soon as the assembler has used them "
            "(--consume-cache); a later re-render will re-create them")
    peak = int_gb + (0 if consume else out_gb)
    while peak + HEADROOM_GB > free and crf < 18 and not args.preview:
        crf += 1
        int_gb = pend_frames * mb_per_frame_int(crf) / 1000
        peak = int_gb + (0 if consume else out_gb)
    if peak + HEADROOM_GB > free:
        log(f"ABORT: this render needs ~{peak:.2f} GB (+{HEADROOM_GB} GB headroom) but only {free:.2f} GB is free.")
        return 3
    for j in pend:
        if j["int_crf"] != crf:
            j["int_crf"] = crf
    if pend and crf != 13 and not args.preview:
        log(f"disk is tight: intermediates encoded at CRF {crf} instead of 13")
    log(f"disk: {free:.2f} GB free, peak need ~{peak:.2f} GB  (cache {cache_dir})")
    ram, ram_total = free_ram_gb()
    if ram is not None:
        log(f"RAM: {ram:.2f} GB available" + (f" of {ram_total:.1f} GB" if ram_total else ""))
        if ram < RAM_SERIAL_GB and args.jobs > 1 and pend:
            log(f"WARNING RAM: only {ram:.2f} GB free -> --jobs 1 instead of {args.jobs}. Close browsers/Word/other "
                f"apps first for speed (a RAM-starved final rendered 4-10x slower)")
            args.jobs = 1
        elif ram < RAM_WARN_GB and pend:
            log(f"WARNING RAM: only {ram:.2f} GB free (< {RAM_WARN_GB:g} GB) - close browsers/Word/other apps before a "
                f"final render (a RAM-starved final rendered 4-10x slower)")

    if args.only:
        results = render_items(sel, args.jobs)
        only_clips(edl, sel, results)
        log(f"done in {time.time() - t_start:.1f}s")
        return 0

    t0 = time.time()
    results = render_items(jobs, args.jobs)
    t_items = time.time() - t0

    import audio as au
    t1 = time.time()
    mix, rep = au.build_mix(edl, results, cache_dir)
    final_wav = os.path.join(cache_dir, "mix_final.wav")
    a = edl["audio"]
    ninfo = au.normalise(mix, final_wav, float(a["target_lufs"]), float(a["true_peak"]), cache_dir)
    del mix
    for k, v in rep.get("clips", {}).items():
        log(f"  audio {k}: {v}")
    if rep.get("music"):
        log(f"  music: {rep['music']}")
    log(f"  loudnorm: {ninfo}")
    t_audio = time.time() - t1

    from textfx import TextRenderer
    from assemble import assemble
    texts = TextRenderer(edl["texts"], edl["output"]["w"], edl["output"]["h"], edl["output"]["fps"]) \
        if edl["texts"] else None
    log("assembling final film ...")
    t_asm = assemble(edl, results, texts, final_wav, edl["output"]["path"], preview=args.preview, consume=consume)
    try:
        os.remove(final_wav)
    except OSError:
        pass
    total = time.time() - t_start
    dur = edl["timeline"]["total"]
    log(f"DONE {edl['output']['path']}  ({os.path.getsize(edl['output']['path']) / 1e6:.1f} MB)")
    log(f"  film {dur:.2f}s | items {t_items:.0f}s, audio {t_audio:.0f}s, assemble+encode {t_asm:.0f}s, "
        f"total {total:.0f}s  => {dur / (total / 60):.1f} s of film per minute of wall time")
    return 0


if __name__ == "__main__":
    sys.exit(main())

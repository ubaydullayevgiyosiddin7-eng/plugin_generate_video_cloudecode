"""EDL loading, validation, defaults and the frame-accurate output timeline."""
import json
import os

from common import probe, log

# Where sources are looked up.  Precedence (highest first):
#   1. CLI flags (render.py --video-dir/--photo-dir/--proxy-dir/--music-dir/--cache-root)
#   2. the EDL's "paths" block (relative paths are relative to the EDL file)
#   3. environment variables VT_VIDEO_DIR, VT_PHOTO_DIR, VT_PROXY_DIR, VT_MUSIC_DIR, VT_CACHE_DIR
#   4. these defaults (relative to the EDL file; None = not set)
# Sources are always also looked up next to the EDL file as a fallback.
DEFAULT_PATHS = {
    "video": ".",            # raw footage (MOV/MP4)
    "photo": "photos",       # upright sRGB JPGs (tools/heic_convert.py) or HEIC
    "proxy": "proxy",        # optional preview proxies <stem>.mp4 (tools/make_proxies.py)
    "music": ".",            # music bed WAV
    "cache": "cache",        # cache ROOT next to the EDL (a sub-folder per EDL name is used) - never inside the
                             # kit; render.py keeps using an old engine/cache/<name> folder if one exists
}
PATH_ENV = {"video": "VT_VIDEO_DIR", "photo": "VT_PHOTO_DIR", "proxy": "VT_PROXY_DIR",
            "music": "VT_MUSIC_DIR", "cache": "VT_CACHE_DIR"}
TRANSITION_DUR = {"cut": 0.0, "crossfade": 0.5, "dip_white": 0.6, "dip_black": 0.6, "whip": 0.25}
TEXT_STYLES = ("title", "subtitle", "label", "credit")
PHOTO_EXT = (".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".webp")


class EDLError(Exception):
    pass


def _resolve(src, dirs):
    if os.path.isabs(src) and os.path.exists(src):
        return os.path.abspath(src)
    for d in dirs:
        if d and os.path.exists(os.path.join(d, src)):
            return os.path.abspath(os.path.join(d, src))
    return None


def _resolve_photo(src, dirs):
    p = _resolve(src, dirs)
    if p:
        return p
    stem = os.path.splitext(os.path.basename(src))[0]
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for ext in PHOTO_EXT + tuple(e.upper() for e in PHOTO_EXT):
            c = os.path.join(d, stem + ext)
            if os.path.exists(c):
                return os.path.abspath(c)
    return None


def _norm_frame(fr, default_mode="crop"):
    fr = dict(fr or {})
    fr.setdefault("mode", default_mode)
    for k, dflt in (("cx", 0.5), ("cy", 0.5), ("zoom", 1.0)):
        v = fr.pop(k, None)
        base = dflt if v is None else v
        fr.setdefault(k + "0", base)
        fr.setdefault(k + "1", fr[k + "0"] if v is None else base)
    fr.setdefault("ease", "inout")
    if fr["mode"] not in ("crop", "box", "fit"):
        raise EDLError(f"frame.mode must be crop|box|fit, got {fr['mode']}")
    if fr["mode"] == "box":
        fr.setdefault("aspect", 0.8)
        if float(fr["aspect"]) <= 0:
            raise EDLError("frame.aspect must be > 0")
    keys = fr.get("keys")
    if keys is not None:
        if not isinstance(keys, list) or len(keys) < 2 or any("t" not in k for k in keys):
            raise EDLError("frame.keys must be a list of >= 2 objects with a 't' (source seconds)")
        ts = sorted(float(k["t"]) for k in keys)
        if any(b - a < 1e-3 for a, b in zip(ts, ts[1:])):
            raise EDLError("frame.keys: duplicate key times")
    if fr["ease"] not in ("linear", "inout", "in", "out"):
        raise EDLError(f"frame.ease must be linear|inout|in|out, got {fr['ease']}")
    return fr


def resolve_paths(edl_paths, edl_dir, overrides=None):
    """Effective source folders (absolute) for an EDL.  See DEFAULT_PATHS for the precedence.
    edl_paths: the EDL's "paths" block (may be None); overrides: {key: dir} from the CLI."""
    out = {}
    edl_paths = edl_paths or {}
    overrides = overrides or {}
    for k, dflt in DEFAULT_PATHS.items():
        if overrides.get(k):
            v = os.path.abspath(overrides[k])                     # CLI: relative to the CWD
        elif edl_paths.get(k):
            v = os.path.abspath(os.path.join(edl_dir, os.path.expandvars(os.path.expanduser(edl_paths[k]))))
        elif os.environ.get(PATH_ENV[k]):
            v = os.path.abspath(os.environ[PATH_ENV[k]])
        elif dflt is not None:
            v = os.path.abspath(os.path.join(edl_dir, dflt))
        else:
            v = None
        out[k] = v
    for k, v in edl_paths.items():                                 # keep unknown keys untouched
        out.setdefault(k, v)
    return out


def load(path, preview=False, use_proxy=None, path_overrides=None):
    """Load + normalise an EDL. Returns a dict with resolved paths and defaults filled in.
    path_overrides: {"video"|"photo"|"proxy"|"music"|"cache": dir} (CLI flags; beat the EDL)."""
    with open(path, "r", encoding="utf-8") as f:
        edl = json.load(f)
    edl_dir = os.path.dirname(os.path.abspath(path))
    edl["_path"] = os.path.abspath(path)
    edl["_name"] = os.path.splitext(os.path.basename(path))[0]
    paths = resolve_paths(edl.get("paths"), edl_dir, path_overrides)
    edl["paths"] = paths

    out = edl.setdefault("output", {})
    out.setdefault("path", os.path.join(edl_dir, edl["_name"] + ".mp4"))
    if not os.path.isabs(out["path"]):
        out["path"] = os.path.normpath(os.path.join(edl_dir, out["path"]))
    out.setdefault("w", 1080)
    out.setdefault("h", 1920)
    out.setdefault("fps", 30)
    out["fps"] = int(out["fps"])
    out.setdefault("crf", 17)
    out.setdefault("preset", "slow")
    if preview:
        out["w"], out["h"] = out["w"] // 2, out["h"] // 2
        out["w"] -= out["w"] % 2
        out["h"] -= out["h"] % 2
        root, ext = os.path.splitext(out["path"])
        out["path"] = root + "_preview" + ext
    edl["_preview"] = bool(preview)
    use_proxy = preview if use_proxy is None else use_proxy

    g = edl.setdefault("grade", {})
    g.setdefault("preset", "warm_pop")
    from grade import PRESETS
    if g["preset"] not in PRESETS:
        raise EDLError(f"unknown grade preset {g['preset']} (have {list(PRESETS)})")

    items = edl.get("items") or []
    if not items:
        raise EDLError("EDL has no items")
    seen = set()
    fps = out["fps"]
    for it in items:
        iid = it.get("id")
        if not iid or iid in seen:
            raise EDLError(f"item ids must be unique and non-empty (got {iid!r})")
        seen.add(iid)
        t = it.get("type", "video")
        it["type"] = t
        if t == "video":
            src = _resolve(it["src"], [paths["video"], edl_dir])
            if not src:
                raise EDLError(f"{iid}: video source not found: {it['src']} (looked in {paths['video']} and {edl_dir})")
            it["_src"] = src
            it["_decode_src"] = src
            if use_proxy and paths.get("proxy"):
                stem = os.path.splitext(os.path.basename(src))[0]
                px = os.path.join(paths["proxy"], stem + ".mp4")
                if os.path.exists(px):
                    it["_decode_src"] = os.path.abspath(px)
            info = probe(src)
            sm = it.get("speed_map")
            if sm:
                if not isinstance(sm, list) or any(not {"in", "out", "speed"} <= set(q) for q in sm):
                    raise EDLError(f"{iid}: speed_map must be a list of {{in, out, speed}}")
                sm = sorted(({"in": float(q["in"]), "out": float(q["out"]), "speed": float(q["speed"])} for q in sm),
                            key=lambda q: q["in"])
                for a, b in zip(sm, sm[1:]):
                    if abs(a["out"] - b["in"]) > 0.011:
                        raise EDLError(f"{iid}: speed_map segments must be contiguous ({a['out']} != {b['in']})")
                    b["in"] = a["out"]
                if any(q["speed"] <= 0 or q["out"] <= q["in"] for q in sm):
                    raise EDLError(f"{iid}: speed_map needs out > in and speed > 0")
                it.setdefault("in", sm[0]["in"])
                it.setdefault("out", sm[-1]["out"])
                if abs(float(it["in"]) - sm[0]["in"]) > 0.011 or abs(float(it["out"]) - sm[-1]["out"]) > 0.011:
                    raise EDLError(f"{iid}: speed_map must cover in..out exactly ({it['in']}-{it['out']})")
                sm[0]["in"], sm[-1]["out"] = float(it["in"]), float(it["out"])
                it["speed_map"] = sm
                it["speed"] = 1.0
            it.setdefault("in", 0.0)
            it.setdefault("out", info["duration"])
            it.setdefault("speed", 1.0)
            it["in"], it["out"], it["speed"] = float(it["in"]), float(it["out"]), float(it["speed"])
            if it["out"] > info["duration"] + 1e-3:
                log(f"WARNING {iid}: out={it['out']} > source duration {info['duration']:.3f}; clamped")
                it["out"] = info["duration"]
                if sm:
                    sm[-1]["out"] = it["out"]
            if not (0 <= it["in"] < it["out"]):
                raise EDLError(f"{iid}: need 0 <= in < out (in={it['in']}, out={it['out']})")
            if it["speed"] <= 0:
                raise EDLError(f"{iid}: speed must be > 0")
            src_fps = round(info["fps"]) if info["fps"] else fps
            it["_src_fps"] = src_fps
            if sm:
                from framing import time_map
                _, it["_n"] = time_map(it["in"], it["out"], sm, fps)
                it["_timemap"] = True
            else:
                ratio = src_fps * it["speed"] / fps  # source frames per output frame
                it["_timemap"] = abs(ratio - round(ratio)) > 1e-3 or ratio < 1 - 1e-3
                it["_n"] = max(1, int(round((it["out"] - it["in"]) / it["speed"] * fps)))
                if it["_timemap"] and ratio < 1 - 1e-3:
                    log(f"WARNING {iid}: speed {it['speed']} needs more frames than the {src_fps} fps source has "
                        f"(frames will be blended/repeated)")
            it.setdefault("frame_blend", "auto")
            it["tilt_deg"] = float(it.get("tilt_deg", 0.0))
            it.setdefault("rotate", 0)
            if int(it["rotate"]) % 90:
                raise EDLError(f"{iid}: rotate must be 0, 90, -90 or 180")
            it["rotate"] = int(it["rotate"]) % 360
            it["hflip"] = bool(it.get("hflip", False))
            it.setdefault("stabilize", False)
            it.setdefault("nat_sound", False)
            it.setdefault("speed_audio", "mute")
            if it["speed_audio"] not in ("mute", "pitch", "natural"):
                raise EDLError(f"{iid}: speed_audio must be mute|pitch|natural")
        elif t == "photo":
            src = _resolve_photo(it["src"], [paths["photo"], edl_dir])
            if not src:
                raise EDLError(f"{iid}: photo not found: {it['src']} (looked in {paths['photo']} and {edl_dir})")
            it["_src"] = it["_decode_src"] = src
            it.setdefault("dur", 3.0)
            it["_n"] = max(1, int(round(float(it["dur"]) * fps)))
            it["rotate"] = int(it.get("rotate", 0)) % 360
            it["hflip"] = bool(it.get("hflip", False))
            it["tilt_deg"] = float(it.get("tilt_deg", 0.0))
            it["stabilize"] = False
            it["nat_sound"] = False
            it["_timemap"] = False
        else:
            raise EDLError(f"{iid}: unknown item type {t}")
        it["frame"] = _norm_frame(it.get("frame"))
        it.setdefault("grade_adjust", {})
    edl["items"] = items

    ids = [it["id"] for it in items]
    tr = {}
    for t in edl.get("transitions", []) or []:
        a = t.get("after")
        if a not in ids:
            raise EDLError(f"transition after unknown item {a!r}")
        if a == ids[-1]:
            log(f"WARNING transition after last item {a} ignored")
            continue
        typ = t.get("type", "cut")
        if typ not in TRANSITION_DUR:
            raise EDLError(f"unknown transition type {typ} (have {list(TRANSITION_DUR)})")
        t = dict(t)
        t["type"] = typ
        t["dur"] = float(t.get("dur", TRANSITION_DUR[typ])) if typ != "cut" else 0.0
        tr[a] = t
    edl["_trans"] = tr

    texts = edl.get("texts", []) or []
    for tx in texts:
        tx.setdefault("style", "label")
        if tx["style"] not in TEXT_STYLES:
            raise EDLError(f"text style must be one of {TEXT_STYLES}")
        tx["start"], tx["end"] = float(tx["start"]), float(tx["end"])
    edl["texts"] = texts

    m = edl.get("music")
    if m and m.get("path"):
        found = _resolve(m["path"], [paths.get("music"), edl_dir])
        # not found: keep a path anyway (audio.py warns and renders without music)
        m["path"] = found or (m["path"] if os.path.isabs(m["path"]) else os.path.join(paths.get("music") or edl_dir, m["path"]))
    a = edl.setdefault("audio", {})
    a.setdefault("target_lufs", -14.0)
    a.setdefault("true_peak", -1.5)
    edl["timeline"] = compute_timeline(edl)
    return edl


def compute_timeline(edl):
    """Frame-quantised timeline. Each non-cut transition overlaps the two neighbouring items by
    round(dur*fps) frames, so the film shrinks by that amount."""
    fps = edl["output"]["fps"]
    items = edl["items"]
    tr = edl["_trans"]
    rows = []
    start = 0
    for i, it in enumerate(items):
        n = it["_n"]
        t_in = tr.get(items[i - 1]["id"]) if i > 0 else None
        t_out = tr.get(it["id"]) if i < len(items) - 1 else None
        o_in = int(round(t_in["dur"] * fps)) if t_in and t_in["type"] != "cut" else 0
        o_out = int(round(t_out["dur"] * fps)) if t_out and t_out["type"] != "cut" else 0
        if i > 0:
            start = rows[-1]["end_f"] - o_in
        rows.append(dict(id=it["id"], idx=i, type=it["type"], n=n, start_f=start, end_f=start + n,
                         o_in=o_in, o_out=o_out,
                         t_in=(t_in or {"type": "cut"})["type"] if i > 0 else None,
                         t_out=(t_out or {"type": "cut"})["type"] if i < len(items) - 1 else None,
                         trans_out=t_out))
    errs = []
    for r in rows:
        if r["o_in"] + r["o_out"] > r["n"]:
            errs.append(f"{r['id']}: transitions ({r['o_in']}+{r['o_out']} frames) longer than item ({r['n']} frames)")
        if r["o_out"]:
            nxt = rows[r["idx"] + 1]
            if r["o_out"] >= min(r["n"], nxt["n"]):
                errs.append(f"{r['id']}: transition overlap {r['o_out']} frames too long for neighbours")
    if errs:
        raise EDLError("; ".join(errs))
    total = rows[-1]["end_f"]
    for r in rows:
        r["start"], r["end"] = r["start_f"] / fps, r["end_f"] / fps
    return dict(rows=rows, total_f=total, total=total / fps, fps=fps)


def fmt_tc(sec):
    m, s = divmod(sec, 60)
    return f"{int(m)}:{s:06.3f}"


def timeline_report(edl):
    tl = edl["timeline"]
    fps = tl["fps"]
    lines = []
    lines.append(f"EDL {edl['_path']}  ->  {edl['output']['path']}")
    lines.append(f"{edl['output']['w']}x{edl['output']['h']} @ {fps} fps, grade={edl['grade']['preset']}")
    pth = edl.get("paths", {})
    lines.append("sources: " + ", ".join(f"{k}={pth.get(k)}" for k in ("video", "photo", "proxy", "music", "cache")
                                         if pth.get(k)))
    lines.append(f"{'#':>2} {'id':<8}{'type':<6}{'source':<16}{'src in-out':<14}{'spd':>5}{'dur':>8}"
                 f"{'start':>11}{'end':>11}  {'in-trans':<17}{'out-trans':<17}flags")
    for r, it in zip(tl["rows"], edl["items"]):
        src = os.path.basename(it["_src"])
        rng = f"{it['in']:.2f}-{it['out']:.2f}" if it["type"] == "video" else f"{float(it['dur']):.2f}s"
        spd = ("ramp" if it.get("speed_map") else f"{it['speed']:.2g}") if it["type"] == "video" else "-"
        tin = f"{r['t_in']}({r['o_in']/fps:.2f})" if r["t_in"] and r["t_in"] != "cut" else (r["t_in"] or "start")
        tout = f"{r['t_out']}({r['o_out']/fps:.2f})" if r["t_out"] and r["t_out"] != "cut" else (r["t_out"] or "end")
        flags = []
        if it.get("stabilize"):
            flags.append("stab")
        if it.get("nat_sound"):
            flags.append("nat")
        if it.get("rotate"):
            flags.append(f"rot{it['rotate']}")
        if it["frame"]["mode"] != "crop":
            flags.append(it["frame"]["mode"] + (f"{float(it['frame'].get('aspect', 0)):.2f}" if it["frame"]["mode"] == "box" else ""))
        if it.get("frame", {}).get("keys"):
            flags.append(f"keys{len(it['frame']['keys'])}")
        if it.get("tilt_deg"):
            flags.append(f"tilt{it['tilt_deg']:+g}")
        if it.get("speed_map"):
            flags.append("ramp " + "/".join(f"{q['speed']:g}" for q in it["speed_map"]))
        lines.append(f"{r['idx']+1:>2} {r['id']:<8}{it['type']:<6}{src[:15]:<16}{rng:<14}{spd:>5}{r['n']/fps:>8.3f}"
                     f"{fmt_tc(r['start']):>11}{fmt_tc(r['end']):>11}  {tin:<17}{tout:<17}{' '.join(flags)}")
    lines.append("Cut points (where the next item becomes the main picture; transition centre):")
    cuts = []
    for r in tl["rows"][1:]:
        c = (r["start_f"] + r["o_in"] / 2) / fps
        cuts.append(round(c, 3))
    lines.append("  " + ", ".join(f"{c:.3f}" for c in cuts))
    if edl["texts"]:
        lines.append("Texts:")
        for tx in edl["texts"]:
            warn = ""
            if tx["end"] > tl["total"] + 1e-6:
                warn = "  !! ends after film end"
            lines.append(f"   {tx['style']:<9}{fmt_tc(tx['start'])}-{fmt_tc(tx['end'])}  {tx['text']!r}{warn}")
    lines.append(f"TOTAL {fmt_tc(tl['total'])}  ({tl['total']:.3f} s, {tl['total_f']} frames)")
    return "\n".join(lines)


def timeline_json(edl):
    tl = edl["timeline"]
    return dict(total=tl["total"], total_frames=tl["total_f"], fps=tl["fps"],
                items=[dict(id=r["id"], start=r["start"], end=r["end"], start_frame=r["start_f"],
                            end_frame=r["end_f"], frames=r["n"], trans_in=r["t_in"], trans_out=r["t_out"],
                            overlap_in=r["o_in"] / tl["fps"], overlap_out=r["o_out"] / tl["fps"])
                       for r in tl["rows"]])

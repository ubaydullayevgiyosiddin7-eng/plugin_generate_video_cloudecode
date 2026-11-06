"""Picks-file helpers shared by edl_builder (auto layout), picks_check and reframe_preview (not a tool).

Picks schema (reviewer output; see examples/kuzgi_sayr/picks_*.json):
  {"picks": [{"id": "g06", "type": "video"|"photo", "src": "IMG_4545.MOV",
              "in": 0.9, "out": 4.4,            # video: HARD usable source limits (seconds as burned on the sheet)
              "ext_in": 0.6, "ext_out": 4.8,    # optional extension room (used only with use_ext)
              "speed": 0.5, "rotate": 0, "hflip": false, "highlight_t": 2.5,
              "dur_suggest": 3.5,               # OUTPUT seconds on screen
              "order": 14, "role": "hero|good|b_roll|hook|closer|end_card_bg", "place": "lake", "setup": "boat",
              "frame": {...engine frame...}}, ...]}
Schema drift seen in real files is normalised here: photo in/out null or numbers (ignored), dur_suggest
missing (falls back to screen_time_s / dur / the usable length), type missing (from the extension).
"""
import json
import os

PHOTO_EXT = (".heic", ".heif", ".jpg", ".jpeg", ".png", ".dng", ".tif", ".tiff", ".webp")
DEFAULTS = {
    "photo_cap": 4.6,      # longest a photo may stay on screen (s); None = unlimited
    "video_max": 6.0,      # no single video shot longer than this (s)
    "margin": 0.05,        # output seconds kept free at the end of a video's usable range (frame rounding)
    "dur_default": 2.4,    # dur_suggest when a pick has none
}
NON_FILM_ROLES = ("end_card_bg",)


def is_photo(p):
    t = p.get("type")
    if t in ("photo", "video"):
        return t == "photo"
    return str(p.get("src", "")).lower().endswith(PHOTO_EXT)


def norm_pick(p):
    """Copy of a pick with the defaults filled in (type, speed, rotate, hflip, float in/out)."""
    q = dict(p)
    q["type"] = "photo" if is_photo(q) else "video"
    q["speed"] = float(q.get("speed") or 1.0)
    q["rotate"] = int(q.get("rotate") or 0)
    q["hflip"] = bool(q.get("hflip"))
    if q["type"] == "video":
        if q.get("speed_map"):
            sm = [x if isinstance(x, dict) else {"in": x[0], "out": x[1], "speed": x[2]} for x in q["speed_map"]]
            q.setdefault("in", float(sm[0]["in"]))
            q.setdefault("out", float(sm[-1]["out"]))
        for k in ("in", "out", "ext_in", "ext_out", "highlight_t"):
            if q.get(k) is not None:
                q[k] = float(q[k])
        if q.get("in") is None:
            q["in"] = 0.0
    else:
        for k in ("in", "out", "ext_in", "ext_out"):      # meaningless for photos (schema drift)
            q.pop(k, None)
    return q


def load_picks(paths):
    """Merge one or more picks files -> (picks dict id -> normalised pick, list of ids in file order).
    Each file may be {"picks": [...]} or a bare list."""
    picks, order = {}, []
    for path in ([paths] if isinstance(paths, str) else paths):
        d = json.load(open(path, encoding="utf-8"))
        lst = d.get("picks", []) if isinstance(d, dict) else d
        for p in lst:
            if "id" not in p or "src" not in p:
                raise ValueError(f"{path}: pick without id/src: {str(p)[:120]}")
            if p["id"] in picks:
                raise ValueError(f"duplicate pick id {p['id']} ({path})")
            q = norm_pick(p)
            q["_file"] = os.path.abspath(path)
            picks[q["id"]] = q
            order.append(q["id"])
    return picks, order


def story_order(picks, ids=None):
    """ids sorted by the pick's `order` (story order) WITHIN each picks file - the files keep the order they
    were given in (one file per location) - file position breaking ties."""
    ids = list(ids if ids is not None else picks)
    pos = {i: k for k, i in enumerate(ids)}
    files = []
    for i in ids:
        if picks[i].get("_file") not in files:
            files.append(picks[i].get("_file"))
    return sorted(ids, key=lambda i: (files.index(picks[i].get("_file")),
                                      float(picks[i]["order"]) if picks[i].get("order") is not None else 50.0, pos[i]))


def load_durations(probe_json):
    """{file name: duration} from a tools/probe_media.py JSON."""
    d = json.load(open(probe_json, encoding="utf-8"))
    return {v["file"]: float(v["duration"]) for v in d.get("videos", []) if v.get("duration")}


def source_limits(p, src_dur=None, use_ext=False):
    """(lo, hi) source seconds a video pick may use: in/out (ext_in/ext_out with use_ext), never past the clip end."""
    lo = float(p.get("ext_in") if use_ext and p.get("ext_in") is not None else p.get("in") or 0.0)
    hi = p.get("ext_out") if use_ext and p.get("ext_out") is not None else p.get("out")
    hi = float(hi) if hi is not None else (src_dur if src_dur else 1e9)
    if src_dur:
        hi = min(hi, float(src_dur) - 0.02)
    return lo, hi


def usable_seconds(p, src_dur=None, use_ext=False):
    """Output seconds a video pick can fill (speed applied).  None for photos."""
    if is_photo(p):
        return None
    if p.get("speed_map"):
        sm = [x if isinstance(x, dict) else {"in": x[0], "out": x[1], "speed": x[2]} for x in p["speed_map"]]
        return sum((float(q["out"]) - float(q["in"])) / float(q["speed"]) for q in sm)
    lo, hi = source_limits(p, src_dur, use_ext)
    return max(0.0, (hi - lo) / float(p.get("speed") or 1.0))


def pick_cap(p, src_dur=None, use_ext=False, o_in=0.0, o_out=0.0, limit=None, photo_cap=DEFAULTS["photo_cap"],
             video_max=DEFAULTS["video_max"], margin=DEFAULTS["margin"]):
    """Longest cut-to-cut time D (output s) a pick may get.  Videos: the usable range minus half of each
    transition overlap (the overlap also shows source) minus a frame-rounding margin - never more.
    limit = per-pick {"max": s} from the layout spec (e.g. a posed portrait 1.5 s, a hook 3.6 s)."""
    lim = (limit or {}).get("max")
    if is_photo(p):
        c = float("inf") if photo_cap is None else float(photo_cap)
    else:
        c = usable_seconds(p, src_dur, use_ext) - (o_in + o_out) / 2.0 - margin
        if video_max:
            c = min(c, float(video_max))
    if lim is not None:
        c = min(c, float(lim))
    return c


def dur_want(p, cap=None):
    """Wanted on-screen seconds: dur_suggest (output s) or its known aliases, clamped to cap."""
    w = None
    for k in ("dur_suggest", "screen_time_s", "dur"):
        if p.get(k) is not None:
            w = float(p[k])
            break
    if w is None:
        u = usable_seconds(p)
        w = min(u, DEFAULTS["dur_default"]) if u else DEFAULTS["dur_default"]
    return min(w, cap) if cap is not None else w


def place_video(p, D, o_in=0.0, o_out=0.0, src_dur=None, use_ext=False, align="auto"):
    """Source second `a` shown AT the cut point for a video pick of cut-to-cut length D, so that the whole
    rendered range [a - o_in/2*speed, a + (D + o_out/2)*speed] stays inside the pick's limits.
    align: "in" = start at the reviewer's in-point (v2 behaviour); "highlight" = centre on highlight_t;
    "auto" = start at `in` unless that would leave highlight_t outside the visible part (then centre it).
    Returns (a, used_in, used_out, ok)."""
    sp = float(p.get("speed") or 1.0)
    lo, hi = source_limits(p, src_dur, use_ext)
    need = (D + (o_in + o_out) / 2.0) * sp
    if p.get("a") is not None:                       # explicit override
        s = float(p["a"]) - o_in / 2.0 * sp
    else:
        # start at the reviewer's `in`; with extension room (ext_in < in) grow the tail first, the head only
        # if the tail runs out
        s = min(max(float(p.get("in", lo)), lo), max(lo, hi - need))
        h = p.get("highlight_t")
        if h is not None and align in ("auto", "highlight"):
            vis0, vis1 = s + o_in / 2.0 * sp, s + need - (o_out / 2.0 + 0.2) * sp
            if align == "highlight" or not (vis0 <= float(h) <= vis1):
                s = float(h) - need / 2.0
        s = min(max(s, lo), max(lo, hi - need))
    used_in, used_out = s, s + need
    ok = used_in >= lo - 1e-3 and used_out <= hi + 1e-3
    return round(s + o_in / 2.0 * sp, 3), round(used_in, 3), round(used_out, 3), ok

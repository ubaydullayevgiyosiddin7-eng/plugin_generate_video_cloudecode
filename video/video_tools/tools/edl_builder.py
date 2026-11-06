"""Build an engine EDL from a beat-locked cut list (library + CLI) - the logic of the Magic Safari
build_edl_v3.py, made generic - or lay reviewer picks out on the music grid automatically.

  python tools/edl_builder.py --example out/example_edl.json [--media engine/test/media]
  python tools/edl_builder.py cutlist.json --out film_edl.json      cut list as JSON (no Python needed)
  then:  python engine/render.py film_edl.json --timeline

Automatic layout (picks + music plan -> every cut on a beat, every shot inside the reviewer's limits):
  python tools/edl_builder.py --layout layout.json --out film.json            sections/limits/texts in a spec
  python tools/edl_builder.py --picks picks_a.json picks_b.json --plan music_plan.json --out film.json
                              [--end final_accent] [--video-dir D --photo-dir D]   one section, quick start
  python tools/edl_builder.py --layout layout.json --out film.json --drop g09        local edit: only the
  python tools/edl_builder.py --layout layout.json --out film.json --insert t05 --after t04   neighbours change
  add --dry-run to print the range table only, --stretch-photos to accept longer photos when a section is
  short of material (otherwise that is an ERROR and nothing is written), --layout-help for the spec format.
  It prints a range table (used source vs the pick limits, highlight inside?) and writes <out>.layout.json.

Library use:
    sys.path.insert(0, "path/to/video_tools/tools"); from edl_builder import build_edl, dur_beats
    CUTS = [  # (id, D = cut-to-cut seconds on the music grid, spec, transition_after)
        ("k02", dur_beats(8, 0.6), dict(src="IMG_4427.MOV", a=0.15, speed=0.5, frame_extra={"box_y": 0.56}), None),
        ("i03", 3.0, dict(src="IMG_4353.jpg"), ("crossfade", 0.6)),
        ("s06", 3.6, dict(src="IMG_4369.MOV", speed_map=[(3.2, 4.0, 1.0), (4.0, 4.6, 0.5), (4.6, 6.2, 1.0)]), None),
    ]
    edl = build_edl(CUTS, frames=reframe_dict, texts=[...], music={"path": "bed.wav"}, paths={...})

Cut-list semantics
  * D is the distance between this item's cut point and the next one.  Cut points are cumulative
    sums of D, so if every D is a whole number of beats, every cut lands on a beat.  A transition of
    duration X after an item overlaps both neighbours by X/2 around the cut point (the visual cut
    centre stays on the beat): rendered length n = D + o_in/2 + o_out/2.
  * spec (video): src, a = source second shown AT the cut point (in = a - o_in/2*speed), speed,
    or speed_map = [(in, out, speed), ...] whose head is stretched/trimmed (tail extended if the head
    runs out) so the nominal length equals n.  rotate, hflip, tilt_deg, stabilize, nat_sound,
    nat_gain_db, duck_window, audio_gain_db (default 0 with nat_sound, else -10), mute, speed_audio,
    frame_blend, grade_adjust.
  * spec (photo, by extension or type="photo"): src; the frame keys (seconds from the item start)
    are scaled to the new duration.
  * framing: spec["frame"], else frames[frame_id or id]["frame"] (reframe-report format; a bare frame
    dict also works); frame_from=[ids] merges several reframes' keys; frame_extra={...} is merged in;
    mirror_keys=True mirrors cx (keys measured on the un-flipped view of an hflip item).
  * key_tweaks={id: {old_t: new_t}} moves individual key times (e.g. slow a whip pan down).
  * project_keys: every key is moved inside its valid window region (zoom >= 1, window inside the
    source) BEFORE the engine interpolates - a clamp that engages mid-move is a visible jolt.
"""
import argparse
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import ENGINE_DIR, PHOTO_EXT, safe_console, use_engine  # noqa: E402
from _picks import (DEFAULTS, NON_FILM_ROLES, dur_want, is_photo, load_durations, load_picks, norm_pick,  # noqa: E402
                    pick_cap, place_video, source_limits, story_order)

__all__ = ["build_edl", "build_item", "project_keys", "scaled_photo_keys", "fit_speed_map", "cut_points",
           "check_on_beats", "dur_beats", "SourceSizer", "auto_layout", "water_fill", "snap_section",
           "range_table", "build_from_layout", "LayoutError"]


def dur_beats(n, period):
    """n beats (or n/4 bars) of the music grid, in seconds."""
    return round(n * float(period), 6)


def scaled_photo_keys(keys, new_dur):
    """Photo keys are seconds from the item start: stretch them to the item's rendered duration."""
    old = max(float(k["t"]) for k in keys) or 1.0
    return [dict(k, t=round(float(k["t"]) * new_dur / old, 3)) for k in keys]


def fit_speed_map(speed_map, n):
    """[(in, out, speed)...] or [{in,out,speed}...] -> list of dicts whose nominal output length is n s.
    The first segment's in-point absorbs the difference; if it would go below 0 the rest comes from the
    tail (last segment's out-point)."""
    sm = [dict(q) if isinstance(q, dict) else {"in": q[0], "out": q[1], "speed": q[2]} for q in speed_map]
    for q in sm:
        q["in"], q["out"], q["speed"] = float(q["in"]), float(q["out"]), float(q["speed"])
    nominal = sum((q["out"] - q["in"]) / q["speed"] for q in sm)
    sm[0]["in"] = round(sm[0]["in"] - (n - nominal) * sm[0]["speed"], 3)
    if sm[0]["in"] < 0:      # not enough head room: take the rest from the tail
        sm[-1]["out"] = round(sm[-1]["out"] + (-sm[0]["in"] / sm[0]["speed"]) * sm[-1]["speed"], 3)
        sm[0]["in"] = 0.0
    if sm[0]["out"] <= sm[0]["in"]:
        raise ValueError(f"speed_map head segment collapsed (in {sm[0]['in']} >= out {sm[0]['out']}): item too short")
    return sm


class SourceSizer:
    """Upright source size (W, H) after autorotate + EDL rotate, looked up in the given folders."""

    def __init__(self, video_dirs=(), photo_dirs=()):
        self.video_dirs, self.photo_dirs = list(video_dirs), list(photo_dirs)
        self._cache = {}

    def find(self, src, photo):
        if os.path.isabs(src) and os.path.exists(src):
            return src
        for d in (self.photo_dirs if photo else self.video_dirs) + ["."]:
            p = os.path.join(d, src)
            if os.path.exists(p):
                return p
            if photo:
                stem = os.path.splitext(src)[0]
                for e in PHOTO_EXT:
                    for ee in (e, e.upper()):
                        if os.path.exists(os.path.join(d, stem + ee)):
                            return os.path.join(d, stem + ee)
        return None

    def info(self, it):
        photo = it["type"] == "photo"
        p = self.find(it["src"], photo)
        if p is None:
            return None
        if p not in self._cache:
            if photo:
                from PIL import Image, ImageOps
                im = Image.open(p)
                if p.lower().endswith((".heic", ".heif")):
                    import pillow_heif
                    pillow_heif.register_heif_opener()
                    im = Image.open(p)
                W, H = ImageOps.exif_transpose(im).size
                self._cache[p] = dict(w=W, h=H, duration=None)
            else:
                use_engine()
                from common import probe
                i = probe(p)
                self._cache[p] = dict(w=i["uw"], h=i["uh"], duration=i["duration"])
        d = dict(self._cache[p])
        if int(it.get("rotate", 0)) % 180:
            d["w"], d["h"] = d["h"], d["w"]
        return d

    def __call__(self, it):
        d = self.info(it)
        return (d["w"], d["h"]) if d else None


def project_keys(it, size, out_aspect=9 / 16):
    """Move every key inside its valid region (zoom >= 1, window inside the source) so the engine never
    has to hard-clamp mid-shot.  size = upright (W, H).  Returns a list of human-readable moves."""
    fr = it["frame"]
    if "keys" not in fr or size is None:
        return []
    W, H = size
    mode = fr.get("mode", "crop")
    a = out_aspect if mode == "crop" else (W / H if mode == "fit" else float(fr.get("aspect", 0.8)))
    bw, bh = ((H * a / W), 1.0) if W / H > a else (1.0, W / (a * H))
    moved = []
    last = {"cx": fr.get("cx0", fr.get("cx", 0.5)), "cy": fr.get("cy0", fr.get("cy", 0.5)), "zoom": fr.get("zoom0", fr.get("zoom", 1.0))}
    for k in fr["keys"]:
        for nm in ("cx", "cy", "zoom"):          # make every key explicit (engine carries values forward too)
            k[nm] = float(k.get(nm, last[nm]))
        last = {nm: k[nm] for nm in ("cx", "cy", "zoom")}
        if k["zoom"] < 1.0:
            moved.append(f"t={k['t']}: zoom {k['zoom']} -> 1.0")
            k["zoom"] = 1.0
        w, h = bw / k["zoom"], bh / k["zoom"]
        eps = 2e-4
        cx = min(max(k["cx"], w / 2 + eps), 1 - w / 2 - eps)
        cy = min(max(k["cy"], h / 2 + eps), 1 - h / 2 - eps)
        if abs(cx - k["cx"]) > 1e-4 or abs(cy - k["cy"]) > 1e-4:
            moved.append(f"t={k['t']}: ({k['cx']},{k['cy']})->({cx:.4f},{cy:.4f}) z={k['zoom']}")
        k["cx"], k["cy"] = round(cx, 4), round(cy, 4)
    return moved


def _frame_of(frames, fid):
    v = (frames or {}).get(fid)
    if v is None:
        return None
    return copy.deepcopy(v["frame"] if isinstance(v, dict) and "frame" in v else v)


def _is_photo(spec):
    return spec.get("type") == "photo" or (spec.get("type") != "video" and spec["src"].lower().endswith(PHOTO_EXT))


def build_item(iid, n, spec, o_in, frames=None, key_tweaks=None, grade_adjust=None):
    """One EDL item of rendered length n seconds (incl. transition overlaps)."""
    src = spec["src"]
    fid = spec.get("frame_id", iid)
    if _is_photo(spec):
        fr = copy.deepcopy(spec["frame"]) if "frame" in spec else _frame_of(frames, fid)
        fr = fr or {"mode": "crop"}
        if "keys" in fr and "frame" not in spec and spec.get("scale_keys", True):
            fr["keys"] = scaled_photo_keys(fr["keys"], n)
        it = dict(id=iid, type="photo", src=src, dur=round(n, 3), frame=fr)
        for k in ("rotate", "hflip", "tilt_deg"):
            if spec.get(k):
                it[k] = spec[k]
    else:
        it = dict(id=iid, type="video", src=src, rotate=spec.get("rotate", 0))
        if spec.get("hflip"):
            it["hflip"] = True
        if spec.get("speed_map"):
            sm = fit_speed_map(spec["speed_map"], n)
            it.update({"in": sm[0]["in"], "out": sm[-1]["out"], "speed": 1.0, "speed_map": sm})
        else:
            if "a" not in spec:
                raise ValueError(f"{iid}: video spec needs 'a' (source second at the cut point) or 'speed_map'")
            sp = float(spec.get("speed", 1.0))
            t_in = float(spec["a"]) - o_in / 2 * sp
            if t_in < 0:
                print(f"  WARNING {iid}: in-point {t_in:.3f} < 0 -> shifted to 0 (the cut is no longer at 'a')")
                t_in = 0.0
            it.update({"in": round(t_in, 3), "out": round(t_in + n * sp, 3), "speed": sp})
        if "frame" in spec:
            fr = copy.deepcopy(spec["frame"])
        elif spec.get("frame_from"):
            ks = []
            for f in spec["frame_from"]:
                ks += (_frame_of(frames, f) or {}).get("keys", [])
            ks.sort(key=lambda k: float(k["t"]))
            dedup = []
            for k in ks:
                if dedup and abs(float(dedup[-1]["t"]) - float(k["t"])) < 1e-3:
                    dedup[-1] = k                 # later reframe wins at a shared time
                else:
                    dedup.append(k)
            fr = dict(_frame_of(frames, spec["frame_from"][0]) or {"mode": "crop"}, keys=dedup)
        else:
            fr = _frame_of(frames, fid) or {"mode": "crop"}
        it["frame"] = fr
        for k in ("tilt_deg", "stabilize", "speed_audio", "frame_blend", "mute"):
            if spec.get(k) not in (None, False, 0):
                it[k] = spec[k]
        it["nat_sound"] = bool(spec.get("nat_sound"))
        it["audio_gain_db"] = spec.get("audio_gain_db", 0 if it["nat_sound"] else -10)
        for k in ("duck_window", "nat_gain_db"):
            if k in spec:
                it[k] = spec[k]
    ga = spec.get("grade_adjust") or (grade_adjust or {}).get(iid)
    if ga:
        it["grade_adjust"] = ga
    it["frame"].update(spec.get("frame_extra", {}))
    if spec.get("mirror_keys"):
        for k in it["frame"].get("keys", []):
            if "cx" in k:
                k["cx"] = round(1 - float(k["cx"]), 4)
        for e in ("cx0", "cx1", "cx"):
            if e in it["frame"]:
                it["frame"][e] = round(1 - float(it["frame"][e]), 4)
    tw = (key_tweaks or {}).get(iid)
    if tw:
        tw = {round(float(a), 3): float(b) for a, b in tw.items()}
        for k in it["frame"].get("keys", []):
            nt = tw.get(round(float(k["t"]), 3))
            if nt is not None:
                k["t"] = nt
        ts = [float(k["t"]) for k in it["frame"].get("keys", [])]
        if ts != sorted(ts):
            raise ValueError(f"{iid}: key order broken by key_tweaks {ts}")
    return it


def build_edl(cuts, frames=None, texts=None, music=None, output=None, paths=None, grade="warm_pop",
              audio=None, key_tweaks=None, grade_adjust=None, source_size=None, out_aspect=None, title=None,
              verbose=True, cache="cache"):
    """cuts: [(id, D, spec, transition_after|None), ...] (or dicts with id/D/spec/transition).
    transition_after: ("crossfade", 0.6) / ("dip_white", 0.6, {"dir": ...}) / {"type": ..., "dur": ...}.
    source_size: callable(item) -> (W, H) upright, for key projection (e.g. SourceSizer(...)); None = skip.
    cache: written as paths.cache unless paths already has one (default "cache" = <EDL folder>/cache, so the
    render cache lives in the project's work folder, never inside the kit); None = leave it out.
    Returns the EDL dict (json.dump it)."""
    paths = dict(paths or {})
    if cache is not None:
        paths.setdefault("cache", cache)
    output = dict(output or {})
    output.setdefault("w", 1080)
    output.setdefault("h", 1920)
    output.setdefault("fps", 30)
    oa = out_aspect or output["w"] / output["h"]
    rows = []
    for c in cuts:
        if isinstance(c, dict):
            rows.append((c["id"], float(c["D"]), c["spec"], c.get("transition")))
        else:
            rows.append((c[0], float(c[1]), c[2], c[3] if len(c) > 3 else None))
    items, transitions = [], []
    prev_tr = None
    t = 0.0
    for iid, D, spec, tr in rows:
        trd = None
        if tr:
            trd = dict(tr) if isinstance(tr, dict) else dict(type=tr[0], dur=float(tr[1]), **(tr[2] if len(tr) > 2 else {}))
            if trd["type"] == "cut":
                trd = None
        o_in = prev_tr["dur"] if prev_tr else 0.0
        o_out = trd["dur"] if trd else 0.0
        n = D + o_in / 2 + o_out / 2
        it = build_item(iid, n, spec, o_in, frames, key_tweaks, grade_adjust)
        if source_size is not None:
            info = source_size.info(it) if hasattr(source_size, "info") else None
            size = (info["w"], info["h"]) if info else source_size(it)
            if size is None and verbose:
                print(f"  NOTE {iid}: source {it['src']} not found - keys not projected")
            mv = project_keys(it, size, oa)
            if mv and verbose:
                print(f"  {iid}: projected key(s) into the source: " + "; ".join(mv))
            if info and info.get("duration") and it["type"] == "video" and it["out"] > info["duration"] + 1e-3:
                print(f"  WARNING {iid}: out {it['out']} > source duration {info['duration']:.3f} - the engine will "
                      f"clamp it and every later cut slides off the beat; move 'a' earlier or shorten D")
        items.append(it)
        if trd:
            transitions.append(dict(after=iid, **trd))
        t += D
        prev_tr = trd
    edl = {}
    if title:
        edl["title"] = title
    edl["output"] = output
    if paths:
        edl["paths"] = paths
    edl["grade"] = {"preset": grade} if isinstance(grade, str) else grade
    edl["items"] = items
    edl["transitions"] = transitions
    edl["texts"] = texts or []
    if music:
        edl["music"] = music
    edl["audio"] = audio or {"target_lufs": -14, "true_peak": -1.5}
    if verbose:
        print(f"built {len(items)} items, cut-grid total {t:.3f} s (= film length; transition overlaps are "
              f"split around the cuts)")
    return edl


# ----------------------------------------------------------------------------------------------
# automatic beat-snapped layout from reviewer picks (generalised from examples/kuzgi_sayr/build_kuzgi90.py v2)
# ----------------------------------------------------------------------------------------------

class LayoutError(Exception):
    pass


ENGINE_PASSTHROUGH = ("tilt_deg", "stabilize", "nat_sound", "nat_gain_db", "duck_window", "audio_gain_db", "mute",
                      "speed_audio", "frame_blend", "grade_adjust", "frame_extra", "mirror_keys")
MIN_SHOT_HARD = 0.3          # never cut a shot shorter than this, even when relaxing min_shot


def water_fill(wants, caps, total, mins=None):
    """Durations summing to `total`: start from `wants` (clamped to caps), then scale the free items
    proportionally - growing never above a cap, shrinking never below `mins`.  Returns (durations, shortfall)
    where shortfall > 0 means every item is at its cap and the material is that many seconds short."""
    n = len(wants)
    mins = list(mins) if mins is not None else [0.0] * n
    want = [min(max(float(w), m), float(c)) for w, c, m in zip(wants, caps, mins)]
    for _ in range(200):
        diff = total - sum(want)
        if abs(diff) < 1e-6:
            break
        free = [k for k in range(n) if (want[k] < caps[k] - 1e-9 if diff > 0 else want[k] > mins[k] + 1e-9)]
        if not free:
            break
        tot = sum(want[k] for k in free)
        if tot <= 1e-9:
            for k in free:
                want[k] = min(caps[k], want[k] + diff / len(free))
            continue
        f = 1.0 + diff / tot
        for k in free:
            want[k] = min(caps[k], max(mins[k], want[k] * f))
    return want, max(0.0, total - sum(want))


SNAP_TOL = 0.03             # a shot may exceed its cap by this much (caps keep a 0.05 s margin for frame rounding)
HALFBEAT_PENALTY = 1.0      # cost of a cut on a half-beat (between two grid points) in the 1st fallback
OFFGRID_PENALTY = 3.0       # cost of a cut on the 0.1 s raster in the 2nd fallback (timing deviations cost ~0.01-0.3)


def snap_section(caps, wants, t0, t1, grid, min_shot=1.0, mins=None, lattice=0.1, soft_over=None):
    """Cut times on the music grid for consecutive items filling [t0, t1] (cuts include t1).
    Targets come from water_fill (the v2 logic: dur_suggest grown/shrunk proportionally under the caps); the cut
    points are then chosen jointly by dynamic programming over the grid points: every shot <= its cap (hard,
    +SNAP_TOL) and >= MIN_SHOT_HARD; cost = relative squared deviation from the target + a penalty below
    min_shot / mins.  (Greedy cut-by-cut snapping painted itself into corners on a coarse rubato grid:
    0.8 s shots next to short caps, the leftovers dumped on the last shot.)  soft_over[k] > 0: item k may run
    that many seconds over its cap at a penalty (photos with --stretch-photos).  Half-beats (midpoints of the
    grid) are allowed at HALFBEAT_PENALTY each, so they are used only to avoid a shot under min_shot or a big
    timing deviation; a `lattice` s raster (OFFGRID_PENALTY each) only if nothing else fits the caps.
    Returns (cuts, notes); cuts is None if even that is impossible (not enough material)."""
    import numpy as np
    n = len(caps)
    mins = list(mins) if mins is not None else [0.0] * n
    soft = np.array(soft_over if soft_over is not None else [0.0] * n, dtype=float)
    targets = water_fill(wants, caps, t1 - t0, mins)[0]
    capv = np.array([float(c) if c != float("inf") else 1e9 for c in caps])
    tg = np.array([max(float(t), 0.3) for t in targets])
    lo_soft = np.array([max(min(min_shot, c), m) for c, m in zip(caps, mins)])
    on_grid = sorted({round(float(g), 4) for g in grid if t0 + 1e-6 < g < t1 - 1e-6})
    full = [t0] + on_grid + [t1]
    half = [round((a + b) / 2, 4) for a, b in zip(full, full[1:]) if b - a > 0.5]
    raster = [] if not lattice else [round(t0 + k * lattice, 4) for k in range(1, int((t1 - t0) / lattice))]
    for tier, pts_extra in enumerate((half, half + raster)):
        P = np.array(sorted({round(t0, 4), round(t1, 4)} | set(on_grid) | set(pts_extra)))
        G = len(P)
        hs = set(half)
        off = np.array([0.0 if (p in on_grid or k in (0, G - 1)) else (HALFBEAT_PENALTY if p in hs else OFFGRID_PENALTY)
                        for k, p in enumerate(P)])
        Dm = P[None, :] - P[:, None]                                  # Dm[i, j] = P[j] - P[i]
        INF = 1e18
        cost = np.full(G, INF)
        cost[0] = 0.0
        back = []
        for k in range(n):
            C = ((Dm - tg[k]) / tg[k]) ** 2
            C = C + np.where(Dm < lo_soft[k] - 1e-6, 2.0 + 10.0 * (lo_soft[k] - Dm) ** 2, 0.0)
            over = Dm - capv[k] - SNAP_TOL
            if soft[k] > 0:
                C = C + np.where(over > 0, 0.5 + 10.0 * (over / capv[k]) ** 2, 0.0)
            bad = (Dm < MIN_SHOT_HARD - 1e-6) | (over > soft[k])
            C = np.where(bad, INF, C)
            tot = cost[:, None] + C + off[None, :]
            if k == n - 1:
                tot[:, :G - 1] = INF                                  # the last item ends exactly at t1
            else:
                tot[:, G - 1] = INF
            arg = tot.argmin(axis=0)
            cost = tot[arg, np.arange(G)]
            cost[cost >= INF / 2] = INF
            back.append(arg)
        if cost[G - 1] < INF / 2:
            j, cuts = G - 1, []
            for k in range(n - 1, -1, -1):
                cuts.append(round(float(P[j]), 4))
                j = int(back[k][j])
            cuts.reverse()
            notes = [f"cut {c} is OFF the beat grid ({'on a half-beat' if c in hs else 'on the 0.1 s raster'}: needed "
                     f"to keep every shot inside its cap and >= min_shot{'' if soft.any() else '; --stretch-photos may help'})"
                     for c in cuts[:-1] if c not in on_grid]
            return cuts, notes
    return None, ["no layout fits inside the caps (not enough material for this section, even off the grid)"]


def _plan_value(plan, key):
    if key == "scene_change":
        j = plan.get("join") or {}
        if isinstance(j, dict) and j.get("scene_change") is not None:
            return float(j["scene_change"])
        if plan.get("scene_change") is not None:
            return float(plan["scene_change"])
        if plan.get("scene_changes"):
            return float(plan["scene_changes"][0])
    m = re.fullmatch(r"scene_change(\d+)", key)
    if m and plan.get("scene_changes"):
        return float(plan["scene_changes"][int(m.group(1)) - 1])
    v = plan.get(key)
    if isinstance(v, (int, float)):
        return float(v)
    raise LayoutError(f"the music plan has no numeric '{key}'")


def snap_time(t, how, plan):
    """Snap a time to the plan grid: downbeat|beat with _before/_after (or nearest)."""
    kind, _, side = how.partition("_")
    pts = sorted(float(x) for x in plan.get("downbeats" if kind in ("downbeat", "bar") else "beats", []))
    if not pts:
        raise LayoutError(f"snap '{how}': the plan has no {kind}s")
    if side == "before":
        c = [p for p in pts if p <= t + 1e-6]
        return c[-1] if c else pts[0]
    if side == "after":
        c = [p for p in pts if p >= t - 1e-6]
        return c[0] if c else pts[-1]
    return min(pts, key=lambda p: abs(p - t))


_TIME_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*(?:\.(?:start|end))?)\s*(?:([+-])\s*(\d+(?:\.\d+)?))?")


def resolve_time(expr, plan, prev_end=None, items=None):
    """number | "plan_key[+-s]" (scene_change, final_accent, recommended_end, ...) | "prev" (end of the previous
    section) | "ID.start/ID.end[+-s]" (layout item times) | {"ref": expr, "offset": s, "snap": "downbeat_before"}."""
    if expr is None:
        return None
    if isinstance(expr, (int, float)):
        return float(expr)
    if isinstance(expr, dict):
        t = resolve_time(expr.get("ref", expr.get("at")), plan, prev_end, items) + float(expr.get("offset", 0.0))
        return snap_time(t, expr["snap"], plan) if expr.get("snap") else t
    s = str(expr).strip()
    try:
        return float(s)
    except ValueError:
        pass
    m = _TIME_RE.fullmatch(s)
    if not m:
        raise LayoutError(f"cannot parse time expression {expr!r}")
    name, sign, off = m.group(1), m.group(2), float(m.group(3) or 0.0)
    if name == "prev":
        if prev_end is None:
            raise LayoutError("'prev' used by the first section")
        base = prev_end
    elif name.endswith((".start", ".end")) and items is not None:
        iid, edge = name.rsplit(".", 1)
        if iid not in items:
            raise LayoutError(f"time expression {expr!r}: no item {iid} in the layout")
        base = items[iid][0 if edge == "start" else 1]
    else:
        base = _plan_value(plan, name)
    return base + (-off if sign == "-" else off)


def section_grid(g, plan, t0, t1, fps=30):
    """Cut candidates strictly inside (t0, t1): "beats" (default) | "downbeats"/"bars" | "frames" (no music
    grid) | {"period": p, "from": expr} | {"list": [...]} | [...]."""
    if g in (None, "beats"):
        pts = plan.get("beats") or []
    elif g in ("downbeats", "bars"):
        pts = plan.get("downbeats") or []
    elif g in ("frames", "none"):
        pts = [k / fps for k in range(int(t0 * fps), int(t1 * fps) + 2)]
    elif isinstance(g, dict) and "period" in g:
        start = resolve_time(g.get("from", t0), plan)
        per = float(g["period"])
        k0 = int((t0 - start) // per) - 1
        pts = [start + k * per for k in range(k0, int((t1 - start) / per) + 2)]
    elif isinstance(g, dict) and "list" in g:
        pts = g["list"]
    elif isinstance(g, list):
        pts = g
    else:
        raise LayoutError(f"unknown grid {g!r}")
    if not pts and g not in ("frames", "none"):
        raise LayoutError(f"grid {g!r} is empty (does the music plan have beats?)")
    return sorted(round(float(p), 4) for p in pts if t0 + 1e-6 < float(p) < t1 - 1e-6)


def _norm_tr(tr):
    if not tr:
        return None
    d = dict(tr) if isinstance(tr, dict) else dict(type=tr[0], dur=float(tr[1]), **(tr[2] if len(tr) > 2 else {}))
    return None if d.get("type") == "cut" else d


class _Ctx:
    """Everything the layout needs to know about picks, limits and transitions."""

    def __init__(self, spec, base, picks, plan, durations, sizer):
        self.spec, self.base, self.plan = spec, base, plan
        d = dict(DEFAULTS)
        d.update({"min_shot": 1.0, "use_ext": False, "align": "auto"})
        d.update(spec.get("defaults") or {})
        self.d = d
        self.limits = spec.get("limits") or {}
        self.overrides = spec.get("overrides") or {}
        self.durations, self.sizer = durations, sizer
        self.picks = {}
        for i, p in picks.items():
            q = dict(p)
            ov = {k: v for k, v in self.overrides.get(i, {}).items() if k != "frame"}
            q.update(ov)
            self.picks[i] = norm_pick(q)
        self.photo_cap_of = {}

    def src_dur(self, p):
        if is_photo(p):
            return None
        if p["src"] in self.durations:
            return self.durations[p["src"]]
        if self.sizer is not None:
            info = self.sizer.info({"type": "video", "src": p["src"]})
            if info and info.get("duration"):
                self.durations[p["src"]] = info["duration"]
                return info["duration"]
        self.durations[p["src"]] = None
        return None

    def cap(self, i, o_in=0.0, o_out=0.0):
        p = self.picks[i]
        pc = self.photo_cap_of.get(i, self.d["photo_cap"])
        return pick_cap(p, self.src_dur(p), self.d["use_ext"], o_in, o_out, self.limits.get(i), pc,
                        self.d["video_max"], self.d["margin"])

    def want(self, i, cap):
        p = self.picks[i]
        lim = self.limits.get(i) or {}
        w = dur_want(p, cap)
        if lim.get("want") is not None:
            w = min(float(lim["want"]), cap)
        return w

    def min_of(self, i):
        return float((self.limits.get(i) or {}).get("min") or 0.0)


def _select_ids(sec, ctx, file_order, drop):
    if sec.get("ids") is not None:
        ids = list(sec["ids"])
        missing = [i for i in ids if i not in ctx.picks]
        if missing:
            raise LayoutError(f"section {sec.get('name')}: unknown pick ids {missing}")
    else:
        pref = sec.get("prefix")
        prefs = [pref] if isinstance(pref, str) else (pref or [])
        roles = set(sec.get("exclude_roles", NON_FILM_ROLES))
        sel = [i for i in file_order if (not prefs or any(i.startswith(x) for x in prefs))
               and ctx.picks[i].get("role") not in roles
               and (sec.get("place") is None or ctx.picks[i].get("place") == sec["place"])]
        ids = story_order(ctx.picks, sel)
    ids = [i for i in ids if i not in drop]
    for key, pos in (("first", 0), ("last", None)):
        if sec.get(key) and sec[key] not in drop:
            if sec[key] in ids:
                ids.remove(sec[key])
            ids.insert(len(ids) if pos is None else pos, sec[key])
    for mv in sec.get("move", []):
        a, how, ref = mv
        if a in ids and ref in ids and a != ref:
            ids.remove(a)
            ids.insert(ids.index(ref) + (1 if how == "after" else 0), a)
    return ids


def _transitions(spec, sections):
    tr = {}
    for s in sections:
        t = _norm_tr(s.get("transition_out"))
        if t and s["ids"]:
            tr[s["ids"][-1]] = t
    for k, v in (spec.get("transitions") or {}).items():
        tr[k] = _norm_tr(v)
    return {k: v for k, v in tr.items() if v}


def _overlaps(order, tr):
    o_in, o_out = {}, {}
    for k, i in enumerate(order):
        o_in[i] = tr[order[k - 1]]["dur"] if k > 0 and order[k - 1] in tr else 0.0
        o_out[i] = tr[i]["dur"] if i in tr and k < len(order) - 1 else 0.0
    return o_in, o_out


def _load_plan(spec, base):
    p = spec.get("plan")
    if isinstance(p, dict):
        return p
    if not p:
        raise LayoutError("the layout needs a music plan ('plan': music_plan_*.json from music_bed.py / music_beats.py)")
    return json.load(open(os.path.join(base, p), encoding="utf-8"))


def _layout_sections(spec, ctx, file_order, drop, stretch_photos, errors, warnings):
    """Full layout: material check, then cut-by-cut snapping per section.  Returns (sections, rows)."""
    plan = ctx.plan
    secs, prev_end, used = [], None, set()
    for n_, sec in enumerate(spec.get("sections") or []):
        s = dict(sec)
        s.setdefault("name", f"section{n_ + 1}")
        s["ids"] = _select_ids(s, ctx, file_order, drop)
        dup = used.intersection(s["ids"])
        if dup:
            raise LayoutError(f"pick(s) {sorted(dup)} are in two sections")
        used.update(s["ids"])
        s["t0"] = resolve_time(s.get("start", "prev" if n_ else 0.0), plan, prev_end)
        s["t1"] = resolve_time(s["end"], plan, s["t0"])
        if s["t1"] <= s["t0"] + 0.2:
            raise LayoutError(f"section {s['name']}: end {s['t1']:.3f} <= start {s['t0']:.3f}")
        if prev_end is not None and abs(s["t0"] - prev_end) > 1e-3:
            raise LayoutError(f"section {s['name']} starts at {s['t0']:.3f} but the previous one ends at {prev_end:.3f} "
                              "(sections must be contiguous; use start 'prev')")
        prev_end = s["t1"]
        if not s["ids"]:
            raise LayoutError(f"section {s['name']} has no picks")
        if "photo_cap" in s:
            for i in s["ids"]:
                ctx.photo_cap_of[i] = s["photo_cap"]
        s["grid"] = section_grid(s.get("grid", "beats"), plan, s["t0"], s["t1"])
        secs.append(s)
    if not secs:
        raise LayoutError("the layout spec has no sections")
    order = [i for s in secs for i in s["ids"]]
    tr = _transitions(spec, secs)
    o_in, o_out = _overlaps(order, tr)
    rows = []
    for s in secs:
        ids, total = s["ids"], s["t1"] - s["t0"]
        caps = [ctx.cap(i, o_in[i], o_out[i]) for i in ids]
        short = total - sum(caps)
        s["material"] = dict(length=round(total, 3), sum_caps=round(sum(caps), 3),
                             sum_want=round(sum(ctx.want(i, c) for i, c in zip(ids, caps)), 3))
        if short > 1e-3:      # stretchable: photos without a hard per-pick limit (limits.max, e.g. a posed portrait)
            photos = [k for k, i in enumerate(ids)
                      if is_photo(ctx.picks[i]) and (ctx.limits.get(i) or {}).get("max") is None]
            msg = (f"section {s['name']} ({s['t0']:.2f}-{s['t1']:.2f} s = {total:.2f} s) has only {sum(caps):.2f} s of "
                   f"usable material: SHORT by {short:.2f} s")
            if stretch_photos and photos:
                step = max([b - a for a, b in zip([s["t0"]] + s["grid"], s["grid"] + [s["t1"]])] or [0.6])
                extra = short + min(step, 1.0)
                wsum = sum(ctx.want(ids[k], caps[k]) for k in photos) or 1.0
                for k in photos:
                    add = extra * ctx.want(ids[k], caps[k]) / wsum
                    ctx.photo_cap_of[ids[k]] = caps[k] + add
                    warnings.append(f"{ids[k]}: photo cap raised {caps[k]:.2f} -> {caps[k] + add:.2f} s (--stretch-photos)")
                caps = [ctx.cap(i, o_in[i], o_out[i]) for i in ids]
                warnings.append(msg + " -> stretched photos")
            else:
                errors.append(msg + ". Add picks, allow extension room (use_ext with ext_in/ext_out), end the "
                              "section earlier (music), or accept longer photos (--stretch-photos)." +
                              ("" if photos else " (no photos in this section to stretch)"))
        wants = [ctx.want(i, c) for i, c in zip(ids, caps)]
        mins = [min(ctx.min_of(i), c) for i, c in zip(ids, caps)]
        soft = [1.0 if stretch_photos and is_photo(ctx.picks[i]) and (ctx.limits.get(i) or {}).get("max") is None
                else 0.0 for i in ids]
        cuts, notes = snap_section(caps, wants, s["t0"], s["t1"], s["grid"], ctx.d["min_shot"], mins, soft_over=soft)
        if cuts is None:     # infeasible: show where it is short (rows flagged), nothing gets written
            if not any(e.startswith(f"section {s['name']} ") for e in errors):
                errors.append(f"section {s['name']}: " + notes[0])
            durs = water_fill(wants, [float("inf")] * len(ids), total)[0]
            cuts, acc = [], s["t0"]
            for d_ in durs:
                acc += d_
                cuts.append(round(acc, 4))
            cuts[-1] = round(s["t1"], 4)
        else:
            warnings.extend(f"section {s['name']}: {x}" for x in notes)
        prev = s["t0"]
        for i, c in zip(ids, cuts):
            rows.append(dict(id=i, section=s["name"], start=round(prev, 4), D=round(c - prev, 4),
                             transition=tr.get(i)))
            prev = c
    return secs, rows


def _grid_of(prev_layout, section):
    for s in prev_layout.get("sections", []):
        if s["name"] == section:
            return list(s.get("grid") or []), s
    return [], None


def _window_edit(orig, ctx, prev_layout, drop_id=None, insert=None):
    """Local edit of a previous layout: drop one item or insert one pick, then re-lay out only the smallest
    window of neighbours (same section, widened one item per side until it fits the caps); every cut outside
    the window keeps its time.  Render caches are content-keyed, so items that merely shift in time and keep
    their length and transitions are reused.  Returns (rows, changed ids)."""
    ids = [r["id"] for r in orig]
    if drop_id is not None:
        if drop_id not in ids:
            raise LayoutError(f"--drop {drop_id}: not in the previous layout")
        k = ids.index(drop_id)
        what = f"--drop {drop_id}"
    else:
        x_id, after = insert
        if x_id in ids:
            raise LayoutError(f"--insert {x_id}: already in the layout")
        if x_id not in ctx.picks:
            raise LayoutError(f"--insert {x_id}: not in the picks")
        if after not in ids:
            raise LayoutError(f"--insert {x_id} --after {after}: {after} is not in the layout")
        k = ids.index(after)
        what = f"--insert {x_id}"
    sec = orig[k]["section"]
    sec_idx = [j for j, r in enumerate(orig) if r["section"] == sec]
    s_lo, s_hi = min(sec_idx), max(sec_idx)
    grid, _ = _grid_of(prev_layout, sec)
    old = {r["id"]: r for r in orig}

    def new_rows():
        rows = [dict(r) for r in orig]
        if drop_id is not None:
            gone = rows.pop(k)
            if k > 0 and gone.get("transition"):
                rows[k - 1]["transition"] = gone["transition"]
            return rows
        x = dict(id=x_id, section=sec, start=None, D=None, transition=rows[k].get("transition"))
        rows[k]["transition"] = None
        rows.insert(k + 1, x)
        return rows

    rows = new_rows()
    order = [r["id"] for r in rows]
    o_in, o_out = _overlaps(order, {r["id"]: r["transition"] for r in rows if r.get("transition")})
    lo, hi = max(s_lo, k - 1), min(s_hi, k + 1)
    if drop_id is None:
        lo = k
    while True:
        t0 = orig[lo]["start"]
        t1 = orig[hi]["start"] + orig[hi]["D"]
        win = [r["id"] for r in orig[lo:hi + 1] if r["id"] != drop_id]
        if drop_id is None:
            win.insert(win.index(orig[k]["id"]) + 1, x_id)
        if win:
            caps = [ctx.cap(i, o_in[i], o_out[i]) for i in win]
            wants = [old[i]["D"] if i in old else ctx.want(i, c) for i, c in zip(win, caps)]
            mins = [min(ctx.min_of(i), c) for i, c in zip(win, caps)]
            g = sorted(set(grid) | {round(r["start"], 4) for r in orig[lo + 1:hi + 1]})
            cuts, notes = snap_section(caps, wants, t0, t1, g, ctx.d["min_shot"], mins)
            if cuts is not None:
                break
        if lo <= s_lo and hi >= s_hi:
            raise LayoutError(f"{what}: section {sec} cannot absorb the change inside the caps; "
                              "run a full re-layout instead (without --drop/--insert)")
        lo, hi = max(s_lo, lo - 1), min(s_hi, hi + 1)
    by = {r["id"]: r for r in rows}
    prev = t0
    for i, c in zip(win, cuts):
        by[i]["start"], by[i]["D"] = round(prev, 4), round(c - prev, 4)
        prev = c
    changed = [i for i in win if i not in old or abs(old[i]["D"] - by[i]["D"]) > 1e-4]
    for r in rows:           # a moved transition changes the neighbours' overlaps too
        if r["id"] in old and r["id"] not in changed:
            o = dict(old[r["id"]])
            if _norm_tr(o.get("transition")) != _norm_tr(r.get("transition")):
                changed.append(r["id"])
    o_in0, o_out0 = _overlaps(ids, {r["id"]: _norm_tr(r.get("transition")) for r in orig if r.get("transition")})
    for i in order:
        if i in old and i not in changed and (o_in0.get(i) != o_in[i] or o_out0.get(i) != o_out[i]):
            changed.append(i)
    return rows, changed, [f"{what}: {x}" for x in notes]


def _row_spec(ctx, r):
    p = ctx.picks[r["id"]]
    ov = ctx.overrides.get(r["id"], {})
    if is_photo(p):
        s = dict(src=p["src"], type="photo", frame_id=r["id"])
        for k in ("rotate", "hflip", "tilt_deg", "grade_adjust", "frame_extra"):
            if p.get(k):
                s[k] = p[k]
    else:
        s = dict(src=p["src"], type="video", speed=p["speed"], rotate=p["rotate"], hflip=p["hflip"], frame_id=r["id"])
        if p.get("speed_map"):
            s["speed_map"] = p["speed_map"]
        else:
            s["a"] = r["a"]
        for k in ENGINE_PASSTHROUGH:
            if p.get(k) not in (None, False):
                s[k] = p[k]
    if "frame" in ov:
        s["frame"] = ov["frame"]
    return s


def _finish_rows(rows, ctx, errors, warnings):
    """Placement (source in-point) of every video row + the range checks."""
    order = [r["id"] for r in rows]
    tr = {r["id"]: r["transition"] for r in rows if r.get("transition")}
    o_in, o_out = _overlaps(order, tr)
    ms = ctx.d["min_shot"]
    for r in rows:
        i = r["id"]
        p = ctx.picks[i]
        r["o_in"], r["o_out"] = o_in[i], o_out[i]
        r["cap"] = round(ctx.cap(i, o_in[i], o_out[i]), 3)
        r["want"] = round(ctx.want(i, r["cap"]), 3)
        r["type"] = "photo" if is_photo(p) else "video"
        r["flags"] = []
        if r["D"] > r["cap"] + 0.02:
            if r["type"] == "video":
                errors.append(f"{i}: {r['D']:.2f} s on screen but the pick allows {r['cap']:.2f} s")
            else:
                r["flags"].append("OVER CAP")
                warnings.append(f"{i}: photo {r['D']:.2f} s > cap {r['cap']:.2f} s")
        if r["D"] < min(ms, r["cap"]) - 0.02:
            r["flags"].append("short")
        if r["type"] == "video":
            src_dur = ctx.src_dur(p)
            lo, hi = source_limits(p, src_dur, ctx.d["use_ext"])
            r["lo"], r["hi"] = round(lo, 3), round(hi, 3)
            if p.get("speed_map"):
                sm = fit_speed_map(p["speed_map"], r["D"] + (o_in[i] + o_out[i]) / 2)
                r["a"], r["used_in"], r["used_out"] = None, sm[0]["in"], sm[-1]["out"]
                ok = r["used_in"] >= lo - 1e-3 and r["used_out"] <= hi + 1e-3
            else:
                r["a"], r["used_in"], r["used_out"], ok = place_video(p, r["D"], o_in[i], o_out[i], src_dur,
                                                                      ctx.d["use_ext"], ctx.d["align"])
            if not ok:
                errors.append(f"{i}: uses source {r['used_in']:.2f}-{r['used_out']:.2f} outside its limits "
                              f"{lo:.2f}-{hi:.2f}")
                r["flags"].append("OVERRUN")
            if src_dur is None:
                r["flags"].append("dur?")
            h = p.get("highlight_t")
            if h is not None:
                sp = p["speed"]
                v0 = r["used_in"] + o_in[i] / 2 * sp
                v1 = r["used_out"] - o_out[i] / 2 * sp
                r["highlight"] = "in" if v0 - 1e-3 <= h <= v1 + 1e-3 else "OUT"
                if r["highlight"] == "OUT":
                    warnings.append(f"{i}: highlight_t {h} is outside the visible source {v0:.2f}-{v1:.2f}")
            if ctx.d["use_ext"] and (r["used_in"] < float(p["in"]) - 1e-3 or
                                     (p.get("out") is not None and r["used_out"] > float(p["out"]) + 1e-3)):
                r["flags"].append("ext")
        r["spec"] = _row_spec(ctx, r)
    return rows


def range_table(rows):
    """Human-readable table: on-screen time vs caps, used source vs pick limits, highlight inside?"""
    L = [f"{'#':>2} {'id':<6}{'sect':<8}{'type':<6}{'start':>7}{'D':>6}{'cap':>6}{'want':>6}  "
         f"{'used src':<13}{'limits':<13}{'hl':<4}trans / flags"]
    for k, r in enumerate(rows):
        used = f"{r['used_in']:.2f}-{r['used_out']:.2f}" if r["type"] == "video" else "photo"
        lim = f"{r['lo']:.2f}-{r['hi']:.2f}" if r["type"] == "video" else ""
        cap = "-" if r["cap"] == float("inf") else f"{r['cap']:.2f}"
        tr = f"{r['transition']['type']} {r['transition']['dur']:g}" if r.get("transition") else ""
        L.append(f"{k + 1:>2} {r['id']:<6}{r['section'][:7]:<8}{r['type']:<6}{r['start']:7.2f}{r['D']:6.2f}{cap:>6}"
                 f"{r['want']:6.2f}  {used:<13}{lim:<13}{r.get('highlight', ''):<4}{tr} {' '.join(r['flags'])}")
    return "\n".join(L)


def auto_layout(spec, base_dir=".", picks=None, file_order=None, durations=None, sizer=None, prev_layout=None,
                drop=(), insert=None, stretch_photos=False):
    """Lay reviewer picks out on the music grid.  spec: layout dict (see LAYOUT_DOC); prev_layout + drop/insert =
    local edit that keeps every other cut time (and so every other item's render cache).
    Returns dict(rows, sections, cuts (for build_edl), errors, warnings, changed)."""
    if picks is None:
        picks, file_order = load_picks([os.path.join(base_dir, p) for p in spec["picks"]])
    plan = _load_plan(spec, base_dir)
    ctx = _Ctx(spec, base_dir, picks, plan, dict(durations or {}), sizer)
    drop_all = set(spec.get("drop") or []) | set(drop or [])
    errors, warnings = [], []
    changed = None
    if prev_layout is not None and (drop or insert):
        rows = [dict(r, transition=_norm_tr(r.get("transition"))) for r in prev_layout["rows"]]
        for s in prev_layout.get("sections", []):
            if "photo_cap" in s:
                for r in rows:
                    if r["section"] == s["name"]:
                        ctx.photo_cap_of[r["id"]] = s["photo_cap"]
        for c in prev_layout.get("photo_caps", {}).items():
            ctx.photo_cap_of[c[0]] = c[1]
        changed = set()
        for d in drop or []:
            rows, ch, nt = _window_edit(rows, ctx, prev_layout, drop_id=d)
            changed.update(ch)
            warnings.extend(nt)
        if insert:
            rows, ch, nt = _window_edit(rows, ctx, prev_layout, insert=insert)
            changed.update(ch)
            warnings.extend(nt)
        secs = prev_layout.get("sections", [])
    else:
        secs, rows = _layout_sections(spec, ctx, file_order or list(picks), drop_all, stretch_photos, errors, warnings)
    rows = _finish_rows(rows, ctx, errors, warnings)
    total = rows[-1]["start"] + rows[-1]["D"]
    cuts = [(r["id"], r["D"], r["spec"], (r["transition"]["type"], r["transition"]["dur"]) if r.get("transition") else None)
            for r in rows]
    used = {r["id"] for r in rows}
    unused = [i for i in (file_order or picks) if i not in used and i not in drop_all
              and ctx.picks[i].get("role") not in NON_FILM_ROLES]
    if unused:
        warnings.append(f"picks not in any section: {unused}")
    sec_out = [dict(name=s["name"], t0=s["t0"], t1=s["t1"], grid=s["grid"],
                    **({"photo_cap": s["photo_cap"]} if "photo_cap" in s else {}),
                    **({"material": s["material"]} if "material" in s else {})) for s in secs]
    return dict(rows=rows, sections=sec_out, cuts=cuts, errors=errors, warnings=warnings, total=round(total, 4),
                changed=changed, plan=plan, ctx=ctx, photo_caps=dict(ctx.photo_cap_of))


def resolve_texts(texts, rows, plan):
    items = {r["id"]: (r["start"], r["start"] + r["D"]) for r in rows}
    out = []
    for t in texts or []:
        t = dict(t)
        for k in ("start", "end"):
            t[k] = round(resolve_time(t[k], plan, None, items), 3)
        out.append(t)
    return out


LAYOUT_DOC = """Layout spec (JSON; relative paths are relative to the spec file):
  {"picks": ["picks_bog.json", "picks_minora.json"],      reviewer picks (tools/_picks.py schema)
   "plan": "music/music_plan_kuzgi90.json",               music plan: beats, downbeats, scene_change, final_accent...
   "probe": "reports/probe.json",                         optional: source durations (else ffprobe via paths.video)
   "paths": {"video": "D:/raw", "photo": "photos", "music": "music"},
   "output": {"path": "film.mp4", "w": 1080, "h": 1920, "fps": 30},
   "music": {"path": "music_bed.wav", "gain_db": 0, "fade_out": 0.3},   default: the plan's rendered bed
   "grade": "warm_pop",
   "defaults": {"photo_cap": 4.6, "video_max": 6.0, "min_shot": 1.0, "use_ext": false, "align": "auto", "margin": 0.05},
   "drop": ["t05"],                                       picks to leave out
   "limits": {"g09": {"max": 1.5}, "g07": {"max": 3.6, "want": 3.1}, "x": {"min": 2.0}},   per-pick on-screen limits
   "overrides": {"t03": {"out": 1.8}, "g02": {"frame": {...}}},   merged into the pick (out/in tighten the limits)
   "transitions": {"g17": ["dip_white", 0.6]},            extra transitions (after id)
   "sections": [                                          contiguous, in film order
     {"name": "garden", "prefix": "g", "first": "g07", "move": [["g04", "after", "g15"]],
      "start": 0, "end": "scene_change", "grid": "beats", "transition_out": ["dip_white", 0.6]},
     {"name": "tower", "prefix": "t", "start": "prev",
      "end": {"ref": "final_accent", "offset": -1.8, "snap": "downbeat_before"}, "grid": {"period": 0.6, "from": "scene_change"},
      "transition_out": ["crossfade", 0.6]},
     {"name": "end", "ids": ["t07"], "start": "prev", "end": "recommended_end+0.5", "photo_cap": null}],
   "texts": [{"text": "Title", "start": 0.25, "end": "g07.end-0.15", "style": "title"}]}
Sections take explicit "ids" (in that order) or select by "prefix"/"place" in story order (pick "order"),
skipping role end_card_bg.  Times: number | plan key [+-s] | "prev" | "ID.start"/"ID.end" [+-s] (texts) |
{"ref", "offset", "snap": downbeat_before|downbeat_after|downbeat|beat...}.  Grid: beats | downbeats |
frames | {"period", "from"} | {"list"} | [..].  Caps: videos never leave in/out (ext_in/ext_out with use_ext),
counting half of each transition overlap; photos <= photo_cap; limits.max per pick.  A section with less
material than time is an ERROR (nothing written) unless --stretch-photos spreads the gap over its photos."""


def build_from_layout(spec_path, out, drop=(), insert=None, prev=None, stretch_photos=False, dry_run=False,
                      spec=None, verbose=True):
    """CLI driver: layout -> range table -> EDL + <out>.layout.json.  Returns an exit code."""
    base = os.path.dirname(os.path.abspath(spec_path)) if spec_path else os.getcwd()
    if spec is None:
        spec = json.load(open(spec_path, encoding="utf-8"))
    paths = dict(spec.get("paths") or {})
    pdir = lambda k: os.path.normpath(os.path.join(base, paths[k])) if paths.get(k) else base  # noqa: E731
    sizer = SourceSizer([pdir("video")], [pdir("photo")])
    durations = load_durations(os.path.join(base, spec["probe"])) if spec.get("probe") else {}
    layout_path = os.path.splitext(out)[0] + ".layout.json"
    prev_layout = None
    if drop or insert:
        pp = prev or layout_path
        if not os.path.exists(pp):
            print(f"ERROR --drop/--insert need the previous layout ({pp}); build once without them first")
            return 2
        prev_layout = json.load(open(pp, encoding="utf-8"))
    try:
        res = auto_layout(spec, base, durations=durations, sizer=sizer, prev_layout=prev_layout, drop=drop,
                          insert=insert, stretch_photos=stretch_photos)
    except LayoutError as e:
        print(f"LAYOUT ERROR: {e}")
        return 2
    for s in res["sections"]:
        m = s.get("material")
        if m:
            print(f"section {s['name']:<8} {s['t0']:7.2f}-{s['t1']:7.2f} s ({m['length']:.2f} s): material "
                  f"{m['sum_caps']:.2f} s max / {m['sum_want']:.2f} s suggested, {len(s['grid'])} grid points")
    print(range_table(res["rows"]))
    print(f"total {res['total']:.3f} s (cut grid)")
    if prev_layout is not None:
        print(f"local edit: re-render {sorted(res['changed'])}; every other item keeps its cut times and cache")
    for w in res["warnings"]:
        print("  WARNING " + w)
    for e in res["errors"]:
        print("  ERROR " + e)
    if res["errors"]:
        print("nothing written (fix the errors above)")
        return 2
    if dry_run:
        return 0
    out_dir = os.path.dirname(os.path.abspath(out))
    rebase = lambda p: p if os.path.isabs(p) else \
        os.path.relpath(os.path.normpath(os.path.join(base, p)), out_dir).replace("\\", "/")  # noqa: E731
    epaths = {k: (rebase(v) if isinstance(v, str) else v) for k, v in paths.items()}
    output = dict(spec.get("output") or {})
    if output.get("path"):
        output["path"] = rebase(output["path"])
    music = spec.get("music")
    if music is None and (res["plan"].get("render") or {}).get("file"):
        music = {"path": res["plan"]["render"]["file"], "gain_db": 0, "fade_out": 0.3}
    elif music and music.get("path") and not os.path.isabs(music["path"]) and not paths.get("music"):
        music = dict(music, path=rebase(music["path"]))
    texts = resolve_texts(spec.get("texts"), res["rows"], res["plan"])
    edl = build_edl(res["cuts"], frames=res["ctx"].picks, texts=texts, music=music, output=output, paths=epaths,
                    grade=spec.get("grade", "warm_pop"), audio=spec.get("audio"), title=spec.get("title"),
                    source_size=sizer, verbose=verbose)
    os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(edl, f, ensure_ascii=False, indent=1)
    lay = {"spec": os.path.abspath(spec_path) if spec_path else None, "total": res["total"],
           "sections": res["sections"], "photo_caps": {k: v for k, v in res["photo_caps"].items()},
           "rows": [{k: r[k] for k in ("id", "section", "start", "D", "transition")} for r in res["rows"]]}
    with open(layout_path, "w", encoding="utf-8") as f:
        json.dump(lay, f, ensure_ascii=False, indent=1)
    off = check_on_beats(res["cuts"], sorted(set(res["plan"].get("beats", [])) |
                                             {g for s in res["sections"] for g in s.get("grid", [])}), tol=0.02)
    print("off-grid cuts:", off or "none")
    print(f"wrote {out}\n      {layout_path} (for --drop/--insert)")
    return 0


def cut_points(cuts, t0=0.0):
    """Timeline seconds of every cut (cumulative D), first item start excluded."""
    out, t = [], t0
    for c in cuts[:-1]:
        t += float(c["D"] if isinstance(c, dict) else c[1])
        out.append(round(t, 4))
    return out


def check_on_beats(cuts, beats, tol=0.02, t0=0.0):
    """Cuts that are not within tol s of a beat (beats: list of timeline seconds, e.g. plan['beats'])."""
    import bisect
    bs = sorted(beats)
    bad = []
    for c in cut_points(cuts, t0):
        i = bisect.bisect_left(bs, c)
        near = min((abs(bs[j] - c) for j in (i - 1, i) if 0 <= j < len(bs)), default=1e9)
        if near > tol:
            bad.append((c, round(near, 4)))
    return bad


# ----------------------------------------------------------------------------------------------
# example on the engine's synthetic test media (engine/test/make_test_media.py)
# ----------------------------------------------------------------------------------------------

EXAMPLE_FRAMES = {   # reframe-report format: id -> {"frame": {...}}; keys t = source s (photo: s from start)
    "open": {"frame": {"mode": "crop", "keys": [{"t": 0.0, "cx": 0.5, "cy": 0.5, "zoom": 1.0},
                                                 {"t": 3.0, "cx": 0.55, "cy": 0.42, "zoom": 1.18}]}},
    "v1": {"frame": {"mode": "crop", "keys": [{"t": 1.0, "cx": 0.30, "cy": 0.5, "zoom": 1.0},
                                               {"t": 3.4, "cx": 0.62, "cy": 0.5, "zoom": 1.08}]}},
    "v2": {"frame": {"mode": "crop", "cx": 0.5, "cy": 0.5, "zoom0": 1.0, "zoom1": 1.06}},
    "v3": {"frame": {"mode": "crop", "keys": [{"t": 3.0, "cx": 0.2, "cy": 0.6, "zoom": 1.2},
                                               {"t": 4.6, "cx": 0.98, "cy": 0.5, "zoom": 1.0},   # off-frame: gets projected
                                               {"t": 6.0, "cx": 0.7, "cy": 0.5, "zoom": 1.05}]}},
    "v4": {"frame": {"mode": "box", "aspect": 1.0, "keys": [{"t": 1.0, "cx": 0.4, "cy": 0.5, "zoom": 1.0},
                                                             {"t": 3.5, "cx": 0.6, "cy": 0.5, "zoom": 1.1}]}},
    "v5": {"frame": {"mode": "crop", "cx": 0.45, "cy": 0.5, "zoom": 1.0}},
}


def example(out_path, media):
    """Beat-locked 100 BPM (beat 0.6 s) mini film from the synthetic test media."""
    media = os.path.abspath(media)
    need = ["clip_land.mp4", "clip_portrait.mov", "clip_shaky.mp4", "test_photo.jpg", "music_bed_test.wav"]
    missing = [f for f in need if not os.path.exists(os.path.join(media, f))]
    if missing:
        raise SystemExit(f"missing test media {missing} in {media} - run: python engine/test/make_test_media.py --out {media}")
    beat = 0.6
    XF = 0.6
    CUTS = [
        ("open", dur_beats(4, beat), dict(src="test_photo.jpg"), None),
        ("v1", dur_beats(4, beat), dict(src="clip_land.mp4", a=1.0), None),
        ("v2", dur_beats(2, beat), dict(src="clip_portrait.mov", a=3.0, nat_sound=True, nat_gain_db=-2,
                                        duck_window=[0.0, 0.9]), ("crossfade", XF)),
        ("v3", dur_beats(6, beat), dict(src="clip_land.mp4", speed_map=[(3.0, 4.0, 1.0), (4.0, 4.6, 0.5), (4.6, 6.0, 1.0)]), None),
        ("v4", dur_beats(4, beat), dict(src="clip_portrait.mov", a=1.0, rotate=-90, hflip=True, mirror_keys=True,
                                        frame_extra={"box_y": 0.45}), ("whip", 0.25, {"dir": "left"})),
        ("v5", dur_beats(6, beat), dict(src="clip_shaky.mp4", a=8.0, stabilize=True), ("dip_white", XF)),
        ("end", dur_beats(5, beat), dict(src="test_photo.jpg", frame={"mode": "box", "aspect": 1.0, "box_y": 0.4,
                                         "keys": [{"t": 0.0, "cx": 0.5, "cy": 0.5, "zoom": 1.0},
                                                  {"t": 3.3, "cx": 0.5, "cy": 0.5, "zoom": 1.06}]}), None),
    ]
    rel = os.path.relpath(media, os.path.dirname(os.path.abspath(out_path))).replace("\\", "/")
    sizer = SourceSizer([media], [media])
    texts = [{"text": "Example film", "start": 0.3, "end": 2.3, "style": "title"},
             {"text": "built by edl_builder.py", "start": 0.7, "end": 2.3, "style": "subtitle"},
             {"text": "speed ramp", "start": 6.4, "end": 8.6, "style": "label"},
             {"text": "Thanks for watching!\n100 BPM test bed", "start": 16.2, "end": 18.6, "style": "credit", "y": 0.72}]
    edl = build_edl(CUTS, frames=EXAMPLE_FRAMES, texts=texts,
                    music={"path": "music_bed_test.wav", "gain_db": 0, "duck_db": -8, "fade_out": 1.5},
                    output={"path": "example_film.mp4", "w": 1080, "h": 1920, "fps": 30},
                    paths={"video": rel, "photo": rel, "music": rel}, grade="warm_pop",
                    grade_adjust={"v5": {"exposure": -0.1}}, key_tweaks={"v3": {4.6: 4.5}},
                    source_size=sizer, title="edl_builder example")
    off = check_on_beats(CUTS, [i * beat for i in range(200)])
    print("cut points:", cut_points(CUTS), "| off-beat:", off or "none")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(edl, f, ensure_ascii=False, indent=1)
    print(f"wrote {out_path}\nnext: python {os.path.relpath(os.path.join(ENGINE_DIR, 'render.py'))} {out_path} --timeline")
    return edl


def from_cutlist_file(path, out):
    """JSON cut list -> EDL. Keys: cuts ([[id, D, spec, transition|null], ...] or [{id, D, spec, transition}]),
    frames (dict or path to a reframe JSON, or a list of such paths), texts, music, output, paths, grade,
    audio, key_tweaks, grade_adjust, title; beat_period + D in beats via {"beats": n} for D."""
    d = json.load(open(path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(path))
    frames = {}
    fr = d.get("frames") or {}
    for f in (fr if isinstance(fr, list) else [fr]):
        if isinstance(f, str):
            f = json.load(open(os.path.join(base, f), encoding="utf-8"))
        frames.update({k: v for k, v in f.items() if isinstance(v, dict) and not v.get("dropped")})
    per = d.get("beat_period")
    cuts = []
    for c in d["cuts"]:
        c = dict(zip(("id", "D", "spec", "transition"), c)) if isinstance(c, list) else dict(c)
        if isinstance(c["D"], dict):
            c["D"] = dur_beats(c["D"]["beats"], per)
        if c.get("transition") and isinstance(c["transition"], list):
            c["transition"] = tuple(c["transition"])
        cuts.append(c)
    paths = d.get("paths") or {}
    pdir = lambda k: os.path.normpath(os.path.join(base, paths[k])) if paths.get(k) else base  # noqa: E731
    sizer = SourceSizer([pdir("video")], [pdir("photo")])
    # relative paths in the cut list are relative to the cut list; the EDL resolves relative to itself
    out_dir = os.path.dirname(os.path.abspath(out))
    rebase = lambda p: p if os.path.isabs(p) else \
        os.path.relpath(os.path.normpath(os.path.join(base, p)), out_dir).replace("\\", "/")  # noqa: E731
    paths = {k: (rebase(v) if isinstance(v, str) else v) for k, v in paths.items()}
    output = dict(d.get("output") or {})
    if output.get("path"):
        output["path"] = rebase(output["path"])
    edl = build_edl(cuts, frames=frames, texts=d.get("texts"), music=d.get("music"), output=output,
                    paths=paths or None, grade=d.get("grade", "warm_pop"), audio=d.get("audio"),
                    key_tweaks=d.get("key_tweaks"), grade_adjust=d.get("grade_adjust"), title=d.get("title"),
                    source_size=sizer)
    if per:
        off = check_on_beats(cuts, [i * per for i in range(int(sum(float(c["D"]) for c in cuts) / per) + 4)])
        print("off-beat cuts:", off or "none")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(edl, f, ensure_ascii=False, indent=1)
    print("wrote", out)


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cutlist", nargs="?", help="cut list JSON (see from_cutlist_file)")
    ap.add_argument("--out", help="EDL to write (with a cut list / --layout / --picks)")
    ap.add_argument("--example", metavar="EDL_PATH", help="write the example EDL built from the engine test media")
    ap.add_argument("--media", default=os.path.join(ENGINE_DIR, "test", "media"),
                    help="test media folder for --example (default engine/test/media)")
    g = ap.add_argument_group("automatic layout")
    g.add_argument("--layout", metavar="SPEC", help="layout spec JSON (see --layout-help)")
    g.add_argument("--picks", nargs="+", metavar="PICKS", help="quick layout: picks file(s), one section")
    g.add_argument("--plan", help="quick layout: music plan JSON (beats, final_accent ...)")
    g.add_argument("--end", default="recommended_end",
                   help="quick layout: film end (number or plan key, e.g. final_accent; default recommended_end)")
    g.add_argument("--video-dir", help="quick layout: raw footage folder (source durations, key projection)")
    g.add_argument("--photo-dir", help="quick layout: photo folder")
    g.add_argument("--drop", action="append", default=[], metavar="ID",
                   help="local edit of the previous layout: remove ID, its neighbours absorb its time (repeatable)")
    g.add_argument("--insert", metavar="ID", help="local edit: insert pick ID (with --after)")
    g.add_argument("--after", metavar="ID", help="--insert position")
    g.add_argument("--prev", metavar="LAYOUT_JSON", help="previous layout (default <out>.layout.json)")
    g.add_argument("--stretch-photos", action="store_true",
                   help="a section short of material: spread the gap over its photos instead of failing")
    g.add_argument("--dry-run", action="store_true", help="print the layout / range table, write nothing")
    g.add_argument("--layout-help", action="store_true", help="print the layout spec format")
    a = ap.parse_args()
    if a.layout_help:
        print(LAYOUT_DOC)
        return 0
    if a.layout or a.picks:
        if not a.out:
            ap.error("--out is required with --layout / --picks")
        if a.insert and not a.after:
            ap.error("--insert needs --after")
        drop = [x for d in a.drop for x in d.split(",") if x]
        ins = (a.insert, a.after) if a.insert else None
        if a.layout:
            return build_from_layout(a.layout, a.out, drop, ins, a.prev, a.stretch_photos, a.dry_run)
        if not a.plan:
            ap.error("--picks needs --plan")
        spec = {"picks": [os.path.abspath(p) for p in a.picks], "plan": os.path.abspath(a.plan),
                "paths": {k: os.path.abspath(v) for k, v in (("video", a.video_dir), ("photo", a.photo_dir)) if v},
                "sections": [{"name": "film", "start": 0.0, "end": a.end, "grid": "beats"}]}
        return build_from_layout(None, a.out, drop, ins, a.prev, a.stretch_photos, a.dry_run, spec=spec)
    if a.example:
        example(a.example, a.media)
    elif a.cutlist and a.out:
        from_cutlist_file(a.cutlist, a.out)
    else:
        ap.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

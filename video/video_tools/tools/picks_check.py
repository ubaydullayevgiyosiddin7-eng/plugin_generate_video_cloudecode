"""Material budget + repetition check of reviewer picks - run it BEFORE the music length is briefed.

  python tools/picks_check.py picks_bog.json picks_minora.json
  python tools/picks_check.py picks_*.json --bar 2.964 --phrase-bars 4          recommend phrase-line lengths
  python tools/picks_check.py picks_*.json --plan music_plan.json               compare with a planned bed
  python tools/picks_check.py picks_*.json --sections g=garden,t=tower --mode reels --json check.json

Budget, per section (one section per picks file, or --sections PREFIX=NAME, or a pick's "section" field):
  number of picks, sum of dur_suggest (what the reviewers want on screen) and of the max usable seconds
  (videos: in..out / speed, <= 6 s; photos: --photo-cap), and the recommended section lengths: music phrase
  lines (--phrase-bars x --bar s, or the plan's bar length) between "suggested" and "max - 10 %" - so the
  music is cut to the material, not the other way round.  With --plan: planned section lengths (split at the
  plan's scene changes, last one up to final_accent) vs the material; SHORT = more time than usable material.
Repetition flags (owner: no near-identical shots, never the same place back to back; memory cut <= 2 shots
per place, Reels 1):
  SAME-SRC  two picks from one clip with overlapping or near (< --near s) source ranges, or one photo twice
  PLACE     more than --max-per-place picks with the same "place" tag (default: memory 2, reels 1)
  ADJACENT  the same place back to back in story order ("order")
  SETUP     the same place + setup twice (same viewpoint/framing)
  info      adjacent picks whose intent texts share a distinctive word (e.g. two storks; words in >= 20 % of a section are ignored)
Exit code: 0 clean, 1 flags found, 2 error.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _picks import (DEFAULTS, NON_FILM_ROLES, dur_want, is_photo, load_picks, pick_cap,  # noqa: E402
                    source_limits, story_order)
from _vtlib import safe_console  # noqa: E402

STOP = set("""about above after again against along around away back before behind below beside between beyond
camera close closeup clip frame from front full giving into just later looking moment more much over shot shots
slow smile smiles smiling selfie selfies still than that their then there these this those through under while
with without zoom pans panning drift drifts view views starts start ends ending second first final short beat
right left calm soft wide high very""".split())


def words(text):
    return {w for w in re.findall(r"[a-z]{5,}", (text or "").lower()) if w not in STOP}


def sections_of(picks, order, spec):
    """{section name: [ids in story order]} (film roles only)."""
    secs = {}
    rules = []
    if spec:
        for part in spec.split(","):
            pre, _, name = part.partition("=")
            rules.append((pre.strip(), (name or pre).strip()))
    for i in order:
        p = picks[i]
        if p.get("role") in NON_FILM_ROLES:
            continue
        name = p.get("section")
        if name is None and rules:
            name = next((n for pre, n in rules if i.startswith(pre)), "other")
        if name is None:
            name = os.path.splitext(os.path.basename(p["_file"]))[0].replace("picks_", "")
        secs.setdefault(name, []).append(i)
    return {k: story_order(picks, v) for k, v in secs.items()}


def phrase_lengths(lo, hi, phrase):
    if not phrase:
        return []
    k0, k1 = int(lo // phrase) + (1 if lo % phrase > 1e-6 else 0), int(hi // phrase)
    return [round(k * phrase, 2) for k in range(max(1, k0), k1 + 1)]


def plan_sections(plan):
    sc = []
    if isinstance(plan.get("join"), dict) and plan["join"].get("scene_change") is not None:
        sc = [float(plan["join"]["scene_change"])]
    sc = [float(x) for x in plan.get("scene_changes", sc)]
    end = float(plan.get("final_accent") or plan.get("recommended_end") or plan.get("total_duration"))
    edges = [0.0] + sc + [end]
    return [round(b - a, 2) for a, b in zip(edges, edges[1:])]


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("picks", nargs="+", help="picks JSON file(s)")
    ap.add_argument("--sections", help="PREFIX=NAME,... (default: one section per picks file)")
    ap.add_argument("--mode", choices=["memory", "reels"], default="memory",
                    help="memory cut (<= 2 per place, default) or reels (1 per place)")
    ap.add_argument("--max-per-place", type=int, help="override the per-place limit")
    ap.add_argument("--near", type=float, default=1.0, help="source ranges closer than this (s) count as the same take")
    ap.add_argument("--photo-cap", type=float, default=DEFAULTS["photo_cap"], help="max seconds per photo (default 4.6)")
    ap.add_argument("--video-max", type=float, default=DEFAULTS["video_max"], help="max seconds per video shot (6)")
    ap.add_argument("--bar", type=float, help="bar length of the planned music (s) for phrase-line recommendations")
    ap.add_argument("--phrase-bars", type=int, default=4, help="bars per phrase line (default 4)")
    ap.add_argument("--plan", help="music plan JSON: compare its section lengths with the material")
    ap.add_argument("--json", help="write the report as JSON")
    a = ap.parse_args()
    try:
        picks, order = load_picks(a.picks)
    except (OSError, ValueError) as e:
        print(f"ERROR {e}")
        return 2
    limit = a.max_per_place or (1 if a.mode == "reels" else 2)
    plan = json.load(open(a.plan, encoding="utf-8")) if a.plan else None
    bar = a.bar
    if bar is None and plan:
        bl = plan.get("bar_length")
        bar = float(bl) if isinstance(bl, (int, float)) else None
    phrase = bar * a.phrase_bars if bar else None
    secs = sections_of(picks, order, a.sections)
    rep = {"sections": [], "flags": [], "info": []}
    print(f"{len(picks)} picks in {len(a.picks)} file(s); mode {a.mode} (<= {limit} per place)")
    print(f"{'section':<10}{'picks':>6}{'suggested':>11}{'max':>8}  recommended length (s)")
    tot_w = tot_m = 0.0
    for name, ids in secs.items():
        caps = [pick_cap(picks[i], photo_cap=a.photo_cap, video_max=a.video_max) for i in ids]
        want = sum(dur_want(picks[i], c) for i, c in zip(ids, caps))
        mx = sum(caps)
        tot_w, tot_m = tot_w + want, tot_m + mx
        hi = mx * 0.9                      # leave ~10 % slack: beat snapping needs room
        lines = phrase_lengths(want, hi, phrase)
        rec = (", ".join(f"{x:g}" for x in lines) + f"  ({a.phrase_bars}-bar lines of {phrase:.2f} s)") if lines else \
            (f"{want:.1f}-{hi:.1f}" + ("" if not phrase else f"  (no {phrase:.2f} s phrase line fits: nearest "
                                                             f"{round(want / phrase) * phrase:.1f})"))
        print(f"{name:<10}{len(ids):>6}{want:>10.1f}s{mx:>7.1f}s  {rec}")
        rep["sections"].append(dict(name=name, picks=ids, suggested=round(want, 2), max=round(mx, 2),
                                    recommended=lines or [round(want, 1), round(hi, 1)]))
    print(f"{'total':<10}{sum(len(v) for v in secs.values()):>6}{tot_w:>10.1f}s{tot_m:>7.1f}s")
    if plan:
        pl = plan_sections(plan)
        print("plan sections:", ", ".join(f"{x:.2f} s" for x in pl))
        for (name, ids), s, L in zip(secs.items(), rep["sections"], pl):
            st = "SHORT" if L > s["max"] * 0.97 else ("tight" if L > s["max"] * 0.9 else "ok")
            print(f"  {name:<10} planned {L:6.2f} s vs material {s['suggested']:.1f} suggested / {s['max']:.1f} max -> {st}")
            s["planned"], s["planned_status"] = L, st
            if st == "SHORT":
                rep["flags"].append(f"BUDGET {name}: planned {L:.2f} s > usable material {s['max']:.1f} s")

    def flag(kind, msg):
        rep["flags"].append(f"{kind} {msg}")

    # same source / same take
    by_src = {}
    for i in order:
        if picks[i].get("role") in NON_FILM_ROLES:
            continue
        by_src.setdefault(picks[i]["src"].lower(), []).append(i)
    for src, ids in by_src.items():
        if len(ids) < 2:
            continue
        if is_photo(picks[ids[0]]):
            flag("SAME-SRC", f"{'/'.join(ids)}: the same photo {picks[ids[0]]['src']} twice")
            continue
        rng = sorted((source_limits(picks[i]) + (i,) for i in ids))
        for (a0, a1, ia), (b0, b1, ib) in zip(rng, rng[1:]):
            gap = b0 - a1
            if gap < a.near:
                flag("SAME-SRC", f"{ia}/{ib}: {picks[ia]['src']} ranges {a0:g}-{a1:g} and {b0:g}-{b1:g} "
                                 f"({'overlap' if gap < 0 else f'gap {gap:.2f} s'}) - the same take?")
    # places / setups
    tagged = [i for i in order if picks[i].get("place")]
    if not tagged:
        rep["info"].append("no 'place' tags in the picks - place/setup checks skipped (see the reviewer template)")
    count = {}
    for i in tagged:
        count.setdefault(picks[i]["place"], []).append(i)
    for pl, ids in count.items():
        if len(ids) > limit:
            flag("PLACE", f"{pl}: {len(ids)} picks ({', '.join(ids)}) > {limit} for a {a.mode} cut")
    seen = {}
    for i in tagged:
        if picks[i].get("setup"):
            key = (picks[i]["place"], picks[i]["setup"])
            if key in seen:
                flag("SETUP", f"{seen[key]}/{i}: same place + setup {key[0]} / {key[1]} (near-identical shots)")
            seen.setdefault(key, i)
    for name, ids in secs.items():
        ws = {i: words(picks[i].get("intent") or picks[i].get("subject")) for i in ids}
        df = {}
        for i in ids:
            for w in ws[i]:
                df[w] = df.get(w, 0) + 1
        common_words = {w for w, n in df.items() if n >= max(3, 0.2 * len(ids))}    # location words ("garden")
        for x, y in zip(ids, ids[1:]):
            px, py = picks[x], picks[y]
            if px.get("place") and px.get("place") == py.get("place"):
                flag("ADJACENT", f"{x} -> {y}: the same place '{px['place']}' back to back")
            common = (ws[x] & ws[y]) - common_words
            if common:
                rep["info"].append(f"{x} -> {y} both mention {sorted(common)} - near-identical back to back?")
    for f in rep["flags"]:
        print("FLAG " + f)
    for f in rep["info"]:
        print("info " + f)
    print("PASS (no flags)" if not rep["flags"] else f"{len(rep['flags'])} flag(s)")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=1, ensure_ascii=False)
    return 1 if rep["flags"] else 0


if __name__ == "__main__":
    sys.exit(main())

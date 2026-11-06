"""Render a music bed from a segment list (re-edit a track on bar/phrase lines) -> 48 kHz WAV + plan JSON;
or join several tracks (one per location) at scene changes into one bed.

  python tools/music_bed.py bed_spec.json --out music_bed.wav            plan -> music_bed_plan.json
  python tools/music_bed.py music_plan_tight.json --out bed.wav          re-render an existing plan
  python tools/music_bed.py bed_spec.json --out bed.wav --plan plan.json
  python tools/music_bed.py bed_spec.json --out bed.wav --length 45      end-anchored: pick the entry bar for ~45 s
  python tools/music_bed.py film_bed.json --out bed.wav --length 90      multi-part spec (below), last part re-entered

Spec (all times in SOURCE seconds of the track unless noted):
  {
    "name": "My film - tight edit",
    "track": {"file": "song.mp3", "title": "Song", "artist": "...", "license": "...",
              "attribution_text": "..."},              # or just "track": "song.mp3"
    "analysis": "song_beats.json",                       # tools/music_beats.py output -> beat grid; or:
    "beat0": 0.055, "period": 0.6,                       # bar-1 downbeat and beat period (overrides analysis)
    "bar_starts": [0.54, 3.56, 6.59, ...],               # OR measured bar lines (rubato/live tracks; music_beats
                                                         #   writes them as bar_starts when tempo_mode is rubato)
    "crossfade": 0.06,                                   # interior splices: equal-power, centred on the cut
    "phrase_bars": 8,
    "segments": [
      {"src_in": 110.455, "src_out": 115.255, "fade_in": 0.6, "note": "cold open (2 bars)"},
      {"src_in": 0.055, "src_out": 38.455, "note": "song start"},
      {"src_in": 153.655, "src_out": 175.40, "fade_out": 0.6, "note": "finale + ring-out"}
    ],
    "sections": [{"name": "intro", "start": 0, "end": 4.8, "energy": "low", "note": ""}],   # TIMELINE s, optional
    "final_accent_src": 172.055, "ring_end_src": 175.25,                                     # optional
    "flex": [{"change": "...", "how": "..."}]                                               # optional notes
  }
Relative paths are relative to the spec file.  A music_plan_*.json (this kit's plan format) is accepted
as a spec too (its beat grid is recovered from downbeat_source_bar).

Multi-part spec (one track per location, joined at the scene change - the Kuzgi sayr bed):
  {"name": "...", "parts": [
     {"spec": "bed_garden.json"},                                  # part 1 starts at 0 s
     {"spec": "bed_tower.json", "scene_change": 56.36,             # timeline s where part 2's entry downbeat lands
      "downbeat_offset": 0.0, "gain_db": 0}],                     # s into part 2's bed (default: its 1st downbeat)
   "join_rule": "...", "sections": [...timeline...], "peak": -1.0, "scene_change_is_phrase": true}
  Each part is an ordinary spec (file or inline); the earlier part fades its own tail out (its last segment's
  fade_out) under the next part's entry.  Original relative levels are kept (gain_db per part), then ONE
  peak-limiting gain.  The merged plan has timeline beats/downbeats/phrases of all parts, join/joins/
  scene_changes, the last part's final_accent and recommended_end, all tracks and attribution texts.
--length S (end-anchored, no new splice): keeps the ending of the (last part's) first segment chain and moves
  its src_in to the bar line (every --entry-every bars) that gives a total closest to S; prints candidates.

Rendering (identical to the Magic Safari bed): the first segment starts with a sin^2 swell over
fade_in, the last ends with a cos^2 fade over fade_out; every interior boundary is a crossfade
(default 60 ms) centred on the cut: the outgoing segment runs crossfade/2 past src_out, the incoming
starts crossfade/2 before src_in.  Only peak-limiting gain is applied (<= -1 dBFS sample and
<= -1 dBTP true peak, measured with ffmpeg ebur128), no loudness normalisation (the engine does that).
Output: WAV PCM 24-bit 48 kHz stereo + plan JSON with beats / downbeats / phrase starts mapped to the
TIMELINE (music_plan format; feed it to tools/edl_builder.py --layout and the WAV to the EDL's music.path).
Use tools/music_beats.py --suggest-jumps to find seamless splice points.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import FFMPEG, safe_console  # noqa: E402

SR = 48000


def decode(path):
    raw = subprocess.run([FFMPEG, "-nostdin", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def take(x, t0, t1):
    a, b = int(round(t0 * SR)), int(round(t1 * SR))
    out = np.zeros((b - a, 2))
    lo, hi = max(a, 0), min(b, len(x))
    if hi > lo:
        out[lo - a:hi - a] = x[lo:hi]
    return out


def write_wav24(path, x):
    q = np.clip(np.round(x * 8388607.0), -8388608, 8388607).astype("<i4")
    b = q.reshape(-1, 1).view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(b)


def ebur(path):
    r = subprocess.run([FFMPEG, "-nostdin", "-hide_banner", "-i", path, "-af", "ebur128=peak=true+sample",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    tp = float(re.findall(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS", r)[-1].replace("-inf", "-120"))
    sp = float(re.findall(r"Sample peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS", r)[-1].replace("-inf", "-120"))
    lra = float(re.findall(r"LRA:\s+(-?[\d.]+) LU", r)[-1])
    return I, tp, sp, lra


def load_spec(path, d=None, base=None):
    """Spec file (or an inline dict d with relative paths resolved against base) -> normalised spec."""
    if d is None:
        d = json.load(open(path, encoding="utf-8"))
        base = os.path.dirname(os.path.abspath(path))
    else:
        d = dict(d)
        base = base or os.getcwd()

    def absp(p):
        return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))
    if "tracks" in d and d.get("segments") and "track_file" in d["segments"][0]:   # a music_plan_*.json
        if d.get("parts"):
            raise SystemExit("this plan was made from a multi-part spec - re-render that spec instead")
        tr = dict(d["tracks"][0])
        per = float(d["beat_period"])
        seg0 = d["segments"][0]
        t_db, bar = d["downbeat_source_bar"][0]
        # source time of that downbeat, then back to bar 1
        src = None
        for s in d["segments"]:
            if s["timeline_start"] - 1e-6 <= t_db <= s["timeline_end"] + 1e-6:
                src = s["src_in"] + (t_db - s["timeline_start"])
                break
        beat0 = (src if src is not None else seg0["src_in"]) - (bar - 1) * 4 * per
        spec = dict(name=d.get("plan", "re-rendered plan"), track=tr, beat0=beat0, period=per,
                    crossfade=0.06, phrase_bars=d.get("phrase_length_bars", 8),
                    segments=[dict(src_in=s["src_in"], src_out=s["src_out"], fade_in=s.get("fade_in"),
                                   fade_out=s.get("fade_out"), bars=s.get("source_bars", ""), note=s.get("note", ""))
                              for s in d["segments"]],
                    sections=d.get("sections", []), flex=d.get("flex_options", []))
        m = re.search(r"(\d+) ms equal-power", d.get("crossfade_rule", ""))
        if m:
            spec["crossfade"] = int(m.group(1)) / 1000.0
        # final accent / ring end back to source time
        for key, out_key in (("final_accent", "final_accent_src"), ("recommended_end", "ring_end_src")):
            t = d.get(key)
            if t is not None:
                for s in d["segments"]:
                    if s["timeline_start"] - 1e-6 <= t <= s["timeline_end"] + 1e-6:
                        spec[out_key] = s["src_in"] + (t - s["timeline_start"])
        tr["file"] = absp(tr["file"])
        return spec
    tr = d["track"] if isinstance(d["track"], dict) else {"file": d["track"]}
    tr = dict(tr)
    tr["file"] = absp(tr["file"])
    tr.setdefault("title", os.path.splitext(os.path.basename(tr["file"]))[0])
    d["track"] = tr
    if d.get("analysis") and ("beat0" not in d or "period" not in d or "bar_starts" not in d):
        an = json.load(open(absp(d["analysis"]), encoding="utf-8"))
        d.setdefault("period", an["beat_period"])
        d.setdefault("beat0", an["downbeats"][0])
        d.setdefault("phrase_bars", an.get("phrase_length_bars", 8))
        if str(an.get("tempo_mode", "")).startswith("rubato") and an.get("bar_starts"):
            d.setdefault("bar_starts", an["bar_starts"])
    if d.get("bar_starts"):
        bl = np.diff(sorted(float(t) for t in d["bar_starts"]))
        d.setdefault("period", float(np.median(bl)) / int(d.get("beats_per_bar", 4)) if len(bl) else 0.6)
        d.setdefault("beat0", float(d["bar_starts"][0]))
    if "beat0" not in d or "period" not in d:
        raise SystemExit("spec needs beat0 + period, bar_starts, or an 'analysis' JSON from tools/music_beats.py")
    return d


def segment_layout(P):
    layout, tl = [], 0.0
    for s in P["segments"]:
        a_, b_ = float(s["src_in"]), float(s["src_out"])
        if b_ <= a_:
            raise SystemExit(f"segment {s}: src_out must be > src_in")
        layout.append(dict(src_in=a_, src_out=b_, tl_start=tl, fade_in=s.get("fade_in"), fade_out=s.get("fade_out"),
                           bars=s.get("bars", s.get("source_bars", "")), note=s.get("note", "")))
        tl += b_ - a_
    return layout, tl


def render_segments(P, x=None):
    """Audio of one spec (no gain applied) -> (bed float64 (n, 2), layout, total seconds)."""
    tr = P["track"]
    XF = float(P.get("crossfade", 0.06))
    H = XF / 2
    if not P.get("segments"):
        raise SystemExit("no segments")
    if x is None:
        x = decode(tr["file"])
    layout, total = segment_layout(P)
    bed = np.zeros((int(np.ceil(total * SR)) + 1, 2))
    for i, L in enumerate(layout):
        first, last = i == 0, i == len(layout) - 1
        pre = 0.0 if first else H
        post = 0.0 if last else H
        seg = take(x, L["src_in"] - pre, L["src_out"] + post)
        m = len(seg)
        g = np.ones(m)
        if first:
            fi = float(L["fade_in"] or 0.0)
            k = min(m, int(round(fi * SR)))
            if k > 0:
                g[:k] *= np.sin(np.linspace(0, np.pi / 2, k)) ** 2          # smooth swell
        else:
            k = min(m, int(round(XF * SR)))
            g[:k] *= np.sin(np.linspace(0, np.pi / 2, k))                   # equal power
        if last:
            fo = float(L["fade_out"] or 0.0)
            k = min(m, int(round(fo * SR)))
            if k > 0:
                g[m - k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
        else:
            k = min(m, int(round(XF * SR)))
            g[m - k:] *= np.cos(np.linspace(0, np.pi / 2, k))
        s0 = int(round((L["tl_start"] - pre) * SR))
        bed[s0:s0 + m] += seg[:len(bed) - s0] * g[:len(bed) - s0, None]
    return bed[:int(round(total * SR))], layout, total


def source_bars(P, upto):
    """Bar lines in SOURCE seconds: the spec's measured `bar_starts` or the constant grid beat0 + 4*period*k.
    -> [(t, bar number)]"""
    if P.get("bar_starts"):
        return [(float(t), k + 1) for k, t in enumerate(sorted(float(x) for x in P["bar_starts"]))]
    b0, per = float(P["beat0"]), float(P["period"])
    k0 = -int(np.floor(b0 / (4 * per))) if b0 > 0 else 0
    return [(b0 + 4 * per * k, k + 1) for k in range(k0, int((upto - b0) / (4 * per)) + 2)]


def plan_grid(P, layout):
    """Timeline beats / downbeats / phrase starts / [time, bar] of a rendered single-track spec."""
    pb = int(P.get("phrase_bars", 8))
    last_beat_src = float(P.get("final_accent_src", P.get("ring_end_src", 1e9))) + float(P["period"]) * 0.51 \
        if P.get("last_beat_src") is None else float(P["last_beat_src"])
    beats, downs, phrases, barmap = [], [], [], []
    if P.get("bar_starts"):
        bars = sorted(float(t) for t in P["bar_starts"])
        bpb = int(P.get("beats_per_bar", 4))
        off = int(P.get("phrase_offset_bars", 0))
        ph_src = [float(t) for t in P.get("phrase_starts_src", [])]
        src_beats = []
        for k, t in enumerate(bars):
            nxt = bars[k + 1] if k + 1 < len(bars) else t + (t - bars[k - 1] if k else 4 * float(P["period"]))
            for j in range(bpb):
                src_beats.append((t + j * (nxt - t) / bpb, j == 0, k + 1))
        for i, L in enumerate(layout):
            a_, b_ = L["src_in"], L["src_out"]
            lim = min(b_, last_beat_src + 1e-3) if i == len(layout) - 1 else b_
            for t, is_down, bar in src_beats:
                if a_ - 1e-6 <= t < lim - 1e-6:
                    tt = round(L["tl_start"] + (t - a_), 4)
                    beats.append(tt)
                    if is_down:
                        downs.append(tt)
                        barmap.append([tt, bar])
                        if any(abs(t - p) < 0.05 for p in ph_src) if ph_src else (bar - 1 - off) % pb == 0:
                            phrases.append(tt)
        return beats, downs, phrases, barmap
    b0, per = float(P["beat0"]), float(P["period"])
    for i, L in enumerate(layout):
        a_, b_ = L["src_in"], L["src_out"]
        lim = min(b_, last_beat_src + 1e-3) if i == len(layout) - 1 else b_
        k = int(np.ceil((a_ - b0) / per - 1e-6))
        while b0 + k * per < lim - 1e-6:
            t = round(L["tl_start"] + (b0 + k * per - a_), 4)
            beats.append(t)
            if k % 4 == 0:
                bar = k // 4 + 1
                downs.append(t)
                barmap.append([t, bar])
                if (bar - 1) % pb == 0:
                    phrases.append(t)
            k += 1
    return beats, downs, phrases, barmap


def build_plan(P, layout, total, out_path):
    """music_plan dict (without the 'render' block) of a single-track spec."""
    tr = P["track"]
    XF = float(P.get("crossfade", 0.06))
    H = XF / 2
    beats, downs, phrases, barmap = plan_grid(P, layout)
    per = float(P["period"])
    pb = int(P.get("phrase_bars", 8))

    def to_tl(src):
        if src is None:
            return None
        for L in layout:
            if L["src_in"] - 1e-6 <= src <= L["src_out"] + 1e-6:
                return round(L["tl_start"] + src - L["src_in"], 3)
        return None
    sections = [{"name": s.get("name", f"section_{i + 1}"), "start": s.get("start"),
                 "end": round(s["end"] if s.get("end") is not None else total, 3), "energy": s.get("energy"),
                 "note": s.get("note", "")} for i, s in enumerate(P.get("sections", []))]
    plan = {
        "plan": P.get("name", os.path.splitext(os.path.basename(out_path))[0]),
        "generated": time.strftime("%Y-%m-%d"),
        "tracks": [dict(tr)],
        "segments": [{"track_file": tr["file"], "src_in": round(L["src_in"], 4), "src_out": round(L["src_out"], 4),
                      "timeline_start": round(L["tl_start"], 4),
                      "timeline_end": round(L["tl_start"] + L["src_out"] - L["src_in"], 4),
                      "fade_in": L["fade_in"] if i == 0 else XF, "fade_out": L["fade_out"] if i == len(layout) - 1 else XF,
                      "source_bars": L["bars"], "note": L["note"]} for i, L in enumerate(layout)],
        "crossfade_rule": f"Interior boundaries: {int(round(XF * 1000))} ms equal-power crossfade centred on the cut "
                          f"(outgoing runs {int(round(H * 1000))} ms past src_out, incoming starts {int(round(H * 1000))} ms "
                          f"before src_in). First segment fade_in and last segment fade_out are plain fades.",
        "total_duration": round(total, 3),
        "bpm": round(60 / per, 3), "beat_period": round(per, 6), "bar_length": round(4 * per, 6), "time_signature": "4/4",
        "phrase_length_bars": pb, "phrase_length_s": round(pb * 4 * per, 4),
        "beats": beats, "downbeats": downs, "phrase_starts": phrases, "downbeat_source_bar": barmap,
        "sections": sections,
        "final_accent": to_tl(P.get("final_accent_src")),
        "recommended_end": to_tl(P.get("ring_end_src")) or round(total, 3),
        "recommended_end_note": "Music naturally ends here; hold the end card at least to this point.",
        "flex_options": P.get("flex", []),
    }
    if P.get("bar_starts"):
        plan["tempo_mode"] = "measured bars (rubato): beats interpolated inside each measured bar"
    return plan


def peak_limit_write(bed, out, peak):
    """Write a 24-bit WAV with one gain so that sample and true peak are <= peak dB.  -> (gain, I, tp, sp, lra)"""
    pk = np.abs(bed).max() or 1.0
    gain = min(1.0, 10 ** (peak / 20) / pk)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    for _ in range(4):
        write_wav24(out, bed * gain)
        I, tp, sp, lra = ebur(out)
        if tp <= peak and sp <= peak:
            break
        gain *= 10 ** ((peak - 0.05 - max(tp, sp)) / 20)
    return gain, I, tp, sp, lra


def render_block(out, gain, I, tp, sp, lra,
                 note="Only peak-limiting gain applied (no loudness normalisation, no compression)."):
    return {"file": os.path.abspath(out), "sample_rate": SR, "channels": 2, "format": "WAV PCM 24-bit",
            "gain_applied_db": round(20 * np.log10(gain), 2), "integrated_lufs": I, "loudness_range_lu": lra,
            "true_peak_dbtp": tp, "sample_peak_dbfs": sp, "note": note}


def entry_candidates(P, target_len, fixed_before=0.0, every=4):
    """End-anchored length helper: keep the spec's END and move the FIRST segment's src_in to another bar
    line (every `every` bars, counted from bar 1) so that fixed_before + bed length ~ target_len.
    The pre-roll of the original entry (a src_in a few ms before its downbeat) is kept.
    Returns [(total, bar, new_src_in)] sorted by distance to the target."""
    seg0 = P["segments"][0]
    src_in, src_out0 = float(seg0["src_in"]), float(seg0["src_out"])
    _, total = segment_layout(P)
    bars = source_bars(P, src_out0)
    near = min(bars, key=lambda b: abs(b[0] - src_in))
    pre = near[0] - src_in
    bar_len = (bars[1][0] - bars[0][0]) if len(bars) > 1 else 2.4
    latest = min(src_out0, float(P.get("final_accent_src") or 1e9)) - 2 * bar_len   # >= 2 bars before the end/hit
    out = []
    for t, bar in bars:
        new_in = t - pre
        if (bar - 1) % every or new_in < 0 or new_in > latest:
            continue
        out.append((round(fixed_before + total - (new_in - src_in), 3), bar, round(new_in, 4)))
    return sorted(out, key=lambda c: abs(c[0] - target_len))


def _print_entry(cands, target, every, label=""):
    print(f"--length {target:g}: entry bar candidates{label} (every {every} bars):")
    for tot, bar, src_in in sorted(cands[:6]):
        print(f"   bar {bar:>4}  src_in {src_in:9.3f}  -> total {tot:7.2f} s")
    print(f"   chosen: bar {cands[0][1]} (src_in {cands[0][2]}) -> {cands[0][0]:.2f} s")


def _load_part_spec(part, base):
    sp = part["spec"]
    if isinstance(sp, str):
        return load_spec(os.path.join(base, sp))
    return load_spec(None, sp, base)


def multi_bed(spec_path, out, plan_path, peak, length=None, every=4):
    """Render a multi-part spec -> one bed + merged plan.  Returns 0."""
    M = json.load(open(spec_path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(spec_path))
    parts = M["parts"]
    if not parts:
        raise SystemExit("multi-part spec: 'parts' is empty")
    specs = [_load_part_spec(p, base) for p in parts]
    if length:
        last, prt = specs[-1], parts[-1]
        before = float(prt.get("scene_change", 0.0)) - float(prt.get("downbeat_offset") or 0.0) if len(parts) > 1 else 0.0
        cands = entry_candidates(last, length, before, every)
        if not cands:
            raise SystemExit("--length: no bar-line candidates in the last part's first segment")
        _print_entry(cands, length, every, " of the last part")
        last["segments"] = [dict(last["segments"][0], src_in=cands[0][2])] + last["segments"][1:]
    beds, plans, offsets = [], [], []
    for k, (P, prt) in enumerate(zip(specs, parts)):
        bed, layout, total = render_segments(P)
        bed *= 10 ** (float(prt.get("gain_db", 0.0)) / 20)
        pl = build_plan(P, layout, total, out)
        if k == 0:
            t_off = 0.0
        else:
            if prt.get("scene_change") is None:
                raise SystemExit(f"part {k + 1} needs scene_change (timeline seconds of its entry downbeat)")
            db = prt.get("downbeat_offset")
            db = float(db) if db is not None else (pl["downbeats"][0] if pl["downbeats"] else 0.0)
            t_off = float(prt["scene_change"]) - db
            if t_off < 0:
                raise SystemExit(f"part {k + 1} would start before 0 s (scene_change < downbeat_offset)")
        beds.append(bed)
        plans.append(pl)
        offsets.append(t_off)
    n = max(int(round(o * SR)) + len(b) for o, b in zip(offsets, beds))
    mix = np.zeros((n, 2))
    for o, b in zip(offsets, beds):
        i0 = int(round(o * SR))
        mix[i0:i0 + len(b)] += b
    total = n / SR
    gain, I, tp, sp, lra = peak_limit_write(mix, out, peak)
    scs = [float(p["scene_change"]) for p in parts[1:]]
    edges = [0.0] + scs + [1e9]

    def sh(v, o):
        return round(v + o, 4)
    beats, downs, phrases, segs, sections = [], [], [], [], []
    for k, (pl, o) in enumerate(zip(plans, offsets)):
        a_, b_ = edges[k], edges[k + 1]

        def keep(t):
            return a_ - 1e-6 <= t < b_ - 0.05
        beats += [sh(t, o) for t in pl["beats"] if keep(sh(t, o))]
        dk = [sh(t, o) for t in pl["downbeats"] if keep(sh(t, o))]
        ph = [sh(t, o) for t in pl["phrase_starts"] if keep(sh(t, o))]
        if k:                                   # the scene change is the entry downbeat of this part
            if all(abs(d - a_) > 0.05 for d in dk):
                dk = [round(a_, 4)] + dk
                beats.append(round(a_, 4))
            if M.get("scene_change_is_phrase", True) and all(abs(p - a_) > 0.05 for p in ph):
                ph = [round(a_, 4)] + ph
        downs += dk
        phrases += ph
        for s in pl["segments"]:
            segs.append(dict(s, part=k + 1, timeline_start=sh(s["timeline_start"], o),
                             timeline_end=sh(s["timeline_end"], o)))
        for s in pl["sections"]:
            st, en = sh(s["start"] or 0.0, o), sh(s["end"], o)
            if en > a_ and st < min(b_, total):
                sections.append(dict(s, start=round(max(st, a_), 3), end=round(min(en, b_, total), 3), part=k + 1))
    last, lo = plans[-1], offsets[-1]
    fa = sh(last["final_accent"], lo) if last.get("final_accent") is not None else None
    re_ = last.get("recommended_end")
    names = [p["tracks"][0].get("title") or f"part{k + 1}" for k, p in enumerate(plans)]
    plan = {
        "plan": M.get("name", os.path.splitext(os.path.basename(out))[0]),
        "generated": time.strftime("%Y-%m-%d"),
        "parts": len(parts),
        "tracks": [p["tracks"][0] for p in plans],
        "segments": segs,
        "join": {"scene_change": scs[0], "rule": M.get("join_rule", "")} if scs else None,
        "joins": [{"scene_change": sc, "part": k + 2} for k, sc in enumerate(scs)],
        "scene_changes": scs,
        "crossfade_rule": "Inside each part: tools/music_bed.py splices. Between parts: the earlier part's own fade-out "
                          "(its last segment's fade_out) under the next part's entry downbeat at scene_change.",
        "total_duration": round(total, 3),
        "bpm": dict(zip(names, (p["bpm"] for p in plans))),
        "beat_period": dict(zip(names, (p["beat_period"] for p in plans))),
        "bar_length": dict(zip(names, (p["bar_length"] for p in plans))),
        "time_signature": "4/4",
        "beats": sorted(set(beats)), "downbeats": sorted(set(downs)), "phrase_starts": sorted(set(phrases)),
        "sections": M.get("sections") or sections,
        "final_accent": fa,
        "recommended_end": min(round(total, 3), sh(re_, lo)) if re_ is not None else round(total, 3),
        "recommended_end_note": "Final hit = final_accent (end card / last cut); hold the picture to recommended_end.",
        "render": render_block(out, gain, I, tp, sp, lra, "One peak-limiting gain on the summed parts (no loudness "
                                                          "normalisation); part levels relative via gain_db."),
        "attribution_text": [p["tracks"][0].get("attribution_text") for p in plans],
    }
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    print(f"{out}: {total:.3f} s, {len(parts)} part(s), scene change(s) {scs}, final accent {fa}, gain "
          f"{20 * np.log10(gain):+.2f} dB, I {I} LUFS, TP {tp} dBTP, SP {sp} dBFS")
    print("plan:", os.path.abspath(plan_path))
    return 0


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="bed spec JSON, a multi-part spec ({\"parts\": [...]}) or a music_plan_*.json")
    ap.add_argument("--out", required=True, help="output WAV")
    ap.add_argument("--plan", help="output plan JSON (default <out>_plan.json)")
    ap.add_argument("--peak", type=float, help="sample/true peak ceiling dB (default -1, or the spec's 'peak')")
    ap.add_argument("--length", type=float, metavar="S",
                    help="end-anchored: move the entry of the (last part's) first segment to the bar line giving "
                         "a total of ~S s (the ending stays, no new splice); prints the candidates")
    ap.add_argument("--entry-every", type=int, default=4, help="--length: entry on every Nth bar (default 4)")
    a = ap.parse_args()
    plan_path = a.plan or os.path.splitext(a.out)[0] + "_plan.json"
    raw = json.load(open(a.spec, encoding="utf-8"))
    peak = a.peak if a.peak is not None else float(raw.get("peak", -1.0)) if isinstance(raw, dict) else -1.0
    if isinstance(raw, dict) and "parts" in raw:
        return multi_bed(a.spec, a.out, plan_path, peak, a.length, a.entry_every)
    P = load_spec(a.spec)
    if a.length:
        cands = entry_candidates(P, a.length, 0.0, a.entry_every)
        if not cands:
            sys.exit("--length: no bar-line candidates in the first segment")
        _print_entry(cands, a.length, a.entry_every)
        P["segments"] = [dict(P["segments"][0], src_in=cands[0][2])] + P["segments"][1:]
    bed, layout, total = render_segments(P)
    gain, I, tp, sp, lra = peak_limit_write(bed, a.out, peak)
    plan = build_plan(P, layout, total, a.out)
    plan["render"] = render_block(a.out, gain, I, tp, sp, lra)
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    print(f"{a.out}: {total:.3f} s, {len(layout)} segment(s), {len(plan['beats'])} beats, {len(plan['downbeats'])} bars, "
          f"gain {20 * np.log10(gain):+.2f} dB, I {I} LUFS, TP {tp} dBTP, SP {sp} dBFS")
    print("phrase starts:", plan["phrase_starts"])
    print("plan:", os.path.abspath(plan_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())

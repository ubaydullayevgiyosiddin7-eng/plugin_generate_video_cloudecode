"""Music analysis for beat-locked editing: BPM, beat grid, downbeats, phrase starts, energy curve,
sections, ending - plus bar-level splice scoring for re-editing a track to length.

  python tools/music_beats.py song.mp3                         -> song_beats.json next to the CWD
  python tools/music_beats.py song.mp3 --bpm-hint 100          tempo hint (catalog BPM) for the tracker
  python tools/music_beats.py song.mp3 --downbeat 0.055 --period 0.6   manually verified grid
  python tools/music_beats.py song.mp3 --jump 8:17 --jump 16:33        score splices (end of bar i -> start of bar j)
  python tools/music_beats.py song.mp3 --suggest-jumps 8               best phrase-line splices

Output JSON uses the same field names as the music_plan_*.json files of the Magic Safari project
(total_duration, bpm, beat_period, bar_length, beats, downbeats, phrase_starts, downbeat_source_bar,
sections, final_accent, recommended_end, segments, tracks ...) with the whole track as one segment,
plus "energy" (RMS dB per second), "analysis" (raw tracker output, confidences) and, when asked,
"jumps" / "jump_suggestions".  Feed jumps into tools/music_bed.py to render a re-edited bed.

Method: librosa onset envelope + beat tracker, then a robust constant-tempo grid fit (DAW music is
click-locked), beat phase from kick (low-band) flux, downbeats from bar-line energy/harmony changes
(automatic estimate - verify by ear, or pass --downbeat), sections from a 4-bar checkerboard novelty
on timbre/harmony/energy, phrase phase from novelty peaks.
Rubato / live tracks: the constant grid's best local phase (6 s windows) is tracked through the song; its drift
after removing a linear trend is analysis.constant_grid_residual_ms (click/DAW music ~0-15 ms, the rubato
koto piece Senbazuru 73 ms).  Above 40 ms the track is "rubato" (tempo_mode) and beats/downbeats/phrase_starts
come from TRACKED, onset-refined bar lines (also written as "bar_starts" for music_bed.py specs; the downbeat
is the beat with the strongest low-band onsets; --grid forces either way).
Splice score = similarity of the bar
before the cut with the bar that originally precedes the target, and of the target bar with the bar
that originally follows the cut (1.0 = identical; > ~0.85 usually seamless, < 0.6 audible).
"""
import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vtlib import FFMPEG, safe_console  # noqa: E402

SR = 22050
HOP = 256


def decode(path, sr=SR):
    """Decode with ffmpeg (same decoder as the render -> identical timing)."""
    raw = subprocess.run([FFMPEG, "-nostdin", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1",
                          "-ar", str(sr), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def analyse(y, bpm_hint=None, db_override=None, per_override=None, phrase_bars=8):
    import librosa
    import scipy.signal as sps
    dur = len(y) / SR
    fps = SR / HOP
    oenv = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP, aggregate=np.median)
    tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=SR, hop_length=HOP,
                                           start_bpm=bpm_hint or 120.0, tightness=400, units="time")
    tempo = float(np.atleast_1d(tempo)[0])
    beats = np.asarray(beats)
    if len(beats) < 8:
        raise RuntimeError(f"only {len(beats)} beats detected - no steady pulse?")
    # constant grid via robust linear regression
    idx = np.arange(len(beats))
    A = np.vstack([idx, np.ones_like(idx)]).T
    period, t0 = np.linalg.lstsq(A, beats, rcond=None)[0]
    for _ in range(3):
        res = beats - (t0 + period * idx)
        keep = np.abs(res) < max(0.04, 2.5 * np.std(res))
        period, t0 = np.linalg.lstsq(A[keep], beats[keep], rcond=None)[0]
    res = beats - (t0 + period * idx)
    small = np.abs(res) < 0.1
    grid_rms_ms = float(np.sqrt(np.mean(res[small] ** 2)) * 1000) if np.any(small) else 999.0

    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)

    def bflux(mask):
        X = np.log1p(10 * S[mask])
        return np.maximum(0, np.diff(X, axis=1, prepend=X[:, :1])).sum(0)
    low_on, all_on = bflux(freqs < 120), bflux(freqs > 0)

    def phase_profile(env, per_):
        prof = []
        for ph_ in np.arange(0, per_, 0.005):
            fr = np.round(np.arange(ph_, dur - 0.1, per_) * fps).astype(int)
            fr = fr[fr < len(env)]
            prof.append(np.mean([env[max(0, i - 1):i + 2].max() for i in fr]) if len(fr) else 0)
        return np.array(prof)
    best_p, best_s = period, -1
    for dp in np.linspace(-0.0015, 0.0015, 13):     # small tempo refinement (max on-grid onset energy)
        pr = phase_profile(all_on, period * (1 + dp))
        sc = pr.max() / (pr.mean() + 1e-12)
        if sc > best_s:
            best_s, best_p = sc, period * (1 + dp)
    period = best_p
    pl, pa = phase_profile(low_on, period), phase_profile(all_on, period)
    low_ratio = pl.max() / (pl.mean() + 1e-12)
    first = (np.argmax(pl) if low_ratio > 1.4 else np.argmax(pa)) * 0.005
    phase_source = "kick/low-band" if low_ratio > 1.4 else "broadband"
    # fine phase: the 2048-pt STFT flux peaks ~20-45 ms before the true onset (window leading edge);
    # re-search +-80 ms in 1 ms steps on a short-window (512/64 = 23 ms / 2.9 ms) flux, symmetric taps
    S2 = np.abs(librosa.stft(y, n_fft=512, hop_length=64))
    f2 = librosa.fft_frequencies(sr=SR, n_fft=512)
    X2 = np.log1p(10 * (S2[f2 < 150] if low_ratio > 1.4 else S2))
    fl2 = np.maximum(0, np.diff(X2, axis=1, prepend=X2[:, :1])).sum(0)
    fps2 = SR / 64.0
    best, best_v = first, -1.0
    for p in np.arange(first - 0.08, first + 0.08, 0.001):
        t = np.arange(p % period, dur - 0.1, period)
        fr = np.round(t * fps2).astype(int)
        fr = fr[(fr > 0) & (fr < len(fl2) - 1)]
        v = float(np.mean(fl2[fr - 1] + fl2[fr] + fl2[fr + 1])) if len(fr) else 0.0
        if v > best_v:
            best_v, best = v, p
    # joint period/phase polish (phase anchored mid-track so the two are decorrelated)
    mid_k = int((dur / 2 - best) / period)
    anchor = best + mid_k * period
    best_pp, best_v = (period, anchor), -1.0
    for pp in period * (1 + np.linspace(-6e-4, 6e-4, 25)):
        for an in np.arange(anchor - 0.015, anchor + 0.0155, 0.001):
            t = an + (np.arange(-mid_k - 2, int(dur / pp) - mid_k + 2)) * pp
            t = t[(t > 0.05) & (t < dur - 0.1)]
            fr = np.round(t * fps2).astype(int)
            fr = fr[(fr > 0) & (fr < len(fl2) - 1)]
            v = float(np.mean(fl2[fr - 1] + fl2[fr] + fl2[fr + 1])) if len(fr) else 0.0
            if v > best_v:
                best_v, best_pp = v, (pp, an)
    period = float(best_pp[0])
    first = float(best_pp[1] % period)
    grid = np.arange(first, dur - 0.05, period)

    # downbeats: arrangement changes happen on bar lines
    gf = np.clip(np.round(grid * fps).astype(int), 0, S.shape[1] - 1)
    lowE = 10 * np.log10((S[freqs < 150] ** 2).sum(0) + 1e-10)
    totE = 10 * np.log10((S ** 2).sum(0) + 1e-10)
    bl = np.array([lowE[a:b].mean() for a, b in zip(gf[:-1], gf[1:])])
    bt = np.array([totE[a:b].mean() for a, b in zip(gf[:-1], gf[1:])])
    votes = np.zeros(4)
    for arr in (bl, bt):
        w = 2
        ch = np.array([abs(arr[i:i + w].mean() - arr[i - w:i].mean()) for i in range(w, len(arr) - w)])
        for t_ in np.argsort(ch)[::-1][:12]:
            votes[(t_ + w) % 4] += ch[t_]
    chroma = librosa.feature.chroma_stft(S=S ** 2, sr=SR, hop_length=HOP)

    def cnorm(c):
        return c / (c.sum() + 1e-9)
    cn = np.nan_to_num(np.array([np.linalg.norm(cnorm(chroma[:, max(0, i - 8):i].mean(1)) - cnorm(chroma[:, i:i + 8].mean(1)))
                                 if i > 0 else 0.0 for i in gf]))
    cvote = np.array([cn[p::4].mean() for p in range(4)])
    phase_scores = list(votes / (votes.sum() + 1e-9) + 0.25 * cvote / (cvote.sum() + 1e-9))
    ph = int(np.argmax(phase_scores))
    downbeats = grid[ph::4]
    confidence = "low (automatic estimate - verify by ear)"
    if db_override is not None:
        if per_override:
            period = per_override
        first = db_override % period
        grid = np.arange(first, dur - 0.05, period)
        downbeats = np.arange(db_override % (4 * period), dur - 0.05, 4 * period)
        ph = int(round((downbeats[0] - first) / period)) % 4
        phase_source = "manual (--downbeat/--period)"
        confidence = "verified"
    if downbeats[0] - 4 * period > -0.05:
        downbeats = np.r_[max(0.0, downbeats[0] - 4 * period), downbeats]

    # energy curve: RMS dB per second
    nsec = int(np.ceil(dur))
    rms_db = np.array([round(float(20 * np.log10(np.sqrt(np.mean(y[i * SR:(i + 1) * SR] ** 2)) + 1e-9)), 1)
                       if len(y[i * SR:(i + 1) * SR]) else -120.0 for i in range(nsec)])

    # sections: bar-level novelty (4-bar checkerboard) on timbre + harmony + energy
    bar_fr = np.clip(np.round(downbeats * SR / HOP).astype(int), 0, S.shape[1] - 1)
    mfcc = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=S ** 2, sr=SR)), n_mfcc=13)
    rms_fr = librosa.feature.rms(S=S)[0]
    feats = np.vstack([librosa.util.normalize(mfcc, axis=1), chroma,
                       4 * librosa.util.normalize(np.log(rms_fr + 1e-6)[None, :], axis=1)])
    B = librosa.util.sync(feats, np.r_[0, bar_fr, S.shape[1]], aggregate=np.mean)
    Bz = (B - B.mean(axis=1, keepdims=True)) / (B.std(axis=1, keepdims=True) + 1e-9)
    ssm = np.nan_to_num(np.corrcoef(Bz.T))
    k = 4
    kern = np.kron(np.array([[1, -1], [-1, 1]]), np.ones((k, k)))
    nov = np.zeros(ssm.shape[0])
    for i in range(k, ssm.shape[0] - k):
        nov[i] = (ssm[i - k:i + k, i - k:i + k] * kern).sum()
    nov = np.maximum(nov, 0)
    peaks, _ = sps.find_peaks(nov, distance=4, height=np.percentile(nov, 70) if nov.max() > 0 else 0)
    bar_times = np.r_[0.0, downbeats]          # column 0 of B = before the first downbeat
    bounds = sorted(set([0.0] + [float(bar_times[p]) for p in peaks if 0 < p < len(bar_times)] + [dur]))
    loud_ref = np.percentile(rms_db, 90)
    sections = []
    for i, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        seg = rms_db[int(a):max(int(a) + 1, int(b))]
        m = float(np.mean(seg))
        lvl = "high" if m > loud_ref - 3 else ("mid" if m > loud_ref - 8 else "low")
        sections.append({"name": f"section_{i + 1}", "start": round(a, 3), "end": round(b, 3), "energy": lvl,
                         "mean_rms_db": round(m, 1), "note": "automatic (bar-level novelty)"})

    # phrase phase: novelty peaks tend to sit on phrase lines (bar index of a downbeat = column + 1)
    P = max(1, phrase_bars)
    bar_nov = nov[1:len(downbeats) + 1] if len(nov) > len(downbeats) else nov[:len(downbeats)]
    scores = [float(bar_nov[o::P].sum()) for o in range(min(P, len(bar_nov)))] or [0.0]
    off = int(np.argmax(scores))
    tot = sum(scores)
    phrase_conf = round(max(scores) / tot, 2) if tot > 0 else 0.0
    phrase_starts = [float(t) for t in downbeats[off::P]]

    # ending
    fr = 2048
    env = np.array([np.sqrt(np.mean(y[i:i + fr] ** 2)) for i in range(0, max(1, len(y) - fr), fr // 2)])
    env_db = 20 * np.log10(env + 1e-9)
    et = np.arange(len(env_db)) * (fr // 2) / SR
    last_sound = float(et[np.where(env_db > -60)[0][-1]]) if np.any(env_db > -60) else dur
    above = np.where(env_db > env_db.max() - 20)[0]
    last_loud = float(et[above[-1]]) if len(above) else dur
    t8 = env_db[et > last_sound - 8]
    slope = float(np.polyfit(np.arange(len(t8)), t8, 1)[0] / ((fr // 2) / SR)) if len(t8) > 5 else 0.0
    # final accent: strongest onset in the last bars before the level falls away, snapped to the grid
    o_t = np.arange(len(oenv)) / fps
    oenv_m = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)   # mean aggregation: chords/hits
    win = np.where((o_t > last_loud - 2 * 4 * period) & (o_t <= last_loud + 0.05))[0]
    fa = last_loud
    if len(win):
        pk, _ = sps.find_peaks(oenv_m[win])
        if len(pk):
            strong = o_t[win][pk[oenv_m[win][pk] >= 0.6 * oenv_m[win][pk].max()]]
            # the LAST big hit before the level falls away; a flam/double hit (< 0.25 s) counts as its first stroke
            fa = float(strong[-1])
            for t_ in strong[::-1][1:]:
                if fa - t_ < 0.25:
                    fa = float(t_)
                else:
                    break
    gnear = grid[np.argmin(np.abs(grid - fa))] if len(grid) else fa
    if abs(gnear - fa) < 0.08:
        fa = float(gnear)
    ending = {"last_sound_s": round(last_sound, 2), "last_loud_s": round(last_loud, 2),
              "decay_after_last_loud_s": round(last_sound - last_loud, 2), "slope_last8s_db_per_s": round(slope, 2),
              "trailing_silence_s": round(dur - last_sound, 2)}
    fit = grid_fit(y, oenv, fl2, fps2, period, first, dur, last_sound)
    tracked = tracked_bars(y, oenv, fl2, fps2, S, freqs, fit["beats"], dur) if fit["beats"] is not None else None
    return dict(dur=dur, tempo=tempo, beats_detected=beats, period=period, first=first, grid=grid,
                grid_rms_ms=grid_rms_ms, phase_source=phase_source, ph=ph, phase_scores=phase_scores,
                confidence=confidence, downbeats=downbeats, rms_db=rms_db, sections=sections,
                novelty_peaks=[round(float(bar_times[p]), 3) for p in peaks if p < len(bar_times)],
                phrase_offset=off, phrase_conf=phrase_conf, phrase_starts=phrase_starts, phrase_bars=P,
                ending=ending, final_accent=fa, fit=fit, tracked=tracked)


RUBATO_RMS_MS = 40.0     # constant-grid residual above this -> the track is not click-locked


def grid_drift(fl2, fps2, period, first, dur, win=6.0):
    """How well does ONE constant tempo fit?  In 6 s windows (3 s hop) the constant grid is shifted to the best
    local phase against the onsets; a click-locked track needs (nearly) the same shift everywhere, a rubato
    one drifts.  Doubled phases (half-beat ambiguity: a grid may lock to off-beat hats), unwrapped, a linear
    trend removed (a slightly wrong period is no rubato) -> rms of what is left, ms.  Measured: synthetic click
    bed 0, Fretless (DAW, 100 BPM) 11, Senbazuru (rubato koto) 73, synthetic rubato 71."""
    offs = np.arange(-period / 2, period / 2, 0.005)
    ts, ds = [], []
    for a in np.arange(0, max(0.0, dur - win), win / 2):
        g = np.arange(first + np.ceil((a - first) / period) * period, a + win, period)
        prof = []
        for d in offs:
            fr = np.round((g + d) * fps2).astype(int)
            fr = fr[(fr > 0) & (fr < len(fl2) - 1)]
            prof.append(np.mean(fl2[fr - 1] + fl2[fr] + fl2[fr + 1]) if len(fr) else 0.0)
        prof = np.array(prof)
        if prof.mean() <= 0 or prof.max() / prof.mean() < 1.15:      # no clear pulse in this window
            continue
        ts.append(a)
        ds.append(offs[int(np.argmax(prof))])
    if len(ds) < 4:
        return None, None
    th = np.unwrap(4 * np.pi * np.array(ds) / period)
    b, a0 = np.polyfit(np.array(ts), th, 1)
    res = (th - (a0 + b * np.array(ts))) / (4 * np.pi) * period
    return round(float(np.sqrt(np.mean(res ** 2)) * 1000), 1), round(float(np.percentile(np.abs(res), 90) * 1000), 1)


def grid_fit(y, oenv, fl2, fps2, period, first, dur, last_sound):
    """Constant-grid drift (grid_drift) + loosely tracked, onset-refined beats (used as the bar lines of a
    rubato track).  Returns {rms_ms, p90_ms, beats}."""
    import librosa
    rms_ms, p90_ms = grid_drift(fl2, fps2, period, first, min(dur, last_sound + 0.5))
    _, tb = librosa.beat.beat_track(onset_envelope=oenv, sr=SR, hop_length=HOP, start_bpm=60.0 / period,
                                    tightness=60, units="time")
    tb = np.asarray(tb, float)
    tb = tb[(tb > 0.05) & (tb < min(dur, last_sound + 0.5) - 0.05)]
    if len(tb) < 8:
        return {"rms_ms": rms_ms, "p90_ms": p90_ms, "beats": None}
    ref = []                                   # refine each tracked beat on the short-window flux (+-60 ms)
    for t in tb:
        a, b = int((t - 0.06) * fps2), int((t + 0.06) * fps2) + 1
        a, b = max(a, 1), min(b, len(fl2) - 1)
        if b <= a:
            ref.append(t)
            continue
        w = fl2[a:b] * np.hanning(b - a + 2)[1:-1]
        ref.append((a + int(np.argmax(w))) / fps2 if w.max() > 0 else t)
    return {"rms_ms": rms_ms, "p90_ms": p90_ms, "beats": np.array(sorted(ref))}


def tracked_bars(y, oenv, fl2, fps2, S, freqs, tb, dur):
    """Bar lines from tracked beats (rubato tracks): the downbeat phase (which beat of 4) is voted like the
    constant-grid downbeats (bar-line energy / harmony changes, low-band onsets), then every bar line is
    refined to the strongest nearby onset.  Returns {bar_starts, beats, phase, bar_lengths}."""
    import librosa
    if tb is None or len(tb) < 12:
        return None
    fps = SR / HOP
    gf = np.clip(np.round(tb * fps).astype(int), 0, S.shape[1] - 1)
    lowE = 10 * np.log10((S[freqs < 150] ** 2).sum(0) + 1e-10)
    totE = 10 * np.log10((S ** 2).sum(0) + 1e-10)
    bl = np.array([lowE[a:b].mean() if b > a else lowE[a] for a, b in zip(gf[:-1], gf[1:])])
    bt = np.array([totE[a:b].mean() if b > a else totE[a] for a, b in zip(gf[:-1], gf[1:])])
    votes = np.zeros(4)
    for arr in (bl, bt):
        w = 2
        ch = np.array([abs(arr[i:i + w].mean() - arr[i - w:i].mean()) for i in range(w, len(arr) - w)])
        for t_ in np.argsort(ch)[::-1][:12]:
            votes[(t_ + w) % 4] += ch[t_]
    chroma = librosa.feature.chroma_stft(S=S ** 2, sr=SR, hop_length=HOP)
    cn = np.nan_to_num(np.array([np.linalg.norm(chroma[:, max(0, i - 8):i].mean(1) / (chroma[:, max(0, i - 8):i].sum() + 1e-9)
                                                - chroma[:, i:i + 8].mean(1) / (chroma[:, i:i + 8].sum() + 1e-9))
                                 if i > 0 else 0.0 for i in gf]))
    # primary cue: a bass note / low thump on the downbeat (low-band onsets at the beat); measured on the koto
    # piece Senbazuru: low-band 1.23 vs <= 0.93 for the other phases, while broadband onsets pointed elsewhere
    Xl = np.log1p(10 * S[freqs < 150])
    lowfl = np.r_[0, np.maximum(0, np.diff(Xl, axis=1)).sum(0)]
    lo_on = np.array([lowfl[max(0, i - 2):i + 3].max() for i in gf])
    low_ratio = np.array([lo_on[p::4].mean() for p in range(4)]) / (lo_on.mean() + 1e-9)
    score = (low_ratio - 1.0) + 0.5 * (votes / (votes.sum() + 1e-9) - 0.25) \
        + 0.25 * (np.array([cn[p::4].mean() for p in range(4)]) / (cn.mean() + 1e-9) - 1.0)
    ph = int(np.argmax(score))
    bars = tb[ph::4]
    if ph > 0 and len(tb) > 4:                 # extrapolate one bar back if the track starts mid-bar
        b0 = bars[0] - (bars[1] - bars[0]) if len(bars) > 1 else None
        if b0 is not None and b0 > -0.05:
            bars = np.r_[max(0.0, b0), bars]
    bl_s = np.diff(bars)
    return {"bar_starts": [round(float(t), 3) for t in bars], "beats": [round(float(t), 3) for t in tb],
            "phase": ph, "bar_lengths": [round(float(x), 3) for x in bl_s]}


def bar_similarity(y, first_downbeat, period):
    """Bar x bar similarity matrix (chroma + MFCC + RMS per beat, 4 beats per bar), bar 1 = first_downbeat."""
    import librosa
    dur = len(y) / SR
    beats = np.arange(first_downbeat, dur, period)
    bf = np.round(beats * SR / HOP).astype(int)
    C = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    M = librosa.feature.mfcc(y=y, sr=SR, hop_length=HOP, n_mfcc=14)[1:]
    R = np.log(librosa.feature.rms(y=y, hop_length=HOP) + 1e-6)
    n = min(C.shape[1], M.shape[1], R.shape[1])
    idx = bf[bf < n]
    Cb = librosa.util.sync(C[:, :n], idx, aggregate=np.mean)[:, 1:]
    Mb = librosa.util.sync(M[:, :n], idx, aggregate=np.mean)[:, 1:]
    Rb = librosa.util.sync(R[:, :n], idx, aggregate=np.mean)[:, 1:]
    nb = Cb.shape[1] // 4

    def z(X):
        return (X - X.mean(1, keepdims=True)) / (X.std(1, keepdims=True) + 1e-9)
    F = np.vstack([z(Cb) * 1.0, z(Mb) * 0.6, z(Rb) * 2.0])[:, :nb * 4]
    bars = F.reshape(F.shape[0], nb, 4).transpose(1, 0, 2).reshape(nb, -1)
    bars = (bars - bars.mean(1, keepdims=True)) / (bars.std(1, keepdims=True) + 1e-9)
    return bars @ bars.T / bars.shape[1]


def jump_score(Sim, i, j):
    """Jump from the END of bar i to the START of bar j (1-based): (sim(bar i, bar j-1), sim(bar i+1, bar j))."""
    nb = Sim.shape[0]
    a = float(Sim[i - 1, j - 2]) if 1 <= i <= nb and 2 <= j <= nb + 1 else float("nan")
    b = float(Sim[i, j - 1]) if i < nb and 1 <= j <= nb else float("nan")
    return a, b


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--bpm-hint", type=float, help="expected tempo (catalog BPM) - helps the tracker")
    ap.add_argument("--downbeat", type=float, help="verified time (s) of any downbeat (bar line)")
    ap.add_argument("--period", type=float, help="verified beat period (s), with --downbeat")
    ap.add_argument("--phrase-bars", type=int, default=8, help="bars per phrase (default 8)")
    ap.add_argument("--jump", action="append", default=[], metavar="I:J",
                    help="score a splice from the end of bar I to the start of bar J (repeatable)")
    ap.add_argument("--suggest-jumps", type=int, default=0, metavar="N", help="list the N best phrase-line splices")
    ap.add_argument("--min-remove", type=int, default=4, help="suggested splices remove at least this many bars")
    ap.add_argument("--grid", choices=["auto", "constant", "tracked"], default="auto",
                    help="beats/downbeats from one constant tempo, from tracked bar lines (rubato / live music), "
                         "or auto: tracked when the constant grid misses by > 40 ms rms (default)")
    ap.add_argument("--json", help="output JSON (default <name>_beats.json in the CWD; '-' = stdout)")
    a = ap.parse_args()
    t0 = time.time()
    name = os.path.splitext(os.path.basename(a.audio))[0]
    y = decode(a.audio)
    if len(y) < SR * 4:
        sys.exit("audio shorter than 4 s")
    r = analyse(y, a.bpm_hint, a.downbeat, a.period, a.phrase_bars)
    per, dbs, dur = r["period"], r["downbeats"], r["dur"]
    grid = r["grid"]
    beats_out = [round(float(b), 4) for b in grid]
    out = {
        "plan": f"analysis of '{name}' (whole track, no edit)",
        "generated": time.strftime("%Y-%m-%d"),
        "tracks": [{"file": os.path.abspath(a.audio), "title": name}],
        "segments": [{"track_file": os.path.abspath(a.audio), "src_in": 0.0, "src_out": round(dur, 4),
                      "timeline_start": 0.0, "timeline_end": round(dur, 4), "fade_in": 0.0, "fade_out": 0.0,
                      "source_bars": f"1-{len(dbs)}", "note": "whole track"}],
        "total_duration": round(dur, 3),
        "bpm": round(60.0 / per, 3), "beat_period": round(per, 6), "bar_length": round(4 * per, 6),
        "time_signature": "4/4",
        "phrase_length_bars": r["phrase_bars"], "phrase_length_s": round(r["phrase_bars"] * 4 * per, 4),
        "beats": beats_out,
        "downbeats": [round(float(t), 4) for t in dbs],
        "phrase_starts": [round(t, 4) for t in r["phrase_starts"]],
        "downbeat_source_bar": [[round(float(t), 4), i + 1] for i, t in enumerate(dbs)],
        "sections": r["sections"],
        "final_accent": round(r["final_accent"], 3),
        "recommended_end": round(r["ending"]["last_sound_s"], 3),
        "recommended_end_note": "Where the track's sound ends (level < -60 dBFS). final_accent is an automatic "
                                "estimate of the last big hit - check by ear.",
        "energy": {"rms_db_per_sec": r["rms_db"].tolist()},
        "analysis": {"librosa_bpm": round(r["tempo"], 2), "grid_first_beat": round(float(r["first"]), 4),
                     "grid_fit_rms_ms": round(r["grid_rms_ms"], 1), "beat_phase_source": r["phase_source"],
                     "downbeat_phase": r["ph"], "downbeat_confidence": r["confidence"],
                     "downbeat_phase_scores": [round(float(s), 3) for s in r["phase_scores"]],
                     "phrase_offset_bars": r["phrase_offset"], "phrase_confidence": r["phrase_conf"],
                     "novelty_bar_peaks": r["novelty_peaks"], "ending": r["ending"],
                     "beats_detected": [round(float(b), 3) for b in r["beats_detected"]],
                     "beat0_for_music_bed": round(float(dbs[0]), 4),
                     "seconds": None},
    }
    if a.jump or a.suggest_jumps:
        Sim = bar_similarity(y, float(dbs[0]), per)
        nb = Sim.shape[0]
        tri = Sim[np.triu_indices(nb, 1)]
        out["bar_similarity_reference"] = {"bars": nb, "upper_decile": round(float(np.percentile(tri, 90)), 2),
                                           "median": round(float(np.median(tri)), 2)}

        def jrec(i, j):
            s1, s2 = jump_score(Sim, i, j)
            return {"from_bar_end": i, "to_bar_start": j, "removes_bars": j - i - 1,
                    "src_out": round(float(dbs[0] + i * 4 * per), 4), "src_in": round(float(dbs[0] + (j - 1) * 4 * per), 4),
                    "removes_s": round((j - i - 1) * 4 * per, 3),
                    "sim_pre": None if np.isnan(s1) else round(s1, 3), "sim_post": None if np.isnan(s2) else round(s2, 3)}
        if a.jump:
            out["jumps"] = []
            for spec in a.jump:
                i, j = (int(v) for v in spec.split(":"))
                out["jumps"].append(jrec(i, j))
        if a.suggest_jumps:
            P, off = r["phrase_bars"], r["phrase_offset"]
            ends = [b for b in range(1, nb) if (b - off) % P == 0]
            starts = [b for b in range(2, nb + 1) if (b - 1 - off) % P == 0]
            cand = []
            for i in ends:
                for j in starts:
                    if j - i - 1 >= a.min_remove:
                        rec = jrec(i, j)
                        s = [v for v in (rec["sim_pre"], rec["sim_post"]) if v is not None]
                        if s:
                            rec["score"] = round(min(s), 3)
                            cand.append(rec)
            cand.sort(key=lambda q: -q["score"])
            out["jump_suggestions"] = cand[:a.suggest_jumps]
    fit, trk = r["fit"], r["tracked"]
    out["analysis"]["constant_grid_residual_ms"] = fit["rms_ms"]
    out["analysis"]["constant_grid_residual_p90_ms"] = fit["p90_ms"]
    rubato = fit["rms_ms"] is not None and fit["rms_ms"] > RUBATO_RMS_MS
    use_tracked = trk is not None and (a.grid == "tracked" or (a.grid == "auto" and rubato and a.downbeat is None))
    out["tempo_mode"] = ("rubato" if rubato else "steady") + (" (tracked bar lines)" if use_tracked else " (constant grid)")
    if use_tracked:
        bars = trk["bar_starts"]
        out["analysis"]["constant_grid"] = {"beat0": out["downbeats"][0], "beat_period": out["beat_period"],
                                            "note": "one constant tempo - NOT used (rubato)"}
        out["beats"] = trk["beats"]
        out["downbeats"] = bars
        out["bar_starts"] = bars
        out["downbeat_source_bar"] = [[t, i + 1] for i, t in enumerate(bars)]
        old_ph = out["phrase_starts"]
        P = r["phrase_bars"]
        if old_ph:                              # phrase phase from the novelty analysis, moved to the tracked bars
            k0 = int(np.argmin([abs(b - old_ph[0]) for b in bars])) % P
        else:
            k0 = 0
        out["phrase_starts"] = bars[k0::P]
        bl = np.diff(bars) if len(bars) > 1 else np.array([4 * per])
        out["beat_period"] = round(float(np.median(bl)) / 4, 6)
        out["bar_length"] = round(float(np.median(bl)), 6)
        out["bpm"] = round(60.0 / out["beat_period"], 3)
        out["analysis"]["bar_length_range_s"] = [round(float(bl.min()), 3), round(float(bl.max()), 3)]
    out["analysis"]["seconds"] = round(time.time() - t0, 1)
    if a.json == "-":
        print(json.dumps(out, indent=1))
        return 0
    path = a.json or f"{name}_beats.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    an = out["analysis"]
    print(f"{name}: {dur:.2f} s | {out['bpm']:.2f} BPM (librosa {an['librosa_bpm']}, grid fit {an['grid_fit_rms_ms']} ms, "
          f"phase {an['beat_phase_source']}) | first beat {an['grid_first_beat']:.3f} | first downbeat "
          f"{out['downbeats'][0]:.3f} ({an['downbeat_confidence']}) | {len(out['downbeats'])} bars")
    print("  phrase starts:", ", ".join(f"{t:.2f}" for t in out["phrase_starts"]),
          f"(confidence {an['phrase_confidence']})")
    print("  sections:", "; ".join(f"{s['start']:.1f}-{s['end']:.1f} {s['energy']}" for s in out["sections"]))
    print(f"  final accent ~{out['final_accent']:.2f} s, sound ends {out['recommended_end']:.2f} s | ending {an['ending']}")
    if an.get("constant_grid_residual_ms") is not None:
        rub = out["tempo_mode"].startswith("rubato")
        print(f"  tempo: {out['tempo_mode']} - the constant grid's local phase drifts by "
              f"{an['constant_grid_residual_ms']} ms rms (p90 {an['constant_grid_residual_p90_ms']} ms; rubato above "
              f"{RUBATO_RMS_MS:g})" + (f"; bars {an['bar_length_range_s'][0]}-{an['bar_length_range_s'][1]} s - CUT ON "
                                      f"THESE MEASURED BAR LINES (bar_starts), verify a few by ear" if "bar_length_range_s" in an
                                      else ("" if not rub else " - pass --grid tracked")))
    print("  RMS dB/s:", " ".join(str(int(v)) for v in out["energy"]["rms_db_per_sec"]))
    for jj in out.get("jumps", []) + out.get("jump_suggestions", []):
        print(f"  jump end of bar {jj['from_bar_end']} -> start of bar {jj['to_bar_start']} (src {jj['src_out']:.3f} -> "
              f"{jj['src_in']:.3f}, removes {jj['removes_bars']} bars / {jj['removes_s']:.1f} s): "
              f"sim pre {jj['sim_pre']}, post {jj['sim_post']}")
    if "bar_similarity_reference" in out:
        ref = out["bar_similarity_reference"]
        print(f"  ({ref['bars']} bars; repeats of identical sections score ~{ref['upper_decile']}, median pair {ref['median']})")
    print(f"JSON: {os.path.abspath(path)}  ({an['seconds']} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

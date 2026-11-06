"""Audio: clip sound placement with micro-fades / equal-power crossfades, music bed with smooth
ducking under nat-sound items and an end fade, then two-pass EBU R128 loudnorm (linear) with a
true-peak ceiling.  Everything is mixed in float32 numpy at 48 kHz stereo."""
import json
import math
import os
import re
import wave

import numpy as np

from common import FFMPEG, run, log, db2lin

SR = 48000
CLIP_REF_LUFS = -20.0   # every clip's sound (120 Hz high-passed) is first normalised to this, then
                        # nat_gain_db (nat_sound items, default 0 -> -20 LUFS) or audio_gain_db applies
MUSIC_REF_LUFS = -16.0  # the music bed is normalised to this, then music.gain_db applies
MICRO_FADE = 0.015      # seconds, at every hard cut


def read_wav(path, nsamp=None):
    """Decode any audio file to float32 stereo 48 kHz via ffmpeg."""
    p = run([FFMPEG, "-nostdin", "-v", "error", "-i", path, "-map", "0:a:0", "-ac", "2", "-ar", str(SR),
             "-f", "f32le", "-"])
    x = np.frombuffer(p.stdout, np.float32).reshape(-1, 2).copy()
    if nsamp is not None:
        if len(x) < nsamp:
            x = np.concatenate([x, np.zeros((nsamp - len(x), 2), np.float32)])
        x = x[:nsamp]
    return x


def write_wav_f32(path, x):
    """float32 WAV (IEEE float, format 3) written by hand so we don't depend on soundfile."""
    x = np.ascontiguousarray(x.astype(np.float32))
    n, ch = x.shape
    data = x.tobytes()
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write((4 + 26 + 12 + 8 + len(data)).to_bytes(4, "little"))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write((18).to_bytes(4, "little"))
        f.write((3).to_bytes(2, "little"))            # WAVE_FORMAT_IEEE_FLOAT
        f.write(ch.to_bytes(2, "little"))
        f.write(SR.to_bytes(4, "little"))
        f.write((SR * ch * 4).to_bytes(4, "little"))
        f.write((ch * 4).to_bytes(2, "little"))
        f.write((32).to_bytes(2, "little"))
        f.write((0).to_bytes(2, "little"))
        f.write(b"fact")
        f.write((4).to_bytes(4, "little"))
        f.write(n.to_bytes(4, "little"))
        f.write(b"data")
        f.write(len(data).to_bytes(4, "little"))
        f.write(data)


def lufs(x, sr=SR):
    """ITU-R BS.1770-4 integrated loudness (K-weighting, 400 ms blocks, abs + relative gates)."""
    from scipy.signal import lfilter
    if len(x) < int(0.4 * sr):
        x = np.concatenate([x, np.zeros((int(0.4 * sr) - len(x), x.shape[1]), np.float32)])
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = lfilter(b2, a2, lfilter(b1, a1, x.astype(np.float64), axis=0), axis=0)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    sq = np.cumsum(np.concatenate([np.zeros((1, y.shape[1])), y * y]), axis=0)
    starts = np.arange(0, len(y) - blk + 1, hop)
    z = (sq[starts + blk] - sq[starts]) / blk
    zs = z.sum(axis=1)
    lk = -0.691 + 10 * np.log10(np.maximum(zs, 1e-20))
    g = zs[lk > -70]
    if len(g) == 0:
        return -math.inf
    rel = -0.691 + 10 * math.log10(g.mean()) - 10
    g2 = zs[(lk > -70) & (lk > rel)]
    return -0.691 + 10 * math.log10(g2.mean()) if len(g2) else -math.inf


def _ramp(n, kind="sin"):
    t = (np.arange(n) + 0.5) / max(1, n)
    if kind == "sin":       # equal-power fade-in
        return np.sin(t * np.pi / 2)
    return 0.5 - 0.5 * np.cos(np.pi * t)  # raised cosine (equal-gain) fade-in


def build_mix(edl, results, workdir):
    """Return (mix float32 stereo, report dict)."""
    tl = edl["timeline"]
    fps = tl["fps"]
    spf = SR / fps
    total = int(round(tl["total_f"] * spf))
    mix = np.zeros((total, 2), np.float32)
    rep = {"clips": {}}
    mf = int(MICRO_FADE * SR)
    rows = tl["rows"]
    for r, it in zip(rows, edl["items"]):
        res = results.get(it["id"], {})
        apath = res.get("audio")
        n = int(round(r["n"] * spf))
        s0 = int(round(r["start_f"] * spf))
        if not apath or not os.path.exists(apath):
            continue
        x = read_wav(apath, n)
        L = lufs(x)
        if not math.isfinite(L) or L < -60:
            rep["clips"][it["id"]] = "silent"
            continue
        norm_db = min(15.0, CLIP_REF_LUFS - L)  # never boost by more than 15 dB (hiss)
        if it.get("nat_sound"):
            g_db = float(it.get("nat_gain_db", 0.0))
        else:
            g_db = float(it.get("audio_gain_db", -18.0))
        if it.get("mute"):
            continue
        g = db2lin(norm_db + g_db)
        env = np.ones(n, np.float32)
        # head: crossfade-in under an overlapping transition, else micro-fade (film start too)
        if r["o_in"] > 0:
            k = min(n, int(round(r["o_in"] * spf)))
            env[:k] *= _ramp(k, "sin")
        else:
            k = min(n, mf)
            env[:k] *= _ramp(k, "cos")
        if r["o_out"] > 0:
            k = min(n, int(round(r["o_out"] * spf)))
            env[n - k:] *= _ramp(k, "sin")[::-1]
        else:
            k = min(n, mf if r["t_out"] is not None else int(0.25 * SR))
            env[n - k:] *= _ramp(k, "cos")[::-1]
        mix[s0:s0 + n] += x * (env[:, None] * g)
        rep["clips"][it["id"]] = f"{L:.1f} LUFS -> {norm_db:+.1f} {g_db:+.1f} dB"

    m = edl.get("music") or {}
    mpath = m.get("path")
    if mpath and os.path.exists(mpath):
        off = int(float(m.get("offset", 0.0)) * SR)
        mus = read_wav(mpath)
        mus = mus[off:]
        if len(mus) < total:
            log(f"WARNING music ({len(mus)/SR:.1f}s) shorter than film ({total/SR:.1f}s); padded with silence")
            mus = np.concatenate([mus, np.zeros((total - len(mus), 2), np.float32)])
        mus = mus[:total]
        L = lufs(mus)
        mg = (MUSIC_REF_LUFS - L if math.isfinite(L) else 0.0) + float(m.get("gain_db", 0.0))
        # ducking envelope (dB) under nat-sound items, smooth raised-cosine ramps outside the item
        duck_db = float(m.get("duck_db", -8.0))
        ramp = float(m.get("duck_ramp", 0.3))
        d = np.zeros(total, np.float32)
        rs = int(ramp * SR)
        for r, it in zip(rows, edl["items"]):
            if not it.get("nat_sound"):
                continue
            a = int(round(r["start_f"] * spf))
            b = int(round(r["end_f"] * spf))
            w = it.get("duck_window")  # [t0, t1] seconds from item start: duck only around the moment
            if w:
                a, b = a + int(round(float(w[0]) * SR)), min(b, a + int(round(float(w[1]) * SR)))
            seg = np.zeros(total, np.float32)
            seg[a:b] = 1
            lo = max(0, a - rs)
            seg[lo:a] = _ramp(rs, "cos")[rs - (a - lo):]
            hi = min(total, b + rs)
            seg[b:hi] = _ramp(rs, "cos")[::-1][:hi - b]
            d = np.maximum(d, seg)
        gain = (10 ** ((mg + duck_db * d) / 20)).astype(np.float32)
        fin = float(m.get("fade_in", 0.0))
        if fin > 0:
            k = min(total, int(fin * SR))
            gain[:k] *= _ramp(k, "cos")
        fo = float(m.get("fade_out", 2.5))
        if fo > 0:
            k = min(total, int(fo * SR))
            # exponential-ish (perceptually even) fade: cosine in the dB domain
            t = (np.arange(k) + 0.5) / k
            gain[total - k:] *= (0.5 + 0.5 * np.cos(np.pi * t)) ** 2
        mix += mus * gain[:, None]
        rep["music"] = f"{os.path.basename(mpath)} {L:.1f} LUFS -> gain {mg:+.1f} dB, duck {duck_db} dB"
    elif mpath:
        log(f"WARNING music not found: {mpath} (rendering without music)")
        rep["music"] = "missing"
    return mix, rep


def _loudnorm_measure(path, I, TP, LRA):
    p = run([FFMPEG, "-nostdin", "-hide_banner", "-i", path, "-af",
             f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"])
    txt = p.stderr.decode("utf-8", "replace")
    j = json.loads(txt[txt.rindex("{"):txt.rindex("}") + 1])
    return j


def normalise(mix, out_wav, target=-14.0, tp=-1.5, workdir="."):
    """Two-pass loudnorm in linear mode.  If the peaks would exceed the ceiling after the linear gain,
    a transparent look-ahead limiter (at 4x oversampling, so it acts on true peaks) runs first.
    The internal TP target keeps 0.5 dB headroom for the AAC encoder's overshoot."""
    raw = os.path.join(workdir, "mix_raw.wav")
    write_wav_f32(raw, mix)
    tp_int = tp - 0.5
    LRA = 20
    m1 = _loudnorm_measure(raw, target, tp_int, LRA)
    I1, TP1 = float(m1["input_i"]), float(m1["input_tp"])
    src = raw
    info = {"pass1_I": I1, "pass1_TP": TP1}
    if not math.isfinite(I1) or I1 < -70:
        log("WARNING mix is silent")
        write_wav_f32(out_wav, mix)
        os.remove(raw)
        return info
    gain = target - I1
    if TP1 + gain > tp_int - 0.1:
        # peaks would exceed the ceiling after the linear gain: transparent look-ahead limiter at 4x
        # oversampling (acts on true peaks) 1 dB under the ceiling.  The limiter itself lowers the
        # loudness a little, so iterate (max 4x) until the linear pass needs < +0.3 dB.
        lim = os.path.join(workdir, "mix_lim.wav")
        ceiling = db2lin(tp_int - 1.0)
        g = gain
        for _ in range(4):
            run([FFMPEG, "-nostdin", "-v", "error", "-y", "-i", raw, "-af",
                 f"volume={g:.3f}dB,aresample=192000,alimiter=limit={ceiling:.5f}:attack=1.5:release=60:"
                 f"level=false:latency=true,aresample=48000", "-c:a", "pcm_f32le", lim])
            m1 = _loudnorm_measure(lim, target, tp_int, LRA)
            short = target - float(m1["input_i"])
            if short < 0.3 or float(m1["input_tp"]) + short <= tp_int - 0.1:
                break
            g += short
        src = lim
        info["limiter"] = f"pre-limited at {tp_int - 1.0:.1f} dBTP (gain {g:+.2f} dB first)"
    meas = (f"measured_I={m1['input_i']}:measured_TP={m1['input_tp']}:measured_LRA={m1['input_lra']}:"
            f"measured_thresh={m1['input_thresh']}:offset={m1['target_offset']}")
    p = run([FFMPEG, "-nostdin", "-hide_banner", "-y", "-i", src, "-af",
             f"loudnorm=I={target}:TP={tp_int}:LRA={LRA}:{meas}:linear=true:print_format=json,aresample={SR}",
             "-c:a", "pcm_f32le", out_wav])
    txt = p.stderr.decode("utf-8", "replace")
    j = json.loads(txt[txt.rindex("{"):txt.rindex("}") + 1])
    info.update({"type": j.get("normalization_type"), "out_I": j.get("output_i"), "out_TP": j.get("output_tp")})
    if j.get("normalization_type") != "linear":
        # never accept loudnorm's dynamic mode (it can pump): exact linear gain instead
        g2 = target - float(m1["input_i"])
        run([FFMPEG, "-nostdin", "-v", "error", "-y", "-i", src, "-af", f"volume={g2:.3f}dB",
             "-c:a", "pcm_f32le", out_wav])
        info.update({"type": f"linear gain {g2:+.2f} dB (loudnorm wanted dynamic)"})
    for f in (raw, os.path.join(workdir, "mix_lim.wav")):  # disk is precious
        try:
            os.remove(f)
        except OSError:
            pass
    return info

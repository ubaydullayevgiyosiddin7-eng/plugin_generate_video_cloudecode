"""Colour grading: presets + per-item adjustments baked into one 3D LUT (.cube) per item.

The same LUT code path (ffmpeg lut3d, tetrahedral) is used for video and photos, so a preset looks
identical on both. All maths is on display-referred Rec.709/sRGB values in [0,1]; exposure and white
balance are done in linear light, contrast/saturation in gamma space (like a colourist's primaries).
"""
import os

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float64)

PRESETS = {
    # identity
    "none": {},
    # clean, true-to-life: tiny warmth, a touch of contrast and vibrance
    "natural": dict(temperature=3, contrast=0.07, saturation=1.03, vibrance=0.10, shoulder=0.88),
    # sunny family-trip look: warm, punchy midtones, vibrant but skin-safe colours
    "warm_pop": dict(temperature=10, tint=-1, contrast=0.16, saturation=1.04, vibrance=0.22,
                     black=0.008, shoulder=0.86, split_hi=(0.012, 0.004, -0.010)),
    # gentle film look: lifted blacks, rolled highlights, slightly muted colours, teal/amber split
    "cinematic_soft": dict(temperature=5, contrast=0.10, saturation=0.90, vibrance=0.06,
                           lift=0.035, hi_max=0.965, shoulder=0.82,
                           split_lo=(-0.014, 0.004, 0.016), split_hi=(0.016, 0.006, -0.012)),
}


def _to_lin(x):
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def _to_gam(x):
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def _shoulder(x, knee):
    """Soft highlight roll-off above `knee` (C1-continuous, asymptote 1.0)."""
    if knee is None or knee >= 1.0:
        return np.clip(x, 0, 1)
    r = 1.0 - knee
    y = np.where(x > knee, knee + r * np.tanh((x - knee) / r), x)
    return np.clip(y, 0, 1)


def _wb(lin, temperature, tint):
    if not temperature and not tint:
        return lin
    t = temperature / 100.0
    g = np.array([1.0 + 0.10 * t, 1.0 - 0.06 * tint / 100.0 + 0.01 * t, 1.0 - 0.12 * t])
    g /= float(LUMA @ g)  # keep luminance
    return lin * g


def _scurve(x, c):
    if not c:
        return x
    return x - c * np.sin(2 * np.pi * x) / (2 * np.pi)


def _sat(x, sat, vib):
    luma = (x @ LUMA)[..., None]
    if vib:
        mx, mn = x.max(-1, keepdims=True), x.min(-1, keepdims=True)
        s = (mx - mn) / np.maximum(mx, 1e-4)
        sat = sat * (1.0 + vib * (1.0 - s) ** 2)
    return luma + (x - luma) * sat


def apply_grade(rgb, preset="natural", adjust=None):
    """rgb: float array (..., 3) in [0,1] -> graded float array."""
    p = dict(PRESETS.get(preset, {}))
    a = dict(adjust or {})
    x = np.asarray(rgb, np.float64)
    # --- per-item correction (applied first, in linear light) ---
    lin = _to_lin(x)
    ev = float(a.get("exposure", 0.0))
    if ev:
        lin = lin * (2.0 ** ev)
    lin = _wb(lin, float(a.get("temperature", 0.0)), float(a.get("tint", 0.0)))
    # --- preset white balance ---
    lin = _wb(lin, float(p.get("temperature", 0.0)), float(p.get("tint", 0.0)))
    x = _to_gam(lin)
    x = _shoulder(x, p.get("shoulder", 0.9 if (ev > 0 or a.get("temperature")) else None))
    # --- tone ---
    if p.get("black"):
        b = p["black"]
        x = np.clip((x - b) / (1 - b), 0, 1)
    x = _scurve(x, p.get("contrast", 0.0) + float(a.get("contrast", 0.0)))
    # --- colour ---
    x = _sat(x, p.get("saturation", 1.0) * float(a.get("saturation", 1.0)), p.get("vibrance", 0.0))
    luma = np.clip(x @ LUMA, 0, 1)[..., None]
    if p.get("split_lo"):
        x = x + np.array(p["split_lo"]) * (1 - luma) ** 2
    if p.get("split_hi"):
        x = x + np.array(p["split_hi"]) * luma ** 2
    x = np.clip(x, 0, 1)
    if p.get("lift") or p.get("hi_max"):
        lo, hi = p.get("lift", 0.0), p.get("hi_max", 1.0)
        x = lo + (hi - lo) * x
    return np.clip(x, 0, 1)


def make_lut(preset, adjust=None, size=33):
    g = np.linspace(0, 1, size)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")  # r fastest in file order
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    return apply_grade(rgb, preset, adjust)


def write_cube(path, preset, adjust=None, size=33):
    lut = make_lut(preset, adjust, size)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="\n") as f:
        f.write(f'TITLE "{preset}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        f.write("\n".join(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}" for v in lut))
        f.write("\n")
    os.replace(tmp, path)
    return path


def grade_image_u8(img, preset, adjust=None):
    """Exact (non-LUT) grade of a uint8 RGB image - used only for previews/contact sheets."""
    return (apply_grade(img.astype(np.float64) / 255.0, preset, adjust) * 255 + 0.5).astype(np.uint8)

"""Animated text overlays rendered with Pillow (FreeType) + OpenCV sub-pixel sprite warps.

Styles: title (per-letter pop-in, gradient fill, outline, shadow, glow, sparkles + shine sweep),
subtitle, label (pill lower-third), credit.  Every text is kept inside the Reels safe zone
(top 14 %, bottom 22 %, 6 % sides).  Unicode: per-glyph fallback; Uzbek okina/apostrophe
(U+02BB / U+02BC) are mapped to U+2018 / U+2019 when the display font lacks them.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import FONT_DIR, log

SAFE = dict(top=0.14, bottom=0.22, side=0.06)
SUBST = {0x02BB: 0x2018, 0x02BC: 0x2019, 0x02BD: 0x2018, 0x02B9: 0x2019, 0x2032: 0x2019}
FALLBACK_FONT = ("Baloo2[wght].ttf", 700)

# Sizes are for a 1080x1920 frame and scale with the output height.
STYLES = {
    "title": dict(font="LilitaOne-Regular.ttf", weight=None, size=168, line=1.0, tracking=3,
                  fill=("#FFE45C", "#FF9A1F"), stroke=9, stroke_color="#3B1D0A",
                  shadow=(0, 12, 10, 0.55), glow=(28, "#FFC24A", 0.35), y=0.30,
                  anim="pop_letters", fade_in=0.45, fade_out=0.5, stagger=0.055, sparkle=True,
                  shine=True, upper=False),
    "subtitle": dict(font="Baloo2[wght].ttf", weight=700, size=60, line=1.15, tracking=4,
                     fill="#FFFFFF", stroke=0, stroke_color="#000000", shadow=(0, 4, 7, 0.65),
                     glow=None, y=None, anim="rise", fade_in=0.6, fade_out=0.5, scrim=0.28),
    "label": dict(font="Baloo2[wght].ttf", weight=700, size=56, line=1.1, tracking=1,
                  fill="#FFFFFF", stroke=0, stroke_color="#000000", shadow=(0, 3, 5, 0.45),
                  glow=None, y=0.735, anim="slide", fade_in=0.35, fade_out=0.3,
                  pill=("#1B140D", 0.62, "#FFB020")),
    "credit": dict(font="Montserrat[wght].ttf", weight=600, size=46, line=1.35, tracking=1,
                   fill="#FFFFFF", stroke=0, stroke_color="#000000", shadow=(0, 3, 8, 0.7),
                   glow=None, y=0.50, anim="rise", fade_in=0.7, fade_out=0.7, scrim=0.42),
}

_font_cache = {}
_cmap_cache = {}


def _cmap(path):
    if path not in _cmap_cache:
        from fontTools.ttLib import TTFont
        _cmap_cache[path] = set(TTFont(path, lazy=True).getBestCmap().keys())
    return _cmap_cache[path]


def get_font(name, size, weight=None):
    path = name if os.path.isabs(name) else os.path.join(FONT_DIR, name)
    k = (path, int(size), weight)
    if k in _font_cache:
        return _font_cache[k]
    f = ImageFont.truetype(path, int(size), layout_engine=ImageFont.Layout.BASIC)
    if weight is not None:
        try:
            axes = f.get_variation_axes()
            vals = []
            for a in axes:
                nm = a.get("name", b"")
                nm = nm.decode() if isinstance(nm, bytes) else str(nm)
                if nm.lower().startswith("weight") or nm.lower() == "wght":
                    vals.append(max(a["minimum"], min(a["maximum"], weight)))
                else:
                    vals.append(a.get("default", a["minimum"]))
            f.set_variation_by_axes(vals)
        except Exception:
            pass
    f._path = path
    _font_cache[k] = f
    return f


def _hex(c, a=255):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


def text_runs(text, font, fb_font):
    """Split text into (font, string) runs with okina substitution / per-glyph fallback."""
    cm = _cmap(font._path)
    fcm = _cmap(fb_font._path)
    runs = []
    for ch in text:
        o = ord(ch)
        f = font
        if o not in cm and not ch.isspace():
            if o in SUBST and SUBST[o] in cm:
                ch = chr(SUBST[o])
            elif o in fcm:
                f = fb_font
        if runs and runs[-1][0] is f:
            runs[-1][1] += ch
        else:
            runs.append([f, ch])
    return runs


def _run_len(runs, tracking):
    return sum(f.getlength(s) + tracking * len(s) for f, s in runs)


def _glyph_positions(runs, tracking):
    """x offset of every character (kerning preserved inside each run)."""
    out = []
    x = 0.0
    for f, s in runs:
        for i, ch in enumerate(s):
            out.append((f, ch, x + f.getlength(s[:i]) + tracking * i))
        x += f.getlength(s) + tracking * len(s)
    return out, x


class _Sprite:
    """Premultiplied float32 RGBA image + anchor (rest position of its anchor on the frame)."""

    def __init__(self, rgba_pm, ax, ay):
        self.img = rgba_pm
        self.ax, self.ay = ax, ay


def _premul(img_rgba_u8):
    a = img_rgba_u8.astype(np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    return a


def _over(dst, src):
    return src + dst * (1.0 - src[..., 3:4])


def _layer(mask, color, alpha=1.0):
    """mask float (h,w) 0..1 -> premultiplied layer of a solid colour."""
    r, g, b, _ = _hex(color) if isinstance(color, str) else color
    out = np.empty(mask.shape + (4,), np.float32)
    a = mask * alpha
    out[..., 0] = a * (r / 255)
    out[..., 1] = a * (g / 255)
    out[..., 2] = a * (b / 255)
    out[..., 3] = a
    return out


def _grad_layer(mask, c_top, c_bot, y0, y1):
    h, w = mask.shape
    t = np.clip((np.arange(h, dtype=np.float32) - y0) / max(1.0, (y1 - y0)), 0, 1)[:, None]
    ct, cb = np.array(_hex(c_top)[:3], np.float32) / 255, np.array(_hex(c_bot)[:3], np.float32) / 255
    col = ct[None, None, :] * (1 - t[..., None]) + cb[None, None, :] * t[..., None]
    out = np.empty((h, w, 4), np.float32)
    out[..., :3] = col * mask[..., None]
    out[..., 3] = mask
    return out


def _blur(mask, r):
    if r <= 0:
        return mask
    im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def _shift(mask, dx, dy):
    out = np.zeros_like(mask)
    h, w = mask.shape
    xs0, xd0 = (0, dx) if dx >= 0 else (-dx, 0)
    ys0, yd0 = (0, dy) if dy >= 0 else (-dy, 0)
    ww, hh = w - abs(dx), h - abs(dy)
    if ww > 0 and hh > 0:
        out[yd0:yd0 + hh, xd0:xd0 + ww] = mask[ys0:ys0 + hh, xs0:xs0 + ww]
    return out


class TextItem:
    def __init__(self, spec, W, H, fps, idx):
        self.spec = spec
        st = dict(STYLES[spec["style"]])
        for k in ("font", "weight", "size", "fill", "stroke", "stroke_color", "y", "x", "anim", "fade_in",
                  "fade_out", "sparkle", "shine", "tracking", "line", "upper", "shadow", "glow", "scrim"):
            if k in spec:
                st[k] = spec[k]
        self.st = st
        self.W, self.H, self.fps = W, H, fps
        self.k = H / 1920.0
        self.f0 = int(round(spec["start"] * fps))
        self.f1 = int(round(spec["end"] * fps))
        self.idx = idx
        self.text = spec["text"].upper() if st.get("upper") else spec["text"]
        self.rng = np.random.default_rng(1234 + idx)
        self.rest_cache = None
        self._build()

    # ---------------------------------------------------------------- layout
    def _layout(self, size):
        st = self.st
        font = get_font(st["font"], size, st.get("weight"))
        fb = get_font(FALLBACK_FONT[0], size, FALLBACK_FONT[1])
        trk = st.get("tracking", 0) * self.k
        maxw = self.W * (1 - 2 * SAFE["side"]) - 2 * st.get("stroke", 0) * self.k - (60 * self.k if st.get("pill") else 0)
        lines = []
        for para in self.text.split("\n"):
            words = para.split(" ")
            cur = ""
            for w in words:
                cand = (cur + " " + w) if cur else w
                if cur and _run_len(text_runs(cand, font, fb), trk) > maxw:
                    lines.append(cur)
                    cur = w
                else:
                    cur = cand
            lines.append(cur)
        widths = [_run_len(text_runs(l, font, fb), trk) for l in lines]
        return font, fb, trk, lines, widths, maxw

    def _build(self):
        st, k = self.st, self.k
        size = st["size"] * k * float(self.spec.get("scale", 1.0))
        for _ in range(30):
            font, fb, trk, lines, widths, maxw = self._layout(size)
            if max(widths) <= maxw + 0.5:
                break
            size *= 0.94
        self.size = size
        asc, desc = font.getmetrics()
        lh = size * st.get("line", 1.1)
        stroke = int(round(st.get("stroke", 0) * k))
        sh = st.get("shadow") or (0, 0, 0, 0)
        glow = st.get("glow")
        pad = int(stroke + abs(sh[0] * k) + abs(sh[1] * k) + sh[2] * k * 3 + (glow[0] * k * 2.5 if glow else 0) + 8)
        if st.get("scrim"):
            pad = max(pad, int(70 * k))
        pill = st.get("pill")
        ppx, ppy = (int(30 * k), int(14 * k)) if pill else (0, 0)
        tw = int(math.ceil(max(widths)))
        th = int(math.ceil(lh * (len(lines) - 1) + asc + desc))
        cw, ch = tw + 2 * (pad + ppx), th + 2 * (pad + ppy)
        ox, oy = pad + ppx, pad + ppy  # text block origin in sprite
        # per-glyph placement (baseline 'ls' anchors)
        glyphs = []
        for li, (line, wdt) in enumerate(zip(lines, widths)):
            runs = text_runs(line, font, fb)
            pos, _ = _glyph_positions(runs, trk)
            x0 = ox + (tw - wdt) / 2
            base = oy + asc + li * lh
            for f, chh, gx in pos:
                glyphs.append((f, chh, x0 + gx, base, li))
        self.glyphs = glyphs
        self.canvas = (cw, ch)
        self.block = (ox, oy, tw, th)
        self.lines = lines
        # rest position (sprite centre on the frame), clamped to the safe zone; integer for crispness
        y = st.get("y")
        if y is None:  # subtitle: just under the title if one exists, else 0.40
            y = self.spec.get("_auto_y", 0.40)
        x = st.get("x", 0.5)
        cx, cy = x * self.W, y * self.H
        hw, hh = tw / 2 + ppx, th / 2 + ppy
        lo_y, hi_y = SAFE["top"] * self.H + hh, (1 - SAFE["bottom"]) * self.H - hh
        lo_x, hi_x = SAFE["side"] * self.W + hw, (1 - SAFE["side"]) * self.W - hw
        if not (lo_y <= cy <= hi_y) or not (lo_x <= cx <= hi_x):
            ny = min(max(cy, lo_y), hi_y)
            nx = min(max(cx, lo_x), hi_x)
            log(f"text {self.text!r}: moved into safe zone ({cx:.0f},{cy:.0f}) -> ({nx:.0f},{ny:.0f})")
            cx, cy = nx, ny
        self.ax, self.ay = cw / 2.0, ch / 2.0
        self.px = round(cx - self.ax) + self.ax
        self.py = round(cy - self.ay) + self.ay
        self.bbox_rest = (self.px - hw, self.py - hh, self.px + hw, self.py + hh)
        if st.get("anim") == "pop_letters":
            self._build_letters(font, stroke, sh, glow, pad)
        self.full = self._render_layers(glyphs, stroke, sh, glow, pill, ppx, ppy)

    def _masks(self, glyphs, stroke):
        cw, ch = self.canvas
        fill = Image.new("L", (cw, ch), 0)
        strk = Image.new("L", (cw, ch), 0)
        df, ds = ImageDraw.Draw(fill), ImageDraw.Draw(strk)
        for f, chh, gx, base, li in glyphs:
            df.text((gx, base), chh, font=f, fill=255, anchor="ls")
            if stroke:
                ds.text((gx, base), chh, font=f, fill=255, anchor="ls", stroke_width=stroke, stroke_fill=255)
        fm = np.asarray(fill, np.float32) / 255
        sm = np.asarray(strk, np.float32) / 255 if stroke else fm
        return fm, sm

    def _render_layers(self, glyphs, stroke, sh, glow, pill=None, ppx=0, ppy=0, parts=False):
        st, k = self.st, self.k
        cw, ch = self.canvas
        fm, sm = self._masks(glyphs, stroke)
        under = np.zeros((ch, cw, 4), np.float32)
        if pill:
            ox, oy, tw, th = self.block
            pm = Image.new("L", (cw, ch), 0)
            r = int((th + 2 * ppy) / 2)
            ImageDraw.Draw(pm).rounded_rectangle([ox - ppx, oy - ppy, ox + tw + ppx, oy + th + ppy], radius=r, fill=255)
            pmask = np.asarray(pm, np.float32) / 255
            under = _over(under, _layer(_shift(_blur(pmask, 8 * k), 0, int(4 * k)), "#000000", 0.35))
            under = _over(under, _layer(pmask, pill[0], pill[1]))
            # small accent bar on the left
            am = Image.new("L", (cw, ch), 0)
            ImageDraw.Draw(am).rounded_rectangle([ox - ppx + int(12 * k), oy, ox - ppx + int(18 * k), oy + th],
                                                 radius=int(3 * k), fill=255)
            under = _over(under, _layer(np.asarray(am, np.float32) / 255, pill[2], 1.0))
        if st.get("scrim") and not parts:
            ox, oy, tw, th = self.block
            sc_m = Image.new("L", (cw, ch), 0)
            ImageDraw.Draw(sc_m).rounded_rectangle([ox - 24 * k, oy - 10 * k, ox + tw + 24 * k, oy + th + 14 * k],
                                                   radius=int(30 * k), fill=255)
            under = _over(under, _layer(_blur(np.asarray(sc_m, np.float32) / 255, 26 * k), "#000000", float(st["scrim"])))
        if sh and sh[3] > 0:
            smask = _shift(_blur(sm, sh[2] * k), int(round(sh[0] * k)), int(round(sh[1] * k)))
            under = _over(under, _layer(smask, "#000000", sh[3]))
        if glow:
            under = _over(under, _layer(_blur(sm, glow[0] * k), glow[1], glow[2]))
        face = np.zeros((ch, cw, 4), np.float32)
        if stroke:
            face = _over(face, _layer(sm, st.get("stroke_color", "#000000")))
        fill = st["fill"]
        if isinstance(fill, (list, tuple)):
            # gradient per line: from cap-top to baseline
            ox, oy, tw, th = self.block
            asc = get_font(st["font"], self.size, st.get("weight")).getmetrics()[0]
            lh = self.size * st.get("line", 1.1)
            lay = np.zeros_like(face)
            for li in range(len(self.lines)):
                base = oy + asc + li * lh
                y0, y1 = base - asc * 0.78, base
                band = np.zeros_like(fm)
                r0, r1 = int(max(0, y0 - asc * 0.4)), int(min(ch, base + asc * 0.5))
                band[r0:r1] = fm[r0:r1]
                lay = lay + _grad_layer(band, fill[0], fill[1], y0, y1)
            face = _over(face, lay)
        else:
            face = _over(face, _layer(fm, fill))
        if parts:
            return under, face, fm
        self.face_mask = fm
        return _over(under, face)

    def _build_letters(self, font, stroke, sh, glow, pad):
        """Each glyph as its own (under, face) sprite pair for the staggered pop-in."""
        self.letters = []
        visible = [g for g in self.glyphs if not g[1].isspace()]
        for i, g in enumerate(visible):
            under, face, fm = self._render_layers([g], stroke, sh, glow, parts=True)
            ys, xs = np.nonzero(under[..., 3] + face[..., 3] > 0.002)
            if len(xs) == 0:
                continue
            x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
            # pivot: bottom-centre of the glyph (letters "pop up" from the baseline)
            f, chh, gx, base, li = g
            gw = f.getlength(chh)
            pivx, pivy = gx + gw / 2, base
            self.letters.append(dict(under=under[y0:y1, x0:x1].copy(), face=face[y0:y1, x0:x1].copy(),
                                     off=(x0, y0), piv=(pivx, pivy), order=i))
        self.n_letters = len(self.letters)

    # ---------------------------------------------------------------- animation
    def active(self, f):
        return self.f0 <= f < self.f1

    def _env(self, f):
        st = self.st
        t = (f - self.f0) / self.fps
        T = (self.f1 - self.f0) / self.fps
        fi, fo = max(1e-3, st["fade_in"]), max(1e-3, st["fade_out"])
        a_in = min(1.0, t / fi)
        a_out = min(1.0, max(0.0, (T - t) / fo))
        return t, T, a_in, a_out


def _smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _back_out(x, s=1.9):
    x = min(1.0, max(0.0, x)) - 1
    return 1 + x * x * ((s + 1) * x + s)


def _ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def _composite(frame, sprite, ax, ay, px, py, scale, alpha, cv2, extra=None):
    """Place premultiplied sprite so that its point (ax,ay) lands on frame point (px,py)."""
    if alpha <= 0.002:
        return
    H, W = frame.shape[:2]
    sh, sw = sprite.shape[:2]
    x0 = int(math.floor(px - ax * scale)) - 1
    y0 = int(math.floor(py - ay * scale)) - 1
    x1 = int(math.ceil(px + (sw - ax) * scale)) + 1
    y1 = int(math.ceil(py + (sh - ay) * scale)) + 1
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    inv = 1.0 / scale
    # inverse map (OpenCV pixel-centre convention)
    M = np.array([[inv, 0, (cx0 + 0.5 - px) * inv + ax - 0.5],
                  [0, inv, (cy0 + 0.5 - py) * inv + ay - 0.5]], np.float64)
    if abs(scale - 1) < 1e-9 and abs(M[0, 2] - round(M[0, 2])) < 1e-6 and abs(M[1, 2] - round(M[1, 2])) < 1e-6:
        ix, iy = int(round(M[0, 2])), int(round(M[1, 2]))
        reg = np.zeros((cy1 - cy0, cx1 - cx0, 4), np.float32)
        sx0, sy0 = max(0, ix), max(0, iy)
        sx1, sy1 = min(sw, ix + cx1 - cx0), min(sh, iy + cy1 - cy0)
        if sx1 > sx0 and sy1 > sy0:
            reg[sy0 - iy:sy1 - iy, sx0 - ix:sx1 - ix] = sprite[sy0:sy1, sx0:sx1]
    else:
        reg = cv2.warpAffine(sprite, M, (cx1 - cx0, cy1 - cy0), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    if extra is not None:
        reg = extra(reg, cx0, cy0)
    a = reg[..., 3:4] * alpha
    if float(a.max()) <= 0.001:
        return
    dst = frame[cy0:cy1, cx0:cx1].astype(np.float32)
    dst = dst * (1.0 - a) + reg[..., :3] * (255.0 * alpha)
    frame[cy0:cy1, cx0:cx1] = np.clip(dst + 0.5, 0, 255).astype(np.uint8)


def _star_sprite(r):
    """4-point twinkle with a soft core (premultiplied, warm white)."""
    s = int(math.ceil(r * 2.4)) * 2 + 1
    c = s // 2
    y, x = np.mgrid[0:s, 0:s].astype(np.float32) - c
    d = np.hypot(x, y) + 1e-6
    core = np.exp(-(d / (r * 0.22)) ** 2)
    rays = np.exp(-(np.abs(x) / (r * 0.06 + 0.35)) ** 2) * np.exp(-(np.abs(y) / r) ** 2) + \
        np.exp(-(np.abs(y) / (r * 0.06 + 0.35)) ** 2) * np.exp(-(np.abs(x) / r) ** 2)
    halo = 0.35 * np.exp(-(d / (r * 0.6)) ** 2)
    a = np.clip(core + 0.8 * rays + halo, 0, 1)
    img = np.zeros((s, s, 4), np.float32)
    col = np.array([1.0, 0.95, 0.80], np.float32)
    img[..., :3] = a[..., None] * col
    img[..., 3] = a
    return img, c, c


class TextRenderer:
    def __init__(self, texts, W, H, fps):
        import cv2
        self.cv2 = cv2
        self.W, self.H, self.fps = W, H, fps
        # subtitle auto-placement under the title that overlaps it in time
        titles = [t for t in texts if t["style"] == "title"]
        self.items = []
        for i, t in enumerate(texts):
            spec = dict(t)
            if spec["style"] == "subtitle" and "y" not in spec:
                over = [x for x in self.items if x.spec["style"] == "title" and
                        x.spec["start"] < spec["end"] and spec["start"] < x.spec["end"]]
                if over:
                    b = over[0].bbox_rest
                    spec["_auto_y"] = (b[3] + 70 * H / 1920) / H
            self.items.append(TextItem(spec, W, H, fps, i))
        self.stars = {r: _star_sprite(r) for r in (6, 9, 12, 16)}
        for it in self.items:
            if it.st.get("sparkle"):
                it.particles = self._particles(it)

    def _particles(self, it):
        rng = it.rng
        x0, y0, x1, y1 = it.bbox_rest
        T = (it.f1 - it.f0) / self.fps
        n = int(10 + 7 * T)
        ps = []
        for _ in range(n):
            ps.append(dict(x=rng.uniform(x0 - 30, x1 + 30), y=rng.uniform(y0 - 50, y1 + 40),
                           t0=rng.uniform(0.15, max(0.3, T - 0.5)), life=rng.uniform(0.6, 1.3),
                           r=float(rng.choice([6, 9, 9, 12, 12, 16])) * it.k,
                           vy=-rng.uniform(8, 26) * it.k, vx=rng.uniform(-6, 6) * it.k,
                           tw=rng.uniform(5, 9), ph=rng.uniform(0, 6.28)))
        return ps

    def apply(self, frame, f):
        for it in self.items:
            if it.active(f):
                self._apply_one(frame, it, f)
        return frame

    def _apply_one(self, frame, it, f):
        cv2 = self.cv2
        st = it.st
        t, T, a_in, a_out = it._env(f)
        anim = st.get("anim", "rise")
        k = it.k
        if anim == "pop_letters" and getattr(it, "letters", None):
            stg = st.get("stagger", 0.05)
            dur = 0.42
            intro = stg * max(0, it.n_letters - 1) + dur
            if t < intro:
                for layer in ("under", "face"):
                    for L in it.letters:
                        lt = (t - L["order"] * stg) / dur
                        if lt <= 0:
                            continue
                        sc = 0.25 + 0.75 * _back_out(lt)
                        al = _smooth(lt * 1.8)
                        dy = (1 - _ease_out(lt)) * 26 * k
                        ox, oy = L["off"]
                        pivx, pivy = L["piv"]
                        _composite(frame, L[layer], pivx - ox, pivy - oy, it.px - it.ax + pivx,
                                   it.py - it.ay + pivy + dy, sc, al * a_out, cv2)
            else:
                self._rest(frame, it, t, intro, a_out, f)
        else:
            e_in = _ease_out(a_in)
            sc = 1.0
            dx = dy = 0.0
            if anim == "rise":
                dy = (1 - e_in) * 26 * k
                sc = 0.97 + 0.03 * e_in
            elif anim == "slide":
                dx = -(1 - e_in) * 40 * k
            elif anim == "pop":
                sc = 0.6 + 0.4 * _back_out(a_in)
            if a_out < 1:
                dy -= (1 - a_out) * 14 * k
            alpha = _smooth(a_in) * _smooth(a_out)
            _composite(frame, it.full, it.ax, it.ay, it.px + dx, it.py + dy, sc, alpha, cv2)
        if st.get("sparkle"):
            self._sparkles(frame, it, t, T, a_out)

    def _rest(self, frame, it, t, intro, a_out, f):
        st = it.st
        extra = None
        if st.get("shine"):
            # one diagonal light sweep across the letters right after the pop-in
            sweep_t = (t - intro - 0.1) / 0.9
            if 0 <= sweep_t <= 1:
                fm = it.face_mask
                cw = fm.shape[1]
                pos = -0.2 * cw + sweep_t * 1.4 * cw
                width = 0.09 * cw

                def extra(reg, cx0, cy0, fm=fm, pos=pos, width=width, it=it):
                    h, w = reg.shape[:2]
                    sx0 = int(round(cx0 - (it.px - it.ax)))
                    sy0 = int(round(cy0 - (it.py - it.ay)))
                    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
                    xx += sx0
                    yy += sy0
                    band = np.exp(-((xx + 0.35 * yy - pos) / width) ** 2)
                    m = np.zeros((h, w), np.float32)
                    ys0, xs0 = max(0, sy0), max(0, sx0)
                    ys1, xs1 = min(fm.shape[0], sy0 + h), min(fm.shape[1], sx0 + w)
                    if ys1 > ys0 and xs1 > xs0:
                        m[ys0 - sy0:ys1 - sy0, xs0 - sx0:xs1 - sx0] = fm[ys0:ys1, xs0:xs1]
                    add = (0.55 * band * m)[..., None]
                    reg = reg.copy()
                    reg[..., :3] = reg[..., :3] + add * (1 - reg[..., :3])
                    return reg
        sc = 1.0
        dy = 0.0
        if a_out < 1:
            sc = 1.0 + (1 - a_out) * 0.06
            dy = -(1 - a_out) * 10 * it.k
        _composite(frame, it.full, it.ax, it.ay, it.px, it.py + dy, sc, _smooth(a_out), self.cv2, extra)

    def _sparkles(self, frame, it, t, T, a_out):
        cv2 = self.cv2
        H, W = frame.shape[:2]
        for p in it.particles:
            lt = (t - p["t0"]) / p["life"]
            if not (0 <= lt <= 1):
                continue
            env = math.sin(math.pi * lt) ** 1.5
            tw = 0.65 + 0.35 * math.sin(p["tw"] * t + p["ph"])
            inten = env * tw * a_out * 0.9
            if inten < 0.02:
                continue
            r = min(self.stars, key=lambda rr: abs(rr * it.k - p["r"]))
            spr, sax, say = self.stars[r]
            age = t - p["t0"]
            x = p["x"] + p["vx"] * age
            y = p["y"] + p["vy"] * age
            sc = (0.6 + 0.4 * env) * it.k
            _screen(frame, spr, sax, say, x, y, sc, inten, cv2)


def _screen(frame, sprite, ax, ay, px, py, scale, inten, cv2):
    H, W = frame.shape[:2]
    sh, sw = sprite.shape[:2]
    x0 = int(math.floor(px - ax * scale)) - 1
    y0 = int(math.floor(py - ay * scale)) - 1
    x1 = int(math.ceil(px + (sw - ax) * scale)) + 1
    y1 = int(math.ceil(py + (sh - ay) * scale)) + 1
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    inv = 1.0 / scale
    M = np.array([[inv, 0, (cx0 + 0.5 - px) * inv + ax - 0.5],
                  [0, inv, (cy0 + 0.5 - py) * inv + ay - 0.5]], np.float64)
    reg = cv2.warpAffine(sprite, M, (cx1 - cx0, cy1 - cy0), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    dst = frame[cy0:cy1, cx0:cx1].astype(np.float32) / 255.0
    add = np.clip(reg[..., :3] * inten, 0, 1)
    dst = 1 - (1 - dst) * (1 - add)
    frame[cy0:cy1, cx0:cx1] = np.clip(dst * 255 + 0.5, 0, 255).astype(np.uint8)

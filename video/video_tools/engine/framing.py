"""Per-frame geometry: crop / box / fit windows with easing or keyframe tracks, tilt correction,
optional stabilisation, speed-ramp time maps, and the affine matrices used by cv2.warpAffine
(one resample per output frame, sub-pixel exact).

Coordinate convention: "continuous" pixel coordinates, pixel i covers [i, i+1) and its centre is at
i+0.5.  M_k maps output continuous coords -> upright source continuous coords.
"""
import math

import numpy as np


def ease(u, kind):
    u = np.clip(u, 0.0, 1.0)
    if kind == "linear":
        return u
    if kind == "in":
        return 1 - np.cos(u * np.pi / 2)
    if kind == "out":
        return np.sin(u * np.pi / 2)
    return 0.5 - 0.5 * np.cos(np.pi * u)  # inout


def base_window(W, H, aspect):
    """Largest window of the given aspect (w/h) that fits the source."""
    if W / H > aspect:
        return H * aspect, float(H)
    return float(W), W / aspect


def hermite_keys(ts, vs, t, smooth=True):
    """Monotone C1 cubic Hermite through keys (Fritsch-Carlson tangents): zero velocity at the
    first/last key (ease in/out) and at local extrema (no overshoot), continuous velocity through
    intermediate keys of a monotone run, values held outside the key range.
    smooth=False -> piecewise linear."""
    ts = np.asarray(ts, float)
    vs = np.asarray(vs, float)
    t = np.asarray(t, float)
    if len(ts) == 1:
        return np.full_like(t, vs[0])
    if not smooth:
        return np.interp(t, ts, vs)
    h = np.diff(ts)
    d = np.diff(vs) / h
    m = np.zeros(len(ts))
    for i in range(1, len(ts) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    tc = np.clip(t, ts[0], ts[-1])
    i = np.clip(np.searchsorted(ts, tc, side="right") - 1, 0, len(ts) - 2)
    hh = h[i]
    u = (tc - ts[i]) / hh
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1
    h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2
    h11 = u ** 3 - u ** 2
    return h00 * vs[i] + h10 * hh * m[i] + h01 * vs[i + 1] + h11 * hh * m[i + 1]


def frame_curves(fr, n, times=None):
    """Per-frame window centre (normalised) and zoom.  With frame.keys, `times` are the SOURCE
    times of each output frame (photos: seconds from item start)."""
    keys = fr.get("keys")
    if keys:
        keys = sorted(keys, key=lambda k: float(k["t"]))
        ts = [float(k["t"]) for k in keys]
        smooth = fr.get("ease", "inout") != "linear"
        out = []
        for name, dflt in (("cx", fr.get("cx0", 0.5)), ("cy", fr.get("cy0", 0.5)), ("zoom", fr.get("zoom0", 1.0))):
            vals, last = [], dflt
            for k in keys:
                last = float(k.get(name, last))
                vals.append(last)
            if name == "zoom":
                vals = np.log(np.maximum(1e-3, vals))  # zoom interpolated geometrically
            out.append(hermite_keys(ts, vals, times, smooth))
        return out[0], out[1], np.exp(out[2])
    u = np.arange(n) / max(1, n - 1)
    e = ease(u, fr.get("ease", "inout"))
    cx = fr["cx0"] + (fr["cx1"] - fr["cx0"]) * e
    cy = fr["cy0"] + (fr["cy1"] - fr["cy0"]) * e
    z0, z1 = max(1e-3, fr["zoom0"]), max(1e-3, fr["zoom1"])
    zoom = z0 * (z1 / z0) ** e  # geometric interpolation = constant perceived zoom speed
    return cx, cy, zoom


def _mat(s, tx, ty):
    return np.array([[s, 0, tx], [0, s, ty], [0, 0, 1.0]])


class Layout:
    """Where the source window lands on the output frame.
    crop: window aspect = output aspect, box = whole frame.
    box : window aspect = frame.aspect; box = full width (minus box_margin), height = width/aspect,
          vertical centre at box_y (alias box_cy); blurred fill of the same frame behind it.
    fit : box with aspect = source aspect (whole picture visible)."""

    def __init__(self, W, H, OW, OH, fr):
        mode = fr["mode"]
        self.mode = mode
        k = OH / 1920.0
        if mode == "crop":
            self.aspect = OW / OH
            self.box = (0.0, 0.0, float(OW), float(OH))
        else:
            a = (W / H) if mode == "fit" else float(fr.get("aspect", 0.8))
            m = float(fr.get("box_margin", 0)) * k
            a = max(a, (OW - 2 * m) / OH)
            self.aspect = a
            bw = OW - 2 * m
            bh = bw / a
            cy = float(fr.get("box_y", fr.get("box_cy", 0.5))) * OH
            cy = min(max(cy, bh / 2), OH - bh / 2)
            self.box = (OW / 2 - bw / 2, cy - bh / 2, OW / 2 + bw / 2, cy + bh / 2)
        self.radius = float(fr.get("radius", 0 if mode == "crop" else 24)) * k
        self.shadow = float(fr.get("shadow", 0.45))
        bx0, by0, bx1, by1 = self.box
        # integer region the foreground warp has to cover
        self.region = (int(math.floor(bx0 + 1e-6)), int(math.floor(by0 + 1e-6)),
                       int(math.ceil(bx1 - 1e-6)), int(math.ceil(by1 - 1e-6)))

    def corners(self):
        bx0, by0, bx1, by1 = self.box
        return np.array([[bx0, by0, 1], [bx1, by0, 1], [bx0, by1, 1], [bx1, by1, 1]], float).T


def inside_violation(M, lay, W, H, tol=0.25):
    P = (M @ lay.corners())[:2]
    return (P[0].min() < -tol) or (P[1].min() < -tol) or (P[0].max() > W + tol) or (P[1].max() > H + tol)


def _projector(W, H, lay, pre, pull):
    """proj(k, X, Y, ww, wh) -> nearest valid window centre for frame k (straightened coords):
    axis clamp inside the source, then (tilt) slide towards the frame centre until no empty
    corner is visible."""
    bx0, by0, bx1, by1 = lay.box
    bw, bcx, bcy = bx1 - bx0, (bx0 + bx1) / 2, (by0 + by1) / 2

    def proj(k, X, Y, ww, wh):
        X = min(max(X, ww / 2), W - ww / 2)
        Y = min(max(Y, wh / 2), H - wh / 2)
        if pre is None or not pull:
            return X, Y
        S = pre[k]
        s = ww / bw

        def bad(x, y):
            return inside_violation(S @ _mat(s, x - s * bcx, y - s * bcy), lay, W, H)
        if not bad(X, Y):
            return X, Y
        c0 = (np.linalg.inv(S) @ np.array([W / 2, H / 2, 1.0]))[:2]
        p1 = np.array([X, Y])
        lo, hi = 0.0, 1.0
        if not bad(*c0):
            for _ in range(18):
                mid = (lo + hi) / 2
                q = c0 + mid * (p1 - c0)
                if bad(*q):
                    hi = mid
                else:
                    lo = mid
        q = c0 + lo * (p1 - c0)
        return float(q[0]), float(q[1])
    return proj


def _project_keys(fr, W, H, lay, n, times, extra_zoom, proj):
    """Move every key (or cx0/cx1 endpoint) into its valid region BEFORE interpolation, so the
    interpolated path is not bent by a hard clamp (zoom < 1 -> 1, centre inside the source)."""
    fr = dict(fr)
    base_w, base_h = base_window(W, H, lay.aspect)
    times = np.asarray(times, float)
    moved = 0

    def fix(cx, cy, z, k):
        nonlocal moved
        z1 = max(1.0, z)
        zz = z1 * extra_zoom
        X, Y = proj(k, cx * W, cy * H, base_w / zz, base_h / zz)
        if abs(X - cx * W) > 0.5 or abs(Y - cy * H) > 0.5 or z1 != z:
            moved += 1
        return X / W, Y / H, z1
    if fr.get("keys"):
        keys = []
        last = {"cx": fr.get("cx0", 0.5), "cy": fr.get("cy0", 0.5), "zoom": fr.get("zoom0", 1.0)}
        for key in sorted(fr["keys"], key=lambda q: float(q["t"])):
            v = {nm: float(key.get(nm, last[nm])) for nm in ("cx", "cy", "zoom")}
            last = v
            k = int(np.argmin(np.abs(times - float(key["t"])))) if len(times) else 0
            cx, cy, z = fix(v["cx"], v["cy"], v["zoom"], k)
            keys.append({"t": float(key["t"]), "cx": cx, "cy": cy, "zoom": z})
        fr["keys"] = keys
    else:
        fr["cx0"], fr["cy0"], fr["zoom0"] = fix(fr["cx0"], fr["cy0"], fr["zoom0"], 0)
        fr["cx1"], fr["cy1"], fr["zoom1"] = fix(fr["cx1"], fr["cy1"], fr["zoom1"], max(0, n - 1))
    return fr, moved


def window_matrices(W, H, lay, fr, n, times, extra_zoom=1.0, pre=None, pull=False, fps=30.0):
    """3x3 matrices output-frame -> source for the box region, plus window centres (source px).
    pre[k] (optional) maps straightened/stabilised coords -> source frame k (tilt, stabilisation).
    pull=True: windows that would show invalid area (the empty corners of a tilt) slide towards
    the frame centre.  Keys are projected into their valid region first; if a per-frame clamp
    still moves the path (> 0.05 px), the path is re-smoothed locally (clamp -> Gaussian 0.15 s
    -> clamp, iterated) so it stays inside the source with continuous velocity - no jolts."""
    warns = []
    proj = _projector(W, H, lay, pre, pull)
    fr2, moved = _project_keys(fr, W, H, lay, n, times, extra_zoom, proj)
    if moved:
        warns.append(f"{moved} key(s)/endpoint(s) moved into the valid region before interpolation")
    cx, cy, zoom = frame_curves(fr2, n, times)
    bx0, by0, bx1, by1 = lay.box
    bw, bcx, bcy = bx1 - bx0, (bx0 + bx1) / 2, (by0 + by1) / 2
    base_w, base_h = base_window(W, H, lay.aspect)
    z = np.maximum(1.0, zoom) * extra_zoom
    ww, wh = base_w / z, base_h / z
    P = np.stack([cx * W, cy * H], 1)

    def project(P):
        return np.array([proj(k, P[k, 0], P[k, 1], ww[k], wh[k]) for k in range(n)])
    C = project(P)
    dev = np.abs(C - P).max() if n else 0.0
    if dev > 0.05 and n > 2:
        # The clamp displacement D = project(P) - P has a kink where it switches on.  Accumulate a
        # *smooth* displacement instead: add the remaining residual, Gaussian-smooth (0.15 s),
        # repeat until project() no longer moves the path (residual < 0.01 px).
        sig = max(1.0, 0.15 * fps)
        Dacc = np.zeros_like(P)
        res = dev
        it = 0
        for it in range(1, 41):
            Q = P + Dacc
            R = project(Q) - Q
            res = np.abs(R).max()
            if res < 0.01:
                break
            Dacc = np.stack([_gauss_smooth(Dacc[:, i] + 1.5 * R[:, i], sig) for i in range(2)], 1)
        C = project(P + Dacc)
        warns.append(f"path touched the frame edge (max {dev:.1f} px): clamp replaced by a smooth push "
                     f"({it} iterations, final residual {res:.3f} px)")
    mats, centres = [], []
    for k in range(n):
        s = ww[k] / bw
        X, Y = C[k]
        M = _mat(s, X - s * bcx, Y - s * bcy)
        c = np.array([X, Y, 1.0])
        if pre is not None:
            M = pre[k] @ M
            c = pre[k] @ c
        mats.append(M)
        centres.append(c[:2])
    return mats, np.array(centres), warns


def tilt_matrix(W, H, deg):
    """straightened coords -> upright source coords, for a picture rotated by `deg` clockwise
    (y axis points down) about its centre."""
    t = math.radians(deg)
    c, s_ = math.cos(t), math.sin(t)
    R = np.array([[c, s_, 0], [-s_, c, 0], [0, 0, 1.0]])
    C = np.array([[1, 0, W / 2], [0, 1, H / 2], [0, 0, 1.0]])
    Ci = np.array([[1, 0, -W / 2], [0, 1, -H / 2], [0, 0, 1.0]])
    return C @ R @ Ci


def solve_zoom(W, H, lay, fr, n, times, pre, pull, max_zoom, fps=30.0):
    """Smallest constant extra zoom (>=1) so every frame's window is valid; None if > max_zoom."""
    def ok(z):
        mats, _, _ = window_matrices(W, H, lay, fr, n, times, z, pre, pull, fps)
        return not any(inside_violation(M, lay, W, H) for M in mats)
    if ok(1.0):
        return 1.0
    if not ok(max_zoom):
        return None
    lo, hi = 1.0, max_zoom
    for _ in range(18):
        mid = (lo + hi) / 2
        if ok(mid):
            hi = mid
        else:
            lo = mid
    return hi


def mat_scale(M):
    return math.sqrt(abs(np.linalg.det(M[:2, :2])))


# ----------------------------------------------------------------------------------------------
# speed ramps
# ----------------------------------------------------------------------------------------------

def _slowness(t_in, t_out, segs, ease_s):
    segs = sorted(segs, key=lambda q: float(q["in"]))
    ds = 0.0005
    s = np.arange(t_in, t_out + ds * 0.5, ds)
    u = np.full_like(s, 1.0 / float(segs[0]["speed"]))
    for a, b in zip(segs, segs[1:]):
        bnd = float(b["in"])
        u1, u2 = 1.0 / float(a["speed"]), 1.0 / float(b["speed"])
        w = ease_s * 2.0 / (u1 + u2)  # source-time width of the ramp ~ ease_s of output time
        w = min(w, 0.9 * (float(a["out"]) - float(a["in"])), 0.9 * (float(b["out"]) - float(b["in"])))
        x = np.clip((s - bnd) / max(w, 1e-6) + 0.5, 0, 1)
        u = u + (u2 - u1) * x * x * (3 - 2 * x)
    tau = np.concatenate([[0.0], np.cumsum((u[1:] + u[:-1]) * 0.5 * np.diff(s))])
    return s, u, tau


def time_map(t_in, t_out, segs, fps, ease_s=0.25):
    """Speed ramp: segs = [{in,out,speed}] contiguous over [t_in, t_out] (source seconds).
    Returns (source time of every output frame, frame count).  The slowness 1/speed is eased with
    a smoothstep around each boundary (~ease_s of output time) so speed is continuous - no
    stutter - and each boundary's source instant keeps its place."""
    s, u, tau = _slowness(t_in, t_out, segs, ease_s)
    n = max(1, int(round(tau[-1] * fps)))
    return np.interp(np.arange(n) / fps, tau, s), n


def time_map_audio(t_in, t_out, segs, sr, nsamp, ease_s=0.25):
    """Source time and instantaneous speed for every output audio sample."""
    s, u, tau = _slowness(t_in, t_out, segs, ease_s)
    tj = np.arange(nsamp) / sr
    return np.interp(tj, tau, s), 1.0 / np.interp(tj, tau, u)


# ----------------------------------------------------------------------------------------------
# Plan
# ----------------------------------------------------------------------------------------------

class Plan:
    """Everything needed to render an item: source crop rect (upright coords), prescale size,
    per-frame 2x3 inverse-map matrices (prescaled-pixel coords, OpenCV convention) for the box
    region, and (box/fit modes) the moving background windows."""

    def __init__(self, W, H, OW, OH, fr, n, times=None, stab=None, stab_opts=None, tilt_deg=0.0, fps=30.0):
        self.W, self.H, self.OW, self.OH, self.n = W, H, OW, OH, n
        self.mode = fr["mode"]
        self.fr = fr
        self.lay = lay = Layout(W, H, OW, OH, fr)
        if times is None:
            times = np.arange(n) / 30.0
        self.times = np.asarray(times, float)
        self.warnings = []
        extra = 1.0
        R = tilt_matrix(W, H, tilt_deg) if abs(tilt_deg) > 1e-6 else None
        pre = None
        pull = R is not None
        if stab is not None:
            extra, pre, w = fit_stabilisation(W, H, lay, fr, n, self.times, stab, stab_opts or {}, R)
            self.warnings += w
        elif R is not None:
            pre = [R] * n
            z = solve_zoom(W, H, lay, fr, n, self.times, pre, True, 4.0, fps)
            extra = z if z is not None else 4.0
            if extra > 1.0001:
                self.warnings.append(f"tilt {tilt_deg:+.1f} deg: zoom auto-raised x{extra:.3f} to hide the empty corners")
        self.extra_zoom = extra
        mats, centres, w = window_matrices(W, H, lay, fr, n, self.times, extra, pre, pull, fps)
        self.warnings += w
        self.mats = mats
        self.centres = centres
        scales = np.array([mat_scale(M) for M in mats])  # source px per output px
        # prescale so that the most zoomed-in frame is ~1:1 -> the warp never upsamples needlessly
        # and downsamples by at most zoom_max/zoom_min.
        p = min(1.0, 1.0 / scales.min())
        C = lay.corners()
        pts = [np.concatenate([(M @ C)[:2] for M in mats], axis=1)]
        self.bg = None
        if self.mode != "crop":
            # background: largest output-aspect window ("cover"), following the box window centre
            cw_, ch_ = base_window(W, H, OW / OH)
            bz = max(1.0, float(fr.get("bg_zoom", 1.0)))
            cw_, ch_ = cw_ / bz, ch_ / bz
            bgc = np.array([(min(max(X, cw_ / 2), W - cw_ / 2), min(max(Y, ch_ / 2), H - ch_ / 2))
                            for X, Y in centres])
            self.bg = dict(w=cw_, h=ch_, centres=bgc)
            pts.append(np.array([bgc[:, 0] - cw_ / 2, bgc[:, 1] - ch_ / 2]))
            pts.append(np.array([bgc[:, 0] + cw_ / 2, bgc[:, 1] + ch_ / 2]))
        pts = np.concatenate(pts, axis=1)
        x0, y0, x1, y1 = pts[0].min(), pts[1].min(), pts[0].max(), pts[1].max()
        margin = 6.0 / p
        x0 = max(0, int(math.floor((x0 - margin) / 2)) * 2)
        y0 = max(0, int(math.floor((y0 - margin) / 2)) * 2)
        x1 = min(W, int(math.ceil((x1 + margin) / 2)) * 2)
        y1 = min(H, int(math.ceil((y1 + margin) / 2)) * 2)
        self.crop = (x0, y0, x1 - x0, y1 - y0)
        cw, ch = x1 - x0, y1 - y0
        self.PW = max(2, int(round(cw * p)))
        self.PH = max(2, int(round(ch * p)))
        px, py = self.PW / cw, self.PH / ch
        self.P = P = np.array([[px, 0, -x0 * px], [0, py, -y0 * py], [0, 0, 1.0]])
        Tm = np.array([[1, 0, -0.5], [0, 1, -0.5], [0, 0, 1.0]])
        rx0, ry0, rx1, ry1 = lay.region
        Tp = np.array([[1, 0, 0.5 + rx0], [0, 1, 0.5 + ry0], [0, 0, 1.0]])
        self.region_size = (rx1 - rx0, ry1 - ry0)
        self.cv_mats = [(Tm @ P @ M @ Tp)[:2].astype(np.float64) for M in mats]
        self.down = scales * p  # warp downsample factor per frame (>1 = minification)
        self.prescale = p

    def blur_sigma(self, k):
        d = self.down[k]
        if d <= 1.25:
            return 0.0
        return 0.5 * math.sqrt(d * d - 1.0)

    def bg_matrix(self, k, sw, sh, q):
        """cv2 inverse-map matrix: small bg image (sw x sh) pixel -> prescaled frame shrunk by q."""
        X, Y = self.bg["centres"][k]
        s = self.bg["w"] / sw
        M = _mat(s, X - s * sw / 2, Y - s * sh / 2)
        Q = np.diag([1 / q, 1 / q, 1.0])
        Tm = np.array([[1, 0, -0.5], [0, 1, -0.5], [0, 0, 1.0]])
        Tp = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1.0]])
        return (Tm @ Q @ self.P @ M @ Tp)[:2]

    def describe(self):
        return (f"mode={self.mode} src={self.W}x{self.H} box={tuple(round(v, 1) for v in self.lay.box)} "
                f"crop={self.crop} prescale={self.prescale:.3f} -> {self.PW}x{self.PH}, warp down "
                f"{self.down.min():.2f}..{self.down.max():.2f}, extra_zoom={self.extra_zoom:.3f}")


# ----------------------------------------------------------------------------------------------
# Stabilisation (OpenCV): estimate inter-frame similarity transforms on a small grey copy,
# accumulate the camera path, smooth it with a Gaussian, and fold the correction into the single
# crop warp (so the picture is resampled exactly once).
# ----------------------------------------------------------------------------------------------

def estimate_motion(gray_frames, scale_to_src):
    """gray_frames: list of uint8 HxW. Returns list of 3x3 matrices T_k mapping frame k-1 coords
    -> frame k coords (in source pixel units, continuous coords), T_0 = I; plus per-pair stats."""
    import cv2
    Ts = [np.eye(3)]
    stats = []
    prev = gray_frames[0]
    h, w = prev.shape
    S = np.diag([scale_to_src, scale_to_src, 1.0])
    Si = np.diag([1 / scale_to_src, 1 / scale_to_src, 1.0])
    for k in range(1, len(gray_frames)):
        cur = gray_frames[k]
        T = np.eye(3)
        ninl = 0
        pts = cv2.goodFeaturesToTrack(prev, maxCorners=500, qualityLevel=0.01, minDistance=max(8, w // 80),
                                      blockSize=7)
        if pts is not None and len(pts) >= 12:
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, pts, None, winSize=(21, 21), maxLevel=3,
                                                  criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
            good = st.reshape(-1) == 1
            p0, p1 = pts.reshape(-1, 2)[good], nxt.reshape(-1, 2)[good]
            if len(p0) >= 10:
                A, inl = cv2.estimateAffinePartial2D(p0 + 0.5, p1 + 0.5, method=cv2.RANSAC,
                                                     ransacReprojThreshold=1.0, maxIters=3000, confidence=0.995)
                if A is not None:
                    ninl = int(inl.sum())
                    if ninl >= 8:
                        T = np.vstack([A, [0, 0, 1]])
        Ts.append(S @ T @ Si)
        stats.append(ninl)
        prev = cur
    return Ts, stats


def _params(A, c):
    a, b = A[0, 0], A[1, 0]
    s = math.hypot(a, b)
    th = math.atan2(b, a)
    t = (A @ np.array([c[0], c[1], 1.0]))[:2] - c
    return th, math.log(s), t[0], t[1]


def _from_params(th, ls, tx, ty, c):
    s = math.exp(ls)
    R = np.array([[s * math.cos(th), -s * math.sin(th)], [s * math.sin(th), s * math.cos(th)]])
    M = np.eye(3)
    M[:2, :2] = R
    M[:2, 2] = np.array(c) + np.array([tx, ty]) - R @ np.array(c)
    return M


def _gauss_smooth(x, sigma):
    if sigma <= 0 or len(x) < 3:
        return x.copy()
    r = int(math.ceil(3 * sigma))
    r_eff = min(r, len(x) - 1)
    # odd reflection keeps the local trend (pans continue straight) at the clip edges
    left = 2 * x[0] - x[1:r_eff + 1][::-1]
    right = 2 * x[-1] - x[-r_eff - 1:-1][::-1]
    if r_eff < r:  # very short clip: extend with the end values
        left = np.concatenate([np.full(r - r_eff, left[0]), left])
        right = np.concatenate([right, np.full(r - r_eff, right[-1])])
    xp = np.concatenate([left, x, right])
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(xp, k, mode="valid")


def _sg(x, win):
    from scipy.signal import savgol_filter
    win = min(win, len(x) if len(x) % 2 else len(x) - 1)
    if win < 5:
        return x.copy()
    return savgol_filter(x, win, 2, mode="interp")


def _soft_limit(D, b, fps):
    """Scale corrections down smoothly (gain envelope) where they exceed the budget - no kinks."""
    from scipy.ndimage import maximum_filter1d, gaussian_filter1d
    out = D.copy()
    for i in range(D.shape[1]):
        m = maximum_filter1d(np.abs(D[:, i]), size=int(fps * 0.5) + 1)
        m = gaussian_filter1d(m, fps * 0.15)
        out[:, i] = D[:, i] * np.minimum(1.0, b[i] / np.maximum(m, 1e-9))
    return out


def stab_corrections(Ts, W, H, fps, smooth_s=0.5, rotation=True, strength=1.0, budget=None):
    """Return per-frame 3x3 W_k mapping stabilised coords -> source frame k coords.
    Camera path = accumulated similarity transforms (rotation, log-scale, centre translation).
    Smoothing: Savitzky-Golay, quadratic, window = smooth_s - follows intentional pans *and their
    acceleration* without lag, removes the shake above ~1/smooth_s Hz.  budget = (rot_rad,
    log_scale, tx_px, ty_px): corrections are soft-limited to it with a smooth gain envelope."""
    c = (W / 2.0, H / 2.0)
    A = np.eye(3)
    P = []
    for T in Ts:
        A = T @ A
        P.append(_params(A, c))
    P = np.array(P)
    P[:, 0] = np.unwrap(P[:, 0])
    win = max(5, 2 * int(round(smooth_s * fps)) + 1)
    Ps = np.stack([_sg(P[:, i], win) for i in range(4)], 1)
    D = Ps - P
    if budget is not None:
        D = _soft_limit(D, np.asarray(budget, float), fps)
    if not rotation:
        D[:, 0] = 0
    Ps = P + D * strength
    out = []
    for k in range(len(Ts)):
        Ak = _from_params(*P[k], c)
        Ab = _from_params(*Ps[k], c)
        out.append(Ak @ np.linalg.inv(Ab))
    return out, P, Ps


def _stab_budget(W, H, lay, fr, n, times, max_zoom, R=None, max_shift=0.08, fps=30.0):
    """How far the window may be pushed around: the free room around the (unstabilised) window in
    the source on each axis plus the margin bought by zooming in up to max_zoom, but never more
    than max_shift x the window size (mild: remove shake, follow intentional pans)."""
    mats, _, _ = window_matrices(W, H, lay, fr, n, times, 1.0, [R] * n if R is not None else None, R is not None, fps)
    C = lay.corners()
    room_x, room_y, ww, wh = [], [], [], []
    for M in mats:
        P = (M @ C)[:2]
        room_x.append(min(P[0].min(), W - P[0].max()))
        room_y.append(min(P[1].min(), H - P[1].max()))
        ww.append(P[0].max() - P[0].min())
        wh.append(P[1].max() - P[1].min())
    zm = 1.0 - 1.0 / max_zoom
    bx = min(max(0.0, min(room_x)) + zm * min(ww) / 2, max_shift * min(ww))
    by = min(max(0.0, min(room_y)) + zm * min(wh) / 2, max_shift * min(wh))
    rot = min(math.radians(0.3), math.atan2(zm * min(wh) / 2, max(ww) / 2 + 1e-6) * 0.25)
    return (rot, math.log(1.02), 0.9 * bx, 0.9 * by)


def fit_stabilisation(W, H, lay, fr, n, times, raw, opts, R=None):
    """raw = dict(Ts=..., fps=...). Choose extra zoom (<= max_zoom) so the stabilised window never
    leaves the source; if even max_zoom is not enough, reduce correction strength uniformly.
    R: optional tilt (straightened -> upright) applied in front of the stabilised window."""
    warns = []
    max_zoom = float(opts.get("max_zoom", 1.15))
    smooth_s = float(opts.get("smooth", 0.5))
    rot = bool(opts.get("rotation", True))
    if R is not None:  # the tilt needs its own zoom on top of the stabilisation margin
        zt = solve_zoom(W, H, lay, fr, n, times, [R] * n, True, 4.0, raw["fps"]) or 1.0
        max_zoom *= zt

    budget = _stab_budget(W, H, lay, fr, n, times, max_zoom, R, float(opts.get("max_shift", 0.08)), raw["fps"])

    def pre_of(strength):
        Wk, _, _ = stab_corrections(raw["Ts"], W, H, raw["fps"], smooth_s, rot, strength, budget)
        return [w @ R for w in Wk] if R is not None else Wk

    pre = pre_of(1.0)
    z = solve_zoom(W, H, lay, fr, n, times, pre, R is not None, max_zoom, raw["fps"])
    if z is None:
        lo, hi = 0.0, 1.0
        best = (max_zoom, pre_of(0.0), 0.0)
        for _ in range(10):
            mid = (lo + hi) / 2
            pp = pre_of(mid)
            zz = solve_zoom(W, H, lay, fr, n, times, pp, R is not None, max_zoom, raw["fps"])
            if zz is None:
                hi = mid
            else:
                lo = mid
                best = (zz, pp, mid)
        z, pre, strength = best
        warns.append(f"stabilisation reduced to {strength:.0%} strength to stay within max_zoom {max_zoom:.2f}")
    return z, pre, warns

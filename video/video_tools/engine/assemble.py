"""Final pass: read graded intermediates in timeline order, build transitions, overlay animated
texts, and encode the deliverable (H.264 High yuv420p BT.709, CRF 17 slow, AAC 256k, faststart)."""
import math
import os
import time

import numpy as np

from common import (FFMPEG, YUV2RGB, RGB2YUV, TAGS709, SETPARAMS709, FrameReader, FrameWriter, log, atomic_replace,
                    free_ram_gb)

SLOW_FPS = 5.0        # assembly normally runs ~11-13 fps (1080x1920); RAM-starved finals ran 1.6-2.4 and 4.4-5.9 fps
SLOW_WINDOW_S = 60.0


def _smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


class Transitions:
    def __init__(self, W, H, cv2):
        self.W, self.H, self.cv2 = W, H, cv2
        self.white = np.full((H, W, 3), 255, np.uint8)
        self.black = np.zeros((H, W, 3), np.uint8)

    def apply(self, typ, A, B, t, o, params):
        cv2 = self.cv2
        if typ == "crossfade":
            return cv2.addWeighted(A, 1.0 - t, B, t, 0.0)
        if typ in ("dip_white", "dip_black"):
            C = self.white if typ == "dip_white" else self.black
            if t < 0.5:
                e = _smooth(t / 0.5)
                return cv2.addWeighted(A, 1.0 - e, C, e, 0.0)
            e = _smooth((t - 0.5) / 0.5)
            return cv2.addWeighted(C, 1.0 - e, B, e, 0.0)
        if typ == "whip":
            return self._whip(A, B, t, o, params.get("dir", "left"))
        raise ValueError(typ)

    def _whip(self, A, B, t, o, direction):
        """Fast directional slide: A and B travel as one strip (like a whip pan), with motion blur
        proportional to the instantaneous velocity (cosine ease -> fast in the middle)."""
        cv2 = self.cv2
        horiz = direction in ("left", "right")
        D = self.W if horiz else self.H
        e = 0.5 - 0.5 * math.cos(math.pi * t)
        v = 0.5 * math.pi * math.sin(math.pi * t) / max(1, o) * D  # px per frame
        off = e * D
        if direction in ("left", "up"):
            strip = np.concatenate([A, B], axis=1 if horiz else 0)
            shift = -off
        else:
            strip = np.concatenate([B, A], axis=1 if horiz else 0)
            shift = -(D - off)
        L = int(max(1, round(v * 0.85)))
        if L > 1:
            strip = cv2.blur(strip, (L, 1) if horiz else (1, L), borderType=cv2.BORDER_REPLICATE)
        M = np.array([[1, 0, shift if horiz else 0], [0, 1, 0 if horiz else shift]], np.float64)
        return cv2.warpAffine(strip, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def _reader(path, W, H):
    cmd = [FFMPEG, "-nostdin", "-hide_banner", "-v", "error", "-threads", "3", "-i", path,
           "-vf", f"scale={YUV2RGB},format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return FrameReader(cmd, (H, W, 3), qsize=3)


def final_encoder_cmd(out_tmp, W, H, fps, audio_wav, preview, crf=17, preset="slow", title=None):
    if preview:
        crf, preset = 23, "veryfast"
    cmd = [FFMPEG, "-nostdin", "-hide_banner", "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(fps), "-i", "-"]
    if audio_wav:
        cmd += ["-i", audio_wav]
    cmd += ["-map", "0:v:0"]
    if audio_wav:
        cmd += ["-map", "1:a:0"]
    cmd += ["-vf", f"scale={RGB2YUV},format=yuv420p,{SETPARAMS709}",
            "-c:v", "libx264", "-profile:v", "high", "-preset", preset, "-crf", str(crf),
            "-g", str(fps * 2), "-keyint_min", str(fps), "-fps_mode", "cfr", "-r", str(fps), *TAGS709]
    if audio_wav:
        cmd += ["-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2"]
    cmd += ["-movflags", "+faststart"]
    if title:
        cmd += ["-metadata", f"title={title}"]
    cmd += [out_tmp]
    return cmd


def assemble(edl, results, texts, audio_wav, out_path, preview=False, consume=False):
    import cv2
    cv2.setNumThreads(4)
    tl = edl["timeline"]
    rows = tl["rows"]
    W, H, fps = edl["output"]["w"], edl["output"]["h"], tl["fps"]
    tmp = out_path + ".tmp.mp4"
    enc = FrameWriter(final_encoder_cmd(tmp, W, H, fps, audio_wav, preview, edl["output"].get("crf", 17),
                                        edl["output"].get("preset", "slow"), edl.get("title")), qsize=6)
    trans = Transitions(W, H, cv2)
    readers, last = {}, {}
    total = tl["total_f"]
    t0 = time.time()
    tlast = t0
    lo = 0
    problems = []
    hist, warned_slow = [(t0, 0)], preview     # (time, frames done) at each progress line
    try:
        for f in range(total):
            while rows[lo]["end_f"] <= f:
                lo += 1
            act = [r for r in rows[lo:lo + 3] if r["start_f"] <= f < r["end_f"]]
            frames = []
            for r in act:
                iid = r["id"]
                if iid not in readers:
                    readers[iid] = _reader(results[iid]["out"], W, H)
                fr = readers[iid].read()
                if fr is None:
                    problems.append(f"{iid}: intermediate ended early at output frame {f}")
                    fr = last.get(iid)
                    if fr is None:
                        raise RuntimeError(f"{iid}: no frames in intermediate {results[iid]['out']}")
                last[iid] = fr
                frames.append(fr)
            if len(frames) == 1:
                img = frames[0].copy() if texts else frames[0]
            else:
                a, b = act[0], act[1]
                tr = a["trans_out"]
                o = a["o_out"]
                t = (f - b["start_f"] + 0.5) / o
                img = trans.apply(tr["type"], frames[0], frames[1], t, o, tr)
            if texts:
                texts.apply(img, f)
            enc.write(img)
            for r in act:
                if r["end_f"] == f + 1:
                    readers.pop(r["id"]).close()
                    last.pop(r["id"], None)
                    if consume:  # low-disk mode: this intermediate is no longer needed
                        try:
                            os.remove(results[r["id"]]["out"])
                        except OSError:
                            pass
            now = time.time()
            if now - tlast > 10:
                tlast = now
                log(f"  assemble {f + 1}/{total} frames ({(f + 1) / (now - t0):.1f} fps)")
                hist.append((now, f + 1))
                old = [h for h in hist if now - h[0] >= SLOW_WINDOW_S]
                if not warned_slow and old:
                    rate = (f + 1 - old[-1][1]) / (now - old[-1][0])
                    if rate < SLOW_FPS:
                        warned_slow = True
                        ram = free_ram_gb()[0]
                        log(f"WARNING assembly has run at {rate:.1f} fps (< {SLOW_FPS:g}) for {now - old[-1][0]:.0f} s - "
                            f"the machine is probably swapping" + (f" ({ram:.2f} GB RAM free)" if ram is not None else "") +
                            ": close browsers/Word/other apps (normal is ~11 fps)")
        enc.close()
    except BaseException:
        enc.abort()
        for rd in readers.values():
            rd.close()
        raise
    for rd in readers.values():
        rd.close()
    atomic_replace(tmp, out_path)
    for p in sorted(set(problems))[:10]:
        log("WARNING " + p)
    return time.time() - t0

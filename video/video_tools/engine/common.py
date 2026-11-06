"""Shared helpers: logging, ffprobe, ffmpeg pipe readers/writers, hashing."""
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

import numpy as np

ENGINE_VERSION = "1.2.0"
STALL_TIMEOUT = 240  # seconds without a frame moving through a pipe => treat the process as hung
ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(ENGINE_DIR, "fonts")
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"

# Windows: don't pop up console windows for child processes
CREATE_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Colour conversion flags used everywhere (explicit BT.709, never rely on defaults)
SWS = "accurate_rnd+full_chroma_int"
YUV2RGB = f"in_color_matrix=bt709:in_range=tv:out_range=pc:flags={SWS}"
RGB2YUV = f"out_color_matrix=bt709:out_range=tv:flags={SWS}"
TAGS709 = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
SETPARAMS709 = "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def key_of(obj, n=12):
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:n]


def file_sig(path):
    st = os.stat(path)
    return [os.path.basename(path), st.st_size, int(st.st_mtime)]


def db2lin(db):
    return 10.0 ** (db / 20.0)


def run(cmd, cwd=None, check=True, capture=True):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.PIPE if capture else None, stdin=subprocess.DEVNULL,
                       creationflags=CREATE_FLAGS)
    if check and p.returncode != 0:
        err = p.stderr.decode("utf-8", "replace")[-3000:] if capture else ""
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str, cmd))[:600]}\n{err}")
    return p


_probe_cache = {}


def probe(path):
    """Return dict(w, h, rotation, duration, fps, has_audio, uw, uh, auto_cw) for a media file.
    rotation: display-matrix rotation as ffprobe reports it; auto_cw: clockwise degrees ffmpeg's
    autorotate would apply; (uw, uh): upright size after autorotate."""
    path = os.path.abspath(path)
    if path in _probe_cache:
        return _probe_cache[path]
    p = run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    j = json.loads(p.stdout.decode("utf-8", "replace"))
    v = next((s for s in j["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in j["streams"] if s.get("codec_type") == "audio"), None)
    if v is None:
        raise RuntimeError(f"no video stream in {path}")
    rot = 0.0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = float(sd["rotation"])
    if "tags" in v and "rotate" in v["tags"]:  # very old style tag
        rot = -float(v["tags"]["rotate"])
    auto_cw = int(round(-rot)) % 360
    w, h = int(v["width"]), int(v["height"])
    uw, uh = (h, w) if auto_cw in (90, 270) else (w, h)
    num, den = v.get("r_frame_rate", "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    dur = float(j.get("format", {}).get("duration", v.get("duration", 0)) or 0)
    info = dict(w=w, h=h, rotation=rot, auto_cw=auto_cw, uw=uw, uh=uh, duration=dur, fps=fps,
                has_audio=a is not None, pix_fmt=v.get("pix_fmt"), codec=v.get("codec_name"),
                transfer=v.get("color_transfer"))
    _probe_cache[path] = info
    return info


def rotation_filters(total_cw, hflip=False):
    total_cw %= 360
    f = []
    if total_cw == 90:
        f.append("transpose=clock")
    elif total_cw == 180:
        f += ["hflip", "vflip"]
    elif total_cw == 270:
        f.append("transpose=cclock")
    elif total_cw != 0:
        raise ValueError(f"rotation must be a multiple of 90, got {total_cw}")
    if hflip:
        f.append("hflip")
    return f


def upright_rect_to_raw(rect, raw_w, raw_h, total_cw, hflip):
    """Map an axis-aligned rect (x, y, w, h) in upright (rotated+flipped) coords back to the raw
    decoded frame, so we can crop BEFORE the (expensive) transpose."""
    x, y, w, h = rect
    total_cw %= 360
    uw, uh = (raw_h, raw_w) if total_cw in (90, 270) else (raw_w, raw_h)
    if hflip:
        x = uw - x - w
    if total_cw == 0:
        return (x, y, w, h)
    if total_cw == 90:      # transpose=clock: raw(xr,yr) -> up(Hr-1-yr, xr)
        return (y, raw_h - x - w, h, w)
    if total_cw == 270:     # transpose=cclock: raw(xr,yr) -> up(yr, Wr-1-xr)
        return (raw_w - y - h, x, h, w)
    if total_cw == 180:
        return (raw_w - x - w, raw_h - y - h, w, h)
    raise ValueError(total_cw)


class _Drain(threading.Thread):
    def __init__(self, stream):
        super().__init__(daemon=True)
        self.stream, self.chunks = stream, []

    def run(self):
        try:
            for line in iter(self.stream.readline, b""):
                self.chunks.append(line)
                if len(self.chunks) > 400:
                    del self.chunks[:200]
        except Exception:
            pass

    def text(self):
        return b"".join(self.chunks).decode("utf-8", "replace")


def _readexact(f, n):
    buf = bytearray(n)
    mv = memoryview(buf)
    got = 0
    while got < n:
        r = f.readinto(mv[got:])
        if not r:
            return None if got == 0 else buf[:got]
        got += r
    return buf


class FrameReader:
    """Runs an ffmpeg command that writes raw frames to stdout; a background thread keeps a small
    queue of decoded frames so decoding overlaps with our processing."""

    def __init__(self, cmd, shape, qsize=4, cwd=None):
        self.shape = tuple(shape)
        self.nbytes = int(np.prod(shape))
        self.cmd = cmd
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     stdin=subprocess.DEVNULL, bufsize=0, cwd=cwd,
                                     creationflags=CREATE_FLAGS)
        self.err = _Drain(self.proc.stderr)
        self.err.start()
        self.q = queue.Queue(maxsize=qsize)
        self.stop = False
        self.partial = False
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()

    def _run(self):
        try:
            while not self.stop:
                buf = _readexact(self.proc.stdout, self.nbytes)
                if buf is None or len(buf) < self.nbytes:
                    self.partial = buf is not None
                    break
                fr = np.frombuffer(buf, np.uint8).reshape(self.shape)
                while not self.stop:
                    try:
                        self.q.put(fr, timeout=1.0)
                        break
                    except queue.Full:
                        continue
        except Exception:
            pass
        finally:
            try:
                self.q.put(None, timeout=5)
            except queue.Full:
                pass

    def read(self, timeout=None):
        try:
            return self.q.get(timeout=timeout or STALL_TIMEOUT)
        except queue.Empty:
            self.close()
            raise RuntimeError(f"decoder stalled for {timeout or STALL_TIMEOUT}s (killed): {' '.join(self.cmd)[:300]}")

    def close(self):
        self.stop = True
        try:
            while True:
                self.q.get_nowait()
        except queue.Empty:
            pass
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait()
        self.t.join(timeout=10)
        try:
            self.proc.stdout.close()
        except Exception:
            pass

    def stderr_text(self):
        return self.err.text()


class FrameWriter:
    """Feeds raw frames to an ffmpeg encoder from a background thread."""

    def __init__(self, cmd, qsize=4, cwd=None):
        self.cmd = cmd
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE, bufsize=0, cwd=cwd,
                                     creationflags=CREATE_FLAGS)
        self.err = _Drain(self.proc.stderr)
        self.err.start()
        self.q = queue.Queue(maxsize=qsize)
        self.exc = None
        self.count = 0
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()

    def _run(self):
        try:
            while True:
                fr = self.q.get()
                if fr is None:
                    break
                self.proc.stdin.write(memoryview(np.ascontiguousarray(fr)).cast("B"))
                self.count += 1
        except Exception as e:  # broken pipe -> encoder died
            self.exc = e
            # keep draining so the producer never blocks forever
            while True:
                try:
                    if self.q.get(timeout=STALL_TIMEOUT) is None:
                        break
                except queue.Empty:
                    break

    def write(self, frame, timeout=None):
        if self.exc is not None:
            raise RuntimeError(f"encoder failed: {self.exc}\n{self.err.text()[-2000:]}")
        try:
            self.q.put(frame, timeout=timeout or STALL_TIMEOUT)
        except queue.Full:
            self.abort()
            raise RuntimeError(f"encoder stalled for {timeout or STALL_TIMEOUT}s (killed): {' '.join(self.cmd)[:300]}")

    def close(self):
        try:
            self.q.put(None, timeout=STALL_TIMEOUT)
        except queue.Full:
            self.abort()
            raise RuntimeError("encoder stalled while closing (killed)")
        self.t.join(timeout=STALL_TIMEOUT)
        if self.t.is_alive():
            self.abort()
            raise RuntimeError("encoder stalled while flushing (killed)")
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        rc = self.proc.wait()
        if rc != 0 or self.exc is not None:
            raise RuntimeError(f"encoder exited {rc}: {' '.join(self.cmd)[:400]}\n{self.err.text()[-3000:]}")

    def abort(self):
        try:
            self.proc.kill()
        except Exception:
            pass


def ffesc(path):
    """Escape a path for use inside an ffmpeg filtergraph option value."""
    p = path.replace("\\", "/")
    return p.replace(":", "\\\\:").replace("'", "\\\\'")


def atomic_replace(tmp, final):
    if os.path.exists(final):
        os.remove(final)
    os.replace(tmp, final)


def free_gb(path):
    try:
        return shutil.disk_usage(os.path.splitdrive(os.path.abspath(path))[0] + os.sep).free / 1e9
    except Exception:
        return float("inf")


def free_ram_gb():
    """(available, total) physical RAM in GB - Windows GlobalMemoryStatusEx, Linux /proc/meminfo, else
    (None, None).  VT_RAM_GB_OVERRIDE=<GB> fakes the available amount (tests of the low-RAM paths)."""
    avail = total = None
    try:
        if os.name == "nt":
            import ctypes

            class _MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            st = _MS()
            st.dwLength = ctypes.sizeof(_MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                avail, total = st.ullAvailPhys / 1e9, st.ullTotalPhys / 1e9
        elif os.path.exists("/proc/meminfo"):
            info = {}
            for line in open("/proc/meminfo"):
                k, _, v = line.partition(":")
                info[k] = float(v.split()[0]) * 1024 / 1e9
            avail, total = info.get("MemAvailable"), info.get("MemTotal")
    except Exception:
        pass
    if os.environ.get("VT_RAM_GB_OVERRIDE"):
        try:
            avail = float(os.environ["VT_RAM_GB_OVERRIDE"])
        except ValueError:
            pass
    return avail, total

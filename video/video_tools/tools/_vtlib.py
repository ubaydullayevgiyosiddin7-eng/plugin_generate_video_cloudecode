"""Small helpers shared by the tools (not a tool itself): locations, ffprobe, console safety."""
import json
import os
import shutil
import subprocess
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
KIT_DIR = os.path.dirname(TOOLS_DIR)
ENGINE_DIR = os.path.join(KIT_DIR, "engine")
FONT_DIR = os.path.join(ENGINE_DIR, "fonts")
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"
CREATE_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

VIDEO_EXT = (".mov", ".mp4", ".m4v", ".avi", ".mkv", ".mts", ".3gp")
PHOTO_EXT = (".heic", ".heif", ".jpg", ".jpeg", ".png", ".dng", ".tif", ".tiff", ".webp")


def safe_console():
    """Never crash printing non-cp1252 text (Uzbek okina, emoji) on a Windows console."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="backslashreplace")
        except Exception:
            pass


def use_engine():
    """Make the engine modules (edl, framing, common, ...) importable."""
    if ENGINE_DIR not in sys.path:
        sys.path.insert(0, ENGINE_DIR)


def run(cmd, check=True, cwd=None, text=False):
    p = subprocess.run([str(c) for c in cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       stdin=subprocess.DEVNULL, cwd=cwd, creationflags=CREATE_FLAGS)
    if check and p.returncode != 0:
        err = p.stderr.decode("utf-8", "replace")[-2500:]
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str, cmd))[:500]}\n{err}")
    if text:
        p.stdout = p.stdout.decode("utf-8", "replace")
        p.stderr = p.stderr.decode("utf-8", "replace")
    return p


def ffprobe(path, extra=()):
    p = run([FFPROBE, "-v", "error", *extra, "-show_streams", "-show_format", "-of", "json", path])
    return json.loads(p.stdout.decode("utf-8", "replace"))


def video_info(path):
    """Duration, fps, coded + upright size, rotation, audio flag, codec, HDR transfer of a video."""
    j = ffprobe(path)
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in j.get("streams", []) if s.get("codec_type") == "audio"), None)
    if v is None:
        raise RuntimeError("no video stream")
    rot = 0.0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = float(sd["rotation"])
    if "rotate" in (v.get("tags") or {}):
        rot = -float(v["tags"]["rotate"])
    w, h = int(v["width"]), int(v["height"])
    cw = int(round(-rot)) % 360
    uw, uh = (h, w) if cw in (90, 270) else (w, h)

    def rate(s):
        n, _, d = (s or "0/1").partition("/")
        return float(n) / float(d or 1) if float(d or 1) else 0.0
    dur = float(j.get("format", {}).get("duration") or v.get("duration") or 0)
    return dict(duration=dur, fps=round(rate(v.get("r_frame_rate")), 3), avg_fps=round(rate(v.get("avg_frame_rate")), 3),
                w=w, h=h, rotation=rot, upright_w=uw, upright_h=uh, codec=v.get("codec_name"),
                pix_fmt=v.get("pix_fmt"), transfer=v.get("color_transfer"), primaries=v.get("color_primaries"),
                has_audio=a is not None, audio_codec=(a or {}).get("codec_name"),
                size=int(j.get("format", {}).get("size") or os.path.getsize(path)), raw=j)


def orientation(w, h):
    if abs(w - h) <= 0.02 * max(w, h):
        return "square"
    return "portrait" if h > w else "landscape"


def font(size, name="Montserrat[wght].ttf"):
    from PIL import ImageFont
    try:
        f = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
        try:
            f.set_variation_by_axes([600])
        except Exception:
            pass
        return f
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


def fmt_t(sec):
    m, s = divmod(max(0.0, sec), 60)
    return f"{int(m)}:{s:05.2f}"


def free_gb(path):
    try:
        return shutil.disk_usage(os.path.splitdrive(os.path.abspath(path))[0] + os.sep).free / 1e9
    except Exception:
        return float("inf")

"""Opuscar timeline → opus-sound-layer cue sheet (audio/cues.json).

    python video/sound/events_to_cues.py <film>/events.json --fps 24 [--map map.json] [--voice-dir voice]
        [--music audio/music.wav] [--energy calm] > <film>/audio/cues.json

`node core/render/events.mjs <film>` writes events.json from the picture's own code (window.EV), so every
cue frame here comes from the timeline, never typed by hand. Each event type maps to a sound type of the
sound-layer library and a "visual" tag that its qa.py checks against the picture:

    magnet → thump (land)     erase → paper (move)      cap → click (land)
    pop / appear → pop        cut → transition (cut)    hero → hit+boom, weight hero, stop_before + build

Pen strokes (stroke / write / dash / tap) are left out by default: there are hundreds and the sound-layer
rules put sound only on real actions. Keep them in your own film's synthesized foley, or give them a sound
with --map '{"stroke": {"sound": "paper"}}'. A map entry of null drops that type.
"vo" events become the voice list (<voice-dir>/t<id>.wav, the trimmed takes). A "cues" event with a
"silence" pair becomes silence_ok, so qa.py does not fail a silence the film planned.
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT = {
    "magnet": {"sound": "thump", "visual": "land"},
    "erase": {"sound": "paper", "visual": "move", "align": "start"},
    "cap": {"sound": "click", "visual": "land"},
    "pop": {"sound": "pop", "visual": "land"},
    "appear": {"sound": "pop", "visual": "land"},
    "cut": {"sound": "transition", "visual": "cut"},
    "hero": {"sound": "hit+boom", "weight": "hero", "visual": "land", "stop_before": True, "build": True},
    "stroke": None, "write": None, "dash": None, "tap": None,
}


def convert(data: dict, fps: int, mapping: dict, voice_dir: str, music: str | None, energy: str) -> dict:
    sheet = {"fps": fps, "duration_s": round(data["dur"], 3), "energy": energy, "kit": "audio/kit", "cues": []}
    if music:
        sheet["music"] = {"file": music, "start_s": 0, "loop": True, "fade_out_s": 1.5}
    voice, n = [], {}
    for e in data["ev"]:
        typ = e.get("type")
        if typ == "vo":
            voice.append({"file": f"{voice_dir}/t{e['id']}.wav", "start_s": round(e["t"], 3)})
            continue
        if typ == "cues":
            if e.get("silence"):
                sheet["silence_ok"] = [[round(e["silence"][0], 2), round(e["silence"][1], 2)]]
            continue
        rule = mapping.get(typ, "unmapped")
        if rule is None:
            continue
        if rule == "unmapped":
            print(f"skipped event type {typ!r} at {e['t']:.2f}s (add it with --map)", file=sys.stderr)
            continue
        n[typ] = n.get(typ, 0) + 1
        cue = {"id": f"{typ}:{n[typ]}", "frame": round(e["t"] * fps), **rule}
        if "pan" in e:
            cue["pan"] = round(max(-0.6, min(0.6, e["pan"])), 2)
        sheet["cues"].append(cue)
    if voice:
        sheet["voice"] = voice
    return sheet


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("events", type=Path)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--map", default=None, help="JSON (inline or a file) merged over the default mapping")
    ap.add_argument("--voice-dir", default="voice")
    ap.add_argument("--music", default=None)
    ap.add_argument("--energy", choices=["punchy", "calm"], default="calm")
    a = ap.parse_args()
    mapping = dict(DEFAULT)
    if a.map:
        extra = Path(a.map).read_text(encoding="utf-8") if Path(a.map).exists() else a.map
        mapping.update(json.loads(extra))
    data = json.loads(a.events.read_text(encoding="utf-8"))
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(convert(data, a.fps, mapping, a.voice_dir, a.music, a.energy), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""O'zbekcha ovoz (Navoiy TTS) GPU'siz, protsessorda: reel va videolar uchun matndan ovoz.

    <tts>\\.venv\\Scripts\\python scripts\\navoiy_tts.py --reference my_ref.wav --lines lines.txt --out out
    <tts>\\.venv\\Scripts\\python scripts\\navoiy_tts.py --reference my_ref.wav "Birinchi gap." "Ikkinchi gap."

O'rnatish va papka tuzilishi: docs/content-tools.md. <tts> papkasi (NAVOIY_ROOT yoki --root, odatda D:\\My_projects\\tts)
CosyVoice, CosyVoice2-0.5B va navoiy-tts ni saqlaydi; skript o'sha papkaning .venv'ida ishga tushiriladi.
navoiy-tts/inference.py dan farqi: CUDA talab qilinmaydi, fp16 o'chiq, model bir marta yuklanib, har qator alohida
NN.wav bo'ladi (24 kHz). Protsessorda real vaqtdan ~6–7 marta sekin (i7-12700).
"""

import argparse
import os
import random
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("texts", nargs="*")
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("NAVOIY_ROOT", r"D:\My_projects\tts")))
    parser.add_argument("--lines", type=Path, help="bir qatorda bitta gap")
    parser.add_argument("--reference", type=Path, required=True, help="ovoz egasining roziligi bilan, 10–20 s toza yozuv")
    parser.add_argument("--emotion", default="warm", help="calm, warm, happy, surprised, sad, ...")
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=1986)
    args = parser.parse_args()
    texts = list(args.texts)
    if args.lines:
        texts += [t.strip() for t in args.lines.read_text(encoding="utf-8").splitlines() if t.strip()]
    if not texts:
        parser.error("matn yo'q")

    root = args.root.resolve()
    navoiy, cosy = root / "navoiy-tts", root / "CosyVoice"
    sys.path[:0] = [str(navoiy), str(cosy), str(cosy / "third_party" / "Matcha-TTS")]
    import torch
    import torchaudio
    from cosyvoice.cli.cosyvoice import CosyVoice2
    from inference import load_emotions, unwrap_state_dict  # navoiy-tts/inference.py
    from uztts.normalize import normalize

    _, emotions = load_emotions(navoiy / "emotions_40h.json")
    instruction = emotions[args.emotion.lower().strip("[]")]["instruct"].strip() + "<|endofprompt|>"

    started = time.time()
    model = CosyVoice2(str(root / "CosyVoice2-0.5B"), load_jit=False, load_trt=False, fp16=False)
    state = unwrap_state_dict(torch.load(navoiy / "emotion_600h_joint.pt", map_location="cpu", weights_only=True))
    model.model.llm.load_state_dict(state, strict=False)
    model.model.llm.eval()
    print(f"model {time.time() - started:.0f} s da yuklandi", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    for n, raw in enumerate(texts, 1):
        random.seed(args.seed)
        torch.manual_seed(args.seed)
        started = time.time()
        with torch.inference_mode():
            chunks = [r["tts_speech"].cpu() for r in model.inference_instruct2(
                normalize(raw, mode="infer"), instruction, str(args.reference.resolve()), stream=False,
                speed=args.speed)]
        audio = torch.cat(chunks, dim=1)
        path = args.out / f"{n:02d}.wav"
        torchaudio.save(str(path), audio, 24000)
        print(f"{path.name}: {audio.shape[-1] / 24000:.1f} s ovoz, {time.time() - started:.0f} s — {raw}", flush=True)


if __name__ == "__main__":
    main()

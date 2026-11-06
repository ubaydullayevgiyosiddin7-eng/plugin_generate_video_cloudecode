# Navoiy TTS: o'zbekcha ovoz, o'z ovozingizda, GPU'siz

Aisha (Toshkent) ochiq modeli, Apache 2.0, tijoriy maqsadda ham bepul: https://huggingface.co/aisha-org/navoiy-tts.
CosyVoice2-0.5B ustiga qurilgan. `navoiy_tts.py` uni protsessorda ishlatadi (fp16 o'chirilgan), qisqa namunadan ovozni
takrorlaydi va har bir gapni alohida `NN.wav` (24 kHz) qilib yozadi.

**Faqat ovoz egasining roziligi bilan** — o'z ovozingiz yoki ruxsat bergan odamniki.

### O'rnatish (bir marta, ~6 GB)

Git Bash'da:

```sh
mkdir -p /d/My_projects/tts && cd /d/My_projects/tts
G="git -c http.schannelCheckRevoke=false"
$G clone https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice && $G checkout 074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc && $G submodule update --init --recursive && cd ..
$G clone https://huggingface.co/aisha-org/navoiy-tts          # emotion_600h_joint.pt — 2 GB (git-lfs kerak)
$G clone https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B   # 3.8 GB

py -3.11 -m venv .venv
P=".venv/Scripts/python -m pip install --use-feature=truststore"
$P --upgrade pip
$P torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu
$P "setuptools<70" wheel numpy==1.26.4 tiktoken more-itertools numba tqdm
$P --no-build-isolation openai-whisper==20231117
$P transformers==4.51.3 huggingface_hub==0.36.2 conformer==0.3.2 diffusers==0.29.0 hydra-core==1.3.2 \
   HyperPyYAML==1.2.3 inflect==7.3.1 librosa==0.10.2 lightning==2.2.4 modelscope==1.20.0 omegaconf==2.3.0 \
   onnx==1.16.0 onnxruntime==1.18.0 protobuf==4.25 pyworld==0.3.4 soundfile==0.12.1 x-transformers==2.11.24 \
   wetext==0.0.4 matplotlib rich==13.7.1
```

Bu ro'yxatda `deepspeed`, `tensorrt` va `onnxruntime-gpu` ataylab yo'q: ular faqat GPU uchun. Whisper'ni
`--no-build-isolation` bilan o'rnatish shart, aks holda `pkg_resources` topilmaydi degan xato chiqadi.

### Namuna ovoz

Model bitta qisqa yozuvdan ovozni nusxalaydi. Yozuv talablari:
- uzunligi 12–20 soniya (30 soniyadan oshmasin);
- jim xonada yozilgan, musiqasiz;
- reelda qanday gapirishni xohlasangiz, o'sha ohangda va sal tezroq.

```sh
ffmpeg -i ovoz.ogg -af "highpass=f=70,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,areverse,loudnorm=I=-18:TP=-2:LRA=11" -ar 24000 -ac 1 -sample_fmt s16 my_ref.wav
```

Faqat egasining o'z ovozi yoki roziligi bor odamning ovozi ishlatiladi.

### Ishlatish

```
D:\My_projects\tts\.venv\Scripts\python video\navoiy\navoiy_tts.py --root D:\My_projects\tts --reference D:\My_projects\tts\my_ref.wav --emotion warm --speed 1.15 --lines lines.txt --out voice
```

- `lines.txt`: bir qatorda bitta gap. Natija `voice\01.wav, 02.wav, ...`
- Tezlik: i7-12700 da real vaqtdan ~20× sekin (4 s ovoz ≈ 80 s). 8 gaplik reel ≈ 10 daqiqa — orqa fonda ishlating.
- `--speed 1.15`–`1.25`: egasining ovozi uchun 1.15 to'g'ri tushgan. `--emotion`: calm, warm, happy, sad, angry, nervous, surprised, whisper, tired, sarcastic.
- Bitta gapni o'zgartirsangiz faqat o'shani qayta chiqaring (alohida lines faylida) va raqamini almashtiring.
- "no frontend is avaliable" va "unexpected 2 keys" xabarlari zararsiz.
- Model ismlar, qisqartmalar va o'zlashma so'zlarni xato o'qishi mumkin. Oddiy Whisper o'zbekchani yomon taniydi; uning
  o'rniga [NavAI Whisper](https://huggingface.co/navai-uz) (Apache-2.0, o'zbekchaga o'qitilgan, small/base CPU da ishlaydi)
  bilan har bir `NN.wav` ni matnga qaytarib, `lines.txt` bilan solishtirish mumkin (sinalmagan, 2026-11 da topilgan).
  Baribir har bir natijani o'zingiz eshiting. Boshqa o'zbekcha resurslar: [`../../uzbek/`](../../uzbek/README.md).

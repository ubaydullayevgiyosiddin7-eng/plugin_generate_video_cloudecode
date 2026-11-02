# Kontent kit — bizning qo'shimchalar

Bu repo [lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) (MIT, © LemoLab) nusxasi: 66 uslubda kod bilan qisqa film
yasaydigan Claude Code plagini. `kit/` — ustiga biz qo'shgan, kontent qilishda sinalgan narsalar. Kutubxonaning o'z fayllari
o'zgartirilmagan, shuning uchun yangilanishni upstream'dan bemalol olish mumkin.

| Papka | Nima | Holat |
|---|---|---|
| [`sound/`](sound/README.md) | videoga haqiqiy ovoz effektlari: Openverse qidiruv (`openverse.py`), Opuscar timeline → cue sheet (`events_to_cues.py`), Earshot + real-sound skill + opus-sound-layer o'rnatish (`setup.sh`) | skriptlar sinalgan; Earshot o'rnatilishi kerak |
| [`navoiy/`](navoiy/README.md) | o'zbekcha ovoz (Navoiy TTS) o'z ovozingizda, protsessorda | ishlaydi, birinchi reel shu bilan |
| [`whiteboard-vertical/`](whiteboard-vertical/README.md) | doska engine'i 9:16 (Reels) uchun | ishlaydi, birinchi reel shu bilan |

## Windows'da o'rnatish (korporativ tarmoq)

```
git clone https://github.com/ubaydullayevgiyosiddin7-eng/plugin_generate_video_cloudecode D:\My_projects\lemo-opuscar
mklink /J %USERPROFILE%\lemo-opuscar D:\My_projects\lemo-opuscar
set LEMO_OPUSCAR_HOME=/d/My_projects/lemo-opuscar
set NODE_OPTIONS=--use-system-ca
set PIP_USE_FEATURE=truststore
set CURL_HOME=D:\My_projects\curlhome          (ichida _curlrc: ssl-no-revoke)
winget install --source winget Gyan.FFmpeg
sh tools/directory/setup.sh deps                (keyin: mklink /J .venv\bin .venv\Scripts)
```

## Claude uchun tartib

1. Film: `AGENTS.md` (kutubxona qoidalari) → uslub `styles/<slug>/STYLE.md`.
2. Ovoz (gap): `kit/navoiy` — egasining roziligi bilan.
3. Effektlar va musiqa: `kit/sound` — haqiqiy CC0 yozuvlar, cue'lar timeline'dan, `qa.py` hal qiladi. Ovozni "yaxshi" deb aytma — raqam bilan ayt.
4. Vertikal doska: `kit/whiteboard-vertical`.
5. Topshirish: mp4 + `CREDITS.md` + Instagram matni; talaffuz va eshitib tekshirishni egasi qiladi.

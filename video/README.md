# Video

Ikki xil ish uchun narsalar:

- **Kod bilan film** (doska, akvarel, infografika va boshqa 66 uslub) — asosi [lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar)
  plagini (MIT, © LemoLab). U bu repoda yo'q: plagin o'zi yuklab oladi. Bu yerda faqat biz qo'shgan narsalar.
- **Telefon videolaridan film** (sayohat, tadbir) — [`video_tools/`](video_tools/README.md) kit.

| Papka | Nima | Holat |
|---|---|---|
| [`navoiy/`](navoiy/README.md) | o'zbekcha ovoz (Navoiy TTS) o'z ovozingizda, protsessorda | ishlaydi, birinchi reel shu bilan |
| [`sound/`](sound/README.md) | haqiqiy ovoz effektlari: Openverse qidiruv (`openverse.py`), Opuscar timeline → cue sheet (`events_to_cues.py`), Earshot + real-sound + opus-sound-layer o'rnatish (`setup.sh`) | skriptlar sinalgan; Earshot o'rnatilishi kerak |
| [`whiteboard-vertical/`](whiteboard-vertical/README.md) | lemo-opuscar doska engine'i 9:16 (Reels) uchun | ishlaydi, birinchi reel shu bilan |
| [`video_tools/`](video_tools/README.md) | telefon videolari → tayyor film: EDL engine, 13 ta tool, saboqlar, agent promptlari va o'zini o'rgatadigan 4 ta agent (retro → toolsmith + curator → auditor) | ishlaydi, 2 ta film shu bilan |

## lemo-opuscar'ni o'rnatish

```sh
claude plugin marketplace add lemomo-ai/lemo-opuscar
claude plugin install lemo-opuscar@lemolab
```

Birinchi ishlatilganda kutubxona `~/lemo-opuscar` ga yuklanadi. Boshqa joyda bo'lsin desangiz: `LEMO_OPUSCAR_HOME=/d/My_projects/lemo-opuscar`.

### Windows'da (korporativ tarmoq)

```
set LEMO_OPUSCAR_HOME=/d/My_projects/lemo-opuscar
set NODE_OPTIONS=--use-system-ca
set PIP_USE_FEATURE=truststore
set CURL_HOME=D:\My_projects\curlhome          (ichida _curlrc: ssl-no-revoke)
winget install --source winget Gyan.FFmpeg
```

Kutubxona papkasida `sh plugin/skills/lemo-opuscar/scripts/setup.sh deps`, keyin `mklink /J .venv\bin .venv\Scripts`.
Katta repo klonlanayotganda uzilsa: `git -c http.schannelCheckRevoke=false clone ...`.

## Claude uchun tartib (kod bilan film)

1. Film: lemo-opuscar skilli (`AGENTS.md` → uslubning `STYLE.md`).
2. Ovoz (gap): `video/navoiy` — faqat ovoz egasining roziligi bilan.
3. Effektlar va musiqa: `video/sound` — haqiqiy CC0 yozuvlar, cue'lar timeline'dan, `qa.py` hal qiladi. Ovozni "yaxshi" deb aytma — raqam bilan ayt.
4. Vertikal doska: `video/whiteboard-vertical`.
5. Topshirish: mp4 + `CREDITS.md` + Instagram matni; talaffuz va eshitib tekshirishni egasi qiladi.

## video_tools haqida

- Ishchi nusxa `C:\My_poject\video_tools` da turadi (agentlar va hujjatlar shu yo'lga bog'langan). Bu papka — uning
  zaxirasi. Kit o'zgargandan keyin yangilash (Git Bash):
  ```sh
  cd /c/My_poject/video_tools && tar --exclude=engine/cache --exclude=__pycache__ --exclude=examples \
    --exclude=retro --exclude=inbox.md --exclude=audit -cf - . | tar -xf - -C /c/My_poject/helpful_cloude/video/video_tools
  ```
- Agentlarni o'rnatish: `python video_tools/agents/install.py` → `~/.claude/agents/`, keyin yangi Claude Code sessiyasi.
- `examples/`, `retro/`, `inbox.md` va render keshi repoga qo'yilmagan: ularda shaxsiy kadrlar tavsifi bor. Shuning uchun
  repodagi nusxada `tools/selftest.py` ning ikkita tekshiruvi (`kuzgi regression`, `kuzgi storks`) misollarsiz o'tmaydi;
  ishchi nusxada hammasi joyida.

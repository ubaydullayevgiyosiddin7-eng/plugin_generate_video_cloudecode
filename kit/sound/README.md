# Ovoz: kod bilan yasalgan videoga haqiqiy ovoz effektlari

Claude ovozni eshitmaydi, shuning uchun o'zi sintez qilgan effektlar "kompyuter ovozi"dek chiqadi va kadrga tushmaydi.
Uchta bepul vosita buni tuzatadi (manba: 2026-11 dagi Instagram video, "pastga ovoz deb yozing").

| # | Vosita | Nima qiladi | Kalit/pul |
|---|---|---|---|
| 1 | **Openverse API** — `openverse.py` (bizniki) | 5 milliondan ortiq ochiq audio ichidan qidiradi, yuklaydi, muallif va litsenziyani `CREDITS.md` ga yozadi | kalitsiz, bepul |
| 2 | **real-sound** skill ("Real SFX") — Earshot repo ichida, `skills/real-sound/` | timeline'dan har bir harakat kadrini oladi, o'sha kadrga haqiqiy yozuvni qo'yadi, miks + QA + kredit. Soddaroq varianti: **opus-sound-layer** (1 139 ta CC0 ovoz, `mix.py` cue sheet bo'yicha, `qa.py` sinxronni tekshiradi) | bepul, MIT |
| 3 | **Earshot** — github.com/Leonxlnx/earshot | agentga "quloq": ovozni tasvirlaydi, tavsifga mosligini o'lchaydi, filmdagi voqealarni topadi; mos ovoz topilmasa **kod bilan yaratadi** (252 ta effekt banki, `earshot sfx render whoosh_fast/crisp`), butun "kit" ham | bepul, MIT, faqat CPU |

## Qachon qaysi biri

- **Tez reel (doska, 30–40 s):** opus-sound-layer. `events_to_cues.py` Opuscar `events.json` dan cue sheet yasaydi → `mix.py` → `qa.py`.
- **Bitta aniq ovoz kerak** ("logoga whoosh"): `openverse.py search "whoosh" --max-s 2` → `get <id>`.
- **Hech narsa topilmadi:** `earshot sfx list --kind whoosh` → `earshot sfx render ... -o x.wav` (modelsiz, internetsiz).
- **Ovoz yaxshimi — tekshirish:** `earshot` (realness, match, timeline). Claude hech qachon "yaxshi eshitiladi" demaydi — raqam bilan aytadi.
- **Katta launch-film:** `skills/real-sound/SKILL.md` to'liq jarayoni (brief, sourcing, litsenziya auditi, 5 ta tanqidchi, master).

## O'rnatish (bir marta)

```
sh kit/sound/setup.sh                 # ../sound-tools ga aniq versiyalarni klonlaydi, Earshot venv (CPU torch), oxirida EARSHOT_PY= va LAYER= chiqaradi
```

Korporativ tarmoqda (sertifikat ushlanadigan joyda) setup.sh o'zi `--use-feature=truststore` va `schannelCheckRevoke=false` ishlatadi.
`uv` kerak emas: opus-sound-layer skriptlarini Earshot venv'idagi python bilan ishga tushiring.

Claude Code'ga ulash (ixtiyoriy, modellar yuklangan holda turadi):

```
claude mcp add earshot --scope user -e EARSHOT_THREADS=3 -- <EARSHOT_PY> -m earshot mcp
```

Skill'lar: `<sound-tools>/earshot/skills/earshot` va `.../real-sound` papkalarini `~/.claude/skills/` ga nusxalang.

## Opuscar filmiga ovoz berish (doska misolida)

```
cd <lemo-opuscar>
node core/render/events.mjs <film> --size 1080x1920                     # timeline → <film>/events.json
python kit/sound/events_to_cues.py <film>/events.json --fps 24 > <film>/audio/cues.json
cd <film>
<EARSHOT_PY> <LAYER>/scripts/sfx.py kit                                  # birinchi marta: 1 139 CC0 ovoz (10 daqiqagacha)
<EARSHOT_PY> <LAYER>/scripts/sfx.py browse --type thump --like "magnet soft"   # audio/browse.png ga qarab id tanlang
<EARSHOT_PY> <LAYER>/scripts/mix.py audio/cues.json                      # → audio/mix.wav (−14 LUFS)
ffmpeg -i out/video.mp4 -i audio/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest out/final.mp4
<EARSHOT_PY> <LAYER>/scripts/qa.py out/final.mp4                          # FAIL bo'lsa cue/ovozni o'zgartiring, chegarani emas
```

`events_to_cues.py` qoidalari: magnit → thump, o'chirg'ich → paper, qopqoq → click, `hero` → hit+boom; ruchka chiziqlari
(yuzlab) default'da tashlab ketiladi — ular uchun filmning o'z sintez foley'si qoladi yoki `--map '{"stroke": {"sound": "paper"}}'`.
Ovoz (`vo`) voqealari `voice` ro'yxatiga, rejalangan jimlik `silence_ok` ga o'tadi.

## Litsenziya qoidasi

Biznes uchun reel = tijoriy foydalanish. Faqat **CC0 / PDM / CC BY** (BY — muallifni yozish shart). NC va ND hech qachon.
`openverse.py` buni o'zi filtrlaydi; har bir yuklangan fayl `CREDITS.md` ga tushadi.

## Holat (2026-11-02)

- `openverse.py` va `events_to_cues.py` shu kompyuterda sinaldi (qidiruv, CC0 yuklash + kredit, doska filmidan cue sheet).
- Openverse'ning yangi (keshlanmagan) so'rovlari ba'zan 60 s da 504 beradi — skript 3 marta qayta urinadi; bo'lmasa so'zni soddalashtiring.
- Earshot va opus-sound-layer hali **o'rnatilmagan**: `setup.sh` ni egasi o'zi ishga tushirishi kerak (begona kodni o'rnatish uchun ruxsat).

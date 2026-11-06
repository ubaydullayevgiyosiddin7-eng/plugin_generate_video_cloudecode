# Reels / Shorts: AI bilan qisqa video

YouTube videolaridan saboqlar (2026-11-06; manba va vaqt belgisi har birida). Tavsiya — majburiy emas.
**C** = Claude / kod avtomatlashtira oladi · **H** = odam yoki tashqi ilova kerak.

## Saboqlar

| # | Nima qilish | Kim | Manba |
|---|---|---|---|
| 1 | **Qatorma-qator vizual reja:** har ssenariy qatori uchun "tushunish uchun muhimmi?" — ha → animatsiya, nafas olish qatori → faqat subtitr. Ilgak (hook) faqat subtitr bilan, tomoshabin gapiruvchi bilan bog'lansin | C | B [5:29], [6:30] |
| 2 | **Subtitr — eng muhim qism:** ko'pchilik ovozsiz ko'radi. Kitda ffmpeg + ASS bilan yoqiladi | C | B [4:06] |
| 3 | **So'z darajasidagi transkript (JSON) bo'yicha kesish:** Claude vaqt belgilaridan bo'laklarni tanlaydi, ffmpeg kesadi (bizning EDL g'oyasi) | C | B [1:35]–[3:11] |
| 4 | **O'z namunalaringiz bilan o'rgating, keyin skill qiling:** 3 ta qo'lda qilingan short + har tanlov sababi; vaqt, tezlik, kamera bo'yicha tuzatishlar skillga yoziladi | C+H | B [0:37], [11:33] |
| 5 | **Avval arzon maket, keyin faqat tasdiqlangan sahnani animatsiya** — animatsiya qimmat bosqich; generatsiya promptini ishga tushirishdan oldin tasdiqlash | H gate | B [7:56]; C [15:26], [24:25] |
| 6 | **Brend izchilligi:** ~15 ta namuna rasm (masalan, oq + ko'k urg'u) — Claude dizayndan oldin o'rganadi; mos kelmagan bo'laklar "arzon yamoq"dek ko'rinadi | C (namunani H tanlaydi) | B [8:30] |
| 7 | **Timeline jadvali:** har animatsiya → vaqt belgisi; yig'ish oson. Musiqa ovoz ostida ~−20 dB | C | B [13:54] |
| 8 | **Tushuntiruvchi motion-grafika turlari:** sarlavha chiqishi, ovozga ergashadigan subtitr, ro'yxat bandlari birma-bir, raqam sanash, ikki fikr yonma-yon; b-roll: hook karta, aniqlik karta, infografika | C (lemo-opuscar) | A [5:06], [5:54]–[6:52] |
| 9 | **Ovoz dizayni videoni "sotadi":** model kadrma-kadr tahlil qilib SFX joyini yozadi; generatsiyadan faqat audio olinib asl videoga qo'yiladi | C (tahlil, miks); generatsiya — H | C [23:32]–[26:02] |
| 10 | Umumiy stock b-roll emas — b-roll aynan o'sha qatorga mos; odam izchilligi uchun 3 ta rasmdan "character sheet" | H/ilova | C [9:44], [10:09] |
| 11 | **Jimlikni transkript bo'yicha kesish**, muharrir izohlari marker sifatida. Premiere'ni computer use bilan boshqarish 14 daqiqa — arzimaydi; kod yoki DaVinci MCP tezroq | C | C [2:52], [3:29], [9:19] |
| 12 | **Ilgak naqshi:** avval natija, keyin burilish ("Bir odam Eyfel minorasini sotdi — keyin yana sotdi"); ssenariy: ilgak → rivoj → qoniqarli yakun | C | D [3:20], [5:03] |
| 13 | 16:9 → 9:16 qayta kadrlash, obyekt kadrda qolsin (kitda bor) | C | A [2:37] |
| 14 | Rang — LUT bilan (ffmpeg `lut3d`) | C | C [21:59] |

## "Faqat Claude bilan" video — nima qayta ishlatiladi

claude.ai'dagi "cartoon audio short" skilli shunday ishlaydi: qayerdan boshlaysiz (tayyor audio yoki "g'oya va ssenariy
kerak") → uzunlik (20–30 s) → **10 ta g'oya, raqam bilan tanlash** → ssenariy (ilgak → rivoj → yakun) → ovoz (u
ElevenLabs'da qilgan) → Claude ~1000 kadrni kodda chizib, audio bilan MP4 qiladi (~30 daqiqa). [D 1:39]–[5:03]

Bizning kitga mos qismi — **lemo-opuscar + navoiy uchun boshlang'ich skill** sifatida:
1. Boshlanish nuqtasi → uzunlik → 10 ta g'oya (o'zbekcha tushuntiruvchi, tarixiy hikoya janri yaxshi mos) → tanlash.
2. Ssenariy: ilgak → rivoj → yakun; qatorma-qator "animatsiya yoki faqat subtitr".
3. Navoiy bilan ovoz → **audio uzunligi kadrlar soni va sahna vaqtlarini belgilaydi**.
4. Opuscar render → `sound/` effektlar → quyidagi tekshiruv.

(Uning skill fayli Google Drive'da tarqatilgan — begona fayl, o'rnatmang; g'oyasi yetarli.)

## Topshirishdan oldin tekshiruv

- [ ] 1080×1920, 9:16, H.264 + AAC; uzunlik maqsadga mos; qora yoki qotgan kadr yo'q
- [ ] Ilgak birinchi 1–2 soniyada (natija yoki qiziqish), faqat subtitr yoki bitta kuchli vizual
- [ ] Subtitr hamma gapni qamraydi, ovoz bilan sinxron (so'z vaqtidan ±100 ms), xavfsiz zonada (pastki ~20% va o'ng
      tugmalardan uzoq)
- [ ] O'zbekcha harflar (oʻ, gʻ, tutuq belgisi) to'g'ri chiqadi, imlo xatosi yo'q
- [ ] ~0.4 s dan uzun jimlik va "e-e" yo'q
- [ ] Har muhim qatorda vizual o'zgarish; ~4 s dan uzun statik joy faqat ataylab
- [ ] Har animatsiya o'z qatoriga mos (timeline jadvali bo'yicha), brend palitrasida
- [ ] Ovoz aniq: musiqa ~−20 dB pastda yoki ducking, umumiy ~−14 LUFS, clipping yo'q
- [ ] Effektlar vizual voqealarga tushadi, ovozni bosmaydi
- [ ] AI xatolari yo'q (buzuq matn, qo'llar, logotip, miltillash); oxiri boshiga ulanadi yoki aniq CTA

## Videolarda tilga olingan toollar

| Tool | Nima | Narx | Bizga | Kit bilan ustma-ust |
|---|---|---|---|---|
| HyperFrames (HeyGen) | Claude Code video atrofida motion-grafikani kod bilan yozadi | bepul ko'rinadi | **ko'rib chiqishga arziydi** | lemo-opuscar |
| ElevenLabs | TTS; STT so'z vaqtlari bilan (JSON) | freemium | STT — o'zbekcha aniqligini tekshirish kerak; TTS — Navoiy bor | navoiy |
| Higgsfield (MCP), Seedance, Kling, Nano Banana | rasm/video generatsiya, reframe, upscale | pullik | faqat fotoreal b-roll kerak bo'lsa | reframe |
| DaVinci Resolve Studio + MCP | AI bilan kesish va rang | pullik | Resolve ishlatilsa | EDL engine |
| Submagic | avtomatik subtitr uslublari | pullik | yo'q — ffmpeg/ASS | — |
| Wispr Flow | prompt uchun ovozli diktovka | freemium | qulaylik | — |
| Pinterest | uslub namunalari | bepul | ha | 66 uslub |

## Manbalar

- **B (montaj mantig'i uchun eng yaxshisi):** Joseph — "How to Edit a Viral Talking-Head Using ONLY AI (2026 Style)",
  https://youtu.be/WcMOCtas1pg (kurs va Higgsfield reklamasi; "hech narsaga tegmadim" — ko'rsatilgan qo'lda qadamlarga zid)
- **D:** ReachMora — "I Tried Making a Viral Video Using ONLY Claude AI", https://youtu.be/kDcxEIDC5NA (g'oya sifatida;
  affiliate; render usuli ko'rsatilmagan)
- **C:** Dan Kieft — "Master AI Video Editing in 25 Minutes", https://youtu.be/AgUATWAOaKY (ovoz dizayni, LUT, jimlik;
  Higgsfield homiysi)
- **A:** Dan Kieft — "I Tried AI Video Editing for 8 Days", https://youtu.be/9-iSl83dF34 (HyperFrames va motion turlari)

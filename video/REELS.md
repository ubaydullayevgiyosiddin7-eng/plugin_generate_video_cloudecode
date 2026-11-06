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
- [ ] 1-qator = mavzu + paradoks yoki foyda; 2–3-qatorda qarama-qarshilik so'zi ("Lekin"); 0-kadrdan 3–5 so'zli ekran matni
- [ ] Har gap yakunga olib boradi; kontekstdan keyin qayta ilgak; yakun 1–2 gap va undan ~1 s ichida video tugaydi
- [ ] Faktlar manba bilan tekshirilgan (sana, raqam); mavzuni katta kanal allaqachon qilmagan
- [ ] To'liq renderdan oldin har sahnadan kadr ko'rilgan: kamera obyekt ichiga kirmagan, ranglar to'g'ri, yuz ustida narsa yo'q
- [ ] Grafika va diagrammalar ham (faqat subtitr emas) xavfsiz zonada, yuzni yopmaydi
- [ ] Kamera harakati yumshoq (~20+ kadr), agar keskin kesish ataylab bo'lmasa; har effekt haqiqatan ko'rinadi (biri boshqasini o'chirmagan)
- [ ] Oldingi versiyalar saqlangan (v1, v2...); eksportdan keyin ham loyiha tahrirlanadi

## Claude bilan video: ish oqimlari (2026-11-07)

| # | Nima qilish | Kitga qanday | Manba |
|---|---|---|---|
| 1 | **Har bosqich alohida sessiyada va qotiriladi:** xom klip → qo'pol montaj (so'z vaqtlari) → grafika → 2-o'tish → subtitr → musiqa → eksport. Grafikadan oldin qo'pol montaj qotiriladi — keyin o'zgartirish qiyin | video_tools EDL ish oqimiga "bosqich darvozalari" sifatida | J [2:00]–[4:38], [10:19] |
| 2 | **Faqat o'zgargan bo'lakni qayta render** — to'liq grafika 22 daqiqa, bitta grafikani tuzatish ~3 daqiqa | lemo-opuscar / doska uchun sahna bo'yicha render keshi — qo'shishga arziydi | J [10:19], [12:30] |
| 3 | **9:16 layout shablonlari:** (a) tushuntiruvchi — tepada grafika, pastda yuz, o'rtada subtitr; (b) "TikTok raw" — matnli ilgak + subtitrli xom kesim. Grafika yuzni yopmasin | | J [4:38], [11:42] |
| 4 | **Subtitr mavjud transkriptdan** — so'zlar birma-bir qora fon ustida; qayta transkripsiya yo'q | | J [16:25] |
| 5 | **Fikr → skill sikli:** avval faqat ilgaklarda o'rgatish; vaqt belgisi bilan fikr ("22-soniyada…"); har turdan keyin "o'rganganingni skillga saqla". Bitta ilgakka 8–10 SFX varianti sinalgan | retro → curator agentlarimiz shuni qiladi; opuscar ish oqimiga aniq "skillga saqla" qadami | P [5:36], [9:41]–[11:06], [14:26] |
| 6 | **Isbot b-roll:** Claude brauzerda asl manbani (post, maqola) skrinshot yoki scroll-yozuv qilib, kalit qatorni belgilaydi / kattalashtiradi | playwright-cli bilan; o'zbekcha yangilik tushuntiruvchilari uchun | P [2:43] |
| 7 | Odam ko'rishidan oldin ffmpeg QA: qora kadr, audio-video sinxroni | | P [5:12] |
| 8 | **Namunani o'lchash, fikr so'ramaslik:** ~20 ta namuna short har kadri (30 fps), kontakt varaqlar (2 s = 60 kadr), kamera harakati, kesishlar, yorqinlik/kontrast. **Ogohlantirish:** tool "kamera 80% qimirlamaydi" degan, aslida 65% kadrda sekin harakat bor edi — o'lchov toolini qo'lda tekshirilgan kadr bilan solishtiring | video_tools'ga `ref_analyze` tool — 66 uslubni sozlash uchun | O [0:50]–[3:24], [9:20] |
| 9 | **Avval kichik sinov:** 5 soniyalik ko'rinish testi; videodan oldin stop-kadrlar (uy ichiga kirgan kamera, ko'k daraxtlar, yuz ustidagi zanjir shu yerda topilgan) | | O [4:55], [6:00] |
| 10 | **Parallel agentlar bilan farq tahlili:** 7 agent (rang, chiziq, yorug'lik, tekstura, personaj, chuqurlik, harakat) namuna bilan raqamda solishtiradi; 4 qayta quruvchi agent — **har biri o'z nusxasida va o'z fayllari egasi**: "ishni emas, fayllarni bo'ling" | | O [7:35]–[8:35] |
| 11 | **Avval g'oya, keyin parallel qurish:** ssenariyni berib "animatsiya qayerga?" — faqat g'oya; tanlash; keyin har biriga mustaqil prompt va parallel chatlar. Overlay: fonsiz PNG yoki yashil fon | | S [5:39]–[8:13] |
| 12 | Kamera harakatini nomlang (push in/out, pan, static) — "cinematic" yetmaydi; bitta promptda bitta o'zgarish + "qolgani o'zgarmasin"; 4–10 s kadrlar, butun video emas; tanish vizual til (Vox, Apple liquid glass, hujjatli) | | S [10:50]–[13:14] |
| 13 | **Muharrir brifi kabi prompt:** soniyama-soniya nima bo'ladi, nima qoladi ("glow qolsin"); "nusxa qilib, faqat nusxani o'zgartir"; har versiya raqamlangan holda `renders/` ga | | R [1:50]–[9:05] |

## Ilgak (hook) va ssenariy qoidalari

1. **1-qator mavzuni aniq aytadi** — tomoshabin qolish-ketishni hal qilsin. [K 0:47]–[1:39]; [D 0:00]
2. **Kontekst → burilish so'zi → kutilmagan javob.** Shablon: *"[Mavzu] — aql bovar qilmaydi. [Hayratli fakt]. Lekin
   bu eng qizig'i emas. Eng qizig'i — [burilish]."* ("Lekin", "Biroq", "Ammo".) [K 0:47]–[4:56]
3. **Vizual ilgak:** 0-kadrdan 3–5 ta katta so'z, "yetarlicha" harakat; noto'g'ri o'qib bo'lmaydigan so'zlar (gapirilgandan
   farq qilsa ham). [K 9:32]–[11:30]
4. **Atama emas, foyda yoki og'riq bilan boshlang:** *"Yaxshi uxlamoqchimisiz? Unda magniy kerak."* [K 11:37]
5. **Notanishni tanish narsaga o'rang:** Amir Temur, Navoiy, Chorsu, mashhur futbolchilar. [K 12:37]
6. **Birinchi foyda ~4 soniyada**, kalit raqam birinchi 5 soniyada. [K 13:50]; [D 10:50]
7. **Ilgak gaplari qisqa va keskin**, keyin uzunroq. [K 15:06]
8. **Yordamchi ilgak:** tomoshabin nima o'ylashini taxmin qilib, rad eting — *"Pul kam deb o'ylaysizmi? Yo'q."* Hikoya
   o'zi kuchli bo'lsa, kerak emas. [D 3:47]–[5:31]
9. **3–4-gaplar:** vaqt, joy, minimal kontekst — ortiqcha tushuntirmang. [D 6:11]
10. **Xavf → ishora → kontekstdan keyin qayta ilgak:** *"Xo'sh, bu qanday qilib [X]ga aylandi?"* [D 7:15], [11:20]
11. **Yakun 1–2 gapda, oxirroqda, keyin darhol tugash.** CTA mazmunga bog'liq: *"Boshidan bilgan bo'lsangiz, obuna
    bo'ling."* [D 8:39]–[9:41]
12. **Birinchi gap — paradoks, keyin doimiy burilish iborasi:** *"74 askar temir ko'prikni shunchaki yurib qulatdi.
    Gap shundaki…"*; ikki tomonlama: *"Baxtiga, daryo atigi 60 sm edi. Baxtiga qarshi…"* Namuna kanal ~4 so'z/s
    gapiradi — o'zbek so'zlari uzunroq, so'z emas, bo'g'in/s ni o'lchang. [O 1:45], [4:14]

Qilmang: irqiy provokatsion ilgaklar va "bosish uchun 'firibgarlik' deng" kabi maslahatlar (D videosida bor).

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
| WhisperX / Parakeet | so'z darajasidagi vaqt belgilari | bepul | o'zbekcha aniqligini tekshirib | `../uzbek/` STT, EDL |
| Remotion + rasmiy skillar | kod bilan video, jonli ko'rish | 4+ kishilik tashkilotga pullik litsenziya | faqat litsenziya mos bo'lsa | lemo-opuscar |
| Epidemic Sound (connector) | musiqa va SFX | ~$10/oy | ixtiyoriy | Openverse / Earshot |
| claude-animated-shorts (GitHub) | 3D short skill + 5k namuna | litsenziya ko'rsatilmagan | o'qish uchun, o'rnatmaslik | — |

## Manbalar

- **B (montaj mantig'i uchun eng yaxshisi):** Joseph — "How to Edit a Viral Talking-Head Using ONLY AI (2026 Style)",
  https://youtu.be/WcMOCtas1pg (kurs va Higgsfield reklamasi; "hech narsaga tegmadim" — ko'rsatilgan qo'lda qadamlarga zid)
- **D:** ReachMora — "I Tried Making a Viral Video Using ONLY Claude AI", https://youtu.be/kDcxEIDC5NA (g'oya sifatida;
  affiliate; render usuli ko'rsatilmagan)
- **C:** Dan Kieft — "Master AI Video Editing in 25 Minutes", https://youtu.be/AgUATWAOaKY (ovoz dizayni, LUT, jimlik;
  Higgsfield homiysi)
- **A:** Dan Kieft — "I Tried AI Video Editing for 8 Days", https://youtu.be/9-iSl83dF34 (HyperFrames va motion turlari)

Claude bilan video va ilgaklar (2026-11-07):
- **O (eng puxta):** Mr omi — "How to Make Viral Animated Shorts Using Claude (Full Workflow)", https://youtu.be/OtbLL6OBNE4
  (usulni oling, boshqa kanalning materiallarini emas; Skool reklamasi)
- **J:** Jason Cooperson — "How I Fully Automated My Video Editing (Claude Code)", https://youtu.be/XeTAlZiIWHE
- **P:** Christian Peverelli — "I Fully Automated My Video Editing Using Claude Code", https://youtu.be/HzXD4GVqXwM
- **S (cheklovlar haqida eng halol):** Science Based AI — "How I create viral animated reels using HyperFrames + Claude
  Code", https://youtu.be/y4YupFxhAog (homiy qismi [8:52]–[10:12])
- **K (ilgak uchun eng yaxshisi):** Kallaway — "How to Create Irresistible Hooks", https://youtu.be/LmXpbP7dD48
- **D:** Daniel Bitton Extra — "How To Write A Killer YouTube Shorts Script That Is Impossible To Skip",
  https://youtu.be/vgq14_IqdYM (tuzilishi uchun; ba'zi maslahatlari olinmadi)
- **R (kam foyda):** Roboverse — "Claude Code Can Now Automate Your Videos (Remotion)", https://youtu.be/6_rCyryA6hg

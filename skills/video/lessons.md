# Sinalgan saboqlar

Bu yerda faqat amalda tekshirilgan narsalar turadi. Har bir saboq bitta qator.

## Ovoz (Navoiy)

- Egasining ovozi uchun to'g'ri sozlama: `--emotion warm --speed 1.15`.
- i7-12700 protsessorida 4 soniyalik gap taxminan 26 soniyada chiqadi, model 22 soniyada yuklanadi.
- Model ismlar, qisqartmalar va o'zlashma so'zlarni xato o'qishi mumkin, har bir natijani eshitib tekshirish kerak.

## Film (Opuscar)

- Plugin faqat o'rnatilgandan keyin ochilgan yangi sessiyada ko'rinadi.
- Opuscar dvigateli 1920×1080 uchun yozilgan. Vertikal doskaga `kit/whiteboard-vertical/wb.js` kerak (`setView(w, h)`).
- Yakuniy ovoz balandligi: −14 LUFS.
- `voice/lines.txt` o'zgarsa, `film.js` dagi `s(gap, 0..1)` ga bog'langan chizmalar yangi uzunlikka o'zi moslashadi.

## Telefon ekran yozuvidan reel (video_tools engine)

- Engine `origin/main:video/video_tools` da; `C:\My_poject\video_tools` ga chiqarib, Python 3.11 venv bilan ishladi (librosa shart emas). Diktor ovozini qabul qilmaydi: ovoz alohida qo'shiladi (`films/caravan-kgd-promo/mix.py`).
- Ekran yozuvida tezlashtirilgan bo'lakda `"frame_blend": false` qo'ying, aks holda chat matni ikki qavat bo'lib qoladi.
- Ilova ekranning butun kengligini egallaydi: zoom 1.05 dan oshsa so'zlar chetidan kesiladi. Urg'u `cy` bilan beriladi.
- Baloo2 shriftida kirill harflari yo'q: ruscha subtitr uchun `Rubik[wght].ttf`. Bir qatorga sig'adigan bo'laklar (o'zbekcha ≤ 30 belgi, 48 px), aks holda o'zbekcha plashka ruschasiga kirib ketadi.
- Telegram orqali kelgan yozuv 576×1246 bo'lib qoldi (siqilgan); 1080×1920 da o'qiladi, lekin biroz yumshoq.
- Ovozni gapma-gap alohida chiqarmang: har gap boshqa ohangda chiqib, egasi rad etdi. Butun matn bitta yozuvda, kadrlar ovozga moslanadi.
- ffmpeg grafidagi `asplit` + `sidechaincompress` + `loudnorm` 6 s ovozni jimgina tashlab yubordi, LUFS raqami esa "joyida" edi. Aralashtirishni numpy'da qiling va yakuniy faylda har bir gap borligini tekshiring (`films/caravan-kgd-promo/mix2.py`).
- Navoiy egasining xonada yozilgan `my_ref.wav` bilan bir tekis chiqdi: F0 oralig'i 6.8 yarim ton, Gemini'da 17–19. Egasi ham "intonatsiya yo'q" dedi.
- Qisqartmalarni TTS uchun o'qilishicha yozing: "Ka-ge-de", "E-pe-i".
- Mustaqil QA agenti (kadrlar har 0.5 s + o'lchovlar) men ko'rmagan 13 ta muammoni topdi: eshitilmaydigan musiqa (−22 dB juda past, −11 to'g'ri), shaffof subtitr plashkasi, ikki subtitr ustma-ust, Telegram rasm ochish animatsiyasidagi ikki qavat kadr. Egasiga yuborishdan oldin har doim ishlating.
- Telegram'dagi ruxsat oynasi ("By launching this mini app…") va "Bekor qilindi" kabi kadrlarni kesing: gapga zid ko'rinadi.

## Windows

- `winget` ffmpeg'ni PATH'ga keyin qo'shadi. Render oldidan terminal yangi ochilgan bo'lishi kerak, aks holda: `$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Links;$env:Path"`.

## Sinalgan filmlar

- `ijara_doska_reel.mp4`: Whiteboard Explainer, 9:16, 34.8 s, egasining ovozida.
- `uy_doska_reel_v2.mp4`: 39 s, 1080×1920. Manba: `D:\My_projects\UY\ijara-bot\content\films\ijara-doska`.
- `CaravanTranzit_KGD_reel_v1.mp4`: egasi rad etdi (ohanglar har xil, 6 s jimlik, pauzalar).
- `CaravanTranzit_KGD_reel_v2.mp4`: telefon ekran yozuvi + Gemini 3.1 Flash TTS (Charon, bitta yozuv) + CC0 musiqa va effektlar, faqat ruscha subtitr, 25.9 s, −14.3 LUFS, ikki QA o'tishi. Manba: `films/caravan-kgd-promo` (`make_edl2.py`, `mix2.py`).
- 2026-11-10 (uytop-pitch): iPhone old kamerasi videoni ko'zgudagidek saqlaydi, kiyimdagi yozuv teskari chiqadi. Montajda `hflip` qo'shing va kiyimdagi yozuvga qarab tekshiring.

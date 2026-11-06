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

## Windows

- `winget` ffmpeg'ni PATH'ga keyin qo'shadi. Render oldidan terminal yangi ochilgan bo'lishi kerak, aks holda: `$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Links;$env:Path"`.

## Sinalgan filmlar

- `ijara_doska_reel.mp4`: Whiteboard Explainer, 9:16, 34.8 s, egasining ovozida.
- `uy_doska_reel_v2.mp4`: 39 s, 1080×1920. Manba: `D:\My_projects\UY\ijara-bot\content\films\ijara-doska`.

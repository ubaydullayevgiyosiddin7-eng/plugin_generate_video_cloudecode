# Whiteboard engine — vertikal (9:16) uchun

Kutubxonadagi `styles/whiteboard/demo/engine/wb.js` 1920×1080 ga qattiq bog'langan. Bu nusxa (`wb.js`, MIT, © LemoLab)
o'lchamni `VIEW` ga oladi: Reels/Shorts uchun 1080×1920.

```js
import * as W from './engine/wb.js';
W.setView(1080, 1920);          // new W.Board(...) dan OLDIN
```

`index.html` dagi canvas ham 1080×1920 bo'lsin, render buyruqlariga `--size 1080x1920` qo'shing.
O'zgarishlar: kamera markazi, ink canvas, fon va soya `VIEW` dan; ko'rinmaydigan chiziqlarni kesish
`Math.max(VIEW.w, VIEW.h) * .73 / zoom`. Boshqa hech narsa o'zgarmagan — gorizontal filmlar avvalgidek ishlaydi.

Tayyor misol (Toshkent uylari bot reeli, 39 s, egasining ovozi): ijara-bot repo'sida `content/films/ijara-doska/` (yopiq repo).

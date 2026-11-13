---
name: miniapp-dizayn
description: Telegram Mini App va mobil veb-ilova dizayni. Qamrab oladi "liquid glass" (shisha) uslubini, yorug' va qorong'i rejimni, natija kartalarini, ChatGPT maketini kodga ko'chirishni, telefonda tekshirishni va iPhone/Telegram tuzoqlarini. Bot ichidagi ilova, glassmorphism, ekran dizayni, maketni kodga o'tkazish, ilovada ko'rinish yoki UX muammosi ishlarida shu skill bilan boshlang. Use for Telegram Mini App and mobile web UI work, liquid-glass styling, porting a mock-up into code, and phone-specific rendering issues.
---

# Mini App dizayni

Bu saboqlar egasi bilan 2026-yil noyabrida bitta Telegram Mini App (bojxona statusini tekshirish) ustida birga topilgan. Ular mukammal qoida emas, o'sha loyihaning tajribasi. Mos kelsa ishlating, yaxshiroq yo'l bo'lsa, o'zgartiring va sababini ayting.

## Fikrlash uslubi

- **Sababni tuzating, alomatni emas.** Masalan, "bir xil raqam ikki marta chiqyapti" degan kuzatuvda karta qo'shadigan funksiya raqam ro'yxatda borligini tekshirmas edi. Shu funksiya tuzatildi, ekrandagi ko'rinish yamalmadi.
- **Bir joyni tuzatsangiz, o'xshashini qidiring.** Shu naqsh boshqa ekranda, admin panelda yoki ikkinchi CSS faylda ham bo'lishi mumkin.
- **Kod shishmasin.** Avval token o'zgartiriladi, kerak bo'lsa bitta qoida qo'shiladi, yangi komponent eng oxirgi chora.
- **Har qarorning sababi bitta jumlada aytiladi.** Maketdan chetga chiqilsa, bu ayniqsa muhim.
- **Egasining skrinshotini diqqat bilan o'qing.** Muammo ko'pincha rasmda ko'rinadi, matnda emas.
- **Halol hisobot bering.** Test, namuna rejimidagi surat va jonli tekshiruvdan qaysi biri qilinmaganini ayting.

## Ish tartibi

1. **Maketni HTML sifatida oling.** Egasi maketni ChatGPT bilan chizdiradi. Undan rasm emas, bitta ekranning HTML kodini so'rang (CSS tokenlari bilan). Rasmdan ko'chirish uch marta "o'xshamadi" bilan tugagan, HTML'dan ko'chirish esa birinchi urinishda o'xshagan.
2. **Yangi maketni eskisi bilan solishtiring.** Yangi versiya kelsa, avval ikkala HTML'ning CSS qismini `diff` qiling: nima o'zgargani aniq ko'rinadi.
3. **Qiymatlarni ko'chiring, tuzilishni emas.** Qiymatlar mavjud tokenlarga o'tadi: yorug' rejim `:root` da, qorong'i rejim `:root[data-scheme="dark"]` da.
4. **Yonma-yon surat oling.** Maket, yorug' va qorong'i rejim bitta rasmda yonma-yon bo'lsin. Playwright (`channel="chrome"`), 390 px, dpr 2, birlashtirish PIL bilan. Farqlarni ro'yxat qiling.
5. **Maketni ko'r-ko'rona olmang.** Foydalanishga zarar qiladigan joyini o'zgartiring va sababini ayting. Misollar:
   - 80 px pastki menyu kichik telefonda joy yeydi, 70 px qilingan;
   - katta harfli raqam kiritish maydoni kichraytirilmagan.
6. **Tekshiring:**
   - 360 va 390 px, yorug' va qorong'i rejim;
   - eng uzun til (rus);
   - bo'sh, xato va kutish holatlari;
   - keyin sinov akkaunti bilan jonli Telegram'da.

   Ilovada `?mock=1` rejimi bo'lsin, unda har bir holatni parametr bilan ochish mumkin bo'lsin.
7. **Oxirgi so'z egasiniki.** U telefonda ko'radi.

## Shisha (liquid glass) retsepti

- **Fon:**
  - sahifa rangi va 3–4 ta yumshoq radial yorug'lik: binafsha yuqori o'ngda, oq chapda, lilak o'ngda, binafsha pastda;
  - yorug'lik `body::before` da, `position: fixed`;
  - `body` shaffof bo'lsin, aks holda yorug'lik ko'rinmaydi;
  - yorug'lik tepada sahifa rangiga so'nadi, shunda Telegram sarlavhasi bilan choki bilinmaydi.
- **Blur faqat "xrom"da:** tepa qator, pastki menyu va menyular (`blur(22px) saturate(125%)`). Kartalarda blur yo'q, shunda arzon Android telefonda ham sahifa silliq aylanadi.
- **Xrom:**
  - oq diagonal gradient (125deg) yarim shaffof oq ustida, 1 px oq chet;
  - **ikkinchi ichki chet:** `::before`, `inset: 2px`, `border-radius: inherit`, `pointer-events: none`. Qalin shisha taassurotini aynan shu beradi;
  - ichki yorug'lik `inset 0 -2px 3px` (oq);
  - soya binafsha rangda va pastga tushadi.
- **Kartalar:** yarim shaffof oq, 120deg gradient, `inset 0 0 0 1px` oq hoshiya, yuqori chetda yorug' chiziq, yumshoq binafsha soya.
- **Plitka va chiplar:** oqdan och binafshaga 140deg, ichki yorug'lik. Matni jim rangda bo'lsin: ekrandagi eng baland narsa raqam va status.
- **Asosiy tugma:** 115deg binafsha gradient, oq yarim shaffof hoshiya, ichki yuqori yorug'lik va pastki soya.
- **Qorong'i rejim:** uchun alohida maket kerak, yorug'ni teskari qilish ishlamaydi.
  - kartalar to'q binafsha-kulrang;
  - status to'q rangda, matni oq;
  - raqam plashkasi och rangligicha qoladi.
- **Shisha ishlamaydigan joy:** `@supports not (backdrop-filter)` va `prefers-reduced-transparency` holatida xrom qattiq rangga o'tadi.
- **`color-mix()`:** CSS o'zgaruvchilari ichida ishlatmang. Eski WebView butun qiymatni tashlab yuboradi.
- **Ikki CSS fayl bo'lsa** (ilova va admin panel), tokenlarni ikkalasiga birga qo'llang.

## Telegram va iPhone tuzoqlari

- **Sarlavha rangi:** Telegram sarlavha va fon rangi sahifa rangiga teng bo'lsin. JS'dagi rang CSS'dagi `--page` bilan bitta qiymat.
- **✕ / ⋯ / Back:** bu tugmalarni Telegram chizadi, sahifa ularni o'zgartira olmaydi.
- **`tel:` havolasi:** iPhone'da WebView ichida ochilmaydi. Kichik alohida sahifani `openLink` bilan oching, u o'zi `tel:` ga o'tadi.
- **Rasmni kattalashtirish:** iOS transform qilingan rasmni past aniqlikda chizadi, ayniqsa doimiy `will-change: transform` bilan. Yechim:
  - tinch holatda rasm haqiqiy `width/height/left/top` bilan joylanadi;
  - transform faqat barmoq qimirlayotganda ishlatiladi.
- **Klaviatura:** ochilganda pastki suzuvchi menyu yashirinsin.
- **Botdagi katta rasm:** Telegram `file_id` bilan keshlang, kalit (yo'l, mtime). Shunda rasm har safar qayta yuklanmaydi: birinchi yuborish 23 s dan 0,8 s ga tushgan. Rasmni JPEG 92 qiling.

## Ekran qoidalari (egasi tasdiqlagan)

- **Ortiqcha yozuv yo'q:**
  - har ekranda ortiqcha yozuv va tugma bo'lmasin;
  - rasm aytib turgan narsa matnda takrorlanmaydi;
  - botning chatdagi matni ilovaga ko'chirilmaydi.
- **Manba:** davlat botining asl matni faqat kutilmagan javobda ko'rsatiladi. Oddiy "bor" yoki "yo'q" uchun statusning o'zi yetarli.
- **Natija kartasi:**
  - tepada raqam plashkasi: qatorni egallaydi (eng ko'pi 280 px), raqamlari qalin, haqiqiy raqamga o'xshaydi;
  - uning o'ngida "Saqlangan" yoki "+ Qo'shish";
  - ostida status chizig'i, vaqt shu chiziqning ichida;
  - statusning o'ngida qayta tekshirish plitkasi, status bilan bir balandlikda. Grid'da o'ng ustun qat'iy 88 px, 360 px'da 78 px;
  - kutish paytida plitka ham, chip ham yo'q, status butun qatorni egallaydi.
- **Bitta element, bitta karta:** raqam qayta tekshirilsa yangi karta qo'shilmaydi, mavjudi tepaga chiqadi.
- **Animatsiya:** ishora bo'lsin, plakat emas. Tekshirish sahnasining balandligi ~60 px.
- **Til tanlash:** alohida sahifa emas, tez ochiladigan menyu.
- **Telefon raqamlari:** bosiladigan qatorlar, "Qo'ng'iroq qilish" yozuvisiz.
- **Tor joy:** kalta matn kalitlari kerak (masalan "Saqlangan"). 360 px'da status ikki qatorga tushmasin, rus tilida tushishi mumkin.

## Halollik

- **Keshdagi javob:** o'zining haqiqiy vaqtini ko'rsatadi ("4 daqiqa oldin"), "hozirgina" emas.
- **Imzoli Mini App havolalari:** sinovdan keyin o'chiriladi, chunki ular foydalanuvchi nomidan kiradi.

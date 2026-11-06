# UI/UX: chiroyli va professional interfeys qilish

YouTube videolaridan olingan amaliy saboqlar (2026-11-06; manba va vaqt belgisi har birida). Tavsiya — majburiy emas.
Toollar: [`README.md`](README.md).

## Jarayon (Claude uchun)

```
1. Avval savol: brend, auditoriya, BITTA asosiy harakat (masalan, "qo'ng'iroq band qilish"), bo'limlar,
   /media papkadagi logotip va rasmlar.
2. Tizimni qotirish (DESIGN.md): neytral rang + bitta urg'u rang (hex), 1–2 shrift, spacing shkalasi, radius, soya.
   Emoji-ikonka yo'q, binafsha / ko'k-binafsha gradient yo'q, "glow" dog'lar yo'q.
3. Namuna: skrinshot yoki URL (URL bo'lsa playwright-cli bilan skrinshot). Sifat so'zlari emas, aniq qiymatlar yoziladi.
4. Avval statik tuzilma. Asosiy CTA — birinchi ekrandagi eng kontrast element.
5. Har o'zgarishdan keyin: 375 / 768 / 1440 da skrinshot → DESIGN.md va namuna bilan solishtirish → konsol → tuzatish.
6. Tanqid: design-reviewer agenti (agents/design-reviewer.md) — P0/P1/P2; P0 va P1 tuzatiladi.
7. Harakat (animatsiya) eng oxirida — `animate` skill: hover / focus / submit javobi, yumshoq scroll reveal,
   prefers-reduced-motion. Layout tartibsiz bo'lsa — `better-layout`.
8. Yakun: web-design-guidelines, oxirgi skrinshotlar.
```

## Saboqlar

| # | Nima qilish | Nega | Manba |
|---|---|---|---|
| 1 | **Claude o'z ishini ko'rsin:** har front-end o'zgarishdan keyin sahifani ochib skrinshot, namuna bilan solishtirish, konsol, tuzatish | faqat kod o'qigan model "o'rtacha" UI qiladi; skrinshot uning ko'rish qobiliyatini ishga soladi | C [0:54], [4:23]–[7:37] |
| 2 | Loyiha CLAUDE.md'iga **"Visual development"** bo'limi: design-principles va style-guide fayllariga havola, qabul mezonlari, viewport, konsol tekshiruvi, yangi kutubxona taqiqi | tekshirish sikli har sessiyada o'zi ishlaydi | C [13:50]–[17:05] |
| 3 | **Design-reviewer subagent**: "principal designer" persona, qadamma-qadam ko'rik, P0/P1/P2 hisobot, faqat playwright va Context7 | alohida ko'z — o'z ishini o'zi maqtamaydi | C [18:44]–[25:22] |
| 4 | **Doim vizual namuna**: Dribbble / Awwwards skrinshoti (bir nechtasini birlashtirib) — matnli tavsifdan ancha yaxshi | | A [7:13]–[9:23], D [7:34]–[8:17] |
| 5 | **Avval tizim**: qora, oq va bitta urg'u; aniq hex va shriftlar; dizayn tizimi fayli | | A [5:08], [10:42]; C [28:37] |
| 6 | Prompt oxiriga: **"Bu ishni bajarish uchun kerakli savollarni ber"** | kod yozishdan oldin brend, bo'limlar, stack so'raladi | D [9:55]–[12:53] |
| 7 | **Avval materiallar**: logotip, rasmlar `/media` da | Claude logotipdan brend ranglarini oladi | D [1:38], [12:53] |
| 8 | **Tanqid → tuzatish** sikli (tipografiya, spacing, ierarxiya, accessibility) ball o'smay qolguncha. Claude eng zaif joyi — layout va spacing | | B [4:27], [9:48], [11:32] |
| 9 | **Landing ≠ bosh sahifa**: bitta harakat atrofida; asosiy CTA eng kontrast | qora fonda CTA yo'qolib ketgan misol | B [5:24]; A [5:08] |
| 10 | **AI belgilari**ni tekshirish: emoji-ikonka, binafsha rangga qaytish, glow va gradient dog'lar, pastki bo'limlarda kartalar tekis emas | | A [8:30], [9:23], [10:56] |
| 11 | **Animatsiya — alohida bosqich**, statikdan keyin, maqsadli | mikro-interaksiya ilovada landingdan muhimroq | B [1:49]–[3:36] |
| 12 | Namunadan **aniq qiymatlar** (rang, spacing, shrift) faylga — tasvirni so'z bilan qayta aytmaslik | | B [9:48]–[10:41] |
| 13 | 2–3 variant parallel (git worktree), eng yaxshisini tanlash | | C [26:10]–[27:00] |
| 14 | 3 kenglikda test + interaktiv holatlar (forma yuborish) brauzerda | | C [9:10], [23:42] |

## Aniq raqamlar (tekshirsa bo'ladigan)

| Soha | Qoida | Manba |
|---|---|---|
| Shrift | bitta sans-serif; landingda ≤ 6 o'lcham, dashboardda matn ≤ 24px; katta sarlavha: letter-spacing −2…−3%, line-height 110–120% | E [3:16]–[4:00] |
| Spacing | hamma qiymat 4 ga karrali; guruh ichidagi oraliq guruhlar orasidagidan kichik (yaqinlik qonuni); 12 ustunli grid faqat takrorlanadigan kontentga | E [2:04]–[3:16]; F [4:21] |
| Rang | fon va matn tuslari bitta brend rangidan; qizil = xato, sariq = ogohlantirish, yashil = muvaffaqiyat — faqat ma'no uchun, bezak uchun emas | E [4:55] |
| Soya | past shaffoflik, katta blur; kartada kuchsiz, menyu/popoverda kuchliroq; "soya birinchi ko'zga tashlansa — xato". Dark mode: chuqurlik soya emas, ochroq sirt bilan | E [5:47]–[6:53] |
| Ikonka, tugma | ikonka o'lchami yonidagi matn line-height'iga teng; tugmada gorizontal padding ≈ vertikalning 2 baravari; ikkinchi CTA — ghost tugma | E [6:53] |
| Rasm ustidagi matn | butun rasmga qoramtir qatlam emas — matn ortida chiziqli gradient (ixtiyoriy progressive blur) | E [8:36] |
| Kontent stress-testi | kartaga 60 belgili nom, rasmsiz holat, juda yorqin rasm; uzun matn kesiladi, rasm ustidagi ikonka orqasida doira; kartada faqat ko'z yuguradigan narsa (joy, reyting, narx), qolgani bosilgandan keyin | G [2:42]–[3:22] |

## UX qonunlari — tekshiruv sifatida

- **Doherty:** 400 ms ichida javob yoki ko'rinadigan feedback. [F 0:50]
- **Fitts:** asosiy tugma katta va foydalanuvchi turgan joyga yaqin. [F 1:25]
- **Hick:** tanlov kam; uzun forma — bosqichlarga. [F 2:02]
- **Jakob:** navigatsiya tepada, kontent yuqoridan pastga, chapdan o'ngga — odamlar o'rgangan joyda. [F 2:39]
- **O'xshashlik:** havola oddiy matndan farq qiladi va hamma joyda bir xil. [F 4:38]
- **Postel:** telefon yoki sanani bo'sh joy / chiziqcha bilan ham qabul qilib, o'zi tozalaydi. [F 7:02]
- **Serial position:** eng muhim menyu bandlari boshida va oxirida. [F 7:29]
- **Tesler:** murakkablikni tizim o'z zimmasiga oladi — default qiymatlar, avtoto'ldirish. [F 8:04]
- **Von Restorff:** har bo'limda faqat bitta ajralib turadigan element. [F 8:42]
- **Zeigarnik:** ko'p bosqichli jarayonda progress ko'rsatiladi. [F 9:13]
- Miller (7±2) xotira haqida — menyuga to'g'ridan-to'g'ri qo'llanmaydi. Yaxshiroq manba: lawsofux.com.

## Matn (copy) ham dizayn

- Har ekranda bitta fikr va bitta so'rov. Foydalanuvchining og'rig'idan boshlanadi. [H 16:09]–[20:08]
- Tugma harakatni aytadi: "Birinchi darsni boshlash", "Bepul boshlash" — "Get started" emas.
- Tasavvur qilinadigan aniq gaplar ("poyezdda 5 daqiqa ham hisob"), umumiy AI iboralari yo'q (taqiqlangan so'zlar ro'yxati).

## Boshqa saboqlar

- **Avval foydalanuvchi niyati:** asosiy funksiya (masalan, qidiruv) birinchi, hero rasm va bezak keyin; yangi UI faqat
  ikkinchi niyat paydo bo'lganda. [G 0:26]–[1:27]
- **Harakatning vazifasi bo'lsin:** cheksiz scroll o'rniga "Ko'proq" (footer'ga yetib bo'lsin), scroll-jacking yo'q, har
  harakatga tasdiq (Nusxalash → "Nusxalandi"). [G 3:32]–[4:12]; [E 8:07]
- **"Yaxshila" emas — namunaga nisbatan o'tdi/o'tmadi:** besh marta "yaxshila" desangiz, Claude besh xil sabab topadi.
  Aniq mezon va namuna bilan baholang; butun sahifadan oldin bitta bo'limni sinov sifatida qiling. [H 10:18]–[11:03]
- **Namunani o'sha sohadan** va bir nechtasini aralashtirib oling — nusxa bo'lib qolmasin; shrift va rasm litsenziyasini
  tekshiring. Namuna galereyalari: styles.refero.design, fontsinuse.com. [H 2:40], [15:08], [21:00]

## Manbalar

- **E (raqamlar uchun eng yaxshisi):** Kole Jain — "Every UI/UX Concept Explained in Under 10 Minutes",
  https://youtu.be/EcbgbKtOELY (Mobbin homiy qismi [4:00]–[4:55])
- **F:** Joseph Todaro — "The Laws of UX - 19 Psychological Design Principles", https://youtu.be/fYs2Mdyasuc (2019, ta'riflar)
- **G:** Kole Jain — "How to think like a GENIUS UI/UX designer", https://youtu.be/HE4rLEQpiXY
- **H:** Jack Roberts — "Claude Design Now Builds Beautiful $10,000 Websites", https://youtu.be/VwGrXe2ricE (faqat matn
  bo'limi va o'tdi/o'tmadi g'oyasi; qolgani ko'p reklama, "$10,000" — clickbait)
- **C (eng foydali):** Patrick Ellis — "Turn Claude Code into Your Own INCREDIBLE UI Designer (Playwright MCP Subagents)",
  https://youtu.be/xOO8Wt_i72s (model nomlari eski, usul hozir ham to'g'ri)
- **B:** AI LABS — "Insane Claude Design Skills You Need…", https://youtu.be/Ysr7oNDajJI (skill katalogi; homiy qismi bor)
- **A:** Build Great Products — "How to Build ACTUALLY Beautiful UI With This Claude Code Skill", https://youtu.be/95_NJ-a-CMQ
- **D:** Create a Pro Website — "The EASY way to build a beautiful website with Claude Code", https://youtu.be/fDTwHIKltpc
  (hosting qismi reklama)

## Videolarda tilga olingan skillar (2026-11-07 da tekshirildi)

- ✅ **animate** (emilkowalski/skills, MIT, 54k★, faqat matn) — o'rnatildi: 7-qadam (animatsiya) uchun.
- ✅ **better-layout** (jakubkrehel/skills, MIT, 11k★, faqat matn) — o'rnatildi: layout va spacing uchun.
- 📦 Shu ikki to'plamning qolgan skillari, tastemaker — [`README.md`](README.md) → Dizayn.
- Tekshirilmagan: UI UX Pro Max (npm — begona kod ishga tushiradi), landing-page-design, MengTo skills, designer-skills —
  qisman taste-skill bilan ustma-ust.

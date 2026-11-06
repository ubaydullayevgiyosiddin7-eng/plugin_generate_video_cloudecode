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
7. Harakat (animatsiya) eng oxirida: hover / focus / submit javobi, yumshoq scroll reveal, prefers-reduced-motion.
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

## Manbalar

- **C (eng foydali):** Patrick Ellis — "Turn Claude Code into Your Own INCREDIBLE UI Designer (Playwright MCP Subagents)",
  https://youtu.be/xOO8Wt_i72s (model nomlari eski, usul hozir ham to'g'ri)
- **B:** AI LABS — "Insane Claude Design Skills You Need…", https://youtu.be/Ysr7oNDajJI (skill katalogi; homiy qismi bor)
- **A:** Build Great Products — "How to Build ACTUALLY Beautiful UI With This Claude Code Skill", https://youtu.be/95_NJ-a-CMQ
- **D:** Create a Pro Website — "The EASY way to build a beautiful website with Claude Code", https://youtu.be/fDTwHIKltpc
  (hosting qismi reklama)

## Videolarda tilga olingan, hali tekshirilmagan skillar

Ko'rib chiqish navbatida (o'rnatishdan oldin repo, litsenziya, ichidagi buyruqlar tekshiriladi):

- Emil Kowalski skillari (animate, design-engineering) — animatsiya; bizda bu bo'shliq
- jakubkrehel skillari (review, layout) — pikselgacha layout tuzatish
- tastemaker (codeswithroh) — namunadan aniq qiymatlarni skript bilan olish
- UI UX Pro Max (npm), landing-page-design, MengTo skills, designer-skills — qisman taste-skill bilan ustma-ust

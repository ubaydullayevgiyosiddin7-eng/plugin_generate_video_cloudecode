# Xakaton

Maqsad: Claude topshiriqni, talablarni va baholash mezonlarini to'liq hisobga olib, **hamma talab bajarilgan, sodda lekin
professional** yechim qilsin, va bu har safar takrorlansin.

## Hozir ishlaydigan tartib (o'rnatilgan toollar bilan)

1. **Topshiriqni o'qish.** Fayl Word / PDF / PowerPoint bo'lsa: `markitdown topshiriq.docx > topshiriq.md`. So'ng
   talablar jadvali: har bir talab → qanday bajaramiz → demoda qayerda ko'rinadi; baholash mezonlari ball bo'yicha
   tartibda. Jadval qurishdan oldin hech narsa yozilmaydi.
2. **Dizayn yo'nalishi.** Sayt / landing → `design-taste-frontend` (taste-skill). Ilova interfeysi (dashboard, CRM,
   panel) → [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) dan o'xshash mahsulotning `DESIGN.md` i.
   Ikkalasida ham: sodda, bitta rang tizimi, ortiqcha effekt yo'q.
3. **Qurish.** Avval eng muhim mezonni yopadigan ishlaydigan versiya, keyin qolgani. Erta deploy.
4. **Tekshirish — har topshirishdan oldin.** `playwright-cli` bilan 390 / 768 / 1440 kenglikda skrinshot, `console` da
   xato yo'q, har bir tugma va forma bosib ko'riladi; so'ng `web-design-guidelines` bilan tekshiruv. Talablar jadvalidagi
   har bir qator demoda ko'rinishini qayta tekshir.
5. **Topshirish.** Havola inkognitoda ochiladi, README'da skrinshot, repo ochiq.

Qolgan resurslar va qachon olinishi: [`../RESOURCES.md`](../RESOURCES.md).

## Tuzilish

| Papka | Nima turadi | Holat |
|---|---|---|
| [`PLAYBOOK.md`](PLAYBOOK.md) | hakamlar qanday baholaydi, 10 qoida, 24 soatlik reja, pitch, topshirish cheklisti | tayyor |
| [`skills/hackathon/`](skills/hackathon/SKILL.md) | Claude "xakaton" deganda o'zi ishga tushiradigan skill: brief → SPEC → qurish → tekshirish → pitch | tayyor, `~/.claude/skills/` ga o'rnatilgan |
| [`agents/spec-reviewer.md`](agents/spec-reviewer.md) | "hakam" agenti: har bir talab va mezonni tekshiradi, ball qo'yadi, top-5 tuzatish | tayyor (loyihaning `.claude/agents/` ga) |
| [`templates/`](templates/) | `SPEC.md` (talablar jadvali, demo ssenariysi), `CLAUDE.md` (loyiha qoidalari), `settings.json` (typecheck o'tmasa to'xtatmaydi, `.env` ni o'qitmaydi) | tayyor |
| [`cases/`](cases/) | o'tgan xakatonlar: topshiriq, mezonlar, nima qildik, nima ishladi | birinchisini to'ldirish kerak |

## Reja

1. **Topshiriq tahlili.** Topshiriq + mezonlar → talablar jadvali (talab → qanday bajaramiz → demoda qayerda ko'rinadi),
   mezonlar ball bo'yicha tartibda, yashirin talablar, MVP chegarasi.
2. **Hakam agenti.** Rubrika bo'yicha ball, kamchiliklar ro'yxati.
3. **Qurish qoidalari.** Ishonchli stack, "sodda lekin professional" dizayn, ishlamaydigan tugma yo'q, telefonda tekshirish,
   erta deploy.
4. **Vaqt rejasi.** 24/48 soatga soatma-soat, "feature freeze" vaqti.
5. **Pitch va demo.** Slayd tuzilishi, demo ssenariysi, savollarga tayyorgarlik; demo videoni `video/` bilan.
6. **Topshirish cheklisti.** Havola inkognitoda ochiladi, repo ochiq, README'da skrinshot, video yuklangan.
7. **Retro.** Har xakatondan keyin `cases/` ga yangi fayl.

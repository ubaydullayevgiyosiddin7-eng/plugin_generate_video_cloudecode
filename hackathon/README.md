# Xakaton

Maqsad: Claude topshiriqni, talablarni va baholash mezonlarini to'liq hisobga olib, **hamma talab bajarilgan, sodda lekin
professional** yechim qilsin, va bu har safar takrorlansin.

## Tuzilish

| Papka | Nima turadi | Holat |
|---|---|---|
| [`cases/`](cases/) | o'tgan xakatonlar: topshiriq, mezonlar, nima qildik, nima ishladi. Skillar shu haqiqiy tajribadan quriladi | birinchisini to'ldirish kerak |
| `skills/` | topshiriq tahlili (talablar jadvali), qurish qoidalari, pitch, topshirish cheklisti | rejada |
| `agents/` | "hakam" agenti — topshirishdan oldin rubrika bo'yicha ball qo'yadi | rejada |
| `templates/` | xakaton loyihasi uchun `CLAUDE.md` shabloni, pitch tuzilishi, README shabloni | rejada |

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

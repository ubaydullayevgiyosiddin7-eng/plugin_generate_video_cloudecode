# UZEX AI Hackathon 2026 · 2026-11-05 · saralash

## Natija
511 jamoa ro'yxatdan o'tdi, saralashdan 20 tasi o'tdi — biz **1-o'rinda**. Final: 7–8-noyabr, Toshkent, oflayn, 09:00 dan.
Topshiriq sahifasi: https://hackathon.uzex.uz/saralash/

## Topshiriq
Birja bitimlari haqidagi savollarga **rus va o'zbek tillarida**, aniq va **faqat ma'lumot asosida** javob beradigan AI-agent —
Telegram-bot yoki veb-servis. Javobda aniq raqamlar, nomlar, kodlar. Ma'lumotda javob bo'lmasa — agent buni ochiq aytadi,
o'ylab topmaydi. Yondashuv erkin, istalgan LLM va AI-yordamchidan foydalanish mumkin.

Ma'lumot (hamma jamoaga bir xil): 500 000 bitim, spot.uzex.uz formatida, 2022-yanvar — 2026-oktabr; bitimlar reyestri,
shartnoma kartochkalari, savdo ishtirokchilari, brokerlar, dollar kursi; har maydon RU/UZ tavsifli README. Kompaniyalar,
STIR va summalar o'ylab topilgan.

## Baholash mezonlari
| Mezon | Ball | Biz nimasi bilan yutdik |
|---|---|---|
| To'g'ri javoblar | 60 (10 savol × 6) | Text-to-SQL + DuckDB: raqamni model emas, baza beradi; har javobdagi raqam, sana va nom SQL natijasi bilan kodda solishtiriladi — tasdiqlanmagan javob chiqmaydi |
| Prototip sifati | 20 | "javob nimaga asoslangani ko'rinadi" → har javob yonida **dalil paneli**: bajarilgan SQL, qaytgan qatorlar, "3/3 tekshiruv o'tdi", nazorat raqamli "javob tasdiqnomasi"; UZ/RU tugmasi; o'rtacha ~12–13 s |
| Yechim tavsifi | 20 | saytning o'zida "Qanday ishlaydi": tushunadi → nomlarni topadi → SQL bilan hisoblaydi → kod bilan tekshiradi → dalili bilan ko'rsatadi; texnologiyalar ro'yxati |

## Cheklovlar
- Bir kecha (prototip 5-noyabr 18:00 gacha), jamoa ≤ 3 kishi.
- Komissiya 10 ta oldindan e'lon qilinmagan savol beradi (RU yoki UZ), har javobga ≤ 90 soniya.
- **Agent javob o'ylab topsa — jamoa saralashdan chiqadi.**
- Prototip o'rnatish va ro'yxatdan o'tishsiz ishlashi, doim ishlab turishi kerak.

## Nima qildik
- **Yechim:** DoppiX — veb-servis. "Birja bitimlari haqida isbotli javoblar."
- **Stack:** Claude Opus 5.5 (text-to-SQL agent) · DuckDB (faqat o'qish rejimida) · Polars · RapidFuzz + translit
  (kompaniya / tovar / hudud lotin yoki kirillda bo'lsa ham bazaga moslanadi, ishonchsiz moslik qabul qilinmaydi) ·
  deterministik verifikator · mustaqil imtihon (o'z savollarimiz bilan sinov).
- **Dizayn:** sodda — bitta katta sarlavha, bitta savol maydoni; ostida **atlas (ikat) matosi** — har ipi bitta savdo
  kuni, ipni bosing — o'sha kun raqamlari. Milliy, esda qoladigan, lekin ma'lumotdan yasalgan. Telefonda ham to'g'ri.
- **Javob ekrani:** katta natija raqami + bir gaplik izoh + "hisobga olinganlar" (masalan: bekor qilinganlarsiz haqiqiy
  bitimlar alohida) + "davom ettirish" savollari; o'ngda tasdiqnoma: nazorat raqami, vaqt, tekshiruvlar, SQL va qatorlar.

## Nima ishladi (2026-11-07 da saytni ko'rib chiqib)
- **Asosiy talabni (o'ylab topmaslik) arxitektura bilan yopish:** model hech qachon raqamni o'zi aytmaydi — SQL yozadi;
  kod har raqamni natija bilan solishtiradi. Ya'ni eng xavfli mezon (diskvalifikatsiya) qoida emas, tizim bilan himoyalangan.
- **Mezon matnini so'zma-so'z UI ga aylantirish:** "javob nimaga asoslangani ko'rinadi" → dalil paneli va tasdiqnoma.
  Komissiya izlagan narsani qidirib o'tirmaydi — ko'zi oldida.
- **Ikki son berish** (reyestrdagi barcha va haqiqiy bitimlar) — noaniq savolga ham to'g'ri javob.
- **Sodda, lekin bitta "wow"**: bitta savol maydoni + ma'lumotdan to'qilgan atlas. Ortiqcha ekran yo'q.
- Tezlik: ~12 s, 90 s chegaradan ancha past. Konsolda xato yo'q.

## Nima ishlamadi / keyingi safar boshqacha
- (jamoa to'ldiradi)

## Claude'ga qanday ko'rsatma berdik
- (jamoa to'ldiradi: eng foydali promptlar, qoidalar)

## Finalga saboq
1. Har mezonni ko'rinadigan UI elementiga aylantiring — hakam izlamasin.
2. Eng og'ir jazoli qoidani (bu yerda: o'ylab topish) promptga emas, kodga topshiring.
3. Bitta milliy / esda qoladigan vizual, qolgani sodda.
4. Yechim tavsifini saytning o'ziga qo'ying — 20 ballik mezon.

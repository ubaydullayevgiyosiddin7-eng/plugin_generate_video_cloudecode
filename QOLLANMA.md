# Umumiy qo'llanma: nima qayerda va qanday tanlash

Bu xarita, buyruq emas. Har bir bo'limda toollar xususiyati va "qachon mos" bilan yozilgan; vaziyatga qarab Claude yoki
egasi o'zi tanlaydi. Topshiriq, mijoz yoki egasi boshqacha desa — o'sha ustun.

Holat belgilari (hamma bo'limda bir xil): ✅ o'rnatilgan · 🔑 egasi qo'shadi (sozlama yoki akkaunt kerak) ·
📦 kerak bo'lganda olinadi · ⛔ ishlatilmaydi (sababi yozilgan)

## Bo'limlar

| Bo'lim | Nima uchun | Asosiy narsalar |
|---|---|---|
| [`web/`](web/README.md) | sayt, landing, ilova interfeysi, backend, deploy | ✅ taste-skill (dizayn) · ✅ playwright-cli + web-design-guidelines (tekshirish) · 🔑 Supabase, Vercel, Railway · loyiha shablonlari |
| [`video/`](video/README.md) | animatsion video, montaj, ovoz, effektlar | lemo-opuscar · navoiy (o'zbekcha ovoz) · sound (effektlar) · video_tools (telefon videolaridan film) |
| [`documents/`](documents/README.md) | fayllarni o'qish va yaratish | ✅ markitdown · ✅ docx/pdf/pptx/xlsx skillari |
| [`automation/`](automation/README.md) | Telegram botlar, avtomatlashtirish, ma'lumot yig'ish | aiogram + Context7 · telegram-reader · n8n, ScrapeGraph |
| [`uzbek/`](uzbek/README.md) | loyiha o'zbek tilida ishlashi kerak bo'lsa | STT/TTS, LLM reytingi, lotin↔kirill, Click/Payme, Eskiz, xaritalar |
| [`claude-code/`](claude-code/README.md) | Claude bilan har qanday ishda | ishlash usullari, 🔑 Context7, yangi narsa topish joylari, ishlatilmaydiganlar |
| [`hackathon/`](hackathon/README.md) | xakaton, tanlov, saralash | playbook, ✅ hackathon skill, hakam agenti — qurish uchun yuqoridagi bo'limlarga yo'naltiradi |

Umumiy toollar va tokenlar repoda emas: `C:\My_poject\tools\` (telegram-reader, `secrets\.env`).

## Qanday tanlash

1. **Ish turini aniqlang** → mos bo'lim. Bir nechta tur bo'lsa (masalan, o'zbekcha bot + sayt) — har biri o'z bo'limidan.
2. **Bo'lim ichida "Qachon mos" ustuniga qarang.** Bir xil vazifani bajaradigan ikki narsa bo'lsa, bo'lim oxiridagi
   "Tanlash" qatori farqini aytadi (masalan: sotadigan sahifa → taste-skill, ishlatiladigan ekran → DESIGN.md).
3. **✅ bor bo'lsa — o'shani.** 📦 ni faqat haqiqatan kerak bo'lganda va faqat o'sha loyihada oling: har bir skill har
   sessiyada joy egallaydi. 🔑 ni Claude o'zi o'rnatmaydi — egasiga buyruqni aytadi.
4. **Natijani tekshiring:** web uchun playwright-cli + web-design-guidelines; ovoz uchun raqam (LUFS, ASR); hammasida
   "tayyor" faqat dalil bilan.
5. **Yangi narsa topilsa:** [`claude-code/`](claude-code/README.md) dagi tekshirish tartibi → mos bo'lim jadvaliga qator.

## Tez yo'naltirgich

| Vaziyat | Qayerga qarash |
|---|---|
| "Sayt qilib ber" / landing / kompaniya sayti | `web/` → Dizayn → taste-skill |
| Dashboard, CRM, admin panel | `web/` → Dizayn → awesome-design-md |
| Sayt tayyor, topshirishdan oldin | `web/` → Tekshirish |
| Topshiriq / TZ Word yoki PDF da keldi | `documents/` → markitdown |
| Taqdimot yoki hisobot fayli kerak | `documents/` → pptx / docx |
| Animatsion yoki tushuntiruvchi reel | `video/` → lemo-opuscar |
| Telefon videolaridan film | `video/` → video_tools |
| O'zbekcha ovoz, nutqni tanish, to'lov, SMS | `uzbek/` |
| Telegram bot | `automation/` + `uzbek/` (to'lov) |
| Kutubxona yangi versiyasi, eskirgan kod xavfi | `claude-code/` → Context7 |
| Xakaton | `hackathon/` (jarayon) + yuqoridagilar (qurish) |

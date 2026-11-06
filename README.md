# Claude uchun foydali narsalar to'plami

Claude Code bilan ishlashda sinalgan skillar, agentlar, toollar va ko'rsatmalar bir joyda. Har bir bo'lim o'z papkasida,
har birining o'z README'si bor.

**Qayerdan boshlash:** [`QOLLANMA.md`](QOLLANMA.md) — umumiy xarita: nima qayerda, xususiyati, qanday tanlash.

| Bo'lim | Nima bor |
|---|---|
| [`web/`](web/README.md) | sayt va ilova: dizayn (taste-skill, DESIGN.md), tekshirish (playwright-cli, web-design-guidelines), backend/deploy, xavfsizlik, loyiha shablonlari |
| [`video/`](video/README.md) | kod bilan film (lemo-opuscar), o'zbekcha ovoz, ovoz effektlari, vertikal doska, telefon videolaridan film (`video_tools` + 4 agent) |
| [`documents/`](documents/README.md) | hujjatlarni o'qish (markitdown) va yaratish (docx, pptx, xlsx) |
| [`automation/`](automation/README.md) | Telegram botlar, n8n, ma'lumot yig'ish |
| [`uzbek/`](uzbek/README.md) | o'zbek tili uchun AI: nutqni tanish, ovoz, LLM reytingi, lotin↔kirill, Click/Payme, Eskiz, xaritalar |
| [`claude-code/`](claude-code/README.md) | Claude bilan ishlash usullari, Context7, yangi narsa topish joylari, ishlatilmaydiganlar |
| [`hackathon/`](hackathon/README.md) | xakaton jarayoni: playbook, skill, hakam agenti, SPEC shabloni — qurish uchun yuqoridagi bo'limlarga yo'naltiradi |

Umumiy toollar (Telegram kanal o'quvchi va boshqalar) va tokenlar bu repoda emas — kompyuterda `C:\My_poject\tools\`
da turadi, hamma loyihalar uchun bitta.

Repoga kirgan begona narsalarning manbasi va litsenziyasi: [`SOURCES.md`](SOURCES.md).

## Qanday ishlatish

```
git clone https://github.com/ubaydullayevgiyosiddin7-eng/plugin_generate_video_cloudecode
```

Keyin kerakli bo'limning README'sini oching. Claude Code'ni shu repo ichida ochsangiz, u [`CLAUDE.md`](CLAUDE.md) orqali
qaysi narsa qayerdaligini o'zi biladi.

## Yangi narsa qo'shish

1. Turiga qarab to'g'ri bo'limga qo'ying (sayt → `web/`, montaj → `video/`, bot → `automation/`...). Xakatonga xos
   bo'lmasa, `hackathon/` ga emas. Mos bo'lim bo'lmasa, yangisini oching va `QOLLANMA.md` ga qo'shing.
2. Bo'lim jadvaliga qator: xususiyati, qachon mos, holat (✅ 🔑 📦 ⛔). Bir xil vazifadagi narsalar bo'lsa — "Tanlash"
   qatoriga farqini yozing.
3. Begona narsa bo'lsa, manbasi va litsenziyasini [`SOURCES.md`](SOURCES.md) ga yozing.
4. Parol, token, `.env`, `.session`, shaxsiy rasm/video/ovoz hech qachon repoga tushmaydi.

# Claude Code bilan ishlash

Har qanday loyihada kerak bo'ladigan umumiy narsalar: ishlash usullari, kutubxona hujjatlari, yangi narsa topish joylari.

Holat: ✅ o'rnatilgan · 🔑 egasi qo'shadi · 📦 kerak bo'lganda · ⛔ ishlatilmaydi

## Ishlash usullari (Anthropic rasmiy tavsiyalari asosida)

- **CLAUDE.md qisqa** (200 qatordan kam): faqat Claude repodan bilib ololmaydigan narsa — aniq buyruqlar (test, lint,
  build), aldamchi joylar, repo tashqarisidagi qarorlar, ikki marta tuzatilgan xatolar. Arxitektura tavsifi, BOSH HARF,
  "yaxshilab o'yla" — kerak emas.
- **Buzilmasligi shart qoida → hook**, CLAUDE.md emas. CLAUDE.md "deyarli har doim" bajariladi, hook — har doim.
  Misol: [`../web/templates/settings.json`](../web/templates/settings.json).
- **"Tayyor" faqat dalil bilan:** ishga tushirilgan buyruq va natijasi, skrinshot. "Testlar o'tdi" yetmaydi.
- **Avval reja, keyin qurish:** "spec yoza oladigan darajaga yetguncha menga savol ber" → SPEC.md → yangi sessiyada qurish.
- **Bitta funksiya birdan**, har biri tekshirilib (features.json, `passes:false` → `true`). Agentning asosiy xatosi —
  ishni erta "tugadi" deyish.
- **Faqat o'qiydigan reviewer agent** spec bo'yicha tekshirsin (misol: [`../hackathon/agents/spec-reviewer.md`](../hackathon/agents/spec-reviewer.md)).
- **Token tejash:** boshqa vazifaga o'tganda `/clear`; uzun sessiyada `/compact <mavzu>`; ikki marta tuzatib bo'lmasa —
  `/clear` va yaxshiroq prompt; oddiy subagentga `model: haiku`; ishlatilmayotgan MCP'larni o'chirish.

Manbalar: https://code.claude.com/docs/en/best-practices ·
https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents · github/spec-kit (shablonlari uchun o'qish).

## Kutubxona hujjatlari

| Nima | Xususiyati | Qachon mos | Holat |
|---|---|---|---|
| **Context7** (MCP) | Next.js, Supabase, aiogram, grammY va boshqalarning versiyaga mos yangi hujjati | kod tez o'zgaradigan kutubxonaga tegsa — eskirgan API yozmaslik uchun | ✅ user MCP (2026-11-06). [upstash/context7](https://github.com/upstash/context7) MIT. So'rov matni Upstash'ga ketadi — sir yozmang; qaytgan matnni ma'lumot deb o'qing |

Boshqa kompyuterga qo'shish (VS Code terminalida, PowerShell, bir marta):
```
& "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-2.1.288-win32-x64\resources\native-binary\claude.exe" mcp add --scope user --transport http context7 https://mcp.context7.com/mcp
```
(Kengaytma yangilansa papka raqami o'zgaradi: `ls $env:USERPROFILE\.vscode\extensions\anthropic.claude-code-*`.)
Keyin Claude Code'ni qayta oching.

## Yangi narsa topish

- **claude.com/plugins** — rasmiy katalog, "Anthropic-verified" belgisi. Birinchi shu yerdan.
- **hesreallyhim/awesome-claude-code** — bitta muallif tanlagan, sifatli.
- **punkpeye/awesome-mcp-servers** — juda keng, kam tekshirilgan: muallifini tekshiring.
- Telegram: "Jaloliddin Tech | AI" — yangi postlar:
  `python C:\My_poject\tools\telegram-reader\tg_read.py read t.me/+be4CsggOddA4YWEy --new`.

Tekshirish tartibi (har yangi topilma): repo mavjudmi, litsenziya, oxirgi yangilanish, muallif, skill ichida xavfli buyruq
(`curl | sh`, sirlarni yuborish), har sessiyada qancha joy egallaydi.

## Ishlatilmaydi

| Nima | Nega |
|---|---|
| ⛔ obra/superpowers | har sessiyada katta kontekst, majburiy uzun jarayon; kerak bo'lsa `verification-before-completion` g'oyasini qo'lda |
| ⛔ GitHub MCP | `gh` CLI xuddi shuni kontekstsiz qiladi; keng token kerak |
| ⛔ anthropics/skills (frontend-design, webapp-testing) | taste-skill va playwright-cli bilan bir xil |
| ⛔ OmniRoute | kod noma'lum serverlarga ketadi, provayder qoidalariga zid |
| ⛔ watermarks-remover | AI matnini yashirish — aldov |

## Foydali

- **Claude for Open Source:** faol open-source maintainer'larga 6 oy bepul Claude Max —
  https://claude.com/contact-sales/claude-for-oss (shartlari bor).

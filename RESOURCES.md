# Topilgan resurslar: nima, qachon, o'rnatilganmi

Har bir narsa ko'rib chiqilgan (repo mavjud, litsenziya, skill ichida xavfli buyruq yo'q). "Qachon" ustuni — Claude
qaysi birini tanlashi uchun. Qisqa jadval global `~/.claude/CLAUDE.md` da ham bor.

Yangi narsa qo'shilsa: shu jadvalga qator, holat va sana bilan.

## O'rnatilgan (2026-11-06)

| Nima | Qachon ishlatiladi | Qanday o'rnatilgan | Manba |
|---|---|---|---|
| **taste-skill** (`design-taste-frontend`) | kompaniya / mahsulot / landing / kafe / SaaS sayti qurish yoki "AI qilgandek" ko'rinadigan saytni tuzatish | `~/.claude/skills/design-taste-frontend/` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) · MIT · 111k★ |
| **web-design-guidelines** | tayyor UI ni topshirishdan oldin tekshirish (accessibility, UX qoidalari) | `~/.claude/skills/web-design-guidelines/` — qoidalarni har safar Vercel repo'sidan oladi | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) · 34k★ |
| **playwright-cli** | Claude o'zi brauzer ochib saytni tekshiradi: skrinshot, konsol xatolari, tugmalar, formalar, telefon kengligi | `npm i -g @playwright/cli` + `~/.claude/skills/playwright-cli/` | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) · Apache-2.0 |
| **markitdown** | topshiriq yoki hujjat Word / PowerPoint / Excel / katta PDF bo'lsa — avval Markdown'ga, tokenni tejaydi | `pip install "markitdown[pdf,docx,pptx,xlsx]"` | [microsoft/markitdown](https://github.com/microsoft/markitdown) · MIT · 194k★ |

## O'rnatilmagan, lekin kerak bo'lganda olinadi

| Nima | Qachon | Nega hozir o'rnatilmagan | O'rnatish |
|---|---|---|---|
| **awesome-design-md** | ilova interfeysi (dashboard, CRM, admin) uchun tayyor dizayn tizimi: Linear, Stripe, Vercel, Apple... uslubidagi `DESIGN.md` | o'rnatiladigan narsa emas — kerakli bitta faylni loyihaga ko'chirasiz | [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) · MIT |
| **replica-skill** | mavjud ilovaning funksiyalarini tez qayta qurish: tahlil → arxitektura → qurish → test → deploy | 11 ta skill har sessiyada joy egallaydi; xakatonda prototip kerak bo'lsa o'sha loyihaga | `/plugin marketplace add Jakeschincariol/replica-skill` · [repo](https://github.com/Jakeschincariol/replica-skill) · MIT |
| **knowledge-work-plugins** (Anthropic) | spetsifikatsiya, roadmap (product-management), marketing rejasi, sales, data/SQL — pitch va hujjatlar uchun | katta to'plam; kerakli bittasini olish kerak | `/plugin marketplace add anthropics/knowledge-work-plugins` → `/plugin install product-management@knowledge-work-plugins` · Apache-2.0 |
| **youtube-agent-skill** | YouTube: ssenariy (21 hook formulasi), sarlavha + thumbnail, Shorts kesish, SEO, kanal auditi | hozir asosiy ish Instagram reels | [Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) · MIT |
| **ScrapeGraph-ai** | saytlardan ma'lumot yig'ish (LLM bilan) | aniq vazifa yo'q | [ScrapeGraphAI/Scrapegraph-ai](https://github.com/ScrapeGraphAI/Scrapegraph-ai) · MIT |
| **DaVinci Resolve MCP** | Claude bilan DaVinci'da montaj | pullik DaVinci kerak | qo'llanma: "Jaloliddin Tech" kanali #86 (PDF) |
| **Clipwing real-sfx** | kadrga mos ovoz effekti | `video/sound` dagi Earshot real-sound bilan bir xil vazifa; 81★, litsenziyasi yo'q | [Clipwing/skills](https://github.com/Clipwing/skills) |
| **LTX-2.5** | lokal video generatsiya | NVIDIA videokarta + 70 GB kerak; bu kompyuterga to'g'ri kelmaydi | [Lightricks/LTX-2](https://github.com/Lightricks/LTX-2) · kod Apache-2.0, model o'z litsenziyasi bilan |

## Ishlatilmaydi

| Nima | Nega |
|---|---|
| OmniRoute | Claude Code'ni 150 ta bepul provayder orqali o'tkazadi: kod noma'lum serverlarga ketadi, bepul tariflarni birlashtirish provayderlar qoidalariga zid |
| watermarks-remover | AI yozgan matnni yashirish va detektorlardan o'tish — xakaton, o'qish va ishda aldov |
| CapCut "skill" (tiktokcdn'dagi SKILL.md) | ChatGPT uchun; noma'lum CDN'dagi ko'rsatmani "aynan bajar" deyiladi |

## Foydali ma'lumot

- **Claude for Open Source:** faol open-source maintainer'larga 6 oy bepul Claude Max. Ariza:
  https://claude.com/contact-sales/claude-for-oss (shartlarini o'qing, hammaga berilmaydi).

## Manbalar

- Telegram: "Jaloliddin Tech | AI" (yopiq, `t.me/+be4CsggOddA4YWEy`) — 2026-11-06 da 90 ta post ko'rib chiqildi.
  Yangi postlar: `python C:\My_poject\tools\telegram-reader\tg_read.py read t.me/+be4CsggOddA4YWEy --new`.

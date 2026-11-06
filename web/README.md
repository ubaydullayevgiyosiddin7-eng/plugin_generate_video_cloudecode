# Web: sayt va ilova qurish

Sayt, landing, ilova interfeysi, backend, deploy. Xakaton, mijoz ishi yoki o'z loyihasi — farqi yo'q.

Holat: ✅ o'rnatilgan · 🔑 egasi qo'shadi (sozlama yoki akkaunt kerak) · 📦 kerak bo'lganda olinadi · ⛔ ishlatilmaydi

**Chiroyli UI jarayoni va saboqlar:** [`UI-UX.md`](UI-UX.md) (YouTube'dagi amaliyotchilardan) ·
**Dizayn tanqidchisi agenti:** [`agents/design-reviewer.md`](agents/design-reviewer.md) (loyihaning `.claude/agents/` iga).

## Dizayn

| Nima | Xususiyati | Qachon mos | Holat |
|---|---|---|---|
| **taste-skill** (`design-taste-frontend`) | figma.com / x.ai darajasidagi kompaniya sayti; haqiqiy rasmlar, bitta tizim, "AI qilgandek" ko'rinmaydi; brauzerda o'zi tekshiradi. Qoidalari qat'iy: bir bo'lim = bir ekran, rasm ostida izoh yo'q | kompaniya, mahsulot, landing, kafe, SaaS sayti; "sayt shablonga o'xshaydi" degan holat | ✅ `~/.claude/skills/design-taste-frontend` · [repo](https://github.com/Leonxlnx/taste-skill) MIT |
| **awesome-design-md** | Linear, Stripe, Vercel, Apple... uslubidagi tayyor `DESIGN.md` (ranglar, shrift, tugmalar); loyihaga bitta fayl qo'yiladi | ilova interfeysi: dashboard, CRM, admin, bot paneli — bu yerda taste-skill qoidalari to'g'ri kelmaydi | 📦 [repo](https://github.com/VoltAgent/awesome-design-md) MIT |

| **better-layout** (jakubkrehel) | guruhlash, tekislash, o'qish tartibi, responsive tuzilma; o'lcham o'zgarsa, tarjima uzunroq bo'lsa (o'zbekcha!) yoki RTL da buzilmasligini sinaydi. Claude'ning eng zaif joyi — layout | sahifa "tartibsiz" ko'rinsa, kartalar tekis emas, telefon/tarjimada buziladi | ✅ `~/.claude/skills/better-layout` (2026-11-07) · [repo](https://github.com/jakubkrehel/skills) MIT 11k★ |
| **animate** (Emil Kowalski) | animatsiyani to'g'ri tartibda quradi: kerakmi → maqsad → tool → xususiyat → egri chiziq va davomiylik → to'xtatilishi → chiqishi | hover, o'tish, "jonli" komponent kerak bo'lganda; animatsiya — alohida, oxirgi bosqich | ✅ `~/.claude/skills/animate` (2026-11-07) · [repo](https://github.com/emilkowalski/skills) MIT 54k★ |
| Emil Kowalski / jakubkrehel qolgan skillari (improve-animations, apple-design, interface-review, better-typography, better-colors...) | animatsiya auditi, tipografiya, ranglar, branch ko'rigi | kerak bo'lsa bittadan | 📦 hammasi faqat matn, MIT; har biri sessiyada joy egallagani uchun hammasi olinmagan; interface-review ≈ bizning design-reviewer |
| tastemaker (codeswithroh) | namunadan aniq qiymatlarni skript bilan oladi, doimiy "did" fayli | namuna asosida aniq nusxa kerak bo'lsa | 📦 526★ MIT, 33 skript — taste-skill + UI-UX jarayoni bilan ustma-ust |

Tanlash: **sotadigan sahifa** (odamga nima sotilishini ko'rsatadi) → taste-skill. **Ishlatiladigan ekran** (jadval, forma,
filtr) → o'xshash mahsulotning DESIGN.md i. Topshiriq yoki mijoz boshqa uslub so'rasa — u ustun.

## Tekshirish

| Nima | Xususiyati | Qachon mos | Holat |
|---|---|---|---|
| **playwright-cli** | Claude brauzer ochadi: skrinshot, konsol xatolari, bosish, forma to'ldirish, istalgan kenglik. MCP dan arzonroq (token) | har qanday UI ni "tayyor" deyishdan oldin; telefon ko'rinishini tekshirish | ✅ `npm i -g @playwright/cli` + skill · [repo](https://github.com/microsoft/playwright-cli) Apache-2.0 |
| **web-design-guidelines** (Vercel) | Vercel'ning interfeys qoidalari bo'yicha `fayl:qator` ko'rinishida kamchiliklar; qoidalarni har safar yangidan oladi | topshirishdan oldingi oxirgi ko'rik, accessibility | ✅ `~/.claude/skills/web-design-guidelines` |
| Chrome DevTools MCP (Google) | tezlik trace, Core Web Vitals, tarmoq | sayt sekin bo'lsa | 📦 ko'p ishni playwright-cli qiladi |

Odatiy tekshiruv: 390 / 768 / 1440 kenglikda skrinshot, `console` da 0 xato, har bir tugma bosilgan → keyin
web-design-guidelines.

## Backend va deploy

| Nima | Xususiyati | Qachon mos | Holat |
|---|---|---|---|
| **Supabase** skill + MCP | Postgres, Auth, RLS, Storage, migratsiya — alohida backend yozmaslik uchun | tez MVP, CRM, xakaton | 🔑 `/plugin marketplace add supabase/agent-skills`; MCP faqat dev loyihaga, `read_only=true` |
| **Vercel plugin** | deploy, env, status (38 skill) | Next.js / statik sayt | 🔑 `npx plugins add vercel/vercel-plugin`, `VERCEL_PLUGIN_TELEMETRY=off` |
| **Railway** (remote MCP + CLI) | arzon server hosting | Telegram bot, backend servis | 🔑 `mcp.railway.com` (OAuth) |
| Netlify MCP | Netlify deploy | mijoz Netlify ishlatsa | 📦 kichik, litsenziyasiz |

Eslatma: Supabase'da har jadvalga RLS — AI qurgan ilovalarning eng ko'p uchraydigan teshigi.

## Tez prototip

| Nima | Xususiyati | Qachon mos | Holat |
|---|---|---|---|
| **replica-skill** | mavjud ilova funksiyalarini qayta quradi: recon → architect → build → test → entrepreneur → deploy (11 skill) | "X ga o'xshash ilova" kerak bo'lganda | 📦 `/plugin marketplace add Jakeschincariol/replica-skill` · MIT. Har sessiyada joy egallaydi — faqat o'sha loyihada |

## Xavfsizlik

| Nima | Xususiyati | Qachon mos | Holat |
|---|---|---|---|
| `/security-review` (o'rnatilgan) | o'zgarishlarni xavfsizlik bo'yicha ko'rib chiqadi | har commit / topshirishdan oldin | ✅ |
| **claude-security** (rasmiy) | ko'p agentli skan: tahdid modeli → qidirish → tekshirish → tuzatish | mijozga topshirishdan oldin | 🔑 `/plugin install claude-security@claude-plugins-official`; token ko'p |
| **security-guidance** (rasmiy) | yozayotganda xavfli kod haqida ogohlantirish (innerHTML, sirlar) | uzoq loyiha | 🔑 `ENABLE_STOP_REVIEW=0` bilan, aks holda har to'xtashda ~32k token |

## Shablonlar

- [`templates/CLAUDE.md`](templates/CLAUDE.md) — web loyiha qoidalari: stack, buyruqlar, "bitta funksiya birdan", sifat
  chizig'i (o'lik tugma yo'q, loading/empty/error holatlari, telefon), xavfsizlik. Loyihaga moslab to'ldiriladi.
- [`templates/settings.json`](templates/settings.json) — loyihaning `.claude/` iga: typecheck o'tmasa Claude ishni
  tugatmaydi, `.env` va `secrets/` ni o'qimaydi.

Kodlash umumiy qoidalari va Context7 (kutubxona hujjatlari): [`../claude-code/`](../claude-code/README.md).

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

### YouTube'dan qo'shimcha saboqlar (2026-11-07)

Rasmiy Anthropic videosi va amaliyotchilardan; xususiyatlar code.claude.com hujjatlari bilan solishtirilgan. (rasmiy) =
Claude Code jamoasining o'zi.

1. **Har vazifaga qisqa brief:** nima qilish, chegaralar, "tayyor" nimani anglatadi. Kichik vazifada rejani uzoq ko'rib
   o'tirmay, natijani baholang; batafsil reja — katta yoki noaniq ishda. [A 0:51]
2. **"Tayyor" — Claude ishga tushira oladigan tekshiruv** (o'tdi/o'tmadi skript). Promptga "ishingni qayta tekshir" deb
   yozish faqat token sarflaydi. [A 3:25]
3. **Claude ilovani o'zi boshidan oxirigacha qurib, sinay oladigan bo'lsin**, dalil sifatida skrinshot yoki ekran yozuvi
   so'raladi. (rasmiy) [B 14:04, 17:30]
4. **`/goal`** — "davom et" deb qayta-qayta yozish o'rniga: oxirgi holat, uni qanday isbotlash, nima o'zgarmasligi va
   tur chegarasi. Misol: `/goal check_report o'tadi, shablon o'zgarmaydi, 15 turdan keyin to'xta`. Hakam faqat chatni
   o'qiydi — maqsad noaniq bo'lsa, erta to'xtaydi. VS Code'da bor. [A 5:02]
5. **Katta o'zgarish oxirida bir sahifalik vizual / HTML xulosa:** nima o'zgardi, nimani taxmin qildi. Savollarni ham
   maketli HTML sahifa orqali berish mumkin. (rasmiy) [B 6:01; A 1:42]
6. **Xato qidirish, audit, tadqiqot — "tarqat, keyin tekshir":** bir nechta agent qidiradi, har topilma ~3 tomondan
   qarshi tekshiriladi, faqat tasdiqlangani qaytadi. (rasmiy) [B 10:30–13:42]
7. **Odam vaqti — katta rasmga:** API shakli, servis chegaralari, repo tashqarisidagi qarorlar; mayda narsani Claude
   o'zi tuzatsin. (rasmiy) [B 9:25]
8. **Skill faqat Claude usiz yiqilgandan keyin:** haqiqiy vazifani skillsiz bajaring, nimani tuzatganingizni yozing —
   skill shu tuzatishlarning o'zi. Ishlatadigan modelda sinang. [A 10:00]
9. **Skillarni kamaytiring:** `/skill-doctor` (foydalanish va narx), `claude plugin eval` (skill bilan va skillsiz
   solishtirish) — natija bir xil bo'lsa, skillni olib tashlang. [A 11:48]
10. **CLAUDE.md — mundarija:** fayllarga oddiy yo'l va qachon o'qish bilan havola ("mijoz ishidan oldin `docs/brief.md`
    ni o'qi"). `@import` butun faylni har sessiyaga yuklaydi. [A 7:36]
11. **Model yaxshilanganda eski "qo'ltiq tayoq"larni olib tashlang.** `/doctor prompt-audit` eski modellar uchun yozilgan
    ko'rsatmalarni topadi (faqat hisobot beradi). (rasmiy) [B 3:25; A 8:50]
12. **Kerakli agent, skill yoki hujjat manbasini nomi bilan ayting** ("implement qilishdan oldin Context7 dan better-auth
    hujjatini ol") — aks holda o'tkazib yuborilishi mumkin. [C 11:06]
13. **Rejani tasdiqlashdan oldin tahrirlang** — keyin kodni tuzatishdan arzon. Mayda o'zgarishni qo'lda qiling. [C 6:19, 15:54]
14. **Xavfli skill (deploy, rollback) — faqat qo'lda:** frontmatter'da `disable-model-invocation: true`. [D 3:33]

Bilish foydali: `/rewind` (kod va suhbatni qaytaradi, lekin Bash orqali o'zgargan fayllarni emas — git commit ham
qiling) · `/branch` (xavfli tajriba uchun suhbatni ajratish) · terminalda `claude -p "..." --output-format json`
(skript va CI uchun) · uzoq vazifalar uchun claude.ai/code va jadvalli routine'lar (noutbuk o'chiq bo'lsa ham).

Ehtiyot bo'ling:
- Ruxsatlarni hech qachon o'chirmang (bypass) — xavfli buyruqni bloklaydigan hook qo'ying. Auto mode — faqat izolyatsiyalangan
  nusxada, sirlar yonida emas.
- Claude testni "o'tkazish" uchun o'zgartirishi mumkin — test fayllarini himoyalang yoki test diff'ini ko'rib chiqing.
- "ultrathink / think hard" endi alohida ta'sir qilmaydi; `ultracode` — workflow orkestratsiyasi kalit so'zi, effort emas.
- "Desktop ilova sizni kuzatib skill yozadi" — hujjatlarda yo'q, noto'g'ri.

Manbalar: **A** Simon Scrapes — "How the Top 1% Use Claude Code Differently", https://youtu.be/J9NQTYUP6k0 (eng amaliysi;
Skool reklamasi) · **B** Claude — "How the Claude Code team uses Claude Code", https://youtu.be/S-sYlFiGFv8 (rasmiy) ·
**C** Academind — "My top 6 tips…", https://youtu.be/WwdIYp5fuxY (eski, 2026-01) · **D** Tech With Tim — "Claude Code: The
Advanced Guide", https://youtu.be/kt5a-TXmWew (Granola homiysi)

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

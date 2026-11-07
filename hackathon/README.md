# Xakaton

Maqsad: Claude topshiriqni, talablarni va baholash mezonlarini to'liq hisobga olib, **hamma talab bajarilgan, sodda lekin
professional** yechim qilsin, va bu har safar takrorlansin.

Bu bo'limda faqat xakatonga xos narsalar (jarayon, hakamlar, pitch). Toollarning o'zi va xususiyatlari o'z bo'limlarida —
bu yerda qaysi bosqichda qaysi biridan foydalanish **tavsiya** etiladi.

## Tuzilish

| Fayl | Nima | Holat |
|---|---|---|
| [`PLAYBOOK.md`](PLAYBOOK.md) | hakamlar qanday baholaydi, 10 qoida, 24 soatlik reja, pitch, topshirish cheklisti | tayyor |
| [`skills/hackathon/`](skills/hackathon/SKILL.md) | Claude "xakaton" deganda o'zi ishga tushiradigan skill | ✅ `~/.claude/skills/` da |
| [`agents/`](agents/) | **Agentlar jamoasi** (✅ `~/.claude/agents/` da, hamma loyihada): `hackathon-researcher` (manbali faktlar, raqobatchilar, sponsor API), `feature-builder` (bitta funksiya, faqat o'z fayllarida, dalil bilan), `qa-tester` (brauzerda hamma narsani bosib chiqadi), `spec-reviewer` (hakam: talablar va ball), `pitch-writer` (pitch, slaydlar, Devpost, savol-javob) + [`../web/agents/design-reviewer.md`](../web/agents/design-reviewer.md). Kim qachon parallel ishlashi — skillning "Agent team" bo'limida | tayyor |
| [`templates/SPEC.md`](templates/SPEC.md) | talablar jadvali, mezonlar, demo ssenariysi, MVP chegarasi | tayyor |
| [`cases/`](cases/) | o'tgan xakatonlar: topshiriq, mezonlar, nima qildik, nima ishladi — birinchisi: [UZEX AI saralash, 511 dan 1-o'rin](cases/2026-11-05-uzex-ai-saralash.md) | 1 ta |

## Bosqichlar va tavsiya etiladigan toollar

| Bosqich | Nima qilinadi | Tavsiya | Bo'lim |
|---|---|---|---|
| 1. Topshiriqni ochish | qoidalar, mezonlar va ulushlari, format, muddat | fayl bo'lsa — markitdown | [`documents/`](../documents/README.md) |
| 2. SPEC | bir gaplik ta'rif, **har bir** talab jadvalda, 90 s demo ssenariysi, MVP chegarasi | [`templates/SPEC.md`](templates/SPEC.md) | shu bo'lim |
| 3. Loyiha sozlash | qoidalar, typecheck hook, `.env` himoyasi, hakam agenti | web shablonlari + `spec-reviewer` | [`web/`](../web/README.md) → Shablonlar |
| 4. Dizayn | sodda, bitta tizim, professional | sayt → taste-skill; ilova ekrani → DESIGN.md | [`web/`](../web/README.md) → Dizayn |
| 5. Qurish | eng og'ir mezondan boshlab, bitta funksiya birdan, erta deploy | backend/deploy, kutubxona hujjatlari | [`web/`](../web/README.md), [`claude-code/`](../claude-code/README.md) |
| — o'zbekcha funksiyalar | ovoz, nutq, to'lov, SMS, xarita | standart to'plam | [`uzbek/`](../uzbek/README.md) |
| — bot bo'lsa | Telegram bot | aiogram + Context7 | [`automation/`](../automation/README.md) |
| 6. Tekshirish | har demo / topshirishdan oldin | playwright-cli → web-design-guidelines → `spec-reviewer` | [`web/`](../web/README.md) → Tekshirish |
| 7. Pitch va video | slaydlar, demo ssenariysi, savollar, demo video | PLAYBOOK §4; slayd — pptx; video — video kit | [`documents/`](../documents/README.md), [`video/`](../video/README.md) |
| 8. Topshirish | cheklist, muddatdan 1 soat oldin | PLAYBOOK §5 | shu bo'lim |
| 9. Retro | nima ishladi, nima ishlamadi | [`cases/TEMPLATE.md`](cases/TEMPLATE.md) | shu bo'lim |

Bu tavsiyalar: topshiriq boshqa stack, uslub yoki format talab qilsa — topshiriq ustun.

Umumiy xarita: [`../QOLLANMA.md`](../QOLLANMA.md).

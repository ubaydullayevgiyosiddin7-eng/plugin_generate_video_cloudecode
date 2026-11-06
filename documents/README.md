# Hujjatlar: o'qish, yozish, taqdimot

Holat: ✅ o'rnatilgan · 🔑 egasi qo'shadi · 📦 kerak bo'lganda

| Nima | Xususiyati | Qachon mos | Holat |
|---|---|---|---|
| **markitdown** (Microsoft) | Word, PowerPoint, Excel, PDF, HTML → toza Markdown; tokenni tejaydi, jadvallarni saqlaydi | topshiriq, shartnoma, texnik vazifa fayl bo'lib kelsa — o'qishdan oldin `markitdown fayl.docx > fayl.md` | ✅ `pip install "markitdown[pdf,docx,pptx,xlsx]"` · [repo](https://github.com/microsoft/markitdown) MIT |
| Claude'ning o'z `docx`, `pdf`, `pptx`, `xlsx` skillari | fayl yaratish va tahrirlash (Word, PDF, slayd, jadval) | natija fayl bo'lishi kerak bo'lganda: taqdimot, hisobot, jadval | ✅ o'rnatilgan |
| **knowledge-work-plugins** (Anthropic) — product-management, marketing, sales, data | spetsifikatsiya, roadmap, kampaniya rejasi, SQL tahlil | pitch hujjati, mijoz uchun taklif, mahsulot rejasi | 📦 `/plugin marketplace add anthropics/knowledge-work-plugins` → kerakli bittasi · Apache-2.0 |

Tanlash: fayl **kirib keladi** → markitdown (kichik PDF ni Claude o'zi ham o'qiydi). Fayl **chiqishi kerak** → docx/pptx/xlsx
skillari. Hujjat **mazmuni** (spec, reja) kerak → knowledge-work-plugins yoki oddiy so'rov.

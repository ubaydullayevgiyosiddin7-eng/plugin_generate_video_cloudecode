# 🎬 video_tools: video tayyorlash asboblari

Telefonda olingan video va rasmlardan professional film yasash uchun kerakli hamma narsa shu yerda. Birinchi marta "Magic Safari" (hayvonot bog'i, 03.10.2026) loyihasida yaratilgan, "Kuzgi sayr" (yapon bog'i va teleminora, 05.10.2026) loyihasida yaxshilangan.

## Keyingi safar qanday boshlanadi?

1. Yangi video va rasmlaringizni alohida papkaga tashlang (masalan `C:\My_poject\yangi_video\`).
2. Claude'ni o'sha papkada oching va shunday yozing:
   > "Yangi video qilamiz. `C:\My_poject\video_tools` dagi asboblar va yo'riqnomadan foydalan."
3. Claude sizdan 3–4 ta savol so'raydi (video kim uchun, format, musiqa, sarlavha), keyin agentlar jamoasini ishga tushiradi.

**Endi odatiy usul — "Tez rejim":** tekshiruvlar kam, birinchi ko'rib chiqish versiyasi taxminan 50 daqiqada tayyor bo'ladi. To'liq tekshiruv faqat siz so'rasangiz yoki film 3 daqiqadan uzun bo'lsa qilinadi. Sayohat filmlari uchun odatiy uzunlik — taxminan 1,5 daqiqalik **"xotira" versiyasi** (har joydan 1–2 ta har xil kadr). Qisqa Reels versiyasi esa xohlasangiz qo'shimcha qilinadi.

## Ichida nima bor?

| Papka | Nima bor |
|---|---|
| `engine/` | **Montaj dvigateli.** Ssenariy (EDL) bo'yicha tayyor videoni yig'adi: kesish, silliq yaqinlashtirish (qaltiramaydi!), sekinlashtirish, sarlavhalar, rang, musiqa |
| `tools/` | Yordamchi asboblar: fayllarni tekshirish, HEIC rasmlarni JPG ga o'tkazish, kontakt varaqlar, kadrlar takrorlanmasligini tekshirish, qaltirashni o'lchash, musiqa zarblarini topish, ulashish uchun ~45 MB versiya yasash |
| `templates/` | Har bir agent (ko'ruvchi, fotograf, musiqachi, kadrlash, nazoratchilar…) uchun tayyor topshiriq matnlari |
| `docs/workflow.md` | Ish jarayoni bosqichma-bosqich |
| `docs/lessons.md` | **O'rganilgan saboqlar.** Birinchi loyihada topilgan muammolar va ularning yechimlari |
| `examples/magic_safari/`, `examples/kuzgi_sayr/` | Ikki filmning ssenariysi va musiqa rejasi (namuna sifatida) |
| `agents/` | "Bilim jamoasi"ning 4 ta agenti (pastda batafsil) |
| `retro/`, `audit/` | Har loyihadan keyingi tahlil va tekshiruv hisobotlari |
| `inbox.md` | Ish davomida tez yozib qo'yiladigan kuzatuvlar |
| `CLAUDE.md` | Claude uchun yo'riqnoma (ingliz tilida) |

## 🧠 Bilim jamoasi: asboblar har safar yaxshilanib boradi

Har bir loyihadan keyin 4 ta maxsus agent ishlaydi. Ular o'sha loyihadan saboq oladi va asboblarni yangilaydi:

| Agent | Vazifasi |
|---|---|
| 🔍 **Retrospektiv tahlilchi** (`video-retro`) | Tugagan loyihani o'rganadi: nima yaxshi bo'ldi, nima xato ketdi, qayerda vaqt yo'qoldi. Har bir taklifni dalil bilan yozadi |
| 🛠️ **Asbobsoz** (`video-toolsmith`) | Tasdiqlangan takliflar asosida yangi asbob yozadi yoki dvigatelni yaxshilaydi |
| 📚 **Kutubxonachi** (`video-curator`) | Saboqlar, yo'riqnomalar va agent topshiriqlarini yangilaydi, takrorlarni olib tashlaydi |
| ✅ **Tekshiruvchi** (`video-kit-auditor`) | Hammasi buzilmasdan ishlayotganini mustaqil tekshiradi. "O'tdi" demaguncha o'zgarish tayyor hisoblanmaydi |

**Qanday ishga tushiriladi?** Loyiha tugagach, Claude buni o'zi taklif qiladi. Yoki siz shunday yozasiz:
> "saboq ol" yoki "asboblarni yangila"

Ish davomida kutilmagan narsa yuz bersa, Claude uni `inbox.md` ga bir qatorda yozib qo'yadi. Tahlilchi keyin shularni ko'rib chiqadi. Qaysi o'zgarish qilinishini Claude tasdiqlaydi. Sizning didingizga oid narsalarni esa sizdan so'raydi.

Qo'shimcha fayllar: `CHANGELOG.md` (nima o'zgargani tarixi), `docs/metrics.md` (har bir loyiha qancha vaqt olgani, shunda "qancha qoldi?" savoliga aniqroq javob beriladi), `docs/backlog.md` (kelajakdagi yaxshilash g'oyalari).

## Muhim eslatmalar

- 📁 **Asl fayllaringizga hech qachon tegilmaydi.** Barcha ish fayllari alohida `_ish` papkasida bo'ladi.
- 💾 Kompyuterda joy va xotira (RAM) kam. Ish tugagach, `_ish` papkasini o'chirib yuborsangiz bo'ladi, chunki tayyor video alohida saqlanadi. Oxirgi render oldidan Claude Chrome yoki Word'ni yopishni so'rashi mumkin: xotira kam bo'lsa, render 4 barobar sekinlashadi.
- 🎵 Bepul musiqa (Kevin MacLeod va boshqalar) ishlatilsa, post tagiga muallif nomini yozish **shart**. Videoning o'zida musiqa nomi chiqmaydi; Claude post uchun tayyor matn beradi.
- 📱 Tayyor fayllar: **asl nusxa** (eng sifatli, katta) va **bitta ulashish versiyasi** (~40–50 MB, Instagram/YouTube/Telegram uchun, sifati deyarli bir xil).

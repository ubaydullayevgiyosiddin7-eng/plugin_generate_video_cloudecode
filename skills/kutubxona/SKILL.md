---
name: kutubxona
description: Egasining GitHub'dagi Claude skill kutubxonasini boshqaradi. Yangi skill, vosita, plugin yoki yangilik qo'shilganda, bir xil turdagi vositalarni solishtirganda, eskirgan yoki sifatsiz narsalarni tekshirganda va kutubxonani GitHub'ga yuklashda ishlating. Use when adding or comparing skills and tools, reviewing outdated ones, or uploading the skill library to GitHub.
---

# Skill kutubxonasi

Egasi o'zbek tilida gaplashadi: unga o'zbekcha (lotin) javob bering.

Asl manba: `D:\My_projects\video`. Ro'yxat: `skills/kutubxona/katalog.md`. Avval katalogni o'qing.

Har bir yo'nalish alohida skill: `skills/<nomi>/SKILL.md`. Hozir: `video`, `miniapp-dizayn` va `kutubxona`. Yangi yo'nalish uchun yangi skill oching, mavjudini kattalashtirmang.

## Yangi narsa qo'shish

1. **Tekshirish:** sahifani o'qing, litsenziya va narxni aniqlang, kodini ko'rib chiqing. Kodini ko'rmasdan hech narsa o'rnatmang.
2. **Turini aniqlash:** katalogda shu turdagi vosita bormi, qarang.
3. **Yozish:** katalogga "Sinovda" holati bilan qo'shing: nima qiladi, qayerdan olingan, sana.
4. **Sinash:** egasining ruxsati bilan alohida papkada kichik sinov qiling. Natijani katalogdagi izohga yozing.
5. **Joylash:** yordam bersa, tegishli skill yo'riqnomasiga qo'shing.
6. **Yuklash:** pastdagi "GitHub'ga yuklash" bo'limi bo'yicha.

## Bir xil turdagi vositalar

Yangi vosita mavjudini o'zi almashtirmaydi.

- Yangisini "Muqobil" qilib qo'shing va izohda qaysi holatda yaxshiroq ekanini yozing.
- Ikkalasini bir xil vazifada sinang. Ovoz uchun: bir xil gaplar, keyin egasi eshitib tanlaydi. Boshqa vositalar uchun: bir xil vazifa, raqam yoki natija bilan.
- "Asosiy" holatini faqat egasi tasdiqlagandan keyin almashtiring. Har bir turda bitta "Asosiy" bo'ladi.

## O'chirishni tavsiya qilish

Egasi "kutubxonani tekshir" deganda, yoki yangi vosita qo'shilib, eski narsa ortiqcha bo'lib qolganda, tavsiya bering.

Sabablar:

- yangi vosita uni hamma jihatdan ortda qoldirgan;
- sinovda yiqilgan yoki sifati past chiqqan;
- loyihasi tashlab ketilgan yoki endi ishlamaydi;
- litsenziyasi yoki narxi yomon tomonga o'zgargan;
- xavfsizlik muammosi chiqqan.

Har bir tavsiyada nomi, sababi, nima yo'qotilishi va o'rnini nima bosishini yozing. **O'chirishni faqat egasi aytgandan keyin bajaring.** Unga qadar holatini "Eskirgan" qilib, izohga sababini yozing.

## GitHub'ga yuklash

Egasining doimiy ko'rsatmasi: kutubxonaga kiritilgan har bir tugallangan o'zgarish GitHub'ga yuklanadi, alohida so'rash shart emas.

Repo **public**, shuning uchun yuklashdan oldin:

- token, kalit, parol va telefon raqami qolmaganini qidirib tekshiring;
- ovoz namunalari, shaxsiy videolar va egasining mijoz yoki ish ma'lumotlarini yuklamang;
- modellar va og'ir fayllarni yuklamang: faqat o'rnatish yo'riqnomasini qoldiring;
- begona skill'ni nusxalashdan oldin litsenziyasi ruxsat berishini tekshiring, muallif va litsenziyani saqlang.

Bir mavzu = bitta commit. Commit matni nima o'zgarganini aytsin.

| Nima | Papka | Buyruq |
|---|---|---|
| Skill va katalog | `D:\My_projects\video` | `git -c http.schannelCheckRevoke=false push origin main:video-markazi` |
| Opuscar `kit/` | `D:\My_projects\lemo-opuscar` | `git -c http.schannelCheckRevoke=false push https://ubaydullayevgiyosiddin7-eng@github.com/ubaydullayevgiyosiddin7-eng/plugin_generate_video_cloudecode.git main:main` |

`lemo-opuscar` dagi `origin` asl muallifning repo'si, unga yuklamang. Force push qilmang. Push o'tmasa, sababini egasiga ayting: token muddati tugagan bo'lishi mumkin.

Yangi skill qo'shilgach, Claude'ga ulash uchun `scripts/link-skills.ps1` ni ishga tushiring va yangi sessiya oching.

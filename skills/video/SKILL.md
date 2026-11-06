---
name: video
description: Egasining yagona video markazi. Har qanday video, reel, film, animatsiya, reklama, tushuntirish videosi, o'zbekcha ovoz, ovoz effekti yoki musiqa ishida, qaysi loyihada bo'lishidan qat'i nazar, shu skill bilan boshlang. Video vositasi yoki yangilik haqida havola berilib "videoga qo'sh" deyilganda ham ishlating. Use for any video, reel, film, animation, voiceover or sound-effect task, and when asked to add a new video tool.
---

# Video markazi

Egasi o'zbek tilida gaplashadi: unga o'zbekcha (lotin) javob bering. Bu skill qaysi vositani qachon ishlatishni aytadi; ishni vositalarning o'zi bajaradi.

Asl manba: `D:\My_projects\video\skills\video`. Yozish kerak bo'lsa, shu joyga yozing.

## Ishni boshlashdan oldin

1. `lessons.md` ni o'qing: bu avvalgi filmlarda sinalgan saboqlar.
2. `news.md` ni o'qing. "Sinalgan" yozuvlarni hisobga oling, "Kutilmoqda" yozuvlarini tekshirmasdan ishlatmang.
3. Vazifaga mos `tools/` faylini o'qing.
4. Vosita shu kompyuterda borligini tekshiring. Yo'q bo'lsa, o'sha fayldagi o'rnatish bo'limiga qarang.

## Vazifa va vosita

| Vazifa | Vosita | Yo'riqnoma |
|---|---|---|
| Kod bilan chizilgan film (66 uslub) | `lemo-opuscar:lemo-opuscar` skill | `tools/opuscar.md` |
| O'zbekcha ovoz, egasining ovozida | Navoiy TTS | `tools/navoiy.md` |
| Ovoz effektlari va musiqa | `kit/sound` | `tools/sound.md` |
| Vertikal doska (9:16) | `kit/whiteboard-vertical` | `tools/opuscar.md` |
| Sertifikat yoki tarmoq xatosi | - | `tools/network.md` |

## Joylar (ish kompyuteri)

| Nima | Papka |
|---|---|
| Video markazi | `D:\My_projects\video` |
| Yangi filmlar (egasi boshqa joy aytmasa) | `D:\My_projects\video\films\<film-nomi>` |
| Opuscar va `kit/` | `D:\My_projects\lemo-opuscar` |
| Navoiy TTS va egasining ovozi | `D:\My_projects\tts` |
| Earshot va opus-sound-layer | `D:\My_projects\sound-tools` |

## Qoidalar

- **Film boshlashdan oldin:** bitta film 30–60 daqiqa oladi va ko'p token sarflaydi. Buni aytib, uslub, davomiylik va formatni kelishib oling.
- **Format:** Reels uchun doim "Vertical 9:16" so'rang, aks holda 1920×1080 chiqadi.
- **Ovoz:** faqat egasining o'z ovozi yoki roziligi bor odamning ovozi ishlatiladi.
- **Litsenziya:** reel tijoriy foydalanish hisoblanadi. Faqat CC0, PDM yoki CC BY (muallifi yoziladi). NC va ND hech qachon.
- **Ovoz sifati:** "yaxshi eshitiladi" demang, `qa.py` yoki Earshot raqamini ayting. Talaffuzni egasi eshitib tekshiradi.
- **Topshirish:** mp4, `CREDITS.md` va Instagram matni.
- **Maxfiylik:** ovoz namunalari, tokenlar va tayyor videolar repo'ga yuklanmaydi.

## Film tugagach

Yangi, sinalgan saboq bo'lsa, `lessons.md` ga bitta qator qo'shing. Taxminlarni yozmang.

## Yangilik qo'shish

Egasi vosita yoki yangilik havolasini berganda:

1. Sahifani o'qing va `news.md` ning "Kutilmoqda" bo'limiga yozing: nima, qayerdan, sana.
2. Litsenziya va narxni tekshiring, kodini o'qing. Kodini ko'rmasdan hech narsa o'rnatmang.
3. Egasining ruxsati bilan alohida papkada kichik sinov qiling.
4. Ishlasa: yozuvni "Sinalgan" ga o'tkazing, kerakli `tools/` fayliga va yuqoridagi jadvalga qo'shing. Ishlamasa: "Rad etilgan" ga sababi bilan o'tkazing.

Commit va push faqat egasi so'raganda qilinadi.

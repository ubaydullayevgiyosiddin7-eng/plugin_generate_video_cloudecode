# Claude uchun foydali narsalar to'plami

Claude Code bilan ishlashda sinalgan skillar, agentlar, toollar va ko'rsatmalar bir joyda. Har bir bo'lim o'z papkasida,
har birining o'z README'si bor.

| Bo'lim | Nima bor | Holat |
|---|---|---|
| [`video/`](video/README.md) | Video qilish: kod bilan film (lemo-opuscar ustiga qo'shimchalar), o'zbekcha ovoz, ovoz effektlari, telefon videolaridan film yig'adigan `video_tools` kit va uning 4 ta agenti | ishlaydi, reellar shu bilan qilingan |
| [`hackathon/`](hackathon/README.md) | Xakatonda yutish uchun: topshiriqni tahlil qilish, baholash mezonlari, qurish, pitch, topshirish | yig'ilmoqda |
| [`tools/`](tools/README.md) | Umumiy toollar (masalan, Telegram kanal o'quvchi) | ishlaydi |

Har bir narsa qayerdan olingani va litsenziyasi: [`SOURCES.md`](SOURCES.md).

## Qanday ishlatish

```
git clone https://github.com/ubaydullayevgiyosiddin7-eng/plugin_generate_video_cloudecode
```

Keyin kerakli bo'limning README'sini oching. Claude Code'ni shu repo ichida ochsangiz, u [`CLAUDE.md`](CLAUDE.md) orqali
qaysi narsa qayerdaligini o'zi biladi.

## Yangi narsa qo'shish

1. To'g'ri papkaga qo'ying (video → `video/`, xakaton → `hackathon/`, umumiy → `tools/`). Mos papka bo'lmasa, yangisini oching.
2. Papkaning README'sidagi jadvalga bir qator qo'shing.
3. Begona narsa bo'lsa, manbasi va litsenziyasini [`SOURCES.md`](SOURCES.md) ga yozing.
4. Parol, token, `.env`, `.session`, shaxsiy rasm/video/ovoz hech qachon repoga tushmaydi.

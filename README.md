# Claude skill kutubxonasi

Claude Code uchun shaxsiy skill'lar: har bir yo'nalish alohida papkada. Istalgan loyihada Claude kerakli vosita, sinalgan saboq va yangilikni shu yerdan topadi.

| Skill | Vazifasi |
|---|---|
| `skills/video` | Film, reel, ovoz va ovoz effektlari |
| `skills/kutubxona` | Yangi narsa qo'shish, solishtirish, eskirganini tavsiya qilish, GitHub'ga yuklash |

Hamma vositalar va ularning holati: [`skills/kutubxona/katalog.md`](skills/kutubxona/katalog.md).

Repo public. Unda modellar, ovoz namunalari, tayyor videolar va tokenlar yo'q.

## Yangi kompyuterga ulash (Windows)

Kutubxona `plugin_generate_video_cloudecode` repo'sining `video-markazi` branch'ida turadi. Opuscar va `kit/` shu repo'ning `main` branch'ida.

```powershell
git clone -b video-markazi https://github.com/ubaydullayevgiyosiddin7-eng/plugin_generate_video_cloudecode.git D:\My_projects\video
powershell -ExecutionPolicy Bypass -File D:\My_projects\video\scripts\link-skills.ps1
```

Papkalar bog'langani uchun `skills/` dagi har bir o'zgarish darrov ishlaydi. Yangi Claude sessiyasini oching.

Video vositalarini o'rnatish: `skills/video/tools/navoiy.md` va `skills/video/tools/opuscar.md`.

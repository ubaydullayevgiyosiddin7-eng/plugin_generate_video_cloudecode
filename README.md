# Video markazi

Claude Code uchun video ishlarining yagona kirish nuqtasi. Istalgan papkada "video qil" deyilganda Claude shu yerdan vositalar, sinalgan saboqlar va yangiliklarni topadi.

| Fayl | Nima |
|---|---|
| `skills/video/SKILL.md` | Kirish nuqtasi va qoidalar |
| `skills/video/tools/` | Navoiy, Opuscar, ovoz effektlari va tarmoq yo'riqnomalari |
| `skills/video/lessons.md` | Sinalgan saboqlar |
| `skills/video/news.md` | Yangi vositalar: kutilmoqda, sinalgan, rad etilgan |

Repo'da modellar, ovoz namunalari, tayyor videolar va tokenlar yo'q.

## Yangi kompyuterga ulash (Windows)

Markaz `plugin_generate_video_cloudecode` repo'sining `video-markazi` branch'ida turadi. Opuscar va `kit/` shu repo'ning `main` branch'ida.

```powershell
git clone -b video-markazi https://github.com/ubaydullayevgiyosiddin7-eng/plugin_generate_video_cloudecode.git D:\My_projects\video
cmd /c mklink /J "$env:USERPROFILE\.claude\skills\video" "D:\My_projects\video\skills\video"
```

Papka bog'langani uchun `skills/video` dagi har bir o'zgarish darrov ishlaydi. Yangi Claude sessiyasini oching va `/video` deb yozing.

Vositalarni o'rnatish: `skills/video/tools/navoiy.md` va `skills/video/tools/opuscar.md`.

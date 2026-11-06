# Opuscar: Claude Code bilan kod orqali chizilgan filmlar

Lemomo'ning bepul plugin'i (MIT + CC BY 4.0): https://github.com/lemomo-ai/lemo-opuscar. Claude hikoyani yozadi,
kadrlarni canvas/WebGL bilan chizadi, musiqa va effektlar qo'shadi, keyin videoni kadrma-kadr render qiladi.
AI video generatsiyasi ishlatilmaydi. Bitta film 30–60 daqiqa oladi va ancha token sarflaydi. Uslublar
Claude Opus uchun moslangan. Uslublar galereyasi: https://lemomo-ai.github.io/lemo-opuscar/

Egasining zaxira nusxasi: https://github.com/ubaydullayevgiyosiddin7-eng/plugin_generate_video_cloudecode
Asl repo yo'qolib qolsa ham, shu nusxadan o'rnatish mumkin.

## O'rnatish (Windows)

Plugin Linux/Mac uchun yozilgan. Windows'da quyidagi tartibda o'rnatiladi (PowerShell):

```
winget install Gyan.FFmpeg --source winget            # ffmpeg + ffprobe (7+ kerak); keyin terminalni qayta oching
cd D:\My_projects
git -c http.schannelCheckRevoke=false clone https://github.com/lemomo-ai/lemo-opuscar.git
#   (yoki zaxira nusxadan: ...ubaydullayevgiyosiddin7-eng/plugin_generate_video_cloudecode.git lemo-opuscar)
$claude = (Get-ChildItem "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe" | Select-Object -Last 1).FullName
& $claude plugin marketplace add D:\My_projects\lemo-opuscar
& $claude plugin install lemo-opuscar@lemolab

cmd /c mklink /J "$env:USERPROFILE\lemo-opuscar" "D:\My_projects\lemo-opuscar"   # kutubxonani qayta yuklamasin
cd D:\My_projects\lemo-opuscar
py -3.12 -m venv .venv
cmd /c mklink /J .venv\bin .venv\Scripts                                          # skriptlar .venv/bin ni kutadi

$env:LEMO_OPUSCAR_HOME="/d/My_projects/lemo-opuscar"   # D:/... yo'lini setup.sh tushunmaydi
$env:NODE_OPTIONS="--use-system-ca"; $env:PIP_USE_FEATURE="truststore"
$env:CURL_HOME="D:\My_projects\curlhome"               # ichida "ssl-no-revoke" qatori bor _curlrc fayli
& "C:\Program Files\Git\bin\sh.exe" plugin/skills/lemo-opuscar/scripts/setup.sh deps voice
```

- Oxirida `LIB=/d/My_projects/lemo-opuscar` chiqsa, o'rnatish tugagan.
- `deps voice` qo'shimcha ravishda inglizcha ovoz modelini (354 MB) yuklaydi. U bizga shart emas: o'zbekcha
  ovozni Navoiy beradi. Yuklash yiqilsa, faqat `deps` bilan ishga tushirsa ham bo'ladi.
- Mac yoki Linux'da `mklink` qadamlari va `$env:` qatorlari kerak emas: plugin'ni o'rnatish va
  `sh .../setup.sh deps` ni ishga tushirish yetadi.

## Ishlatish

1. VS Code'da Claude Code'ning **yangi** oynasini oching. Plugin faqat o'rnatilgandan keyin boshlangan
   sessiyada ko'rinadi.
2. `/lemo-opuscar:lemo-opuscar` deb yozing yoki so'rovni to'g'ridan-to'g'ri yozing, masalan:
   > Make a 35-second film in the **Whiteboard Explainer** style about finding a rental flat in Tashkent with one
   > Telegram bot instead of ten channels. Uzbek narration — I will give you my own voice track. Vertical 9:16.
   > End with "Izohga UY deb yozing".
3. Claude o'z ovozingiz bormi deb so'raydi. Avval Navoiy bilan gaplarni ovozga aylantirib (`tools/navoiy.md`), tayyor
   wav fayllarni bering.
4. Reels uchun so'rovga albatta "Vertical 9:16" qo'shing (aks holda 1920×1080 chiqadi). Filmda tashqi musiqa
   ishlatilgan bo'lsa, litsenziyasi va krediti qanday ekanini Claude'dan so'rang va kreditni caption'ga yozing.

## Vertikal doska

9:16 doska uchun `D:\My_projects\lemo-opuscar\kit\whiteboard-vertical\README.md` ni o'qing.

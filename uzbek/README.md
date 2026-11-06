# O'zbek tili uchun AI resurslari

Bot, xakaton loyihasi yoki video o'zbekcha ishlashi kerak bo'lganda. 2026-11-06 da tekshirilgan (mavjudligi, litsenziya,
narx); hech narsa o'rnatilmagan. Baho: **ishlat** · **sinab ko'r** · **kerak emas**.

## Standart to'plam (o'zbekcha xakaton loyihasi)

| Qism | Tanlov |
|---|---|
| Bot | Telegram, Python (aiogram) |
| Matn yaratish (o'zbekcha) | Gemini Flash; agent mantiqi va kod — Claude Sonnet 5.5+. Internetsiz kerak bo'lsa — NeuronAI-Uzbek 4B |
| Nutqni tanish (STT) | `navai-uz` whisper-small (CPU) yoki medium; zaxira — Aisha STT API |
| Ovoz (TTS) | Navoiy (lokal, oldidan `uztextnorm`); tez bulutli zaxira — Azure Madina/Sardor yoki Aisha TTS; video uchun — ElevenLabs v3 |
| Lotin / kirill | Matnni lotinda saqlang, ko'rsatishda UzTransliterator bilan kirillga |
| To'lov | Click yoki Payme — BotFather → Payments orqali (eng tez); web uchun Payme Merchant API sandbox |
| SMS / OTP | Eskiz |
| Xarita | Yandex Maps + joy qidirish uchun 2GIS |
| Ochiq ma'lumot | data.egov.uz ("civic tech" g'oyalar uchun) |

Asosiy ogohlantirish: ochiq STT modellari lotinda, ko'pincha tinish belgisiz va 9–17% xato bilan yozadi. Foydalanuvchiga
ko'rsatiladigan matnni LLM (Gemini) bilan tuzatib oling. O'zbekcha matnni har doim odam o'qib chiqsin.

## Nutqni tanish (STT)

| Nima | Baho | Izoh |
|---|---|---|
| [NavAI Whisper](https://huggingface.co/navai-uz) (medium/small/base/tiny) | **ishlat** | Apache-2.0, 753 soat inson belgilagan audio; medium 9.73 WER. small/base CPU da real. Eng yaxshi ochiq variant |
| [rubaiSTT v2 medium](https://huggingface.co/islomov/rubaistt_v2_medium) | sinab ko'r | Apache-2.0, ~17% WER, Toshkent shevasi |
| [piyola-v2](https://huggingface.co/idrock/piyola-v2) (Parakeet 0.6B) | sinab ko'r | CC-BY-4.0, tez; NeMo kerak, tinish belgisi va raqam yo'q |
| [BuzzASR/uzbek](https://huggingface.co/BuzzASR/uzbek) | faqat GPU bilan | MIT, Whisper large-v3, CPU uchun og'ir |
| [Aisha STT API](https://aisha.group/en/api-documentation) | **ishlat** (API) | 425 so'm/daqiqa, bepul sinov, uz/ru/en |
| Muxlisa AI (muxlisa.uz), Yandex SpeechKit, ElevenLabs Scribe, Google Chirp 3 | sinab ko'r | Muxlisa: narxi ochiq emas; Yandex: call-markazlar uchun; qolganlari zaxira |

## Ovoz (TTS)

| Nima | Baho | Izoh |
|---|---|---|
| Navoiy (`video/navoiy`) | **ishlat** | lokal, o'z ovozingiz, bepul |
| Azure TTS (uz-UZ-MadinaNeural, SardorNeural) | **ishlat** | ishonchli, bepul tarifi bor |
| Aisha TTS API | **ishlat** | 1 so'm/belgi, kayfiyat va tezlik, lotin va kirill |
| ElevenLabs Eleven v3 | sinab ko'r | o'zbekcha rasman bor (v2/Flash da yo'q), video uchun eng jonli, pullik |
| [Uzbek-tts-chatterbox](https://huggingface.co/UAzimov/Uzbek-tts-chatterbox) | sinab ko'r | MIT, ochiq |
| f5-tts-uzbek, abbos2332/uzbek-tts, facebook mms-tts-uzb | kerak emas | NC litsenziya yoki tarqatib bo'lmaydi / robotcha |

## LLM'lar o'zbekchada

[UzLiB](https://github.com/tahrirchi/uzlib/blob/main/LEADERBOARD.md) reytingi (91 model): Gemini 4 Argon 0.844 ·
Gemini 3 Pro 0.826 · Gemini 3.7 Flash 0.809 · GPT-6 Luna 0.809 · **Claude Sonnet 5.5 0.781** · DeepSeek V4.1 Flash 0.748.

- Ko'p o'zbekcha matn va grammatika muhim joyda — Gemini Flash. Agent, kod va interfeys matni — Claude ham yetadi.
- Ochiq: [NeuronAI-Uzbek 4B](https://huggingface.co/NeuronUz/NeuronAI-Uzbek) (Apache-2.0, 0.662) — eng yaxshi kichik
  lokal model. Gemma 4 ~0.55. Behbudiy fine-tune'lari va Qwen3.x — kuchsiz.

## Tarjima, transliteratsiya, imlo

| Nima | Baho | Izoh |
|---|---|---|
| Tarjima: Gemini / Claude; zaxira Google / Yandex Translate API | **ishlat** | Tilmoch (tahrirchi) B2B API — sinab ko'r; NLLB fine-tune'lari NC — kerak emas |
| [UzTransliterator](https://github.com/UlugbekSalaev/UzTransliterator) | **ishlat** | MIT, lotin ↔ kirill, е/ц/ё va istisno so'zlar |
| [uztextnorm](https://pypi.org/project/uztextnorm/) | **ishlat** | raqam va matnni TTS uchun tayyorlaydi (Navoiy oldidan) |
| uzbek-text-tools, uzmorph, hunspell-uz | sinab ko'r | imlo tekshirish, morfologiya |
| Ma'lumotlar: tahrirchi/uz-crawl, uz-books (Apache-2.0); nutq: USC, FeruzaSpeech, Common Voice, FLEURS | — | model sinash yoki fine-tune uchun |

## Mahalliy servislar

| Nima | Baho | Hujjat |
|---|---|---|
| Payme | **ishlat** | https://developer.help.paycom.uz · sandbox: test.paycom.uz |
| Click | **ishlat** | https://docs.click.uz |
| Uzum Checkout | sinab ko'r | https://developer.uzumbank.uz/en/checkout — menejer orqali ulanadi, xakatonga sekin |
| paytechuz (PyPI: Payme, Click, Uzum, Paynet bitta kutubxonada) | sinab ko'r | |
| Eskiz SMS | **ishlat** | https://notify.eskiz.uz/api/ — shablonlar oldindan tasdiqlanishi mumkin, vaqt qoldiring |
| Yandex Maps | **ishlat** | O'zbekistonda eng yaxshi qamrov; bepul 250k geokod/yil, Yandex xaritasida ko'rsatish shart |
| 2GIS API | **ishlat** | https://docs.2gis.com — joylar va kirishlar ma'lumoti |
| OSM / Nominatim, uzgeocoder | sinab ko'r | uzgeocoder: internetsiz viloyat/tuman |
| data.egov.uz | sinab ko'r | ~10k ochiq ma'lumot to'plami, sifati har xil |

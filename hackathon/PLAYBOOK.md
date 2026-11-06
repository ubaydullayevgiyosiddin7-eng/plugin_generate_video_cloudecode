# Xakaton playbook

Manba: o'z tajribamiz (2026-11-05 saralash, ~500 jamoa ichida 1-o'rin: sodda lekin professional sayt, hamma talab
bajarilgan) + hakamlar va g'oliblarning yozganlari (pastda). Har xakatondan keyin `cases/` dagi saboq bilan yangilanadi.

## 1. Hakamlar qanday baholaydi

| Format | Mezonlar |
|---|---|
| Odatiy (ko'p Devpost tadbirlari) | Innovatsiya 25% · Texnik bajarilish 25% · Foyda / ta'sir 20% · Taqdimot 15% · Dizayn / UX 15% (har biri 1–5 yoki 1–10) |
| Devpost klassik | G'oya sifati · Potensial ta'sir · Texnik amalga oshirish · Dizayn — teng ulush |
| ETHGlobal | Texniklik · Originallik · Amaliylik ("foydalanuvchi bugun ishlata oladimi?") · Qulaylik · WOW |
| AI / sponsor xakatonlari | texnik bajarilish va demo ko'proq; ko'pincha "sponsor API'sidan foydalanish" uchun ~10% |
| MLH | jamoaga ~3 daqiqa (2 demo + 1 savol), har hakam o'z top-3 ni tanlaydi (3/2/1 ball) — mukammal emas, har hakamning top-3 ida bo'lish kerak |
| Onlayn | hakam ko'pincha videoni 3:00 da to'xtatadi — video asosiy narsa |

**Yaxshi loyihalar nega yutqazadi:** birinchi gapdan nima ekani tushunarsiz; demo to'xtab qoladi yoki faqat slayd;
butun "platforma" yarim ishlaydi; pitch muammo o'rniga stack bilan boshlanadi; sponsor texnologiyasi ko'rinmaydi; repo
yopiq yoki havola ishlamaydi; majburiy maydon / format yo'q (diskvalifikatsiya); isbotsiz buzzword'lar.

## 2. Qoidalar

1. G'oya tanlashdan **oldin**: qoidalar, mezonlar va ulushlari, hakamlar kimligi, o'tgan g'oliblar. Har soat bitta
   mezonni oldinga surishi kerak.
2. Kod yozishdan oldin bitta gap: "**X — Y uchun, Z qiladi.**" Har bir funksiya shu gapdan o'tadi.
3. **90 soniyalik demo ssenariysini birinchi yoz.** Faqat demoda ko'rinadigan narsa quriladi.
4. Bitta foydalanuvchi, bitta to'liq oqim boshidan oxirigacha. Tor va silliq > keng va buzuq.
5. **Talablar jadvali** (`templates/SPEC.md`): topshiriqdagi har bir talab → qanday bajaramiz → demoda qayerda ko'rinadi.
   Bizning saralashdagi g'alabamiz shu: hamma talab bajarilgan va ko'rinadigan.
6. Jonli havolani erta chiqar (~6-soat), xunuk bo'lsa ham; keyin doim qayta deploy.
7. Vaqtning ~75% ida **feature freeze**. Keyin faqat xato, sayqal va hikoya.
8. Aniq foydalanuvchini ayt ("Toshkentdagi 3–10 xodimli qurilish firmalari"), "bizneslar" emas.
9. Nimani tayyor oldingiz va nima birinchi buziladi — halol ayting; hakamlar buni yuqori baholaydi.
10. Ko'rinadigan mayda narsalar: o'lik havola yo'q, lorem ipsum yo'q, bitta brend, telefonda ishlaydi. Zaxira demo
    video. 4–6 soat uxlash.

## 3. 24 soatlik reja (48 soat: qurish 2–30, sayqal/demo/mashq 30–48)

| Soat | Ish |
|---|---|
| 0–1 | Qoidalar va mezonlarni ochish, g'oya, bir gaplik ta'rif. Rollar: quruvchi(lar), dizayn/frontend, taqdimotchi (pitch va topshirish uning zimmasida) |
| 1–2 | Demo ssenariysi, MVP ni bitta oqimga qisqartirish, talablar jadvali, stack, repo |
| 2–6 | Boshidan oxirigacha ishlaydigan skelet. **Deploy.** Birinchi integratsiya |
| 6–12 | Asosiy funksiya va "wow" lahza. 12-soatda tekshiruv: butun oqim ishlashi shart |
| 12–18 | UI/UX sayqal, demo yo'lidagi chekka holatlar, demo ma'lumotlar. **18-soatda freeze** |
| 18–20 | Toza qurilma va boshqa tarmoqda to'liq test (`playwright-cli`, `spec-reviewer` agenti). Sirlar skani. README |
| 20–22 | Slaydlar, demo video (20-soatdan oldin boshlang), topshirish maydonlari |
| 22–23 | Erta topshirish, keyin pitchni 5+ marta mashq, savollarga tayyorgarlik |
| 23–24 | Zaxira vaqt |

## 4. Pitch (3 daqiqa; 2 yoki 5 ga moslang)

| Vaqt | Nima |
|---|---|
| 0:00–0:20 | "Bu — Y uchun X." Foydalanuvchi og'rig'i bitta aniq gapda, raqam bo'lsa raqam bilan |
| 0:20–0:35 | Nega hozir / mavjud yechimlar nega yetmaydi |
| 0:35–2:05 | **Jonli demo (vaqtning yarmi):** bitta yo'l, haqiqiy ma'lumot, ~1:30 da wow lahza. Qaysi tugmani bosayotganingizni emas, foydalanuvchi nima olishini ayting |
| 2:05–2:30 | Qanday ishlaydi: bitta arxitektura qatori/slaydi + sponsor texnologiyasi |
| 2:30–2:50 | Ta'sir va keyingi qadam: kim ishlatadi, qancha turadi, keyin nima |
| 2:50–3:00 | Bitta xulosa gapi va jamoa |

Slaydlar (5–6): Nom + bir gap / Muammo / Yechim + demo / Qanday ishlaydi / Ta'sir + reja / Jamoa. Jonli demo yiqilsa —
skrinshotli zaxira slayd.

Yozma ta'rif: "**[Kim] uchun [Ilova] [vazifa]ni [usul] orqali bajaradi, natijada ular [natija].**"

Savollarga tayyorlaning: Aniq kim uchun? Bu tadbirda nima qurildi, nima tayyor olindi? Nima birinchi buziladi?
[Raqobatchi]dan farqi? Qanday pul topadi / kengayadi? Ma'lumot haqiqiymi?

Demo video: ≤ 2–3 daqiqa, birinchi 60–90 soniyada ilgak va isbot, haqiqiy ilova haqiqiy qurilmada, subtitr, mualliflik
huquqi bor musiqa yo'q. Video bizning `video/` kit bilan ham qilinadi.

## 5. Topshirish cheklisti

- [ ] Har bir majburiy maydon, format, so'z chegarasi. Talab qilingan sponsor texnologiyasi aniq ko'rsatilgan
- [ ] Repo ochiq. README: bir gap, skrinshot/GIF, jonli havola, video havolasi, funksiyalar, arxitektura, stack,
      ≤ 3 buyruqda ishga tushirish, test login, jamoa, tadbirda nima qurilgani
- [ ] Demo inkognitoda, telefonda va boshqa tarmoqda ishlaydi. Demo ma'lumotlar yuklangan. Git tarixida sir yo'q
- [ ] Video ochiq yoki havola orqali, vaqt chegarasida, loginsiz ochiladi
- [ ] Devpost bo'limlari: Inspiration / What it does / How we built it / Challenges / Accomplishments / What's next
- [ ] Skrinshotlar yangi; nom, tagline, thumbnail bor; har bir havola bosib ko'rilgan
- [ ] Muddatdan kamida 1 soat oldin topshirilgan

## Manbalar

- Hakam eslatmalari: https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l
- Baholash qanday ishlaydi (25/25/20/15/15): https://intercom.help/builderbase/en/articles/14836129-builder-s-guide-ch-15-how-judging-works
- MLH baholash rejasi: https://guide.mlh.com/general-information/judging-and-submissions/judging-plan
- Nega yutqazasiz (~$65k yutgan muallif): https://sliplane.io/blog/this-is-why-you-are-losing-hackathons
- Pitch va demo video: https://www.revenuecat.com/blog/engineering/how-to-win-shipaton-part-4-pitching-your-app
- Yaxshi topshirish: https://dev.to/dorahacks/what-does-a-good-hackathon-submission-look-like-5398 ·
  https://dev.to/jacklynbiggin/how-to-make-your-devpost-submissions-not-suck-37i0
- Tuzilishi uchun o'qilgan (o'rnatilmagan, yangi va tekshirilmagan): github.com/SidTheKid-dotcom/hackathon-playbook (MIT)
- ⛔ abhilashpandurangan/hackathon-prep (litsenziyasiz — faqat g'oya), rajkaria/hackathon-skills (tarmoqqa chiqadigan
  skriptlar, web3) — ~0★, tekshirilmagan; g'oyalari bu playbook'ga o'z so'zimiz bilan olingan

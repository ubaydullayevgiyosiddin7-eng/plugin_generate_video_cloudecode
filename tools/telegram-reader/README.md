# Telegram kanal o'quvchi

Kanal postlarini Markdown faylga yozadi: sana, havola, ko'rishlar soni, fayl nomlari, ichidagi linklar. **Faqat o'qiydi**:
xabar yubormaydi, kanalga o'zi qo'shilmaydi. Yopiq kanallar ham o'qiladi, agar akkaunt ularga a'zo bo'lsa.

Ochiq kanal uchun bu tool shart emas: `https://t.me/s/<kanal_nomi>` sahifasini Claude login qilmasdan o'qiydi.

## Sozlash (bir marta)

1. Ishlatadigan akkaunt bilan kerakli kanallarga Telegram ilovasida qo'shiling. Imkon bo'lsa, alohida akkaunt yaxshiroq.
2. `my.telegram.org` → "API development tools" → `api_id` va `api_hash`.
3. Shu papkada `.env` fayl yarating (chatga yozmang, faylga yozing):
   ```
   TG_API_ID=123456
   TG_API_HASH=abc123...
   ```
4. **O'z terminalingizda** kiring — telefon raqam va kodni o'zingiz kiritasiz:
   ```
   pip install telethon
   python tools/telegram-reader/tg_read.py login
   ```

`.env`, `tg.session` va `state.json` `.gitignore` da — GitHub'ga tushmaydi. `tg.session` akkauntga to'liq kirish beradi,
hech kimga bermang.

## Ishlatish

```
python tools/telegram-reader/tg_read.py channels                              # a'zo bo'lgan kanallar: ID va nom
python tools/telegram-reader/tg_read.py read t.me/+be4CsggOddA4YWEy --limit 200 --out posts.md
python tools/telegram-reader/tg_read.py read @kanal_nomi --new                # faqat oxirgi o'qishdan keyingi postlar
```

`<kanal>`: `t.me/+taklif` havolasi, `@username` yoki `-100...` ID. `--new` qaysi postgacha o'qilganini `state.json` da
eslab qoladi — doimiy kuzatish (`/loop`, `/schedule`) shunga quriladi.

## Kuzatilayotgan kanallar

| Kanal | Havola | Nima uchun |
|---|---|---|
| Jaloliddin Tech \| AI (yopiq, ~3 000 obunachi) | `t.me/+be4CsggOddA4YWEy` | AI, Claude, avtomatlashtirish bo'yicha o'zbekcha kontent |

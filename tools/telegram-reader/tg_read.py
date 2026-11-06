"""Telegram kanal o'quvchi — faqat o'qiydi, hech narsa yubormaydi.

Sozlash (bir marta):
  1. my.telegram.org -> API development tools -> api_id va api_hash
  2. Shu papkada .env fayl:  TG_API_ID=123456
                             TG_API_HASH=abcdef...
  3. O'z terminalingizda:   python tg_read.py login
     (telefon raqam va Telegram yuborgan kodni SIZ kiritasiz)

Ishlatish:
  python tg_read.py channels                          # a'zo bo'lgan kanallar ro'yxati (nom va ID)
  python tg_read.py read <kanal> [--limit 100] [--new] [--out posts.md]
     <kanal>: t.me/+taklif havolasi, @username yoki -100... ID
     --new  : faqat oldingi o'qishdan keyingi yangi postlar (state.json da eslab qoladi)
"""
import argparse, asyncio, json, os, re, sys
from pathlib import Path

from telethon import TelegramClient, functions, types

HERE = Path(__file__).resolve().parent
SESSION = HERE / "tg"          # tg.session — akkauntga to'liq kirish, hech kimga bermang
STATE = HERE / "state.json"


def load_env():
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    try:
        return int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"]
    except KeyError:
        sys.exit("TG_API_ID va TG_API_HASH topilmadi: shu papkada .env yarating (tepadagi izohga qarang).")


async def resolve(client, ref):
    m = re.search(r"(?:t\.me/|telegram\.me/)(?:\+|joinchat/)([\w-]+)", ref)
    if m:  # taklif havolasi: faqat a'zo bo'lsangiz ishlaydi, o'zi qo'shilmaydi
        inv = await client(functions.messages.CheckChatInviteRequest(m.group(1)))
        if isinstance(inv, (types.ChatInviteAlready, types.ChatInvitePeek)):
            return inv.chat
        sys.exit(f"Bu akkaunt '{inv.title}' kanaliga a'zo emas. Avval Telegram ilovasida havola orqali qo'shiling.")
    if re.fullmatch(r"-?\d+", ref):
        want = int(ref)
        async for d in client.iter_dialogs():
            if d.id == want or d.entity.id == abs(want) % 10**10:
                return d.entity
        sys.exit(f"{ref} ID li kanal dialoglar orasida yo'q (akkaunt a'zo emasmi?).")
    return await client.get_entity(ref.lstrip("@").replace("https://t.me/", ""))


def post_md(chat, msg):
    link = f"https://t.me/{chat.username}/{msg.id}" if getattr(chat, "username", None) else f"https://t.me/c/{chat.id}/{msg.id}"
    media = type(msg.media).__name__.replace("MessageMedia", "") if msg.media else ""
    if msg.file and msg.file.name:
        media += f" `{msg.file.name}`"
    urls = sorted({e.url for e, _ in msg.get_entities_text() if isinstance(e, types.MessageEntityTextUrl)})
    head = f"## {msg.date:%Y-%m-%d %H:%M} · [#{msg.id}]({link})"
    if msg.views:
        head += f" · {msg.views} ko'rish"
    parts = [head]
    if media:
        parts.append(f"*Media:* {media}")
    parts.append((msg.message or "").strip() or "_(matnsiz)_")
    if urls:
        parts.append("Havolalar: " + ", ".join(urls))
    return "\n\n".join(parts)


async def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login")
    sub.add_parser("channels")
    r = sub.add_parser("read")
    r.add_argument("channel")
    r.add_argument("--limit", type=int, default=100)
    r.add_argument("--new", action="store_true")
    r.add_argument("--out")
    a = ap.parse_args()

    api_id, api_hash = load_env()
    client = TelegramClient(str(SESSION), api_id, api_hash)

    if a.cmd == "login":
        await client.start()
        me = await client.get_me()
        print(f"Kirildi: {me.first_name} (@{me.username}). Session: {SESSION}.session")
        return

    await client.connect()
    if not await client.is_user_authorized():
        sys.exit("Avval o'z terminalingizda: python tg_read.py login")

    async with client:
        if a.cmd == "channels":
            async for d in client.iter_dialogs():
                if d.is_channel:
                    print(f"{d.id}\t{d.name}")
            return

        chat = await resolve(client, a.channel)
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
        key = str(chat.id)
        min_id = state.get(key, 0) if a.new else 0

        msgs = [m async for m in client.iter_messages(chat, limit=a.limit, min_id=min_id)]
        msgs.reverse()  # eskidan yangiga
        body = "\n\n---\n\n".join(post_md(chat, m) for m in msgs if not isinstance(m, types.MessageService))
        title = f"# {chat.title} — {len(msgs)} ta post\n\n"
        text = title + (body or "_Yangi post yo'q._") + "\n"

        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
            print(f"{len(msgs)} ta post -> {a.out}")
        else:
            sys.stdout.reconfigure(encoding="utf-8")
            print(text)

        if msgs:
            state[key] = max(state.get(key, 0), msgs[-1].id)
            STATE.write_text(json.dumps(state, indent=2))


asyncio.run(main())

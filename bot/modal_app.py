"""Telegram bot for "No-code AI for Young Cambodian Learners", deployed on Modal.

The bot only serves what is listed in bot/published.json (the reviewed chapters). Files are
sent from the public GitHub repo, so publishing a new chapter = update published.json and push.

Setup (see bot/README.md):
  modal secret create book-telegram-bot BOT_TOKEN=... WEBHOOK_SECRET=...
  modal deploy bot/modal_app.py
  modal run bot/modal_app.py --url https://<your-workspace>--book-telegram-bot-web.modal.run
"""
import json
import os
import time

import modal

app = modal.App("book-telegram-bot")
_HERE = os.path.dirname(os.path.abspath(__file__))
image = (modal.Image.debian_slim().pip_install("fastapi[standard]", "httpx")
         .add_local_file(os.path.join(_HERE, "published.json"), "/root/published.json"))
secret = modal.Secret.from_name("book-telegram-bot")

MANIFEST_URL = "https://raw.githubusercontent.com/rinabuoy/no-code-ai-cambodian-learners/main/bot/published.json"
_cache = {"at": 0.0, "data": None}


# ------------------------------------------------------------------ bot logic (no Modal needed)
async def load_manifest(http, ttl=300):
    if _cache["data"] and time.time() - _cache["at"] < ttl:
        return _cache["data"]
    try:
        r = await http.get(MANIFEST_URL, timeout=10)
        r.raise_for_status()
        _cache["data"], _cache["at"] = r.json(), time.time()
    except Exception:
        if not _cache["data"]:   # GitHub unreachable: use the copy bundled at deploy time
            for path in ("/root/published.json", os.path.join(_HERE, "published.json")):
                if os.path.exists(path):
                    _cache["data"], _cache["at"] = json.load(open(path)), time.time() - 240
                    break
            else:
                raise
    return _cache["data"]


def main_menu():
    return {"inline_keyboard": [
        [{"text": "\U0001F4D8 Read the book so far (PDF)", "callback_data": "book"}],
        [{"text": "\U0001F4D6 Chapters", "callback_data": "chapters"}],
        [{"text": "\U0001F49D Support this work", "callback_data": "support"}],
        [{"text": "ℹ️ About the book", "callback_data": "about"}],
    ]}


def back_row():
    return [{"text": "⬅️ Menu", "callback_data": "menu"}]


def welcome(m):
    return (f"Welcome to *{m['book_title']}* by {m['author']}.\n\n"
            "Here you can read the chapters the author has reviewed so far. Choose an option:")


async def handle_update(update, tg, http):
    """tg(method, **payload) calls the Telegram Bot API."""
    m = await load_manifest(http)
    raw = m["raw_base"]
    if "callback_query" in update:
        cq = update["callback_query"]
        chat = cq["message"]["chat"]["id"]
        data = cq.get("data", "")
        await tg("answerCallbackQuery", callback_query_id=cq["id"])
    elif "message" in update and "chat" in update["message"]:
        chat = update["message"]["chat"]["id"]
        text = (update["message"].get("text") or "").strip().lower()
        data = {"/start": "start", "/menu": "menu", "/book": "book", "/chapters": "chapters",
                "/support": "support", "/about": "about", "/help": "menu"}.get(text.split("@")[0], "menu")
    else:
        return

    if data == "start":
        await tg("sendMessage", chat_id=chat, text=welcome(m), parse_mode="Markdown", reply_markup=main_menu())
    elif data == "menu":
        await tg("sendMessage", chat_id=chat, text="What would you like to do?", reply_markup=main_menu())
    elif data == "book":
        await tg("sendDocument", chat_id=chat, document=raw + m["book"]["file"],
                 caption=m["book"]["title"] + "\nDRAFT: only reviewed material is included.")
        await tg("sendMessage", chat_id=chat, text="Anything else?", reply_markup={"inline_keyboard": [back_row()]})
    elif data == "chapters":
        rows = [[{"text": f"Chapter {c['n']}: {c['title']}"[:60], "callback_data": f"ch:{c['n']}"}] for c in m["chapters"]]
        soon = "\n".join(f"- Chapter {c['n']}: {c['title']}" for c in m["coming_soon"])
        msg = "*Reviewed chapters* (tap to download the PDF):"
        if soon:
            msg += "\n\n*Not yet published* (coming as the author reviews them):\n" + soon
        await tg("sendMessage", chat_id=chat, text=msg, parse_mode="Markdown",
                 reply_markup={"inline_keyboard": rows + [back_row()]})
    elif data.startswith("ch:"):
        ch = next((c for c in m["chapters"] if str(c["n"]) == data[3:]), None)
        if ch is None:
            await tg("sendMessage", chat_id=chat, text="That chapter is not published yet.",
                     reply_markup={"inline_keyboard": [back_row()]})
        else:
            await tg("sendDocument", chat_id=chat, document=raw + ch["file"],
                     caption=f"Chapter {ch['n']}: {ch['title']}\nDRAFT edition")
            await tg("sendMessage", chat_id=chat, text="Anything else?",
                     reply_markup={"inline_keyboard": [[{"text": "\U0001F4D6 Chapters", "callback_data": "chapters"}], back_row()]})
    elif data == "support":
        rows = [[{"text": f"${s['amount']}", "callback_data": f"donate:{s['amount']}"} for s in m["support"]]]
        await tg("sendMessage", chat_id=chat, parse_mode="Markdown",
                 text=("*Support this work*\nThe goal is a complete reviewed book by the end of 2026, with a free soft copy "
                       "and a low-cost hard copy. You can help by donating *$2, $5 or $10* with ABA / KHQR. Choose an amount:"),
                 reply_markup={"inline_keyboard": rows + [back_row()]})
    elif data.startswith("donate:"):
        s = next((x for x in m["support"] if str(x["amount"]) == data[7:]), None)
        if s is None:
            return
        await tg("sendPhoto", chat_id=chat, photo=raw + s["file"],
                 caption=f"ABA KHQR, ${s['amount']}. Open your banking app and scan this code. Thank you for your support!")
        await tg("sendMessage", chat_id=chat, text="Thank you!", reply_markup={"inline_keyboard": [back_row()]})
    elif data == "about":
        await tg("sendMessage", chat_id=chat, text=m["about"] + "\n\nSource: " + m["repo_url"],
                 reply_markup={"inline_keyboard": [back_row()]})


# ------------------------------------------------------------------ Modal wiring
@app.function(image=image, secrets=[secret])
@modal.asgi_app()
def web():
    import os

    import httpx
    from fastapi import FastAPI, Header, HTTPException, Request

    api = FastAPI()
    token = os.environ["BOT_TOKEN"]
    secret_token = os.environ["WEBHOOK_SECRET"]

    @api.post("/")
    async def webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(default="")):
        if x_telegram_bot_api_secret_token != secret_token:
            raise HTTPException(status_code=403)
        update = await request.json()
        async with httpx.AsyncClient() as http:
            async def tg(method, **payload):
                r = await http.post(f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=30)
                return r.json()
            try:
                await handle_update(update, tg, http)
            except Exception as e:  # never make Telegram retry forever
                print("handler error:", repr(e))
        return {"ok": True}

    @api.get("/")
    async def health():
        return {"status": "ok"}

    return api


@app.function(image=image, secrets=[secret])
def register(url: str):
    """Point the Telegram webhook at the deployed URL."""
    import os

    import httpx
    r = httpx.post(f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}/setWebhook",
                   json={"url": url, "secret_token": os.environ["WEBHOOK_SECRET"],
                         "allowed_updates": ["message", "callback_query"]}, timeout=30)
    print(r.json())


@app.local_entrypoint()
def main(url: str):
    register.remote(url)

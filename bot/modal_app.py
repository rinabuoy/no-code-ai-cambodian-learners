"""Telegram bot for "No-code AI for Young Cambodian Learners", deployed on Modal.

The bot shows the reviewed chapters, the appendices and the author page as formatted TEXT
(no PDFs), read from the Markdown files in the public GitHub repo. What is listed in
bot/published.json is all it will serve, so unreviewed chapters never appear.

Setup (see bot/README.md):
  modal secret create book-telegram-bot BOT_TOKEN=... WEBHOOK_SECRET=...
  modal deploy bot/modal_app.py
  modal run bot/modal_app.py --url https://<your-workspace>--book-telegram-bot-web.modal.run
"""
import html as _html
import json
import os
import re
import time

import modal

app = modal.App("book-telegram-bot")
_HERE = os.path.dirname(os.path.abspath(__file__))
image = (modal.Image.debian_slim().pip_install("fastapi[standard]", "httpx")
         .add_local_file(os.path.join(_HERE, "published.json"), "/root/published.json"))
secret = modal.Secret.from_name("book-telegram-bot")

RAW = "https://raw.githubusercontent.com/rinabuoy/no-code-ai-cambodian-learners/main/"
MANIFEST_URL = RAW + "bot/published.json"
MAX_MSG = 3800
_cache = {}   # url -> (time, data)


# ------------------------------------------------------------------ fetching
async def fetch(http, url, as_json=False, ttl=300):
    hit = _cache.get(url)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    try:
        r = await http.get(url, timeout=15)
        r.raise_for_status()
        data = r.json() if as_json else r.text
    except Exception:
        if hit:
            return hit[1]
        if as_json:   # GitHub unreachable: use the manifest bundled at deploy time
            for path in ("/root/published.json", os.path.join(_HERE, "published.json")):
                if os.path.exists(path):
                    data = json.load(open(path, encoding="utf-8"))
                    _cache[url] = (time.time() - ttl + 30, data)
                    return data
        raise
    _cache[url] = (time.time(), data)
    return data


# ------------------------------------------------------------------ Markdown -> Telegram HTML
def esc(s):
    return _html.escape(s, quote=False)


def inline(s):
    s = re.sub(r"\^\[([^\]]+)\]", r" (\1)", s)                      # footnotes -> (text)
    s = re.sub(r"(^|[.!?]\s+)Figure @fig:[\w-]+", r"\1The figure", s)
    s = re.sub(r"Figure @fig:[\w-]+", "the figure", s)
    out = []
    for i, part in enumerate(re.split(r"(`[^`]+`)", s)):
        if i % 2:
            out.append("<code>" + esc(part[1:-1]) + "</code>")
            continue
        t = esc(part)
        t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
        out.append(t)
    return "".join(out)


def plain(s):
    return _html.unescape(re.sub(r"<[^>]+>", "", s))


def blocks(md):
    """Markdown (no heading handling) -> list of HTML blocks."""
    lines, out, i = md.split("\n"), [], 0
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s or re.match(r"^<!--.*-->$", s) or s == "---":
            i += 1
            continue
        if s.startswith("*Draft notes.*"):
            i += 1
            continue
        m = re.match(r"^#{3,4}\s+(.*)$", s)
        if m:
            out.append("<b>" + inline(m.group(1)) + "</b>")
            i += 1
            continue
        m = re.match(r"^!\[(.*?)\]\(", s)
        if m:
            out.append("\U0001F5BC <i>" + inline(m.group(1)) + "</i>")
            i += 1
            continue
        if s.startswith(">"):
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>" + inline(" ".join(x for x in q if x)) + "</blockquote>")
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            if rows:
                body = ["<i>" + " | ".join(inline(c) for c in rows[0] if c) + "</i>"]
                for r in rows[1:]:
                    cs = [inline(c) for c in r]
                    body.append("• <b>" + cs[0] + "</b>" + ("".join(" — " + c for c in cs[1:] if c)))
                out.append("\n".join(body))
            continue
        if re.match(r"^(\s*)([-*]|\d+\.)\s+", ln):
            items = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("#", ">", "|", "!")):
                l2 = lines[i].rstrip()
                m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", l2)
                if m and len(m.group(1)) < 2:
                    bullet = "•" if m.group(2) in "-*" else m.group(2)
                    items.append(f"{bullet} " + inline(m.group(3)))
                elif items:
                    items[-1] += "\n    " + inline(l2.strip())
                i += 1
            out.append("\n".join(items))
            continue
        para = [s]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|>|\||!\[|[-*]\s|\d+\.\s|<!--|---)", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append(inline(" ".join(para)))
    return out


def pack(parts, limit=MAX_MSG):
    """Join HTML blocks into messages under the Telegram length limit."""
    msgs, cur = [], ""
    for p in parts:
        if len(p) > limit:                      # very long block: split on lines
            lines, buf = p.split("\n"), ""
            for ln in lines:
                if buf and len(buf) + len(ln) + 1 > limit:
                    msgs.append(buf)
                    buf = ""
                buf = (buf + "\n" + ln) if buf else ln
            p = buf
        if cur and len(cur) + len(p) + 2 > limit:
            msgs.append(cur)
            cur = ""
        cur = (cur + "\n\n" + p) if cur else p
    if cur:
        msgs.append(cur)
    return msgs


def parse_doc(md, intro="Chapter at a glance"):
    """-> (title, [(section_title, [message, ...]), ...])"""
    md = re.sub(r"^---\n.*?\n---\n", "", md, count=1, flags=re.S)
    md = md.split("<!-- wiki-nav -->")[0]
    title, secs, cur_t, cur_lines = "", [], None, []
    for ln in md.split("\n"):
        m1 = re.match(r"^#\s+(.*)$", ln)
        m2 = re.match(r"^##\s+(.*)$", ln)
        if m1 and not title:
            title = re.sub(r"\*", "", m1.group(1)).strip()
        elif m2:
            secs.append((cur_t, cur_lines))
            cur_t, cur_lines = re.sub(r"[*`]", "", m2.group(1)).strip(), []
        else:
            cur_lines.append(ln)
    secs.append((cur_t, cur_lines))
    out = []
    for t, ls in secs:
        if t is None:
            t = intro if any(l.startswith(">") for l in ls) else "Introduction"
        if re.match(r"^Related", t):
            continue
        body = blocks("\n".join(ls))
        if not any(b for b in body):
            continue
        out.append((t, pack(["<b>" + esc(t) + "</b>"] + body)))
    return title, out


# ------------------------------------------------------------------ keyboards and text
def btn(text, data):
    return {"text": text[:60], "callback_data": data}


def main_menu():
    return {"inline_keyboard": [
        [btn("\U0001F4D6 Chapters", "chapters")],
        [btn("\U0001F9EA Appendices (for curious readers)", "appendices")],
        [btn("\U0001F464 About the author", "author")],
        [btn("\U0001F49D Support this work", "support")],
        [btn("ℹ️ About the book", "about")],
    ]}


MENU_ROW = [btn("\U0001F3E0 Menu", "menu")]


def welcome(m):
    return (f"Welcome to <b>{esc(m['book_title'])}</b> by {esc(m['author'])}.\n\n"
            "Read the chapters the author has reviewed so far, right here in Telegram. Choose an option:")


# ------------------------------------------------------------------ bot logic
async def send(tg, chat, text, markup=None):
    payload = {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if markup:
        payload["reply_markup"] = markup
    r = await tg("sendMessage", **payload)
    if isinstance(r, dict) and r.get("ok") is False and "parse" in str(r.get("description", "")).lower():
        payload.pop("parse_mode")
        payload["text"] = plain(text)
        await tg("sendMessage", **payload)


async def load_doc(m, d, http):
    md = await fetch(http, RAW + d["md"])
    return parse_doc(md, "Chapter at a glance" if d["kind"] == "chapter" else "About this appendix")


def find_doc(m, doc_id):
    return next((d for d in m["docs"] if d["id"] == doc_id), None)


def doc_label(d):
    return f"Chapter {d['n']}: {d['title']}" if d["kind"] == "chapter" else f"Appendix {d['n']}: {d['title']}"


async def show_contents(tg, chat, m, d, http):
    _, secs = await load_doc(m, d, http)
    rows = [[btn(("▶️ Start: " if i == 0 else "") + t, f"s:{d['id']}:{i}")] for i, (t, _) in enumerate(secs)]
    back = "chapters" if d["kind"] == "chapter" else "appendices"
    await send(tg, chat, f"<b>{esc(doc_label(d))}</b>\nChoose a section:",
               {"inline_keyboard": rows + [[btn("⬅️ Back", back)], MENU_ROW]})


async def show_section(tg, chat, m, d, idx, http):
    _, secs = await load_doc(m, d, http)
    if not 0 <= idx < len(secs):
        return
    msgs = secs[idx][1]
    for msg in msgs[:-1]:
        await send(tg, chat, msg)
    nav = []
    if idx > 0:
        nav.append(btn("◀️ Previous", f"s:{d['id']}:{idx - 1}"))
    if idx < len(secs) - 1:
        nav.append(btn("Next ▶️", f"s:{d['id']}:{idx + 1}"))
    markup = {"inline_keyboard": ([nav] if nav else []) + [[btn("\U0001F4D1 Contents", f"d:{d['id']}"), MENU_ROW[0]]]}
    await send(tg, chat, msgs[-1], markup)


async def handle_update(update, tg, http):
    """tg(method, **payload) calls the Telegram Bot API."""
    m = await fetch(http, MANIFEST_URL, as_json=True)
    if "callback_query" in update:
        cq = update["callback_query"]
        chat = cq["message"]["chat"]["id"]
        data = cq.get("data", "")
        await tg("answerCallbackQuery", callback_query_id=cq["id"])
    elif "message" in update and "chat" in update["message"]:
        chat = update["message"]["chat"]["id"]
        text = (update["message"].get("text") or "").strip().lower()
        data = {"/start": "start", "/menu": "menu", "/chapters": "chapters", "/appendices": "appendices",
                "/author": "author", "/support": "support", "/about": "about", "/help": "menu"}.get(text.split("@")[0], "menu")
    else:
        return

    if data == "start":
        await send(tg, chat, welcome(m), main_menu())
    elif data == "menu":
        await send(tg, chat, "What would you like to do?", main_menu())
    elif data == "chapters":
        chs = [d for d in m["docs"] if d["kind"] == "chapter"]
        rows = [[btn(doc_label(d), f"d:{d['id']}")] for d in chs]
        soon = "\n".join(f"• Chapter {c['n']}: {esc(c['title'])}" for c in m["coming_soon"])
        msg = "<b>Reviewed chapters</b> (tap to read):"
        if soon:
            msg += "\n\n<b>Not yet published</b> (coming as the author reviews them):\n" + soon
        await send(tg, chat, msg, {"inline_keyboard": rows + [MENU_ROW]})
    elif data == "appendices":
        aps = [d for d in m["docs"] if d["kind"] == "appendix"]
        rows = [[btn(doc_label(d), f"d:{d['id']}")] for d in aps]
        await send(tg, chat, "<b>Appendices</b>\nOptional background for interested readers:",
                   {"inline_keyboard": rows + [MENU_ROW]})
    elif data.startswith("d:"):
        d = find_doc(m, data[2:])
        if d:
            await show_contents(tg, chat, m, d, http)
    elif data.startswith("s:"):
        _, doc_id, idx = data.split(":")
        d = find_doc(m, doc_id)
        if d:
            await show_section(tg, chat, m, d, int(idx), http)
    elif data == "author":
        md = await fetch(http, RAW + m["author_md"])
        msgs = pack(["<b>About the Author</b>"] + blocks(re.sub(r"^---\n.*?\n---\n", "", md, count=1, flags=re.S)))
        for msg in msgs[:-1]:
            await send(tg, chat, msg)
        await send(tg, chat, msgs[-1], {"inline_keyboard": [MENU_ROW]})
    elif data == "support":
        rows = [[btn(f"${s['amount']}", f"donate:{s['amount']}") for s in m["support"]]]
        await send(tg, chat, ("<b>Support this work</b>\nThe goal is a complete reviewed book by the end of 2026, with a free "
                              "soft copy and a low-cost hard copy. You can help by donating <b>$2, $5 or $10</b> with ABA / KHQR. "
                              "Choose an amount:"), {"inline_keyboard": rows + [MENU_ROW]})
    elif data.startswith("donate:"):
        s = next((x for x in m["support"] if str(x["amount"]) == data[7:]), None)
        if s is None:
            return
        await tg("sendPhoto", chat_id=chat, photo=RAW + s["file"],
                 caption=f"ABA KHQR, ${s['amount']}. Open your banking app and scan this code. Thank you for your support!")
        await send(tg, chat, "Thank you!", {"inline_keyboard": [MENU_ROW]})
    elif data == "about":
        await send(tg, chat, esc(m["about"]) + "\n\nSource: " + esc(m["repo_url"]), {"inline_keyboard": [MENU_ROW]})


# ------------------------------------------------------------------ Modal wiring
@app.function(image=image, secrets=[secret])
@modal.asgi_app()
def web():
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
    import httpx
    r = httpx.post(f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}/setWebhook",
                   json={"url": url, "secret_token": os.environ["WEBHOOK_SECRET"],
                         "allowed_updates": ["message", "callback_query"]}, timeout=30)
    print(r.json())


@app.local_entrypoint()
def main(url: str):
    register.remote(url)

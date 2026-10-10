# Telegram bot (Modal)

A Telegram bot for *No-code AI for Young Cambodian Learners*. It serves **only the reviewed chapters** listed in `published.json`, and lets readers support the work with the ABA KHQR codes.

**Menu:** read the book so far (PDF) · chapters (tap to download Chapter 1, 2 or 3; Chapters 4–9 are listed by title as "not yet published") · support this work ($2, $5, $10 QR codes) · about the book.

Files are sent from this public repo, and the bot reloads `published.json` every few minutes. **To publish a new reviewed chapter:** add its PDF under `book/public/`, add it to `chapters` in `published.json` (and remove it from `coming_soon`), and push. No redeploy is needed.

## Deploy
1. In Telegram, open **@BotFather** → `/newbot` and copy the bot token. Keep it secret.
2. Install and log in to Modal: `pip install modal` then `modal setup`.
3. Store the secrets in Modal (pick any long random string for `WEBHOOK_SECRET`):
   `modal secret create book-telegram-bot BOT_TOKEN=<token> WEBHOOK_SECRET=<random>`
4. Deploy: `modal deploy bot/modal_app.py`. It prints the web URL (ends in `.modal.run`).
5. Point Telegram at it: `modal run bot/modal_app.py --url <that web URL>`.
6. Message your bot `/start`.

Commands: `/start`, `/menu`, `/book`, `/chapters`, `/support`, `/about`.

# Telegram bot (Modal)

A Telegram bot for *No-code AI for Young Cambodian Learners*. It serves **only the reviewed chapters** listed in `published.json`, and lets readers support the work with the ABA KHQR codes.

**Menu:** chapters · appendices · about the author · support this work ($2, $5, $10 QR codes) · about the book. Chapters, appendices and the author page are shown **as formatted text** in the chat (no PDFs): pick a chapter, choose a section, then use Previous / Next. Figures appear as a short caption line. Chapters 4–9 are listed by title as "not yet published".

Text is read from the Markdown files in this public repo, and the bot reloads `published.json` and the files every few minutes. **To publish a new reviewed chapter:** add an entry for its Markdown file to `docs` in `published.json` (and remove it from `coming_soon`), and push. No redeploy is needed.

## Deploy
1. In Telegram, open **@BotFather** → `/newbot` and copy the bot token. Keep it secret.
2. Install and log in to Modal: `pip install modal` then `modal setup`.
3. Store the secrets in Modal (pick any long random string for `WEBHOOK_SECRET`):
   `modal secret create book-telegram-bot BOT_TOKEN=<token> WEBHOOK_SECRET=<random>`
4. Deploy: `modal deploy bot/modal_app.py`. It prints the web URL (ends in `.modal.run`).
5. Point Telegram at it: `modal run bot/modal_app.py --url <that web URL>`.
6. Message your bot `/start`.

Commands: `/start`, `/menu`, `/chapters`, `/appendices`, `/author`, `/support`, `/about`.

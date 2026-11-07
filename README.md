# Gift Parser

Private Telegram bot project for monitoring Telegram NFT gift listings.

## Current status

- [x] Bot foundation (aiogram 3)
- [x] SQLite persistence and event deduplication
- [x] Normalized listing/seller models
- [x] Notification formatter
- [ ] Verified Telegram-market event source
- [ ] Seller resolution with evidence levels
- [ ] Reconnect recovery and integration tests

## Setup

Python 3.11+

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```env
BOT_TOKEN=your_bot_token
ADMIN_ID=your_numeric_telegram_id
```

Run:

```bash
python -m app.bot
```

Open the bot and send `/start`.

## Important source/API note

The Telegram Bot API does not provide a public feed of all marketplace listings.
A marketplace adapter must use a documented/authorized data source. The adapter
is kept separate so the bot, database, and message format do not depend on a
particular provider.

Before connecting an external data API, verify its current terms. For example,
the see.tg API documentation describes live listing events and owner-resolution
methods, but also restricts using the API to build a competing standalone gift
search/owner-catalog/alert service. This project must not bypass those terms.

## Seller identity

Seller data is represented with a confidence/evidence field. A display-name
match alone is not proof of identity. If a source hides the account or does not
expose a Telegram ID/username, the bot reports it as unknown instead of guessing.

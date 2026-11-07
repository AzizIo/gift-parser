# Gift Parser

Private Telegram bot for monitoring collectible gifts listed in Telegram's built-in Gift Market.

## Current status

- [x] Bot foundation (aiogram 3)
- [x] SQLite persistence and event deduplication
- [x] Official Telegram MTProto resale-market source
- [x] Gift model/backdrop/pattern and Stars/TON price parsing
- [x] Seller peer ID / username / name / TON-wallet extraction when Telegram exposes it
- [x] Silent first scan to avoid flooding the chat with old listings
- [ ] Live VPS integration test with an authorized user session
- [ ] Improve coverage beyond the first resale page per gift type

## Source: official Telegram MTProto API

The collector uses two documented Telegram methods:

- `payments.getStarGifts` — discovers base gift types with resale availability.
- `payments.getResaleStarGifts` — retrieves collectible gifts currently listed for resale for each base gift type.

Important source limitations:

- `payments.getResaleStarGifts` is user-only. A Bot API token is not sufficient; the collector needs a separately authorized Telegram user session.
- This is snapshot polling, not a Telegram push/WebSocket stream. Results are sorted by most recent resale-price change by default.
- Telegram provides optional `owner_id`, `owner_name`, and `owner_address` fields. The account ID/username can only be shown when Telegram actually returns a peer. A display name or wallet address is not proof of a Telegram account.
- The current implementation polls the first page for each gift type. Listings beyond that page are not exhaustively scanned on each cycle. Telegram may also impose flood waits; the client respects them.
- The first scan on a new database is silent to avoid sending a flood of old active listings.

Official docs:
- https://core.telegram.org/api/gifts
- https://core.telegram.org/method/payments.getResaleStarGifts
- https://docs.telethon.dev/en/stable/basic/signing-in.html

## Requirements

Python 3.11+

## 1. Create Telegram API credentials

Go to https://my.telegram.org → API Development Tools and create an application.
You need `api_id` and `api_hash`. Keep the hash private.

## 2. Configure

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env`:

```env
BOT_TOKEN=your_bot_token
ADMIN_ID=your_numeric_telegram_id
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=your_api_hash
# Optional; if empty, auth command asks interactively.
TELEGRAM_PHONE=+123456789
```

## 3. Authorize the user session

```bash
python -m app.auth
```

Enter the Telegram login code and 2FA password in the terminal when prompted.
This creates `data/telegram_market.session`.

**The session file grants access to your Telegram account. Never send it to anyone, commit it, or upload it to a public server.** Keep it on the VPS with restricted file permissions.

## 4. Check owner visibility from your own Telegram session

Run a small read-only sample against the current MTProto API:

```bash
python -m app.diagnostics
```

It reports only counts and public gift slugs. It does not print Telegram IDs,
usernames, names, phone numbers, session data, or API credentials. In
particular, it distinguishes listings where Telegram returned `owner_id`,
`owner_name` only, or a TON `owner_address`.

This is the practical check for whether the October 22 public-page privacy
change is also reflected in MTProto responses for your account.

## 5. Run the notification bot

```bash
python -m app.bot
```

Open your BotFather-created bot, send `/start`, then use `/status`.

## Configuration

- `POLL_INTERVAL_SECONDS` — minimum pause between full scan cycles (default 45).
- `REQUEST_DELAY_SECONDS` — pause between gift-type requests (default 0.25).
- `RESALE_PAGE_SIZE` — first-page size per gift type (default 100).

The full scan duration depends on the number of gift types that currently have resale inventory and Telegram rate limits. A requested interval is a target minimum pause after a cycle, not a guaranteed end-to-end latency.

## Seller identity

Seller resolution uses only data returned by Telegram itself:

- `owner_id` + returned user/chat data: Telegram peer ID, with username/profile link when available.
- `owner_name` without `owner_id`: display name only; no account is guessed.
- `owner_address`: TON wallet address, not a Telegram user ID.

The collector does not try to bypass Telegram privacy controls or infer identity from a name match.

from pathlib import Path
import aiosqlite
from app.models import GiftListing


class Database:
    def __init__(self, path: str):
        self.path = path

    async def initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS listings (
                    event_id TEXT PRIMARY KEY,
                    gift_ref TEXT NOT NULL,
                    title TEXT NOT NULL,
                    gift_url TEXT NOT NULL,
                    price TEXT,
                    currency TEXT,
                    market TEXT NOT NULL,
                    seller_username TEXT,
                    seller_id INTEGER,
                    seller_confidence TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def is_empty(self) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT 1 FROM listings LIMIT 1")
            return await cursor.fetchone() is None

    async def has_event(self, event_id: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM listings WHERE event_id = ?", (event_id,)
            )
            return await cursor.fetchone() is not None

    async def save_listing(self, listing: GiftListing) -> bool:
        seller = listing.seller
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("""
                INSERT OR IGNORE INTO listings (
                    event_id, gift_ref, title, gift_url, price, currency, market,
                    seller_username, seller_id, seller_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                listing.event_id, listing.gift_ref, listing.title, listing.gift_url,
                str(listing.price) if listing.price is not None else None,
                listing.currency, listing.market,
                seller.username if seller else None,
                seller.telegram_id if seller else None,
                seller.confidence if seller else "unknown",
            ))
            await db.commit()
            return cursor.rowcount == 1

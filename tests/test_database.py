import asyncio

from app.database import Database
from app.models import GiftListing, Seller


def test_database_initializes_and_deduplicates(tmp_path):
    async def scenario():
        database = Database(str(tmp_path / "test.sqlite3"))
        await database.initialize()

        assert await database.is_empty()

        listing = GiftListing(
            event_id="event-1",
            gift_ref="InputKey-84682",
            title="Input Key #84682",
            gift_url="https://t.me/nft/InputKey-84682",
            price=None,
            currency=None,
            market="telegram",
            seller=Seller(display_name="Hidden seller", confidence="name_only"),
        )

        assert await database.save_listing(listing) is True
        assert await database.save_listing(listing) is False
        assert await database.has_event("event-1") is True
        assert await database.is_empty() is False

    asyncio.run(scenario())

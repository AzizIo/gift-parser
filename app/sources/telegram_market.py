from collections.abc import AsyncIterator
from app.models import GiftListing
from app.sources.base import MarketplaceSource


class TelegramMarketSource(MarketplaceSource):
    async def listen(self) -> AsyncIterator[GiftListing]:
        """
        Marketplace adapter is intentionally not implemented yet.

        Telegram Bot API does not expose a public stream of every marketplace
        listing. Before implementing this adapter, select a permitted data
        source and verify its current API contract and terms.
        """
        if False:
            yield GiftListing(
                event_id="", gift_ref="", title="", gift_url="",
                price=None, currency=None, market="telegram"
            )
        raise RuntimeError(
            "Источник Telegram Market ещё не настроен. "
            "Нужно подтвердить доступный API/MTProto источник и его условия."
        )

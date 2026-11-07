from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from app.models import GiftListing


class MarketplaceSource(ABC):
    @abstractmethod
    async def listen(self) -> AsyncIterator[GiftListing]:
        """Yield normalized new listings from a marketplace source."""
        raise NotImplementedError

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class Seller:
    display_name: str | None = None
    username: str | None = None
    telegram_id: int | None = None
    profile_url: str | None = None
    confidence: str = "unknown"
    evidence: str | None = None
    wallet_address: str | None = None


@dataclass(slots=True)
class GiftListing:
    event_id: str
    gift_ref: str
    title: str
    gift_url: str
    price: Decimal | None
    currency: str | None
    market: str
    model: str | None = None
    backdrop: str | None = None
    pattern: str | None = None
    seller: Seller | None = None
    raw: dict[str, Any] | None = None
    price_labels: tuple[str, ...] = field(default_factory=tuple)
    initial_snapshot: bool = False

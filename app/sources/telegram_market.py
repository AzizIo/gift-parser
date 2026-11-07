import asyncio
import hashlib
import logging
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path
from typing import Any

from telethon import TelegramClient, functions
from telethon.errors import FloodWaitError

from app.models import GiftListing, Seller
from app.sources.base import MarketplaceSource
from config import settings

log = logging.getLogger(__name__)


class TelegramMarketSource(MarketplaceSource):
    """Reads public resale listings through Telegram's documented user MTProto API.

    The method is user-only and returns a snapshot, not a push event stream.
    We poll the first page of each gift type; Telegram's default ordering is by
    the time when the resale price was last changed (newest first).
    """

    def __init__(self, silent_initial_snapshot: bool = False):
        self.silent_initial_snapshot = silent_initial_snapshot
        self.client: TelegramClient | None = None
        self._gift_types: list[Any] = []
        self._catalog_loaded_at = 0.0

    async def listen(self) -> AsyncIterator[GiftListing]:
        if not settings.telegram_api_id or not settings.telegram_api_hash:
            raise RuntimeError("Заполни TELEGRAM_API_ID и TELEGRAM_API_HASH в .env")

        Path(settings.telegram_session_path).parent.mkdir(parents=True, exist_ok=True)
        self.client = TelegramClient(
            settings.telegram_session_path,
            settings.telegram_api_id,
            settings.telegram_api_hash,
            flood_sleep_threshold=60,
            request_retries=5,
            connection_retries=5,
            auto_reconnect=True,
        )
        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                raise RuntimeError(
                    "MTProto-сессия не авторизована. Сначала выполни: python -m app.auth"
                )

            log.info("Telegram MTProto подключён; начинаем опрос Gift Market")
            first_cycle = True

            while True:
                cycle_started = asyncio.get_running_loop().time()
                await self._refresh_gift_types_if_needed()

                for gift_type in self._gift_types:
                    gift_id = int(gift_type.id)
                    try:
                        result = await self.client(
                            functions.payments.GetResaleStarGiftsRequest(
                                gift_id=gift_id,
                                offset="",
                                limit=settings.resale_page_size,
                            )
                        )
                        for gift in result.gifts:
                            listing = self._to_listing(gift, result)
                            if listing is None:
                                continue
                            listing.initial_snapshot = (
                                first_cycle and self.silent_initial_snapshot
                            )
                            yield listing

                    except FloodWaitError as exc:
                        log.warning("Telegram flood wait: %s sec", exc.seconds)
                        await asyncio.sleep(exc.seconds + 1)
                    except Exception:
                        log.exception("Не удалось получить resale для gift_id=%s", gift_id)

                    await asyncio.sleep(settings.request_delay_seconds)

                first_cycle = False
                elapsed = asyncio.get_running_loop().time() - cycle_started
                sleep_for = max(1.0, settings.poll_interval_seconds - elapsed)
                log.info(
                    "Цикл рынка завершён: типов=%s, длительность=%.1fs, пауза=%.1fs",
                    len(self._gift_types), elapsed, sleep_for,
                )
                await asyncio.sleep(sleep_for)
        finally:
            if self.client:
                await self.client.disconnect()
                self.client = None

    async def _refresh_gift_types_if_needed(self) -> None:
        loop = asyncio.get_running_loop()
        now = loop.time()
        if self._gift_types and now - self._catalog_loaded_at < 900:
            return

        assert self.client is not None
        result = await self.client(
            functions.payments.GetStarGiftsRequest(hash=0)
        )
        self._gift_types = [
            gift for gift in getattr(result, "gifts", [])
            if int(getattr(gift, "availability_resale", 0) or 0) > 0
        ]
        self._catalog_loaded_at = now
        log.info("Обновлён каталог: %s типов доступны для перепродажи", len(self._gift_types))

    def _to_listing(self, gift: Any, response: Any) -> GiftListing | None:
        # Resale responses contain collectible StarGiftUnique objects.
        if not hasattr(gift, "slug") or not getattr(gift, "slug", None):
            return None

        slug = str(gift.slug)
        number = getattr(gift, "num", None)
        title = str(getattr(gift, "title", None) or "Telegram Gift")
        display_title = f"{title} #{number}" if number is not None else title
        prices = self._format_prices(getattr(gift, "resell_amount", None))
        primary_amount, primary_currency = self._primary_price(
            getattr(gift, "resell_amount", None)
        )

        attrs = list(getattr(gift, "attributes", None) or [])
        model = backdrop = pattern = None
        for attr in attrs:
            class_name = type(attr).__name__.lower()
            name = getattr(attr, "name", None)
            rarity = self._rarity_text(getattr(attr, "rarity", None))
            value = f"{name} {rarity}".strip() if name else None
            if "model" in class_name:
                model = value
            elif "backdrop" in class_name:
                backdrop = value
            elif "pattern" in class_name:
                pattern = value

        seller = self._resolve_seller(gift, response)
        fingerprint = "|".join((slug, *(prices or ["no-price"])))
        event_id = hashlib.sha256(fingerprint.encode()).hexdigest()

        return GiftListing(
            event_id=event_id,
            gift_ref=slug,
            title=display_title,
            gift_url=f"https://t.me/nft/{slug}",
            price=primary_amount,
            currency=primary_currency,
            market="telegram",
            model=model,
            backdrop=backdrop,
            pattern=pattern,
            seller=seller,
            raw={"gift_id": getattr(gift, "id", None), "slug": slug},
            price_labels=tuple(prices),
        )

    @staticmethod
    def _format_prices(amounts: Any) -> list[str]:
        labels: list[str] = []
        for amount in amounts or []:
            class_name = type(amount).__name__.lower()
            raw_amount = int(getattr(amount, "amount", 0) or 0)
            if "ton" in class_name:
                value = Decimal(raw_amount) / Decimal(1_000_000_000)
                labels.append(f"{format(value.normalize(), 'f')} TON")
            else:
                nanos = int(getattr(amount, "nanos", 0) or 0)
                value = Decimal(raw_amount) + Decimal(nanos) / Decimal(1_000_000_000)
                labels.append(f"{format(value.normalize(), 'f')} Stars")
        return labels

    @staticmethod
    def _primary_price(amounts: Any) -> tuple[Decimal | None, str | None]:
        formatted = TelegramMarketSource._format_prices(amounts)
        if not formatted:
            return None, None
        label = formatted[0]
        parts = label.rsplit(" ", 1)
        try:
            return Decimal(parts[0]), parts[1]
        except (ValueError, IndexError):
            return None, None

    @staticmethod
    def _rarity_text(rarity: Any) -> str:
        if rarity is None:
            return ""
        permille = getattr(rarity, "permille", None)
        if permille is not None:
            percentage = Decimal(int(permille)) / Decimal(10)
            return f"{format(percentage.normalize(), 'f')}%"
        name = type(rarity).__name__.replace("StarGiftAttributeRarity", "")
        return name

    @staticmethod
    def _resolve_seller(gift: Any, response: Any) -> Seller:
        peer = getattr(gift, "owner_id", None)
        owner_name = getattr(gift, "owner_name", None)
        wallet = getattr(gift, "owner_address", None)
        if peer is None:
            if wallet:
                return Seller(
                    display_name=owner_name or "TON wallet",
                    confidence="wallet_only",
                    evidence="Telegram API returned owner_address",
                    wallet_address=str(wallet),
                )
            if owner_name:
                return Seller(
                    display_name=str(owner_name),
                    confidence="name_only",
                    evidence="Telegram API returned owner_name without owner_id",
                )
            return Seller()

        peer_id = getattr(peer, "user_id", None)
        peer_kind = "user"
        if peer_id is None:
            peer_id = getattr(peer, "channel_id", None)
            peer_kind = "channel"
        if peer_id is None:
            peer_id = getattr(peer, "chat_id", None)
            peer_kind = "chat"

        entity = None
        if peer_kind == "user":
            entity = next(
                (user for user in getattr(response, "users", []) if getattr(user, "id", None) == peer_id),
                None,
            )
        else:
            entity = next(
                (chat for chat in getattr(response, "chats", []) if getattr(chat, "id", None) == peer_id),
                None,
            )

        username = getattr(entity, "username", None) if entity else None
        first_name = getattr(entity, "first_name", None) if entity else None
        last_name = getattr(entity, "last_name", None) if entity else None
        display_name = " ".join(part for part in (first_name, last_name) if part)
        display_name = display_name or owner_name or (f"ID {peer_id}" if peer_id else "Неизвестно")

        profile_url = None
        if username:
            profile_url = f"https://t.me/{username}"
        elif peer_kind == "user" and peer_id:
            profile_url = f"tg://user?id={peer_id}"

        return Seller(
            display_name=display_name,
            username=username,
            telegram_id=int(peer_id) if peer_id is not None else None,
            profile_url=profile_url,
            confidence="telegram_peer",
            evidence="owner_id field returned by Telegram MTProto",
            wallet_address=str(wallet) if wallet else None,
        )

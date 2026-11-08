import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from telethon import TelegramClient, functions
from telethon.errors import FloodWaitError

from config import settings


def _owner_state(gift: Any, users: list[Any]) -> tuple[str, bool]:
    """Classify only fields explicitly returned by Telegram; never infer identity."""
    owner_peer = getattr(gift, "owner_id", None)
    owner_name = getattr(gift, "owner_name", None)
    owner_address = getattr(gift, "owner_address", None)

    if owner_peer is not None:
        peer_id = getattr(owner_peer, "user_id", None)
        if peer_id is None:
            peer_id = getattr(owner_peer, "channel_id", None)
        if peer_id is None:
            peer_id = getattr(owner_peer, "chat_id", None)

        has_username = False
        if peer_id is not None:
            has_username = any(
                int(getattr(user, "id", -1)) == int(peer_id)
                and bool(getattr(user, "username", None))
                for user in users
            )
        return "peer", has_username

    if owner_address:
        return "wallet", False
    if owner_name:
        return "name_only", False
    return "missing", False


async def main() -> None:
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise RuntimeError("Заполни TELEGRAM_API_ID и TELEGRAM_API_HASH в .env")

    Path(settings.telegram_session_path).parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(
        settings.telegram_session_path,
        settings.telegram_api_id,
        settings.telegram_api_hash,
        flood_sleep_threshold=60,
    )

    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError("Нет авторизации. Сначала запусти: python -m app.auth")

        catalog = await client(functions.payments.GetStarGiftsRequest(hash=0))
        gift_types = [
            gift for gift in getattr(catalog, "gifts", [])
            if int(getattr(gift, "availability_resale", 0) or 0) > 0
        ]
        gift_types.sort(
            key=lambda gift: int(getattr(gift, "availability_resale", 0) or 0),
            reverse=True,
        )

        summary = {
            "gift_types_with_resale": len(gift_types),
            "gift_types_checked": 0,
            "listings_checked": 0,
            "resale_owner_id_present": 0,
            "resale_owner_username_resolved": 0,
            "resale_owner_name_only": 0,
            "resale_owner_address_present": 0,
            "resale_owner_fields_missing": 0,
            "unique_method_available_in_telethon": hasattr(
                functions.payments, "GetUniqueStarGiftRequest"
            ),
            "unique_gifts_checked": 0,
            "unique_owner_id_present": 0,
            "unique_owner_username_resolved": 0,
            "unique_owner_name_only": 0,
            "unique_owner_address_present": 0,
            "unique_owner_fields_missing": 0,
            "unique_users_returned_total": 0,
            "unique_method_errors": 0,
            "unique_comparison_samples": [],
        }

        # Keep the sample small: only five additional, read-only Telegram calls.
        unique_candidates: list[tuple[str, str]] = []
        seen_slugs: set[str] = set()

        for gift_type in gift_types[:5]:
            try:
                response = await client(
                    functions.payments.GetResaleStarGiftsRequest(
                        gift_id=int(gift_type.id),
                        offset="",
                        limit=20,
                    )
                )
            except FloodWaitError as exc:
                logging.warning("Resale request rate-limited for %s seconds", exc.seconds)
                continue

            summary["gift_types_checked"] += 1
            response_users = list(getattr(response, "users", []) or [])

            for gift in getattr(response, "gifts", []):
                summary["listings_checked"] += 1
                state, has_username = _owner_state(gift, response_users)

                if state == "peer":
                    summary["resale_owner_id_present"] += 1
                    if has_username:
                        summary["resale_owner_username_resolved"] += 1
                elif state == "wallet":
                    summary["resale_owner_address_present"] += 1
                elif state == "name_only":
                    summary["resale_owner_name_only"] += 1
                else:
                    summary["resale_owner_fields_missing"] += 1

                slug = str(getattr(gift, "slug", "") or "")
                if slug and slug not in seen_slugs and len(unique_candidates) < 5:
                    seen_slugs.add(slug)
                    unique_candidates.append((slug, state))

            await asyncio.sleep(settings.request_delay_seconds)

        # Compare resale listing data with payments.getUniqueStarGift for the
        # same collectible. The method is a normal read-only MTProto request.
        if summary["unique_method_available_in_telethon"]:
            for slug, resale_state in unique_candidates:
                try:
                    unique_response = await client(
                        functions.payments.GetUniqueStarGiftRequest(slug=slug)
                    )
                    unique_gift = getattr(unique_response, "gift", None)
                    unique_users = list(getattr(unique_response, "users", []) or [])
                    summary["unique_gifts_checked"] += 1
                    summary["unique_users_returned_total"] += len(unique_users)

                    unique_state, has_username = _owner_state(
                        unique_gift, unique_users
                    ) if unique_gift is not None else ("missing", False)

                    if unique_state == "peer":
                        summary["unique_owner_id_present"] += 1
                        if has_username:
                            summary["unique_owner_username_resolved"] += 1
                    elif unique_state == "wallet":
                        summary["unique_owner_address_present"] += 1
                    elif unique_state == "name_only":
                        summary["unique_owner_name_only"] += 1
                    else:
                        summary["unique_owner_fields_missing"] += 1

                    summary["unique_comparison_samples"].append({
                        "gift": slug,
                        "resale_owner_field": resale_state,
                        "unique_gift_owner_field": unique_state,
                        "unique_gift_username_available": has_username,
                        "unique_users_returned": len(unique_users),
                    })
                except FloodWaitError as exc:
                    summary["unique_method_errors"] += 1
                    logging.warning(
                        "Unique-gift request rate-limited for %s seconds",
                        exc.seconds,
                    )
                    break
                except Exception as exc:
                    summary["unique_method_errors"] += 1
                    logging.warning(
                        "Unique-gift request failed (%s)", type(exc).__name__
                    )

                await asyncio.sleep(settings.request_delay_seconds)

        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(
            "\nВажно: сравниваются только поля, которые Telegram сам вернул "
            "для объявления и по slug. Поля пользователей из ответа не "
            "считаются владельцем, если owner_id отсутствует. Идентичность "
            "по имени не угадывается."
        )
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

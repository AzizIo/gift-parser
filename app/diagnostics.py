import asyncio
import json
import logging
from pathlib import Path

from telethon import TelegramClient, functions
from telethon.errors import FloodWaitError

from config import settings


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
            "owner_id_present": 0,
            "owner_username_resolved": 0,
            "owner_name_only": 0,
            "owner_address_present": 0,
            "owner_fields_missing": 0,
            "samples": [],
        }

        # A small sample is enough to check what Telegram currently exposes.
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
                logging.warning("Flood wait from Telegram: %s seconds", exc.seconds)
                await asyncio.sleep(exc.seconds + 1)
                continue

            summary["gift_types_checked"] += 1
            users_by_id = {
                int(user.id): user for user in getattr(response, "users", [])
            }

            for gift in getattr(response, "gifts", []):
                summary["listings_checked"] += 1
                owner_peer = getattr(gift, "owner_id", None)
                owner_name = getattr(gift, "owner_name", None)
                owner_address = getattr(gift, "owner_address", None)

                field_state = "missing"
                has_username = False
                if owner_peer is not None:
                    summary["owner_id_present"] += 1
                    field_state = "peer"
                    peer_id = getattr(owner_peer, "user_id", None)
                    if peer_id is not None:
                        user = users_by_id.get(int(peer_id))
                        has_username = bool(getattr(user, "username", None)) if user else False
                        if has_username:
                            summary["owner_username_resolved"] += 1
                elif owner_address:
                    summary["owner_address_present"] += 1
                    field_state = "wallet"
                elif owner_name:
                    summary["owner_name_only"] += 1
                    field_state = "name_only"
                else:
                    summary["owner_fields_missing"] += 1

                if len(summary["samples"]) < 10:
                    summary["samples"].append({
                        "gift": str(getattr(gift, "slug", "unknown")),
                        "owner_field": field_state,
                        "username_available": has_username,
                    })

            await asyncio.sleep(settings.request_delay_seconds)

        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(
            "\nВажно: диагностика показывает только поля, которые Telegram вернул "
            "этому аккаунту в MTProto-ответе. Она не пытается угадывать владельцев."
        )
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

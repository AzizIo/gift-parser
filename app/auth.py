import asyncio
from pathlib import Path

from telethon import TelegramClient

from config import settings


async def main() -> None:
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise RuntimeError("Сначала заполни TELEGRAM_API_ID и TELEGRAM_API_HASH в .env")

    Path(settings.telegram_session_path).parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(
        settings.telegram_session_path,
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    try:
        await client.start(phone=settings.telegram_phone or None)
        me = await client.get_me()
        print(f"MTProto авторизован: id={me.id}, username=@{me.username or 'нет username'}")
        print(f"Файл сессии: {settings.telegram_session_path}.session")
        print("Не отправляй этот файл никому и не загружай его в GitHub.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

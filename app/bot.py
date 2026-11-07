import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from app.database import Database
from app.formatting import format_listing
from app.sources.telegram_market import TelegramMarketSource
from config import settings


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    db = Database(settings.database_path)
    await db.initialize()

    def is_admin(message: Message) -> bool:
        return bool(message.from_user and message.from_user.id == settings.admin_id)

    @dp.message(Command("start"))
    async def start(message: Message) -> None:
        if not is_admin(message):
            return
        await message.answer(
            "👋 <b>Gift Parser</b>\n"
            "Бот создан. Источник объявлений пока не подключён.\n"
            "/status — состояние парсера"
        )

    @dp.message(Command("status"))
    async def status(message: Message) -> None:
        if not is_admin(message):
            return
        await message.answer(
            "🟡 Бот запущен, но источник Telegram Market ещё не настроен.\n"
            "Не отправляю выдуманные объявления или неподтверждённых владельцев."
        )

    async def collect() -> None:
        source = TelegramMarketSource()
        while True:
            try:
                async for listing in source.listen():
                    if await db.save_listing(listing):
                        await bot.send_message(
                            settings.admin_id,
                            format_listing(listing),
                            disable_web_page_preview=True,
                        )
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("Collector stopped")
                await asyncio.sleep(5)

    collector_task = asyncio.create_task(collect())
    try:
        await dp.start_polling(bot)
    finally:
        collector_task.cancel()
        await asyncio.gather(collector_task, return_exceptions=True)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

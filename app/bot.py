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
    state = {"collector": "starting", "last_error": None}

    def is_admin(message: Message) -> bool:
        return bool(message.from_user and message.from_user.id == settings.admin_id)

    @dp.message(Command("start"))
    async def start(message: Message) -> None:
        if not is_admin(message):
            return
        await message.answer(
            "👋 <b>Gift Parser</b> запущен.\n"
            "Источник: официальный Telegram Gift Market API (MTProto).\n"
            "/status — состояние парсера"
        )

    @dp.message(Command("status"))
    async def status(message: Message) -> None:
        if not is_admin(message):
            return
        error = f"\nПоследняя ошибка: <code>{state['last_error']}</code>" if state["last_error"] else ""
        await message.answer(
            f"Сборщик: <b>{state['collector']}</b>\n"
            f"Интервал опроса: {settings.poll_interval_seconds} сек."
            f"{error}"
        )

    async def collect() -> None:
        first_run = await db.is_empty()
        while True:
            source = TelegramMarketSource(silent_initial_snapshot=first_run)
            try:
                state["collector"] = "connecting"
                state["last_error"] = None
                async for listing in source.listen():
                    inserted = await db.save_listing(listing)
                    if inserted and not listing.initial_snapshot:
                        await bot.send_message(
                            settings.admin_id,
                            format_listing(listing),
                            disable_web_page_preview=True,
                        )
                first_run = False
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                state["collector"] = "reconnecting"
                state["last_error"] = str(exc)[:300]
                logging.exception("Collector stopped")
                await asyncio.sleep(10)
            else:
                first_run = False

    collector_task = asyncio.create_task(collect())
    try:
        await dp.start_polling(bot)
    finally:
        collector_task.cancel()
        await asyncio.gather(collector_task, return_exceptions=True)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

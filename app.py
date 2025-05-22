import asyncio

from logs_setup import logger, new_session_log

from config import TOKEN, MessageTexts, QuestionsData

from aiogram.enums import ParseMode
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats

_bot_settings = {"parse_mode": ParseMode.HTML}
BOT_PROPERTIES = DefaultBotProperties(**_bot_settings)

bot = Bot(TOKEN, default=BOT_PROPERTIES)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

msg_texts = MessageTexts()
questions_data = QuestionsData()


async def on_startup():
    logger.info("Bot online.")
    await bot.delete_my_commands()
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="перезапустить бота"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )
    from utils import startup_admins_notify, load_json_data

    await startup_admins_notify()
    await load_json_data()
    await dp.start_polling(bot)


if __name__ == "__main__":
    new_session_log()

    from handlers import users_router, admins_router

    dp.include_router(admins_router)
    dp.include_router(users_router)

    asyncio.run(on_startup())

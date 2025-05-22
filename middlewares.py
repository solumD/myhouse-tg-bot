import asyncio
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, ChatMemberUpdated

from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from utils import notify_admins_about_error

from app import logger

import traceback


async def answer_event(event: CallbackQuery | Message | ChatMemberUpdated):
    if isinstance(event, CallbackQuery):
        return await event.answer(
            "Произошла ошибка. Попробуйте еще раз.", show_alert=True
        )
    if isinstance(event, Message):
        await event.answer("🫠")
        return await event.reply("Произошла ошибка. Попробуйте еще раз.")


class ErrorMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        pass

    async def __call__(
        self,
        handler: Callable[[CallbackQuery | Message, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery | Message,
        data: Dict[str, Any],
    ) -> Any:
        try:
            result = await handler(event, data)
            return result
        except TelegramRetryAfter as ex:
            logger.warning(
                f"Flood control by API in telegram bot warning try in: {ex.retry_after} seconds"
            )
            await asyncio.sleep(ex.retry_after + 10)
            return await handler(event, data)
        except TelegramAPIError as ex:
            if "message is not modified" in str(ex.message):
                await event.answer()
                return
            logger.error("Telegram API error while handling event", exc_info=True)
            await notify_admins_about_error(
                str(ex.label),
                traceback.format_exc(limit=4).splitlines(),
                event.from_user,
            )
            await answer_event(event)
        except Exception as ex:
            logger.error("Error while handling event", exc_info=True)
            await notify_admins_about_error(
                str(type(ex).__name__),
                traceback.format_exc(limit=4).splitlines(),
                event.from_user,
            )
            await answer_event(event)

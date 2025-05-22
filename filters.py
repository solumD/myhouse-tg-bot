from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config import ADMINS


class IsAdminFilter(BaseFilter):
    def __init__(self, is_admin: bool):
        self.is_admin = is_admin

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return (event.from_user.id in ADMINS) == self.is_admin

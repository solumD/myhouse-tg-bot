import json
from json import JSONDecodeError

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    FSInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.utils.formatting import Text, BlockQuote, Bold

from config import TEXTS_LABELS, JSON_DATA_PATH
from filters import IsAdminFilter
from logs_setup import logger
from middlewares import ErrorMiddleware

from app import msg_texts, questions_data
from utils import (
    number_to_emojis,
    parse_json,
    DataParseException,
    json_format_error_notify,
    json_updated_notify,
    backup_file,
)

# Routers
users_router = Router(name="users")
users_router.message.middleware(ErrorMiddleware())
users_router.callback_query.middleware(ErrorMiddleware())

admins_router = Router(name="admins")
admins_router.message.filter(IsAdminFilter(is_admin=True))
admins_router.callback_query.filter(IsAdminFilter(is_admin=True))
admins_router.message.middleware(ErrorMiddleware())
admins_router.callback_query.middleware(ErrorMiddleware())


def _generate_kb(parent_id: int = 0) -> (str, InlineKeyboardMarkup | None):
    tree = questions_data.QUESTIONS_TREE
    if parent_id != 0:
        tree = questions_data.get_category_items(cat_id=parent_id)
    kb = None
    buttons = []
    current_row = -1
    counter = 0
    text = ""
    items = tree.keys() if isinstance(tree, dict) else tree
    for k in items:
        if isinstance(k, dict):
            key = list(k.keys())[0]
        else:
            key = k
        counter += 1
        if key < 0:
            name = questions_data.QUESTIONS[key]["question"]
            text += f"{counter}. ❔ {name}\n\n"
        else:
            name = questions_data.CATEGORIES[key]["name"]
            text += f"{counter}. 🏷 {name}\n\n"
        current_row += 1
        if current_row > 2:
            current_row = 0
        if current_row == 0:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{number_to_emojis(counter)}",
                        callback_data=f"go_by_id:{key}",
                    )
                ]
            )
        else:
            buttons[-1].append(
                InlineKeyboardButton(
                    text=f"{number_to_emojis(counter)}", callback_data=f"go_by_id:{key}"
                )
            )

    if buttons:
        if parent_id != 0:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад", callback_data=f"back_by_id:{parent_id}"
                    ),
                    InlineKeyboardButton(
                        text="⏺️ Главная", callback_data=f"go_by_id:{0}"
                    ),
                ]
            )
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    return text, kb


def _get_back_kb(parent_id: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"back_by_id:{parent_id}"
                ),
                InlineKeyboardButton(text="⏺️ Главная", callback_data=f"go_by_id:{0}"),
            ]
        ]
    )


# === User ===
@users_router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    text, kb = _generate_kb()
    await message.answer(
        text=msg_texts.TEXTS[TEXTS_LABELS.START.value] + "\n\n" + text, reply_markup=kb
    )


@users_router.callback_query(lambda q: q.data.startswith("go_by_id:"))
async def go_to_callback(query: CallbackQuery, state: FSMContext):
    param_id = int(query.data.split(":")[1])
    if param_id < 0:
        question = questions_data.QUESTIONS[param_id]["question"]
        answer = questions_data.QUESTIONS[param_id]["answer"]
        text = Text(BlockQuote(question), "\n\n", answer)
        await query.message.answer(
            **text.as_kwargs(), reply_markup=_get_back_kb(param_id)
        )
    else:
        prefix = ""
        if param_id != 0:
            prefix = BlockQuote(questions_data.CATEGORIES[param_id]["name"]) + "\n\n"
        text, kb = _generate_kb(parent_id=param_id)
        await query.message.answer(
            **Text(
                prefix, msg_texts.TEXTS[TEXTS_LABELS.SELECT.value], "\n\n", text
            ).as_kwargs(),
            reply_markup=kb,
        )
    await query.answer()


@users_router.callback_query(lambda q: q.data.startswith("back_by_id:"))
async def back_to_callback(query: CallbackQuery, state: FSMContext):
    param_id = int(query.data.split(":")[1])
    parent_id = questions_data.get_item_parent(item_id=param_id)
    text, kb = _generate_kb(parent_id=parent_id)
    prefix = ""
    if parent_id != 0:
        prefix = BlockQuote(questions_data.CATEGORIES[parent_id]["name"]) + "\n\n"
    await query.message.answer(
        **Text(
            prefix, msg_texts.TEXTS[TEXTS_LABELS.SELECT.value], "\n\n", text
        ).as_kwargs(),
        reply_markup=kb,
    )
    await query.answer()


@admins_router.message(Command("update"))
async def update_cmd(message: Message, state: FSMContext):
    if not message.document:
        await message.answer(
            **Text(
                Bold("Команда должна быть отправлена в подписи к файлу для изменений")
            ).as_kwargs()
        )
        await message.answer_document(
            document=FSInputFile(path="data.json", filename="data.json"),
            caption="текущий файл",
        )
        return

    if message.document.file_name.split(".")[-1].strip() != "json":
        await message.answer("❌")
        return await message.answer(
            **Text(Bold("Файл должен быть в формате .json")).as_kwargs()
        )

    try:
        file = await message.bot.download(file=message.document.file_id)
        data = file.read()
        json_data = json.loads(data)
        parse_json(json_data)
        back_path = backup_file(JSON_DATA_PATH, "data_backups/")
        with open(JSON_DATA_PATH, "wb") as new_file:
            new_file.write(data)
    except JSONDecodeError:
        await message.answer("❌")
        return await message.answer(
            **Text(
                Bold("Ошибка при чтении json файла (неверный синтаксис)")
            ).as_kwargs()
        )
    except DataParseException as ex:
        logger.warning("cant parse new json file error")
        return await json_format_error_notify(err_txt=ex.detail)

    await json_updated_notify(message.from_user, backup_path=back_path)


@users_router.message()
async def all_msg(message: Message, state: FSMContext):
    logger.info(f"Unhandled msg update {message}")
    await message.answer(text=msg_texts.TEXTS[TEXTS_LABELS.UNKNOWN.value])
    await start_cmd(message, state)


@users_router.callback_query()
async def all_callback(query: CallbackQuery, state: FSMContext):
    logger.info(f"Unhandled callback update {query.message}")
    await query.message.answer(text=msg_texts.TEXTS[TEXTS_LABELS.UNKNOWN.value])
    await start_cmd(query.message, state)


import json
import os
import shutil
from datetime import datetime
from enum import Enum

from app import bot, msg_texts, questions_data

from logs_setup import logger

from config import (
    ADMINS,
    JSON_DATA_PATH,
    TEXTS_LABELS,
)

from aiogram.utils.formatting import Text, Pre, Bold, Italic, Code, BlockQuote
from aiogram.types import InlineKeyboardMarkup, User, InputFile, FSInputFile


async def _notify_admins(
    contents: list[Text],
    reply_markup: InlineKeyboardMarkup | None = None,
    keyboard_message_index: int = 0,
    with_file: InputFile | None = None,
    file_message_index: int = 0,
):
    for admin in ADMINS:
        try:
            for index, content in enumerate(contents):
                if index == keyboard_message_index:
                    rm = reply_markup
                else:
                    rm = None
                if with_file and index == file_message_index:
                    await bot.send_document(
                        chat_id=admin,
                        **content.as_kwargs(
                            text_key="caption", entities_key="caption_entities"
                        ),
                        reply_markup=rm,
                        document=with_file,
                    )
                else:
                    await bot.send_message(
                        chat_id=admin, **content.as_kwargs(), reply_markup=rm
                    )
        except Exception as e:
            logger.warning(
                f"error while sending message to admin : {admin}", exc_info=e
            )


async def startup_admins_notify():
    emoji_content = Text("🚀")
    content = Text("Бот запущен.")
    await _notify_admins([emoji_content, content])


async def notify_admins_about_error(
    error_label: str, error_message: str | list, user: User
):
    if isinstance(error_message, list):
        error_message = "\n".join(error_message)
    content = Text(
        "⚠️ Произошла неизвестная ошибка при работе бота\n\n",
        Italic("user_id: "),
        Code(user.id),
        "\n",
        Italic("full name: "),
        Code(user.full_name),
        "\n",
        Italic("username: "),
        "@" + str(user.username),
        "\n\n",
        Bold(error_label),
        "\n\n",
        Pre(error_message),
    )
    await _notify_admins([content])


async def json_format_error_notify(err_txt: str = "Ошибка парсинга"):
    emoji_content = Text("⚠️")
    content = Text(
        Bold("При чтении файла с данными произошла ошибка форматирования."),
        "\n\n",
        BlockQuote("Проверьте правильность структуры файла и загрузите его еще раз."),
        "\n\nВозвращен к предыдущий вариант данных.",
        "\n\nТекст ошибки:\n",
        Code(err_txt),
    )
    await _notify_admins([emoji_content, content])


async def json_updated_notify(user: User, backup_path: str = ""):
    content = Text(
        "🔄 Обновлен json файл пользователем:\n\n",
        Italic("user_id: "),
        Code(user.id),
        "\n",
        Italic("full name: "),
        Code(user.full_name),
        "\n",
        Italic("username: "),
        "@" + str(user.username),
        "\n\n",
        BlockQuote(
            f"ℹ️ Была создана резервная копия старого файла по пути: {backup_path}"
        ),
    )
    await _notify_admins([content])


async def json_not_loaded_notify():
    emoji_content = Text("🗂")
    content = Text(
        Bold("Файл с данными не обнаружен."),
        "\n\n",
        BlockQuote(
            "Для работы бота необходимо загрузить файл данных через /upload"
            "\n\nили указать правильный путь на уже существующий в config.py."
        ),
    )
    await _notify_admins(
        [emoji_content, content],
        with_file=FSInputFile(path="example_data.json", filename="пример.json"),
        file_message_index=1,
    )


class DataParseException(Exception):
    """Raised when provided json data is not in correct format"""

    def __init__(self, detail_message: str = ""):
        self.detail = detail_message
        super().__init__(self.detail)


class TOP_LEVEL_LABELS(Enum):
    TEXTS = "texts"
    QUESTIONS = "questions"


def parse_json(raw_json: dict):
    # check top level params
    top_params = [label.value for label in TOP_LEVEL_LABELS]
    for key in top_params:
        if key not in raw_json:
            raise DataParseException(f'"{key}" must be in top level json')

    # check texts level params
    texts_params = [label.value for label in TEXTS_LABELS]
    new_texts = {}
    for key in texts_params:
        if key not in raw_json[TOP_LEVEL_LABELS.TEXTS.value]:
            raise DataParseException(
                f'"{key}" must be in "{TOP_LEVEL_LABELS.TEXTS.value}" section'
            )
        new_texts[key] = raw_json[TOP_LEVEL_LABELS.TEXTS.value][key]

    # check question formats
    def parse_structure(
        data,
        parent_id=None,
        categories=None,
        questions=None,
        cat_counter=None,
        q_counter=None,
    ):
        if categories is None:
            categories = {}
        if questions is None:
            questions = {}
        if cat_counter is None:
            cat_counter = [1]
        if q_counter is None:
            q_counter = [-1]

        tree = {}

        for name, content in data.items():
            if isinstance(content, dict):
                cat_id = cat_counter[0]
                cat_counter[0] += 1
                categories[cat_id] = {"name": name, "is_category": True}
                tree[cat_id] = []
                subtree, _, _ = parse_structure(
                    content, cat_id, categories, questions, cat_counter, q_counter
                )
                if cat_id in subtree:
                    tree[cat_id].extend(subtree[cat_id])
                if parent_id is not None:
                    if parent_id not in tree:
                        tree[parent_id] = []
                    tree[parent_id].append({cat_id: tree[cat_id]})
            elif isinstance(content, str):
                q_id = q_counter[0]
                q_counter[0] -= 1
                questions[q_id] = {
                    "question": name,
                    "answer": content,
                    "category_id": parent_id,
                }
                if parent_id is not None:
                    if parent_id not in tree:
                        tree[parent_id] = []
                    tree[parent_id].append(q_id)
                else:
                    cat_id = cat_counter[0]
                    cat_counter[0] += 1
                    categories[cat_id] = {"name": name, "is_category": False}
                    tree[cat_id] = [q_id]
            else:
                raise DataParseException(
                    f'all values in "{TOP_LEVEL_LABELS.QUESTIONS.value}" '
                    f'section must be dict or str (error on value for: "{name}")'
                )

        return tree, categories, questions

    res_tree, new_cats, new_questions = parse_structure(
        raw_json[TOP_LEVEL_LABELS.QUESTIONS.value]
    )
    logger.info("data parsed without errors")
    # set config params to parsed data
    msg_texts.set_new_texts(new_texts)
    logger.info("message texts updated without errors")
    questions_data.set_new_questions(new_questions)
    logger.info("questions dict updated without errors")
    questions_data.set_new_tree(res_tree)
    logger.info("tree dict updated without errors")
    questions_data.set_new_cats(new_cats)
    logger.info("categories dict updated without errors")

    # FOR DEBUG
    # print(json.dumps(res_tree, ensure_ascii=False))


async def load_json_data():
    try:
        with open(JSON_DATA_PATH, "r") as file:
            data = json.load(file)
            parse_json(data)
    except FileNotFoundError:
        logger.warning("json file is not found error")
        await json_not_loaded_notify()
    except DataParseException as ex:
        logger.warning("cant parse new json file error")
        await json_format_error_notify(err_txt=ex.detail)


def number_to_emojis(number):
    emoji_digits = {
        "0": "0️⃣",
        "1": "1️⃣",
        "2": "2️⃣",
        "3": "3️⃣",
        "4": "4️⃣",
        "5": "5️⃣",
        "6": "6️⃣",
        "7": "7️⃣",
        "8": "8️⃣",
        "9": "9️⃣",
    }
    number_str = str(number)
    result = []
    for digit in number_str:
        if digit in emoji_digits:
            result.append(emoji_digits[digit])
        else:
            result.append(digit)
    return "".join(result)


def backup_file(file_path, backup_dir) -> str:
    os.makedirs(backup_dir, exist_ok=True)

    base_name = os.path.basename(file_path)

    # Create a timestamped backup file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_name = f"{base_name}.{timestamp}.bak"
    backup_path = os.path.join(backup_dir, backup_file_name)

    # Copy the file
    shutil.copy2(file_path, backup_path)
    logger.info(f"Backup created: {backup_path}")

    # Clean up old backups (keep only the last 5)
    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith(base_name)], reverse=True
    )

    for old_backup in backups[5:]:
        old_backup_path = os.path.join(backup_dir, old_backup)
        os.remove(old_backup_path)
        logger.info(f"Old backup removed: {old_backup_path}")

    return backup_path

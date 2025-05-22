from enum import Enum

from dotenv import load_dotenv
import os

from singleton import singleton

load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMINS = [int(x) for x in os.getenv("ADMINS").split(",")]

JSON_DATA_PATH = "data.json"


# Данные снизу парятся из файла (внизу дефолтные значения)
class TEXTS_LABELS(Enum):
    START = "start"
    SELECT = "select"
    UNKNOWN = "unknown"


@singleton
class MessageTexts:
    def __init__(self):
        self.TEXTS = {
            TEXTS_LABELS.START.value: "start text",
            TEXTS_LABELS.SELECT.value: "select text",
            TEXTS_LABELS.UNKNOWN.value: "unknown text",
        }

    def set_new_texts(self, new_texts: dict):
        self.TEXTS = new_texts


@singleton
class QuestionsData:
    def __init__(self):
        self.QUESTIONS_TREE = {}
        self.CATEGORIES = {}
        self.QUESTIONS = {}

    def set_new_tree(self, new_tree: dict):
        self.QUESTIONS_TREE = new_tree

    def set_new_cats(self, new_cats: dict):
        self.CATEGORIES = new_cats

    def set_new_questions(self, new_questions: dict):
        self.QUESTIONS = new_questions

    def get_item_parent(self, item_id: int) -> int:
        def find_parent(tree, target_id):
            if isinstance(tree, dict):
                for cat_id, items in tree.items():
                    for item in items:
                        if item == target_id:
                            return cat_id
                        if isinstance(item, dict):
                            if target_id in item:
                                return cat_id
                            for subcat_id, subitems in item.items():
                                parent = find_parent({subcat_id: subitems}, target_id)
                                if parent:
                                    return parent
            return 0

        return find_parent(self.QUESTIONS_TREE, item_id)

    def get_category_items(self, cat_id: int):
        def find_category_and_get_top_level_members(
            tree, category_id, current_level=None
        ):
            if current_level is None:
                current_level = tree
            for key, value in current_level.items():
                if key == category_id:
                    return value
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            result = find_category_and_get_top_level_members(
                                tree, category_id, item
                            )
                            if result is not None:
                                return result
                elif isinstance(value, dict):
                    result = find_category_and_get_top_level_members(
                        tree, category_id, value
                    )
                    if result is not None:
                        return result

            return None

        return find_category_and_get_top_level_members(
            self.QUESTIONS_TREE, category_id=cat_id
        )

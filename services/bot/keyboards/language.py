from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def language_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="O'zbek"),
                KeyboardButton(text="Русский"),
                KeyboardButton(text="English"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

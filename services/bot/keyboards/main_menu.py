from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def quiz_active_keyboard() -> ReplyKeyboardMarkup:
    """Quiz davomida ko'rsatiladigan keyboard — faqat Exit."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏹ Exit")]],
        resize_keyboard=True,
    )


def main_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    buttons = {
        "uz": [
            ["▶️ Boshlash", "🔍 Qidirish"],
            ["📤 Quiz Yaratish", "🏆 Reyting"],
            ["👤 Profil", "👥 Taklif qilish"],
        ],
        "ru": [
            ["▶️ Начать", "🔍 Поиск"],
            ["📤 Создать квиз", "🏆 Рейтинг"],
            ["👤 Профиль", "👥 Пригласить"],
        ],
        "en": [
            ["▶️ Start", "🔍 Search"],
            ["📤 Create Quiz", "🏆 Leaderboard"],
            ["👤 Profile", "👥 Invite"],
        ],
    }

    rows = buttons.get(lang, buttons["uz"])
    keyboard = [[KeyboardButton(text=btn) for btn in row] for row in rows]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )

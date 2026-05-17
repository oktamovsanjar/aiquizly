from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


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

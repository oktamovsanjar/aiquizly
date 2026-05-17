"""
Oddiy i18n — barcha bot xabarlari uchun tarjima.
Foydalanish: t("key", lang)
"""
from typing import Optional

_TEXTS: dict[str, dict[str, str]] = {
    # ── Start ──────────────────────────────────────────────────────────────────
    "welcome_new": {
        "uz": (
            "Quiz Bot ga xush kelibsiz!\n\n"
            "Bu bot orqali:\n"
            "• Tayyor quizlarni yechishingiz\n"
            "• O'z testlaringizni yaratishingiz\n"
            "• Do'stlar bilan bellashishingiz mumkin\n\n"
            "Tilni tanlang:"
        ),
        "ru": (
            "Добро пожаловать в Quiz Bot!\n\n"
            "С этим ботом вы можете:\n"
            "• Проходить готовые квизы\n"
            "• Создавать свои тесты\n"
            "• Соревноваться с друзьями\n\n"
            "Выберите язык:"
        ),
        "en": (
            "Welcome to Quiz Bot!\n\n"
            "With this bot you can:\n"
            "• Solve ready-made quizzes\n"
            "• Create your own tests\n"
            "• Compete with friends\n\n"
            "Select language:"
        ),
    },
    "welcome_back": {
        "uz": "Xush kelibsiz, {name}! 👋\n\nAsosiy menyu:",
        "ru": "Добро пожаловать, {name}! 👋\n\nГлавное меню:",
        "en": "Welcome back, {name}! 👋\n\nMain menu:",
    },
    "referral_bonus": {
        "uz": "\n\n🎁 <b>{name}</b> taklifi orqali keldingiz!\nSiz: <b>+{xp} XP</b> bonus oldingiz!",
        "ru": "\n\n🎁 Вы пришли по приглашению <b>{name}</b>!\nВы получили: <b>+{xp} XP</b> бонус!",
        "en": "\n\n🎁 You joined via <b>{name}</b>'s invite!\nYou got: <b>+{xp} XP</b> bonus!",
    },
    # ── Til tanlash ────────────────────────────────────────────────────────────
    "language_saved": {
        "uz": "Asosiy menyu:",
        "ru": "Главное меню:",
        "en": "Main menu:",
    },
    # ── Quiz ──────────────────────────────────────────────────────────────────
    "quiz_select_mode": {
        "uz": "Qayerdan o'ynaysiz?",
        "ru": "Откуда будете играть?",
        "en": "Where do you want to play from?",
    },
    "quiz_search_prompt": {
        "uz": "🔍 Qidiring yoki teg tanlang:\n\nYoki matn yozing...",
        "ru": "🔍 Ищите или выберите тег:\n\nИли введите текст...",
        "en": "🔍 Search or select a tag:\n\nOr type text...",
    },
    "quiz_not_found": {
        "uz": "😔 Natija topilmadi. Boshqa so'z yozing.",
        "ru": "😔 Ничего не найдено. Попробуйте другой запрос.",
        "en": "😔 Nothing found. Try a different query.",
    },
    "quiz_select_set": {
        "uz": "To'plamni tanlang:",
        "ru": "Выберите набор:",
        "en": "Select a set:",
    },
    "quiz_select_time": {
        "uz": "⏱ Har savol uchun vaqt tanlang:",
        "ru": "⏱ Выберите время на каждый вопрос:",
        "en": "⏱ Select time per question:",
    },
    "quiz_starting": {
        "uz": "🎮 Quiz boshlanmoqda...",
        "ru": "🎮 Квиз начинается...",
        "en": "🎮 Quiz is starting...",
    },
    "quiz_paused": {
        "uz": "⏸ Quiz to'xtatildi. Davom etish uchun bosing.",
        "ru": "⏸ Квиз на паузе. Нажмите для продолжения.",
        "en": "⏸ Quiz paused. Press to continue.",
    },
    "quiz_stopped": {
        "uz": "🛑 Quiz to'xtatildi.",
        "ru": "🛑 Квиз остановлен.",
        "en": "🛑 Quiz stopped.",
    },
    "quiz_completed": {
        "uz": "✅ Quiz yakunlandi!",
        "ru": "✅ Квиз завершён!",
        "en": "✅ Quiz completed!",
    },
    "quiz_correct": {
        "uz": "✅ To'g'ri!",
        "ru": "✅ Правильно!",
        "en": "✅ Correct!",
    },
    "quiz_wrong": {
        "uz": "❌ Noto'g'ri!",
        "ru": "❌ Неверно!",
        "en": "❌ Wrong!",
    },
    "quiz_timeout": {
        "uz": "⏰ Vaqt tugadi!",
        "ru": "⏰ Время вышло!",
        "en": "⏰ Time's up!",
    },
    "quiz_score": {
        "uz": "Natija: {correct}/{total} ({pct}%)",
        "ru": "Результат: {correct}/{total} ({pct}%)",
        "en": "Score: {correct}/{total} ({pct}%)",
    },
    # ── Upload ────────────────────────────────────────────────────────────────
    "upload_select_method": {
        "uz": "Quiz yaratish usulini tanlang:",
        "ru": "Выберите способ создания квиза:",
        "en": "Select how to create your quiz:",
    },
    "upload_send_file": {
        "uz": "📎 Faylni yuboring (.docx, .pdf, .xlsx, .txt, max 10 MB):",
        "ru": "📎 Отправьте файл (.docx, .pdf, .xlsx, .txt, макс 10 МБ):",
        "en": "📎 Send your file (.docx, .pdf, .xlsx, .txt, max 10 MB):",
    },
    "upload_send_image": {
        "uz": "📸 Rasmni yuboring (savollar bilan, max 5 MB):",
        "ru": "📸 Отправьте изображение (с вопросами, макс 5 МБ):",
        "en": "📸 Send an image (with questions, max 5 MB):",
    },
    "upload_processing": {
        "uz": "⏳ Fayl qayta ishlanmoqda... Bu bir necha daqiqa olishi mumkin.",
        "ru": "⏳ Файл обрабатывается... Это может занять несколько минут.",
        "en": "⏳ Processing your file... This may take a few minutes.",
    },
    "upload_error": {
        "uz": "❌ Fayl qayta ishlanmadi. Keyinroq urinib ko'ring.",
        "ru": "❌ Не удалось обработать файл. Попробуйте позже.",
        "en": "❌ File processing failed. Please try again later.",
    },
    "upload_limit_reached": {
        "uz": "⚠️ Oylik limitga yetdingiz. Premium obuna oling yoki keyingi oy kuting.",
        "ru": "⚠️ Вы достигли месячного лимита. Оформите Premium или подождите следующего месяца.",
        "en": "⚠️ Monthly limit reached. Get Premium or wait until next month.",
    },
    "upload_file_too_large": {
        "uz": "❌ Fayl juda katta (max 10 MB).",
        "ru": "❌ Файл слишком большой (макс 10 МБ).",
        "en": "❌ File is too large (max 10 MB).",
    },
    # ── Manual quiz ───────────────────────────────────────────────────────────
    "manual_title_prompt": {
        "uz": "📝 Quiz nomini kiriting:",
        "ru": "📝 Введите название квиза:",
        "en": "📝 Enter quiz title:",
    },
    "manual_question_prompt": {
        "uz": "❓ {num}-savol matnini kiriting:",
        "ru": "❓ Введите текст {num}-го вопроса:",
        "en": "❓ Enter question {num} text:",
    },
    "manual_options_prompt": {
        "uz": "📋 Variant {num} ({letter}):",
        "ru": "📋 Вариант {num} ({letter}):",
        "en": "📋 Option {num} ({letter}):",
    },
    "manual_correct_prompt": {
        "uz": "✅ To'g'ri variantni tanlang:",
        "ru": "✅ Выберите правильный вариант:",
        "en": "✅ Select the correct option:",
    },
    "manual_saved": {
        "uz": "✅ Quiz saqlandi! <b>{title}</b> ({count} ta savol)",
        "ru": "✅ Квиз сохранён! <b>{title}</b> ({count} вопросов)",
        "en": "✅ Quiz saved! <b>{title}</b> ({count} questions)",
    },
    # ── Profile ───────────────────────────────────────────────────────────────
    "profile_title": {
        "uz": "👤 <b>Profil</b>",
        "ru": "👤 <b>Профиль</b>",
        "en": "👤 <b>Profile</b>",
    },
    "profile_level": {
        "uz": "Daraja",
        "ru": "Уровень",
        "en": "Level",
    },
    "profile_xp": {
        "uz": "XP",
        "ru": "XP",
        "en": "XP",
    },
    "profile_quizzes_completed": {
        "uz": "Yechilgan quizlar",
        "ru": "Пройдено квизов",
        "en": "Quizzes completed",
    },
    "profile_streak": {
        "uz": "Kun ketma-ketligi",
        "ru": "Серия дней",
        "en": "Day streak",
    },
    # ── Leaderboard ───────────────────────────────────────────────────────────
    "leaderboard_title": {
        "uz": "🏆 <b>Reyting</b>",
        "ru": "🏆 <b>Рейтинг</b>",
        "en": "🏆 <b>Leaderboard</b>",
    },
    "leaderboard_empty": {
        "uz": "Hozircha hech kim yo'q.",
        "ru": "Пока никого нет.",
        "en": "No entries yet.",
    },
    # ── Referral ──────────────────────────────────────────────────────────────
    "referral_title": {
        "uz": "👥 <b>Do'st taklif qilish</b>",
        "ru": "👥 <b>Пригласить друга</b>",
        "en": "👥 <b>Invite Friends</b>",
    },
    "referral_description": {
        "uz": (
            "Do'stingizni taklif qiling va bonus oling!\n\n"
            "Har bir taklif uchun:\n"
            "├── Siz: <b>+50 XP + 3 kun premium</b>\n"
            "└── Do'st: <b>+20 XP</b> bonus\n\n"
            "Sizning havolangiz:"
        ),
        "ru": (
            "Пригласите друга и получите бонус!\n\n"
            "За каждое приглашение:\n"
            "├── Вы: <b>+50 XP + 3 дня Premium</b>\n"
            "└── Друг: <b>+20 XP</b> бонус\n\n"
            "Ваша ссылка:"
        ),
        "en": (
            "Invite a friend and get bonuses!\n\n"
            "For each referral:\n"
            "├── You: <b>+50 XP + 3 days Premium</b>\n"
            "└── Friend: <b>+20 XP</b> bonus\n\n"
            "Your link:"
        ),
    },
    # ── Premium ───────────────────────────────────────────────────────────────
    "premium_title": {
        "uz": "💎 <b>Premium rejalar</b>",
        "ru": "💎 <b>Планы Premium</b>",
        "en": "💎 <b>Premium Plans</b>",
    },
    "premium_description": {
        "uz": (
            "📅 <b>Oylik</b> — 29 000 so'm / 150 ⭐\n"
            "📆 <b>Yillik</b> — 249 000 so'm / 1200 ⭐ (29% tejash)\n\n"
            "Premium bilan:\n"
            "• Cheksiz fayl yuklash\n"
            "• Guruhga ulashish\n"
            "• Quiz doim saqlanadi\n"
            "• Batafsil statistika\n\n"
            "Yoki 3 ta do'st taklif qiling = 9 kun bepul!"
        ),
        "ru": (
            "📅 <b>Ежемесячный</b> — 29 000 сум / 150 ⭐\n"
            "📆 <b>Годовой</b> — 249 000 сум / 1200 ⭐ (экономия 29%)\n\n"
            "С Premium:\n"
            "• Безлимитная загрузка файлов\n"
            "• Публикация в группах\n"
            "• Квизы сохраняются навсегда\n"
            "• Подробная статистика\n\n"
            "Или пригласите 3 друзей = 9 дней бесплатно!"
        ),
        "en": (
            "📅 <b>Monthly</b> — 29 000 UZS / 150 ⭐\n"
            "📆 <b>Yearly</b> — 249 000 UZS / 1200 ⭐ (save 29%)\n\n"
            "With Premium:\n"
            "• Unlimited file uploads\n"
            "• Share to groups\n"
            "• Quizzes saved forever\n"
            "• Detailed statistics\n\n"
            "Or invite 3 friends = 9 days free!"
        ),
    },
    # ── Payment ───────────────────────────────────────────────────────────────
    "payment_select": {
        "uz": "💳 <b>{period}</b> — {price}\n\nTo'lov usulini tanlang:",
        "ru": "💳 <b>{period}</b> — {price}\n\nВыберите способ оплаты:",
        "en": "💳 <b>{period}</b> — {price}\n\nSelect payment method:",
    },
    "payment_success": {
        "uz": "✅ <b>To'lov qabul qilindi!</b>\n\n💎 Premium ({period}) faollashtirildi.\nYaxshi o'qishlar! 🎓",
        "ru": "✅ <b>Оплата принята!</b>\n\n💎 Premium ({period}) активирован.\nУдачи! 🎓",
        "en": "✅ <b>Payment accepted!</b>\n\n💎 Premium ({period}) activated.\nHappy learning! 🎓",
    },
    # ── Errors / system ───────────────────────────────────────────────────────
    "action_cancelled": {
        "uz": "✅ Amal bekor qilindi.",
        "ru": "✅ Действие отменено.",
        "en": "✅ Action cancelled.",
    },
    "nothing_to_cancel": {
        "uz": "Bekor qilish uchun hech narsa yo'q.",
        "ru": "Нечего отменять.",
        "en": "Nothing to cancel.",
    },
    "error_generic": {
        "uz": "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.",
        "ru": "❌ Произошла ошибка. Попробуйте позже.",
        "en": "❌ An error occurred. Please try again later.",
    },
    "upload_wrong_format": {
        "uz": "❌ Faqat quyidagi formatlar qabul qilinadi:\n.docx, .pdf, .xlsx, .txt",
        "ru": "❌ Принимаются только следующие форматы:\n.docx, .pdf, .xlsx, .txt",
        "en": "❌ Only the following formats are accepted:\n.docx, .pdf, .xlsx, .txt",
    },
}


def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """Tarjimani qaytaradi. kwargs bilan format() qo'llaniladi."""
    lang = lang or "uz"
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    entry = _TEXTS.get(key, {})
    text = entry.get(lang) or entry.get("uz") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text

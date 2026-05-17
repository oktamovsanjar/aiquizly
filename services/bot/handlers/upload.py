"""
Upload handlers: fayl va rasm yuborish orqali quiz yaratish.

BOT_UX.md §6:
  §6.1 — Fayl yuklash (.docx/.pdf/.xlsx/.txt)
  §6.3 — Rasm yuborish
"""
import asyncio
import logging
import os

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Document,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PhotoSize,
)

from fsm.states import QuizStates
from keyboards.main_menu import main_menu_keyboard
from utils.api import ai_engine_client
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router()

ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
POLL_INTERVAL = 4       # sekund
POLL_TIMEOUT  = 300     # 5 daqiqa


def _create_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Fayl yuklash", callback_data="up:file")],
        [InlineKeyboardButton(text="📷 Rasm yuborish", callback_data="up:image")],
    ])


def _done_keyboard(quiz_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ O'ynash", callback_data=f"qb:play:{quiz_id}")],
        [InlineKeyboardButton(text="📤 Yana yuklash", callback_data="up:retry")],
    ])


async def _get_lang(state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("language_code", "uz")


# ─────────────────────── Polling background task ───────────────────────

async def _poll_until_done(
    bot: Bot,
    chat_id: int,
    user_id: int,
    task_id: str,
    file_name: str,
    lang: str,
) -> None:
    """
    Celery task tugaguncha /tasks/{task_id} ni har POLL_INTERVAL sekundda so'raydi.
    Tugagach foydalanuvchiga natija xabarini yuboradi.
    """
    deadline = asyncio.get_event_loop().time() + POLL_TIMEOUT
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            data = await ai_engine_client().get_task_status(task_id)
            status = data.get("status")

            if status == "completed":
                result = data.get("result", {})
                quiz_id  = result.get("quiz_id")
                total_q  = result.get("total_questions", 0)

                if not quiz_id or total_q == 0:
                    await bot.send_message(
                        chat_id,
                        "⚠️ Faylda savol topilmadi. Boshqa fayl yuboring.",
                        reply_markup=_create_keyboard(),
                    )
                    return

                labels = {
                    "uz": f"✅ Quiz tayyor!\n📄 <b>{file_name}</b>\n📊 {total_q} ta savol topildi.",
                    "ru": f"✅ Квиз готов!\n📄 <b>{file_name}</b>\n📊 Найдено вопросов: {total_q}.",
                    "en": f"✅ Quiz ready!\n📄 <b>{file_name}</b>\n📊 {total_q} questions found.",
                }
                await bot.send_message(
                    chat_id,
                    labels.get(lang, labels["uz"]),
                    reply_markup=_done_keyboard(quiz_id),
                )
                return

            if status == "failed":
                await bot.send_message(chat_id, t("upload_error", lang))
                return

        except Exception as exc:
            logger.warning("poll task %s xatosi: %s", task_id, exc)

    # Timeout
    await bot.send_message(chat_id, t("upload_error", lang))


# ─────────────────────── Quiz yaratish menyu ───────────────────────

@router.message(F.text.in_({"📤 Quiz Yaratish", "📤 Создать квиз", "📤 Create Quiz"}))
@router.message(Command("create"))
async def quiz_create_menu(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(state)
    await state.set_state(QuizStates.FILE_UPLOAD)
    await message.answer(t("upload_select_method", lang), reply_markup=_create_keyboard())


@router.callback_query(F.data == "up:file")
async def cb_file_upload(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _get_lang(state)
    await state.set_state(QuizStates.FILE_UPLOAD)
    await callback.message.edit_text(t("upload_send_file", lang))
    await callback.answer()


@router.callback_query(F.data == "up:image")
async def cb_image_upload(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _get_lang(state)
    await state.set_state(QuizStates.IMAGE_UPLOAD)
    await state.update_data(image_file_ids=[])
    await callback.message.edit_text(
        t("upload_send_image", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tamom", callback_data="up:images_done")]
        ]),
    )
    await callback.answer()


# ─────────────────────── Fayl handler ───────────────────────

@router.message(F.document)
async def handle_document(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(state)
    doc: Document = message.document

    if doc.file_size > MAX_FILE_SIZE:
        await message.answer(t("upload_file_too_large", lang))
        return

    if doc.mime_type not in ALLOWED_MIME_TYPES:
        await message.answer(t("upload_wrong_format", lang))
        return

    progress_msg = await message.answer(
        f"⏳ Fayl qabul qilindi...\n📄 {doc.file_name}\n[████░░░░░░ 40%]"
    )
    await state.set_state(QuizStates.PROCESSING)

    try:
        file = await message.bot.get_file(doc.file_id)
        file_url = (
            f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
        )

        result = await ai_engine_client().process_file(
            file_url=file_url,
            file_name=doc.file_name,
            file_size=doc.file_size,
            user_id=message.from_user.id,
        )

        if result.get("status") == "already_processed":
            quiz_id = result.get("quiz_id")
            await progress_msg.edit_text(
                "ℹ️ Bu fayl avval yuklangan.",
                reply_markup=_done_keyboard(quiz_id) if quiz_id else _create_keyboard(),
            )
            await state.clear()
            return

        task_id = result.get("task_id")
        if not task_id:
            raise ValueError("task_id qaytarilmadi")

        await state.update_data(task_id=task_id, file_name=doc.file_name)
        await progress_msg.edit_text(
            f"⏳ AI tahlil qilmoqda...\n📄 {doc.file_name}\n[██████████ 100%]\n\n"
            "Tayyor bo'lgach xabar keladi ✉️"
        )
        await state.clear()

        # Background polling — state endi kerak emas
        asyncio.create_task(_poll_until_done(
            bot=message.bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            task_id=task_id,
            file_name=doc.file_name,
            lang=lang,
        ))

    except Exception as e:
        logger.error("Fayl yuklash xatosi: %s", e)
        await progress_msg.edit_text(t("upload_error", lang))
        await state.clear()


# ─────────────────────── Rasm handler ───────────────────────

@router.message(QuizStates.IMAGE_UPLOAD, F.photo)
async def handle_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    file_ids: list = data.get("image_file_ids", [])
    photo: PhotoSize = message.photo[-1]
    file_ids.append(photo.file_id)
    await state.update_data(image_file_ids=file_ids)

    await message.answer(
        f"📷 {len(file_ids)} ta rasm qabul qilindi.\n"
        "Yana yuboring yoki '✅ Tamom' bosing.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tamom", callback_data="up:images_done")]
        ]),
    )


@router.callback_query(F.data == "up:images_done")
async def cb_images_done(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _get_lang(state)
    data = await state.get_data()
    file_ids: list = data.get("image_file_ids", [])

    if not file_ids:
        await callback.answer("Hech qanday rasm yuborilmadi!", show_alert=True)
        return

    progress_msg = await callback.message.edit_text(
        f"⏳ {len(file_ids)} ta rasm tahlil qilinmoqda..."
    )
    await state.set_state(QuizStates.PROCESSING)
    await callback.answer()

    try:
        result = await ai_engine_client().process_images(
            file_ids=file_ids,
            user_id=callback.from_user.id,
            bot_token=callback.bot.token,
        )

        task_id = result.get("task_id")
        if not task_id:
            raise ValueError("task_id qaytarilmadi")

        await progress_msg.edit_text(
            f"⏳ AI Vision tahlil qilmoqda ({len(file_ids)} ta rasm)...\n"
            "Tayyor bo'lgach xabar keladi ✉️"
        )
        await state.clear()

        asyncio.create_task(_poll_until_done(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            task_id=task_id,
            file_name="rasmlar",
            lang=lang,
        ))

    except Exception as e:
        logger.error("Rasm yuklash xatosi: %s", e)
        await progress_msg.edit_text(t("upload_error", lang))
        await state.clear()


# ─────────────────────── Retry ───────────────────────

@router.callback_query(F.data == "up:retry")
async def cb_retry(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _get_lang(state)
    await state.set_state(QuizStates.FILE_UPLOAD)
    await callback.message.edit_text(
        t("upload_select_method", lang),
        reply_markup=_create_keyboard(),
    )
    await callback.answer()

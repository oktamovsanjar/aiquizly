"""
Upload handlers: fayl va rasm yuborish orqali quiz yaratish.

BOT_UX.md §6 talablariga muvofiq:
  §6.1 — Fayl yuklash (.docx/.pdf/.xlsx/.txt)
  §6.3 — Rasm yuborish (multi-image, Vision pipeline)
"""
import logging
import os
from typing import Any

from aiogram import F, Router
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
from utils.api import ai_engine_client
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router()

AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://ai-engine:8002")
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _create_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Fayl yuklash", callback_data="up:file")],
        [InlineKeyboardButton(text="📷 Rasm yuborish", callback_data="up:image")],
    ])


def _save_keyboard(quiz_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Saqlash", callback_data="up:save"),
            InlineKeyboardButton(text="👁 Ko'rib chiqish", callback_data="up:preview"),
        ],
        [InlineKeyboardButton(text="🔁 Qayta yuklash", callback_data="up:retry")],
    ])


async def _get_lang(state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("language_code", "uz")


# ─────────────────────── Quiz yaratish menyu ───────────────────────

@router.message(F.text.in_({"📤 Quiz Yaratish", "📤 Создать квиз", "📤 Create Quiz"}))
@router.message(Command("create"))
async def quiz_create_menu(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(state)
    await state.set_state(QuizStates.FILE_UPLOAD)
    await message.answer(
        t("upload_select_method", lang),
        reply_markup=_create_keyboard(),
    )


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
        f"⏳ Qayta ishlanmoqda...\n📄 {doc.file_name}\n[░░░░░░░░░░ 0%]"
    )
    await state.set_state(QuizStates.PROCESSING)

    try:
        file = await message.bot.get_file(doc.file_id)
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"

        await progress_msg.edit_text(
            f"⏳ Qayta ishlanmoqda...\n📄 {doc.file_name}\n[████░░░░░░ 40%]"
        )

        result = await ai_engine_client().process_file(
            file_url=file_url,
            file_name=doc.file_name,
            file_size=doc.file_size,
            user_id=message.from_user.id,
        )

        await progress_msg.edit_text(
            f"⏳ Qayta ishlanmoqda...\n📄 {doc.file_name}\n[████████░░ 80%]"
        )

        task_id = result.get("task_id")
        if not task_id:
            if result.get("status") == "already_processed":
                await progress_msg.edit_text(
                    "ℹ️ Bu fayl avval yuklangan.\n"
                    f"Quiz ID: {result.get('quiz_id', '—')}"
                )
                await state.clear()
                return

        # Task ID ni saqlab qo'yamiz — polling uchun
        await state.update_data(
            task_id=task_id,
            file_name=doc.file_name,
            import_log_id=result.get("import_log_id"),
        )

        await progress_msg.edit_text(
            f"⏳ AI tahlil qilmoqda...\n📄 {doc.file_name}\n[██████████ 100%]\n\n"
            "Natija tayyor bo'lgach xabar keladi."
        )

    except Exception as e:
        logger.error("Fayl yuklash xatosi: %s", e)
        await progress_msg.edit_text(t("upload_error", lang))
        await state.clear()


# ─────────────────────── Rasm handler ───────────────────────

@router.message(QuizStates.IMAGE_UPLOAD, F.photo)
async def handle_photo(message: Message, state: FSMContext) -> None:
    """Foydalanuvchi rasm yuboradi — file_id larni yig'amiz."""
    data = await state.get_data()
    file_ids: list = data.get("image_file_ids", [])

    # Eng katta o'lchamdagi rasmni olamiz
    photo: PhotoSize = message.photo[-1]
    file_ids.append(photo.file_id)
    await state.update_data(image_file_ids=file_ids)

    count = len(file_ids)
    await message.answer(
        f"📷 {count} ta rasm qabul qilindi.\n"
        "Yana rasm yuboring yoki '✅ Tamom' bosing.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tamom", callback_data="up:images_done")]
        ]),
    )


@router.callback_query(F.data == "up:images_done")
async def cb_images_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    file_ids: list = data.get("image_file_ids", [])

    if not file_ids:
        await callback.answer("Hech qanday rasm yuborilmadi!", show_alert=True)
        return

    progress_msg = await callback.message.edit_text(
        f"⏳ {len(file_ids)} ta rasm tahlil qilinmoqda...\n[████████░░ 80%]"
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
        await state.update_data(task_id=task_id, file_name="rasmlar")

        await progress_msg.edit_text(
            f"⏳ AI Vision tahlil qilmoqda ({len(file_ids)} ta rasm)...\n"
            "Natija tayyor bo'lgach xabar keladi."
        )
    except Exception as e:
        logger.error("Rasm yuklash xatosi: %s", e)
        await progress_msg.edit_text("❌ Rasmlar qayta ishlanmadi. Keyinroq urinib ko'ring.")
        await state.clear()


# ─────────────────────── Save callbacks ───────────────────────

@router.callback_query(F.data == "up:save")
async def cb_save_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    task_id = data.get("task_id")

    if not task_id:
        await callback.answer("Quiz topilmadi!", show_alert=True)
        return

    try:
        await ai_engine_client().save_quiz(
            task_id=task_id,
            name=data.get("file_name", "Yangi quiz"),
            tags=[],
            is_public=False,
            quiz_group_id=None,
            user_id=callback.from_user.id,
        )
        await callback.message.edit_text("✅ Quiz saqlandi! /quiz bilan boshlashingiz mumkin.")
    except Exception as e:
        logger.error("Quiz saqlash xatosi: %s", e)
        await callback.message.edit_text("❌ Saqlashda xato yuz berdi.")
    finally:
        await state.clear()
    await callback.answer()


@router.callback_query(F.data == "up:retry")
async def cb_retry(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _get_lang(state)
    await state.set_state(QuizStates.FILE_UPLOAD)
    await callback.message.edit_text(
        t("upload_select_method", lang),
        reply_markup=_create_keyboard(),
    )
    await callback.answer()

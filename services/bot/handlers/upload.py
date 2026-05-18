"""
Upload handlers: fayl va rasm yuborish orqali quiz yaratish.

BOT_UX.md §6:
  §6.1 — Fayl yuklash (.docx/.pdf/.xlsx/.txt)
  §6.3 — Rasm yuborish
"""

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Document,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from fsm.states import QuizStates
from keyboards.inline import quiz_done_with_review_keyboard
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
POLL_INTERVAL = 4  # sekund
POLL_TIMEOUT = 300  # 5 daqiqa


def _create_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Fayl yuklash", callback_data="up:file")],
        ]
    )


def _done_keyboard(quiz_id: str) -> InlineKeyboardMarkup:
    return quiz_done_with_review_keyboard(quiz_id)


async def _get_lang(state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("language_code", "uz")


# ─────────────────────── Polling background task ───────────────────────

_SPINNER = ["⏳", "⌛️"]
_STATUS_UPDATE_EVERY = 3  # har 3 siklda (12 sek) xabar yangilanadi


async def _poll_until_done(
    bot: Bot,
    chat_id: int,
    user_id: int,
    task_id: str,
    file_name: str,
    lang: str,
    progress_msg_id: int,
) -> None:
    loop = asyncio.get_running_loop()
    start = loop.time()
    deadline = start + POLL_TIMEOUT
    tick = 0

    while loop.time() < deadline:
        await asyncio.sleep(POLL_INTERVAL)
        tick += 1
        elapsed = int(loop.time() - start)

        try:
            data = await ai_engine_client().get_task_status(task_id)
            status = data.get("status")
        except Exception as exc:
            logger.warning("poll task %s status xatosi: %s", task_id, exc)
            continue

        if status == "completed":
            result = data.get("result", {})
            quiz_id = result.get("quiz_id")
            total_q = result.get("total_questions", 0)

            if not quiz_id or total_q == 0:
                try:
                    await bot.edit_message_text(
                        "⚠️ Faylda savol topilmadi. Boshqa fayl yuboring.",
                        chat_id=chat_id,
                        message_id=progress_msg_id,
                        reply_markup=_create_keyboard(),
                    )
                except Exception:
                    await bot.send_message(
                        chat_id, "⚠️ Faylda savol topilmadi. Boshqa fayl yuboring."
                    )
                return

            warnings = result.get("warnings", {})
            warn_lines = []
            if warnings.get("skipped_no_options", 0):
                warn_lines.append(
                    f"⛔️ {warnings['skipped_no_options']} ta savol o'tkazib yuborildi (variant topilmadi)"
                )
            if warnings.get("few_options", 0):
                warn_lines.append(
                    f"⚠️ {warnings['few_options']} ta savolda 4 dan kam variant"
                )
            if warnings.get("many_options", 0):
                warn_lines.append(
                    f"⚠️ {warnings['many_options']} ta savolda 4 dan ko'p variant"
                )

            labels = {
                "uz": f"✅ Quiz tayyor!\n📄 <b>{file_name}</b>\n📊 {total_q} ta savol topildi.",
                "ru": f"✅ Квиз готов!\n📄 <b>{file_name}</b>\n📊 Найдено вопросов: {total_q}.",
                "en": f"✅ Quiz ready!\n📄 <b>{file_name}</b>\n📊 {total_q} questions found.",
            }
            text = labels.get(lang, labels["uz"])
            if warn_lines:
                text += "\n\n" + "\n".join(warn_lines)

            try:
                await bot.edit_message_text(
                    text,
                    chat_id=chat_id,
                    message_id=progress_msg_id,
                    reply_markup=_done_keyboard(quiz_id),
                )
            except Exception:
                # progress xabari o'chirilgan bo'lsa — yangi xabar yuboramiz
                await bot.send_message(
                    chat_id,
                    text,
                    reply_markup=_done_keyboard(quiz_id),
                )
            return

        if status == "failed":
            try:
                await bot.edit_message_text(
                    t("upload_error", lang),
                    chat_id=chat_id,
                    message_id=progress_msg_id,
                )
            except Exception:
                await bot.send_message(chat_id, t("upload_error", lang))
            return

        # Har 3 siklda (12 sek) status xabarini yangilash
        if tick % _STATUS_UPDATE_EVERY == 0:
            try:
                spinner = _SPINNER[(tick // _STATUS_UPDATE_EVERY) % len(_SPINNER)]
                mins, secs = divmod(elapsed, 60)
                timer = f"{mins}:{secs:02d}" if mins else f"{secs} sek"
                await bot.edit_message_text(
                    f"{spinner} AI savol ajratmoqda...\n📄 {file_name}\n⏱ {timer}",
                    chat_id=chat_id,
                    message_id=progress_msg_id,
                )
            except Exception:
                pass

    # Timeout
    try:
        await bot.edit_message_text(
            t("upload_error", lang),
            chat_id=chat_id,
            message_id=progress_msg_id,
        )
    except Exception:
        await bot.send_message(chat_id, t("upload_error", lang))


# ─────────────────────── Quiz yaratish menyu ───────────────────────


@router.message(F.text.in_({"📤 Quiz Yaratish", "📤 Создать квиз", "📤 Create Quiz"}))
@router.message(Command("create"))
async def quiz_create_menu(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(state)
    await state.set_state(QuizStates.FILE_UPLOAD)
    await message.answer(
        t("upload_select_method", lang), reply_markup=_create_keyboard()
    )


@router.callback_query(F.data == "up:file")
async def cb_file_upload(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _get_lang(state)
    await state.set_state(QuizStates.FILE_UPLOAD)
    await callback.message.edit_text(t("upload_send_file", lang))
    await callback.answer()


@router.callback_query(F.data == "up:image")
async def cb_image_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer(
        "⏳ Rasm orqali quiz yaratish vaqtincha to'xtatilgan.\nIltimos, fayl yuboring (PDF, DOCX, TXT).",
        show_alert=True,
    )


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

    progress_msg = await message.answer(f"⏳ Yuklanmoqda...\n📄 {doc.file_name}")
    await state.set_state(QuizStates.PROCESSING)

    try:
        file = await message.bot.get_file(doc.file_id)
        file_url = (
            f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
        )

        await progress_msg.edit_text(f"🔍 AI tahlil qilmoqda...\n📄 {doc.file_name}")

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

        await progress_msg.edit_text(
            f"🤖 AI savol ajratmoqda...\n📄 {doc.file_name}\n\nNatija tayyor bo'lgach xabar keladi ✉️"
        )
        await state.clear()

        # Background polling — state endi kerak emas
        asyncio.create_task(
            _poll_until_done(
                bot=message.bot,
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                task_id=task_id,
                file_name=doc.file_name,
                lang=lang,
                progress_msg_id=progress_msg.message_id,
            )
        )

    except Exception as e:
        logger.error("Fayl yuklash xatosi: %s", e)
        await progress_msg.edit_text(t("upload_error", lang))
        await state.clear()


# ─────────────────────── Rasm handler ───────────────────────


@router.message(QuizStates.IMAGE_UPLOAD, F.photo)
async def handle_photo(message: Message, state: FSMContext) -> None:
    # Rasm orqali quiz yaratish vaqtincha to'xtatilgan
    await message.answer(
        "⏳ Rasm orqali quiz yaratish vaqtincha to'xtatilgan.\nIltimos, fayl yuboring (PDF, DOCX, TXT).",
        reply_markup=_create_keyboard(),
    )
    await state.set_state(QuizStates.FILE_UPLOAD)


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

        asyncio.create_task(
            _poll_until_done(
                bot=callback.bot,
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                task_id=task_id,
                file_name="rasmlar",
                lang=lang,
            )
        )

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

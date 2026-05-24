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
from utils.api import ai_engine_client, subscription_client
from utils.i18n import t
from utils.task_tracker import save_pending_task, remove_pending_task
from redis_client import get_redis

logger = logging.getLogger(__name__)
router = Router()

ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
POLL_INTERVAL = 4  # sekund
POLL_TIMEOUT = 900  # 15 daqiqa


def _create_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Fayl yuklash", callback_data="up:file")],
        ]
    )


def _done_keyboard(quiz_id: str, bot_username: str = "aiquizlybot") -> InlineKeyboardMarkup:
    return quiz_done_with_review_keyboard(quiz_id, bot_username)


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
    bot_username: str = "aiquizlybot",
    redis_client=None,
) -> None:
    # Redis da saqlash — restart da tiklansin
    if redis_client:
        try:
            await save_pending_task(redis_client, task_id, chat_id, user_id,
                                    file_name, lang, progress_msg_id, bot_username)
        except Exception:
            pass
    try:
        await _do_poll(bot, chat_id, task_id, file_name, lang, progress_msg_id, bot_username)
    finally:
        # Task tugagach (yoki xato) Redis dan o'chirish
        if redis_client:
            try:
                await remove_pending_task(redis_client, task_id)
            except Exception:
                pass


async def _do_poll(
    bot: Bot,
    chat_id: int,
    task_id: str,
    file_name: str,
    lang: str,
    progress_msg_id: int,
    bot_username: str,
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
                warnings = result.get("warnings", {})
                if warnings.get("quota_error"):
                    msg = t("ai_quota_error", lang)
                else:
                    msg = t("upload_no_questions", lang)
                try:
                    await bot.edit_message_text(msg, chat_id=chat_id, message_id=progress_msg_id)
                except Exception:
                    await bot.send_message(chat_id, msg)
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

            share_link = f"https://t.me/{bot_username}?start=quiz_{quiz_id}"
            labels = {
                "uz": f"✅ Quiz tayyor!\n📄 <b>{file_name}</b>\n📊 {total_q} ta savol topildi.\n\n🔗 <code>{share_link}</code>",
                "ru": f"✅ Квиз готов!\n📄 <b>{file_name}</b>\n📊 Найдено вопросов: {total_q}.\n\n🔗 <code>{share_link}</code>",
                "en": f"✅ Quiz ready!\n📄 <b>{file_name}</b>\n📊 {total_q} questions found.\n\n🔗 <code>{share_link}</code>",
            }
            text = labels.get(lang, labels["uz"])
            if warn_lines:
                text += "\n\n" + "\n".join(warn_lines)

            try:
                await bot.edit_message_text(
                    text,
                    chat_id=chat_id,
                    message_id=progress_msg_id,
                    reply_markup=_done_keyboard(quiz_id, bot_username),
                )
            except Exception:
                # progress xabari o'chirilgan bo'lsa — yangi xabar yuboramiz
                await bot.send_message(
                    chat_id,
                    text,
                    reply_markup=_done_keyboard(quiz_id, bot_username),
                )
            return

        if status == "failed":
            error_msg = result.get("error", "")
            if "AI_QUOTA_ERROR" in error_msg:
                msg = t("ai_quota_error", lang)
            else:
                msg = t("upload_error", lang)
            try:
                await bot.edit_message_text(msg, chat_id=chat_id, message_id=progress_msg_id)
            except Exception:
                await bot.send_message(chat_id, msg)
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
    await message.answer(t("upload_send_file", lang))


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

            # quiz_id None bo'lsa — user ning quizlaridan shu fayl nomiga mos qidiramiz
            if not quiz_id:
                try:
                    data_q = await ai_engine_client().get_quizzes(
                        user_id=message.from_user.id
                    )
                    quizzes = data_q.get("quizzes", []) if isinstance(data_q, dict) else []
                    file_title = doc.file_name.rsplit(".", 1)[0]
                    for q in quizzes:
                        if q.get("title", "").strip() == file_title.strip():
                            quiz_id = q.get("id") or q.get("quiz_id")
                            break
                except Exception:
                    pass

            await state.update_data(
                reprocess_file_url=file_url,
                reprocess_file_name=doc.file_name,
                reprocess_file_size=doc.file_size,
            )
            kb_rows = []
            if quiz_id:
                kb_rows.append([InlineKeyboardButton(text="▶️ Quizni boshlash", callback_data=f"up:existing:{quiz_id}")])
            kb_rows.append([InlineKeyboardButton(text="🔄 Qaytadan tahlil qilish", callback_data="up:reprocess")])

            await progress_msg.edit_text(
                f"✅ <b>{doc.file_name}</b>\n\nBu fayl avval tahlil qilingan — quiz tayyor!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
                parse_mode="HTML",
            )
            return

        task_id = result.get("task_id")
        if not task_id:
            raise ValueError("task_id qaytarilmadi")

        await progress_msg.edit_text(
            f"🤖 AI savol ajratmoqda...\n📄 {doc.file_name}\n\nNatija tayyor bo'lgach xabar keladi ✉️"
        )
        await state.clear()
        # Foydalanish limitini oshirish
        try:
            await subscription_client().increment_usage(message.from_user.id)
        except Exception:
            pass

        # Background polling — Redis da saqlanadi, restart da tiklanadi
        me = await message.bot.get_me()
        asyncio.create_task(
            _poll_until_done(
                bot=message.bot,
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                task_id=task_id,
                file_name=doc.file_name,
                lang=lang,
                progress_msg_id=progress_msg.message_id,
                bot_username=me.username or "aiquizlybot",
                redis_client=get_redis(),
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


@router.callback_query(F.data == "up:reprocess")
async def cb_reprocess(callback: CallbackQuery, state: FSMContext) -> None:
    """Avval yuklangan faylni force=True bilan qayta tahlil qilish."""
    lang = await _get_lang(state)
    data = await state.get_data()
    file_url = data.get("reprocess_file_url")
    file_name = data.get("reprocess_file_name", "fayl")
    file_size = data.get("reprocess_file_size", 0)

    if not file_url:
        await callback.answer("Fayl ma'lumoti topilmadi. Qaytadan yuboring.", show_alert=True)
        await state.clear()
        return

    progress_msg = await callback.message.edit_text(
        f"🔍 Qayta tahlil qilinmoqda...\n📄 {file_name}"
    )
    await callback.answer()

    try:
        result = await ai_engine_client().process_file(
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            user_id=callback.from_user.id,
            force=True,
        )
        task_id = result.get("task_id")
        if not task_id:
            raise ValueError("task_id qaytarilmadi")

        await progress_msg.edit_text(
            f"🤖 AI savol ajratmoqda...\n📄 {file_name}\n\nNatija tayyor bo'lgach xabar keladi ✉️"
        )
        await state.clear()
        me = await callback.bot.get_me()
        asyncio.create_task(
            _poll_until_done(
                bot=callback.bot,
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                task_id=task_id,
                file_name=file_name,
                lang=lang,
                progress_msg_id=progress_msg.message_id,
                bot_username=me.username or "aiquizlybot",
                redis_client=get_redis(),
            )
        )
    except Exception as e:
        logger.error("Qayta tahlil xatosi: %s", e)
        await progress_msg.edit_text(t("upload_error", lang))
        await state.clear()


@router.callback_query(F.data.startswith("up:existing:"))
async def cb_existing_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    """Mavjud quizga o'tish — to'g'ridan set tanlash ekrani."""
    quiz_id = callback.data.split(":", 2)[2]
    await callback.answer()
    from keyboards.inline import set_select_keyboard
    from utils.api import ai_engine_client as _ai
    from fsm.states import QuizStates

    try:
        quiz = await _ai().get_quiz(quiz_id)
        title = quiz.get("title", "Quiz")
        total_q = quiz.get("total_questions", 0)
        set_size = 20
        num_sets = max(1, (total_q + set_size - 1) // set_size) if total_q else 1
        sets = [
            {"set_number": i + 1, "question_count": min(set_size, total_q - i * set_size)}
            for i in range(num_sets)
        ]
        me = await callback.bot.get_me()
        share_link = f"https://t.me/{me.username}?start=quiz_{quiz_id}"

        await state.set_state(QuizStates.BROWSING_MY_QUIZZES)
        await state.update_data(quiz_id=quiz_id, quiz_title=title)

        await callback.message.edit_text(
            f"📋 <b>{title}</b>\n"
            f"📏 {total_q} savol | {num_sets} set\n\n"
            f"🔗 <code>{share_link}</code>\n\n"
            "Set tanlang:",
            reply_markup=set_select_keyboard(sets, quiz_id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("cb_existing_quiz xatosi: %s", e, exc_info=True)
        await callback.message.edit_text(
            "Quiz topilmadi.", reply_markup=_create_keyboard()
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

        me = await callback.bot.get_me()
        asyncio.create_task(
            _poll_until_done(
                bot=callback.bot,
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                task_id=task_id,
                file_name="rasmlar",
                lang=lang,
                bot_username=me.username or "aiquizlybot",
                redis_client=get_redis(),
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

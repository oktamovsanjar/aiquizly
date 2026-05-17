import httpx
import os
import logging

from aiogram import Router, F
from aiogram.types import Message, Document

logger = logging.getLogger(__name__)
router = Router()

AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://ai-engine:8002")
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.message(F.text == "📤 Quiz Yaratish")
async def quiz_create_menu(message: Message) -> None:
    await message.answer(
        "Quiz yaratish:\n\n"
        "📄 Fayl yuklash — Word/PDF/Excel\n"
        "📷 Rasm yuborish — Screenshot/skan\n"
        "✍️ Qo'lda yozish",
        # TODO: inline keyboard qo'shish
    )


@router.message(F.document)
async def handle_document(message: Message) -> None:
    """Fayl yuklash — AI Engine ga yuborish"""
    doc: Document = message.document

    if doc.file_size > MAX_FILE_SIZE:
        await message.answer("❌ Fayl hajmi 10 MB dan oshmasligi kerak.")
        return

    if doc.mime_type not in ALLOWED_MIME_TYPES:
        await message.answer("❌ Faqat .docx, .pdf, .xlsx, .txt fayllar qabul qilinadi.")
        return

    progress_msg = await message.answer(f"⏳ Qayta ishlanmoqda...\n📄 {doc.file_name}")

    try:
        file = await message.bot.get_file(doc.file_id)
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{AI_ENGINE_URL}/process",
                json={
                    "file_url": file_url,
                    "file_name": doc.file_name,
                    "file_size": doc.file_size,
                    "user_id": str(message.from_user.id),
                },
            )
            resp.raise_for_status()
            data = resp.json()

        await progress_msg.edit_text(
            f"✅ {data.get('total_questions', 0)} ta savol topildi!\n\n"
            f"To'plam nomi: {doc.file_name}\n"
            f"Avtomatik bo'lindi: {data.get('total_sets', 0)} ta set"
        )

    except httpx.HTTPError as e:
        logger.error("AI Engine xatosi: %s", e)
        await progress_msg.edit_text("❌ Fayl qayta ishlanmadi. Keyinroq urinib ko'ring.")

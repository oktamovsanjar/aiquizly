"""Stage 5: Validation — AI natijasini tekshiradi"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def validate_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    AI natijasini tekshiradi va to'g'ri savollarni qaytaradi.
    Noto'g'ri savollar o'tkazib yuboriladi (HECH QACHON DB ga yozilmaydi).
    """
    if not isinstance(questions, list):
        return []

    valid = []
    seen_questions = set()

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            logger.warning("Savol %d: dict emas", i)
            continue

        # Majburiy tekshiruvlar
        question_text = q.get("question", "").strip()
        if not question_text:
            logger.warning("Savol %d: question maydoni bo'sh", i)
            continue

        options = q.get("options", [])
        if not isinstance(options, list) or len(options) < 2:
            logger.warning("Savol %d: kamida 2 variant kerak", i)
            continue

        correct_index = q.get("correct_index")
        if not isinstance(correct_index, int) or not (0 <= correct_index < len(options)):
            logger.warning("Savol %d: correct_index noto'g'ri: %s", i, correct_index)
            continue

        # Dublikat tekshirish (fuzzy match emas, oddiy)
        normalized = question_text.lower()
        if normalized in seen_questions:
            logger.warning("Savol %d: dublikat topildi", i)
            continue
        seen_questions.add(normalized)

        valid.append({
            "question": question_text,
            "options": [str(o) for o in options],
            "correct_index": correct_index,
            "explanation": q.get("explanation", "") or "",
        })

    return valid

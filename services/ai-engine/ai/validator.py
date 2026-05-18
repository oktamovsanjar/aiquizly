"""Stage 5: Validation — AI natijasini tekshiradi"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

STANDARD_OPTIONS = 4


def validate_questions(
    questions: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    AI natijasini tekshiradi va to'g'ri savollarni qaytaradi.

    Qaytaradi: (valid_questions, stats)
    stats = {
        "skipped_no_options": int,   # variant yo'q yoki 1 ta
        "few_options": int,          # 2-3 ta variant (standart 4 dan kam)
        "many_options": int,         # 5+ ta variant (standart 4 dan ko'p)
        "duplicates": int,
    }
    """
    if not isinstance(questions, list):
        return [], {
            "skipped_no_options": 0,
            "few_options": 0,
            "many_options": 0,
            "duplicates": 0,
        }

    valid = []
    seen_questions = set()
    stats = {
        "skipped_no_options": 0,
        "few_options": 0,
        "many_options": 0,
        "duplicates": 0,
    }

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue

        question_text = q.get("question", "").strip()
        if not question_text:
            continue

        options = q.get("options", [])
        if not isinstance(options, list) or len(options) < 2:
            logger.warning("Savol %d: variant yo'q yoki 1 ta — o'tkazib yuborildi", i)
            stats["skipped_no_options"] += 1
            continue

        correct_index = q.get("correct_index")
        if not isinstance(correct_index, int) or not (
            0 <= correct_index < len(options)
        ):
            logger.warning("Savol %d: correct_index noto'g'ri: %s", i, correct_index)
            continue

        normalized = question_text.lower()
        if normalized in seen_questions:
            stats["duplicates"] += 1
            continue
        seen_questions.add(normalized)

        n = len(options)
        if n < STANDARD_OPTIONS:
            stats["few_options"] += 1
        elif n > STANDARD_OPTIONS:
            stats["many_options"] += 1

        valid.append(
            {
                "question": question_text,
                "options": [str(o).strip() for o in options],
                "correct_index": correct_index,
                "explanation": q.get("explanation", "") or "",
            }
        )

    return valid, stats

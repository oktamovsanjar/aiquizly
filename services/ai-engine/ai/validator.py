"""Stage 5: Validation — AI natijasini tekshiradi"""

import logging
import re
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

STANDARD_OPTIONS = 4
SIMILARITY_THRESHOLD = 0.85


def _normalize(text: str) -> str:
    """Matnni solishtirish uchun normallashtiradi."""
    text = text.lower().strip()
    text = re.sub(r"^\d+[\.\)]\s*", "", text)   # bosh raqam: "1. " yoki "1) "
    text = re.sub(r"\s+", " ", text)             # ko'p bo'sh joy → bitta
    text = re.sub(r"[?!.,;:]+$", "", text)       # oxirgi tinish belgilari
    return text


def _trigrams(text: str) -> set:
    return {text[i:i+3] for i in range(len(text) - 2)} if len(text) >= 3 else {text}


def _similarity(a: str, b: str) -> float:
    """Jaccard trigram o'xshashligi."""
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 1.0 if a == b else 0.0
    return len(ta & tb) / len(ta | tb)


def _is_duplicate(text: str, seen: list, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    for s in seen:
        if _similarity(text, s) >= threshold:
            return True
    return False


def validate_questions(
    questions: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    AI natijasini tekshiradi va to'g'ri savollarni qaytaradi.

    Qaytaradi: (valid_questions, stats)
    stats = {
        "skipped_no_options": int,
        "few_options": int,
        "many_options": int,
        "duplicates": int,
    }
    """
    if not isinstance(questions, list):
        return [], {"skipped_no_options": 0, "few_options": 0, "many_options": 0, "duplicates": 0}

    valid = []
    seen_normalized: list = []
    stats = {"skipped_no_options": 0, "few_options": 0, "many_options": 0, "duplicates": 0}

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
        if not isinstance(correct_index, int) or not (0 <= correct_index < len(options)):
            logger.warning("Savol %d: correct_index noto'g'ri: %s", i, correct_index)
            continue

        normalized = _normalize(question_text)
        if _is_duplicate(normalized, seen_normalized):
            stats["duplicates"] += 1
            continue
        seen_normalized.append(normalized)

        n = len(options)
        if n < STANDARD_OPTIONS:
            stats["few_options"] += 1
        elif n > STANDARD_OPTIONS:
            stats["many_options"] += 1

        valid.append({
            "question": question_text,
            "options": [str(o).strip() for o in options],
            "correct_index": correct_index,
            "explanation": q.get("explanation", "") or "",
        })

    return valid, stats

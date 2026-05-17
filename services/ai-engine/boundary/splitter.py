"""Stage 3: Boundary Detection — matndan savollarni blok-blok ajratadi"""
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class QuestionBlock:
    question: str
    options: List[str] = field(default_factory=list)
    answer_hint: str = ""  # Topilgan to'g'ri javob belgisi (agar bor bo'lsa)
    raw_text: str = ""


# Savol boshlanish pattern lari
QUESTION_PATTERNS = [
    re.compile(r"^\s*(\d+)[.)]\s+(.+)"),        # "1. Savol" yoki "1) Savol"
    re.compile(r"^\s*№\s*(\d+)\s*[.):]?\s*(.+)"),  # "№1 Savol"
]

# Variant pattern lari
OPTION_PATTERNS = [
    re.compile(r"^\s*([A-Да-д])[.)]\s+(.+)", re.IGNORECASE),  # "A) variant"
    re.compile(r"^\s*([A-Да-д])[.]\s+(.+)", re.IGNORECASE),   # "A. variant"
]

# To'g'ri javob pattern lari
ANSWER_PATTERNS = [
    re.compile(r"^[Жж]авоб\s*[:.]?\s*(.+)"),         # "Жавоб: B"
    re.compile(r"^[Аа]нсвер\s*[:.]?\s*(.+)"),         # "Answer: B"
    re.compile(r"^\*\*(.+)\*\*$"),                     # **qalin** variant
]


def detect_boundaries(text: str) -> List[QuestionBlock]:
    """
    Matndan savollarni ajratadi.
    Qaytaradi: QuestionBlock lardan iborat ro'yxat.
    """
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    blocks: List[QuestionBlock] = []
    current_block: QuestionBlock | None = None

    for line in lines:
        stripped = line.strip()

        # Yangi savol boshlanishi?
        q_match = _match_question(stripped)
        if q_match:
            if current_block:
                blocks.append(current_block)
            current_block = QuestionBlock(question=q_match, raw_text=stripped + "\n")
            continue

        # Variant?
        opt_match = _match_option(stripped)
        if opt_match and current_block is not None:
            current_block.options.append(opt_match)
            current_block.raw_text += stripped + "\n"
            continue

        # To'g'ri javob belgisi?
        ans_match = _match_answer(stripped)
        if ans_match and current_block is not None:
            current_block.answer_hint = ans_match
            current_block.raw_text += stripped + "\n"
            continue

        # Mavjud blokka qo'shimcha matn
        if current_block is not None and stripped:
            current_block.raw_text += stripped + "\n"

    if current_block:
        blocks.append(current_block)

    return blocks


def _match_question(line: str) -> str | None:
    for pattern in QUESTION_PATTERNS:
        m = pattern.match(line)
        if m:
            return m.group(2).strip()
    return None


def _match_option(line: str) -> str | None:
    for pattern in OPTION_PATTERNS:
        m = pattern.match(line)
        if m:
            return m.group(2).strip()
    return None


def _match_answer(line: str) -> str | None:
    for pattern in ANSWER_PATTERNS:
        m = pattern.match(line)
        if m:
            return m.group(1).strip()
    return None

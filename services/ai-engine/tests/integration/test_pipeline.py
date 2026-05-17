"""
AI Engine pipeline integration testlar.

Har bir stage alohida test qilinadi:
  Stage 1: Format detection
  Stage 2: Text extraction (mock fayllar bilan)
  Stage 3: Boundary detection (real matn bilan)
  Stage 4: AI Structuring (mock OpenAI/DeepSeek bilan)
  Stage 5: Validation

QA.md §5 ga asoslanadi.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Stage 1: Format Detection ─────────────────────────────────────────────────

def test_format_detect_docx():
    from parsers.detector import detect_format
    assert detect_format("biology.docx") == "word"


def test_format_detect_pdf():
    from parsers.detector import detect_format
    assert detect_format("test.pdf") == "pdf"


def test_format_detect_xlsx():
    from parsers.detector import detect_format
    assert detect_format("questions.xlsx") == "excel"


def test_format_detect_txt():
    from parsers.detector import detect_format
    assert detect_format("savollar.txt") == "text"


def test_format_detect_png():
    from parsers.detector import detect_format
    assert detect_format("screenshot.png") == "image"


def test_format_detect_jpg():
    from parsers.detector import detect_format
    assert detect_format("photo.jpg") == "image"


def test_format_detect_unknown_raises():
    from parsers.detector import detect_format
    with pytest.raises(ValueError):
        detect_format("file.xyz")


# ── Stage 3: Boundary Detection (real matn) ───────────────────────────────────

def test_boundary_numbered_questions():
    """Raqamli savollar (1. 2. 3.) to'g'ri ajratilishi."""
    from boundary.splitter import detect_boundaries

    text = (
        "1. O'zbekistonning poytaxti?\n"
        "A) Samarqand\n"
        "B) Toshkent\n"
        "C) Buxoro\n"
        "D) Namangan\n"
        "Javob: B\n\n"
        "2. Quyosh tizimidagi eng katta sayyora?\n"
        "A) Saturn\n"
        "B) Mars\n"
        "C) Yupiter\n"
        "D) Venera\n"
        "Javob: C\n"
    )
    blocks = detect_boundaries(text)
    assert len(blocks) >= 2
    assert "poytaxti" in blocks[0].raw_text
    assert "sayyora" in blocks[1].raw_text


def test_boundary_empty_text():
    """Bo'sh matn — bo'sh ro'yxat."""
    from boundary.splitter import detect_boundaries
    blocks = detect_boundaries("")
    assert blocks == []


def test_boundary_single_question():
    """Bitta savol — bitta block."""
    from boundary.splitter import detect_boundaries
    text = "1. Test savol?\nA) Ha\nB) Yo'q\n"
    blocks = detect_boundaries(text)
    assert len(blocks) >= 1


def test_boundary_no_options():
    """Variantsiz savol — block yaratilishi (yoki bo'sh)."""
    from boundary.splitter import detect_boundaries
    text = "1. Faqat savol matni"
    blocks = detect_boundaries(text)
    # Hech bo'lmaganda xato bermasligi kerak
    assert isinstance(blocks, list)


# ── Stage 4: AI Structuring (mock API) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_structurer_parses_valid_response():
    """Mock AI response → to'g'ri JSON parse."""
    try:
        from ai import AIStructurer
        from boundary.splitter import QuestionBlock
    except ImportError:
        pytest.skip("Structurer relative import — Docker ichida ishlanadi")

    structurer = AIStructurer()

    mock_response_data = {
        "questions": [
            {
                "question": "O'zbekistonning poytaxti?",
                "options": ["Samarqand", "Toshkent", "Buxoro", "Namangan"],
                "correct_index": 1,
                "explanation": "Toshkent — O'zbekistonning poytaxti.",
            }
        ]
    }

    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_response_data)
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch.object(structurer.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_completion
        blocks = [QuestionBlock(raw_text="O'zbekistonning poytaxti?\nA) Samarqand\nB) Toshkent")]
        result = await structurer.structure_blocks(blocks)

    assert len(result) == 1
    assert result[0]["question"] == "O'zbekistonning poytaxti?"
    assert result[0]["correct_index"] == 1


@pytest.mark.asyncio
async def test_structurer_retries_on_invalid_json():
    """AI noto'g'ri JSON bersa retry ishlaydi."""
    try:
        from ai import AIStructurer
        from boundary.splitter import QuestionBlock
    except ImportError:
        pytest.skip("Structurer relative import — Docker ichida ishlanadi")

    structurer = AIStructurer()
    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        mock_choice = MagicMock()
        if call_count == 1:
            mock_choice.message.content = "bu JSON emas!!!"
        else:
            mock_choice.message.content = json.dumps({
                "questions": [{"question": "Q?", "options": ["A", "B"], "correct_index": 0}]
            })
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        return mock_completion

    with patch.object(structurer.client.chat.completions, "create", new_callable=AsyncMock) as mock_api:
        mock_api.side_effect = mock_create
        blocks = [QuestionBlock(raw_text="Q?\nA) A\nB) B")]
        result = await structurer.structure_blocks(blocks)

    assert call_count >= 2


@pytest.mark.asyncio
async def test_structurer_empty_blocks():
    """Bo'sh blocks → bo'sh ro'yxat."""
    try:
        from ai import AIStructurer
    except ImportError:
        pytest.skip("Structurer relative import — Docker ichida ishlanadi")

    structurer = AIStructurer()
    result = await structurer.structure_blocks([])
    assert result == []


# ── Stage 5: Validation ───────────────────────────────────────────────────────

def test_validator_valid_questions():
    """To'g'ri savollar → hamma o'tadi (list qaytaradi)."""
    from ai.validator import validate_questions

    questions = [
        {
            "question": "Savol 1?",
            "options": ["A", "B", "C", "D"],
            "correct_index": 0,
            "explanation": "Tushuntirish",
        },
        {
            "question": "Savol 2?",
            "options": ["Ha", "Yo'q"],
            "correct_index": 1,
        },
    ]
    result = validate_questions(questions)
    # validate_questions valid savollar listini qaytaradi
    assert isinstance(result, list)
    assert len(result) == 2


def test_validator_out_of_range_index():
    """correct_index options dan tashqarida → natijadan o'chiriladi."""
    from ai.validator import validate_questions

    questions = [
        {
            "question": "Savol?",
            "options": ["A", "B"],
            "correct_index": 5,  # Noto'g'ri
        }
    ]
    result = validate_questions(questions)
    assert len(result) == 0


def test_validator_missing_question_text():
    """Savol matni yo'q → natijadan o'chiriladi."""
    from ai.validator import validate_questions

    questions = [{"options": ["A", "B"], "correct_index": 0}]
    result = validate_questions(questions)
    assert len(result) == 0


def test_validator_empty_options():
    """Variantlar bo'sh → natijadan o'chiriladi."""
    from ai.validator import validate_questions

    questions = [{"question": "Savol?", "options": [], "correct_index": 0}]
    result = validate_questions(questions)
    assert len(result) == 0


def test_validator_mixed():
    """Aralash: faqat to'g'rilar qoladi."""
    from ai.validator import validate_questions

    questions = [
        {"question": "To'g'ri?", "options": ["A", "B"], "correct_index": 0},
        {"options": ["A"], "correct_index": 0},  # question yo'q → o'chiriladi
        {"question": "Yana to'g'ri?", "options": ["X", "Y", "Z"], "correct_index": 2},
    ]
    result = validate_questions(questions)
    assert len(result) == 2
    assert result[0]["question"] == "To'g'ri?"

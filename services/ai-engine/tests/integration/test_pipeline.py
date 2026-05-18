"""
AI Engine pipeline integration testlar.

Har bir stage alohida test qilinadi:
  Stage 1: Format detection
  Stage 2: Text extraction (mock fayllar bilan)
  Stage 3: Text chunking
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


# ── Stage 3: Text Chunking ────────────────────────────────────────────────────


def _import_chunk_text():
    """celery va config ni mock qilib _chunk_text ni yuklaydi."""
    import sys
    from unittest.mock import MagicMock

    sys.modules.setdefault("celery", MagicMock())
    sys.modules.setdefault("config", MagicMock())
    # Avval yuklangan bo'lsa qayta yuklamaslik
    if "tasks.process_file" in sys.modules:
        del sys.modules["tasks.process_file"]
    from tasks.process_file import _chunk_text

    return _chunk_text


def test_chunk_text_basic():
    """Matn to'g'ri bo'laklarga bo'linadi."""
    _chunk_text = _import_chunk_text()
    text = "A" * 20000
    chunks = _chunk_text(text, chunk_size=8000, overlap=200)
    assert len(chunks) == 3
    assert all(len(c.raw_text) <= 8000 for c in chunks)


def test_chunk_text_short():
    """Qisqa matn — bitta chunk."""
    _chunk_text = _import_chunk_text()
    text = "Qisqa matn"
    chunks = _chunk_text(text, chunk_size=8000, overlap=200)
    assert len(chunks) == 1
    assert chunks[0].raw_text == text


def test_chunk_text_empty():
    """Bo'sh matn — hech qanday chunk yo'q."""
    _chunk_text = _import_chunk_text()
    chunks = _chunk_text("", chunk_size=8000, overlap=200)
    assert len(chunks) == 0


def test_chunk_text_overlap():
    """Overlap ishlaydi — keyingi chunk oldingi oxirini o'z ichiga oladi."""
    _chunk_text = _import_chunk_text()
    # chunk_size=8000, overlap=200: i=0→7800→... ikkinchi chunk [7800:15800]
    # [7800:8000]="A"*200 (overlap), [8000:8200]="B"*200
    text = "A" * 8000 + "B" * 200 + "C" * 200
    chunks = _chunk_text(text, chunk_size=8000, overlap=200)
    assert len(chunks) >= 2
    # Ikkinchi chunk overlap tufayli birinchi A larning oxiri bilan boshlanadi
    assert chunks[1].raw_text[:200] == "A" * 200


# ── Stage 4: AI Structuring (mock API) ───────────────────────────────────────


def _make_settings_mock():
    m = MagicMock()
    m.ai_batch_size = 5
    m.ai_max_retries = 3
    m.ai_max_concurrent = 3
    m.ai_model_primary = "gpt-4o"
    m.ai_model_fallback = "gpt-4o-mini"
    m.openai_api_key = "test-key"
    return m


@pytest.mark.asyncio
async def test_structurer_parses_valid_response():
    """Mock AI response → to'g'ri JSON parse."""
    try:
        from ai import AIStructurer
    except ImportError:
        pytest.skip("Structurer relative import — Docker ichida ishlanadi")

    with patch("ai.structurer.settings", _make_settings_mock()):
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

        with patch.object(
            structurer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_completion
            blocks = [
                type(
                    "Block",
                    (),
                    {
                        "raw_text": "O'zbekistonning poytaxti?\nA) Samarqand\nB) Toshkent"
                    },
                )()
            ]
            questions, _ = await structurer.structure_blocks(blocks)

    assert len(questions) == 1
    assert questions[0]["question"] == "O'zbekistonning poytaxti?"
    assert questions[0]["correct_index"] == 1


@pytest.mark.asyncio
async def test_structurer_retries_on_invalid_json():
    """AI noto'g'ri JSON bersa retry ishlaydi."""
    try:
        from ai import AIStructurer
    except ImportError:
        pytest.skip("Structurer relative import — Docker ichida ishlanadi")

    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        mock_choice = MagicMock()
        if call_count == 1:
            mock_choice.message.content = "bu JSON emas!!!"
        else:
            mock_choice.message.content = json.dumps(
                {
                    "questions": [
                        {"question": "Q?", "options": ["A", "B"], "correct_index": 0}
                    ]
                }
            )
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        return mock_completion

    with patch("ai.structurer.settings", _make_settings_mock()):
        structurer = AIStructurer()
        with patch.object(
            structurer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_api:
            mock_api.side_effect = mock_create
            blocks = [type("Block", (), {"raw_text": "Q?\nA) A\nB) B"})()]
            await structurer.structure_blocks(blocks)

    assert call_count >= 2


@pytest.mark.asyncio
async def test_structurer_empty_blocks():
    """Bo'sh blocks → bo'sh ro'yxat."""
    try:
        from ai import AIStructurer
    except ImportError:
        pytest.skip("Structurer relative import — Docker ichida ishlanadi")

    with patch("ai.structurer.settings", _make_settings_mock()):
        structurer = AIStructurer()
        questions, stats = await structurer.structure_blocks([])

    assert questions == []
    assert stats == {}


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
    result, stats = validate_questions(questions)
    assert isinstance(result, list)
    assert len(result) == 2
    assert stats["few_options"] == 1  # "Savol 2?" 2 ta variant — standart 4 dan kam


def test_validator_out_of_range_index():
    """correct_index options dan tashqarida → natijadan o'chiriladi."""
    from ai.validator import validate_questions

    questions = [{"question": "Savol?", "options": ["A", "B"], "correct_index": 5}]
    result, _ = validate_questions(questions)
    assert len(result) == 0


def test_validator_missing_question_text():
    """Savol matni yo'q → natijadan o'chiriladi."""
    from ai.validator import validate_questions

    questions = [{"options": ["A", "B"], "correct_index": 0}]
    result, _ = validate_questions(questions)
    assert len(result) == 0


def test_validator_empty_options():
    """Variantlar bo'sh → natijadan o'chiriladi."""
    from ai.validator import validate_questions

    questions = [{"question": "Savol?", "options": [], "correct_index": 0}]
    result, stats = validate_questions(questions)
    assert len(result) == 0
    assert stats["skipped_no_options"] == 1


def test_validator_mixed():
    """Aralash: faqat to'g'rilar qoladi."""
    from ai.validator import validate_questions

    questions = [
        {"question": "To'g'ri?", "options": ["A", "B"], "correct_index": 0},
        {
            "question": "Bir variant",
            "options": ["A"],
            "correct_index": 0,
        },  # 1 ta variant → skip
        {"question": "Yana to'g'ri?", "options": ["X", "Y", "Z"], "correct_index": 2},
    ]
    result, stats = validate_questions(questions)
    assert len(result) == 2
    assert result[0]["question"] == "To'g'ri?"
    assert stats["skipped_no_options"] == 1

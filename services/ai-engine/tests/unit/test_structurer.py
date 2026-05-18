"""AI Structurer — validate_questions bilan integration test (mock OpenAI)"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ai.validator import validate_questions


def test_validate_strips_whitespace():
    questions = [
        {
            "question": "  Savol matni?  ",
            "options": ["A", "B", "C", "D"],
            "correct_index": 0,
            "explanation": "  Izoh  ",
        }
    ]
    result, _ = validate_questions(questions)
    assert len(result) == 1
    assert result[0]["question"] == "Savol matni?"
    assert result[0]["explanation"] == "  Izoh  "  # explanation strip qilinmaydi


def test_validate_options_converted_to_string():
    questions = [
        {
            "question": "Savol?",
            "options": [1, 2, 3, 4],
            "correct_index": 0,
        }
    ]
    result, _ = validate_questions(questions)
    assert len(result) == 1
    assert all(isinstance(o, str) for o in result[0]["options"])


def test_validate_missing_explanation_ok():
    questions = [
        {
            "question": "Savol?",
            "options": ["A", "B"],
            "correct_index": 1,
        }
    ]
    result, _ = validate_questions(questions)
    assert len(result) == 1
    assert result[0]["explanation"] == ""


def test_validate_correct_index_out_of_range():
    questions = [
        {"question": "S1?", "options": ["A", "B"], "correct_index": 2},
        {"question": "S2?", "options": ["A", "B", "C"], "correct_index": -1},
    ]
    result, _ = validate_questions(questions)
    assert len(result) == 0


def test_validate_mixed_valid_invalid():
    questions = [
        {"question": "Valid?", "options": ["A", "B", "C"], "correct_index": 0},
        {"question": "", "options": ["A", "B"], "correct_index": 0},
        {"question": "Valid2?", "options": ["X", "Y"], "correct_index": 1},
        {"question": "No options", "options": [], "correct_index": 0},
    ]
    result, stats = validate_questions(questions)
    assert len(result) == 2
    assert result[0]["question"] == "Valid?"
    assert result[1]["question"] == "Valid2?"
    assert stats["skipped_no_options"] == 1


def test_validate_non_list_input():
    result, _ = validate_questions(None)
    assert result == []
    result, _ = validate_questions("not a list")
    assert result == []
    result, _ = validate_questions(42)
    assert result == []


def test_validate_non_dict_item():
    questions = [
        "not a dict",
        {"question": "OK?", "options": ["A", "B"], "correct_index": 0},
    ]
    result, _ = validate_questions(questions)
    assert len(result) == 1

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ai.validator import validate_questions


def test_valid_question():
    questions = [{
        "question": "O'zbekiston qachon mustaqil bo'lgan?",
        "options": ["1990", "1991", "1992", "1993"],
        "correct_index": 1,
        "explanation": "1991-yil",
    }]
    result, stats = validate_questions(questions)
    assert len(result) == 1
    assert result[0]["correct_index"] == 1
    assert stats["few_options"] == 0
    assert stats["many_options"] == 0


def test_missing_question_text():
    questions = [{"question": "", "options": ["A", "B"], "correct_index": 0}]
    result, _ = validate_questions(questions)
    assert len(result) == 0


def test_insufficient_options():
    questions = [{"question": "Savol?", "options": ["A"], "correct_index": 0}]
    result, stats = validate_questions(questions)
    assert len(result) == 0
    assert stats["skipped_no_options"] == 1


def test_invalid_correct_index():
    questions = [{"question": "Savol?", "options": ["A", "B"], "correct_index": 5}]
    result, _ = validate_questions(questions)
    assert len(result) == 0


def test_duplicate_questions():
    questions = [
        {"question": "Savol bir?", "options": ["A", "B"], "correct_index": 0},
        {"question": "Savol bir?", "options": ["A", "B"], "correct_index": 1},
    ]
    result, stats = validate_questions(questions)
    assert len(result) == 1
    assert stats["duplicates"] == 1


def test_few_options_warning():
    questions = [{"question": "Savol?", "options": ["A", "B"], "correct_index": 0}]
    result, stats = validate_questions(questions)
    assert len(result) == 1
    assert stats["few_options"] == 1
    assert stats["many_options"] == 0


def test_many_options_warning():
    questions = [{"question": "Savol?", "options": ["A", "B", "C", "D", "E"], "correct_index": 0}]
    result, stats = validate_questions(questions)
    assert len(result) == 1
    assert stats["many_options"] == 1
    assert stats["few_options"] == 0


def test_empty_input():
    result, stats = validate_questions([])
    assert result == []
    assert stats == {"skipped_no_options": 0, "few_options": 0, "many_options": 0, "duplicates": 0}

    result, stats = validate_questions(None)
    assert result == []

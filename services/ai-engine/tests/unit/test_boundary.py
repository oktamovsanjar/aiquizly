import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from boundary.splitter import detect_boundaries


def test_boundary_detects_numbered_questions():
    text = "1. Savol bir\nA) variant\nB) variant\n2. Savol ikki\nA) variant"
    blocks = detect_boundaries(text)
    assert len(blocks) == 2
    assert blocks[0].question == "Savol bir"
    assert len(blocks[0].options) == 2


def test_boundary_handles_empty_text():
    blocks = detect_boundaries("")
    assert blocks == []


def test_boundary_detects_options():
    text = "1. O'zbekiston poytaxti qaysi shahar?\nA) Samarqand\nB) Toshkent\nC) Buxoro\nD) Namangan"
    blocks = detect_boundaries(text)
    assert len(blocks) == 1
    assert len(blocks[0].options) == 4
    assert blocks[0].options[1] == "Toshkent"


def test_boundary_multiple_questions():
    text = "\n".join([
        f"{i}. Savol {i}\nA) variant1\nB) variant2" for i in range(1, 6)
    ])
    blocks = detect_boundaries(text)
    assert len(blocks) == 5

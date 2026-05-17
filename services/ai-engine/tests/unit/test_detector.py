import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from parsers.detector import detect_format


def test_detect_docx():
    assert detect_format("test.docx") == "word"


def test_detect_pdf():
    assert detect_format("test.pdf") == "pdf"


def test_detect_xlsx():
    assert detect_format("test.xlsx") == "excel"


def test_detect_txt():
    assert detect_format("test.txt") == "text"


def test_detect_image():
    assert detect_format("screenshot.png") == "image"
    assert detect_format("photo.jpg") == "image"


def test_unsupported_format():
    with pytest.raises(ValueError):
        detect_format("document.zip")


def test_uppercase_extension():
    assert detect_format("test.PDF") == "pdf"
    assert detect_format("test.DOCX") == "word"

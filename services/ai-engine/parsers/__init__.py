from .detector import detect_format
from .word_parser import parse_word
from .pdf_parser import parse_pdf
from .excel_parser import parse_excel
from .text_parser import parse_text

__all__ = ["detect_format", "parse_word", "parse_pdf", "parse_excel", "parse_text"]

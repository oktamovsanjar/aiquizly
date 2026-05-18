"""Stage 2: Text (.txt) parser"""

import chardet


def parse_text(file_content: bytes) -> str:
    """
    .txt fayldan matn chiqaradi.
    Encoding avtomatik aniqlanadi.
    """
    detected = chardet.detect(file_content)
    encoding = detected.get("encoding") or "utf-8"
    try:
        return file_content.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return file_content.decode("utf-8", errors="replace")

"""Stage 1: Format Detector — faylni turini aniqlaydi"""

SUPPORTED_FORMATS = {
    ".docx": "word",
    ".pdf": "pdf",
    ".xlsx": "excel",
    ".txt": "text",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}


def detect_format(filename: str) -> str:
    """
    Fayl nomidan formatini aniqlaydi.
    Qaytaradi: 'word' | 'pdf' | 'excel' | 'text' | 'image'
    Ko'taradigan xato: ValueError — agar format qo'llab-quvvatlanmasa
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    fmt = SUPPORTED_FORMATS.get(ext)
    if not fmt:
        raise ValueError(f"Qo'llab-quvvatlanmaydigan format: {ext}")
    return fmt

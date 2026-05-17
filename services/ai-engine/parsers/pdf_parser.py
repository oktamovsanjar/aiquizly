"""Stage 2: PDF parser — PyMuPDF (fitz)"""
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# A page is considered "scanned" (image-only) when it has fewer than this
# many meaningful characters of text.
_SCANNED_PAGE_CHAR_THRESHOLD = 50
# A whole PDF is considered scanned when more than this fraction of pages
# have little or no text.
_SCANNED_PDF_PAGE_RATIO = 0.6


def parse_pdf(file_content: bytes) -> str:
    """
    Extracts text from a PDF file page by page using PyMuPDF.

    Scanned pages (little text) are flagged in the output with a marker
    so the caller can route them through the Vision pipeline.
    Returns the combined text of all text-bearing pages.
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_content, filetype="pdf")
        pages_text: List[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Extract text with layout preservation
            text = page.get_text("text")  # type: ignore[arg-type]
            stripped = text.strip()

            if len(stripped) < _SCANNED_PAGE_CHAR_THRESHOLD:
                # Page is likely scanned — mark it so callers can detect it
                logger.debug(
                    "Page %d appears scanned (text length=%d)", page_num + 1, len(stripped)
                )
                pages_text.append(f"[SCANNED_PAGE:{page_num + 1}]")
            else:
                pages_text.append(text)

        doc.close()
        return "\n\n".join(pages_text)

    except Exception as exc:
        raise RuntimeError(f"PDF fayl o'qilmadi: {exc}") from exc


def is_scanned_pdf(file_content: bytes) -> bool:
    """
    Returns True when the PDF is primarily scanned (image-based) and needs
    the Vision API pipeline instead of the text extraction pipeline.

    Heuristic: if more than 60 % of pages have fewer than 50 characters
    of text, the document is treated as scanned.
    """
    try:
        import fitz

        doc = fitz.open(stream=file_content, filetype="pdf")
        total_pages = len(doc)

        if total_pages == 0:
            doc.close()
            return False

        scanned_pages = 0
        for page in doc:
            text = page.get_text("text")  # type: ignore[arg-type]
            if len(text.strip()) < _SCANNED_PAGE_CHAR_THRESHOLD:
                scanned_pages += 1

        doc.close()
        ratio = scanned_pages / total_pages
        return ratio >= _SCANNED_PDF_PAGE_RATIO

    except Exception:
        # If we cannot open the PDF at all, assume it needs Vision
        return True


def extract_pdf_page_images(file_content: bytes) -> List[bytes]:
    """
    Renders each PDF page to a PNG image (for scanned PDFs).
    Returns a list of PNG bytes, one per page.
    Used to feed scanned pages into the Vision pipeline.
    """
    try:
        import fitz

        doc = fitz.open(stream=file_content, filetype="pdf")
        images: List[bytes] = []

        for page in doc:
            # 2× zoom for better OCR quality
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)  # type: ignore[attr-defined]
            images.append(pix.tobytes("png"))

        doc.close()
        return images

    except Exception as exc:
        raise RuntimeError(f"PDF sahifalarni rasmga aylantirish xatosi: {exc}") from exc

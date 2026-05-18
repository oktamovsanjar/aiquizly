"""Stage 2: Image (.png/.jpg) parser — GPT-4o Vision API"""
import asyncio
import base64
import io
import logging
from typing import List

logger = logging.getLogger(__name__)

# Horizontal split threshold: images taller than this pixel count will be split
_SPLIT_HEIGHT_THRESHOLD = 3000
# Overlap fraction (20 %) for split segments
_OVERLAP = 0.20

VISION_PROMPT = (
    "Bu rasmda test savollari bor. Ularni quyidagi matn formatida yoz:\n"
    "1. [savol matni]\n"
    "A) [variant]\n"
    "B) [variant]\n"
    "C) [variant]\n"
    "D) [variant]\n"
    "Javob: [to'g'ri variant harfi]\n\n"
    "Faqat savollarni yoz, boshqa hech narsa qo'shma. "
    "Agar rasm bo'sh yoki savol yo'q bo'lsa, bo'sh javob qaytarsan."
)


def _encode_bytes(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def _split_image_vertically(image_bytes: bytes) -> List[bytes]:
    """
    Splits a tall image into horizontal slices with 20% overlap.
    Uses Pillow (PIL). Falls back to returning the original if Pillow is missing.
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size

        if height <= _SPLIT_HEIGHT_THRESHOLD:
            return [image_bytes]

        # Determine slice height so each slice is ~_SPLIT_HEIGHT_THRESHOLD px
        slice_h = _SPLIT_HEIGHT_THRESHOLD
        overlap_px = int(slice_h * _OVERLAP)
        step = slice_h - overlap_px

        slices: List[bytes] = []
        top = 0
        while top < height:
            bottom = min(top + slice_h, height)
            cropped = img.crop((0, top, width, bottom))
            buf = io.BytesIO()
            fmt = img.format or "PNG"
            cropped.save(buf, format=fmt)
            slices.append(buf.getvalue())
            if bottom >= height:
                break
            top += step

        return slices

    except ImportError:
        logger.warning("Pillow not installed — skipping image split")
        return [image_bytes]
    except Exception as exc:
        logger.warning("Image split failed: %s — using original", exc)
        return [image_bytes]


async def parse_image(file_content: bytes, openai_client) -> str:
    """
    Sends a single image to GPT-4o Vision and returns extracted quiz text.
    If the image is very tall, it is split horizontally with 20% overlap.
    """
    segments = _split_image_vertically(file_content)

    if len(segments) == 1:
        return await _call_vision(segments[0], openai_client)

    # Multiple segments — process in parallel and combine
    tasks = [_call_vision(seg, openai_client) for seg in segments]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    parts: List[str] = []
    for r in results:
        if isinstance(r, Exception):
            logger.error("Vision segment error: %s", r)
            continue
        if r.strip():
            parts.append(r.strip())

    return "\n\n".join(parts)


async def _call_vision(image_bytes: bytes, openai_client) -> str:
    """Makes a single GPT-4o vision API call and returns the raw text response."""
    b64 = _encode_bytes(image_bytes)
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.error("Vision API call failed: %s", exc)
        raise


async def parse_images_batch(images: List[bytes], openai_client, max_concurrent: int = 3) -> str:
    """
    Processes multiple images in parallel (max_concurrent bir vaqtda).
    Each image triggers one API call; results are combined in order.
    """
    if not images:
        return ""

    sem = asyncio.Semaphore(max_concurrent)

    async def _bounded(img: bytes) -> str:
        async with sem:
            return await parse_image(img, openai_client)

    tasks = [_bounded(img) for img in images]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    parts: List[str] = []
    for idx, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error("Image %d processing failed: %s", idx, r)
            continue
        if r.strip():
            parts.append(r.strip())

    return "\n\n".join(parts)

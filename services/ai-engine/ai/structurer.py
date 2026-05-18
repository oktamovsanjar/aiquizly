"""Stage 4: AI Structuring — savollarni batch qilib AI ga yuboradi"""

import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Tuple

from openai import AsyncOpenAI

from .prompts import STRUCTURE_PROMPT
from .validator import validate_questions
from config import settings

logger = logging.getLogger(__name__)


def _merge_stats(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


def _repair_truncated_json(raw: str) -> List[Dict[str, Any]]:
    """
    Truncated JSON dan to'liq savollarni regex orqali tiklash.
    DeepSeek javobni kesib tashlaganda bu funksiya ishlatiladi.
    """
    pattern = re.compile(
        r'\{\s*"question_text"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,'
        r'\s*"options"\s*:\s*\[((?:[^\[\]]|\[(?:[^\[\]])*\])*)\]\s*,'
        r'\s*"correct_indices"\s*:\s*\[(\d+)\]',
        re.DOTALL,
    )
    results = []
    for m in pattern.finditer(raw):
        try:
            q_text = m.group(1).replace('\\"', '"')
            opts_raw = "[" + m.group(2) + "]"
            options = json.loads(opts_raw)
            correct = int(m.group(3))
            if isinstance(options, list) and len(options) >= 2:
                results.append(
                    {
                        "question_text": q_text,
                        "options": options,
                        "correct_indices": [correct],
                    }
                )
        except Exception:
            continue
    return results


class AIStructurer:
    def __init__(self) -> None:
        if settings.ai_provider == "deepseek" and settings.deepseek_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
            )
        else:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def structure_blocks(
        self, blocks: List[Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        if not blocks:
            return [], {}

        batch_size = settings.ai_batch_size
        batches = [
            blocks[i : i + batch_size] for i in range(0, len(blocks), batch_size)
        ]
        total = len(batches)
        logger.info("Jami %d batch, max %d parallel", total, settings.ai_max_concurrent)

        sem = asyncio.Semaphore(settings.ai_max_concurrent)

        async def _bounded(
            batch: List[Any], idx: int
        ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
            async with sem:
                logger.debug("Batch %d/%d boshlandi", idx + 1, total)
                result = await self._process_batch(batch, idx)
                logger.debug("Batch %d/%d tugadi", idx + 1, total)
                return result

        tasks = [_bounded(batch, i) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_questions: List[Dict[str, Any]] = []
        combined_stats: Dict[str, int] = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error("Batch xatosi: %s", result)
                continue
            questions, stats = result
            all_questions.extend(questions)
            combined_stats = _merge_stats(combined_stats, stats)

        logger.info("Jami %d savol chiqarildi", len(all_questions))
        return all_questions, combined_stats

    async def _process_batch(
        self, blocks: List[Any], batch_idx: int
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        questions_text = "\n\n".join(
            f"{i + 1}. {b.raw_text}" for i, b in enumerate(blocks)
        )
        prompt = STRUCTURE_PROMPT.format(questions_text=questions_text)

        for attempt in range(settings.ai_max_retries):
            try:
                model = (
                    settings.ai_model_primary
                    if attempt == 0
                    else settings.ai_model_fallback
                )
                supports_json_format = "gpt-4" in model or "deepseek" in model
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=8000,  # truncation oldini olish
                    response_format=(
                        {"type": "json_object"} if supports_json_format else None
                    ),
                )
                raw = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                if finish_reason == "length":
                    logger.warning(
                        "Batch %d truncated (finish_reason=length), regex fallback",
                        batch_idx,
                    )

                questions = self._parse_response(raw)
                validated, stats = validate_questions(questions)
                if validated:
                    return validated, stats

            except Exception as e:
                logger.warning(
                    "Batch %d, urinish %d xatosi: %s", batch_idx, attempt + 1, e
                )
                if attempt < settings.ai_max_retries - 1:
                    await asyncio.sleep(2**attempt)

        logger.error(
            "Batch %d barcha urinishlardan keyin ham muvaffaqiyatsiz", batch_idx
        )
        return [], {}

    def _parse_response(self, raw: str) -> List[Dict[str, Any]]:
        raw = raw.strip()
        try:
            if raw.startswith("{"):
                data = json.loads(raw)
                for val in data.values():
                    if isinstance(val, list):
                        return val
                return []
            return json.loads(raw)
        except json.JSONDecodeError:
            # Truncated JSON — regex bilan tiklash
            logger.warning("JSON parse xatosi, regex fallback ishlatilmoqda")
            repaired = _repair_truncated_json(raw)
            if repaired:
                logger.info("Regex fallback: %d savol tiklandi", len(repaired))
            return repaired

"""Stage 4: AI Structuring — savollarni batch qilib AI ga yuboradi"""
import asyncio
import json
import logging
from typing import List, Dict, Any

from openai import AsyncOpenAI

from .prompts import STRUCTURE_PROMPT
from .validator import validate_questions
from boundary.splitter import QuestionBlock
from config import settings

logger = logging.getLogger(__name__)


class AIStructurer:
    def __init__(self) -> None:
        if settings.ai_provider == "deepseek" and settings.deepseek_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
            )
        else:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def structure_blocks(self, blocks: List[QuestionBlock]) -> List[Dict[str, Any]]:
        """
        Savollarni batch qilib AI ga yuboradi va strukturalangan ro'yxat qaytaradi.
        Parallel batch processing: 10x tezroq.
        """
        batch_size = settings.ai_batch_size
        batches = [blocks[i:i + batch_size] for i in range(0, len(blocks), batch_size)]

        tasks = [self._process_batch(batch, batch_idx) for batch_idx, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_questions = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Batch xatosi: %s", result)
                continue
            all_questions.extend(result)

        return all_questions

    async def _process_batch(self, blocks: List[QuestionBlock], batch_idx: int) -> List[Dict[str, Any]]:
        """Bitta batchni AI ga yuboradi, retry bilan"""
        questions_text = "\n\n".join(
            f"{i + 1}. {b.raw_text}" for i, b in enumerate(blocks)
        )
        prompt = STRUCTURE_PROMPT.format(questions_text=questions_text)

        for attempt in range(settings.ai_max_retries):
            try:
                model = settings.ai_model_primary if attempt == 0 else settings.ai_model_fallback
                # DeepSeek va ba'zi modellar json_object formatini qo'llab-quvvatlaydi
                supports_json_format = "gpt-4" in model or "deepseek" in model
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    response_format={"type": "json_object"} if supports_json_format else None,
                )
                raw = response.choices[0].message.content
                questions = self._parse_response(raw)
                validated = validate_questions(questions)
                if validated:
                    return validated

            except Exception as e:
                logger.warning("Batch %d, urinish %d xatosi: %s", batch_idx, attempt + 1, e)
                if attempt < settings.ai_max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        logger.error("Batch %d barcha urinishlardan keyin ham muvaffaqiyatsiz", batch_idx)
        return []

    def _parse_response(self, raw: str) -> List[Dict[str, Any]]:
        """AI javobidan JSON parserlaydi"""
        raw = raw.strip()
        # JSON array yoki object ichidagi array ni topish
        if raw.startswith("{"):
            data = json.loads(raw)
            # {"questions": [...]} yoki birinchi list qiymatni topish
            for val in data.values():
                if isinstance(val, list):
                    return val
            return []
        return json.loads(raw)

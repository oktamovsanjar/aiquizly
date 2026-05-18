"""
HTTP clients for internal microservices.

All clients use a single shared httpx.AsyncClient per service (connection pool).
URLs are read from environment variables.

Clients:
  GameClient         → game service (Go)
  AIEngineClient     → ai-engine service (Python / FastAPI)
  SubscriptionClient → subscription service (Python / FastAPI)
  NotifierClient     → notifier service (Go)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ──────────────────────────── Simple TTL cache ────────────────────────────
# Bot o'zi Redis ni FSM uchun ishlatadi, lekin API javoblari uchun
# oddiy in-process cache yetarli (har process uchun, restart da tozalanadi)

_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()


async def _cached(key: str, ttl: float, coro) -> Any:
    """TTL cache wrapper. ttl — sekund."""
    now = time.monotonic()
    async with _cache_lock:
        if key in _cache:
            exp, val = _cache[key]
            if now < exp:
                return val
    result = await coro
    async with _cache_lock:
        _cache[key] = (now + ttl, result)
    return result


def _cache_invalidate(prefix: str) -> None:
    """Berilgan prefix bilan boshlangan barcha kalit larni o'chiradi."""
    for k in list(_cache):
        if k.startswith(prefix):
            del _cache[k]


GAME_SERVICE_URL: str = os.environ.get("GAME_SERVICE_URL", "http://game:8081")
AI_ENGINE_URL: str = os.environ.get("AI_ENGINE_URL", "http://ai-engine:8002")
SUBSCRIPTION_URL: str = os.environ.get("SUBSCRIPTION_URL", "http://subscription:8003")
NOTIFIER_URL: str = os.environ.get("NOTIFIER_URL", "http://notifier:8082")

DEFAULT_TIMEOUT = 30.0

# Shared connection pool settings — ulanishlarni qayta ishlatish
_POOL_LIMITS = httpx.Limits(
    max_connections=50,
    max_keepalive_connections=20,
    keepalive_expiry=30,
)


# ──────────────────────────── Base ────────────────────────────


class ServiceError(Exception):
    """Raised when a downstream service returns an unexpected response."""

    def __init__(self, service: str, status: int, body: str) -> None:
        self.service = service
        self.status = status
        self.body = body
        super().__init__(f"{service} returned {status}: {body[:200]}")


def _raise_for_service(service: str, resp: httpx.Response) -> None:
    if resp.is_error:
        raise ServiceError(service, resp.status_code, resp.text)


# ──────────────────────────── Game Client ────────────────────────────


class GameClient:
    """Wraps the Go game service REST API."""

    def __init__(self, base_url: str = GAME_SERVICE_URL) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=DEFAULT_TIMEOUT,
            limits=_POOL_LIMITS,
        )

    async def start_game(
        self,
        user_id: int,
        quiz_id: str,
        set_number: int,
        time_per_question: int = 30,
        chat_id: int | None = None,
    ) -> dict[str, Any]:
        resp = await self._http.post(
            "/games",
            json={
                "user_id": user_id,
                "quiz_id": quiz_id,
                "set_number": set_number,
                "time_per_question": time_per_question,
                "chat_id": chat_id,
            },
        )
        _raise_for_service("game", resp)
        return resp.json()

    async def submit_answer(
        self,
        game_id: str,
        question_index: int,
        chosen_option: int | None,
        time_taken_ms: int,
    ) -> dict[str, Any]:
        resp = await self._http.put(
            f"/games/{game_id}/answer",
            json={
                "question_index": question_index,
                "chosen_option": chosen_option,
                "time_taken_ms": time_taken_ms,
            },
        )
        _raise_for_service("game", resp)
        return resp.json()

    async def finish_game(
        self,
        game_id: str,
        status: str = "completed",
    ) -> dict[str, Any]:
        resp = await self._http.put(
            f"/games/{game_id}/finish",
            json={"status": status},
        )
        # 409 = allaqachon tugagan — XP yo'qolmasin, bo'sh dict qaytaramiz
        if resp.status_code == 409:
            logger.debug("finish_game 409 — game %s already finished", game_id)
            return {}
        _raise_for_service("game", resp)
        result = resp.json()
        # XP berilgani uchun stats/rank/lb cache ni tozalaymiz
        _cache_invalidate("lb:")
        return result

    async def get_leaderboard(
        self,
        period: str = "all",
        tag: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if tag:
            params["tag"] = tag

        async def _fetch():
            resp = await self._http.get(f"/leaderboard/{period}", params=params)
            _raise_for_service("game", resp)
            return resp.json()

        return await _cached(f"lb:{period}:{tag}:{limit}", ttl=30, coro=_fetch())

    async def get_user_rank(self, user_id: int, period: str = "all") -> dict[str, Any]:
        async def _fetch():
            resp = await self._http.get(
                f"/users/{user_id}/rank", params={"period": period}
            )
            _raise_for_service("game", resp)
            return resp.json()

        return await _cached(f"rank:{user_id}:{period}", ttl=30, coro=_fetch())

    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        async def _fetch():
            resp = await self._http.get(f"/users/{user_id}/stats")
            _raise_for_service("game", resp)
            return resp.json()

        return await _cached(f"stats:{user_id}", ttl=20, coro=_fetch())

    async def award_xp(self, user_id: int, xp: int, reason: str) -> dict[str, Any]:
        resp = await self._http.post(
            f"/users/{user_id}/xp",
            json={"xp": xp, "reason": reason},
        )
        _raise_for_service("game", resp)
        _cache_invalidate(f"stats:{user_id}")
        _cache_invalidate(f"rank:{user_id}")
        _cache_invalidate("lb:")
        return resp.json()

    async def get_group_leaderboard(
        self, chat_id: int, game_session_id: str
    ) -> dict[str, Any]:
        resp = await self._http.get(f"/groups/{chat_id}/leaderboard/{game_session_id}")
        _raise_for_service("game", resp)
        return resp.json()


# ──────────────────────────── AI Engine Client ────────────────────────────


class AIEngineClient:
    """Wraps the Python ai-engine FastAPI service."""

    def __init__(self, base_url: str = AI_ENGINE_URL) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=DEFAULT_TIMEOUT,
            limits=_POOL_LIMITS,
        )

    async def process_file(
        self,
        file_url: str,
        file_name: str,
        file_size: int,
        user_id: int,
        mime_type: str = "",
        force: bool = False,
    ) -> dict[str, Any]:
        resp = await self._http.post(
            "/process",
            json={
                "file_url": file_url,
                "file_name": file_name,
                "file_size": file_size,
                "user_id": str(user_id),
                "mime_type": mime_type,
                "force": force,
            },
        )
        _raise_for_service("ai-engine", resp)
        return resp.json()

    async def process_images(
        self,
        file_ids: list[str],
        user_id: int,
        bot_token: str,
    ) -> dict[str, Any]:
        resp = await self._http.post(
            "/tasks/images",
            json={"file_ids": file_ids, "user_id": user_id, "bot_token": bot_token},
        )
        _raise_for_service("ai-engine", resp)
        return resp.json()

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        resp = await self._http.get(f"/tasks/{task_id}")
        _raise_for_service("ai-engine", resp)
        return resp.json()

    async def get_quizzes(
        self,
        user_id: int | None = None,
        tag: str | None = None,
        search: str | None = None,
        public: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """
        GET /quizzes
        Returns {"quizzes": [...]}
        ai-engine params: user_id, tag, q (search), visibility, limit, offset
        """
        params: dict[str, Any] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if user_id is not None:
            params["user_id"] = user_id
        if tag:
            params["tag"] = tag
        if search:
            params["q"] = search
        if public is not None:
            params["visibility"] = "public" if public else "private"

        # Search yoki tag bo'lsa — cache yo'q (har xil natija)
        if search or tag:
            resp = await self._http.get("/quizzes", params=params)
            _raise_for_service("ai-engine", resp)
            return resp.json()

        cache_key = f"quizzes:u{user_id}:p{public}:pg{page}"
        ttl = 15.0 if user_id else 30.0  # o'z quizlari tezroq eskiradi

        async def _fetch():
            resp = await self._http.get("/quizzes", params=params)
            _raise_for_service("ai-engine", resp)
            return resp.json()

        return await _cached(cache_key, ttl=ttl, coro=_fetch())

    async def get_quiz(self, quiz_id: str) -> dict[str, Any]:
        async def _fetch():
            resp = await self._http.get(f"/quizzes/{quiz_id}")
            _raise_for_service("ai-engine", resp)
            return resp.json()

        return await _cached(f"quiz:{quiz_id}", ttl=30, coro=_fetch())

    async def get_questions(
        self,
        quiz_id: str,
        set_number: int,
    ) -> list[dict[str, Any]]:
        async def _fetch():
            resp = await self._http.get(
                f"/quizzes/{quiz_id}/sets/{set_number}/questions"
            )
            _raise_for_service("ai-engine", resp)
            data = resp.json()
            return data if isinstance(data, list) else data.get("questions", [])

        return await _cached(f"qset:{quiz_id}:{set_number}", ttl=60, coro=_fetch())

    async def save_quiz(
        self,
        task_id: str,
        name: str,
        tags: list[str],
        is_public: bool,
        quiz_group_id: int | None,
        user_id: int,
    ) -> dict[str, Any]:
        resp = await self._http.post(
            "/quizzes",
            json={
                "task_id": task_id,
                "name": name,
                "tags": tags,
                "is_public": is_public,
                "quiz_group_id": quiz_group_id,
                "user_id": user_id,
            },
        )
        _raise_for_service("ai-engine", resp)
        _cache_invalidate("quizzes:")
        return resp.json()

    async def get_trending_tags(self, limit: int = 9) -> list[str]:
        resp = await self._http.get("/tags/trending", params={"limit": limit})
        _raise_for_service("ai-engine", resp)
        data = resp.json()
        return data if isinstance(data, list) else data.get("tags", [])

    async def count_questions(self, quiz_id: str) -> int:
        resp = await self._http.get(f"/quizzes/{quiz_id}/questions/count")
        _raise_for_service("ai-engine", resp)
        return resp.json().get("total", 0)

    async def update_question(
        self,
        quiz_id: str,
        question_id: str,
        question_text: str | None = None,
        options: list[str] | None = None,
        correct_indices: list[int] | None = None,
        explanation: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if question_text is not None:
            body["question_text"] = question_text
        if options is not None:
            body["options"] = options
        if correct_indices is not None:
            body["correct_indices"] = correct_indices
        if explanation is not None:
            body["explanation"] = explanation
        resp = await self._http.patch(
            f"/quizzes/{quiz_id}/questions/{question_id}", json=body
        )
        _raise_for_service("ai-engine", resp)
        return resp.json()

    async def delete_question(self, quiz_id: str, question_id: str) -> dict[str, Any]:
        resp = await self._http.delete(f"/quizzes/{quiz_id}/questions/{question_id}")
        _raise_for_service("ai-engine", resp)
        return resp.json()

    async def update_quiz(
        self,
        quiz_id: str,
        title: str | None = None,
        is_public: bool | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if is_public is not None:
            body["visibility"] = "public" if is_public else "private"
        resp = await self._http.patch(f"/quizzes/{quiz_id}", json=body)
        _raise_for_service("ai-engine", resp)
        _cache_invalidate(f"quiz:{quiz_id}")
        return resp.json()

    async def update_quiz_visibility(
        self, quiz_id: str, is_public: bool
    ) -> dict[str, Any]:
        return await self.update_quiz(quiz_id, is_public=is_public)

    async def delete_quiz(self, quiz_id: str) -> dict[str, Any]:
        resp = await self._http.delete(f"/quizzes/{quiz_id}")
        _raise_for_service("ai-engine", resp)
        _cache_invalidate(f"quiz:{quiz_id}")
        _cache_invalidate("quizzes:")
        return resp.json()


# ──────────────────────────── Subscription Client ────────────────────────────


class SubscriptionClient:
    """Wraps the subscription service REST API."""

    def __init__(self, base_url: str = SUBSCRIPTION_URL) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=5.0,
            limits=_POOL_LIMITS,
        )

    async def check_limit(self, user_id: int, action: str = "file_upload") -> bool:
        try:
            resp = await self._http.get(
                "/limits/check",
                params={"telegram_id": user_id, "action": action},
            )
            if resp.is_error:
                return True
            return resp.json().get("allowed", True)
        except httpx.HTTPError as exc:
            logger.warning("subscription check_limit failed: %s", exc)
            return True

    async def increment_usage(self, user_id: int, action: str = "file_upload") -> None:
        try:
            await self._http.post(
                "/limits/increment",
                json={"telegram_id": user_id, "action": action},
            )
        except httpx.HTTPError as exc:
            logger.warning("subscription increment_usage failed: %s", exc)

    async def get_plan(self, user_id: int) -> dict[str, Any]:
        try:
            resp = await self._http.get(f"/users/{user_id}/plan")
            if resp.is_error:
                return {"plan": "free"}
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("subscription get_plan failed: %s", exc)
            return {"plan": "free"}

    async def activate_premium(
        self, user_id: int, days: int, source: str = "stars"
    ) -> dict[str, Any]:
        resp = await self._http.post(
            f"/users/{user_id}/premium",
            json={"days": days, "source": source},
            timeout=DEFAULT_TIMEOUT,
        )
        _raise_for_service("subscription", resp)
        return resp.json()


# ──────────────────────────── Notifier Client ────────────────────────────


class NotifierClient:
    """Wraps the Go notifier service REST API."""

    def __init__(self, base_url: str = NOTIFIER_URL) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=10.0,
            limits=_POOL_LIMITS,
        )

    async def send_notification(
        self,
        user_id: int,
        text: str,
        inline_keyboard: list[list[dict[str, str]]] | None = None,
    ) -> None:
        try:
            await self._http.post(
                "/notify",
                json={
                    "user_id": user_id,
                    "text": text,
                    "inline_keyboard": inline_keyboard or [],
                },
            )
        except httpx.HTTPError as exc:
            logger.warning("notifier send_notification failed: %s", exc)

    async def broadcast(
        self,
        user_ids: list[int],
        text: str,
        inline_keyboard: list[list[dict[str, str]]] | None = None,
    ) -> None:
        try:
            await self._http.post(
                "/broadcast",
                json={
                    "user_ids": user_ids,
                    "text": text,
                    "inline_keyboard": inline_keyboard or [],
                },
                timeout=60.0,
            )
        except httpx.HTTPError as exc:
            logger.warning("notifier broadcast failed: %s", exc)


# ──────────────────────────── Singleton accessors ────────────────────────────

_game_client: GameClient | None = None
_ai_client: AIEngineClient | None = None
_sub_client: SubscriptionClient | None = None
_notifier_client: NotifierClient | None = None


def game_client() -> GameClient:
    global _game_client
    if _game_client is None:
        _game_client = GameClient()
    return _game_client


def ai_engine_client() -> AIEngineClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = AIEngineClient()
    return _ai_client


def subscription_client() -> SubscriptionClient:
    global _sub_client
    if _sub_client is None:
        _sub_client = SubscriptionClient()
    return _sub_client


def notifier_client() -> NotifierClient:
    global _notifier_client
    if _notifier_client is None:
        _notifier_client = NotifierClient()
    return _notifier_client

"""
HTTP clients for internal microservices.

All clients use httpx.AsyncClient.  They read service URLs from environment
variables so no URL is ever hardcoded.

Clients:
  GameClient         → game service (Go)
  AIEngineClient     → ai-engine service (Python / FastAPI)
  SubscriptionClient → subscription service (Python / FastAPI)
  NotifierClient     → notifier service (Go)
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GAME_SERVICE_URL: str = os.environ.get("GAME_SERVICE_URL", "http://game:8001")
AI_ENGINE_URL: str = os.environ.get("AI_ENGINE_URL", "http://ai-engine:8002")
SUBSCRIPTION_URL: str = os.environ.get("SUBSCRIPTION_URL", "http://subscription:8003")
NOTIFIER_URL: str = os.environ.get("NOTIFIER_URL", "http://notifier:8004")

DEFAULT_TIMEOUT = 30.0


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
        self._base = base_url.rstrip("/")

    async def start_game(
        self,
        user_id: int,
        quiz_id: str,
        set_number: int,
        time_per_question: int = 30,
        chat_id: int | None = None,
    ) -> dict[str, Any]:
        """
        POST /games
        Returns game record with game_id.
        """
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base}/games",
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
        """
        POST /games/{game_id}/answers
        Returns updated score info.
        """
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base}/games/{game_id}/answers",
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
        """
        PATCH /games/{game_id}
        status: "completed" | "saved" | "stopped"
        Returns final result with XP awarded.
        """
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.patch(
                f"{self._base}/games/{game_id}",
                json={"status": status},
            )
            _raise_for_service("game", resp)
            return resp.json()

    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        """GET /users/{user_id}/stats"""
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(f"{self._base}/users/{user_id}/stats")
            _raise_for_service("game", resp)
            return resp.json()

    async def get_leaderboard(
        self,
        period: str = "all",
        tag: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        GET /leaderboard
        period: "today" | "week" | "month" | "all"
        """
        params: dict[str, Any] = {"period": period, "limit": limit}
        if tag:
            params["tag"] = tag
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(f"{self._base}/leaderboard", params=params)
            _raise_for_service("game", resp)
            return resp.json()

    async def get_user_rank(self, user_id: int, period: str = "all") -> dict[str, Any]:
        """GET /users/{user_id}/rank"""
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                f"{self._base}/users/{user_id}/rank", params={"period": period}
            )
            _raise_for_service("game", resp)
            return resp.json()

    async def award_xp(self, user_id: int, xp: int, reason: str) -> dict[str, Any]:
        """POST /users/{user_id}/xp"""
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base}/users/{user_id}/xp",
                json={"xp": xp, "reason": reason},
            )
            _raise_for_service("game", resp)
            return resp.json()

    async def get_group_leaderboard(self, chat_id: int, game_session_id: str) -> dict[str, Any]:
        """GET /groups/{chat_id}/leaderboard/{game_session_id}"""
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                f"{self._base}/groups/{chat_id}/leaderboard/{game_session_id}"
            )
            _raise_for_service("game", resp)
            return resp.json()


# ──────────────────────────── AI Engine Client ────────────────────────────


class AIEngineClient:
    """Wraps the Python ai-engine FastAPI service."""

    def __init__(self, base_url: str = AI_ENGINE_URL) -> None:
        self._base = base_url.rstrip("/")

    async def process_file(
        self,
        file_url: str,
        file_name: str,
        file_size: int,
        user_id: int,
        mime_type: str = "",
    ) -> dict[str, Any]:
        """
        POST /tasks
        Enqueues an AI processing task.
        Returns {"task_id": "...", "status": "queued"}
        """
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base}/tasks",
                json={
                    "file_url": file_url,
                    "file_name": file_name,
                    "file_size": file_size,
                    "user_id": user_id,
                    "mime_type": mime_type,
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
        """
        POST /tasks/images
        Returns {"task_id": "...", "status": "queued"}
        """
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base}/tasks/images",
                json={"file_ids": file_ids, "user_id": user_id, "bot_token": bot_token},
            )
            _raise_for_service("ai-engine", resp)
            return resp.json()

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        GET /tasks/{task_id}
        Returns {"status": "queued|processing|done|failed", ...result fields...}
        """
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(f"{self._base}/tasks/{task_id}")
            _raise_for_service("ai-engine", resp)
            return resp.json()

    async def get_quizzes(
        self,
        user_id: int | None = None,
        tag: str | None = None,
        search: str | None = None,
        public: bool | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """
        GET /quizzes
        Returns {"items": [...], "total": int, "page": int}
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if user_id is not None:
            params["user_id"] = user_id
        if tag:
            params["tag"] = tag
        if search:
            params["search"] = search
        if public is not None:
            params["public"] = public
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(f"{self._base}/quizzes", params=params)
            _raise_for_service("ai-engine", resp)
            return resp.json()

    async def get_quiz(self, quiz_id: str) -> dict[str, Any]:
        """GET /quizzes/{quiz_id}"""
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(f"{self._base}/quizzes/{quiz_id}")
            _raise_for_service("ai-engine", resp)
            return resp.json()

    async def get_questions(
        self,
        quiz_id: str,
        set_number: int,
    ) -> list[dict[str, Any]]:
        """
        GET /quizzes/{quiz_id}/sets/{set_number}/questions
        Returns list of question objects.
        """
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                f"{self._base}/quizzes/{quiz_id}/sets/{set_number}/questions"
            )
            _raise_for_service("ai-engine", resp)
            data = resp.json()
            return data if isinstance(data, list) else data.get("questions", [])

    async def save_quiz(
        self,
        task_id: str,
        name: str,
        tags: list[str],
        is_public: bool,
        quiz_group_id: int | None,
        user_id: int,
    ) -> dict[str, Any]:
        """
        POST /quizzes
        Saves the quiz produced by a task to the DB.
        """
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base}/quizzes",
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
            return resp.json()

    async def save_manual_quiz(
        self,
        name: str,
        questions: list[dict[str, Any]],
        tags: list[str],
        is_public: bool,
        user_id: int,
    ) -> dict[str, Any]:
        """POST /quizzes/manual"""
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base}/quizzes/manual",
                json={
                    "name": name,
                    "questions": questions,
                    "tags": tags,
                    "is_public": is_public,
                    "user_id": user_id,
                },
            )
            _raise_for_service("ai-engine", resp)
            return resp.json()

    async def get_trending_tags(self, limit: int = 9) -> list[str]:
        """GET /tags/trending"""
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(f"{self._base}/tags/trending", params={"limit": limit})
            _raise_for_service("ai-engine", resp)
            data = resp.json()
            return data if isinstance(data, list) else data.get("tags", [])

    async def update_quiz_visibility(self, quiz_id: str, is_public: bool) -> dict[str, Any]:
        """PATCH /quizzes/{quiz_id}"""
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.patch(
                f"{self._base}/quizzes/{quiz_id}",
                json={"is_public": is_public},
            )
            _raise_for_service("ai-engine", resp)
            return resp.json()


# ──────────────────────────── Subscription Client ────────────────────────────


class SubscriptionClient:
    """Wraps the subscription service REST API."""

    def __init__(self, base_url: str = SUBSCRIPTION_URL) -> None:
        self._base = base_url.rstrip("/")

    async def check_limit(self, user_id: int, action: str = "file_upload") -> bool:
        """
        GET /limits/check
        Returns True if the action is still allowed.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._base}/limits/check",
                    params={"telegram_id": user_id, "action": action},
                )
                if resp.is_error:
                    return True  # fail-open
                return resp.json().get("allowed", True)
        except httpx.HTTPError as exc:
            logger.warning("subscription check_limit failed: %s", exc)
            return True  # fail-open

    async def increment_usage(self, user_id: int, action: str = "file_upload") -> None:
        """POST /limits/increment"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self._base}/limits/increment",
                    json={"telegram_id": user_id, "action": action},
                )
        except httpx.HTTPError as exc:
            logger.warning("subscription increment_usage failed: %s", exc)

    async def get_plan(self, user_id: int) -> dict[str, Any]:
        """GET /users/{user_id}/plan"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base}/users/{user_id}/plan")
                if resp.is_error:
                    return {"plan": "free"}
                return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("subscription get_plan failed: %s", exc)
            return {"plan": "free"}

    async def activate_premium(
        self, user_id: int, days: int, source: str = "stars"
    ) -> dict[str, Any]:
        """POST /users/{user_id}/premium"""
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                f"{self._base}/users/{user_id}/premium",
                json={"days": days, "source": source},
            )
            _raise_for_service("subscription", resp)
            return resp.json()


# ──────────────────────────── Notifier Client ────────────────────────────


class NotifierClient:
    """Wraps the Go notifier service REST API."""

    def __init__(self, base_url: str = NOTIFIER_URL) -> None:
        self._base = base_url.rstrip("/")

    async def send_notification(
        self,
        user_id: int,
        text: str,
        inline_keyboard: list[list[dict[str, str]]] | None = None,
    ) -> None:
        """POST /notify — send a message to a single user."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self._base}/notify",
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
        """POST /broadcast — send a message to multiple users."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                await client.post(
                    f"{self._base}/broadcast",
                    json={
                        "user_ids": user_ids,
                        "text": text,
                        "inline_keyboard": inline_keyboard or [],
                    },
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

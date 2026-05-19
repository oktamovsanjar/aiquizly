"""
Redis da fayl qayta ishlash tasklari saqlanadi.
Bot restart bo'lganda pending tasklar tiklanadi.
"""
import json
import logging

logger = logging.getLogger(__name__)

REDIS_TASK_KEY = "upload:pending_tasks"  # Redis Hash: task_id -> JSON


async def save_pending_task(redis_client, task_id: str, chat_id: int, user_id: int,
                             file_name: str, lang: str, progress_msg_id: int,
                             bot_username: str) -> None:
    """Pending taskni Redis ga saqlaydi."""
    data = json.dumps({
        "task_id": task_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "file_name": file_name,
        "lang": lang,
        "progress_msg_id": progress_msg_id,
        "bot_username": bot_username,
    }, ensure_ascii=False)
    await redis_client.hset(REDIS_TASK_KEY, task_id, data)
    # 2 soatdan keyin avtomatik o'chirish
    await redis_client.expire(REDIS_TASK_KEY, 7200)


async def remove_pending_task(redis_client, task_id: str) -> None:
    """Tugagan taskni Redis dan o'chiradi."""
    await redis_client.hdel(REDIS_TASK_KEY, task_id)


async def get_all_pending_tasks(redis_client) -> list[dict]:
    """Barcha pending tasklarni qaytaradi."""
    raw = await redis_client.hgetall(REDIS_TASK_KEY)
    tasks = []
    for task_id, data in raw.items():
        try:
            t = json.loads(data)
            tasks.append(t)
        except Exception:
            pass
    return tasks


async def restore_pending_tasks(bot, redis_client) -> None:
    """Bot startup da Redis dan pending tasklarni qayta ishga tushiradi."""
    import asyncio
    from handlers.upload import _poll_until_done

    tasks = await get_all_pending_tasks(redis_client)
    if not tasks:
        return

    logger.info("Redis dan %d ta pending task tiklanyapti", len(tasks))
    for t in tasks:
        try:
            asyncio.create_task(
                _poll_until_done(
                    bot=bot,
                    chat_id=t["chat_id"],
                    user_id=t["user_id"],
                    task_id=t["task_id"],
                    file_name=t["file_name"],
                    lang=t["lang"],
                    progress_msg_id=t["progress_msg_id"],
                    bot_username=t.get("bot_username", "aiquizlybot"),
                )
            )
            logger.info("Task %s tiklandi", t["task_id"])
        except Exception as e:
            logger.warning("Task %s tiklanmadi: %s", t.get("task_id"), e)

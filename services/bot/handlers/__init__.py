from aiogram import Router, F

from .start import router as start_router
from .commands import router as commands_router
from .quiz import router as quiz_router
from .upload import router as upload_router
from .review import router as review_router
from .group import router as group_router
from .profile import router as profile_router
from .tg_group import router as tg_group_router

# ── Faqat private chatlarda ishlaydigan routerlar ──────────────────────────
# Guruhda bu handlerlar umuman chaqirilmaydi
_PRIVATE = F.chat.type == "private"
_PRIVATE_CB = F.message.chat.type == "private"

for _r in [start_router, commands_router, quiz_router,
           upload_router, review_router, group_router, profile_router]:
    _r.message.filter(_PRIVATE)
    _r.callback_query.filter(_PRIVATE_CB)

# ── Asosiy router ─────────────────────────────────────────────────────────
router = Router()

# Guruh handlerlari birinchi (aniq filtrli)
router.include_router(tg_group_router)

# Private handlerlari
router.include_router(start_router)
router.include_router(commands_router)
router.include_router(quiz_router)
router.include_router(upload_router)
router.include_router(review_router)
router.include_router(group_router)
router.include_router(profile_router)

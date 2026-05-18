from fastapi import APIRouter

from .analytics import router as analytics_router
from .notifications import router as notifications_router
from .quizzes import router as quizzes_router
from .settings import router as settings_router
from .users import router as users_router

router = APIRouter()
router.include_router(analytics_router)
router.include_router(users_router)
router.include_router(quizzes_router)
router.include_router(notifications_router)
router.include_router(settings_router)

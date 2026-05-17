from aiogram import Router

from .start import router as start_router
from .commands import router as commands_router
from .quiz import router as quiz_router
from .upload import router as upload_router
from .profile import router as profile_router

router = Router()
router.include_router(start_router)
router.include_router(commands_router)
router.include_router(quiz_router)
router.include_router(upload_router)
router.include_router(profile_router)

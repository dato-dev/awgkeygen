from aiogram import Router

from bot.handlers.admin import router as admin_router
from bot.handlers.user import router as user_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(admin_router)
    root.include_router(user_router)
    return root

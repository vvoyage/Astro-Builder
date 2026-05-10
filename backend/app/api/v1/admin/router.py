"""Агрегирующий роутер для /admin/*."""
from fastapi import APIRouter

from app.api.v1.admin.stats import router as admin_stats_router
from app.api.v1.admin.users import router as admin_users_router

router = APIRouter()
router.include_router(admin_stats_router)
router.include_router(admin_users_router)

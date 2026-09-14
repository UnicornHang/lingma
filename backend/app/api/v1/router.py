"""v1 API 主路由"""
from fastapi import APIRouter

from app.api.v1 import (
    backup,
    chapters,
    characters,
    critic,
    outline,
    rag,
    settings,
    tasks,
    works,
    world,
)

api_router = APIRouter()

# 注册子路由
api_router.include_router(works.router, prefix="/works", tags=["作品"])
api_router.include_router(chapters.router, prefix="/chapters", tags=["章节"])
api_router.include_router(characters.router, tags=["角色"])
api_router.include_router(outline.router, tags=["大纲"])
api_router.include_router(world.router, tags=["世界书"])
api_router.include_router(critic.router, tags=["评审"])
api_router.include_router(rag.router, tags=["RAG"])
api_router.include_router(tasks.router, tags=["任务"])
api_router.include_router(settings.router, prefix="/settings", tags=["设置"])
api_router.include_router(
    backup.router, prefix="/settings/backup", tags=["备份"]
)
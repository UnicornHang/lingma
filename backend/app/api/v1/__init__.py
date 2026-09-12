"""v1 API 路由聚合"""
from fastapi import APIRouter

from app.api.v1 import works

api_router = APIRouter()

# 注册子路由
api_router.include_router(works.router, prefix="/works", tags=["作品"])

# TODO: 其他路由（chapters, outline, characters, world, agents, settings 等）
# api_router.include_router(chapters.router, prefix="/chapters", tags=["章节"])
# api_router.include_router(outline.router, prefix="/outline", tags=["大纲"])
# api_router.include_router(characters.router, prefix="/characters", tags=["角色"])
# api_router.include_router(world.router, prefix="/world", tags=["世界"])
# api_router.include_router(agents.router, prefix="/agents", tags=["Agent"])
# api_router.include_router(tasks.router, prefix="/tasks", tags=["任务"])
# api_router.include_router(settings.router, prefix="/settings", tags=["设置"])
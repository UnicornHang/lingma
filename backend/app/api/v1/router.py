"""v1 API 主路由"""
from fastapi import APIRouter

from app.api.v1 import chapters, settings, works

api_router = APIRouter()

# 注册子路由
api_router.include_router(works.router, prefix="/works", tags=["作品"])
api_router.include_router(chapters.router, prefix="/chapters", tags=["章节"])
api_router.include_router(settings.router, prefix="/settings", tags=["设置"])
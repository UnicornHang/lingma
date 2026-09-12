"""Pytest 配置 - 启用 lifespan + 测试用 SQLite"""
import os

# 设置测试环境变量（必须在导入 app 之前）
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault(
    "APP_SECRET", "test-secret-for-unit-tests-32chars-min-length-required-please"
)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test_lingma.db")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import asyncio
from pathlib import Path
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.main import app
from app.db.session import async_session_factory, engine, init_db


@pytest.fixture(scope="session")
def event_loop():
    """事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def _setup_database():
    """会话级：建表 + 清理"""
    # 确保 data 目录存在
    Path("data").mkdir(exist_ok=True)
    # 删除旧测试库
    db_file = Path("data/test_lingma.db")
    if db_file.exists():
        db_file.unlink()

    # 建表
    async with engine.begin() as conn:
        from app.models.base import Base
        from app.models import (  # noqa: F401
            api_config,
            chapter,
            character,
            outline,
            setting,
            task,
            world,
            work,
        )
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 清理
    await engine.dispose()
    if db_file.exists():
        db_file.unlink()


@pytest.fixture
async def db_session():
    """每个测试一个事务"""
    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP 客户端（自动清理表数据）"""
    from httpx import ASGITransport
    from app.models.base import Base

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 清空所有表（保留 schema）
        async with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(text(f"DELETE FROM {table.name}"))
        yield ac
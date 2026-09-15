"""数据库 Session 管理"""
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

# 确保数据目录存在
db_path = settings.database_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
if db_path and not db_path.startswith(":"):  # 跳过内存数据库
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
    future=True,
)

# Session 工厂
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """初始化数据库（创建表）"""
    # 导入所有模型以注册到 Base.metadata
    from app.models.base import Base
    from app.models import (  # noqa: F401
        api_config,
        chapter,
        character,
        critic_evaluation,  # [P2]
        outline,
        prompt_template,  # [P4]
        setting,
        style_profile,  # 仿文风格画像
        task,
        tracking,  # 连续性账本
        world,
        work,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_sqlite_columns)

    logger.info(f"数据库初始化完成: {settings.database_url}")


def _ensure_sqlite_columns(sync_conn) -> None:
    """为已有 SQLite 库补列（create_all 不会 ALTER 旧表）。"""
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    tables = set(insp.get_table_names())
    if "outline_nodes" not in tables:
        return
    cols = {c["name"] for c in insp.get_columns("outline_nodes")}
    if "write_constraints" not in cols:
        sync_conn.execute(text("ALTER TABLE outline_nodes ADD COLUMN write_constraints JSON"))
        logger.info("已为 outline_nodes 补列 write_constraints")


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
    logger.info("数据库连接已关闭")


async def check_db_health() -> bool:
    """检查数据库连接是否正常"""
    from sqlalchemy import text

    async with async_session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        return result.scalar() == 1
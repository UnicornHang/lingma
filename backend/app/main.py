"""ZhiMeng Backend - FastAPI 应用入口"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import async_session_factory, close_db, init_db
from app.api.v1.router import api_router
from app.services import backup_service

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

# 自动备份后台任务句柄
_auto_backup_task: asyncio.Task | None = None


def _interval_delta(interval: str) -> timedelta:
    """备份周期 → timedelta。"""
    if interval == "weekly":
        return timedelta(days=7)
    if interval == "monthly":
        return timedelta(days=30)
    return timedelta(days=1)


async def _auto_backup_loop() -> None:
    """每小时检查一次;若开启自动备份且距上次超过周期则创建。"""
    while True:
        try:
            await asyncio.sleep(3600)
            async with async_session_factory() as db:
                prefs = await backup_service.get_backup_prefs(db)
                if not prefs.auto_backup:
                    continue
                items = backup_service.list_backup_files()
                last = items[0].created_at if items else None
                now = datetime.now(tz=timezone.utc)
                due = last is None or (now - last) >= _interval_delta(prefs.interval)
                if due:
                    result = await backup_service.create_backup(db)
                    await db.commit()
                    logger.info(
                        "自动备份完成: %s (pruned=%s)",
                        result.backup.filename,
                        result.pruned,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("自动备份循环异常: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _auto_backup_task

    # 启动
    logger.info("🚀 ZhiMeng Backend 启动中...")
    logger.info(f"环境: {settings.app_env}")
    logger.info(f"日志级别: {settings.log_level}")

    try:
        await init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}", exc_info=True)
        raise

    _auto_backup_task = asyncio.create_task(_auto_backup_loop())
    logger.info("✅ 自动备份调度已启动(每小时检查)")
    logger.info(f"✅ 服务就绪，监听端口: {settings.backend_port}")

    yield

    # 关闭
    logger.info("🛑 ZhiMeng Backend 关闭中...")
    if _auto_backup_task is not None:
        _auto_backup_task.cancel()
        try:
            await _auto_backup_task
        except asyncio.CancelledError:
            pass
        _auto_backup_task = None
    await close_db()
    logger.info("✅ 资源清理完成")


# 创建 FastAPI 应用
app = FastAPI(
    title="ZhiMeng API",
    description="织梦小说 AI Agent 平台 - 后端 API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
    openapi_url="/openapi.json" if settings.app_env == "development" else None,
    lifespan=lifespan,
)

# ==================== 中间件 ====================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 全局异常处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常捕获"""
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": str(exc) if settings.app_env == "development" else None,
            }
        },
    )


# ==================== 路由 ====================

# 根路径
@app.get("/")
async def root():
    return {
        "name": "ZhiMeng API",
        "version": "0.1.0",
        "docs": "/docs" if settings.app_env == "development" else "disabled",
    }


# 健康检查
@app.get("/health")
async def health():
    """健康检查端点"""
    from app.db.session import check_db_health

    db_status = "ok"
    try:
        await check_db_health()
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "0.1.0",
        "environment": settings.app_env,
        "database": db_status,
        "vector_store": "ok",  # TODO: 实检测
    }


# 注册 v1 API 路由
app.include_router(api_router, prefix="/api/v1")


# ==================== WebSocket 路由 ====================

from app.api.ws.generation import ws_router  # noqa: E402

app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn

    is_dev = settings.app_env == "development"
    if is_dev:
        # 开发模式默认开 --reload,改代码自动重启
        logger.info("🛠️  开发模式: 启用 uvicorn --reload,改动会自动重启")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=is_dev,
        reload_dirs=["app"] if is_dev else None,
        log_level=settings.log_level.lower(),
    )
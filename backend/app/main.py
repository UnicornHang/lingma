"""ZhiMeng Backend - FastAPI 应用入口"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import close_db, init_db
from app.api.v1.router import api_router

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
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

    logger.info(f"✅ 服务就绪，监听端口: {settings.backend_port}")

    yield

    # 关闭
    logger.info("🛑 ZhiMeng Backend 关闭中...")
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
"""应用配置 - 基于 Pydantic Settings"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置（自动从 .env 读取）"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ===== 基础 =====
    app_env: Literal["development", "production"] = "production"
    app_secret: str = Field(
        default="change-me-to-random-32-chars-string-please",
        min_length=32,
    )
    log_level: str = "INFO"

    # ===== 服务 =====
    backend_port: int = 8000
    workers: int = 2

    # ===== 数据库 =====
    database_url: str = "sqlite+aiosqlite:////app/data/works/zhimeng.db"

    @property
    def database_url_sync(self) -> str:
        """同步版本（用于 Alembic）"""
        return self.database_url.replace("+aiosqlite", "")

    # ===== 向量库 =====
    vector_store_path: str = "/app/data/vector_store"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    # ===== LLM 限流 =====
    rate_limit_per_minute: int = 60
    max_concurrent_llm: int = 3

    # ===== Redis (可选) =====
    redis_url: str | None = None

    # ===== CORS =====
    cors_origins: list[str] = [
        "http://localhost:7860",
        "http://localhost:3000",
        "http://127.0.0.1:7860",
    ]


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()


settings = get_settings()
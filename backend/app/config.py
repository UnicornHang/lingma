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
    rag_enabled: bool = True                       # RAG 总开关（设为 False 全量跳过向量检索）
    rag_top_k: int = 5                             # 默认检索条数
    rag_chunk_min_chars: int = 200                 # 段落级 chunk 最小字数
    rag_chunk_max_chars: int = 500                 # 段落级 chunk 最大字数
    rag_collection_prefix: str = "lingma"          # collection 前缀（按 work 隔离）

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

    # ===== [P3.3] Critic 触发自动改写循环 =====
    # 当 critic.overall 低于此阈值时,触发整章改写(写新 ChapterVersion 保留历史)
    # 保守起步 0.6:防止劣改、防止生成时长膨胀;可由 per-request 或 per-work 覆盖
    critic_rewrite_threshold: float = 0.6
    # 单次生成最多改写次数(包含第一次失败的 0 改写)
    # 默认 1:首次 critic 不达标则改一次,不再退步
    critic_rewrite_max: int = 1

    # ===== [P3.4] DOCX + EPUB 导出 =====
    # 单次导出最多包含的章节数(防止大作品阻塞请求线程)
    export_max_chapters: int = 500
    # DOCX Normal style + EPUB CSS 使用的 CJK 字体名(英文界面显示用)
    # 在 Linux/Docker 上若无该字体,Word 会回退到默认中文字形
    export_cjk_font_name: str = "Microsoft YaHei"
    # 可选:指向具体字体文件的相对路径(供 epub CSS @font-face 嵌入)
    # 留空则 EPUB CSS 只声明 font-family,不内嵌字体(包体小,跨平台字形回退)
    export_font_path: str = ""


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()


settings = get_settings()
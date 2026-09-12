"""API 配置 (APIConfig) 数据模型"""
import enum
from uuid import UUID

from sqlalchemy import Boolean, Enum as SAEnum, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Provider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    VLLM = "vllm"
    CUSTOM = "custom"


class APIConfig(Base, UUIDMixin, TimestampMixin):
    """LLM API 配置（API Key 加密存储）"""

    __tablename__ = "api_configs"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[Provider] = mapped_column(SAEnum(Provider), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Agent 分配
    agent_assignments: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # 元数据
    max_context_tokens: Mapped[int] = mapped_column(Integer, default=32000, nullable=False)
    cost_per_1k_input: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_per_1k_output: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
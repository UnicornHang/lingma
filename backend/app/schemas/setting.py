"""设置 (Setting) 相关的 Pydantic Schema"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr


# ==================== 应用设置（key-value）====================


class SettingsBundle(BaseModel):
    """应用全局设置包（聚合）"""

    theme: str = Field(default="light", description="light | dark | system")
    language: str = Field(default="zh-CN")
    font_size: int = Field(default=14, ge=10, le=24)
    auto_save_interval: int = Field(default=30, ge=5, le=600)
    default_model: str | None = None
    active_preset: str | None = None


class SettingsUpdate(BaseModel):
    """更新设置（全部字段可选）"""

    theme: str | None = None
    language: str | None = None
    font_size: int | None = Field(None, ge=10, le=24)
    auto_save_interval: int | None = Field(None, ge=5, le=600)
    default_model: str | None = None
    active_preset: str | None = None


# ==================== API 配置 ====================


class ApiConfigCreate(BaseModel):
    """创建 API 配置"""

    name: str = Field(..., min_length=1, max_length=100, description="备注名")
    provider: str = Field(..., description="openai | anthropic | deepseek | qwen | ollama | custom")
    api_key: SecretStr | None = Field(None, description="API Key（加密存储）")
    base_url: str | None = Field(None, description="自定义 Base URL")
    model_name: str = Field(..., description="默认模型名")
    enabled: bool = Field(default=True)
    max_context_tokens: int = Field(default=32_000, ge=1_000, le=200_000)
    cost_per_1k_input: float = Field(default=0.0, ge=0)
    cost_per_1k_output: float = Field(default=0.0, ge=0)
    agent_assignments: list[str] = Field(default_factory=list)


class ApiConfigUpdate(BaseModel):
    """更新 API 配置"""

    name: str | None = Field(None, min_length=1, max_length=100)
    api_key: SecretStr | None = None
    base_url: str | None = None
    model_name: str | None = None
    enabled: bool | None = None
    max_context_tokens: int | None = Field(None, ge=1_000, le=200_000)
    cost_per_1k_input: float | None = Field(None, ge=0)
    cost_per_1k_output: float | None = Field(None, ge=0)
    agent_assignments: list[str] | None = None


class ApiConfigRead(BaseModel):
    """读取 API 配置（不回显 Key）"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    provider: str
    masked_key: str = Field(..., description="脱敏后的 Key")
    base_url: str
    model_name: str
    enabled: bool
    max_context_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    agent_assignments: list[str]
    created_at: datetime
    updated_at: datetime


class ApiKeyReveal(BaseModel):
    """一次性展示明文 Key"""

    api_key: str
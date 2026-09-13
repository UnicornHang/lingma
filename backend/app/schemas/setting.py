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
    density: str = Field(default="comfortable", description="compact | comfortable")
    default_model: str | None = None
    active_preset: str | None = Field(None, description="StylePreset.name（默认预设名）")
    default_target_word_count: int = Field(default=3000, ge=500, le=20000)


class SettingsUpdate(BaseModel):
    """更新设置（全部字段可选）"""

    theme: str | None = None
    language: str | None = None
    font_size: int | None = Field(None, ge=10, le=24)
    auto_save_interval: int | None = Field(None, ge=5, le=600)
    density: str | None = None
    default_model: str | None = None
    active_preset: str | None = None
    default_target_word_count: int | None = Field(None, ge=500, le=20000)


# ==================== StylePreset 写作风格预设 ====================


class StylePresetCreate(BaseModel):
    """新建风格预设"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    style_keywords: list[str] = Field(default_factory=list)
    target_audience: list[str] = Field(default_factory=list)
    target_word_count: int = Field(default=3000, ge=500, le=20000)


class StylePresetUpdate(BaseModel):
    """更新风格预设"""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    style_keywords: list[str] | None = None
    target_audience: list[str] | None = None
    target_word_count: int | None = Field(None, ge=500, le=20000)


class StylePresetRead(BaseModel):
    """读取风格预设"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    style_keywords: list[str]
    target_audience: list[str]
    target_word_count: int
    is_builtin: bool
    created_at: datetime
    updated_at: datetime


# ==================== API 配置 ====================


class ApiConfigCreate(BaseModel):
    """创建 API 配置"""

    name: str = Field(..., min_length=1, max_length=100, description="备注名")
    provider: str = Field(..., description="openai | anthropic | deepseek | qwen | MiniMax | ollama | lmstudio | vllm | custom")
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


class ProviderModelsRequest(BaseModel):
    """拉取 Provider 模型清单（不持久化 api_key）"""

    provider: str = Field(..., description="openai | anthropic | deepseek | qwen | MiniMax | ollama | lmstudio | vllm | custom")
    base_url: str | None = Field(None, description="可选，留空则用 Provider 默认值")
    api_key: str | None = Field(None, description="仅本次请求使用，不存储")


class ProviderModelsResponse(BaseModel):
    """模型清单响应"""

    models: list[str] = Field(default_factory=list)
    source: str = Field(..., description="api 实时拉取 | static 内置静态清单")
    note: str | None = None
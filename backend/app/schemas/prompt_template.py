"""[P4] Prompt 模板 Schema"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AgentType = Literal[
    "writer", "plot", "world", "character", "editor", "critic"
]


class PromptTemplateRead(BaseModel):
    """读取单个 Agent 的 Prompt 模板。"""

    model_config = ConfigDict(from_attributes=True)

    agent_type: AgentType
    name: str
    description: str
    system_prompt: str
    enabled: bool
    variables: list[str] = Field(default_factory=list)
    is_customized: bool = Field(
        False, description="相对内置默认是否已被用户修改"
    )
    updated_at: datetime | None = None


class PromptTemplateUpdate(BaseModel):
    """更新 Prompt 模板(全部可选)。"""

    model_config = ConfigDict(extra="forbid")

    system_prompt: str | None = Field(None, min_length=20)
    enabled: bool | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class PromptTemplateListResponse(BaseModel):
    """六个 Agent 模板列表。"""

    items: list[PromptTemplateRead]

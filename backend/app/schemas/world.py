"""World bible 相关的 Pydantic Schema"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorldBibleBase(BaseModel):
    """世界观基础字段"""

    geography: dict = Field(default_factory=dict)
    factions: list = Field(default_factory=list)
    power_system: dict = Field(default_factory=dict)
    timeline: list = Field(default_factory=list)
    rules: list = Field(default_factory=list)
    culture: dict = Field(default_factory=dict)
    raw_text: str = Field(default="", max_length=20_000)


class WorldBibleCreate(WorldBibleBase):
    """创建世界观"""

    work_id: UUID


class WorldBibleUpdate(BaseModel):
    """更新世界观（字段可选）"""

    geography: dict | None = None
    factions: list | None = None
    power_system: dict | None = None
    timeline: list | None = None
    rules: list | None = None
    culture: dict | None = None
    raw_text: str | None = Field(None, max_length=20_000)


class WorldBibleRead(WorldBibleBase):
    """读取世界观"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_id: UUID
    is_indexed: bool = False
    created_at: datetime
    updated_at: datetime
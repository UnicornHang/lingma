"""Character 相关的 Pydantic Schema"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CharacterBase(BaseModel):
    """角色基础字段"""

    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(
        default="supporting",
        description="protagonist/antagonist/supporting/narrator",
        max_length=20,
    )
    basic_info: dict = Field(default_factory=dict)
    personality: dict = Field(default_factory=dict)
    backstory: dict = Field(default_factory=dict)
    relationships: list = Field(default_factory=list)
    arc: dict = Field(default_factory=dict)
    voice_samples: list = Field(default_factory=list)
    raw_text: str = Field(default="", max_length=10_000)


class CharacterCreate(CharacterBase):
    """创建角色"""

    work_id: UUID


class CharacterUpdate(BaseModel):
    """更新角色（字段可选）"""

    name: str | None = Field(None, min_length=1, max_length=100)
    role: str | None = Field(None, max_length=20)
    basic_info: dict | None = None
    personality: dict | None = None
    backstory: dict | None = None
    relationships: list | None = None
    arc: dict | None = None
    voice_samples: list | None = None
    raw_text: str | None = Field(None, max_length=10_000)


class CharacterRead(CharacterBase):
    """读取角色"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_id: UUID
    appearance_count: int = 0
    is_indexed: bool = False
    created_at: datetime
    updated_at: datetime


class CharacterListResponse(BaseModel):
    total: int
    items: list[CharacterRead]
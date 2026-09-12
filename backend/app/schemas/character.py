"""Character 相关的 Pydantic Schema"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ==================== 基础 CRUD ====================


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


# ==================== AI 推荐（强 schema 校验）====================


CharacterRoleLiteral = Literal["protagonist", "antagonist", "supporting", "narrator"]


class CharacterBasicInfo(BaseModel):
    """LLM 输出：基础信息（年龄/身份/外貌/背景）"""

    model_config = ConfigDict(extra="forbid")

    age: str | None = None
    occupation: str | None = None
    appearance: str | None = None
    background: str | None = None


class CharacterPersonality(BaseModel):
    """LLM 输出：性格画像"""

    model_config = ConfigDict(extra="forbid")

    traits: list[str] = Field(default_factory=list, max_length=12)
    mbti: str | None = None
    strengths: list[str] = Field(default_factory=list, max_length=12)
    flaws: list[str] = Field(default_factory=list, max_length=12)


class CharacterBackstory(BaseModel):
    """LLM 输出：身世与过往"""

    model_config = ConfigDict(extra="forbid")

    origin: str | None = None
    key_events: list[str] = Field(default_factory=list, max_length=8)
    secrets: list[str] = Field(default_factory=list, max_length=6)


class CharacterRelationship(BaseModel):
    """LLM 输出：人物关系（一句话）"""

    model_config = ConfigDict(extra="forbid")

    target_character: str = Field(..., min_length=1, max_length=100)
    relation: str = Field(..., min_length=1, max_length=50)
    dynamic: str = Field(default="", max_length=300)


class CharacterArc(BaseModel):
    """LLM 输出：人物弧线"""

    model_config = ConfigDict(extra="forbid")

    start_state: str | None = None
    end_state: str | None = None
    key_transformations: list[str] = Field(default_factory=list, max_length=8)


class CharacterCard(BaseModel):
    """LLM 输出的单个角色卡（强 schema 校验）"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)
    role: CharacterRoleLiteral = "supporting"
    basic_info: CharacterBasicInfo = Field(default_factory=CharacterBasicInfo)
    personality: CharacterPersonality = Field(default_factory=CharacterPersonality)
    backstory: CharacterBackstory = Field(default_factory=CharacterBackstory)
    relationships: list[CharacterRelationship] = Field(default_factory=list, max_length=20)
    arc: CharacterArc = Field(default_factory=CharacterArc)
    voice_samples: list[str] = Field(default_factory=list, max_length=8)
    raw_text: str = Field(default="", max_length=10_000)


class CharacterSuggestRequest(BaseModel):
    """AI 推荐角色请求"""

    work_id: UUID
    count: int = Field(3, ge=1, le=10)
    focus: Literal["protagonist", "antagonist", "supporting", "all"] = "supporting"
    extra_hint: str | None = Field(default=None, max_length=500)


class CharacterSuggestResponse(BaseModel):
    """AI 推荐角色响应"""

    cards: list[CharacterCard]
    model_used: str = "mock"
    raw_content: str = ""  # 调试用：LLM 原始输出（解析失败时排查）


# ==================== AI 推荐（兼容层）====================
# 注：为避免破坏向后兼容，老的 CharacterBase.character 字段保留 dict 类型。
# 若需将 CharacterCard 落库，调用方应用 CharacterCard → CharacterCreate 的字段映射：
#   CharacterCreate(
#       work_id=..., name=c.name, role=c.role, raw_text=c.raw_text,
#       basic_info=c.basic_info.model_dump(),
#       personality=c.personality.model_dump(),
#       ...
#   )

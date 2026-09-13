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


# ==================== AI 推荐（强 schema 校验）====================
# 注:这些 schema 用于 World Agent 的 LLM 输出校验,不直接对应 DB 字段。
# LLM 返回后,前端可选择把各维度合并进 WorldBible 对应的 JSON blob 字段。

from typing import Literal  # noqa: E402  (放在文件末尾便于阅读)


WorldDimensionLiteral = Literal[
    "geography", "factions", "power_system", "timeline", "rules", "culture"
]


class GeographyEntry(BaseModel):
    """LLM 输出:地理区域条目"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    climate: str | None = None
    notable_features: list[str] = Field(default_factory=list, max_length=8)


class FactionEntry(BaseModel):
    """LLM 输出:势力条目"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="", max_length=40)
    description: str = Field(default="", max_length=500)
    leader: str | None = None
    goals: str | None = None
    territory: str | None = None


class PowerTier(BaseModel):
    """LLM 输出:力量体系的一个等级"""

    model_config = ConfigDict(extra="forbid")

    tier_name: str = Field(..., min_length=1, max_length=50)
    tier_level: int = Field(default=1, ge=1, le=99)
    description: str = Field(default="", max_length=300)
    abilities: list[str] = Field(default_factory=list, max_length=8)


class PowerSystem(BaseModel):
    """LLM 输出:力量体系(整张表)"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=500)
    tiers: list[PowerTier] = Field(default_factory=list, max_length=20)
    rules: list[str] = Field(default_factory=list, max_length=12)
    resources: list[str] = Field(default_factory=list, max_length=12)


class TimelineEvent(BaseModel):
    """LLM 输出:历史时间线事件"""

    model_config = ConfigDict(extra="forbid")

    era: str = Field(default="", max_length=60)
    year: str | None = None
    event_name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    key_figures: list[str] = Field(default_factory=list, max_length=8)


class RuleEntry(BaseModel):
    """LLM 输出:世界规则/禁忌"""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(default="", max_length=40)
    description: str = Field(..., min_length=1, max_length=300)
    examples: list[str] = Field(default_factory=list, max_length=4)


class CultureEntry(BaseModel):
    """LLM 输出:文化条目"""

    model_config = ConfigDict(extra="forbid")

    languages: list[str] = Field(default_factory=list, max_length=12)
    customs: list[str] = Field(default_factory=list, max_length=12)
    religions: list[str] = Field(default_factory=list, max_length=12)
    arts: list[str] = Field(default_factory=list, max_length=12)
    cuisine: list[str] = Field(default_factory=list, max_length=12)
    values: list[str] = Field(default_factory=list, max_length=12)


class WorldBibleSuggestion(BaseModel):
    """LLM 输出的完整世界书建议(6 维度)。

    - 顶层 extra="ignore":允许 LLM 输出意外字段不阻断
    - 每个维度可以是 dict(自由结构) 或对应 Entry schema(强结构)
    - 单维度校验失败 → 跳过该维度,其余保留(由 world_agent 内部处理)
    """

    model_config = ConfigDict(extra="ignore")

    geography: dict = Field(default_factory=dict)
    factions: dict = Field(default_factory=dict)
    power_system: dict = Field(default_factory=dict)
    timeline: dict = Field(default_factory=dict)
    rules: dict = Field(default_factory=dict)
    culture: dict = Field(default_factory=dict)


class WorldSuggestRequest(BaseModel):
    """AI 推荐世界书请求"""

    work_id: UUID
    focus_dimension: Literal[
        "geography", "factions", "power_system", "timeline", "rules", "culture", "all"
    ] = "all"
    extra_hint: str | None = Field(default=None, max_length=500)


class WorldSuggestResponse(BaseModel):
    """AI 推荐世界书响应"""

    suggestion: WorldBibleSuggestion
    model_used: str = "mock"
    raw_content: str = ""  # 调试用:LLM 原始输出
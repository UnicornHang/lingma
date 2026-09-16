"""Work 相关的 Pydantic Schema"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.work import Genre, WorkStatus
from app.schemas.outline import PlotVolume


class WorkWizardSeed(BaseModel):
    """新建向导种子：落库到 settings，并起步大纲 / 世界 / 主角。"""

    pen_name: str = Field(default="", max_length=100)
    volume1_name: str = Field(default="", max_length=200)
    chapter_target_words: int | None = Field(default=None, ge=100, le=20_000)
    pace: Literal["slow", "balanced", "fast"] = "balanced"
    reader_portrait: str = Field(default="", max_length=2000)
    core_conflict: str = Field(default="", max_length=2000)
    protagonist: str = Field(default="", max_length=100)
    origin_setting: str = Field(default="", max_length=200)
    opening_beats: list[str] = Field(default_factory=list, max_length=12)


class WorkBase(BaseModel):
    """作品基础字段"""

    title: str = Field(..., min_length=1, max_length=100, description="作品名")
    genre: Genre = Field(..., description="题材")
    logline: str = Field(default="", max_length=500, description="一句话简介")
    target_word_count: int = Field(
        default=1_000_000, ge=10_000, le=10_000_000, description="目标字数"
    )
    style_keywords: list[str] = Field(default_factory=list, description="风格关键词")
    target_audience: list[str] = Field(default_factory=list, description="目标读者")


class WorkCreate(WorkBase):
    """创建作品。seed 会引导起步大纲；volumes 有值时优先写入 AI 大纲。"""

    seed: WorkWizardSeed | None = None
    volumes: list[PlotVolume] = Field(default_factory=list, max_length=20)


class WorkUpdate(BaseModel):
    """更新作品（字段可选）"""

    title: str | None = Field(None, min_length=1, max_length=100)
    genre: Genre | None = None
    logline: str | None = Field(None, max_length=500)
    target_word_count: int | None = Field(None, ge=10_000, le=10_000_000)
    style_keywords: list[str] | None = None
    target_audience: list[str] | None = None
    status: WorkStatus | None = None
    settings: dict | None = None


class WorkRead(WorkBase):
    """读取作品"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: WorkStatus
    word_count: int
    settings: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WorkListResponse(BaseModel):
    """分页作品列表"""

    total: int
    page: int
    page_size: int
    items: list[WorkRead]
"""Outline 相关的 Pydantic Schema"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.outline import OutlineNodeType


class OutlineNodeBase(BaseModel):
    """大纲节点基础字段"""

    parent_id: UUID | None = Field(None, description="父节点 id（卷/章）")
    type: OutlineNodeType = Field(..., description="节点类型：volume/chapter/beat")
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(default="", max_length=2000)
    beats: list[str] = Field(default_factory=list, description="节拍要点")
    characters_involved: list[str] = Field(default_factory=list, description="涉及角色")
    world_refs: list[str] = Field(default_factory=list, description="引用世界观条目")
    target_word_count: int = Field(default=3000, ge=100, le=20_000)
    order: int = Field(default=0, ge=0, le=10_000)


class OutlineNodeCreate(OutlineNodeBase):
    """创建大纲节点"""

    work_id: UUID = Field(..., description="所属作品 id")


class OutlineNodeUpdate(BaseModel):
    """更新大纲节点（字段可选）"""

    parent_id: UUID | None = None
    type: OutlineNodeType | None = None
    title: str | None = Field(None, min_length=1, max_length=200)
    summary: str | None = Field(None, max_length=2000)
    beats: list[str] | None = None
    characters_involved: list[str] | None = None
    world_refs: list[str] | None = None
    target_word_count: int | None = Field(None, ge=100, le=20_000)
    order: int | None = Field(None, ge=0, le=10_000)


class OutlineNodeRead(OutlineNodeBase):
    """读取大纲节点"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_id: UUID
    created_at: datetime
    updated_at: datetime


class OutlineNodeListResponse(BaseModel):
    """大纲节点列表"""

    total: int
    items: list[OutlineNodeRead]


class OutlineTreeNode(BaseModel):
    """树形大纲节点（递归）"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parent_id: UUID | None
    type: OutlineNodeType
    title: str
    summary: str
    beats: list[str]
    characters_involved: list[str]
    world_refs: list[str]
    target_word_count: int
    order: int
    children: list["OutlineTreeNode"] = Field(default_factory=list)


class OutlineTreeResponse(BaseModel):
    """作品完整大纲树"""

    work_id: UUID
    nodes: list[OutlineTreeNode]


# ==================== AI 推荐大纲（强 schema 校验）====================


class PlotBeat(BaseModel):
    """LLM 输出：节拍要点"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=100)
    summary: str = Field(default="", max_length=500)


class PlotChapter(BaseModel):
    """LLM 输出：单章大纲"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(default="", max_length=2000)
    target_word_count: int = Field(default=3000, ge=100, le=20_000)
    beats: list[PlotBeat] = Field(default_factory=list, max_length=12)
    characters_involved: list[str] = Field(default_factory=list, max_length=20)
    world_refs: list[str] = Field(default_factory=list, max_length=20)
    key_events: list[str] = Field(default_factory=list, max_length=10)


class PlotVolume(BaseModel):
    """LLM 输出：单卷大纲"""

    model_config = ConfigDict(extra="forbid")

    vol_no: int = Field(..., ge=1, le=100)
    vol_title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(default="", max_length=2000)
    chapters: list[PlotChapter] = Field(default_factory=list, max_length=200)


class PlotOutlineRequest(BaseModel):
    """AI 推荐大纲请求"""

    total_volumes: int = Field(default=3, ge=1, le=10)
    target_chapter_count: int | None = Field(default=None, ge=1, le=200)
    extra_hint: str | None = Field(default=None, max_length=500)


class PlotOutlineResponse(BaseModel):
    """AI 推荐大纲响应"""

    volumes: list[PlotVolume]
    model_used: str = "mock"
    raw_content: str = ""  # 调试用：LLM 原始输出


class BulkOutlineCreateRequest(BaseModel):
    """批量写入大纲（接受 AI 推荐产出）"""

    volumes: list[PlotVolume] = Field(default_factory=list, max_length=20)
    extra_hint: str | None = None  # 占位,暂未使用
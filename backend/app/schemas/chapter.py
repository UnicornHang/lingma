"""Chapter 相关的 Pydantic Schema"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChapterBase(BaseModel):
    """章节基础字段"""

    title: str = Field(..., min_length=1, max_length=200, description="章节标题")
    content: dict[str, Any] = Field(default_factory=dict, description="TipTap JSON")
    plain_content: str = Field(default="", description="纯文本内容")
    summary: str = Field(default="", description="章节摘要")
    key_events: list[str] = Field(default_factory=list, description="关键事件")
    outline_node_id: UUID | None = Field(None, description="关联大纲节点")


class ChapterCreate(ChapterBase):
    """创建章节"""

    work_id: UUID = Field(..., description="所属作品 ID")


class ChapterUpdate(BaseModel):
    """更新章节"""

    title: str | None = Field(None, min_length=1, max_length=200)
    content: dict[str, Any] | None = None
    plain_content: str | None = None
    summary: str | None = None
    key_events: list[str] | None = None
    status: str | None = Field(None, description="draft | generated | reviewed | finalized")


class ChapterRead(ChapterBase):
    """读取章节"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_id: UUID
    status: str
    word_count: int
    version: int
    created_at: datetime
    updated_at: datetime


class ChapterListResponse(BaseModel):
    """分页章节列表"""

    total: int
    page: int
    page_size: int
    items: list[ChapterRead]


class GenerateChapterRequest(BaseModel):
    """生成章节请求"""

    chapter_id: UUID | None = Field(None, description="已存在章节 ID（重生成）")
    title: str | None = Field(None, description="新章节标题")
    outline_node_id: UUID | None = Field(None, description="基于哪个大纲节点生成")
    target_word_count: int | None = Field(None, ge=500, le=20_000)
    style_overrides: dict[str, Any] = Field(
        default_factory=dict, description="本次覆盖的 Prompt 变量"
    )
    mode: Literal["continue", "generate"] = Field(
        "continue",
        description="continue=续写已有正文（追加），generate=全量重写整章",
    )
    continue_from_chars: int = Field(
        1500,
        ge=100,
        le=5000,
        description="续写模式下，取章节末尾最近 N 字作为 prompt 上下文",
    )


class GenerationStreamEvent(BaseModel):
    """生成流式事件"""

    type: str = Field(..., description="事件类型: start | delta | progress | done | error")
    task_id: UUID | None = None
    chapter_id: UUID | None = None
    content: str | None = None
    progress: float | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None
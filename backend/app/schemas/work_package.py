"""[P3.5] 作品级 JSON 包 Schema(项目导入/导出)。

对齐 PRD 4.13.3:
{
  "format_version": "1.0",
  "work_info": {...},
  "world_bible": {...},
  "characters": [...],
  "outline": [...],
  "chapters": [...],
  "settings": {...}
}
"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


FORMAT_VERSION = "1.0"
ImportMode = Literal["create", "overwrite"]


class WorkPackageMeta(BaseModel):
    """包头信息。"""

    format_version: str = FORMAT_VERSION
    exported_at: datetime | None = None
    app: str = "zhimeng"


class WorkPackage(BaseModel):
    """完整作品包。"""

    format_version: str = FORMAT_VERSION
    exported_at: datetime | None = None
    app: str = "zhimeng"
    work_info: dict[str, Any]
    world_bible: dict[str, Any] | None = None
    characters: list[dict[str, Any]] = Field(default_factory=list)
    outline: list[dict[str, Any]] = Field(default_factory=list)
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class WorkImportResult(BaseModel):
    """导入结果摘要。"""

    work_id: UUID
    title: str
    mode: ImportMode
    chapter_count: int
    character_count: int
    outline_count: int
    has_world_bible: bool
    message: str

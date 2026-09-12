"""Task 相关的 Pydantic Schema"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerationTaskRead(BaseModel):
    """读取生成任务"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_id: UUID
    chapter_id: UUID | None
    outline_node_id: UUID | None
    task_type: str
    status: str
    progress: int = 0
    params: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    token_usage: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
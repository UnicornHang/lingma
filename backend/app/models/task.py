"""生成任务 (GenerationTask) 数据模型"""
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TaskType(str, enum.Enum):
    OUTLINE_GENERATE = "outline_generate"
    OUTLINE_EXPAND = "outline_expand"
    CHAPTER_GENERATE = "chapter_generate"
    CHAPTER_CONTINUE = "chapter_continue"
    CHAPTER_REWRITE = "chapter_rewrite"
    CHAPTER_EXPAND = "chapter_expand"
    CHAPTER_SHORTEN = "chapter_shorten"
    CHAPTER_POLISH = "chapter_polish"
    CHAPTER_REVIEW = "chapter_review"
    WORLD_BUILD = "world_build"
    CHARACTER_DESIGN = "character_design"
    CRITIC_EVALUATE = "critic_evaluate"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationTask(Base, UUIDMixin, TimestampMixin):
    """异步生成任务"""

    __tablename__ = "generation_tasks"

    work_id: Mapped[UUID] = mapped_column(ForeignKey("works.id"), nullable=False, index=True)
    chapter_id: Mapped[UUID | None] = mapped_column(ForeignKey("chapters.id"), nullable=True)
    outline_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("outline_nodes.id"), nullable=True
    )

    task_type: Mapped[TaskType] = mapped_column(String(50), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        String(20), default=TaskStatus.PENDING, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
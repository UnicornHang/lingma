"""世界观 (WorldBible) 数据模型"""
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorldBible(Base, UUIDMixin, TimestampMixin):
    """世界观圣经"""

    __tablename__ = "world_bibles"

    work_id: Mapped[UUID] = mapped_column(
        ForeignKey("works.id"), unique=True, nullable=False, index=True
    )

    # 结构化字段
    geography: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    factions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    power_system: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    timeline: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    rules: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    culture: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # 自然语言版本（供 Prompt 注入 + 向量化）
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # 向量化状态
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    if TYPE_CHECKING:
        from app.models.work import Work

    work: Mapped["Work"] = relationship(back_populates="world_bible")
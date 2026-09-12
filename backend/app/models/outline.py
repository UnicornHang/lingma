"""大纲节点 (OutlineNode) 数据模型"""
import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class OutlineNodeType(str, enum.Enum):
    VOLUME = "volume"
    CHAPTER = "chapter"
    BEAT = "beat"


class OutlineNode(Base, UUIDMixin, TimestampMixin):
    """大纲节点（卷/章/节拍）"""

    __tablename__ = "outline_nodes"

    work_id: Mapped[UUID] = mapped_column(ForeignKey("works.id"), nullable=False, index=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("outline_nodes.id"), nullable=True
    )

    type: Mapped[OutlineNodeType] = mapped_column(
        SAEnum(OutlineNodeType), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    beats: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    characters_involved: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    world_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    target_word_count: Mapped[int] = mapped_column(Integer, default=3000, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    if TYPE_CHECKING:
        from app.models.work import Work

    work: Mapped["Work"] = relationship(back_populates="outline_nodes")
    children: Mapped[list["OutlineNode"]] = relationship(
        "OutlineNode",
        backref="parent",
        remote_side="OutlineNode.id",
        lazy="selectin",
    )
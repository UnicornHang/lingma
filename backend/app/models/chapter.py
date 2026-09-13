"""章节 (Chapter) 数据模型"""
import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ChapterStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    FINALIZED = "finalized"


class Chapter(Base, UUIDMixin, TimestampMixin):
    """章节"""

    __tablename__ = "chapters"

    work_id: Mapped[UUID] = mapped_column(ForeignKey("works.id"), nullable=False, index=True)
    outline_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("outline_nodes.id"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # TipTap JSON
    plain_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    key_events: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[ChapterStatus] = mapped_column(
        String(20), default=ChapterStatus.DRAFT, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    if TYPE_CHECKING:
        from app.models.work import Work
        from app.models.critic_evaluation import CriticEvaluation

    work: Mapped["Work"] = relationship(back_populates="chapters")
    versions: Mapped[list["ChapterVersion"]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # [P2] 章节评审历史(同一章节多版本各一条)
    evaluations: Mapped[list["CriticEvaluation"]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CriticEvaluation.created_at.desc()",
    )


class ChapterVersion(Base, UUIDMixin, TimestampMixin):
    """章节版本历史"""

    __tablename__ = "chapter_versions"

    chapter_id: Mapped[UUID] = mapped_column(ForeignKey("chapters.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    plain_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    generated_by: Mapped[str] = mapped_column(String(20), nullable=False)  # user / ai / ai_revised
    prompt_used: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    note: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    chapter: Mapped["Chapter"] = relationship(back_populates="versions")
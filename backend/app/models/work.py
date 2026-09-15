"""作品 (Work) 数据模型"""
import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkStatus(str, enum.Enum):
    """作品状态"""

    DRAFT = "draft"
    WRITING = "writing"
    FINISHED = "finished"
    ARCHIVED = "archived"


class Genre(str, enum.Enum):
    """题材"""

    FANTASY = "fantasy"
    URBAN = "urban"
    ROMANCE = "romance"
    HISTORICAL = "historical"
    SCI_FI = "sci_fi"
    MYSTERY = "mystery"
    OTHER = "other"


class Work(Base, UUIDMixin, TimestampMixin):
    """作品主表"""

    __tablename__ = "works"

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    genre: Mapped[Genre] = mapped_column(SAEnum(Genre), nullable=False)
    target_word_count: Mapped[int] = mapped_column(Integer, default=1000000, nullable=False)
    logline: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    style_keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    target_audience: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[WorkStatus] = mapped_column(
        SAEnum(WorkStatus),
        default=WorkStatus.DRAFT,
        nullable=False,
    )
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # 关系
    if TYPE_CHECKING:
        from app.models.chapter import Chapter
        from app.models.character import Character
        from app.models.outline import OutlineNode
        from app.models.world import WorldBible
        from app.models.tracking import TrackingState
        from app.models.style_profile import StyleProfile

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="work",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    characters: Mapped[list["Character"]] = relationship(
        back_populates="work",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    outline_nodes: Mapped[list["OutlineNode"]] = relationship(
        back_populates="work",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    world_bible: Mapped["WorldBible"] = relationship(
        back_populates="work",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    tracking_state: Mapped["TrackingState"] = relationship(
        back_populates="work",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    style_profile: Mapped["StyleProfile"] = relationship(
        back_populates="work",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
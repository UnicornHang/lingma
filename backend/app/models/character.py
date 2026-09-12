"""角色 (Character) 数据模型"""
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Character(Base, UUIDMixin, TimestampMixin):
    """角色卡"""

    __tablename__ = "characters"

    work_id: Mapped[UUID] = mapped_column(ForeignKey("works.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="supporting", nullable=False)

    # 结构化字段
    basic_info: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    personality: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    backstory: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    relationships: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    arc: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    voice_samples: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # 统计
    appearance_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 向量化
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    if TYPE_CHECKING:
        from app.models.work import Work

    work: Mapped["Work"] = relationship(back_populates="characters")
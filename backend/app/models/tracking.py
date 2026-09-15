"""作品连续性追踪账本。

``payload`` JSON 是唯一可写权威；API 派生视图（上下文卡、伏笔列表、知情范围）
均由 payload 生成，禁止把派生 Markdown/摘要反向写回。
"""
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class TrackingState(Base, UUIDMixin, TimestampMixin):
    """每部作品一条追踪账本。"""

    __tablename__ = "tracking_states"

    work_id: Mapped[UUID] = mapped_column(
        ForeignKey("works.id"), nullable=False, unique=True, index=True
    )
    # 权威 JSON：伏笔、角色运行时状态、作者/读者时间线、章级增量、章约束
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    if TYPE_CHECKING:
        from app.models.work import Work

    work: Mapped["Work"] = relationship(back_populates="tracking_state")

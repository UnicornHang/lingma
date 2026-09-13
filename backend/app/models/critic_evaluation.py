"""CriticEvaluation 模型 —— 章节评审结果持久化

P2 新增:章节生成 WS 流完成后,由 ws/generation.py 的 critic hook 写入。
同一章节多版本可各自评分;前端从最新一条读(留 P3 趋势图)。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chapter import Chapter


class CriticEvaluation(Base):
    """章节评审记录(历史表,按时间倒序读最新一条)

    设计决策:
    - 不污染 chapters 表(不存 latest_* 列),原因:同一章节多版本应各自评分
    - version_no 取 critic 当时的 chapter.version,便于版本对齐
    - persona_scores 存 JSON list(单个 persona < 1KB)
    - consensus_issues 存 JSON list(LLM 二次聚合前的中转数据)
    """

    __tablename__ = "critic_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 取 critic 当时的 chapter.version(快照)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 4 维度评分 + overall,等权平均,范围 [0, 1]
    overall: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    consistency: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    pacing: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    prose: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    engagement: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    # 完整 persona 评分(Pydantic dump 后存 JSON)
    persona_scores: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # 共识问题(出现 ≥ 2 次的 top_issues)
    consensus_issues: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # 实际调用的模型
    model_used: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    if TYPE_CHECKING:
        from app.models.chapter import Chapter as _Chapter

    chapter: Mapped["Chapter"] = relationship(back_populates="evaluations")


__all__ = ["CriticEvaluation"]
"""仿文风格画像（StyleProfile）。

每部作品最多一条。只存结构化画像 + 短技法片段，不存对标书全文，
也不得写入连续性账本。
"""
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class StyleProfile(Base, UUIDMixin, TimestampMixin):
    """作品级仿文风格记忆。"""

    __tablename__ = "style_profiles"

    work_id: Mapped[UUID] = mapped_column(
        ForeignKey("works.id"), unique=True, nullable=False, index=True
    )

    # 用户自定义的对标来源标签（书名等），仅展示用
    source_label: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    # 参与分析的样本文字数（不落原文）
    source_char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 结构化风格画像（人称、句长、对话密度、节奏标签等）
    portrait: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # 可直接注入 Writer 的短指令
    writing_directives: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # 去剧情化短片段 [{tag, text}, ...]，MVP 内存 JSON，后续可迁向量库
    snippets: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # 关闭后 Writer 不注入本画像（关键词文风裁决仍生效）
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    if TYPE_CHECKING:
        from app.models.work import Work

    work: Mapped["Work"] = relationship(back_populates="style_profile")

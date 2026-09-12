"""系统设置 (Setting) 数据模型"""
from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Setting(Base, TimestampMixin):
    """键值对设置（单条记录即一个 key）"""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
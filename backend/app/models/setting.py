"""系统设置 (Setting) 数据模型"""
from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Setting(Base, TimestampMixin):
    """键值对设置(单条记录即一个 key)"""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class StylePreset(Base, UUIDMixin, TimestampMixin):
    """写作风格预设。

    - 用户可创建多套预设(如「仙侠玄幻」「都市言情」「科幻硬核」)
    - 每套预设包含 style_keywords(风格关键词)+ target_audience(目标读者)
    - 在 SettingsBundle.active_preset 中标记默认预设
    """

    __tablename__ = "style_presets"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    target_audience: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    target_word_count: Mapped[int] = mapped_column(Integer, default=3000, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
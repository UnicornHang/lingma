"""[P4] Prompt 模板覆盖 —— 每 Agent 一条可编辑 system prompt。"""
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PromptTemplate(Base, TimestampMixin):
    """用户可定制的 Agent System Prompt。

    - 以 agent_type 为自然主键(writer/plot/world/character/editor/critic)
    - enabled=False 时运行时回退到代码内置默认
    - system_prompt 支持 ``{{var}}`` 占位符(如 writer 的 target_words)
    """

    __tablename__ = "prompt_templates"

    agent_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # 文档用:该模板支持的占位符列表,如 ["target_words"]
    variables: Mapped[str] = mapped_column(
        String(200), default="", nullable=False
    )

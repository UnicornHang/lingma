"""仿文 Agent / 风格画像 API Schema。"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StyleSnippet(BaseModel):
    """去剧情化的短技法片段。"""

    tag: str = Field(default="通用", description="场景标签：对话/战斗/写景/心理等")
    text: str = Field(..., min_length=1, max_length=400, description="短样本，禁止整章")


class StylePortrait(BaseModel):
    """结构化风格画像（短 JSON）。"""

    narrative_pov: str = Field(default="", description="叙事人称/距离感")
    avg_sentence_len: str = Field(default="", description="句长倾向：偏短/中等/偏长")
    dialogue_density: str = Field(default="", description="对话密度：高/中/低")
    rhetoric_habits: list[str] = Field(default_factory=list, description="修辞习惯标签")
    pacing_tags: list[str] = Field(default_factory=list, description="节奏标签")
    emotional_style: str = Field(default="", description="情绪推进习惯")
    lexicon_notes: str = Field(default="", description="用词气质简述")


class StyleMimicAnalyzeRequest(BaseModel):
    """粘贴样本 → 抽风格画像。"""

    sample_text: str = Field(..., min_length=200, max_length=20000, description="用户自备样本文本")
    source_label: str = Field(default="", max_length=200, description="对标来源标签")
    save: bool = Field(default=True, description="是否写入本作品风格画像")
    enabled: bool = Field(default=True, description="保存后是否立即启用写前注入")


class StyleProfileUpdate(BaseModel):
    """更新启用状态或来源标签。"""

    enabled: bool | None = None
    source_label: str | None = Field(default=None, max_length=200)


class StyleProfileRead(BaseModel):
    """风格画像读模型。"""

    id: UUID
    work_id: UUID
    source_label: str
    source_char_count: int
    portrait: StylePortrait
    writing_directives: str
    snippets: list[StyleSnippet]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StyleMimicAnalyzeResponse(BaseModel):
    """分析预览；save=true 时附带已落库画像。"""

    portrait: StylePortrait
    writing_directives: str
    snippets: list[StyleSnippet]
    source_char_count: int
    model_used: str = "mock"
    used_heuristic: bool = False
    profile: StyleProfileRead | None = None


class StyleMemoryCard(BaseModel):
    """Writer 写前注入用的短卡（不落库）。"""

    source_label: str = ""
    writing_directives: str = ""
    portrait: StylePortrait = Field(default_factory=StylePortrait)
    snippets: list[StyleSnippet] = Field(default_factory=list)

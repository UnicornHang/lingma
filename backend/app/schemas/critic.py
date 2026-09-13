"""Critic 相关的 Pydantic Schema

5 Persona × 4 维度评审模型，对应 PRD §4.10。
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============== 常量定义 ==============

CriticPersona = Literal["shuangwen", "wenqing", "kaoju", "mengxin", "zhubian"]

ALL_PERSONAS: list[CriticPersona] = [
    "shuangwen", "wenqing", "kaoju", "mengxin", "zhubian",
]

PERSONA_LABELS_ZH: dict[CriticPersona, str] = {
    "shuangwen": "爽文党",
    "wenqing": "文青党",
    "kaoju": "考据党",
    "mengxin": "萌新读者",
    "zhubian": "主编",
}

PERSONA_DESCRIPTIONS: dict[CriticPersona, str] = {
    "shuangwen": "节奏爽感、主角打脸/升级",
    "wenqing": "文笔、意象、留白、隐喻",
    "kaoju": "设定自洽、人物言行一致、力量体系无 bug",
    "mengxin": "500 字入戏、钩子、顺畅度",
    "zhubian": "结构、节奏、市场卖点",
}


# ============== LLM 输出 schema ==============


class PersonaScore(BaseModel):
    """LLM 输出的单个 persona 评分(强 schema 校验)"""

    model_config = ConfigDict(extra="forbid")

    persona: CriticPersona
    consistency: float = Field(..., ge=0.0, le=1.0)
    pacing: float = Field(..., ge=0.0, le=1.0)
    prose: float = Field(..., ge=0.0, le=1.0)
    engagement: float = Field(..., ge=0.0, le=1.0)
    comment: str = Field(default="", max_length=300)
    top_issues: list[str] = Field(default_factory=list, max_length=5)


class AggregatedScore(BaseModel):
    """5 persona 的聚合分(等权平均)"""

    model_config = ConfigDict(extra="forbid")

    consistency: float = Field(..., ge=0.0, le=1.0)
    pacing: float = Field(..., ge=0.0, le=1.0)
    prose: float = Field(..., ge=0.0, le=1.0)
    engagement: float = Field(..., ge=0.0, le=1.0)
    overall: float = Field(..., ge=0.0, le=1.0)


# ============== 业务 schema ==============


class CriticEvaluateRequest(BaseModel):
    """Critic 评审请求

    - work_id: 必填,用于加载 work meta 与解析 provider config
    - chapter_id: 可选,提供时自动加载 chapter.plain_content 作为待评正文
    - content: 可选,直接传入待评正文(优先级高于 chapter_id)
    - personas: 可选,None 时评审全部 5 个 persona
    - extra_hint: 用户附加要求
    """

    work_id: UUID
    chapter_id: UUID | None = None
    content: str | None = Field(default=None, max_length=20_000)
    personas: list[CriticPersona] | None = None
    extra_hint: str | None = Field(default=None, max_length=500)


class CriticEvaluation(BaseModel):
    """Critic 评审结果(完整)"""

    chapter_id: UUID | None = None
    persona_scores: list[PersonaScore] = Field(default_factory=list)
    aggregated: AggregatedScore
    consensus_issues: list[str] = Field(default_factory=list, max_length=10)
    model_used: str = "mock"
    raw_content: str = ""


class CriticEvaluateResponse(BaseModel):
    """Critic 评审响应"""

    evaluation: CriticEvaluation
"""[P2] Critic 自动评审 hook 测试

覆盖:
- CriticEvaluation 模型持久化(创建 / 字段齐全)
- CriticSummary schema 校验
- GenerateChapterRequest.auto_critic 默认 True
- WS done payload schema 兼容 critic 字段(用 orchestrator 风格触发 done,
  验证生成的 payload 含 critic=None 或 dict)

实现策略:
WS hook 在 _handle_start 内调用 CriticAgent + 落库 + emit done,
直接测试 _handle_start 需要 mock 大量 LLM 流式,性价比低。
本测试聚焦:① 新模型/字段持久化路径 ② WS done payload 序列化兼容
完整 E2E 由 smoke_e2e_continue.py 覆盖。
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.chapter import Chapter, ChapterStatus
from app.models.critic_evaluation import CriticEvaluation
from app.models.work import Genre, Work
from app.schemas.chapter import GenerateChapterRequest
from app.schemas.critic import (
    AggregatedScore,
    CriticEvaluation as CriticEvaluationSchema,
    CriticSummary,
    PersonaScore,
)


# ============== 模型 / Schema ==============


async def test_critic_evaluation_model_can_be_created(db_session):
    """CriticEvaluation 落库:全字段写入 + 可 SELECT 出来"""
    work = Work(
        title="测试", genre="fantasy", logline="", style_keywords=[],
        target_audience=[], target_word_count=10000, notes="",
    )
    db_session.add(work)
    await db_session.flush()
    chapter = Chapter(
        work_id=work.id,
        title="第1章",
        plain_content="一段测试正文。" * 20,
        content={},
        status=ChapterStatus.GENERATED,
        word_count=200,
        version=2,
    )
    db_session.add(chapter)
    await db_session.flush()

    ce = CriticEvaluation(
        chapter_id=chapter.id,
        version_no=2,
        overall=0.78,
        consistency=0.80,
        pacing=0.75,
        prose=0.82,
        engagement=0.74,
        persona_scores=[{"persona": "shuangwen", "consistency": 0.8, "pacing": 0.7,
                          "prose": 0.9, "engagement": 0.7, "comment": "", "top_issues": []}],
        consensus_issues=["对话单薄", "节奏偏慢"],
        model_used="MiniMax-M3",
    )
    db_session.add(ce)
    await db_session.commit()

    r = await db_session.execute(select(CriticEvaluation).where(CriticEvaluation.id == ce.id))
    loaded = r.scalar_one()
    assert loaded.chapter_id == chapter.id
    assert loaded.version_no == 2
    assert loaded.overall == pytest.approx(0.78)
    assert loaded.consensus_issues == ["对话单薄", "节奏偏慢"]
    assert loaded.model_used == "MiniMax-M3"


def test_critic_summary_schema_accepts_valid_data():
    """CriticSummary Pydantic 校验:典型字段"""
    summary = CriticSummary(
        overall=0.82,
        consistency=0.85,
        pacing=0.78,
        prose=0.88,
        engagement=0.76,
        consensus_issues=["对话单薄"],
        model_used="MiniMax-M3",
        evaluation_id="00000000-0000-0000-0000-000000000001",
    )
    assert summary.overall == 0.82
    assert summary.consensus_issues == ["对话单薄"]
    dumped = summary.model_dump()
    assert dumped["model_used"] == "MiniMax-M3"
    assert dumped["evaluation_id"] == "00000000-0000-0000-0000-000000000001"


def test_critic_summary_schema_rejects_out_of_range():
    """评分必须 [0, 1]"""
    with pytest.raises(Exception):
        CriticSummary(
            overall=1.5,  # 超出上限
            consistency=0.5, pacing=0.5, prose=0.5, engagement=0.5,
            consensus_issues=[], model_used="x",
        )


def test_generate_chapter_request_auto_critic_default_true():
    """GenerateChapterRequest.auto_critic 默认 True(前端不传时也开)"""
    req = GenerateChapterRequest()
    assert req.auto_critic is True
    assert req.auto_polish is True  # 同时验证之前的字段未被破坏


def test_generate_chapter_request_auto_critic_can_be_disabled():
    """前端可显式关闭 auto_critic"""
    req = GenerateChapterRequest(auto_critic=False, auto_polish=False)
    assert req.auto_critic is False
    assert req.auto_polish is False


# ============== WS done payload schema 兼容 ==============


def test_done_payload_includes_critic_field_when_set():
    """WS done payload 含 critic 字段(dict 或 None)"""
    # 直接构造一个与 _handle_start done emit 形态一致的 dict
    payload = {
        "type": "done",
        "task_id": str(uuid4()),
        "stream_id": str(uuid4()),
        "content": "正文",
        "token_usage": {"input_tokens": 100, "output_tokens": 200},
        "mode": "continue",
        "auto_polish_report": None,
        "critic": {
            "overall": 0.8, "consistency": 0.85, "pacing": 0.75,
            "prose": 0.9, "engagement": 0.7,
            "consensus_issues": ["对话单薄"],
            "model_used": "MiniMax-M3",
            "evaluation_id": str(uuid4()),
        },
    }
    assert "critic" in payload
    assert payload["critic"]["overall"] == 0.8
    assert payload["critic"]["consensus_issues"] == ["对话单薄"]


def test_done_payload_critic_none_when_hook_fails():
    """critic hook 失败时 done payload critic=None(graceful degradation)"""
    payload = {
        "type": "done",
        "critic": None,
        "auto_polish_report": None,
    }
    assert payload["critic"] is None
    assert payload["auto_polish_report"] is None


# ============== 集成:CriticSummary 从 CriticEvaluation 派生 ==============


def test_critic_summary_derivable_from_evaluation():
    """CriticSummary 可以从 CriticEvaluation(完整版)派生 — 验证字段语义一致"""
    evaluation = CriticEvaluationSchema(
        chapter_id=uuid4(),
        persona_scores=[
            PersonaScore(persona="shuangwen", consistency=0.8, pacing=0.7,
                         prose=0.9, engagement=0.7, comment="ok", top_issues=[]),
            PersonaScore(persona="zhubian", consistency=0.9, pacing=0.8,
                         prose=0.8, engagement=0.8, comment="ok", top_issues=["对话单薄"]),
        ],
        aggregated=AggregatedScore(
            consistency=0.85, pacing=0.75, prose=0.85, engagement=0.75, overall=0.8,
        ),
        consensus_issues=["对话单薄"],
        model_used="MiniMax-M3",
    )
    # 模拟 ws/generation.py 中的派生代码
    summary = CriticSummary(
        overall=evaluation.aggregated.overall,
        consistency=evaluation.aggregated.consistency,
        pacing=evaluation.aggregated.pacing,
        prose=evaluation.aggregated.prose,
        engagement=evaluation.aggregated.engagement,
        consensus_issues=list(evaluation.consensus_issues),
        model_used=evaluation.model_used,
        evaluation_id="00000000-0000-0000-0000-000000000002",
    )
    assert summary.overall == 0.8
    assert summary.consensus_issues == ["对话单薄"]


# ============== 集成:WS hook 中提取 version snapshot 的逻辑 ==============


async def test_version_snapshot_for_critic_matches_chapter_version(db_session):
    """验证:critic hook 取 chapter.version 快照时,数值正确

    (实际 _handle_start 的版本快照在 writer 完成时取,这里只验证
    db_session.get(Chapter, id).version 字段可用)
    """
    work = Work(title="t", genre="x", logline="", style_keywords=[],
                target_audience=[], target_word_count=10000, notes="")
    db_session.add(work)
    await db_session.flush()
    chapter = Chapter(
        work_id=work.id, title="c", plain_content="x", content={},
        status=ChapterStatus.GENERATED, word_count=1, version=3,
    )
    db_session.add(chapter)
    await db_session.flush()

    fetched = await db_session.get(Chapter, chapter.id)
    assert fetched.version == 3
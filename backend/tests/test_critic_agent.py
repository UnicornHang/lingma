"""Critic Agent Prompt 模板 & 真实 LLM 校验测试

覆盖:
- 5 persona 关键词在 system prompt 中存在
- 禁 thinking aloud / 禁 markdown fence
- user prompt 长文截断 (6000 字上限)
- user prompt 部分 persona
- aggregated 平均计算正确
- consensus_issues 去重
- agent.evaluate() 在 mock 模式下不抛异常
- agent.evaluate() 对非法 JSON 容错
- agent.evaluate() 对合法 JSON 强 schema 校验通过
- 分数范围 0-1 校验
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.critic_agent import CriticAgent
from app.prompts.critic_prompts import (
    ALL_PERSONAS,
    build_critic_system_prompt,
    build_critic_user_prompt,
)
from app.schemas.critic import (
    AggregatedScore,
    CriticEvaluation,
    PersonaScore,
)


@pytest.fixture(autouse=True)
def _stub_tracking_ledger(monkeypatch):
    """评审测试不连账本库，知情范围走空 payload。"""

    async def _fake_get_or_create(_db, _work_id):
        return SimpleNamespace(payload={})

    monkeypatch.setattr(
        "app.agents.critic_agent.tracking_service.get_or_create_tracking",
        _fake_get_or_create,
    )


# ============== Prompt 模板测试 ==============


def test_critic_system_prompt_lists_five_personas_by_default():
    sys_p = build_critic_system_prompt(ALL_PERSONAS)
    for persona in ("shuangwen", "wenqing", "kaoju", "mengxin", "zhubian"):
        assert persona in sys_p


def test_critic_system_prompt_forbids_thinking_aloud():
    sys_p = build_critic_system_prompt(ALL_PERSONAS)
    assert "禁止 thinking aloud" in sys_p


def test_critic_system_prompt_forbids_markdown_fence():
    sys_p = build_critic_system_prompt(ALL_PERSONAS)
    assert "markdown fence" in sys_p


def test_critic_user_prompt_truncates_long_content():
    work = SimpleNamespace(
        title="测试作品", genre="fantasy", logline="",
        style_keywords=[], target_audience=[], notes="",
    )
    long_content = "字" * 10_000
    user_p = build_critic_user_prompt(
        work=work,
        chapter_title="第1章",
        chapter_summary="简介",
        content=long_content,
        personas=ALL_PERSONAS,
    )
    # 应出现省略标记
    assert "后续省略" in user_p
    # 注入 prompt 的正文应不超过 6000 字 + 省略标记
    # 取出正文段落后的字符数应该 < 6500
    assert user_p.count("字") <= 6500


def test_critic_user_prompt_with_explicit_personas():
    work = SimpleNamespace(
        title="测试作品", genre="xianxia", logline="",
        style_keywords=["热血"], target_audience=["男频"], notes="",
    )
    user_p = build_critic_user_prompt(
        work=work,
        chapter_title="第1章",
        chapter_summary="",
        content="一段正文",
        personas=["shuangwen", "zhubian"],
    )
    # 只列 2 个 persona
    assert "shuangwen" in user_p
    assert "zhubian" in user_p
    assert "wenqing" not in user_p.split("【待评正文】")[0]


def test_critic_user_prompt_includes_knowledge_brief():
    work = SimpleNamespace(
        title="测试作品", genre="fantasy", logline="",
        style_keywords=[], target_audience=[], notes="",
    )
    user_p = build_critic_user_prompt(
        work=work,
        chapter_title="第1章",
        chapter_summary="",
        content="一段正文",
        personas=["kaoju"],
        knowledge_brief="【知情范围】林墨未知：凶手是哥哥",
    )
    assert "知情范围" in user_p
    assert "凶手是哥哥" in user_p


# ============== 聚合逻辑测试 ==============


def test_critic_aggregate_score_means():
    from app.agents.critic_agent import _aggregate_scores

    scores = [
        PersonaScore(persona="shuangwen", consistency=0.8, pacing=0.7, prose=0.6, engagement=0.9),
        PersonaScore(persona="wenqing", consistency=0.7, pacing=0.6, prose=0.9, engagement=0.8),
    ]
    agg = _aggregate_scores(scores)
    assert isinstance(agg, AggregatedScore)
    # consistency: (0.8+0.7)/2 = 0.75
    assert abs(agg.consistency - 0.75) < 0.01
    # overall = (consistency + pacing + prose + engagement) / 4
    expected_overall = (0.75 + 0.65 + 0.75 + 0.85) / 4
    assert abs(agg.overall - expected_overall) < 0.01


def test_critic_aggregate_score_empty_returns_neutral():
    from app.agents.critic_agent import _aggregate_scores

    agg = _aggregate_scores([])
    assert agg.overall == 0.5
    assert agg.consistency == 0.5


def test_critic_consensus_issues_dedup():
    from app.agents.critic_agent import _extract_consensus_issues

    scores = [
        PersonaScore(
            persona="shuangwen", consistency=0.7, pacing=0.7, prose=0.7, engagement=0.7,
            top_issues=["节奏偏慢", "主角对话生硬"],
        ),
        PersonaScore(
            persona="wenqing", consistency=0.7, pacing=0.7, prose=0.7, engagement=0.7,
            top_issues=["节奏偏慢", "意象不足"],
        ),
        PersonaScore(
            persona="kaoju", consistency=0.7, pacing=0.7, prose=0.7, engagement=0.7,
            top_issues=["设定有 bug", "节奏偏慢"],
        ),
    ]
    consensus = _extract_consensus_issues(scores)
    # "节奏偏慢" 出现 3 次(≥2),应进入 consensus
    assert "节奏偏慢" in consensus
    # "设定有 bug"、"主角对话生硬"、"意象不足" 各 1 次,不应进入
    assert "设定有 bug" not in consensus


# ============== Agent 真实方法测试 ==============


def _stub_work() -> SimpleNamespace:
    return SimpleNamespace(
        title="测试作品",
        genre="fantasy",
        logline="一句话",
        style_keywords=["玄幻"],
        target_audience=["男频"],
        notes="",
        id=uuid4(),
    )


def _mock_db(work: SimpleNamespace):
    """Mock db,db.execute 返回 work(用于 _load_work);第二次调用返回空 list
    (用于 resolve_provider_config 的 scalars().all())。"""
    call_log = []

    def make_exec():
        idx = len(call_log)
        call_log.append(idx)
        m = AsyncMock()
        if idx == 0:
            m.scalar_one_or_none = lambda: work
        else:
            scalars_mock = AsyncMock()
            scalars_mock.all = lambda: []
            m.scalars = lambda: scalars_mock
        return m

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=lambda *a, **kw: make_exec())
    return db


class _MockLLMService:
    def __init__(self, content):
        self._content = content

    async def chat(self, req, cfg):
        if self._content is None:
            return SimpleNamespace(content="非 JSON 输出", model="mock")
        return SimpleNamespace(content=self._content, model="mock")


def _patch_llm(content):
    from unittest.mock import patch
    return patch(
        "app.agents.critic_agent.get_llm_service",
        return_value=_MockLLMService(content),
    )


@pytest.mark.asyncio
async def test_critic_evaluate_handles_missing_work():
    db = AsyncMock()

    def make_exec():
        m = AsyncMock()
        m.scalar_one_or_none = lambda: None
        return m

    db.execute = AsyncMock(side_effect=lambda *a, **kw: make_exec())

    agent = CriticAgent()
    eval_, model_used = await agent.evaluate(
        db, work_id=uuid4(), content="一段正文"
    )
    assert isinstance(eval_, CriticEvaluation)
    assert eval_.persona_scores == []
    assert model_used == "mock"


@pytest.mark.asyncio
async def test_critic_evaluate_handles_no_content():
    db = _mock_db(_stub_work())
    agent = CriticAgent()
    eval_, _ = await agent.evaluate(db, work_id=uuid4())  # 无 content 无 chapter_id
    assert eval_.persona_scores == []
    assert eval_.aggregated.overall == 0.5


@pytest.mark.asyncio
async def test_critic_evaluate_returns_empty_when_no_json():
    db = _mock_db(_stub_work())
    with _patch_llm(None):
        agent = CriticAgent()
        eval_, _ = await agent.evaluate(db, work_id=uuid4(), content="一段正文")
    assert eval_.persona_scores == []
    assert eval_.model_used == "mock"


@pytest.mark.asyncio
async def test_critic_evaluate_rejects_invalid_json():
    db = _mock_db(_stub_work())
    with _patch_llm("不是 JSON {{{"):
        agent = CriticAgent()
        eval_, _ = await agent.evaluate(db, work_id=uuid4(), content="一段正文")
    assert eval_.persona_scores == []


@pytest.mark.asyncio
async def test_critic_evaluate_validates_llm_json_with_five_personas():
    valid_json = """{
        "persona_scores": [
            {"persona": "shuangwen", "consistency": 0.8, "pacing": 0.7, "prose": 0.6, "engagement": 0.9, "comment": "爽点够", "top_issues": ["节奏偏慢"]},
            {"persona": "wenqing", "consistency": 0.7, "pacing": 0.6, "prose": 0.9, "engagement": 0.8, "comment": "文笔好", "top_issues": ["节奏偏慢"]},
            {"persona": "kaoju", "consistency": 0.6, "pacing": 0.7, "prose": 0.7, "engagement": 0.7, "comment": "设定有 bug", "top_issues": ["设定有 bug"]},
            {"persona": "mengxin", "consistency": 0.8, "pacing": 0.8, "prose": 0.7, "engagement": 0.8, "comment": "可读", "top_issues": []},
            {"persona": "zhubian", "consistency": 0.7, "pacing": 0.7, "prose": 0.7, "engagement": 0.7, "comment": "结构完整", "top_issues": []}
        ]
    }"""
    db = _mock_db(_stub_work())
    with _patch_llm(valid_json):
        agent = CriticAgent()
        eval_, _ = await agent.evaluate(db, work_id=uuid4(), content="一段正文")
    assert len(eval_.persona_scores) == 5
    # "节奏偏慢" 出现 2 次 → consensus
    assert "节奏偏慢" in eval_.consensus_issues


@pytest.mark.asyncio
async def test_critic_evaluate_validates_score_range():
    """分数超范围时该条 persona 校验失败,被丢弃。"""
    invalid_json = """{
        "persona_scores": [
            {"persona": "shuangwen", "consistency": 1.5, "pacing": 0.7, "prose": 0.7, "engagement": 0.7},
            {"persona": "wenqing", "consistency": 0.7, "pacing": 0.7, "prose": 0.7, "engagement": 0.7}
        ]
    }"""
    db = _mock_db(_stub_work())
    with _patch_llm(invalid_json):
        agent = CriticAgent()
        eval_, _ = await agent.evaluate(db, work_id=uuid4(), content="一段正文")
    # 第一条因 consistency=1.5 超 1.0 上限被丢弃,只剩第二条
    assert len(eval_.persona_scores) == 1
    assert eval_.persona_scores[0].persona == "wenqing"


@pytest.mark.asyncio
async def test_critic_evaluate_rejects_unrequested_persona():
    """LLM 返回了未在请求中的 persona 应被丢弃。"""
    json_with_extra = """{
        "persona_scores": [
            {"persona": "shuangwen", "consistency": 0.7, "pacing": 0.7, "prose": 0.7, "engagement": 0.7},
            {"persona": "fake_persona", "consistency": 0.7, "pacing": 0.7, "prose": 0.7, "engagement": 0.7}
        ]
    }"""
    db = _mock_db(_stub_work())
    with _patch_llm(json_with_extra):
        agent = CriticAgent()
        eval_, _ = await agent.evaluate(
            db, work_id=uuid4(), content="一段正文",
            personas=["shuangwen"],  # 只请求 1 个
        )
    assert len(eval_.persona_scores) == 1
    assert eval_.persona_scores[0].persona == "shuangwen"


@pytest.mark.asyncio
async def test_critic_evaluate_handles_markdown_fence():
    fenced = """以下为 JSON:
```json
{"persona_scores": [
    {"persona": "shuangwen", "consistency": 0.7, "pacing": 0.7, "prose": 0.7, "engagement": 0.7}
]}
```
"""
    db = _mock_db(_stub_work())
    with _patch_llm(fenced):
        agent = CriticAgent()
        eval_, _ = await agent.evaluate(
            db, work_id=uuid4(), content="一段正文", personas=["shuangwen"],
        )
    assert len(eval_.persona_scores) == 1
"""[P3.3] _run_auto_rewrite_loop 测试。

覆盖:
- 初始分已达标 → 跳过(无 iterations,skipped_reason=score_above_threshold)
- max=0 → 跳过(skipped_reason=disabled)
- 多轮迭代到达标
- 达到 max_retries 仍未达标 → 退出循环
- rewrite_for_critic 抛异常 → 优雅退出(graceful)
- per-request threshold 覆盖 env 默认

策略:
- patch `_session_factory` 传 mock context manager
- patch `RewriteAgent().rewrite_for_critic` 返回修改后的内容
- patch `CriticAgent().evaluate` 返回 (CriticEvaluation, model_name)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws.generation import _run_auto_rewrite_loop


# ============== Helpers ==============


def make_summary(overall: float, issues: list[str] | None = None) -> dict:
    """构造 CriticSummary dict(WS done 事件形态)。"""
    return {
        "overall": overall,
        "consistency": overall,
        "pacing": overall,
        "prose": overall,
        "engagement": overall,
        "consensus_issues": issues or [],
        "model_used": "mock",
    }


def make_evaluation(overall: float):
    """构造 CriticAgent().evaluate() 返回元组的第一个元素。"""
    evaluation = MagicMock()
    evaluation.aggregated.overall = overall
    evaluation.aggregated.consistency = overall
    evaluation.aggregated.pacing = overall
    evaluation.aggregated.prose = overall
    evaluation.aggregated.engagement = overall
    evaluation.persona_scores = []
    evaluation.consensus_issues = []
    return evaluation


def make_session_factory():
    """构造一个 mock session factory —— 返回 dummy AsyncSession(不真连 DB)。

    测试只关心 orchestrator 调度逻辑,不真验证 SQL。
    """
    @asynccontextmanager
    async def _factory():
        # 返回一个 dummy session —— 写操作不真发生
        yield MagicMock(spec=AsyncSession)

    return _factory


# ============== 1. 已达标 → 跳过 ==============


async def test_loop_skips_when_initial_score_above_threshold():
    """初始 overall >= threshold → 立即返回,无 iterations。"""
    content = "原文章节正文..."
    initial = make_summary(overall=0.8, issues=["x"])

    with patch("app.services.llm_service.resolve_provider_config", AsyncMock(return_value=None)):
        content_out, summary_out, report = await _run_auto_rewrite_loop(
            chapter_id=uuid4(),
            work_id=uuid4(),
            initial_content=content,
            initial_summary=initial,
            threshold=0.6,
            max_retries=2,
            cfg=None,
            style_keywords=None,
            _session_factory=make_session_factory(),
        )

    assert content_out == content
    assert summary_out == initial
    assert report["executed"] is False
    assert report["skipped_reason"] == "score_above_threshold"
    assert report["iterations"] == []
    assert report["final_overall"] == 0.8


# ============== 2. max=0 → 跳过 ==============


async def test_loop_skips_when_max_is_zero():
    """max_retries=0 → 不执行任何迭代(per-work/per-request 禁用开关)。

    注意:helper 不区分「disabled」与「no_iterations」,统一用 no_iterations。
    「disabled」语义由调用方(WS generation hook)在调用 helper 之前判断。
    """
    with patch("app.services.llm_service.resolve_provider_config", AsyncMock(return_value=None)):
        initial = make_summary(overall=0.4)

        _, _, report = await _run_auto_rewrite_loop(
            chapter_id=uuid4(),
            work_id=uuid4(),
            initial_content="内容",
            initial_summary=initial,
            threshold=0.6,
            max_retries=0,
            cfg=None,
            style_keywords=None,
            _session_factory=make_session_factory(),
        )

    assert report["executed"] is False
    assert report["iterations"] == []
    assert report["skipped_reason"] in ("disabled", "no_iterations")


# ============== 3. 迭代到达标 ==============


async def test_loop_iterates_until_threshold_met():
    """第 1 次改写后分仍低(0.5)→ 第 2 次改写后达 0.7 → break。"""
    call_count = {"rewrite": 0, "evaluate": 0}

    async def fake_rewrite(*args, **kwargs):
        call_count["rewrite"] += 1
        # 每次返回不同的改写内容(避免 no_change 提前 break)
        return f"改写后内容 #{call_count['rewrite']}"

    async def fake_evaluate(db, **kwargs):
        call_count["evaluate"] += 1
        # 第 1 次:0.5 (未达标);第 2 次:0.7 (达标)
        score = 0.5 if call_count["evaluate"] == 1 else 0.7
        return make_evaluation(score), "mock"

    with patch("app.agents.rewrite_agent.RewriteAgent") as MockRW, \
         patch("app.agents.critic_agent.CriticAgent") as MockCrit, \
         patch("app.services.llm_service.resolve_provider_config", AsyncMock(return_value=None)):

        MockRW.return_value.rewrite_for_critic = AsyncMock(side_effect=fake_rewrite)
        MockCrit.return_value.evaluate = AsyncMock(side_effect=fake_evaluate)

        _, _, report = await _run_auto_rewrite_loop(
            chapter_id=uuid4(),
            work_id=uuid4(),
            initial_content="原文",
            initial_summary=make_summary(overall=0.4),
            threshold=0.6,
            max_retries=3,  # 给到 3,验证不会跑满 3 次
            cfg=None,
            style_keywords=None,
            _session_factory=make_session_factory(),
        )

    assert call_count["rewrite"] == 2  # 跑了 2 次(达标 break)
    assert call_count["evaluate"] == 2  # 每次改写后都跑 critic
    assert report["executed"] is True
    assert report["improved"] is True
    assert report["final_overall"] == 0.7
    assert len(report["iterations"]) == 2
    # 第 2 次 outcome 应是 success
    assert report["iterations"][1]["outcome"] == "success"
    assert report["iterations"][1]["post_overall"] == 0.7


# ============== 4. 达到 max 仍未达标 ==============


async def test_loop_caps_at_max_retries():
    """3 次改写仍都 < threshold → 跑满 max_retries 后退出,improved=False。"""
    async def fake_rewrite(*args, **kwargs):
        # 每次返回不同内容(避免 no_change 提前 break)
        call_count["n"] = call_count.get("n", 0) + 1
        return f"改写后内容 #{call_count['n']}"

    async def fake_evaluate(db, **kwargs):
        # 每次都给 0.5 (始终未达标)
        return make_evaluation(0.5), "mock"

    call_count = {}

    with patch("app.agents.rewrite_agent.RewriteAgent") as MockRW, \
         patch("app.agents.critic_agent.CriticAgent") as MockCrit, \
         patch("app.services.llm_service.resolve_provider_config", AsyncMock(return_value=None)):

        MockRW.return_value.rewrite_for_critic = AsyncMock(side_effect=fake_rewrite)
        MockCrit.return_value.evaluate = AsyncMock(side_effect=fake_evaluate)

        _, _, report = await _run_auto_rewrite_loop(
            chapter_id=uuid4(),
            work_id=uuid4(),
            initial_content="原文",
            initial_summary=make_summary(overall=0.4),
            threshold=0.7,  # 严格阈值,0.5 永远不达标
            max_retries=3,
            cfg=None,
            style_keywords=None,
            _session_factory=make_session_factory(),
        )

    assert len(report["iterations"]) == 3
    assert report["improved"] is False
    assert report["final_overall"] == 0.5
    # 每次 outcome 都是 below_threshold
    for it in report["iterations"]:
        assert it["outcome"] == "below_threshold"


# ============== 5. rewrite 抛异常 → graceful 退出 ==============


async def test_loop_handles_rewrite_exception_gracefully():
    """rewrite_for_critic 抛异常 → 记录 outcome=error + break,最终 summary 回退到 initial。"""
    async def fake_rewrite(*args, **kwargs):
        raise RuntimeError("LLM 调用失败")

    with patch("app.agents.rewrite_agent.RewriteAgent") as MockRW, \
         patch("app.agents.critic_agent.CriticAgent") as MockCrit, \
         patch("app.services.llm_service.resolve_provider_config", AsyncMock(return_value=None)):
        MockRW.return_value.rewrite_for_critic = AsyncMock(side_effect=fake_rewrite)
        MockCrit.return_value.evaluate = AsyncMock()  # 不应被调用

        initial = make_summary(overall=0.4)
        content_out, summary_out, report = await _run_auto_rewrite_loop(
            chapter_id=uuid4(),
            work_id=uuid4(),
            initial_content="原文",
            initial_summary=initial,
            threshold=0.6,
            max_retries=3,
            cfg=None,
            style_keywords=None,
            _session_factory=make_session_factory(),
        )

    # 内容未改写(回退原文),summary 回退 initial
    assert content_out == "原文"
    assert summary_out == initial
    # 1 次失败的 iteration,后续未跑
    assert len(report["iterations"]) == 1
    assert report["iterations"][0]["outcome"] == "error"
    assert "LLM 调用失败" in report["iterations"][0]["error"]
    # CriticAgent 不应被调用
    MockCrit.return_value.evaluate.assert_not_called()


# ============== 6. per-request threshold 覆盖 env 默认 ==============


async def test_per_request_threshold_overrides_env_default():
    """threshold 参数(0.5)覆盖 env 默认(0.6): 0.55 应判定为达标 → 不改写。"""
    initial = make_summary(overall=0.55)
    content = "原文"

    with patch("app.services.llm_service.resolve_provider_config", AsyncMock(return_value=None)):
        content_out, _, report = await _run_auto_rewrite_loop(
            chapter_id=uuid4(),
            work_id=uuid4(),
            initial_content=content,
            initial_summary=initial,
            threshold=0.5,  # per-request: 比 0.55 默认 0.6 低 → 视为达标
            max_retries=1,
            cfg=None,
            style_keywords=None,
            _session_factory=make_session_factory(),
        )

    assert content_out == content
    assert report["skipped_reason"] == "score_above_threshold"
    assert report["threshold"] == 0.5
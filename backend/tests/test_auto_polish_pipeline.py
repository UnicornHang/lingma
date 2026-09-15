"""提交 C — 自动去味流水线测试

覆盖:
- 干净文本:无 blocking → 不重写
- 含 blocking:触发 LLM 重写
- LLM 失败:保留原文 + 报告 rewrite_error
- LLM 输出过短:视为没救,保留原文
- advisory 不触发重写
- pre_findings 至多 5 条
- cfg=None 时走 mock LLM 路径
"""
from __future__ import annotations

import pytest

from app.api.ws.generation import _auto_polish_if_needed
from app.services.llm_service import LLMError


# ==================== 干净文本 ====================


@pytest.mark.asyncio
async def test_empty_text_skips():
    """空文本 → 跳过,report=None"""
    text, report = await _auto_polish_if_needed("", cfg=None, style_keywords=None)
    assert text == ""
    assert report is None


@pytest.mark.asyncio
async def test_whitespace_only_skips():
    text, report = await _auto_polish_if_needed("   \n\n  ", cfg=None, style_keywords=None)
    assert text == "   \n\n  "
    assert report is None


@pytest.mark.asyncio
async def test_clean_text_no_blocking_no_rewrite():
    """干净文本:无 blocking → 不重写,rewrite_attempted=False"""
    clean = (
        "韩立睁开眼,只见屋内一片昏暗,油灯的火焰跳了跳,随即熄灭。"
        "他从床沿坐起身,耳边传来远处鸡鸣。推开门,冷风灌入,山林寂静。"
    )
    text, report = await _auto_polish_if_needed(clean, cfg=None, style_keywords=None)
    assert text == clean  # 原文不变
    assert report is not None
    assert report["rewrite_attempted"] is False
    assert report["blocking_count"] == 0
    assert report["final_blocking"] is None


# ==================== blocking 触发重写 ====================


@pytest.mark.asyncio
async def test_blocking_triggers_rewrite():
    """含 blocking 文本(cfg=None → mock LLM 路径)"""
    # 故意构造一个含 not-is-reverse 的句子,确保命中至少 1 条 blocking
    dirty = "他咬牙冲上前,是愤怒,不是恐惧。刀光剑影中,血溅当场。"
    text, report = await _auto_polish_if_needed(
        dirty, cfg=None, style_keywords=["热血"], auto_rewrite=True
    )
    assert report is not None
    assert report["blocking_count"] >= 1
    assert report["rewrite_attempted"] is True
    # mock LLM 返回时也应通过验收
    # mock_chat 的输出是 messages 内容 echo,不会 < 50 字
    assert report["rewrite_succeeded"] is True


@pytest.mark.asyncio
async def test_blocking_final_blocking_recorded():
    """改写后再跑检测,final_blocking 应被记录"""
    dirty = "他咬牙冲上前,是愤怒,不是恐惧。刀光剑影中,血溅当场。"
    text, report = await _auto_polish_if_needed(
        dirty, cfg=None, style_keywords=None, auto_rewrite=True
    )
    assert report["final_blocking"] is not None
    # 是整数
    assert isinstance(report["final_blocking"], int)


# ==================== 失败兜底 ====================


@pytest.mark.asyncio
async def test_llm_failure_keeps_original():
    """LLM 抛错 → 保留原文 + report.rewrite_error"""
    from unittest.mock import AsyncMock, patch

    # Patch get_llm_service 返回的 mock 的 chat 方法
    from app.api.ws import generation
    fake_llm = AsyncMock()
    fake_llm.chat.side_effect = LLMError("simulated upstream failure")

    with patch.object(generation, "get_llm_service", return_value=fake_llm):
        dirty = "他咬牙冲上前,是愤怒,不是恐惧。"
        text, report = await _auto_polish_if_needed(
            dirty, cfg=None, style_keywords=None, auto_rewrite=True
        )
    assert text == dirty  # 原文未变
    assert report is not None
    assert report["rewrite_attempted"] is True
    assert report["rewrite_succeeded"] is False
    assert "simulated upstream failure" in report["rewrite_error"]


@pytest.mark.asyncio
async def test_llm_output_too_short_keeps_original():
    """LLM 返回过短(<50 字)→ 视为没救,保留原文"""
    from unittest.mock import AsyncMock, patch

    from app.api.ws import generation
    from app.services.llm_service import LLMResponse

    fake_llm = AsyncMock()
    fake_resp = LLMResponse(
        content="嗯。",  # < 50 字
        model="mock",
        input_tokens=10,
        output_tokens=2,
        cost_usd=0.0,
        raw={},
    )
    fake_llm.chat.return_value = fake_resp

    with patch.object(generation, "get_llm_service", return_value=fake_llm):
        dirty = "他咬牙冲上前,是愤怒,不是恐惧。"
        text, report = await _auto_polish_if_needed(
            dirty, cfg=None, style_keywords=None, auto_rewrite=True
        )
    assert text == dirty
    assert report["rewrite_attempted"] is True
    assert report["rewrite_succeeded"] is False
    assert "output_too_short" in report["rewrite_error"]


# ==================== advisory 不触发 ====================


@pytest.mark.asyncio
async def test_only_advisory_no_rewrite():
    """只有 advisory(无 blocking)→ 不触发重写"""
    # micro-action-tic 阈值是 5 个"了+下/阵/圈...",advisory 级
    # 这里构造一个含 ~6 个这种模式的段落
    advisory_only = (
        "他点了一下头,她看了一眼远方,他叹了一口气。"
        "又点了一下头,她又看了一眼远方。"
        "再点了一下头,她最后看了一眼天边。"
    )
    text, report = await _auto_polish_if_needed(
        advisory_only, cfg=None, style_keywords=None
    )
    # 不管有没有 advisory,blocking_count 应为 0 → 不触发
    assert report["blocking_count"] == 0
    assert report["rewrite_attempted"] is False


@pytest.mark.asyncio
async def test_blocking_without_auto_rewrite_only_lints():
    """默认不自动润色：有 blocking 也只出检测报告。"""
    dirty = "他咬牙冲上前,是愤怒,不是恐惧。刀光剑影中,血溅当场。"
    text, report = await _auto_polish_if_needed(dirty, cfg=None, style_keywords=None)
    assert text == dirty
    assert report is not None
    assert report["blocking_count"] >= 1
    assert report["rewrite_attempted"] is False


# ==================== pre_findings 上限 ====================


@pytest.mark.asyncio
async def test_pre_findings_capped_at_5():
    """pre_findings 至多 5 条"""
    dirty = "他咬牙冲上前,是愤怒,不是恐惧。刀光剑影中,血溅当场。"
    text, report = await _auto_polish_if_needed(
        dirty, cfg=None, style_keywords=None
    )
    assert len(report["pre_findings"]) <= 5


# ==================== elapsed_ms 字段 ====================


@pytest.mark.asyncio
async def test_report_includes_elapsed_ms():
    text, report = await _auto_polish_if_needed(
        "他咬牙冲上前,是愤怒,不是恐惧。",
        cfg=None,
        style_keywords=None,
    )
    assert "elapsed_ms" in report
    assert isinstance(report["elapsed_ms"], int)
    assert report["elapsed_ms"] >= 0


# ==================== schema 验证 ====================


def test_generate_chapter_request_accepts_auto_polish():
    """GenerateChapterRequest 应接受 auto_polish 与 max_blocking_for_rewrite"""
    from app.schemas.chapter import GenerateChapterRequest

    req = GenerateChapterRequest(auto_polish=False, max_blocking_for_rewrite=3)
    assert req.auto_polish is False
    assert req.max_blocking_for_rewrite == 3


def test_generate_chapter_request_defaults_are_permissive():
    """默认:检测开、自动润色关。"""
    from app.schemas.chapter import GenerateChapterRequest

    req = GenerateChapterRequest()
    assert req.auto_polish is True
    assert req.auto_rewrite is False
    assert req.max_blocking_for_rewrite == 0

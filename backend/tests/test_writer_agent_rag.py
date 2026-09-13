"""Writer Agent RAG 集成单测

覆盖:
- assemble_writer_slots 在 rag_hits 非空时插入「【RAG 向量检索补充】」slot
- assemble_writer_slots 在 rag_hits 为空/None 时跳过 RAG slot
- assemble_writer_slots 的 slot 顺序:RAG 在「出场角色」之后、「上一章摘要」之前
- build_user_prompt 透传 rag_hits(向后兼容 None)
- _search_rag_hits:rag_enabled=False → 返回 [],不调 service
- _search_rag_hits:search 抛异常 → 返回 [],不阻塞
- _search_rag_hits:asyncio.TimeoutError → 返回 []
"""
from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.schemas.rag import RagHit


# ============== Slot 装配测试 ==============


def _stub_work():
    return SimpleNamespace(
        title="测试小说",
        genre=SimpleNamespace(value="玄幻"),
        logline="一句话简介",
        target_audience=["男频"],
        style_keywords=[],
    )


def _stub_chapter():
    return SimpleNamespace(
        title="测试章节",
        summary="本章摘要",
        word_count=3000,
        plain_content="",
        content=None,
        key_events=None,
    )


def _stub_outline():
    return SimpleNamespace(
        title="本章大纲",
        type="chapter",
        summary="大纲摘要",
        beats=["冲突展开", "高潮"],
        characters_involved=["主角"],
        world_refs=["青云山"],
    )


def test_writer_slots_inserts_rag_slot_when_hits_present():
    """rag_hits 非空 → prompt 中应出现【RAG 向量检索补充】。"""
    from app.prompts.writer_slots import assemble_writer_slots

    rag_hits = [
        RagHit(
            target_type="character",
            target_id=str(uuid4()),
            chunk_index=0,
            text="林轩在青云山修炼时偶得一柄灵剑。",
            score=0.12,
            metadata={},
        ),
        RagHit(
            target_type="world",
            target_id=str(uuid4()),
            chunk_index=1,
            text="青云山乃东域第一仙门,灵气充沛。",
            score=0.34,
            metadata={},
        ),
    ]

    assembly = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=_stub_outline(),
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
        rag_hits=rag_hits,
    )

    titles = assembly.slot_titles()
    assert "【RAG 向量检索补充】" in titles
    # 检查位置:在「出场角色」之后、「上一章摘要」之前
    # 由于没传 characters,没有【出场角色】,所以这里只能检查相对顺序
    if "【出场角色】" in titles:
        idx_char = titles.index("【出场角色】")
        idx_rag = titles.index("【RAG 向量检索补充】")
        assert idx_char < idx_rag
    assert "rag_hit_count" in assembly.metadata
    assert assembly.metadata["rag_hit_count"] == 2


def test_writer_slots_renders_rag_hit_lines():
    """RAG slot 内容应包含 score + target_type + 文本前 300 字。"""
    from app.prompts.writer_slots import assemble_writer_slots

    rag_hits = [
        RagHit(
            target_type="character",
            target_id=str(uuid4()),
            chunk_index=0,
            text="角色设定文本。",
            score=0.15,
            metadata={},
        ),
    ]

    assembly = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
        rag_hits=rag_hits,
    )

    user_text = assembly.user_text
    assert "【RAG 向量检索补充】" in user_text
    assert "[character]" in user_text
    assert "score=0.15" in user_text
    assert "角色设定文本" in user_text


def test_writer_slots_skips_rag_slot_when_empty():
    """rag_hits=[] → 不渲染 RAG slot。"""
    from app.prompts.writer_slots import assemble_writer_slots

    assembly = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
        rag_hits=[],
    )

    titles = assembly.slot_titles()
    assert "【RAG 向量检索补充】" not in titles
    assert assembly.metadata["rag_hit_count"] == 0


def test_writer_slots_skips_rag_slot_when_none():
    """rag_hits=None → 不渲染 RAG slot,向后兼容。"""
    from app.prompts.writer_slots import assemble_writer_slots

    assembly = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
        rag_hits=None,
    )

    titles = assembly.slot_titles()
    assert "【RAG 向量检索补充】" not in titles
    assert assembly.metadata["rag_hit_count"] == 0


def test_writer_slots_rag_position_between_characters_and_previous_summary():
    """RAG slot 应在【出场角色】之后、【上一章摘要】之前。"""
    from app.prompts.writer_slots import assemble_writer_slots

    character = SimpleNamespace(
        name="林轩",
        role="主角",
        raw_text="少年修士。",
    )
    rag_hits = [
        RagHit(
            target_type="chapter",
            target_id=str(uuid4()),
            chunk_index=0,
            text="前章摘要。",
            score=0.20,
            metadata={},
        ),
    ]

    assembly = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=[character],
        previous_summary="上一章摘要",
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
        rag_hits=rag_hits,
    )

    titles = assembly.slot_titles()
    idx_char = titles.index("【出场角色】")
    idx_rag = titles.index("【RAG 向量检索补充】")
    idx_prev = titles.index("【上一章摘要】")
    assert idx_char < idx_rag < idx_prev


# ============== build_user_prompt 透传测试 ==============


def test_build_user_prompt_passes_rag_hits_through():
    """build_user_prompt 接受 rag_hits 并把它写入 prompt 文本。"""
    from app.prompts.writer_prompts import build_user_prompt

    rag_hits = [
        RagHit(
            target_type="character",
            target_id=str(uuid4()),
            chunk_index=0,
            text="X 设定。",
            score=0.10,
            metadata={},
        ),
    ]

    prompt = build_user_prompt(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
        rag_hits=rag_hits,
    )
    assert "【RAG 向量检索补充】" in prompt


def test_build_user_prompt_backward_compatible_without_rag():
    """不传 rag_hits → 不渲染 RAG slot,行为与原版一致。"""
    from app.prompts.writer_prompts import build_user_prompt

    prompt = build_user_prompt(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
    )
    assert "【RAG 向量检索补充】" not in prompt


# ============== _search_rag_hits 行为测试 ==============


@pytest.mark.asyncio
async def test_search_rag_hits_disabled_returns_empty(monkeypatch):
    """settings.rag_enabled=False → 返回 [],不调用 service。"""
    from app.config import settings
    from app.agents.writer_agent import _search_rag_hits

    monkeypatch.setattr(settings, "rag_enabled", False)

    mock_svc = AsyncMock()
    monkeypatch.setattr(
        "app.agents.writer_agent.get_rag_service",
        lambda: mock_svc,
    )

    chapter = SimpleNamespace(
        id=uuid4(),
        work_id=uuid4(),
        title="ch1",
        summary="summary",
        plain_content="",
    )
    hits = await _search_rag_hits(AsyncMock(), chapter, None)
    assert hits == []
    mock_svc.search.assert_not_called()


@pytest.mark.asyncio
async def test_search_rag_hits_returns_empty_query(monkeypatch):
    """query 为空(无 outline/summary/title)→ 返回 [],不调 service。"""
    from app.config import settings
    from app.agents.writer_agent import _search_rag_hits

    monkeypatch.setattr(settings, "rag_enabled", True)

    mock_svc = AsyncMock()
    monkeypatch.setattr(
        "app.agents.writer_agent.get_rag_service",
        lambda: mock_svc,
    )

    chapter = SimpleNamespace(
        id=uuid4(),
        work_id=uuid4(),
        title="",
        summary="",
        plain_content="",
    )
    hits = await _search_rag_hits(AsyncMock(), chapter, None)
    assert hits == []
    mock_svc.search.assert_not_called()


@pytest.mark.asyncio
async def test_search_rag_hits_returns_results(monkeypatch):
    """正常路径 → 返回 hits。"""
    from app.config import settings
    from app.agents.writer_agent import _search_rag_hits

    monkeypatch.setattr(settings, "rag_enabled", True)

    expected = [
        RagHit(
            target_type="character",
            target_id=str(uuid4()),
            chunk_index=0,
            text="命中。",
            score=0.10,
            metadata={},
        ),
    ]

    mock_svc = AsyncMock()
    mock_svc.search = AsyncMock(return_value=expected)
    monkeypatch.setattr(
        "app.agents.writer_agent.get_rag_service",
        lambda: mock_svc,
    )

    chapter = SimpleNamespace(
        id=uuid4(),
        work_id=uuid4(),
        title="ch1",
        summary="summary",
        plain_content="",
    )
    hits = await _search_rag_hits(AsyncMock(), chapter, None)
    assert hits == expected
    mock_svc.search.assert_called_once()


@pytest.mark.asyncio
async def test_search_rag_hits_handles_exception(monkeypatch, caplog):
    """search 抛异常 → 返回 [],不阻塞。"""
    from app.config import settings
    from app.agents.writer_agent import _search_rag_hits

    monkeypatch.setattr(settings, "rag_enabled", True)

    mock_svc = AsyncMock()
    mock_svc.search = AsyncMock(side_effect=RuntimeError("vector store down"))
    monkeypatch.setattr(
        "app.agents.writer_agent.get_rag_service",
        lambda: mock_svc,
    )

    chapter = SimpleNamespace(
        id=uuid4(),
        work_id=uuid4(),
        title="ch1",
        summary="summary",
        plain_content="",
    )

    with caplog.at_level(logging.WARNING):
        hits = await _search_rag_hits(AsyncMock(), chapter, None)
    assert hits == []
    # 应有 warning log
    assert any("RAG" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_search_rag_hits_handles_timeout(monkeypatch, caplog):
    """search 超时 → 返回 [],不阻塞。"""
    from app.config import settings
    from app.agents.writer_agent import _search_rag_hits

    monkeypatch.setattr(settings, "rag_enabled", True)

    async def slow_search(*args, **kwargs):
        await asyncio.sleep(5)  # 超过 timeout
        return []

    mock_svc = AsyncMock()
    mock_svc.search = slow_search
    monkeypatch.setattr(
        "app.agents.writer_agent.get_rag_service",
        lambda: mock_svc,
    )

    chapter = SimpleNamespace(
        id=uuid4(),
        work_id=uuid4(),
        title="ch1",
        summary="summary",
        plain_content="",
    )

    with caplog.at_level(logging.WARNING):
        hits = await _search_rag_hits(AsyncMock(), chapter, None, timeout_s=0.1)
    assert hits == []


@pytest.mark.asyncio
async def test_search_rag_hits_uses_outline_summary_in_query(monkeypatch):
    """query 应包含 outline.summary + chapter.summary + chapter.title。"""
    from app.config import settings
    from app.agents.writer_agent import _search_rag_hits

    monkeypatch.setattr(settings, "rag_enabled", True)

    captured: dict = {}

    async def fake_search(work_id, query, **kwargs):
        captured["work_id"] = work_id
        captured["query"] = query
        captured["kwargs"] = kwargs
        return []

    mock_svc = AsyncMock()
    mock_svc.search = fake_search
    monkeypatch.setattr(
        "app.agents.writer_agent.get_rag_service",
        lambda: mock_svc,
    )

    work_id = uuid4()
    chapter = SimpleNamespace(
        id=uuid4(),
        work_id=work_id,
        title="大战",
        summary="两大高手对决",
        plain_content="",
    )
    outline = SimpleNamespace(summary="林轩挑战剑宗宗主")
    await _search_rag_hits(AsyncMock(), chapter, outline)
    assert "林轩挑战剑宗宗主" in captured["query"]
    assert "两大高手对决" in captured["query"]
    assert "大战" in captured["query"]
"""Orchestrator 预填（preflight）单元测试

覆盖:
- 3 个 skip 判定(_has_outline / _has_world_bible / _has_characters)
- 3 stage 在空 work 时全部跑
- 已有数据时对应 stage skip
- 异常隔离(stage 抛错 → 后续 stage 继续)
- on_progress 回调被正确调用
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.preflight import (
    _has_characters,
    _has_outline,
    _has_world_bible,
    run_chapter_prefill,
)


# ============== Fixtures ==============


@pytest.fixture
async def db():
    from app.db.session import async_session_factory
    from app.models.character import Character
    from app.models.outline import OutlineNode
    from app.models.work import Work
    from app.models.world import WorldBible
    from sqlalchemy import delete as sa_delete

    async with async_session_factory() as session:
        yield session
        # 清理依赖表(按 FK 反向)
        await session.execute(sa_delete(OutlineNode))
        await session.execute(sa_delete(Character))
        await session.execute(sa_delete(WorldBible))
        await session.execute(sa_delete(Work))
        await session.commit()


@pytest.fixture
async def work(db: AsyncSession):
    """创建一个空白 work 供测试用。"""
    from app.models.work import Genre, Work, WorkStatus

    w = Work(
        id=uuid4(),
        title="测试作品",
        genre=Genre.FANTASY,
        target_word_count=100000,
        logline="一个测试作品",
        style_keywords=[],
        target_audience=["不限"],
        status=WorkStatus.DRAFT,
        word_count=0,
        settings={},
    )
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


# ============== Skip 判定函数 ==============


async def test_has_outline_empty_returns_false(db: db, work):
    assert await _has_outline(db, work.id) is False


async def test_has_outline_with_volume_returns_true(db: db, work):
    from app.models.outline import OutlineNode, OutlineNodeType

    node = OutlineNode(
        work_id=work.id,
        type=OutlineNodeType.VOLUME,
        title="第一卷",
        summary="",
        beats=[],
        characters_involved=[],
        world_refs=[],
        target_word_count=30000,
        order=0,
    )
    db.add(node)
    await db.commit()
    assert await _has_outline(db, work.id) is True


async def test_has_outline_only_beats_returns_false(db: db, work):
    """只有 beat 节点不算大纲(必须有 volume)。"""
    from app.models.outline import OutlineNode, OutlineNodeType

    node = OutlineNode(
        work_id=work.id,
        type=OutlineNodeType.BEAT,
        title="开场",
        summary="",
        beats=[],
        characters_involved=[],
        world_refs=[],
        target_word_count=1000,
        order=0,
    )
    db.add(node)
    await db.commit()
    assert await _has_outline(db, work.id) is False


async def test_has_world_bible_empty_returns_false(db: db, work):
    assert await _has_world_bible(db, work.id) is False


async def test_has_world_bible_with_raw_text_returns_true(db: db, work):
    from app.models.world import WorldBible

    wb = WorldBible(work_id=work.id, raw_text="这是一个世界", is_indexed=False)
    db.add(wb)
    await db.commit()
    assert await _has_world_bible(db, work.id) is True


async def test_has_world_bible_with_dimensions_returns_true(db: db, work):
    from app.models.world import WorldBible

    wb = WorldBible(
        work_id=work.id,
        raw_text="",
        factions=["修仙界"],
        is_indexed=False,
    )
    db.add(wb)
    await db.commit()
    assert await _has_world_bible(db, work.id) is True


async def test_has_world_bible_empty_dim_returns_false(db: db, work):
    from app.models.world import WorldBible

    wb = WorldBible(work_id=work.id, raw_text="", is_indexed=False)
    db.add(wb)
    await db.commit()
    assert await _has_world_bible(db, work.id) is False


async def test_has_characters_empty_returns_false(db: db, work):
    assert await _has_characters(db, work.id) is False


async def test_has_characters_with_one_returns_true(db: db, work):
    from app.models.character import Character

    c = Character(
        work_id=work.id,
        name="主角",
        role="protagonist",
        basic_info={},
        personality={},
        backstory={},
        raw_text="",
    )
    db.add(c)
    await db.commit()
    assert await _has_characters(db, work.id) is True


# ============== run_chapter_prefill: 空 work 全跑 ==============


async def test_prefill_empty_work_runs_all_three_stages(db: db, work):
    """空 work → 3 个 stage 都跑(返回 status != skipped)。"""
    events: list[dict] = []

    async def on_progress(payload: dict):
        events.append(payload)

    # Mock 三个 agent 让其立即返回(避免真实 LLM)
    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        mock_plot_inst = MockPlot.return_value
        mock_plot_inst.generate_outline = AsyncMock(return_value=("plot_result", "mock"))

        mock_world_inst = MockWorld.return_value
        mock_world_inst.suggest = AsyncMock(return_value=("wb_result", "mock", ""))

        mock_char_inst = MockChar.return_value
        mock_char_inst.suggest = AsyncMock(return_value=([], "mock", ""))

        result = await run_chapter_prefill(db, work.id, on_progress=on_progress)

    assert result["plot"]["status"] == "done"
    assert result["world"]["status"] == "done"
    assert result["character"]["status"] == "done"

    # 进度事件:每 stage 至少 running + done
    stages_seen = {e["stage"] for e in events if e["status"] in ("running", "done")}
    assert stages_seen == {"plot", "world", "character"}


# ============== 已有数据 → skip ==============


async def test_prefill_with_outline_skips_plot_only(db: db, work):
    from app.models.outline import OutlineNode, OutlineNodeType

    node = OutlineNode(
        work_id=work.id,
        type=OutlineNodeType.VOLUME,
        title="第一卷",
        summary="",
        beats=[],
        characters_involved=[],
        world_refs=[],
        target_word_count=30000,
        order=0,
    )
    db.add(node)
    await db.commit()

    events: list[dict] = []

    async def on_progress(payload: dict):
        events.append(payload)

    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock()
        MockWorld.return_value.suggest = AsyncMock(return_value=("wb", "mock", ""))
        MockChar.return_value.suggest = AsyncMock(return_value=([], "mock", ""))

        result = await run_chapter_prefill(db, work.id, on_progress=on_progress)

    assert result["plot"]["status"] == "skipped"
    assert result["plot"]["skipped_reason"] == "outline_exists"
    assert result["world"]["status"] == "done"
    assert result["character"]["status"] == "done"

    # PlotAgent.generate_outline 不应被调用
    MockPlot.return_value.generate_outline.assert_not_called()
    # 跳过事件应上报
    skip_events = [e for e in events if e.get("status") == "skipped"]
    assert any(e["stage"] == "plot" for e in skip_events)


async def test_prefill_with_world_skips_world_only(db: db, work):
    from app.models.world import WorldBible

    wb = WorldBible(work_id=work.id, raw_text="已有世界观", is_indexed=True)
    db.add(wb)
    await db.commit()

    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock(return_value=("p", "mock"))
        MockWorld.return_value.suggest = AsyncMock()
        MockChar.return_value.suggest = AsyncMock(return_value=([], "mock", ""))

        result = await run_chapter_prefill(db, work.id)

    assert result["world"]["status"] == "skipped"
    MockWorld.return_value.suggest.assert_not_called()
    assert result["plot"]["status"] == "done"
    assert result["character"]["status"] == "done"


async def test_prefill_with_character_skips_character_only(db: db, work):
    from app.models.character import Character

    c = Character(
        work_id=work.id,
        name="主角",
        role="protagonist",
        basic_info={},
        personality={},
        backstory={},
        raw_text="",
    )
    db.add(c)
    await db.commit()

    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock(return_value=("p", "mock"))
        MockWorld.return_value.suggest = AsyncMock(return_value=("wb", "mock", ""))
        MockChar.return_value.suggest = AsyncMock()

        result = await run_chapter_prefill(db, work.id)

    assert result["character"]["status"] == "skipped"
    MockChar.return_value.suggest.assert_not_called()
    assert result["plot"]["status"] == "done"
    assert result["world"]["status"] == "done"


async def test_prefill_all_existing_skips_all_three(db: db, work):
    """work 已有 plot + world + character → 全 skipped(快速通道)。"""
    from app.models.character import Character
    from app.models.outline import OutlineNode, OutlineNodeType
    from app.models.world import WorldBible

    db.add_all([
        OutlineNode(
            work_id=work.id, type=OutlineNodeType.VOLUME, title="第一卷",
            summary="", beats=[], characters_involved=[], world_refs=[],
            target_word_count=30000, order=0,
        ),
        WorldBible(work_id=work.id, raw_text="世界观", is_indexed=True),
        Character(
            work_id=work.id, name="主角", role="protagonist",
            basic_info={}, personality={}, backstory={}, raw_text="",
        ),
    ])
    await db.commit()

    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock()
        MockWorld.return_value.suggest = AsyncMock()
        MockChar.return_value.suggest = AsyncMock()

        result = await run_chapter_prefill(db, work.id)

    assert result["plot"]["status"] == "skipped"
    assert result["world"]["status"] == "skipped"
    assert result["character"]["status"] == "skipped"
    MockPlot.return_value.generate_outline.assert_not_called()
    MockWorld.return_value.suggest.assert_not_called()
    MockChar.return_value.suggest.assert_not_called()


# ============== 异常隔离 ==============


async def test_preflight_plot_failure_does_not_block_world_and_character(db: db, work):
    """plot 抛异常 → world + character 仍继续(graceful degradation)。"""
    events: list[dict] = []

    async def on_progress(payload: dict):
        events.append(payload)

    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock(
            side_effect=RuntimeError("plot failed"),
        )
        MockWorld.return_value.suggest = AsyncMock(return_value=("wb", "mock", ""))
        MockChar.return_value.suggest = AsyncMock(return_value=([], "mock", ""))

        result = await run_chapter_prefill(db, work.id, on_progress=on_progress)

    assert result["plot"]["status"] == "error"
    assert "plot failed" in result["plot"]["error"]
    assert result["world"]["status"] == "done"
    assert result["character"]["status"] == "done"


async def test_preflight_world_failure_does_not_block_character(db: db, work):
    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock(return_value=("p", "mock"))
        MockWorld.return_value.suggest = AsyncMock(
            side_effect=ValueError("world boom"),
        )
        MockChar.return_value.suggest = AsyncMock(return_value=([], "mock", ""))

        result = await run_chapter_prefill(db, work.id)

    assert result["plot"]["status"] == "done"
    assert result["world"]["status"] == "error"
    assert result["character"]["status"] == "done"


# ============== 回调进度事件 schema ==============


async def test_preflight_callback_payload_schema(db: db, work):
    """回调 payload 字段齐全(running / done / skipped / error)。"""
    events: list[dict] = []

    async def on_progress(payload: dict):
        events.append(payload)

    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock(return_value=("p", "mock"))
        MockWorld.return_value.suggest = AsyncMock(return_value=("wb", "mock", ""))
        MockChar.return_value.suggest = AsyncMock(return_value=([], "mock", ""))

        await run_chapter_prefill(db, work.id, on_progress=on_progress)

    running_events = [e for e in events if e["status"] == "running"]
    done_events = [e for e in events if e["status"] == "done"]

    # 每 stage 各有 running + done
    assert {e["stage"] for e in running_events} == {"plot", "world", "character"}
    assert {e["stage"] for e in done_events} == {"plot", "world", "character"}
    # done 事件必有 elapsed_ms
    for ev in done_events:
        assert "elapsed_ms" in ev
        assert isinstance(ev["elapsed_ms"], int)


async def test_preflight_skipped_event_includes_reason(db: db, work):
    from app.models.outline import OutlineNode, OutlineNodeType

    db.add(OutlineNode(
        work_id=work.id, type=OutlineNodeType.VOLUME, title="第一卷",
        summary="", beats=[], characters_involved=[], world_refs=[],
        target_word_count=30000, order=0,
    ))
    await db.commit()

    events: list[dict] = []

    async def on_progress(payload: dict):
        events.append(payload)

    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock()
        MockWorld.return_value.suggest = AsyncMock(return_value=("wb", "mock", ""))
        MockChar.return_value.suggest = AsyncMock(return_value=([], "mock", ""))

        await run_chapter_prefill(db, work.id, on_progress=on_progress)

    plot_skipped = [e for e in events if e["stage"] == "plot" and e["status"] == "skipped"]
    assert plot_skipped
    assert plot_skipped[0]["skipped_reason"] == "outline_exists"
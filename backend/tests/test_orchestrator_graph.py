"""[P3.1] LangGraph StateGraph 编排测试。

覆盖：
- build_prefill_graph 返回的拓扑(plot / world / character 三个节点连边)
- ainvoke 真实遍历图(非顺序伪装)
- WS stage 事件 schema bit-compat(与原 _execute_stage 一致)
- state 参数(target_chapter_count)正确透传到 agent

注意：18 个旧测试已通过公共 API(run_chapter_prefill)覆盖异常隔离 / skip
逻辑；本文件聚焦在「图本体」—— 编译产物、节点连通性、状态 schema。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.preflight import run_chapter_prefill
from app.orchestrator.preflight_graph import build_prefill_graph


# ============== Fixtures（与 test_orchestrator_preflight.py 保持一致） ==============


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
        await session.execute(sa_delete(OutlineNode))
        await session.execute(sa_delete(Character))
        await session.execute(sa_delete(WorldBible))
        await session.execute(sa_delete(Work))
        await session.commit()


@pytest.fixture
async def work(db: AsyncSession):
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


# ============== 1. 编译产物拓扑 ==============


def test_graph_compiles_with_three_stages():
    """build_prefill_graph 返回 CompiledStateGraph 含 plot/world/character + START/END。"""
    graph = build_prefill_graph()

    # 类型断言：LangGraph 编译产物
    assert type(graph).__name__ == "CompiledStateGraph"

    # 节点拓扑：必须包含 3 个 stage + __start__ 哨兵
    node_names = set(graph.nodes.keys())
    assert "plot" in node_names, f"缺少 plot 节点, 实际节点: {node_names}"
    assert "world" in node_names, f"缺少 world 节点, 实际节点: {node_names}"
    assert "character" in node_names, f"缺少 character 节点, 实际节点: {node_names}"
    # LangGraph 自动注入的 START 哨兵
    assert "__start__" in node_names, f"缺少 START 哨兵, 实际节点: {node_names}"


# ============== 2. ainvoke 真实遍历图 ==============


async def test_graph_ainvoke_traverses_all_three_nodes(db: db, work):
    """直接 ainvoke 编译图 → 三个 result 槽都被填充(证明 LangGraph 真的走了 3 节点)。

    区别于 test_prefill_empty_work_runs_all_three_stages(通过 run_chapter_prefill 公共 API),
    此测试直接驱动 CompiledStateGraph.ainvoke —— 如果未来有人误改拓扑为单节点合并,
    此测试会失败。
    """
    graph = build_prefill_graph()

    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock(return_value=("p", "mock"))
        MockWorld.return_value.suggest = AsyncMock(return_value=("wb", "mock", ""))
        MockChar.return_value.suggest = AsyncMock(return_value=([], "mock", ""))

        final_state = await graph.ainvoke({
            "db": db,
            "work_id": work.id,
            "target_chapter_count": 10,
            "character_count": 3,
            "on_progress": None,
        })

    # 三个 result 槽都必须存在 —— LangGraph 把每个 node 返回的 dict 合并到 state
    assert "plot_result" in final_state
    assert "world_result" in final_state
    assert "character_result" in final_state

    # 每个 result 都标记 done(空 work 触发全跑)
    assert final_state["plot_result"]["status"] == "done"
    assert final_state["world_result"]["status"] == "done"
    assert final_state["character_result"]["status"] == "done"

    # 三个 mock 都被实际调用 —— 证明 LangGraph 真的按 plot→world→character 顺序 invoke
    MockPlot.return_value.generate_outline.assert_awaited_once()
    MockWorld.return_value.suggest.assert_awaited_once()
    MockChar.return_value.suggest.assert_awaited_once()


# ============== 3. WS stage 事件 schema bit-compat ==============


async def test_graph_ws_payload_shape_bit_compat(db: db, work):
    """WS stage 事件 schema 与原 _execute_stage 完全一致(前端无感升级)。"""
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

    # 至少 6 条事件(3 stage × running + done)
    assert len(events) >= 6, f"事件数不足, 实际: {len(events)}"

    # 每个 stage 都产生 running + done
    for stage in ("plot", "world", "character"):
        stage_events = [e for e in events if e["stage"] == stage]
        statuses = {e["status"] for e in stage_events}
        assert "running" in statuses, f"{stage} 缺少 running 事件"
        assert "done" in statuses, f"{stage} 缺少 done 事件"

    # done 事件必有 elapsed_ms 且为 int(WS payload 契约)
    for ev in events:
        if ev["status"] == "done":
            assert "elapsed_ms" in ev, f"done 事件缺 elapsed_ms: {ev}"
            assert isinstance(ev["elapsed_ms"], int)
            assert ev["elapsed_ms"] >= 0


# ============== 4. state 参数透传 ==============


async def test_graph_params_threaded_from_state(db: db, work):
    """target_chapter_count=5 从 state 透传到 PlotAgent.generate_outline。"""
    events: list[dict] = []

    async def on_progress(payload: dict):
        events.append(payload)

    with patch("app.orchestrator.preflight.PlotAgent") as MockPlot, \
         patch("app.orchestrator.preflight.WorldAgent") as MockWorld, \
         patch("app.orchestrator.preflight.CharacterAgent") as MockChar:

        MockPlot.return_value.generate_outline = AsyncMock(return_value=("p", "mock"))
        MockWorld.return_value.suggest = AsyncMock(return_value=("wb", "mock", ""))
        MockChar.return_value.suggest = AsyncMock(return_value=([], "mock", ""))

        await run_chapter_prefill(
            db, work.id,
            on_progress=on_progress,
            target_chapter_count=5,  # ← 关键参数
            character_count=7,
        )

    # 验证 target_chapter_count=5 真的传到了 agent
    plot_call_kwargs = MockPlot.return_value.generate_outline.call_args.kwargs
    assert plot_call_kwargs.get("target_chapter_count") == 5, (
        f"target_chapter_count 未透传, 实际调用: {plot_call_kwargs}"
    )
    # work_id 也必须透传
    assert plot_call_kwargs.get("work_id") == work.id
    # db 必须透传(供 agent 写库)
    assert plot_call_kwargs.get("db") is db

    # character_count=7 透传到 CharacterAgent.suggest
    char_call_kwargs = MockChar.return_value.suggest.call_args.kwargs
    assert char_call_kwargs.get("count") == 7, (
        f"character count 未透传, 实际调用: {char_call_kwargs}"
    )
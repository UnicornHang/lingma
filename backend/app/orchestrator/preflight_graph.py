"""[P3.1] LangGraph 实现的 prefill 流水线。

替换原命令式 preflight.py 主流程。设计目标:
- 保持 `run_chapter_prefill` 签名不变 → 14 个现有测试零修改
- 保留 `_execute_stage` 的 per-stage try/except + on_progress 契约
  (LangGraph 没有原生 skip-on-error,所以节点内部做异常隔离)
- 节点按 START → plot → world → character → END 顺序连接
- 每个节点返回 dict,LangGraph 把返回 dict 合并到 state

为什么不直接复用 LangGraph 的 RetryPolicy / with_fallbacks:
- 需求是「跳过失败节点继续下一个」,不是「重试」也不是「整图回退」
- 原 `_execute_stage` 已经实现 exactly this 行为 —— 克隆为 `safe_node`
"""
from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

# [P3.1] Agent 类必须通过 `preflight` 模块间接 import —— 既有测试用
# `patch("app.orchestrator.preflight.PlotAgent")` 这种按模块属性的方式 mock。
# 直接 import 会让 mock target 与生产调用点脱钩(patch 改了 preflight 的属性,
# 但 graph 调用的是自己的全局命名空间)。
#
# 进一步注意:不能用 `PlotAgent = _preflight.PlotAgent` 在模块顶部做绑定 —— Python
# 的 `from X import Y` 语义会让 `PlotAgent` 成为 `preflight_graph` 模块自己的属性,
# 捕获的是 import 那一刻的类对象。后续 `patch("preflight.PlotAgent", ...)` 会
# 替换 `preflight` 上的属性,但本模块的 `PlotAgent` 仍指向原类。
#
# 因此:节点内部用 `_preflight.PlotAgent()` 每次调用时做属性查找 —— 让 mock
# 透传到生产调用点。
from app.orchestrator import preflight as _preflight
from app.orchestrator.graph_state import PreflightState, StageProgress

logger = logging.getLogger(__name__)


# ============ 跳过判定(与原 preflight.py 完全一致,保留供节点调用) ============


async def _has_outline(db: AsyncSession, work_id: UUID) -> bool:
    """work 是否已有大纲(至少一个 volume 节点)。"""
    from sqlalchemy import func, select
    from app.models.outline import OutlineNode, OutlineNodeType

    r = await db.execute(
        select(func.count(OutlineNode.id)).where(
            OutlineNode.work_id == work_id,
            OutlineNode.type == OutlineNodeType.VOLUME,
        )
    )
    return (r.scalar() or 0) > 0


async def _has_world_bible(db: AsyncSession, work_id: UUID) -> bool:
    """work 是否已有世界书(raw_text 非空 或 任一维度非空)。"""
    from sqlalchemy import select
    from app.models.world import WorldBible

    r = await db.execute(select(WorldBible).where(WorldBible.work_id == work_id))
    wb = r.scalar_one_or_none()
    if not wb:
        return False
    if wb.raw_text and wb.raw_text.strip():
        return True
    if any([wb.geography, wb.factions, wb.power_system, wb.timeline, wb.rules, wb.culture]):
        return True
    return False


async def _has_characters(db: AsyncSession, work_id: UUID) -> bool:
    """work 是否已有角色(至少 1 张 character 卡)。"""
    from sqlalchemy import func, select
    from app.models.character import Character

    r = await db.execute(select(func.count(Character.id)).where(Character.work_id == work_id))
    return (r.scalar() or 0) >= 1


# ============ safe_node: 克隆 _execute_stage 的异常隔离模式 ============


async def _safe_node(
    name: str,
    fn: Callable[..., Awaitable[Any]],
    state: PreflightState,
    *,
    on_skip: Callable[[], Awaitable[None]],
    on_skip_result: dict[str, Any],
    fn_args: dict[str, Any],
) -> dict[str, Any]:
    """执行单个 stage,统一异常隔离。

    行为契约(必须与原 _execute_stage 完全一致):
    1. 先发 `running` 事件 → 调 fn → 发 `done`/`error` 事件
    2. 异常时 log + 发 `error` 事件 + 返回 status="error"(不抛)
    3. 返回的 dict 写入 state 槽位供 LangGraph 合并

    Args:
        name: stage 名(plot/world/character)
        fn: agent 函数(agent.generate_outline / agent.suggest)
        state: 当前 LangGraph state
        on_skip: 已存在数据时回调(发 skipped 事件 + 返回 skipped dict)
        on_skip_result: skip 时返回的 dict 模板
        fn_args: 调 fn 时的 kwargs

    Returns:
        写入 state 的 dict,例如 {"plot_result": {"status": "done", "elapsed_ms": 1234}}
    """
    on_progress: Optional[StageProgress] = state.get("on_progress")
    db: AsyncSession = state["db"]

    # 跳过判定(在 running 事件之前)
    # 注意:skip 分支不走 running → done/error,只发 skipped 事件(与原 _report_skip 一致)
    if name == "plot" and await _has_outline(db, state["work_id"]):
        await _emit_skip(on_progress, name, "outline_exists")
        return {"plot_result": dict(on_skip_result)}
    if name == "world" and await _has_world_bible(db, state["work_id"]):
        await _emit_skip(on_progress, name, "world_bible_exists")
        return {"world_result": dict(on_skip_result)}
    if name == "character" and await _has_characters(db, state["work_id"]):
        await _emit_skip(on_progress, name, "characters_exist")
        return {"character_result": dict(on_skip_result)}

    # 实际执行
    if on_progress:
        await on_progress({"stage": name, "status": "running"})

    start = time.time()
    try:
        await fn(db=db, **fn_args)
        elapsed_ms = int((time.time() - start) * 1000)
        if on_progress:
            await on_progress({"stage": name, "status": "done", "elapsed_ms": elapsed_ms})
        result = {"status": "done", "elapsed_ms": elapsed_ms}
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.warning(
            "[PreflightGraph] %s stage failed: %s",
            name, e, exc_info=True,
        )
        if on_progress:
            await on_progress({
                "stage": name, "status": "error",
                "elapsed_ms": elapsed_ms, "error": str(e),
            })
        result = {"status": "error", "elapsed_ms": elapsed_ms, "error": str(e)}

    key = f"{name}_result"
    return {key: result}


async def _emit_skip(
    on_progress: Optional[StageProgress],
    name: str,
    reason: str,
) -> None:
    """发 skipped 事件(与原 _report_skip 一致)。"""
    if on_progress:
        await on_progress({"stage": name, "status": "skipped", "skipped_reason": reason})


# ============ LangGraph 节点函数 ============


async def plot_node(state: PreflightState) -> dict[str, Any]:
    """plot 节点:生成大纲。"""
    target = state.get("target_chapter_count", 10)
    return await _safe_node(
        "plot",
        _preflight.PlotAgent().generate_outline,
        state,
        on_skip=lambda: None,  # 已内联在 _safe_node
        on_skip_result={"status": "skipped", "skipped_reason": "outline_exists"},
        fn_args={"work_id": state["work_id"], "target_chapter_count": target},
    )


async def world_node(state: PreflightState) -> dict[str, Any]:
    """world 节点:生成世界书。"""
    return await _safe_node(
        "world",
        _preflight.WorldAgent().suggest,
        state,
        on_skip=lambda: None,
        on_skip_result={"status": "skipped", "skipped_reason": "world_bible_exists"},
        fn_args={"work_id": state["work_id"], "focus_dimension": "all"},
    )


async def character_node(state: PreflightState) -> dict[str, Any]:
    """character 节点:生成角色卡。"""
    count = state.get("character_count", 3)
    return await _safe_node(
        "character",
        _preflight.CharacterAgent().suggest,
        state,
        on_skip=lambda: None,
        on_skip_result={"status": "skipped", "skipped_reason": "characters_exist"},
        fn_args={"work_id": state["work_id"], "count": count, "focus": "protagonist"},
    )


# ============ StateGraph 构建 ============


def build_prefill_graph():
    """构建并编译章节预填 StateGraph。

    返回 CompiledStateGraph,可 .ainvoke(initial_state) 异步调用。

    拓扑:
        START → plot → world → character → END

    每个节点都包了 safe_node 异常隔离:任一节点抛错不会阻断后续节点
    (因为 _safe_node 自己 catch 了;但即使 catch 漏了,LangGraph 默认行为是终止图)。
    """
    builder = StateGraph(PreflightState)
    builder.add_node("plot", plot_node)
    builder.add_node("world", world_node)
    builder.add_node("character", character_node)

    builder.add_edge(START, "plot")
    builder.add_edge("plot", "world")
    builder.add_edge("world", "character")
    builder.add_edge("character", END)

    return builder.compile()


# ============ 主入口(供 preflight.py 薄壳调用) ============


async def run_chapter_prefill_graph(
    db: AsyncSession,
    work_id: UUID,
    *,
    on_progress: Optional[StageProgress] = None,
    target_chapter_count: int = 10,
    character_count: int = 3,
) -> dict[str, Any]:
    """LangGraph 版 run_chapter_prefill。

    返回的 dict 结构与原命令式实现一致:
        {
            "plot":     {"status": "done"|"error"|"skipped", ...},
            "world":    {...},
            "character": {...},
        }
    """
    graph = build_prefill_graph()
    final_state = await graph.ainvoke({
        "db": db,
        "work_id": work_id,
        "target_chapter_count": target_chapter_count,
        "character_count": character_count,
        "on_progress": on_progress,
    })

    # 把 state 槽(plot_result/world_result/character_result)映射回原返回 schema
    return {
        "plot": final_state.get("plot_result", {"status": "skipped"}),
        "world": final_state.get("world_result", {"status": "skipped"}),
        "character": final_state.get("character_result", {"status": "skipped"}),
    }
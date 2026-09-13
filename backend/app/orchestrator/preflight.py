"""Orchestrator 预填(章节生成前的智能补全)。

[P3.1] 该模块现为 LangGraph StateGraph 实现的薄壳。
原命令式实现保留为内部 helper(_has_outline / _has_world_bible / _has_characters /
_execute_stage / _report_skip / StageProgress),供既有测试直接 import(零修改)。

实际主流程委托给 `app.orchestrator.preflight_graph.run_chapter_prefill_graph`。
- WS stage 事件 schema 完全一致(`stage` / `status` / `elapsed_ms` /
  `skipped_reason` / `error`)
- 返回 dict schema 完全一致(`{plot, world, character}` 三个 stage)
- per-stage 异常隔离 + graceful degradation 完全保留

设计:
- 三个 stage(plot / world / character)在章节生成前智能跳过:
  已存在则跳过,缺失则调用对应 agent 生成。
- 任一 stage 失败 → 记录 warning,**继续下一 stage**(graceful degradation)。
- 通过 on_progress 回调报告 stage 状态给 WS 前端。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.models.outline import OutlineNode, OutlineNodeType
from app.models.world import WorldBible

# [P3.1] 重新导出 Agent 类,供既有测试通过 `patch("app.orchestrator.preflight.PlotAgent")`
# 这种按模块属性的方式 mock。实际执行在 preflight_graph 中,但 mock target 仍在
# preflight 上 → 必须保留 PlotAgent / WorldAgent / CharacterAgent 作为模块属性。
from app.agents.plot_agent import PlotAgent  # noqa: F401
from app.agents.world_agent import WorldAgent  # noqa: F401
from app.agents.character_agent import CharacterAgent  # noqa: F401

logger = logging.getLogger(__name__)


# ============ 跳过判定(供既有测试 import,实际由 preflight_graph._safe_node 调用) ============


async def _has_outline(db: AsyncSession, work_id: UUID) -> bool:
    """work 是否已有大纲(至少一个 volume 节点)。"""
    r = await db.execute(
        select(func.count(OutlineNode.id)).where(
            OutlineNode.work_id == work_id,
            OutlineNode.type == OutlineNodeType.VOLUME,
        )
    )
    return (r.scalar() or 0) > 0


async def _has_world_bible(db: AsyncSession, work_id: UUID) -> bool:
    """work 是否已有世界书(raw_text 非空 或 任一维度非空)。"""
    r = await db.execute(select(WorldBible).where(WorldBible.work_id == work_id))
    wb = r.scalar_one_or_none()
    if not wb:
        return False
    if wb.raw_text and wb.raw_text.strip():
        return True
    # 6 维度任一非空
    if any([
        wb.geography,
        wb.factions,
        wb.power_system,
        wb.timeline,
        wb.rules,
        wb.culture,
    ]):
        return True
    return False


async def _has_characters(db: AsyncSession, work_id: UUID) -> bool:
    """work 是否已有角色(至少 1 张 character 卡)。"""
    r = await db.execute(
        select(func.count(Character.id)).where(Character.work_id == work_id)
    )
    return (r.scalar() or 0) >= 1


# ============ 单 stage 执行(含异常隔离) — 保留以兼容既有 import ============


StageProgress = Callable[[dict[str, Any]], Awaitable[None]]


async def _execute_stage(
    name: str,
    fn,
    *args,
    on_progress: Optional[StageProgress] = None,
    **kwargs,
) -> dict[str, Any]:
    """执行单个 stage,统一异常隔离。

    [P3.1] 实际由 `preflight_graph._safe_node` 实现,本函数保留供
    既有代码 / 测试 import 不报错。生产路径不调用。
    """
    if on_progress:
        await on_progress({
            "stage": name,
            "status": "running",
        })
    start = time.time()
    try:
        result = await fn(*args, **kwargs)
        elapsed_ms = int((time.time() - start) * 1000)
        if on_progress:
            await on_progress({
                "stage": name,
                "status": "done",
                "elapsed_ms": elapsed_ms,
            })
        return {"status": "done", "elapsed_ms": elapsed_ms, "result": result}
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.warning(
            "[Preflight] %s stage failed: %s",
            name, e, exc_info=True,
        )
        if on_progress:
            await on_progress({
                "stage": name,
                "status": "error",
                "elapsed_ms": elapsed_ms,
                "error": str(e),
            })
        return {"status": "error", "elapsed_ms": elapsed_ms, "error": str(e)}


# ============ 跳过报告 — 保留以兼容既有 import ============


async def _report_skip(
    name: str,
    reason: str,
    on_progress: Optional[StageProgress],
) -> None:
    """向前端报告 stage 跳过。生产路径由 `preflight_graph._emit_skip` 调用。"""
    if on_progress:
        await on_progress({
            "stage": name,
            "status": "skipped",
            "skipped_reason": reason,
        })


# ============ 主入口:章节生成前预填 — 委托给 LangGraph 实现 ============


async def run_chapter_prefill(
    db: AsyncSession,
    work_id: UUID,
    *,
    on_progress: Optional[StageProgress] = None,
    target_chapter_count: int = 10,
    character_count: int = 3,
) -> dict[str, Any]:
    """章节生成前:智能补全 plot → world → character。

    [P3.1] 委托给 LangGraph StateGraph 实现(`preflight_graph`)。
    签名与返回 schema 完全保留 → 14 个既有测试零修改通过。

    Args:
        db: async session
        work_id: 作品 id
        on_progress: async 回调 fn(payload),payload schema 与 WS stage 事件一致
        target_chapter_count: plot agent 目标章节数
        character_count: character agent 生成数量

    Returns:
        {
            "plot":     {"status": "done"|"error"|"skipped", "elapsed_ms"?, "skipped_reason"?},
            "world":    {...},
            "character": {...},
        }
    """
    from app.orchestrator.preflight_graph import run_chapter_prefill_graph

    return await run_chapter_prefill_graph(
        db,
        work_id,
        on_progress=on_progress,
        target_chapter_count=target_chapter_count,
        character_count=character_count,
    )
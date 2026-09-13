"""Orchestrator 预填(章节生成前的智能补全)。

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

from app.agents.character_agent import CharacterAgent
from app.agents.plot_agent import PlotAgent
from app.agents.world_agent import WorldAgent
from app.models.character import Character
from app.models.outline import OutlineNode, OutlineNodeType
from app.models.world import WorldBible

logger = logging.getLogger(__name__)


# ============ 跳过判定 ============


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
    r = await db.execute(
        select(WorldBible).where(WorldBible.work_id == work_id)
    )
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


# ============ 单 stage 执行(含异常隔离) ============


StageProgress = Callable[[dict[str, Any]], Awaitable[None]]


async def _execute_stage(
    name: str,
    fn,
    *args,
    on_progress: Optional[StageProgress] = None,
    **kwargs,
) -> dict[str, Any]:
    """执行单个 stage,统一异常隔离。

    返回: {"status": "done"|"error", "elapsed_ms": int, "result": ..., "error": str?}
    - status="done": fn 成功返回
    - status="error": fn 抛异常(不阻断调用方)

    on_progress 回调在执行前后各发一次(running → done/error)。
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


# ============ 跳过报告 ============


async def _report_skip(
    name: str,
    reason: str,
    on_progress: Optional[StageProgress],
) -> None:
    """向前端报告 stage 跳过。"""
    if on_progress:
        await on_progress({
            "stage": name,
            "status": "skipped",
            "skipped_reason": reason,
        })


# ============ 主入口:章节生成前预填 ============


async def run_chapter_prefill(
    db: AsyncSession,
    work_id: UUID,
    *,
    on_progress: Optional[StageProgress] = None,
    target_chapter_count: int = 10,
    character_count: int = 3,
) -> dict[str, Any]:
    """章节生成前:智能补全 plot → world → character。

    行为:
    - 每 stage 先做 skip 判定(已有数据 → 跳过)
    - 缺失则调用对应 Agent 真实实现,异步 stream-friendly
    - 任一失败 → 仅 warning,不影响后续 stage 与 writer

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
    results: dict[str, dict] = {}

    # ===== plot stage =====
    if await _has_outline(db, work_id):
        await _report_skip("plot", "outline_exists", on_progress)
        results["plot"] = {"status": "skipped", "skipped_reason": "outline_exists"}
    else:
        agent = PlotAgent()
        stage = await _execute_stage(
            "plot",
            agent.generate_outline,
            db,
            work_id=work_id,
            target_chapter_count=target_chapter_count,
            on_progress=on_progress,
        )
        results["plot"] = stage

    # ===== world stage =====
    if await _has_world_bible(db, work_id):
        await _report_skip("world", "world_bible_exists", on_progress)
        results["world"] = {"status": "skipped", "skipped_reason": "world_bible_exists"}
    else:
        agent = WorldAgent()
        stage = await _execute_stage(
            "world",
            agent.suggest,
            db,
            work_id=work_id,
            focus_dimension="all",
            on_progress=on_progress,
        )
        results["world"] = stage

    # ===== character stage =====
    if await _has_characters(db, work_id):
        await _report_skip("character", "characters_exist", on_progress)
        results["character"] = {"status": "skipped", "skipped_reason": "characters_exist"}
    else:
        agent = CharacterAgent()
        stage = await _execute_stage(
            "character",
            agent.suggest,
            db,
            work_id=work_id,
            count=character_count,
            focus="protagonist",
            on_progress=on_progress,
        )
        results["character"] = stage

    return results
"""[P3.1] 编排引擎 — 精简版。

P3.1 重构:
- 删除 `run_pipeline`(6-agent 串行占位实现,已确认无调用方)
- 删除 `run_single`(未使用)
- 保留 `run_chapter_prefill` 委托给 `app.orchestrator.preflight`,
  后者进一步委托给 LangGraph StateGraph
- 保留 `get_orchestrator()` 单例工厂以兼容现有调用方

为什么 Orchestrator 类不整体删:
- `get_orchestrator()` 在 `app/orchestrator/__init__.py` 中导出,
  `backend/app/api/ws/generation.py:234` 可能 import(待核实)
- 类可瘦身为仅含 `run_chapter_prefill` 一个方法
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class Orchestrator:
    """编排器:目前仅承担章节生成前的预填职责。

    后续若需要更复杂的状态机(条件分支 / 并行 node / 子图),
    直接扩展 `app.orchestrator.preflight_graph.build_prefill_graph()`。
    """

    async def run_chapter_prefill(
        self,
        db: AsyncSession,
        work_id: UUID,
        *,
        on_progress: Callable[[dict], Awaitable[None]] | None = None,
        target_chapter_count: int = 10,
        character_count: int = 3,
    ) -> dict[str, Any]:
        """章节生成前的预填:智能跳过已有数据,补全 plot/world/character。

        委托给 `app.orchestrator.preflight.run_chapter_prefill` → LangGraph 实现。
        任一 stage 失败 → 仅 warning,不阻断 writer。
        """
        from app.orchestrator.preflight import run_chapter_prefill

        return await run_chapter_prefill(
            db,
            work_id,
            on_progress=on_progress,
            target_chapter_count=target_chapter_count,
            character_count=character_count,
        )


_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """获取全局单例 Orchestrator。

    保留以兼容 `from app.orchestrator import get_orchestrator` 调用方。
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
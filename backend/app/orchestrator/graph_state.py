"""[P3.1] LangGraph StateGraph 的 prefill 状态定义。

设计要点:
- PreflightState 是 TypedDict,LangGraph 用作状态合并的 schema
- 每个 node 返回 dict → LangGraph 自动把返回的键合并到 state
- 必须返回新 dict(不能就地改 state),LangGraph 1.x 的状态合并契约
- DB session 和 on_progress 回调注入 state(不是 config["configurable"]),
  与 prefill.py 现有「外部传入 session」的契约一致
- 节点名 `character` 撞 Python 内置名,所以 state 槽用 `character_result`,
  最终返回 dict 用 `character` 与 WS / smoke test schema 对齐
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional, TypedDict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


# 与 preflight.py 共享类型别名 —— 兼容既有 on_progress 调用方
StageProgress = Callable[[dict[str, Any]], Awaitable[None]]


class PreflightState(TypedDict, total=False):
    """LangGraph StateGraph 的状态 schema。

    输入字段(invoke 前传入):
        db: AsyncSession —— 整个 prefill 复用同一 session(与原实现一致)
        work_id: UUID —— 作品 id
        target_chapter_count: int —— plot agent 期望章节数(默认 10)
        character_count: int —— character agent 期望角色数(默认 3)
        on_progress: Optional[StageProgress] —— 回调,WS stage 事件写入

    输出字段(nodes 写入):
        plot_result: dict —— plot stage 的 done/error/skipped 报告
        world_result: dict
        character_result: dict
    """

    # 输入
    db: AsyncSession
    work_id: UUID
    target_chapter_count: int
    character_count: int
    on_progress: Optional[StageProgress]

    # 输出(nodes 填入)
    plot_result: dict[str, Any]
    world_result: dict[str, Any]
    character_result: dict[str, Any]
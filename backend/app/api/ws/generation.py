"""WebSocket - 流式生成路由（P2-1：真实 LLM 接入）

协议（前后端约定）：
- 客户端连入
- 服务端发送 {type: "connected", task_id, message}
- 客户端发送 {type: "start"} 触发生成
- 服务端流式返回 {type: "delta", content} ... {type: "done", content, token_usage}
- 服务端可能发送 {type: "error", error}
- 客户端可发送 {type: "ping"} / 服务端回 {type: "pong"}
- 客户端发送 {type: "cancel"} / 服务端回 {type: "cancelled"} 并断开

P2-1 增量：
- 从 DB 拉 GenerationTask 与 chapter 上下文
- 按 task_type 选择对应 Agent（当前仅 writer 实现了真实流）
- 通过 `LLMService.resolve_provider_config` 选 APIConfig
- 流式内容逐 delta 写回 `chapter.plain_content`（带行级节流）
- done 时落库 `chapter.content`（空 TipTap doc 占位）、`word_count`、`version`、`status=generated`
- 更新 `task.status`、`task.completed_at`、`task.token_usage`
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.agents.writer_agent import WriterAgent
from app.db.session import async_session_factory
from app.models.chapter import Chapter, ChapterStatus
from app.models.task import GenerationTask, TaskStatus, TaskType
from app.services.chapter_service import count_words
from app.services.llm_service import (
    LLMMessage,
    LLMRequest,
    ProviderConfig,
    get_llm_service,
    resolve_provider_config,
)

logger = logging.getLogger(__name__)

ws_router = APIRouter()


# ==================== Task → Agent 路由 ====================

AGENT_FOR_TASK: dict[TaskType, str] = {
    TaskType.CHAPTER_CONTINUE: "writer",
    TaskType.CHAPTER_GENERATE: "writer",
    TaskType.CHAPTER_REWRITE: "writer",
    TaskType.CHAPTER_EXPAND: "writer",
    TaskType.CHAPTER_SHORTEN: "writer",
    TaskType.CHAPTER_POLISH: "writer",
}


# ==================== WS 端点 ====================


@ws_router.websocket("/ws/generation/{task_id}")
async def generation_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()
    logger.info("WS 连接建立: task_id=%s", task_id)
    llm = get_llm_service()

    try:
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": "WebSocket 已连接，请发送 start 启动生成",
        })

        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            logger.debug("WS 收到: task_id=%s, type=%s", task_id, event_type)

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif event_type == "start":
                await _handle_start(websocket, task_id, data, llm)

            elif event_type == "cancel":
                await _cancel_task(task_id)
                await websocket.send_json({"type": "cancelled", "task_id": task_id})
                break

            else:
                await websocket.send_json({
                    "type": "error",
                    "error": f"未知事件类型: {event_type}",
                })

    except WebSocketDisconnect:
        logger.info("WS 断开: task_id=%s", task_id)
        await _cancel_task(task_id)
    except Exception as e:
        logger.error("WS 异常: task_id=%s, error=%s", task_id, e, exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass


# ==================== start 处理 ====================


async def _handle_start(
    websocket: WebSocket,
    task_id: str,
    data: dict[str, Any],
    llm,
) -> None:
    """触发一次流式生成。

    关键路径：
    1. 解析 task_id → GenerationTask → chapter_id
    2. 选择 Agent（按 task_type） + APIConfig
    3. 若 client 自带 messages（向后兼容旧前端），走 LLMService.stream 直接流
    4. 否则委托 Agent.stream()，加载完整上下文
    """
    override_messages: list[LLMMessage] | None = None
    if "messages" in data and data["messages"]:
        override_messages = [
            LLMMessage(role=m.get("role", "user"), content=m.get("content", ""))
            for m in data["messages"]
            if m.get("content")
        ]

    stream_id = str(uuid.uuid4())

    async with async_session_factory() as db:
        task = await _load_task(db, task_id)
        if task is None:
            await websocket.send_json({"type": "error", "error": f"task {task_id} 不存在"})
            return
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            await websocket.send_json({
                "type": "error",
                "error": f"task {task_id} 状态为 {task.status.value}，无法再次启动",
            })
            return

        chapter_id = task.chapter_id
        agent_type = AGENT_FOR_TASK.get(task.task_type, "writer")

        # 解析 APIConfig（找不到则走 mock）
        cfg = await resolve_provider_config(db, agent_type=agent_type)

        # 标记 task 进入 running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

    await websocket.send_json({
        "type": "start",
        "task_id": task_id,
        "stream_id": stream_id,
        "agent": agent_type,
        "model": cfg.model if cfg else "mock",
        "provider": cfg.provider.value if cfg else "mock",
    })

    full_content = ""
    final_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
    error_msg: str | None = None

    try:
        async with async_session_factory() as db:
            if chapter_id is None:
                # 兜底：仅用 client messages
                if not override_messages:
                    raise ValueError("task 未绑定 chapter，且客户端未提供 messages")
                req = LLMRequest(
                    messages=override_messages,
                    model=data.get("model", cfg.model if cfg else "mock"),
                    temperature=float(data.get("temperature", 0.8)),
                    max_tokens=int(data.get("max_tokens", 2048)),
                    stream=True,
                )
                async for delta in llm.stream(req, cfg):
                    full_content += delta
                    await websocket.send_json({
                        "type": "delta",
                        "task_id": task_id,
                        "stream_id": stream_id,
                        "content": delta,
                    })
            else:
                # ===== 真实 writer 路径 =====
                writer = WriterAgent()
                buffer_size = 0
                flush_threshold = 200  # 字符，超过则写一次库
                async for delta in writer.stream(
                    db,
                    chapter_id,
                    cfg,
                    override_messages=override_messages,
                    temperature=float(data.get("temperature", 0.85)),
                    max_tokens=int(data.get("max_tokens", 4096)),
                ):
                    full_content += delta
                    buffer_size += len(delta)
                    await websocket.send_json({
                        "type": "delta",
                        "task_id": task_id,
                        "stream_id": stream_id,
                        "content": delta,
                    })
                    # 节流写回：避免每字符一次 IO
                    if buffer_size >= flush_threshold:
                        await _partial_save_chapter(db, chapter_id, full_content)
                        buffer_size = 0

    except Exception as e:
        logger.error("生成失败: task_id=%s, error=%s", task_id, e, exc_info=True)
        error_msg = str(e)

    # ===== 完成态落库 =====
    async with async_session_factory() as db:
        task = await _load_task(db, task_id)
        chapter_id = task.chapter_id if task else None
        if task:
            task.completed_at = datetime.now(timezone.utc)
            if error_msg:
                task.status = TaskStatus.FAILED
                task.error = error_msg[:2000]
            elif task.status == TaskStatus.CANCELLED:
                pass  # 用户已取消
            else:
                task.status = TaskStatus.COMPLETED
                task.result = {
                    "preview": full_content[:500],
                    "length": len(full_content),
                }
            task.token_usage = final_usage
            await db.commit()

        if chapter_id and not error_msg:
            await _finalize_chapter(db, chapter_id, full_content)

    # ===== 给前端回报 =====
    if error_msg:
        await websocket.send_json({
            "type": "error",
            "task_id": task_id,
            "stream_id": stream_id,
            "error": error_msg,
        })
    else:
        await websocket.send_json({
            "type": "done",
            "task_id": task_id,
            "stream_id": stream_id,
            "content": full_content,
            "token_usage": final_usage,
        })


# ==================== 持久化辅助 ====================


async def _load_task(db, task_id: str) -> GenerationTask | None:
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        return None
    r = await db.execute(select(GenerationTask).where(GenerationTask.id == tid))
    return r.scalar_one_or_none()


async def _partial_save_chapter(db, chapter_id: uuid.UUID, full_content: str) -> None:
    """流式过程中节流写 plain_content（status 暂不更新为 generated）"""
    r = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    ch = r.scalar_one_or_none()
    if not ch:
        return
    ch.plain_content = full_content
    ch.word_count = count_words(full_content)
    await db.commit()


async def _finalize_chapter(db, chapter_id: uuid.UUID, full_content: str) -> None:
    """完成时落库：content (TipTap 占位) + plain_content + word_count + status=generated + version++"""
    r = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    ch = r.scalar_one_or_none()
    if not ch:
        return
    ch.plain_content = full_content
    ch.word_count = count_words(full_content)
    ch.content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": full_content}],
            }
        ],
    }
    ch.status = ChapterStatus.GENERATED
    ch.version = (ch.version or 0) + 1
    await db.commit()


async def _cancel_task(task_id: str) -> None:
    """客户端断开或收到 cancel 时，把 task 标记为 cancelled。"""
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        return
    async with async_session_factory() as db:
        r = await db.execute(select(GenerationTask).where(GenerationTask.id == tid))
        t = r.scalar_one_or_none()
        if t and t.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            t.status = TaskStatus.CANCELLED
            t.completed_at = datetime.now(timezone.utc)
            await db.commit()
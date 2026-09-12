"""WebSocket - 流式生成路由（MVP 基础版）"""
import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.llm_service import LLMMessage, LLMRequest, get_llm_service

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws/generation/{task_id}")
async def generation_ws(websocket: WebSocket, task_id: str):
    """生成任务 WebSocket 端点

    客户端协议：
    1. 客户端连入
    2. 服务端发送 {type: "connected", task_id: ...}
    3. 客户端发送 {type: "start", messages: [...], model: "..."}
    4. 服务端流式返回 {type: "delta", content: "..."} ... {type: "done"}
    5. 客户端可发送 {type: "ping"} 维持心跳
    """
    await websocket.accept()
    logger.info(f"WS 连接建立: task_id={task_id}")

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
            logger.debug(f"WS 收到: task_id={task_id}, type={event_type}")

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif event_type == "start":
                # 启动生成
                raw_messages = data.get("messages", [])
                messages = [
                    LLMMessage(role=m.get("role", "user"), content=m.get("content", ""))
                    for m in raw_messages
                    if m.get("content")
                ]
                if not messages:
                    await websocket.send_json({
                        "type": "error",
                        "error": "messages 为空",
                    })
                    continue

                req = LLMRequest(
                    messages=messages,
                    model=data.get("model", "gpt-4o-mini"),
                    temperature=float(data.get("temperature", 0.8)),
                    max_tokens=int(data.get("max_tokens", 2048)),
                    stream=True,
                )

                stream_id = str(uuid.uuid4())
                await websocket.send_json({
                    "type": "start",
                    "task_id": task_id,
                    "stream_id": stream_id,
                    "model": req.model,
                })

                try:
                    full_content = ""
                    async for delta in llm.stream(req):
                        full_content += delta
                        await websocket.send_json({
                            "type": "delta",
                            "task_id": task_id,
                            "stream_id": stream_id,
                            "content": delta,
                        })

                    await websocket.send_json({
                        "type": "done",
                        "task_id": task_id,
                        "stream_id": stream_id,
                        "content": full_content,
                    })
                except Exception as e:
                    logger.error(f"生成失败: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "task_id": task_id,
                        "stream_id": stream_id,
                        "error": str(e),
                    })

            elif event_type == "cancel":
                await websocket.send_json({"type": "cancelled", "task_id": task_id})
                break

            else:
                await websocket.send_json({
                    "type": "error",
                    "error": f"未知事件类型: {event_type}",
                })

    except WebSocketDisconnect:
        logger.info(f"WS 断开: task_id={task_id}")
    except Exception as e:
        logger.error(f"WS 异常: task_id={task_id}, error={e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
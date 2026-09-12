"""LLM 适配服务（基于 LiteLLM 接口约定）

MVP 阶段：仅暴露协议接口，不强制依赖 LiteLLM 包，
       用户接入真实模型时可在环境变量中配置。
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """统一消息结构"""

    role: str  # system | user | assistant
    content: str


@dataclass
class LLMRequest:
    """统一 LLM 请求"""

    messages: list[LLMMessage]
    model: str = "gpt-4o-mini"
    temperature: float = 0.8
    max_tokens: int = 2048
    stream: bool = True
    extra: dict[str, Any] | None = None


@dataclass
class LLMResponse:
    """统一 LLM 响应"""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    raw: dict[str, Any] | None = None


class LLMError(Exception):
    """LLM 调用错误"""

    def __init__(self, message: str, *, code: str = "LLM_ERROR") -> None:
        super().__init__(message)
        self.code = code


class LLMService:
    """LLM 服务门面 - MVP 占位实现

    真实实现可基于 LiteLLM：
        from litellm import acompletion, completion
        completion(messages=..., model=..., stream=True)
    当前阶段：返回 Mock 流以便端到端链路验证。
    """

    async def chat(self, req: LLMRequest) -> LLMResponse:
        """一次性调用"""
        if not req.messages:
            raise LLMError("messages 不能为空", code="EMPTY_MESSAGES")
        # MVP Mock：拼接最后一条用户消息
        last = req.messages[-1].content[:200]
        return LLMResponse(
            content=f"[Mock {req.model}] 已收到 {len(req.messages)} 条消息。最后一条：{last}",
            model=req.model,
            input_tokens=sum(len(m.content) for m in req.messages) // 4,
            output_tokens=64,
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[str]:
        """流式调用"""
        last = req.messages[-1].content if req.messages else ""
        chunks = [
            f"[Mock {req.model}] 流式输出开始...\n",
            "正在思考：",
            f"\n\n你说的是：{last[:80]}\n\n",
            "这是一段示例文本。请在设置中配置真实 LLM 后获得更好效果。\n\n",
            "—— 完 ——",
        ]
        for c in chunks:
            yield c

    async def health_check(self) -> bool:
        return True


# 单例
_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _service
    if _service is None:
        _service = LLMService()
    return _service
"""LLM 适配服务

支持 OpenAI 兼容协议的 provider（OpenAI / DeepSeek / Qwen / Ollama / LMStudio / vLLM / 自定义）。
无 APIConfig 时回退到 Mock，便于无 key 的本地开发。

Provider 列表见 `app.models.api_config.Provider`。
Anthropic 不在本版本范围（需要独立 SDK）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_config import APIConfig, Provider
from app.services.crypto_service import decrypt

logger = logging.getLogger(__name__)


# ==================== 数据结构 ====================


@dataclass
class LLMMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class LLMRequest:
    messages: list[LLMMessage]
    model: str = "gpt-4o-mini"
    temperature: float = 0.8
    max_tokens: int = 2048
    stream: bool = True
    extra: dict[str, Any] | None = None


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    raw: dict[str, Any] | None = None


@dataclass
class ProviderConfig:
    """LLM 调用所需的 provider 配置"""

    provider: Provider
    base_url: str
    api_key: str
    model: str
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


# ==================== 错误 ====================


class LLMError(Exception):
    def __init__(self, message: str, *, code: str = "LLM_ERROR") -> None:
        super().__init__(message)
        self.code = code


# ==================== 配置解析 ====================


# 不需要 API Key 的 provider（本地推理）
LOCAL_PROVIDERS = {Provider.OLLAMA, Provider.LMSTUDIO, Provider.VLLM}

# 各 provider 的默认 base_url
DEFAULT_BASE_URLS: dict[Provider, str] = {
    Provider.OPENAI: "https://api.openai.com/v1",
    Provider.ANTHROPIC: "https://api.anthropic.com/v1",
    Provider.DEEPSEEK: "https://api.deepseek.com/v1",
    Provider.QWEN: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    Provider.OLLAMA: "http://127.0.0.1:11434/v1",
    Provider.LMSTUDIO: "http://127.0.0.1:1234/v1",
    Provider.VLLM: "http://127.0.0.1:8000/v1",
    Provider.CUSTOM: "",
}


async def resolve_provider_config(
    db: AsyncSession,
    *,
    agent_type: str,
    work_id: UUID | None = None,
) -> ProviderConfig | None:
    """从 APIConfig 表中查找分配给指定 agent 的可用配置。

    优先级：work 绑定 > 全局默认（agent_assignments 含 agent_type 且 enabled）。
    找到第一个匹配项即返回，未找到返回 None。
    """
    stmt = (
        select(APIConfig)
        .where(APIConfig.enabled.is_(True))
        .where(APIConfig.agent_assignments.is_not(None))
        .order_by(APIConfig.created_at.asc())
    )
    result = await db.execute(stmt)
    configs = result.scalars().all()

    for cfg in configs:
        if agent_type in (cfg.agent_assignments or []):
            api_key = decrypt(cfg.api_key_encrypted or "") if cfg.provider not in LOCAL_PROVIDERS else "sk-local-no-auth"
            base_url = cfg.base_url or DEFAULT_BASE_URLS.get(cfg.provider, "")
            return ProviderConfig(
                provider=cfg.provider,
                base_url=base_url,
                api_key=api_key,
                model=cfg.model_name,
                cost_per_1k_input=cfg.cost_per_1k_input,
                cost_per_1k_output=cfg.cost_per_1k_output,
            )
    return None


# ==================== 服务 ====================


class LLMService:
    """LLM 服务门面

    提供两类入口：
    - mock_*：纯本地假流，永远可用（兜底）
    - stream/chat：根据 ProviderConfig 调 OpenAI-compatible 端点
    """

    # ===== Mock 实现（无 LLM 时的兜底） =====

    async def _mock_chat(self, req: LLMRequest) -> LLMResponse:
        if not req.messages:
            raise LLMError("messages 不能为空", code="EMPTY_MESSAGES")
        last = req.messages[-1].content[:200]
        return LLMResponse(
            content=f"[Mock {req.model}] 已收到 {len(req.messages)} 条消息。最后一条：{last}",
            model=req.model,
            input_tokens=sum(len(m.content) for m in req.messages) // 4,
            output_tokens=64,
        )

    async def _mock_stream(self, req: LLMRequest) -> AsyncIterator[str]:
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

    # ===== 真实实现（OpenAI-compatible） =====

    def _build_client(self, cfg: ProviderConfig):
        """根据 provider 创建对应 client。仅 openai 已安装。"""
        # 延迟 import 以避免在 mock-only 场景下加载 openai 依赖
        try:
            from openai import AsyncOpenAI  # type: ignore[import-not-found]
        except ImportError as e:
            raise LLMError(
                "未安装 openai 包，无法调用真实 LLM。请 `pip install openai` 后重试。",
                code="MISSING_DEPENDENCY",
            ) from e
        return AsyncOpenAI(api_key=cfg.api_key or "sk-no-auth", base_url=cfg.base_url or None)

    async def _real_chat(self, cfg: ProviderConfig, req: LLMRequest) -> LLMResponse:
        client = self._build_client(cfg)
        msgs = [{"role": m.role, "content": m.content} for m in req.messages]
        try:
            resp = await client.chat.completions.create(
                model=req.model or cfg.model,
                messages=msgs,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=False,
            )
        except Exception as e:
            logger.error("LLM 调用失败: %s", e, exc_info=True)
            raise LLMError(f"LLM 调用失败: {e}", code="LLM_CALL_FAILED") from e
        content = (resp.choices[0].message.content or "") if resp.choices else ""
        usage = getattr(resp, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
        out_tok = getattr(usage, "completion_tokens", 0) if usage else 0
        cost = (
            in_tok / 1000 * cfg.cost_per_1k_input
            + out_tok / 1000 * cfg.cost_per_1k_output
        )
        return LLMResponse(
            content=content,
            model=req.model or cfg.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=cost,
        )

    async def _real_stream(
        self,
        cfg: ProviderConfig,
        req: LLMRequest,
    ) -> AsyncIterator[tuple[str, dict[str, int] | None]]:
        """流式调用 —— yield (delta_text, usage_or_None)。

        usage 仅在流结束时由最后一个 chunk 携带（部分 provider）。
        """
        client = self._build_client(cfg)
        msgs = [{"role": m.role, "content": m.content} for m in req.messages]
        try:
            stream = await client.chat.completions.create(
                model=req.model or cfg.model,
                messages=msgs,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=True,
                stream_options={"include_usage": True} if cfg.provider != Provider.ANTHROPIC else None,
            )
            async for chunk in stream:
                # 最后一个 chunk 可能只携带 usage，无 delta
                if not getattr(chunk, "choices", None):
                    usage_obj = getattr(chunk, "usage", None)
                    if usage_obj:
                        yield "", {
                            "input_tokens": getattr(usage_obj, "prompt_tokens", 0),
                            "output_tokens": getattr(usage_obj, "completion_tokens", 0),
                        }
                    continue
                choice = chunk.choices[0]
                delta_text = getattr(getattr(choice, "delta", None), "content", None) or ""
                # 部分 chunk 在尾段会带 usage
                usage_obj = getattr(chunk, "usage", None)
                usage_payload = None
                if usage_obj:
                    usage_payload = {
                        "input_tokens": getattr(usage_obj, "prompt_tokens", 0),
                        "output_tokens": getattr(usage_obj, "completion_tokens", 0),
                    }
                yield delta_text, usage_payload
        except LLMError:
            raise
        except Exception as e:
            logger.error("LLM 流式调用失败: %s", e, exc_info=True)
            raise LLMError(f"LLM 流式调用失败: {e}", code="LLM_STREAM_FAILED") from e

    # ===== 公共入口 =====

    async def chat(self, req: LLMRequest, cfg: ProviderConfig | None = None) -> LLMResponse:
        if not req.messages:
            raise LLMError("messages 不能为空", code="EMPTY_MESSAGES")
        if cfg is None:
            return await self._mock_chat(req)
        return await self._real_chat(cfg, req)

    async def stream(
        self,
        req: LLMRequest,
        cfg: ProviderConfig | None = None,
    ) -> AsyncIterator[str]:
        if not req.messages:
            raise LLMError("messages 不能为空", code="EMPTY_MESSAGES")
            yield  # noqa: 让 async generator 合法
        if cfg is None:
            async for d in self._mock_stream(req):
                yield d
            return
        async for delta, _usage in self._real_stream(cfg, req):
            if delta:
                yield delta

    async def health_check(self) -> bool:
        return True


# 单例
_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _service
    if _service is None:
        _service = LLMService()
    return _service
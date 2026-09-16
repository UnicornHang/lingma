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


def thinking_extra_body(cfg: ProviderConfig | None, model_name: str = "") -> dict[str, Any] | None:
    """MiniMax 默认开 thinking，正文/JSON 任务必须关掉，否则会吞 token 或把提示词抄进正文。"""
    model = (model_name or (cfg.model if cfg else "") or "").lower()
    provider = cfg.provider if cfg is not None else None
    if provider == Provider.MINIMAX or "minimax" in model:
        return {"thinking": {"type": "disabled"}}
    return None


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
    Provider.MINIMAX: "https://api.MiniMax.cn/v1",
    Provider.OLLAMA: "http://127.0.0.1:11434/v1",
    Provider.LMSTUDIO: "http://127.0.0.1:1234/v1",
    Provider.VLLM: "http://127.0.0.1:8000/v1",
    Provider.CUSTOM: "",
}


# Anthropic 没有公开的 /models 端点，这里维护一份常用清单
_ANTHROPIC_STATIC_MODELS: list[str] = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]


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


# ==================== 模型清单 ====================


@dataclass
class ProviderModelsResult:
    """模型清单拉取结果"""

    models: list[str]
    source: str  # "api" | "static"
    note: str | None = None


async def list_provider_models(
    provider: str,
    base_url: str | None = None,
    api_key: str | None = None,
    *,
    timeout: float = 10.0,
) -> ProviderModelsResult:
    """从 Provider 拉取可用模型清单

    - Anthropic：返回内置静态清单（官方不暴露 /models）
    - OpenAI 兼容（openai / deepseek / qwen / MiniMax / lmstudio / vllm / custom）：GET {base_url}/models
    - Ollama：GET {base_url}/api/tags（Ollama 自己的端点）
    - 本地推理（ollama / lmstudio / vllm）允许不传 api_key

    Raises:
        LLMError: 当 base_url 缺失或网络异常时
    """
    try:
        provider_enum = Provider(provider)
    except ValueError as e:
        raise LLMError(f"未知 provider: {provider}") from e

    # Anthropic：静态清单
    if provider_enum == Provider.ANTHROPIC:
        return ProviderModelsResult(
            models=_ANTHROPIC_STATIC_MODELS,
            source="static",
            note="Anthropic 官方未暴露 /models 端点，返回内置清单",
        )

    base = (base_url or DEFAULT_BASE_URLS.get(provider_enum, "")).rstrip("/")
    if not base:
        raise LLMError(
            f"{provider} 需要填写 base_url，例如 "
            f"{DEFAULT_BASE_URLS.get(provider_enum) or 'https://your-endpoint/v1'}"
        )

    # Ollama 端点是 /api/tags，不是 /v1/models
    if provider_enum == Provider.OLLAMA:
        url = base.removesuffix("/v1") + "/api/tags"
    else:
        url = base + "/models"

    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key and provider_enum not in LOCAL_PROVIDERS:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except ImportError as e:
        raise LLMError("缺少 httpx 依赖，请安装：pip install httpx") from e
    except Exception as e:  # httpx.HTTPError, JSONDecodeError, ...
        raise LLMError(f"拉取模型清单失败：{type(e).__name__}: {e}") from e

    # 提取模型 ID：兼容 OpenAI `{data:[{id:..}]}` 与 Ollama `{models:[{name:..}]}`
    raw_list = data.get("data") or data.get("models") or []
    models: list[str] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        mid = item.get("id") or item.get("name")
        if isinstance(mid, str) and mid.strip():
            models.append(mid.strip())

    if not models:
        return ProviderModelsResult(
            models=[],
            source="api",
            note="Provider 返回了空列表，请确认 Key 与权限",
        )

    return ProviderModelsResult(models=models, source="api")


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

    def _completion_kwargs(
        self,
        cfg: ProviderConfig,
        req: LLMRequest,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        """拼出 chat.completions.create 参数；req.extra 透传到 extra_body。"""
        kwargs: dict[str, Any] = {
            "model": cfg.model or req.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "stream": stream,
        }
        if req.extra:
            kwargs["extra_body"] = req.extra
        if stream and cfg.provider != Provider.ANTHROPIC:
            kwargs["stream_options"] = {"include_usage": True}
        return kwargs

    async def _real_chat(self, cfg: ProviderConfig, req: LLMRequest) -> LLMResponse:
        client = self._build_client(cfg)
        try:
            resp = await client.chat.completions.create(
                **self._completion_kwargs(cfg, req, stream=False),
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
            # 与上行请求保持一致,优先 cfg.model
            model=cfg.model or req.model,
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
        try:
            stream = await client.chat.completions.create(
                **self._completion_kwargs(cfg, req, stream=True),
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

    async def stream_with_usage(
        self,
        req: LLMRequest,
        cfg: ProviderConfig | None = None,
    ) -> AsyncIterator[tuple[str, dict[str, int] | None]]:
        """流式输出 + token 用量。

        - 每条 delta 携带 ``usage_or_None``(仅 OpenAI 兼容的最后一个 chunk 会带真实数字)
        - Mock 模式下 usage 始终为 None
        - 调用方应取最后一个非空 usage 作为 ``final_usage``
        """
        if not req.messages:
            raise LLMError("messages 不能为空", code="EMPTY_MESSAGES")
            yield ("", None)  # noqa: 让 async generator 合法
            return
        if cfg is None:
            async for d in self._mock_stream(req):
                yield d, None
            return
        async for delta, usage in self._real_stream(cfg, req):
            if delta:
                yield delta, usage

    async def health_check(self) -> bool:
        return True


# 单例
_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _service
    if _service is None:
        _service = LLMService()
    return _service
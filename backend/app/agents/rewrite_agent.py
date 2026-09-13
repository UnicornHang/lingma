"""[P3.3] Rewrite Agent —— Critic 引导的整章改写。

不同于 EditorAgent(针对 AI 痕迹的微观逐句改写),
本 Agent 针对 critic 多 Persona 共识问题的整章重写:

- 接收 chapter 全文 + consensus_issues + scores + style_keywords
- 复用 writer 模型(provider = "writer") —— 改写是创作活动,不是润色活动
- 输出纯文本章节正文(可能很长,需要较大 max_tokens)
- 不落库、不调 critic —— 调用方负责 orchestrator

为什么不用 EditorAgent:
- EditorAgent 输出 JSON 改写映射(逐句),不输出全文
- EditorAgent 复用 editor 模型(provider = "editor"),改写风格偏保守
- RewriteAgent 复用 writer 模型,改写时能动结构/句式

参考: app/agents/editor_agent.py(同质化的 prompt + LLM 调用模式)
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.prompts.editor_prompts import build_critic_guided_rewrite_prompt
from app.services.llm_service import (
    LLMMessage,
    LLMRequest,
    ProviderConfig,
    get_llm_service,
    resolve_provider_config,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RewriteAgent(BaseAgent):
    """[P3.3] Critic 引导的整章改写 Agent。

    设计要点:
    - 同步调 LLM(改写是单次 LLM 完成,不像 generation 是流式)
    - max_tokens 动态由 caller 传入(默认 4096,生成管线下游一般会传 ≥ 6000)
    - 输出清洗:`_strip_think_blocks` 去掉 <think>...</think> 思维链
    - 失败兜底:异常时返回原文 + 错误日志,绝不抛(让 orchestrator 优雅降级)
    """

    async def rewrite_for_critic(
        self,
        content: str,
        *,
        consensus_issues: list[str],
        scores: dict[str, float],
        style_keywords: list[str] | None = None,
        cfg: ProviderConfig | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> str:
        """整章改写 → 返回改写后的纯文本章节正文。

        Args:
            content: 原章节正文
            consensus_issues: critic 共识问题清单(取 top 5)
            scores: 4 子分 + overall dict
            style_keywords: 文风锚
            cfg: provider 配置(None 时走 mock)
            max_tokens: LLM 输出上限
            temperature: 0.5(改写需要稳定性,但也不能完全 deterministic)

        Returns:
            改写后的章节正文(str)。失败时返回原 content(graceful degradation)。
        """
        if not content or not content.strip():
            logger.warning("RewriteAgent: 空内容,直接返回空串")
            return content

        system, user = build_critic_guided_rewrite_prompt(
            chapter_text=content,
            consensus_issues=consensus_issues,
            scores=scores,
            style_keywords=style_keywords,
        )
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]
        model_name = cfg.model if cfg else "mock"
        req = LLMRequest(
            messages=messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )

        try:
            llm = get_llm_service()
            raw = await llm.acomplete(req, cfg)
            cleaned = self._strip_think_blocks(raw)
            if not cleaned or not cleaned.strip():
                logger.warning("RewriteAgent: LLM 返回空,降级返回原文")
                return content
            return cleaned
        except Exception as e:
            logger.warning("RewriteAgent.rewrite_for_critic 失败: %s", e, exc_info=True)
            return content  # graceful degradation

    @staticmethod
    def _strip_think_blocks(text: str) -> str:
        """去掉 <think>...</think> / 思考链块,与 WS generation.py 中的同名 helper 行为一致。"""
        import re
        if not text:
            return ""
        # 去 <think>...</think>(大小写不敏感,可能跨多行)
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
        # 去 ```...```  ``` fence(防御性)
        text = re.sub(r"```[\s\S]*?```", "", text)
        return text.strip()

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """兼容 BaseAgent 接口(供 orchestrator 调用)。"""
        content = context.get("content", "")
        consensus_issues = context.get("consensus_issues", [])
        scores = context.get("scores", {})
        style_keywords = context.get("style_keywords")
        rewritten = await self.rewrite_for_critic(
            content=content,
            consensus_issues=consensus_issues,
            scores=scores,
            style_keywords=style_keywords,
        )
        return {"rewritten_content": rewritten, "status": "done"}


# ============ Factory helpers ============


async def get_rewrite_agent(db: AsyncSession, work_id: Any) -> tuple[RewriteAgent, ProviderConfig | None]:
    """获取 RewriteAgent + 复用 writer provider 的 cfg。

    与 _auto_polish_if_needed 类似:从 work_id 解析 provider,agent 类可单例复用。
    """
    cfg = await resolve_provider_config(db, agent_type="writer")
    return RewriteAgent(), cfg
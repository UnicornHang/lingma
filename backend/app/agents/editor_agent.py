"""Editor Agent - 编辑润色 + AI 痕迹检测与去味

工作流(P2-3 / Beta 范畴):

- ``analyze(text)`` —— 纯检测,跑 AI 痕迹检测器,返回 findings。
  - 不调 LLM,无副作用,可独立用于前端"先看报告再决定要不要改"
- ``polish(text, ...)`` —— 完整去味:detect → 把 findings + 原文喂给 LLM → 让 LLM 逐条重写 → 返回原文+改写映射。
  - 不直接写库;由调用方决定如何落到 chapter.plain_content

兼容旧版 ``execute(context)`` 接口,供 orchestrator 使用。

参考: zenstory-ai/oh-story-claudecode ``skills/story-deslop/`` + ``check-ai-patterns.js``
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.prompts.editor_prompts import (
    build_editor_system_prompt,
    build_editor_user_prompt,
)
from app.services.ai_pattern_detector import (
    AIPatternDetector,
    PatternFinding,
    Severity,
    summarize as summarize_findings,
)
from app.services import prompt_template_service
from app.services.llm_service import (
    LLMError,
    LLMMessage,
    LLMRequest,
    ProviderConfig,
    get_llm_service,
)

logger = logging.getLogger(__name__)


_JSON_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*([\s\S]*?)```", re.DOTALL)


def _extract_json_object(raw: str) -> str | None:
    """尽力从 LLM 输出中抽取首个 JSON object。"""
    if not raw:
        return None
    text = raw.strip()
    m = _JSON_FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


@dataclass(slots=True)
class PolishRewrite:
    """单条 finding 的改写结果"""

    category: str
    original: str
    rewritten: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "original": self.original,
            "rewritten": self.rewritten,
            "reason": self.reason,
        }


@dataclass(slots=True)
class PolishResult:
    """polish() 的完整结果"""

    findings: list[PatternFinding]
    rewrites: list[PolishRewrite]
    polished_text: str  # 把原文按 finding 顺序逐条替换后的成品
    summary: str
    stats: dict

    def to_dict(self) -> dict:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "rewrites": [r.to_dict() for r in self.rewrites],
            "polished_text": self.polished_text,
            "summary": self.summary,
            "stats": self.stats,
        }


class EditorAgent(BaseAgent):
    agent_type = "editor"
    description = "AI 痕迹检测 + 去味润色"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._detector = AIPatternDetector()

    # ==================== 兼容旧版 ====================

    async def execute(self, context: dict) -> dict:
        """兼容 orchestrator 旧调用。

        context 字段:
        - text: 待润色文本(可选,默认空)
        - style_keywords: list[str] 可选
        """
        text = context.get("text", "") or ""
        if not text:
            return {
                "agent": self.agent_type,
                "polished_text": "",
                "suggestions": [],
                "findings": [],
                "message": "EditorAgent: 空文本,跳过",
            }
        findings = self._detector.detect(text)
        return {
            "agent": self.agent_type,
            "polished_text": text,  # 旧版同步模式不重写,只报告
            "suggestions": [f.to_dict() for f in findings],
            "findings": [f.to_dict() for f in findings],
            "stats": summarize_findings(findings),
            "message": f"EditorAgent analyze 完成,共 {len(findings)} 条 finding",
        }

    # ==================== 检测(纯本地,无 LLM) ====================

    def analyze(self, text: str) -> dict:
        """纯本地检测,返回 findings + 统计。"""
        if not text:
            return {
                "findings": [],
                "stats": summarize_findings([]),
                "blocking_count": 0,
                "advisory_count": 0,
            }
        findings = self._detector.detect(text)
        return {
            "findings": [f.to_dict() for f in findings],
            "stats": summarize_findings(findings),
            "blocking_count": sum(1 for f in findings if f.severity == Severity.BLOCKING),
            "advisory_count": sum(1 for f in findings if f.severity == Severity.ADVISORY),
        }

    # ==================== 去味(调 LLM) ====================

    async def polish(
        self,
        text: str,
        *,
        cfg: ProviderConfig | None,
        style_keywords: list[str] | None = None,
        temperature: float = 0.6,
        max_tokens: int = 4096,
        db: AsyncSession | None = None,
    ) -> PolishResult:
        """完整去味流程:detect → LLM 逐条重写 → 应用改写到原文。

        失败行为:
        - LLM 不可用/返回非 JSON → 返回 findings + polished_text=原文本 + 空 rewrites,
          不抛异常(让前端可以选择直接展示报告)
        """
        findings = self._detector.detect(text) if text else []
        if not findings:
            logger.info("EditorAgent polish: 无 AI 痕迹,跳过 LLM")
            return PolishResult(
                findings=[],
                rewrites=[],
                polished_text=text,
                summary="未检测到 AI 痕迹,无需润色",
                stats=summarize_findings([]),
            )

        system = await prompt_template_service.resolve_system_prompt(
            db,
            "editor",
            fallback=build_editor_system_prompt(),
        )
        user = build_editor_user_prompt(
            chapter_text=text,
            findings=findings,
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

        rewrites: list[PolishRewrite] = []
        summary = "本次未执行 LLM 改写"

        llm = get_llm_service()
        try:
            resp = await llm.chat(req, cfg)
            raw = resp.content or ""
            json_text = _extract_json_object(raw)
            if json_text:
                payload = json.loads(json_text)
                rewrites = [
                    PolishRewrite(
                        category=str(r.get("category", "")),
                        original=str(r.get("original", "")),
                        rewritten=str(r.get("rewritten", "")),
                        reason=str(r.get("reason", "")),
                    )
                    for r in payload.get("rewrites", [])
                ]
                summary = str(payload.get("summary", summary))
            else:
                logger.warning(
                    "EditorAgent polish: LLM 输出无法解析为 JSON, raw_len=%d", len(raw)
                )
                summary = "LLM 输出非 JSON,已返回原文 + findings 报告"
        except (LLMError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("EditorAgent polish: LLM 失败或解析失败,降级为仅报告 (%s)", exc)
            summary = f"LLM 失败({exc.__class__.__name__}),已返回原文 + findings 报告"

        polished = self._apply_rewrites(text, findings, rewrites)

        return PolishResult(
            findings=findings,
            rewrites=rewrites,
            polished_text=polished,
            summary=summary,
            stats=summarize_findings(findings),
        )

    # ==================== 工具方法 ====================

    @staticmethod
    def _apply_rewrites(
        original: str,
        findings: list[PatternFinding],
        rewrites: list[PolishRewrite],
    ) -> str:
        """按 finding 顺序,把 rewrites[i].rewritten 替换进 original。

        替换策略:
        - 优先按 snippet 精确匹配替换;匹配不到则按 [start:end] 区间替换
        - rewrites[i].rewritten == rewrites[i].original 时,视为"无需改写",原样保留
        - 任一 finding 替换失败 → 跳过该条,继续后续

        注意:区间替换必须按 start 倒序处理,避免前序替换影响后续 offset。
        """
        if not findings or not rewrites:
            return original

        # 按 start 倒序处理,避免 offset 漂移
        indexed = sorted(
            zip(findings, rewrites), key=lambda pair: pair[0].start, reverse=True
        )
        text = original
        applied = 0
        for f, r in indexed:
            if not r.rewritten or r.rewritten == r.original:
                continue
            replaced = False
            # 1) 按 snippet 全文精确匹配
            if r.original and r.original in text:
                text = text.replace(r.original, r.rewritten, 1)
                replaced = True
            else:
                # 2) 按 finding 的 start:end 区间替换
                if 0 <= f.start < f.end <= len(text):
                    text = text[: f.start] + r.rewritten + text[f.end :]
                    replaced = True
            if replaced:
                applied += 1
        if applied:
            logger.info(
                "EditorAgent: 成功应用 %d/%d 条改写",
                applied,
                len(findings),
            )
        return text


# ==================== 工厂 ====================


_default_editor: Optional[EditorAgent] = None


def get_editor_agent() -> EditorAgent:
    """全局单例(无状态,可重入)。"""
    global _default_editor
    if _default_editor is None:
        _default_editor = EditorAgent()
    return _default_editor

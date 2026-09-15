"""Style Mimic Agent — 仿文：从样本抽风格画像。

MVP：粘贴数章 → LLM（失败则启发式）→ 风格画像 + 短片段。
不写连续性账本，不产出大纲骨架。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.character_agent import _extract_json_object
from app.prompts.style_mimic_prompts import (
    build_style_mimic_system_prompt,
    build_style_mimic_user_prompt,
)
from app.schemas.style_mimic import StylePortrait, StyleSnippet
from app.services import prompt_template_service
from app.services.llm_service import (
    LLMError,
    LLMMessage,
    LLMRequest,
    get_llm_service,
    resolve_provider_config,
)

logger = logging.getLogger(__name__)

# MVP 分析窗口：约数章；禁止整书一次塞入
_MAX_SAMPLE_CHARS = 12_000
_MIN_SAMPLE_CHARS = 200
_MAX_SNIPPETS = 5
_SNIPPET_MAX_LEN = 120


class StyleMimicAgent(BaseAgent):
    """仿文 Agent：学习文笔文风，产出风格记忆。"""

    agent_type = "style_mimic"
    description = "导入样本学习文笔文风，生成风格画像供 Writer 写前引用"

    async def execute(self, context: dict) -> dict:
        """编排器兼容占位。"""
        return {
            "agent": self.agent_type,
            "message": "请使用 analyze_sample() 真实实现",
            "work_id": context.get("work_id"),
        }

    async def analyze_sample(
        self,
        db: AsyncSession,
        *,
        sample_text: str,
        source_label: str = "",
        work_id=None,
    ) -> tuple[StylePortrait, str, list[StyleSnippet], str, bool]:
        """分析样本文本。

        返回: (portrait, writing_directives, snippets, model_used, used_heuristic)
        """
        text = _prepare_sample(sample_text)
        if len(text) < _MIN_SAMPLE_CHARS:
            raise ValueError(f"样本文本至少 {_MIN_SAMPLE_CHARS} 字")

        cfg = await resolve_provider_config(
            db, agent_type=self.agent_type, work_id=work_id
        )
        if cfg is None:
            # 无独立绑定则回退 writer 配置
            cfg = await resolve_provider_config(db, agent_type="writer", work_id=work_id)
        model_name = cfg.model if cfg else "mock"

        system_msg = await prompt_template_service.resolve_system_prompt(
            db,
            "style_mimic",
            fallback=build_style_mimic_system_prompt(),
        )
        user_msg = build_style_mimic_user_prompt(
            sample_text=text, source_label=source_label
        )

        raw = ""
        used_heuristic = False
        try:
            llm = get_llm_service()
            resp = await llm.chat(
                LLMRequest(
                    messages=[
                        LLMMessage(role="system", content=system_msg),
                        LLMMessage(role="user", content=user_msg),
                    ],
                    model=model_name,
                    temperature=0.4,
                    max_tokens=2048,
                    stream=False,
                ),
                cfg,
            )
            raw = resp.content or ""
            model_name = resp.model or model_name
        except (LLMError, Exception) as exc:
            logger.warning("StyleMimicAgent LLM 失败，改用启发式: %s", exc)
            used_heuristic = True

        parsed = parse_style_mimic_payload(raw) if raw else None
        if parsed is None:
            portrait, directives, snippets = heuristic_style_from_text(text)
            used_heuristic = True
            return portrait, directives, snippets, model_name, used_heuristic

        return (*parsed, model_name, used_heuristic)


def _prepare_sample(sample_text: str) -> str:
    """清洗并截断样本。"""
    text = (sample_text or "").strip()
    if len(text) > _MAX_SAMPLE_CHARS:
        half = _MAX_SAMPLE_CHARS // 2
        text = text[:half] + "\n…(中间已截断)…\n" + text[-half:]
    return text


def parse_style_mimic_payload(
    raw: str,
) -> tuple[StylePortrait, str, list[StyleSnippet]] | None:
    """解析 LLM JSON；失败返回 None。"""
    blob = _extract_json_object(raw)
    if not blob:
        return None
    try:
        data: dict[str, Any] = json.loads(blob)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    portrait_raw = data.get("portrait") or {}
    if not isinstance(portrait_raw, dict):
        portrait_raw = {}
    portrait = StylePortrait(
        narrative_pov=str(portrait_raw.get("narrative_pov") or ""),
        avg_sentence_len=str(portrait_raw.get("avg_sentence_len") or ""),
        dialogue_density=str(portrait_raw.get("dialogue_density") or ""),
        rhetoric_habits=_as_str_list(portrait_raw.get("rhetoric_habits")),
        pacing_tags=_as_str_list(portrait_raw.get("pacing_tags")),
        emotional_style=str(portrait_raw.get("emotional_style") or ""),
        lexicon_notes=str(portrait_raw.get("lexicon_notes") or ""),
    )
    directives = str(data.get("writing_directives") or "").strip()
    if not directives:
        directives = _directives_from_portrait(portrait)

    snippets: list[StyleSnippet] = []
    for item in data.get("snippets") or []:
        if len(snippets) >= _MAX_SNIPPETS:
            break
        if isinstance(item, str) and item.strip():
            snippets.append(
                StyleSnippet(tag="通用", text=item.strip()[:_SNIPPET_MAX_LEN])
            )
            continue
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        tag = str(item.get("tag") or "通用").strip() or "通用"
        snippets.append(StyleSnippet(tag=tag[:20], text=text[:_SNIPPET_MAX_LEN]))

    return portrait, directives, snippets


def heuristic_style_from_text(
    text: str,
) -> tuple[StylePortrait, str, list[StyleSnippet]]:
    """无 LLM 时的统计启发式画像，保证 MVP 可离线预览。"""
    sentences = [s.strip() for s in re.split(r"[。！？!?；;\n]+", text) if s.strip()]
    avg_len = (
        sum(len(s) for s in sentences) / len(sentences) if sentences else len(text)
    )
    if avg_len < 18:
        sent_label = "偏短"
    elif avg_len > 40:
        sent_label = "偏长"
    else:
        sent_label = "中等"

    quote_chars = text.count("「") + text.count("」") + text.count('"') + text.count("“")
    density_ratio = quote_chars / max(len(text), 1)
    if density_ratio > 0.04:
        dialogue = "高"
    elif density_ratio > 0.015:
        dialogue = "中"
    else:
        dialogue = "低"

    portrait = StylePortrait(
        narrative_pov="第三人称（启发式未判定）",
        avg_sentence_len=sent_label,
        dialogue_density=dialogue,
        rhetoric_habits=["动作推进"] if sent_label == "偏短" else ["描写铺陈"],
        pacing_tags=["快节奏"] if sent_label == "偏短" else ["舒缓"],
        emotional_style="由样本统计推断，建议人工核对",
        lexicon_notes=f"样本约 {len(text)} 字，平均句长约 {avg_len:.0f}",
    )
    directives = _directives_from_portrait(portrait)
    snippets = _pick_heuristic_snippets(sentences)
    return portrait, directives, snippets


def _directives_from_portrait(portrait: StylePortrait) -> str:
    """由画像拼一段写前指令。"""
    return (
        f"叙事倾向「{portrait.narrative_pov or '跟随大纲'}」；"
        f"句长「{portrait.avg_sentence_len or '中等'}」；"
        f"对话密度「{portrait.dialogue_density or '中'}」。"
        f"{'；'.join(portrait.rhetoric_habits[:3])}。"
        "学技法与节奏，禁止照抄专有名词、桥段与原文长句。"
    )


def _pick_heuristic_snippets(sentences: list[str]) -> list[StyleSnippet]:
    """从样本挑短句作技法示意（截断，非整章）。"""
    out: list[StyleSnippet] = []
    for s in sentences:
        if len(out) >= 3:
            break
        if 20 <= len(s) <= _SNIPPET_MAX_LEN:
            # 粗暴抹去可能的引号人名痕迹感：过长专有名词不处理，仅截断
            out.append(StyleSnippet(tag="通用", text=s[:_SNIPPET_MAX_LEN]))
    return out


def _as_str_list(value: Any) -> list[str]:
    """把任意字段规范成短字符串列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()][:8]
    return []

"""Character Agent - 角色设计

真实实现：基于 Work 上下文 + 已有角色清单，调用 LLM 生成 N 个 CharacterCard。
- 强 schema 校验：LLM 输出不符合 CharacterCard 时返回空 list，不抛 500。
- 不直接写库：返回建议列表由前端调用 `POST /characters` 写入。
- 兼容旧版 `execute(context)` 接口（orchestrator 调用方保持不变）。
"""
from __future__ import annotations

import json
import logging
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.models.character import Character
from app.models.work import Work
from app.prompts.character_prompts import (
    build_character_system_prompt,
    build_character_user_prompt,
)
from app.schemas.character import CharacterCard
from app.services import prompt_template_service
from app.services.llm_service import (
    LLMError,
    LLMMessage,
    LLMRequest,
    get_llm_service,
    resolve_provider_config,
)

logger = logging.getLogger(__name__)


# 用于在 LLM 输出偶尔包了一层 markdown fence 时容错抽取
_JSON_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*([\s\S]*?)```", re.DOTALL)
_THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)


def _strip_llm_think(raw: str) -> str:
    """去掉 MiniMax 等模型的 <think> 思维链，避免把思考稿当成 JSON。"""
    text = _THINK_BLOCK_RE.sub("", raw)
    leftover = re.search(r"<think>", text, re.IGNORECASE)
    if leftover:
        rest = text[leftover.end() :]
        vol_at = rest.find('{"volumes"')
        brace_at = rest.find("{")
        cut = vol_at if vol_at >= 0 else brace_at
        text = rest[cut:] if cut >= 0 else text[: leftover.start()]
    return text.strip()


def _matching_brace_end(text: str, start: int) -> int | None:
    """返回与 text[start]=='{' 配对的 '}' 下标；截断或不平衡则 None。"""
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
                return i
    return None


def _extract_json_object(raw: str) -> str | None:
    """从 LLM 输出中尽力抽取 JSON object。

    处理:
    - <think> 思维链
    - 开头/结尾的说明文字
    - markdown fence ```json ... ```
    - 多个大括号对象时取最长的一份（优先含 volumes）
    - 顶层 JSON 被截断时仍返回从 { 起的原文，供上层 salvage
    """
    if not raw:
        return None
    text = _strip_llm_think(raw)
    if not text:
        return None

    m = _JSON_FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()

    candidates: list[str] = []
    search_from = 0
    while True:
        start = text.find("{", search_from)
        if start < 0:
            break
        end = _matching_brace_end(text, start)
        if end is None:
            dangling = text[start:]
            if '"volumes"' in dangling[:800] or dangling.lstrip().startswith("{"):
                candidates.append(dangling)
            break
        candidates.append(text[start : end + 1])
        search_from = start + 1

    if not candidates:
        return None
    with_volumes = [c for c in candidates if '"volumes"' in c[:2000]]
    pool = with_volumes or candidates
    return max(pool, key=len)


class CharacterAgent(BaseAgent):
    agent_type = "character"
    description = "设计人物档案：背景/性格/动机/人物弧"

    # ------- 兼容旧版 orchestrator 调用 -------

    async def execute(self, context: dict) -> dict:
        work_id = context.get("work_id")
        return {
            "agent": self.agent_type,
            "work_id": str(work_id) if work_id else None,
            "characters": [],
            "message": "Character Agent MVP 占位输出（请使用 suggest() 真实实现）",
        }

    # ------- 真实实现 -------

    async def suggest(
        self,
        db: AsyncSession,
        *,
        work_id: UUID,
        count: int,
        focus: str,
        extra_hint: str | None = None,
    ) -> tuple[list[CharacterCard], str, str]:
        """生成 N 个角色卡。

        返回: (cards, model_used, raw_content)
        - cards: 强 schema 校验通过的列表；失败时为空列表
        - model_used: 实际调用的模型名（"mock" 表示走 mock provider）
        - raw_content: LLM 原始输出，便于调试
        """
        # 1) 加载 work
        work = await _load_work(db, work_id)
        if work is None:
            logger.error("CharacterAgent.suggest: work %s 不存在", work_id)
            return [], "mock", ""

        # 2) 加载已有角色(用于避免重名)
        existing = await _load_existing_characters(db, work_id)

        # 3) 构造 prompt
        system_msg = await prompt_template_service.resolve_system_prompt(
            db,
            "character",
            fallback=build_character_system_prompt(),
        )
        user_msg = build_character_user_prompt(
            work=work,
            existing_characters=existing,
            count=count,
            focus=focus,
            extra_hint=extra_hint,
        )

        # 4) 解析 provider 配置
        cfg = await resolve_provider_config(db, agent_type=self.agent_type, work_id=work_id)
        model_name = cfg.model if cfg else "mock"

        # 5) 调用 LLM（非流式 JSON）
        llm = get_llm_service()
        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=system_msg),
                LLMMessage(role="user", content=user_msg),
            ],
            model=model_name,
            temperature=0.85,
            max_tokens=min(8192, 1500 + count * 600),
            stream=False,
        )

        raw_content = ""
        try:
            resp = await llm.chat(req, cfg)
            raw_content = resp.content or ""
        except LLMError as e:
            logger.error("CharacterAgent LLM 调用失败: %s", e, exc_info=True)
            return [], model_name, raw_content
        except Exception as e:
            logger.error("CharacterAgent 异常: %s", e, exc_info=True)
            return [], model_name, raw_content

        # 6) 抽取 + 解析 JSON
        json_text = _extract_json_object(raw_content)
        if not json_text:
            logger.warning(
                "CharacterAgent LLM 输出中找不到 JSON: model=%s, raw_len=%d",
                model_name, len(raw_content),
            )
            return [], model_name, raw_content

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(
                "CharacterAgent JSON 解析失败: %s; text_head=%s",
                e, json_text[:200],
            )
            return [], model_name, raw_content

        # 兼容 LLM 直接给 list 或给 {cards: [...]} 两种结构
        cards_payload = parsed.get("cards") if isinstance(parsed, dict) else parsed
        if not isinstance(cards_payload, list):
            logger.warning("CharacterAgent JSON.cards 不是 list: %s", type(cards_payload))
            return [], model_name, raw_content

        # 7) 强 schema 校验：逐条 Pydantic 解析（单条失败仅丢弃，不影响其他）
        cards: list[CharacterCard] = []
        for i, item in enumerate(cards_payload):
            if not isinstance(item, dict):
                logger.warning("CharacterAgent 第 %d 张不是 dict: %r", i, item)
                continue
            try:
                cards.append(CharacterCard.model_validate(item))
            except Exception as e:
                logger.warning("CharacterAgent 第 %d 张校验失败: %s; raw=%r", i, e, item)
                continue

        logger.info(
            "CharacterAgent.suggest: work=%s, count=%s, focus=%s, model=%s, generated=%d",
            work_id, count, focus, model_name, len(cards),
        )
        return cards, model_name, raw_content


# ==================== DB 加载辅助 ====================


async def _load_work(db: AsyncSession, work_id: UUID) -> Work | None:
    r = await db.execute(select(Work).where(Work.id == work_id))
    return r.scalar_one_or_none()


async def _load_existing_characters(db: AsyncSession, work_id: UUID) -> list[Character]:
    r = await db.execute(
        select(Character).where(Character.work_id == work_id).order_by(Character.created_at.asc())
    )
    return list(r.scalars().all())

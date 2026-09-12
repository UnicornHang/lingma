"""Writer Agent - 章节正文写作（真实 LLM 接入版）

工作流：
1. 加载上下文（作品 / 章节 / 大纲 / 世界书 / 角色）
2. 由 `prompts.writer_prompts` 组装 system+user 消息
3. 调用 `LLMService.stream()` 产出 delta
4. 不在此处持久化 —— 由上层（ws handler）负责保存章节
"""
from __future__ import annotations

import logging
from typing import AsyncIterator, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.models.character import Character
from app.models.chapter import Chapter
from app.models.outline import OutlineNode
from app.models.work import Work
from app.models.world import WorldBible
from app.prompts.writer_prompts import build_system_prompt, build_user_prompt
from app.services.llm_service import (
    LLMMessage,
    LLMRequest,
    ProviderConfig,
    get_llm_service,
)
from app.services.world_service import get_or_create_world_bible

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    agent_type = "writer"
    description = "基于大纲 + 上下文生成章节正文"

    # ------- 兼容性：旧版一次性调用 -------

    async def execute(self, context: dict) -> dict:
        chapter_id = context.get("chapter_id")
        target_words = context.get("target_word_count", 3000)
        return {
            "agent": self.agent_type,
            "chapter_id": str(chapter_id) if chapter_id else None,
            "content": f"[Writer 占位] 已根据上下文规划 {target_words} 字章节内容...",
            "word_count": 0,
            "message": "Writer Agent MVP 占位输出",
        }

    # ------- 流式生成（P2-1 核心） -------

    async def stream(
        self,
        db: AsyncSession,
        chapter_id: UUID,
        cfg: ProviderConfig | None,
        *,
        override_messages: list[LLMMessage] | None = None,
        temperature: float = 0.85,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """流式生成章节正文。

        - ``override_messages`` 用于调试/单测直接注入 prompt，跳过 DB 加载
        - ``cfg=None`` 时 LLMService 自动回退到 mock
        """
        llm = get_llm_service()
        if override_messages is not None:
            messages = override_messages
            req = LLMRequest(
                messages=messages,
                model=(cfg.model if cfg else "mock"),
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for delta in llm.stream(req, cfg):
                yield delta
            return

        # ===== 加载上下文 =====
        chapter = await _load_chapter(db, chapter_id)
        work = await _load_work(db, chapter.work_id)
        outline = await _load_outline_node(db, chapter.outline_node_id) if chapter.outline_node_id else None
        world = await _maybe_load_world(db, chapter.work_id)
        characters = await _load_characters(db, chapter.work_id)
        previous_summary = await _load_previous_chapter_summary(db, chapter)

        target_words = (
            outline.target_word_count if outline and outline.target_word_count else 3000
        )

        # ===== 构建消息 =====
        system = build_system_prompt(target_words)
        user = build_user_prompt(
            work=work,
            chapter=chapter,
            outline=outline,
            world=world,
            characters=characters,
            previous_summary=previous_summary,
        )
        messages = [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]

        model_name = cfg.model if cfg else "mock"
        req = LLMRequest(
            messages=messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        logger.info(
            "WriterAgent stream 启动: chapter=%s, model=%s, target=%s字",
            chapter_id, model_name, target_words,
        )
        async for delta in llm.stream(req, cfg):
            yield delta

    # ------- 消息装配（供 WS / 测试复用） -------

    async def build_messages(
        self,
        db: AsyncSession,
        chapter_id: UUID,
        *,
        mode: Literal["continue", "generate"] = "generate",
        continue_from_chars: int = 1500,
        target_word_count: int | None = None,
    ) -> tuple[list[LLMMessage], str, str]:
        """加载上下文并装配 system + user 消息。

        返回: (messages, model_name, user_prompt_text)
        - ``mode="continue"`` 且章节有 plain_content 时,会取末尾 N 字作为 existing_tail
        - ``mode="continue"`` 且章节为空时,降级为 ``generate`` 语义(避免给 LLM 看空块)
        - ``target_word_count``(来自请求)优先于 outline 默认值
        """
        chapter = await _load_chapter(db, chapter_id)
        work = await _load_work(db, chapter.work_id)
        outline = (
            await _load_outline_node(db, chapter.outline_node_id)
            if chapter.outline_node_id
            else None
        )
        world = await _maybe_load_world(db, chapter.work_id)
        characters = await _load_characters(db, chapter.work_id)
        previous_summary = await _load_previous_chapter_summary(db, chapter)

        # 计算有效目标字数:请求 > outline > 默认 3000
        effective_target = target_word_count
        if not effective_target:
            effective_target = (
                outline.target_word_count if outline and outline.target_word_count else 3000
            )

        # 续写模式:取正文末尾 N 字;空章节则降级为 generate
        existing_tail: str | None = None
        effective_mode = mode
        if mode == "continue":
            tail_source = (chapter.plain_content or "").strip()
            if tail_source:
                existing_tail = tail_source[-continue_from_chars:]
            else:
                logger.info(
                    "WriterAgent build_messages: 章节 %s 正文为空,降级为 generate 模式",
                    chapter_id,
                )
                effective_mode = "generate"

        system = build_system_prompt(effective_target)
        user = build_user_prompt(
            work=work,
            chapter=chapter,
            outline=outline,
            world=world,
            characters=characters,
            previous_summary=previous_summary,
            existing_tail=existing_tail,
            target_word_count=effective_target,
        )
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]
        logger.info(
            "WriterAgent build_messages: chapter=%s, mode=%s, target=%s字",
            chapter_id,
            effective_mode,
            effective_target,
        )
        return messages, "mock", user


# ==================== DB 加载辅助 ====================


async def _load_chapter(db: AsyncSession, chapter_id: UUID) -> Chapter:
    r = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    ch = r.scalar_one_or_none()
    if not ch:
        raise ValueError(f"chapter {chapter_id} 不存在")
    return ch


async def _load_work(db: AsyncSession, work_id: UUID) -> Work:
    r = await db.execute(select(Work).where(Work.id == work_id))
    w = r.scalar_one_or_none()
    if not w:
        raise ValueError(f"work {work_id} 不存在")
    return w


async def _load_outline_node(db: AsyncSession, node_id: UUID) -> OutlineNode | None:
    r = await db.execute(select(OutlineNode).where(OutlineNode.id == node_id))
    return r.scalar_one_or_none()


async def _maybe_load_world(db: AsyncSession, work_id: UUID) -> WorldBible | None:
    try:
        return await get_or_create_world_bible(db, work_id)
    except Exception:
        return None


async def _load_characters(db: AsyncSession, work_id: UUID, limit: int = 8) -> list[Character]:
    r = await db.execute(
        select(Character).where(Character.work_id == work_id).limit(limit)
    )
    return list(r.scalars().all())


async def _load_previous_chapter_summary(db: AsyncSession, chapter: Chapter) -> str | None:
    """取按 created_at 排在本章之前的最近一章摘要，避免重复叙事。"""
    r = await db.execute(
        select(Chapter)
        .where(Chapter.work_id == chapter.work_id, Chapter.id != chapter.id)
        .order_by(Chapter.created_at.desc())
        .limit(1)
    )
    prev = r.scalar_one_or_none()
    if not prev:
        return None
    return prev.summary or (prev.plain_content[:300] if prev.plain_content else None)
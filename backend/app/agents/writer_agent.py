"""Writer Agent - 章节正文写作（真实 LLM 接入版）

工作流：
1. 加载上下文（作品 / 章节 / 大纲 / 同卷大纲 / 世界书 / 角色）
2. 由 `prompts.writer_prompts` 组装 system+user 消息
3. 调用 `LLMService.stream()` 产出 delta
4. 不在此处持久化 —— 由上层（ws handler）负责保存章节

[P3 增强] build_messages 现在支持 ``outline_node_id`` 显式参数,并:
- 同卷(同 parent_id)其他章节大纲注入
- 本章相关角色优先(按 outline.characters_involved 匹配已有 Character)
- 本章相关世界条目作为强提示注入

[提交 B] 装配升级为确定性 slot + Reference Gate:
- ``build_user_prompt`` 委托给 ``writer_slots.assemble_writer_slots``
- pre-write Reference Gate 根据章节角色(opening/reveal/climax/transition)
  路由不同 references,确保 LLM 看到必需的世界书/角色卡片段
- 日志输出 slot 数 + 总字数 + 截断列表
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.config import settings
from app.models.character import Character
from app.models.chapter import Chapter
from app.models.outline import OutlineNode, OutlineNodeType
from app.models.work import Work
from app.models.world import WorldBible
from app.prompts.writer_prompts import build_system_prompt, build_user_prompt
from app.schemas.rag import RagHit
from app.services import prompt_template_service
from app.services.chapter_role_resolver import (
    ChapterRole,
    ReferenceHints,
    apply_reference_gate,
    references_for_role,
    resolve_chapter_role,
)
from app.services.llm_service import (
    LLMMessage,
    LLMRequest,
    ProviderConfig,
    get_llm_service,
)
from app.services.rag_service import get_rag_service
from app.services.tracking_service import build_writer_context_card
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
        outline_node_id: UUID | None = None,
    ) -> AsyncIterator[str]:
        """流式生成章节正文。

        - ``override_messages`` 用于调试/单测直接注入 prompt，跳过 DB 加载
        - ``cfg=None`` 时 LLMService 自动回退到 mock
        - ``outline_node_id`` 显式覆盖（可选,默认从 chapter.outline_node_id 取）
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

        # ===== 加载上下文（精细化版本）=====
        chapter = await _load_chapter(db, chapter_id)
        work = await _load_work(db, chapter.work_id)
        outline = await _load_outline_node(db, outline_node_id or chapter.outline_node_id)
        world = await _maybe_load_world(db, chapter.work_id)
        characters = await _load_focused_characters(db, chapter.work_id, outline)
        same_volume_outline = await _load_same_volume_outline(db, outline)
        previous_summary = await _load_previous_chapter_summary(db, chapter)

        # ===== RAG 检索（可优雅降级）=====
        rag_hits = await _search_rag_hits(db, chapter, outline)
        continuity = await _load_continuity(db, chapter.work_id, outline, characters)

        target_words = (
            outline.target_word_count if outline and outline.target_word_count else 3000
        )

        # ===== 构建消息 =====
        system = await prompt_template_service.resolve_system_prompt(
            db,
            "writer",
            variables={"target_words": str(target_words)},
            fallback=build_system_prompt(target_words),
        )
        user = build_user_prompt(
            work=work,
            chapter=chapter,
            outline=outline,
            world=world,
            characters=characters,
            previous_summary=previous_summary,
            same_volume_outline=same_volume_outline,
            world_refs=(outline.world_refs if outline else None),
            rag_hits=rag_hits,
            continuity=continuity,
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
            "WriterAgent stream 启动: chapter=%s, outline=%s, model=%s, target=%s字, 同卷章=%d, 聚焦角色=%d",
            chapter_id,
            outline.id if outline else None,
            model_name,
            target_words,
            len(same_volume_outline),
            len(characters),
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
        outline_node_id: UUID | None = None,
        chapter_role: ChapterRole | None = None,
    ) -> tuple[list[LLMMessage], str, str]:
        """加载上下文并装配 system + user 消息。

        返回: (messages, model_name, user_prompt_text)
        - ``mode="continue"`` 且章节有 plain_content 时,会取末尾 N 字作为 existing_tail
        - ``mode="continue"`` 且章节为空时,降级为 ``generate`` 语义(避免给 LLM 看空块)
        - ``target_word_count``(来自请求)优先于 outline 默认值
        - ``outline_node_id``(来自请求)优先于 chapter.outline_node_id
        - ``chapter_role``(可选):外部传入的章节角色判定;缺省时由 outline 启发式推断
        """
        chapter = await _load_chapter(db, chapter_id)
        work = await _load_work(db, chapter.work_id)
        resolved_outline_id = outline_node_id or chapter.outline_node_id
        outline = (
            await _load_outline_node(db, resolved_outline_id)
            if resolved_outline_id
            else None
        )
        world = await _maybe_load_world(db, chapter.work_id)
        characters = await _load_focused_characters(db, chapter.work_id, outline)
        same_volume_outline = await _load_same_volume_outline(db, outline)
        previous_summary = await _load_previous_chapter_summary(db, chapter)

        rag_hits = await _search_rag_hits(db, chapter, outline)
        continuity = await _load_continuity(db, chapter.work_id, outline, characters)

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

        # ===== Reference Gate =====
        # 1) 章节角色判定:外部传入优先,否则由 outline 启发式推断
        resolved_role = chapter_role or resolve_chapter_role(outline)
        # 2) 根据角色拿到 ReferenceHints
        hints = references_for_role(resolved_role, outline)
        # 3) 实际应用 hints 到 world/characters
        effective_world, effective_characters = apply_reference_gate(
            outline=outline,
            world=world,
            characters=characters,
            hints=hints,
        )

        system = await prompt_template_service.resolve_system_prompt(
            db,
            "writer",
            variables={"target_words": str(effective_target)},
            fallback=build_system_prompt(effective_target),
        )
        user = build_user_prompt(
            work=work,
            chapter=chapter,
            outline=outline,
            world=effective_world,
            characters=effective_characters,
            previous_summary=previous_summary,
            existing_tail=existing_tail,
            target_word_count=effective_target,
            same_volume_outline=same_volume_outline,
            world_refs=(outline.world_refs if outline else None),
            reference_hints=hints,
            rag_hits=rag_hits,
            continuity=continuity,
        )
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]

        # 简要统计 slot 数(从 user 文本倒推)
        slot_marks = [
            "【作品总览】", "【文风裁决】", "【本章约束锁】", "【本章大纲】", "【Reference Gate 必读】",
            "【同卷其他章节", "【世界书", "【世界条目", "【出场角色】", "【角色当前状态】",
            "【RAG 向量检索补充】", "【待收伏笔】", "【知情范围】",
            "【上一章摘要】", "【本章已有正文", "【本章任务】",
        ]
        slots_present = [m for m in slot_marks if m in user]
        logger.info(
            "WriterAgent build_messages: chapter=%s, mode=%s, target=%s字, "
            "chapter_role=%s, slots=%d/%d, user_chars=%d, 同卷章=%d, 聚焦角色=%d",
            chapter_id,
            effective_mode,
            effective_target,
            resolved_role.value,
            len(slots_present),
            len(slot_marks),
            len(user),
            len(same_volume_outline),
            len(effective_characters),
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


async def _load_outline_node(db: AsyncSession, node_id: UUID | None) -> OutlineNode | None:
    if not node_id:
        return None
    r = await db.execute(select(OutlineNode).where(OutlineNode.id == node_id))
    return r.scalar_one_or_none()


async def _maybe_load_world(db: AsyncSession, work_id: UUID) -> WorldBible | None:
    try:
        return await get_or_create_world_bible(db, work_id)
    except Exception:
        return None


async def _load_focused_characters(
    db: AsyncSession,
    work_id: UUID,
    outline: OutlineNode | None,
    *,
    fallback_limit: int = 8,
) -> list[Character]:
    """根据 outline.characters_involved 精细筛选角色;缺失时降级到 work_id 取前 N。

    返回顺序:聚焦角色(按 outline 列表顺序)在前,补充角色在后。
    """
    if outline and outline.characters_involved:
        names = [n for n in outline.characters_involved if n]
        if names:
            # 1) 精确匹配 (name == ?)
            stmt = select(Character).where(
                Character.work_id == work_id,
                Character.name.in_(names),
            )
            focused = list((await db.execute(stmt)).scalars().all())
            if focused:
                # 按 outline 列表顺序排序
                name_to_idx = {n: i for i, n in enumerate(names)}
                focused.sort(key=lambda c: name_to_idx.get(c.name, 9999))
                # 2) 若未达到 fallback_limit,补充 work 下其他角色
                if len(focused) < fallback_limit:
                    extra_stmt = (
                        select(Character)
                        .where(
                            Character.work_id == work_id,
                            ~Character.id.in_([c.id for c in focused]),
                        )
                        .limit(fallback_limit - len(focused))
                    )
                    extra = list((await db.execute(extra_stmt)).scalars().all())
                    focused.extend(extra)
                return focused[:fallback_limit]
    # 降级路径
    return await _load_characters(db, work_id, limit=fallback_limit)


async def _load_same_volume_outline(
    db: AsyncSession,
    outline: OutlineNode | None,
) -> list[OutlineNode]:
    """加载同卷(同 parent_id)其他章节大纲,作为上下文连贯性参考。

    仅取 type=chapter 的同级节点,按 order 排序。
    """
    if outline is None or outline.parent_id is None:
        return []
    r = await db.execute(
        select(OutlineNode)
        .where(
            OutlineNode.parent_id == outline.parent_id,
            OutlineNode.id != outline.id,
            OutlineNode.type == OutlineNodeType.CHAPTER,
        )
        .order_by(OutlineNode.order.asc(), OutlineNode.created_at.asc())
    )
    return list(r.scalars().all())


async def _load_characters(db: AsyncSession, work_id: UUID, limit: int = 8) -> list[Character]:
    """降级:按 work_id 取前 N 个角色(保留旧行为)。"""
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


async def _load_continuity(
    db: AsyncSession,
    work_id: UUID,
    outline: OutlineNode | None,
    characters: list[Character],
):
    """加载写前连续性上下文卡；失败时降级为 None，不阻断写作。"""
    try:
        return await build_writer_context_card(
            db, work_id, outline=outline, characters=characters
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("WriterAgent 追踪上下文加载失败(已降级): %s", exc)
        return None


async def _search_rag_hits(
    db: AsyncSession,
    chapter: Chapter,
    outline: OutlineNode | None,
    *,
    timeout_s: float = 2.0,
) -> list[RagHit]:
    """从 RAG 检索与本章相关的历史上下文。

    行为契约:
    - ``settings.rag_enabled=False`` → 立即返回 []
    - 任何异常 / 超时 → 记 warning 后返回 [],不阻塞章节生成
    - query 由 outline.summary + chapter.summary + chapter.title 拼接(空字段过滤)
    - 取 ``settings.rag_top_k`` 条
    """
    if not settings.rag_enabled:
        return []
    try:
        query_parts = [
            (outline.summary if outline and outline.summary else ""),
            (chapter.summary or ""),
            (chapter.title or ""),
        ]
        query = " ".join(p for p in query_parts if p and p.strip())
        if not query:
            return []
        hits = await asyncio.wait_for(
            get_rag_service().search(
                work_id=chapter.work_id,
                query=query,
                top_k=settings.rag_top_k,
            ),
            timeout=timeout_s,
        )
        if hits:
            logger.info(
                "WriterAgent RAG 检索: chapter=%s, hits=%d, query_len=%d",
                chapter.id, len(hits), len(query),
            )
        return hits
    except asyncio.TimeoutError:
        logger.warning(
            "WriterAgent RAG 检索超时(%.1fs): chapter=%s", timeout_s, chapter.id,
        )
        return []
    except Exception as e:
        logger.warning("WriterAgent RAG 检索失败(已降级): %s", e)
        return []

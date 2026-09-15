"""World bible 业务逻辑层"""
import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.world_agent import WorldAgent
from app.models.world import WorldBible
from app.schemas.world import (
    ConsistencyCheckResponse,
    WorldBibleCreate,
    WorldBibleUpdate,
)
from app.services import work_service
from app.services.chapter_service import get_chapter
from app.services.rag_service import get_rag_service
from app.services.world_consistency import (
    extract_rule_lines,
    heuristic_scan,
    is_world_empty,
    merge_issues,
    serialize_world_brief,
)

logger = logging.getLogger(__name__)


async def _try_index_world(db: AsyncSession, bible: WorldBible) -> None:
    """RAG 索引世界书(失败仅 log,不阻塞业务)。"""
    try:
        n = await get_rag_service().index_world(db, bible)
        if n > 0:
            logger.info("RAG 索引世界书: work=%s, chunks=%d", bible.work_id, n)
    except Exception as e:  # pragma: no cover - 防御
        logger.warning("RAG 索引世界书失败(已降级): %s", e)


async def get_or_create_world_bible(db: AsyncSession, work_id: UUID) -> WorldBible:
    """获取作品的世界书；不存在则创建空记录"""
    result = await db.execute(
        select(WorldBible).where(WorldBible.work_id == work_id)
    )
    bible = result.scalar_one_or_none()
    if bible is None:
        bible = WorldBible(work_id=work_id)
        db.add(bible)
        await db.flush()
        await db.refresh(bible)
    return bible


async def create_world_bible(db: AsyncSession, payload: WorldBibleCreate) -> WorldBible:
    existing = await db.execute(
        select(WorldBible).where(WorldBible.work_id == payload.work_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"作品 {payload.work_id} 已存在世界书，请使用 PATCH 更新",
        )
    bible = WorldBible(
        work_id=payload.work_id,
        geography=payload.geography,
        factions=payload.factions,
        power_system=payload.power_system,
        timeline=payload.timeline,
        rules=payload.rules,
        culture=payload.culture,
        raw_text=payload.raw_text,
    )
    db.add(bible)
    await db.flush()
    await db.refresh(bible)
    await _try_index_world(db, bible)
    return bible


async def update_world_bible(
    db: AsyncSession, work_id: UUID, payload: WorldBibleUpdate
) -> WorldBible:
    bible = await get_or_create_world_bible(db, work_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(bible, key, value)
    await db.flush()
    await db.refresh(bible)
    await _try_index_world(db, bible)
    return bible


async def check_consistency(
    db: AsyncSession,
    work_id: UUID,
    *,
    text: str | None = None,
    chapter_id: UUID | None = None,
) -> ConsistencyCheckResponse:
    """对照世界书检查正文(或世界书自检)。

    - 提供 text:直接检查该文本
    - 仅 chapter_id:用章节 plain_content
    - 都空:用 raw_text 做世界书内部自检(规则 vs 自然语言)
    """
    await work_service.get_work(db, work_id)
    bible = await get_or_create_world_bible(db, work_id)
    chapter_title: str | None = None
    checked = (text or "").strip()
    # 外部正文才跑启发式,避免用规则原文自检时误报
    external_text = bool(checked)

    if chapter_id is not None:
        chapter = await get_chapter(db, chapter_id)
        if chapter.work_id != work_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="章节不属于该作品",
            )
        chapter_title = chapter.title
        if not checked:
            checked = (chapter.plain_content or "").strip()
            external_text = bool(checked)

    world_empty = is_world_empty(bible)
    if world_empty:
        return ConsistencyCheckResponse(
            passed=True,
            issue_count=0,
            issues=[],
            summary="世界书为空，无法对照校验。请先填写世界观圣经。",
            model_used="none",
            checked_chars=len(checked),
            world_empty=True,
        )

    if not checked:
        checked = (bible.raw_text or "").strip()
        if not checked:
            checked = serialize_world_brief(bible)

    rules = extract_rule_lines(bible)
    heuristic = heuristic_scan(checked, rules) if external_text else []
    world_brief = serialize_world_brief(bible)

    agent = WorldAgent()
    llm_issues, llm_summary, model_used, _raw = await agent.check_consistency(
        db,
        work_id=work_id,
        text=checked,
        world_brief=world_brief,
        chapter_title=chapter_title,
    )
    issues = merge_issues(heuristic, llm_issues)
    if issues:
        summary = llm_summary or f"发现 {len(issues)} 处与世界书可能冲突的表述"
        passed = not any(i.severity == "error" for i in issues)
    else:
        summary = llm_summary or "未发现与世界书冲突"
        passed = True

    return ConsistencyCheckResponse(
        passed=passed,
        issue_count=len(issues),
        issues=issues,
        summary=summary,
        model_used=model_used if (llm_issues or llm_summary) else (
            "heuristic" if heuristic else model_used
        ),
        checked_chars=len(checked),
        world_empty=False,
    )
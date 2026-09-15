"""连续性追踪业务：权威 JSON 读写 + 派生 Writer 上下文卡。"""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.models.outline import OutlineNode
from app.models.tracking import TrackingState
from app.models.work import Work
from app.schemas.tracking import (
    CharacterRuntimeState,
    ChapterTrackRecord,
    ForeshadowItem,
    ForeshadowUpsert,
    TimelineEvent,
    TrackingCommitRequest,
    TrackingStateRead,
    WriteConstraints,
    WriterContextCard,
)
from app.services.tracking_payload import (
    apply_commit,
    build_context_card,
    empty_payload,
    merge_constraints,
    normalize_payload,
    upsert_foreshadow,
)


async def _ensure_work(db: AsyncSession, work_id: UUID) -> None:
    """作品不存在则 404。"""
    exists = await db.execute(select(Work.id).where(Work.id == work_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"作品 {work_id} 不存在",
        )


async def get_or_create_tracking(db: AsyncSession, work_id: UUID) -> TrackingState:
    """获取或初始化作品追踪账本。"""
    await _ensure_work(db, work_id)
    result = await db.execute(
        select(TrackingState).where(TrackingState.work_id == work_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = TrackingState(work_id=work_id, payload=empty_payload(), revision=1)
        db.add(row)
        await db.flush()
        await db.refresh(row)
    else:
        row.payload = normalize_payload(row.payload)
    return row


def _to_read(
    row: TrackingState,
    *,
    context_card: WriterContextCard | None = None,
) -> TrackingStateRead:
    """权威 payload → API 派生视图。"""
    payload = normalize_payload(row.payload)
    characters = [
        CharacterRuntimeState(
            character_id=cid,
            name=str(slot.get("name") or ""),
            location=str(slot.get("location") or ""),
            goal=str(slot.get("goal") or ""),
            known_facts=list(slot.get("known_facts") or []),
            unknown_facts=list(slot.get("unknown_facts") or []),
            open_threads=list(slot.get("open_threads") or []),
        )
        for cid, slot in (payload.get("characters") or {}).items()
        if isinstance(slot, dict)
    ]
    return TrackingStateRead(
        work_id=row.work_id,
        revision=row.revision,
        last_chapter_id=payload.get("last_chapter_id"),
        foreshadows=[ForeshadowItem.model_validate(x) for x in payload.get("foreshadows") or []],
        character_states=characters,
        author_timeline=[TimelineEvent.model_validate(x) for x in payload.get("author_timeline") or []],
        reader_timeline=[TimelineEvent.model_validate(x) for x in payload.get("reader_timeline") or []],
        chapter_records=[
            ChapterTrackRecord.model_validate(x) for x in payload.get("chapter_records") or []
        ][-30:],
        context_card=context_card,
    )


async def get_tracking_view(
    db: AsyncSession,
    work_id: UUID,
    *,
    outline_node_id: UUID | None = None,
    chapter_id: UUID | None = None,  # noqa: ARG001 — 预留下章过滤
) -> TrackingStateRead:
    """返回 UI 用总览；可选带上指定细纲的 Writer 上下文卡。"""
    row = await get_or_create_tracking(db, work_id)
    card = None
    if outline_node_id is not None:
        outline = await db.get(OutlineNode, outline_node_id)
        characters: list[Character] = []
        if outline and outline.characters_involved:
            stmt = select(Character).where(
                Character.work_id == work_id,
                Character.name.in_(list(outline.characters_involved)),
            )
            characters = list((await db.execute(stmt)).scalars().all())
        card = await build_writer_context_card(db, work_id, outline=outline, characters=characters)
    return _to_read(row, context_card=card)


async def commit_tracking(
    db: AsyncSession,
    work_id: UUID,
    payload: TrackingCommitRequest,
) -> TrackingStateRead:
    """提交一章增量并升 revision。"""
    row = await get_or_create_tracking(db, work_id)
    commit_dict = payload.model_dump(mode="json")
    row.payload = apply_commit(row.payload, commit_dict)
    row.revision = int(row.revision or 1) + 1
    await db.flush()
    await db.refresh(row)
    return _to_read(row)


async def upsert_foreshadow_item(
    db: AsyncSession,
    work_id: UUID,
    item: ForeshadowUpsert,
) -> TrackingStateRead:
    """手工登记/更新伏笔。"""
    row = await get_or_create_tracking(db, work_id)
    row.payload = upsert_foreshadow(row.payload, item.model_dump(mode="json"))
    row.revision = int(row.revision or 1) + 1
    await db.flush()
    await db.refresh(row)
    return _to_read(row)


async def save_chapter_constraints(
    db: AsyncSession,
    work_id: UUID,
    outline_node_id: UUID,
    constraints: WriteConstraints,
) -> TrackingStateRead:
    """把约束锁缓存进账本（细纲列仍是产品主入口）。"""
    row = await get_or_create_tracking(db, work_id)
    payload = normalize_payload(row.payload)
    payload["chapter_constraints"][str(outline_node_id)] = constraints.model_dump()
    row.payload = payload
    row.revision = int(row.revision or 1) + 1
    await db.flush()
    await db.refresh(row)
    return _to_read(row)


async def build_writer_context_card(
    db: AsyncSession,
    work_id: UUID,
    *,
    outline: OutlineNode | None,
    characters: list[Character],
) -> WriterContextCard:
    """组装 Writer 写前上下文卡（短、可审计）。"""
    row = await get_or_create_tracking(db, work_id)
    payload = normalize_payload(row.payload)
    outline_wc = getattr(outline, "write_constraints", None) or {}
    cached = {}
    if outline is not None:
        cached = (payload.get("chapter_constraints") or {}).get(str(outline.id)) or {}
    constraints = merge_constraints(outline_wc, cached)
    appearing_ids = [str(c.id) for c in characters]
    # 人设卡有、运行时还没有时，用名字占位，避免模型把设定当成已知
    char_map = payload.setdefault("characters", {})
    for ch in characters:
        char_map.setdefault(
            str(ch.id),
            {
                "name": ch.name,
                "location": "",
                "goal": "",
                "known_facts": [],
                "unknown_facts": [],
                "open_threads": [],
            },
        )
    card = build_context_card(
        payload,
        constraints=constraints,
        appearing_character_ids=appearing_ids,
    )
    return WriterContextCard.model_validate(card)

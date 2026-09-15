"""作品连续性追踪 API。"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.tracking import (
    ForeshadowUpsert,
    TrackingCommitRequest,
    TrackingStateRead,
    WriteConstraints,
    WriterContextCard,
)
from app.services import tracking_service

router = APIRouter()


@router.get(
    "/works/{work_id}/tracking",
    response_model=TrackingStateRead,
    summary="获取作品连续性账本（派生视图）",
)
async def get_tracking(
    work_id: UUID,
    outline_node_id: UUID | None = Query(None, description="若提供则附带该细纲的写前上下文卡"),
    db: AsyncSession = Depends(get_db),
) -> TrackingStateRead:
    view = await tracking_service.get_tracking_view(
        db, work_id, outline_node_id=outline_node_id
    )
    await db.commit()
    return view


@router.get(
    "/works/{work_id}/tracking/context",
    response_model=WriterContextCard,
    summary="Writer 写前上下文卡（短、本章相关）",
)
async def get_writer_context(
    work_id: UUID,
    outline_node_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> WriterContextCard:
    from sqlalchemy import select

    from app.models.character import Character
    from app.models.outline import OutlineNode

    outline = await db.get(OutlineNode, outline_node_id) if outline_node_id else None
    characters: list[Character] = []
    if outline and outline.characters_involved:
        stmt = select(Character).where(
            Character.work_id == work_id,
            Character.name.in_(list(outline.characters_involved)),
        )
        characters = list((await db.execute(stmt)).scalars().all())
    card = await tracking_service.build_writer_context_card(
        db, work_id, outline=outline, characters=characters
    )
    await db.commit()
    return card


@router.post(
    "/works/{work_id}/tracking/commit",
    response_model=TrackingStateRead,
    summary="提交一章连续性增量（权威写入）",
)
async def commit_tracking(
    work_id: UUID,
    payload: TrackingCommitRequest,
    db: AsyncSession = Depends(get_db),
) -> TrackingStateRead:
    view = await tracking_service.commit_tracking(db, work_id, payload)
    await db.commit()
    return view


@router.post(
    "/works/{work_id}/tracking/foreshadows",
    response_model=TrackingStateRead,
    summary="登记或更新一条伏笔",
)
async def upsert_foreshadow(
    work_id: UUID,
    payload: ForeshadowUpsert,
    db: AsyncSession = Depends(get_db),
) -> TrackingStateRead:
    view = await tracking_service.upsert_foreshadow_item(db, work_id, payload)
    await db.commit()
    return view


@router.put(
    "/works/{work_id}/tracking/constraints/{outline_node_id}",
    response_model=TrackingStateRead,
    summary="缓存指定细纲的约束锁（细纲列仍为主入口）",
)
async def put_constraints(
    work_id: UUID,
    outline_node_id: UUID,
    payload: WriteConstraints,
    db: AsyncSession = Depends(get_db),
) -> TrackingStateRead:
    view = await tracking_service.save_chapter_constraints(
        db, work_id, outline_node_id, payload
    )
    await db.commit()
    return view

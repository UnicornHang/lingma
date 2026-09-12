"""World bible 业务逻辑层"""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world import WorldBible
from app.schemas.world import WorldBibleCreate, WorldBibleUpdate


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
    return bible
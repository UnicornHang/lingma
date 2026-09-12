"""世界观圣经 CRUD API"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.world import (
    WorldBibleCreate,
    WorldBibleRead,
    WorldBibleUpdate,
)
from app.services import world_service

router = APIRouter()


@router.get(
    "/works/{work_id}/world",
    response_model=WorldBibleRead,
    summary="获取/初始化作品的世界书（无则自动创建空记录）",
)
async def get_world_bible_endpoint(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorldBibleRead:
    bible = await world_service.get_or_create_world_bible(db, work_id)
    await db.commit()
    return WorldBibleRead.model_validate(bible)


@router.post(
    "/world",
    response_model=WorldBibleRead,
    status_code=status.HTTP_201_CREATED,
    summary="显式创建作品的世界书（已存在则 409）",
)
async def create_world_bible_endpoint(
    payload: WorldBibleCreate,
    db: AsyncSession = Depends(get_db),
) -> WorldBibleRead:
    bible = await world_service.create_world_bible(db, payload)
    await db.commit()
    await db.refresh(bible)
    return WorldBibleRead.model_validate(bible)


@router.patch(
    "/works/{work_id}/world",
    response_model=WorldBibleRead,
    summary="部分更新世界书（不存在则自动创建）",
)
async def update_world_bible_endpoint(
    work_id: UUID,
    payload: WorldBibleUpdate,
    db: AsyncSession = Depends(get_db),
) -> WorldBibleRead:
    bible = await world_service.update_world_bible(db, work_id, payload)
    await db.commit()
    await db.refresh(bible)
    return WorldBibleRead.model_validate(bible)
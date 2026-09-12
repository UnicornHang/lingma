"""Character 业务逻辑层"""
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.models.work import Work
from app.schemas.character import CharacterCreate, CharacterUpdate


async def _ensure_work(db: AsyncSession, work_id: UUID) -> None:
    exists = await db.execute(select(Work.id).where(Work.id == work_id))
    if not exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"作品 {work_id} 不存在",
        )


async def create_character(db: AsyncSession, payload: CharacterCreate) -> Character:
    await _ensure_work(db, payload.work_id)
    character = Character(
        work_id=payload.work_id,
        name=payload.name,
        role=payload.role,
        basic_info=payload.basic_info,
        personality=payload.personality,
        backstory=payload.backstory,
        relationships=payload.relationships,
        arc=payload.arc,
        voice_samples=payload.voice_samples,
        raw_text=payload.raw_text,
    )
    db.add(character)
    await db.flush()
    await db.refresh(character)
    return character


async def get_character(db: AsyncSession, character_id: UUID) -> Character:
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"角色 {character_id} 不存在",
        )
    return character


async def list_characters(
    db: AsyncSession, work_id: UUID
) -> tuple[Sequence[Character], int]:
    await _ensure_work(db, work_id)
    total = (
        await db.execute(
            select(func.count()).select_from(Character).where(Character.work_id == work_id)
        )
    ).scalar_one()
    stmt = (
        select(Character)
        .where(Character.work_id == work_id)
        .order_by(Character.created_at.asc())
    )
    items = (await db.execute(stmt)).scalars().all()
    return items, total


async def update_character(
    db: AsyncSession, character_id: UUID, payload: CharacterUpdate
) -> Character:
    character = await get_character(db, character_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(character, key, value)
    await db.flush()
    await db.refresh(character)
    return character


async def delete_character(db: AsyncSession, character_id: UUID) -> None:
    character = await get_character(db, character_id)
    await db.delete(character)
    await db.flush()
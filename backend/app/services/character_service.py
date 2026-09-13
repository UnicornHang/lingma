"""Character 业务逻辑层"""
import logging
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.models.work import Work
from app.schemas.character import CharacterCreate, CharacterUpdate
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)


async def _try_index_character(db: AsyncSession, character: Character) -> None:
    """RAG 索引(失败仅 log,不阻塞业务)。"""
    try:
        n = await get_rag_service().index_character(db, character)
        if n > 0:
            logger.info("RAG 索引角色: name=%s, chunks=%d", character.name, n)
    except Exception as e:  # pragma: no cover - 防御
        logger.warning("RAG 索引角色失败(已降级): %s", e)


async def _try_delete_character_collection(character: Character) -> None:
    """删除角色在 RAG 中的 collection 记录(失败仅 log)。"""
    try:
        get_rag_service().delete_collection_for_work(character.work_id, "character")
    except Exception as e:  # pragma: no cover - 防御
        logger.warning("RAG 删除角色 collection 失败(已降级): %s", e)


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
    await _try_index_character(db, character)
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
    await _try_index_character(db, character)
    return character


async def delete_character(db: AsyncSession, character_id: UUID) -> None:
    character = await get_character(db, character_id)
    work_id = character.work_id
    target_id = str(character.id)
    await db.delete(character)
    await db.flush()
    # 用最小依赖重建一个 stub 用于 RAG collection 清理
    try:
        get_rag_service().delete_collection_for_work(work_id, "character")
        logger.info("RAG 删除角色 collection: work=%s, target=%s", work_id, target_id)
    except Exception as e:  # pragma: no cover - 防御
        logger.warning("RAG 删除角色 collection 失败(已降级): %s", e)
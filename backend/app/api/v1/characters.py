"""角色 CRUD API"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.character_agent import CharacterAgent
from app.deps import get_db
from app.schemas.character import (
    CharacterCreate,
    CharacterListResponse,
    CharacterRead,
    CharacterSuggestRequest,
    CharacterSuggestResponse,
    CharacterUpdate,
)
from app.services import character_service

router = APIRouter()


@router.get(
    "/works/{work_id}/characters",
    response_model=CharacterListResponse,
    summary="获取作品下的所有角色",
)
async def list_characters_endpoint(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CharacterListResponse:
    items, total = await character_service.list_characters(db, work_id)
    return CharacterListResponse(
        total=total,
        items=[CharacterRead.model_validate(it) for it in items],
    )


@router.post(
    "/characters",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建角色",
)
async def create_character_endpoint(
    payload: CharacterCreate,
    db: AsyncSession = Depends(get_db),
) -> CharacterRead:
    character = await character_service.create_character(db, payload)
    await db.commit()
    await db.refresh(character)
    return CharacterRead.model_validate(character)


@router.get(
    "/characters/{character_id}",
    response_model=CharacterRead,
    summary="获取角色详情",
)
async def get_character_endpoint(
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CharacterRead:
    character = await character_service.get_character(db, character_id)
    return CharacterRead.model_validate(character)


@router.patch(
    "/characters/{character_id}",
    response_model=CharacterRead,
    summary="更新角色",
)
async def update_character_endpoint(
    character_id: UUID,
    payload: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
) -> CharacterRead:
    character = await character_service.update_character(db, character_id, payload)
    await db.commit()
    await db.refresh(character)
    return CharacterRead.model_validate(character)


@router.delete(
    "/characters/{character_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除角色",
)
async def delete_character_endpoint(
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await character_service.delete_character(db, character_id)
    await db.commit()


@router.post(
    "/characters/ai-suggest",
    response_model=CharacterSuggestResponse,
    summary="AI 推荐角色（不强写入 DB；前端按需采纳）",
)
async def ai_suggest_characters(
    payload: CharacterSuggestRequest,
    db: AsyncSession = Depends(get_db),
) -> CharacterSuggestResponse:
    agent = CharacterAgent()
    cards, model_used, raw = await agent.suggest(
        db,
        work_id=payload.work_id,
        count=payload.count,
        focus=payload.focus,
        extra_hint=payload.extra_hint,
    )
    return CharacterSuggestResponse(
        cards=cards,
        model_used=model_used,
        raw_content=raw,
    )
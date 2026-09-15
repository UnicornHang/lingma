"""世界观圣经 CRUD API"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.world_agent import WorldAgent
from app.deps import get_db
from app.schemas.world import (
    ConsistencyCheckRequest,
    ConsistencyCheckResponse,
    WorldBibleCreate,
    WorldBibleRead,
    WorldBibleUpdate,
    WorldSuggestRequest,
    WorldSuggestResponse,
)
from app.services import world_service

router = APIRouter()


@router.get(
    "/works/{work_id}/world",
    response_model=WorldBibleRead,
    summary="获取/初始化作品的世界书(无则自动创建空记录)",
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
    summary="显式创建作品的世界书(已存在则 409)",
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
    summary="部分更新世界书(不存在则自动创建)",
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


@router.post(
    "/world/ai-suggest",
    response_model=WorldSuggestResponse,
    summary="AI 推荐世界书 6 维度(不强写入 DB;前端按需合并)",
)
async def ai_suggest_world(
    payload: WorldSuggestRequest,
    db: AsyncSession = Depends(get_db),
) -> WorldSuggestResponse:
    agent = WorldAgent()
    suggestion, model_used, raw = await agent.suggest(
        db,
        work_id=payload.work_id,
        focus_dimension=payload.focus_dimension,
        extra_hint=payload.extra_hint,
    )
    return WorldSuggestResponse(
        suggestion=suggestion,
        model_used=model_used,
        raw_content=raw,
    )


@router.post(
    "/works/{work_id}/world/check-consistency",
    response_model=ConsistencyCheckResponse,
    summary="对照世界书检查正文一致性",
)
async def check_world_consistency_endpoint(
    work_id: UUID,
    payload: ConsistencyCheckRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> ConsistencyCheckResponse:
    """检查待检文本(或章节)是否违反世界书设定。

    - `text`: 直接检查这段文字
    - `chapter_id`: 读取该章节 plain_content(须属于本作品)
    - 两者都空: 用世界书 raw_text 做内部自检
    """
    body = payload or ConsistencyCheckRequest()
    return await world_service.check_consistency(
        db,
        work_id,
        text=body.text,
        chapter_id=body.chapter_id,
    )
"""作品 CRUD API"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.work import WorkStatus
from app.schemas.work import (
    WorkCreate,
    WorkListResponse,
    WorkRead,
    WorkUpdate,
)
from app.services import work_service
from app.services.chapter_service import list_chapters

router = APIRouter()


@router.get(
    "/",
    response_model=WorkListResponse,
    summary="分页获取作品列表",
)
async def list_works_endpoint(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    status_filter: Optional[WorkStatus] = Query(None, alias="status", description="状态过滤"),
    db: AsyncSession = Depends(get_db),
) -> WorkListResponse:
    items, total = await work_service.list_works(
        db, page=page, page_size=page_size, status_filter=status_filter
    )
    return WorkListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[WorkRead.model_validate(it) for it in items],
    )


@router.post(
    "/",
    response_model=WorkRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建作品",
)
async def create_work_endpoint(
    payload: WorkCreate,
    db: AsyncSession = Depends(get_db),
) -> WorkRead:
    work = await work_service.create_work(db, payload)
    await db.commit()
    await db.refresh(work)
    return WorkRead.model_validate(work)


@router.get(
    "/{work_id}",
    response_model=WorkRead,
    summary="获取作品详情",
)
async def get_work_endpoint(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkRead:
    work = await work_service.get_work(db, work_id)
    return WorkRead.model_validate(work)


@router.patch(
    "/{work_id}",
    response_model=WorkRead,
    summary="更新作品",
)
async def update_work_endpoint(
    work_id: UUID,
    payload: WorkUpdate,
    db: AsyncSession = Depends(get_db),
) -> WorkRead:
    work = await work_service.update_work(db, work_id, payload)
    await db.commit()
    await db.refresh(work)
    return WorkRead.model_validate(work)


@router.delete(
    "/{work_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除作品",
)
async def delete_work_endpoint(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await work_service.delete_work(db, work_id)
    await db.commit()


@router.get(
    "/{work_id}/chapters",
    summary="获取作品下的章节列表",
)
async def list_work_chapters_endpoint(
    work_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """便捷聚合：作品信息 + 章节列表（前端常用）"""
    work = await work_service.get_work(db, work_id)
    items, total = await list_chapters(db, work_id, page=page, page_size=page_size)
    return {
        "work": WorkRead.model_validate(work).model_dump(mode="json"),
        "total_chapters": total,
        "chapters": [
            {
                "id": str(c.id),
                "title": c.title,
                "status": c.status if isinstance(c.status, str) else c.status.value,
                "word_count": c.word_count,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in items
        ],
    }
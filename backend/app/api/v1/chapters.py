"""章节 CRUD API"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.task import GenerationTask, TaskStatus, TaskType
from app.schemas.chapter import (
    ChapterCreate,
    ChapterListResponse,
    ChapterRead,
    ChapterUpdate,
    GenerateChapterRequest,
)
from app.services import chapter_service
from app.services import work_service

router = APIRouter()


@router.get(
    "/",
    response_model=ChapterListResponse,
    summary="按作品列出章节",
)
async def list_chapters_endpoint(
    work_id: UUID = Query(..., description="所属作品 ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> ChapterListResponse:
    # 校验作品存在
    await work_service.get_work(db, work_id)
    items, total = await chapter_service.list_chapters(
        db, work_id, page=page, page_size=page_size
    )
    return ChapterListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ChapterRead.model_validate(it) for it in items],
    )


@router.post(
    "/",
    response_model=ChapterRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建章节",
)
async def create_chapter_endpoint(
    payload: ChapterCreate,
    db: AsyncSession = Depends(get_db),
) -> ChapterRead:
    chapter = await chapter_service.create_chapter(db, payload)
    await db.commit()
    await db.refresh(chapter)
    return ChapterRead.model_validate(chapter)


@router.get(
    "/{chapter_id}",
    response_model=ChapterRead,
    summary="获取章节详情",
)
async def get_chapter_endpoint(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChapterRead:
    chapter = await chapter_service.get_chapter(db, chapter_id)
    return ChapterRead.model_validate(chapter)


@router.patch(
    "/{chapter_id}",
    response_model=ChapterRead,
    summary="更新章节",
)
async def update_chapter_endpoint(
    chapter_id: UUID,
    payload: ChapterUpdate,
    db: AsyncSession = Depends(get_db),
) -> ChapterRead:
    chapter = await chapter_service.update_chapter(db, chapter_id, payload)
    await db.commit()
    await db.refresh(chapter)
    return ChapterRead.model_validate(chapter)


@router.delete(
    "/{chapter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除章节",
)
async def delete_chapter_endpoint(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await chapter_service.delete_chapter(db, chapter_id)
    await db.commit()


@router.post(
    "/{chapter_id}/generate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="异步生成/续写章节",
    description=(
        "创建异步生成任务并返回 task_id 与 WS 地址。"
        "前端需在收到响应后连接 WS：ws://<host>/ws/generation/{task_id}，"
        "发送 {type: 'start', messages: [...], model: '...'} 启动流式输出。"
    ),
)
async def generate_chapter_endpoint(
    chapter_id: UUID,
    payload: GenerateChapterRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    chapter = await chapter_service.get_chapter(db, chapter_id)

    params: dict = {}
    if payload:
        # mode='json' 确保 UUID 等非 JSON 原生类型序列化为字符串,
        # 否则 SQLAlchemy 写 params JSON 列时会抛 TypeError
        params = payload.model_dump(exclude_none=True, mode="json")

    task = GenerationTask(
        work_id=chapter.work_id,
        chapter_id=chapter_id,
        task_type=TaskType.CHAPTER_CONTINUE,
        status=TaskStatus.PENDING,
        params=params,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "task_id": str(task.id),
        "ws_url": f"/ws/generation/{task.id}",
        "status": task.status if isinstance(task.status, str) else task.status.value,
        "chapter_id": str(chapter_id),
    }
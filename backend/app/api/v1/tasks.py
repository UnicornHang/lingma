"""生成任务查询 API"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.task import GenerationTask
from app.schemas.task import GenerationTaskRead

router = APIRouter()


@router.get(
    "/tasks/{task_id}",
    response_model=GenerationTaskRead,
    summary="查询生成任务状态（供 WS 断线时前端轮询兜底）",
)
async def get_task_endpoint(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> GenerationTaskRead:
    result = await db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在",
        )
    return GenerationTaskRead.model_validate(task)
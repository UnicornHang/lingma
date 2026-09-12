"""Work 业务逻辑层"""
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import Work, WorkStatus
from app.schemas.work import WorkCreate, WorkUpdate


async def create_work(db: AsyncSession, payload: WorkCreate) -> Work:
    """创建作品"""
    work = Work(
        title=payload.title,
        genre=payload.genre,
        logline=payload.logline,
        target_word_count=payload.target_word_count,
        style_keywords=payload.style_keywords,
        target_audience=payload.target_audience,
        status=WorkStatus.DRAFT,
        word_count=0,
    )
    db.add(work)
    await db.flush()
    await db.refresh(work)
    return work


async def get_work(db: AsyncSession, work_id: UUID) -> Work:
    """获取作品，找不到则 404"""
    result = await db.execute(select(Work).where(Work.id == work_id))
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"作品 {work_id} 不存在",
        )
    return work


async def list_works(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status_filter: WorkStatus | None = None,
) -> tuple[Sequence[Work], int]:
    """分页查询作品"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    # 计数
    count_stmt = select(func.count()).select_from(Work)
    if status_filter:
        count_stmt = count_stmt.where(Work.status == status_filter)
    total = (await db.execute(count_stmt)).scalar_one()

    # 列表
    stmt = select(Work)
    if status_filter:
        stmt = stmt.where(Work.status == status_filter)
    stmt = stmt.order_by(Work.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    items = result.scalars().all()

    return items, total


async def update_work(db: AsyncSession, work_id: UUID, payload: WorkUpdate) -> Work:
    """更新作品（部分字段）"""
    work = await get_work(db, work_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(work, key, value)
    await db.flush()
    await db.refresh(work)
    return work


async def delete_work(db: AsyncSession, work_id: UUID) -> None:
    """删除作品（级联章节/角色/大纲/世界书）"""
    work = await get_work(db, work_id)
    await db.delete(work)
    await db.flush()
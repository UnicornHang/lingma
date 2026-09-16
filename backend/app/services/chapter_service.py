"""Chapter 业务逻辑层"""
import asyncio
import logging
from types import SimpleNamespace
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import async_session_factory
from app.models.chapter import Chapter
from app.models.work import Work
from app.schemas.chapter import ChapterCreate, ChapterUpdate
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)


def _log_index_task_result(task: asyncio.Task) -> None:
    """避免后台索引 Task 异常变成 'exception was never retrieved'。"""
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.warning("后台 RAG 索引任务异常: %s", exc)


def schedule_chapter_summary_index(chapter_id: UUID) -> None:
    """commit 之后异步索引章节摘要,不阻塞 PATCH/POST 响应。

    embedding 首次加载可能 >10s,必须离开请求路径,否则编辑器 30s axios 会超时。
    """
    if not settings.rag_enabled:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(_index_chapter_summary_detached(chapter_id))
    task.add_done_callback(_log_index_task_result)


async def _index_chapter_summary_detached(chapter_id: UUID) -> None:
    """独立 session + 工作线程跑 RAG,失败仅 log。"""
    try:
        async with async_session_factory() as db:
            chapter = await db.get(Chapter, chapter_id)
            if chapter is None:
                return
            # ORM 对象不能安全跨线程;抽纯字段再丢给工作线程
            snapshot = SimpleNamespace(
                id=chapter.id,
                work_id=chapter.work_id,
                title=chapter.title,
                summary=chapter.summary,
                plain_content=chapter.plain_content,
            )
        n = await asyncio.to_thread(_index_chapter_summary_sync, snapshot)
        if n > 0:
            logger.info("RAG 索引章节: title=%s, chunks=%d", snapshot.title, n)
    except Exception as e:  # pragma: no cover - 防御
        logger.warning("后台 RAG 索引失败: %s", e)


def _index_chapter_summary_sync(chapter: object) -> int:
    """在工作线程调用异步 RAG 接口(其内部实际是同步 embedding/chroma)。"""
    return asyncio.run(get_rag_service().index_chapter_summary(None, chapter))  # type: ignore[arg-type]


def count_words(text: str) -> int:
    """粗略字数统计（中英文混合）"""
    if not text:
        return 0
    # 中文按字符计数，英文按单词
    chinese = sum(1 for c in text if "一" <= c <= "鿿")
    others = len(text) - chinese
    # 简易英文单词切分
    english_words = len([w for w in text.split() if w.isascii()])
    return chinese + english_words


async def create_chapter(db: AsyncSession, payload: ChapterCreate) -> Chapter:
    """创建章节"""
    # 校验作品存在
    work_exists = await db.execute(select(Work.id).where(Work.id == payload.work_id))
    if not work_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"作品 {payload.work_id} 不存在",
        )

    chapter = Chapter(
        work_id=payload.work_id,
        title=payload.title,
        content=payload.content,
        plain_content=payload.plain_content,
        summary=payload.summary,
        key_events=payload.key_events,
        outline_node_id=payload.outline_node_id,
        word_count=count_words(payload.plain_content),
    )
    db.add(chapter)
    await db.flush()
    await db.refresh(chapter)
    return chapter


async def get_chapter(db: AsyncSession, chapter_id: UUID) -> Chapter:
    """获取章节"""
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"章节 {chapter_id} 不存在",
        )
    return chapter


async def list_chapters(
    db: AsyncSession,
    work_id: UUID,
    *,
    page: int = 1,
    page_size: int = 50,
) -> tuple[Sequence[Chapter], int]:
    """列出作品下的章节"""
    total = (
        await db.execute(
            select(func.count()).select_from(Chapter).where(Chapter.work_id == work_id)
        )
    ).scalar_one()

    stmt = (
        select(Chapter)
        .where(Chapter.work_id == work_id)
        .order_by(Chapter.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return items, total


async def update_chapter(
    db: AsyncSession, chapter_id: UUID, payload: ChapterUpdate
) -> Chapter:
    """更新章节"""
    chapter = await get_chapter(db, chapter_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(chapter, key, value)
    if "plain_content" in data:
        chapter.word_count = count_words(data["plain_content"])
    chapter.version += 1
    await db.flush()
    await db.refresh(chapter)
    return chapter


async def delete_chapter(db: AsyncSession, chapter_id: UUID) -> None:
    """删除章节"""
    chapter = await get_chapter(db, chapter_id)
    await db.delete(chapter)
    await db.flush()
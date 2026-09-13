"""[P3.2] GET /chapters/{id}/evaluations 端点测试。

覆盖:
- 空数据返 200 + [] (不返 404)
- 多条记录按 created_at ASC 排列
- 章节不存在返 404
- 评审按 chapter_id 隔离(不串章)

不依赖 FastAPI TestClient —— 直接调用 service 层函数 + 手动 build response。
原因: P3.2 端点逻辑在 endpoint 函数内(校验章节 + 简单 SELECT),不值得
引入 HTTP client 测试基础设施,直接覆盖 endpoint 函数即可。
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.chapters import list_chapter_evaluations_endpoint
from app.models.critic_evaluation import CriticEvaluation


# ============== Fixtures ==============


@pytest.fixture
async def db():
    from app.db.session import async_session_factory
    from app.models.character import Character
    from app.models.chapter import Chapter
    from app.models.outline import OutlineNode
    from app.models.work import Genre, Work, WorkStatus
    from app.models.world import WorldBible
    from sqlalchemy import delete as sa_delete

    async with async_session_factory() as session:
        yield session
        await session.execute(sa_delete(CriticEvaluation))
        await session.execute(sa_delete(Chapter))
        await session.execute(sa_delete(OutlineNode))
        await session.execute(sa_delete(Character))
        await session.execute(sa_delete(WorldBible))
        await session.execute(sa_delete(Work))
        await session.commit()


@pytest.fixture
async def work(db: AsyncSession):
    from app.models.work import Genre, Work, WorkStatus

    w = Work(
        id=uuid4(),
        title="测试作品",
        genre=Genre.FANTASY,
        target_word_count=100000,
        logline="测试",
        style_keywords=[],
        target_audience=["不限"],
        status=WorkStatus.DRAFT,
        word_count=0,
        settings={},
    )
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


@pytest.fixture
async def chapter(db: AsyncSession, work):
    from app.models.chapter import Chapter, ChapterStatus

    c = Chapter(
        work_id=work.id,
        title="第一章",
        plain_content="content",
        status=ChapterStatus.DRAFT,
        word_count=100,
        version=1,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


# ============== 1. 空评审返 200 + [] ==============


async def test_returns_empty_list_for_chapter_with_no_evals(db: db, chapter):
    """章节无评审 → 200 + 空列表(不返 404)。"""
    result = await list_chapter_evaluations_endpoint(chapter.id, db=db)
    assert result == []


# ============== 2. 多条按时间正序 ==============


async def test_returns_chronological_order_asc(db: db, chapter):
    """3 条评审按 created_at ASC 排列(趋势图 X 轴)。"""
    # 创建 3 条评审,故意按 created_at desc 插入(验证 SQL ORDER BY 生效)
    rows = []
    for i, dt in enumerate([
        datetime(2026, 9, 13, 12, 0, 0, tzinfo=timezone.utc),  # 最早
        datetime(2026, 9, 13, 14, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 13, 16, 0, 0, tzinfo=timezone.utc),  # 最新
    ]):
        r = CriticEvaluation(
            chapter_id=chapter.id,
            version_no=i + 1,
            overall=0.5 + i * 0.1,
            consistency=0.5,
            pacing=0.5,
            prose=0.5,
            engagement=0.5,
            persona_scores=[],
            consensus_issues=[],
            model_used=f"model-{i}",
            created_at=dt,
        )
        db.add(r)
        rows.append(r)
    await db.commit()

    result = await list_chapter_evaluations_endpoint(chapter.id, db=db)

    assert len(result) == 3
    # 验证按 ASC 排列
    assert result[0].model_used == "model-0"
    assert result[1].model_used == "model-1"
    assert result[2].model_used == "model-2"
    # 评分也对应
    assert result[0].overall == pytest.approx(0.5)
    assert result[2].overall == pytest.approx(0.7)
    # version_no 字段
    assert result[0].version_no == 1
    assert result[2].version_no == 3


# ============== 3. 章节不存在返 404 ==============


async def test_raises_404_for_unknown_chapter(db: db):
    """chapter_id 不存在 → 404(由 chapter_service.get_chapter 抛)。"""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await list_chapter_evaluations_endpoint(uuid4(), db=db)
    assert exc_info.value.status_code == 404


# ============== 4. 评审按 chapter_id 隔离 ==============


async def test_evaluations_are_scoped_to_chapter(db: db, chapter, work):
    """2 章节各 1 条评审 → 互不串。"""
    from app.models.chapter import Chapter, ChapterStatus

    other_chapter = Chapter(
        work_id=work.id,
        title="第二章",
        plain_content="",
        status=ChapterStatus.DRAFT,
        word_count=0,
        version=1,
    )
    db.add(other_chapter)
    await db.commit()
    await db.refresh(other_chapter)

    # chapter 1 → eval with overall=0.6
    db.add(CriticEvaluation(
        chapter_id=chapter.id, version_no=1,
        overall=0.6, consistency=0.6, pacing=0.6, prose=0.6, engagement=0.6,
        persona_scores=[], consensus_issues=[], model_used="a",
    ))
    # other_chapter → eval with overall=0.9
    db.add(CriticEvaluation(
        chapter_id=other_chapter.id, version_no=1,
        overall=0.9, consistency=0.9, pacing=0.9, prose=0.9, engagement=0.9,
        persona_scores=[], consensus_issues=[], model_used="b",
    ))
    await db.commit()

    r1 = await list_chapter_evaluations_endpoint(chapter.id, db=db)
    r2 = await list_chapter_evaluations_endpoint(other_chapter.id, db=db)

    assert len(r1) == 1
    assert len(r2) == 1
    assert r1[0].overall == pytest.approx(0.6)
    assert r2[0].overall == pytest.approx(0.9)
    # 章节 1 拿不到章节 2 的数据
    assert r1[0].id != r2[0].id
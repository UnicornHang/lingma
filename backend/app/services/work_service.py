"""Work 业务逻辑层"""
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import Work, WorkStatus
from app.schemas.work import WorkCreate, WorkUpdate, WorkWizardSeed


def _settings_from_seed(seed: WorkWizardSeed | None) -> dict:
    """把向导种子压进 works.settings，供后续设置页读取。"""
    if seed is None:
        return {}
    return seed.model_dump()


async def create_work(db: AsyncSession, payload: WorkCreate) -> Work:
    """创建作品，并按 seed / volumes 补起步大纲、世界书与主角卡。"""
    work = Work(
        title=payload.title,
        genre=payload.genre,
        logline=payload.logline,
        target_word_count=payload.target_word_count,
        style_keywords=payload.style_keywords,
        target_audience=payload.target_audience,
        status=WorkStatus.DRAFT,
        word_count=0,
        settings=_settings_from_seed(payload.seed),
    )
    db.add(work)
    await db.flush()

    if payload.volumes:
        from app.services.outline_service import bulk_create_volumes

        default_words = (
            payload.seed.chapter_target_words
            if payload.seed and payload.seed.chapter_target_words
            else 3000
        )
        await bulk_create_volumes(
            db, work.id, payload.volumes, default_chapter_words=default_words
        )
    elif payload.seed is not None:
        await _seed_starter_outline(db, work, payload.seed)

    await _seed_world_and_character(db, work, payload.seed)
    await db.refresh(work)
    return work


async def _seed_starter_outline(
    db: AsyncSession, work: Work, seed: WorkWizardSeed
) -> None:
    """无 AI 大纲时写入一卷一章，保证细纲门禁能过。"""
    from app.models.outline import OutlineNode, OutlineNodeType

    vol_title = (seed.volume1_name or "").strip() or "第一卷"
    chapter_words = seed.chapter_target_words or 3000
    beats = [b.strip() for b in seed.opening_beats if isinstance(b, str) and b.strip()]
    protagonist = (seed.protagonist or "").strip()
    origin = (seed.origin_setting or "").strip()
    conflict = (seed.core_conflict or "").strip()
    summary = conflict or (work.logline or "").strip() or f"《{work.title}》开篇。"
    chapter_title = (beats[0] if beats else "第一章")[:200]

    vol_node = OutlineNode(
        work_id=work.id,
        parent_id=None,
        type=OutlineNodeType.VOLUME,
        title=vol_title[:200],
        summary=conflict[:2000] if conflict else "",
        beats=[],
        characters_involved=[protagonist] if protagonist else [],
        world_refs=[origin] if origin else [],
        target_word_count=chapter_words,
        order=1,
    )
    db.add(vol_node)
    await db.flush()

    ch_node = OutlineNode(
        work_id=work.id,
        parent_id=vol_node.id,
        type=OutlineNodeType.CHAPTER,
        title=chapter_title,
        summary=summary[:2000],
        beats=beats,
        characters_involved=[protagonist] if protagonist else [],
        world_refs=[origin] if origin else [],
        target_word_count=max(100, min(20_000, chapter_words)),
        order=1,
        write_constraints={"must_happen": beats[:3]} if beats else {},
    )
    db.add(ch_node)
    await db.flush()


async def _seed_world_and_character(
    db: AsyncSession, work: Work, seed: WorkWizardSeed | None
) -> None:
    """有主角/世界观种子时写入世界书与主角卡（延迟 import 避免环依赖）。"""
    if seed is None:
        return

    from app.models.character import Character
    from app.models.world import WorldBible

    origin = (seed.origin_setting or "").strip()
    conflict = (seed.core_conflict or "").strip()
    protagonist = (seed.protagonist or "").strip()
    raw_parts = []
    if origin:
        raw_parts.append(f"起点设定：{origin}")
    if conflict:
        raw_parts.append(f"核心矛盾：{conflict}")
    if protagonist:
        raw_parts.append(f"主角：{protagonist}")

    if origin or conflict:
        bible = WorldBible(
            work_id=work.id,
            geography={"origin": {"name": origin, "description": conflict}} if origin else {},
            raw_text="\n".join(raw_parts),
        )
        db.add(bible)

    if protagonist:
        character = Character(
            work_id=work.id,
            name=protagonist[:100],
            role="protagonist",
            basic_info={"origin": origin} if origin else {},
            raw_text="\n".join(raw_parts),
        )
        db.add(character)
    await db.flush()


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

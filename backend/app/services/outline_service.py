"""Outline 业务逻辑层"""
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outline import OutlineNode, OutlineNodeType
from app.models.work import Work
from app.schemas.outline import OutlineNodeCreate, OutlineNodeUpdate, PlotVolume


async def _ensure_work(db: AsyncSession, work_id: UUID) -> None:
    exists = await db.execute(select(Work.id).where(Work.id == work_id))
    if not exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"作品 {work_id} 不存在",
        )


async def bulk_create_volumes(
    db: AsyncSession,
    work_id: UUID,
    volumes: Sequence[PlotVolume],
    *,
    default_chapter_words: int = 3000,
) -> list[OutlineNode]:
    """按卷→章写入大纲节点，不 commit（由调用方统一提交）。"""
    await _ensure_work(db, work_id)
    chapter_words = max(100, min(20_000, default_chapter_words or 3000))
    created: list[OutlineNode] = []
    order_vol = 0
    for vol in volumes:
        order_vol += 1
        vol_node = OutlineNode(
            work_id=work_id,
            parent_id=None,
            type=OutlineNodeType.VOLUME,
            title=vol.vol_title[:200],
            summary=(vol.summary or "")[:2000],
            beats=[],
            characters_involved=[],
            world_refs=[],
            target_word_count=chapter_words,
            order=order_vol,
        )
        db.add(vol_node)
        await db.flush()
        created.append(vol_node)

        order_ch = 0
        for ch in vol.chapters:
            order_ch += 1
            beats_text = [b.title for b in ch.beats if b.title]
            ch_node = OutlineNode(
                work_id=work_id,
                parent_id=vol_node.id,
                type=OutlineNodeType.CHAPTER,
                title=ch.title[:200],
                summary=(ch.summary or "")[:2000],
                beats=beats_text,
                characters_involved=list(ch.characters_involved),
                world_refs=list(ch.world_refs),
                target_word_count=max(100, min(20_000, ch.target_word_count or chapter_words)),
                order=order_ch,
            )
            db.add(ch_node)
            created.append(ch_node)
    await db.flush()
    return created


async def create_outline_node(db: AsyncSession, payload: OutlineNodeCreate) -> OutlineNode:
    await _ensure_work(db, payload.work_id)
    # 校验父节点存在并属于同一作品
    if payload.parent_id:
        parent = await db.execute(
            select(OutlineNode).where(OutlineNode.id == payload.parent_id)
        )
        parent_node = parent.scalar_one_or_none()
        if not parent_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"父节点 {payload.parent_id} 不存在",
            )
        if parent_node.work_id != payload.work_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="父节点必须属于同一作品",
            )
    node = OutlineNode(
        work_id=payload.work_id,
        parent_id=payload.parent_id,
        type=payload.type,
        title=payload.title,
        summary=payload.summary,
        beats=payload.beats,
        characters_involved=payload.characters_involved,
        world_refs=payload.world_refs,
        target_word_count=payload.target_word_count,
        order=payload.order,
        write_constraints=payload.write_constraints.model_dump(),
    )
    db.add(node)
    await db.flush()
    await db.refresh(node)
    return node


async def get_outline_node(db: AsyncSession, node_id: UUID) -> OutlineNode:
    result = await db.execute(select(OutlineNode).where(OutlineNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"大纲节点 {node_id} 不存在",
        )
    return node


async def list_outline_nodes(
    db: AsyncSession, work_id: UUID
) -> tuple[Sequence[OutlineNode], int]:
    await _ensure_work(db, work_id)
    total = (
        await db.execute(
            select(func.count()).select_from(OutlineNode).where(OutlineNode.work_id == work_id)
        )
    ).scalar_one()
    stmt = (
        select(OutlineNode)
        .where(OutlineNode.work_id == work_id)
        .order_by(OutlineNode.order.asc(), OutlineNode.created_at.asc())
    )
    items = (await db.execute(stmt)).scalars().all()
    return items, total


async def update_outline_node(
    db: AsyncSession, node_id: UUID, payload: OutlineNodeUpdate
) -> OutlineNode:
    node = await get_outline_node(db, node_id)
    data = payload.model_dump(exclude_unset=True)
    # 不允许跨作品改父节点
    if "parent_id" in data and data["parent_id"] is not None and data["parent_id"] != node.id:
        parent = await db.execute(
            select(OutlineNode).where(OutlineNode.id == data["parent_id"])
        )
        parent_node = parent.scalar_one_or_none()
        if not parent_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"父节点 {data['parent_id']} 不存在",
            )
        if parent_node.work_id != node.work_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="父节点必须属于同一作品",
            )
    for key, value in data.items():
        if key == "write_constraints" and value is not None and hasattr(value, "model_dump"):
            value = value.model_dump()
        elif key == "write_constraints" and isinstance(value, dict):
            pass
        setattr(node, key, value)
    await db.flush()
    await db.refresh(node)
    return node


async def delete_outline_node(db: AsyncSession, node_id: UUID) -> None:
    node = await get_outline_node(db, node_id)
    await db.delete(node)
    await db.flush()
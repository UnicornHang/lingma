"""大纲节点 CRUD API"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.outline import OutlineNode
from app.schemas.outline import (
    OutlineNodeCreate,
    OutlineNodeListResponse,
    OutlineNodeRead,
    OutlineNodeUpdate,
    OutlineTreeNode,
    OutlineTreeResponse,
)
from app.services import outline_service
from sqlalchemy import select

router = APIRouter()


@router.get(
    "/works/{work_id}/outline",
    response_model=OutlineNodeListResponse,
    summary="获取作品大纲节点（扁平列表，按 order 排序）",
)
async def list_outline_endpoint(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> OutlineNodeListResponse:
    items, total = await outline_service.list_outline_nodes(db, work_id)
    return OutlineNodeListResponse(
        total=total,
        items=[OutlineNodeRead.model_validate(it) for it in items],
    )


@router.get(
    "/works/{work_id}/outline/tree",
    response_model=OutlineTreeResponse,
    summary="获取作品大纲树（卷→章→节拍）",
)
async def get_outline_tree_endpoint(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> OutlineTreeResponse:
    items, _ = await outline_service.list_outline_nodes(db, work_id)

    by_id: dict[UUID, OutlineTreeNode] = {
        n.id: OutlineTreeNode(
            id=n.id,
            parent_id=n.parent_id,
            type=n.type,
            title=n.title,
            summary=n.summary,
            beats=n.beats,
            characters_involved=n.characters_involved,
            world_refs=n.world_refs,
            target_word_count=n.target_word_count,
            order=n.order,
            children=[],
        )
        for n in items
    }

    roots: list[OutlineTreeNode] = []
    for n in items:
        node = by_id[n.id]
        if n.parent_id is None:
            roots.append(node)
        else:
            parent = by_id.get(n.parent_id)
            if parent is not None:
                parent.children.append(node)
            else:
                roots.append(node)

    roots.sort(key=lambda x: (x.order, x.title))
    for r in roots:
        r.children.sort(key=lambda x: (x.order, x.title))

    return OutlineTreeResponse(work_id=work_id, nodes=roots)


@router.post(
    "/outline",
    response_model=OutlineNodeRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建大纲节点",
)
async def create_outline_node_endpoint(
    payload: OutlineNodeCreate,
    db: AsyncSession = Depends(get_db),
) -> OutlineNodeRead:
    node = await outline_service.create_outline_node(db, payload)
    await db.commit()
    await db.refresh(node)
    return OutlineNodeRead.model_validate(node)


@router.get(
    "/outline/{node_id}",
    response_model=OutlineNodeRead,
    summary="获取大纲节点",
)
async def get_outline_node_endpoint(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> OutlineNodeRead:
    node = await outline_service.get_outline_node(db, node_id)
    return OutlineNodeRead.model_validate(node)


@router.patch(
    "/outline/{node_id}",
    response_model=OutlineNodeRead,
    summary="更新大纲节点",
)
async def update_outline_node_endpoint(
    node_id: UUID,
    payload: OutlineNodeUpdate,
    db: AsyncSession = Depends(get_db),
) -> OutlineNodeRead:
    node = await outline_service.update_outline_node(db, node_id, payload)
    await db.commit()
    await db.refresh(node)
    return OutlineNodeRead.model_validate(node)


@router.delete(
    "/outline/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除大纲节点（级联删除子节点）",
)
async def delete_outline_node_endpoint(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await outline_service.delete_outline_node(db, node_id)
    await db.commit()
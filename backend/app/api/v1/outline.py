"""大纲节点 CRUD API"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.plot_agent import PlotAgent
from app.deps import get_db
from app.models.outline import OutlineNode, OutlineNodeType
from app.schemas.outline import (
    BulkOutlineCreateRequest,
    OutlineNodeCreate,
    OutlineNodeListResponse,
    OutlineNodeRead,
    OutlineNodeUpdate,
    OutlineTreeNode,
    OutlineTreeResponse,
    PlotChapterExpandRequest,
    PlotChapterExpandResponse,
    PlotOutlineRequest,
    PlotOutlineResponse,
)
from app.services import outline_service

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
        n.id: _to_tree_node(n) for n in items
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


def _to_tree_node(n: OutlineNode) -> OutlineTreeNode:
    """ORM 节点 → 树节点（含约束锁）。"""
    return OutlineTreeNode(
        id=n.id,
        parent_id=n.parent_id,
        type=n.type,
        title=n.title,
        summary=n.summary,
        beats=n.beats or [],
        characters_involved=n.characters_involved or [],
        world_refs=n.world_refs or [],
        target_word_count=n.target_word_count,
        order=n.order,
        write_constraints=n.write_constraints or {},
        children=[],
    )


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


@router.post(
    "/outline/{node_id}/ai-expand",
    response_model=PlotChapterExpandResponse,
    summary="AI 扩写本章细纲（PlotAgent，不写库）",
)
async def expand_outline_node_endpoint(
    node_id: UUID,
    payload: PlotChapterExpandRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> PlotChapterExpandResponse:
    """只返回建议；采用后由前端 PATCH /outline/{id}。卷纲不可扩写。"""
    node = await outline_service.get_outline_node(db, node_id)
    if node.type == OutlineNodeType.VOLUME:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="请选择章纲或节拍节点再扩写细纲，卷纲不能直接扩写成章细纲。",
        )
    agent = PlotAgent()
    hint = payload.extra_hint if payload else None
    result, _model = await agent.expand_chapter_outline(db, node=node, extra_hint=hint)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="细纲扩写失败，请稍后重试或先手改简介与约束锁。",
        )
    return result


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


@router.post(
    "/works/{work_id}/outline/ai-outline",
    response_model=PlotOutlineResponse,
    summary="AI 推荐大纲（卷→章，不写入 DB）",
)
async def ai_generate_outline(
    work_id: UUID,
    payload: PlotOutlineRequest,
    db: AsyncSession = Depends(get_db),
) -> PlotOutlineResponse:
    agent = PlotAgent()
    response, _model = await agent.generate_outline(
        db,
        work_id=work_id,
        total_volumes=payload.total_volumes,
        target_chapter_count=payload.target_chapter_count,
        extra_hint=payload.extra_hint,
    )
    return response


class WorkPreview(BaseModel):
    """作品预览数据（用于 AI 在作品创建前调用大纲生成）"""

    title: str = Field(..., min_length=1, max_length=200)
    genre: str | None = None
    logline: str | None = None
    style_keywords: list[str] = Field(default_factory=list)
    target_audience: list[str] = Field(default_factory=list)
    notes: str | None = None
    target_word_count: int | None = Field(default=None, ge=1000, le=10_000_000)


class PlotOutlinePreviewRequest(BaseModel):
    """AI 推荐大纲预览请求（不要求 work_id）"""

    work_preview: WorkPreview
    total_volumes: int = Field(default=3, ge=1, le=10)
    target_chapter_count: int | None = Field(default=None, ge=1, le=200)
    extra_hint: str | None = Field(default=None, max_length=500)


@router.post(
    "/outline/ai-preview",
    response_model=PlotOutlineResponse,
    summary="AI 推荐大纲（预览模式：work 尚未创建，传 inline 数据）",
)
async def ai_generate_outline_preview(
    payload: PlotOutlinePreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> PlotOutlineResponse:
    """Wizard 等"作品尚未入库"的场景下使用：把 work 字段 inline 传给 Agent。"""
    from app.models.work import Work

    work = Work(
        id=UUID(int=0),  # 占位;不会写库
        title=payload.work_preview.title,
        genre=payload.work_preview.genre,
        logline=payload.work_preview.logline,
        style_keywords=payload.work_preview.style_keywords,
        target_audience=payload.work_preview.target_audience,
        notes=payload.work_preview.notes,
        target_word_count=payload.work_preview.target_word_count,
    )
    agent = PlotAgent()
    response, _model = await agent.generate_outline(
        db,
        work=work,
        total_volumes=payload.total_volumes,
        target_chapter_count=payload.target_chapter_count,
        extra_hint=payload.extra_hint,
    )
    return response


@router.post(
    "/works/{work_id}/outline/bulk-create",
    response_model=OutlineTreeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="批量写入大纲（来自 AI 推荐结果，单事务保证一致）",
)
async def bulk_create_outline_nodes(
    work_id: UUID,
    payload: BulkOutlineCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> OutlineTreeResponse:
    """一次性写入卷→章两层 OutlineNode。

    - 每个 volume 创建 type=volume 节点
    - 每个 chapter 创建 type=chapter 节点(parent_id=对应 volume.id)
    - 整批在同一事务中提交,失败回滚
    """
    # 校验作品存在
    from app.models.work import Work
    exists = await db.execute(select(Work.id).where(Work.id == work_id))
    if not exists.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"作品 {work_id} 不存在",
        )

    created_nodes: list[OutlineNode] = []
    order_vol = 0
    for vol in payload.volumes:
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
            target_word_count=3000,
            order=order_vol,
        )
        db.add(vol_node)
        await db.flush()  # 取到 vol_node.id
        created_nodes.append(vol_node)

        order_ch = 0
        for ch in vol.chapters:
            order_ch += 1
            # 把 beat 标题与 summary 拍平为 beats(str) 列表
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
                target_word_count=max(100, min(20_000, ch.target_word_count or 3000)),
                order=order_ch,
            )
            db.add(ch_node)
            created_nodes.append(ch_node)

    await db.commit()
    for n in created_nodes:
        await db.refresh(n)

    # 构造响应树
    by_id: dict[UUID, OutlineTreeNode] = {
        n.id: _to_tree_node(n) for n in created_nodes
    }
    roots: list[OutlineTreeNode] = []
    for n in created_nodes:
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
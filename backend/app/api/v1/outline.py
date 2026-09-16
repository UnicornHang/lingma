"""大纲节点 CRUD API"""
import asyncio
import json
import logging
from types import SimpleNamespace
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.plot_agent import PlotAgent
from app.agents.plot_outline_parse import OUTLINE_VOLUME_ATTEMPTS, parse_one_volume
from app.deps import get_db
from app.models.outline import OutlineNode, OutlineNodeType
from app.models.work import Genre
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
    PlotVolume,
)
from app.services import outline_service
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

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
    extra_hint: str | None = Field(default=None, max_length=4000)


def _sse(event: str, payload: dict) -> str:
    """构造单条 SSE 消息。"""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _preview_work_namespace(payload: PlotOutlinePreviewRequest) -> SimpleNamespace:
    """把向导 inline 字段转成 PlotAgent 可用的 work 形对象，不写库。"""
    genre_raw = (payload.work_preview.genre or "other").strip().lower()
    try:
        genre = Genre(genre_raw)
    except ValueError:
        genre = Genre.OTHER
    return SimpleNamespace(
        title=payload.work_preview.title,
        genre=genre,
        logline=payload.work_preview.logline or "",
        style_keywords=payload.work_preview.style_keywords,
        target_audience=payload.work_preview.target_audience,
        notes=payload.work_preview.notes or "",
        target_word_count=payload.work_preview.target_word_count or 1_000_000,
    )


def _preview_chapter_count(payload: PlotOutlinePreviewRequest, work: SimpleNamespace) -> int:
    """向导未指定章数时给 3–6 章/卷骨架，上限 20，避免一次生成过长。"""
    chapter_count = payload.target_chapter_count
    if chapter_count is None:
        words = work.target_word_count or 1_000_000
        chapter_count = min(20, max(payload.total_volumes * 3, words // 5_000))
    return chapter_count


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
    work = _preview_work_namespace(payload)
    agent = PlotAgent()
    chapter_count = _preview_chapter_count(payload, work)
    response, _model = await agent.generate_outline(
        db,
        work=work,
        total_volumes=payload.total_volumes,
        target_chapter_count=chapter_count,
        extra_hint=payload.extra_hint,
    )
    return response


@router.post(
    "/outline/ai-preview/stream",
    summary="AI 推荐大纲（SSE：心跳保活 + 流式 delta）",
    description=(
        "与 /outline/ai-preview 相同输入。"
        "事件：started → (volume_started → llm_delta* → volume)* → done。"
        "按卷多次调用 LLM，避免 60 章一次 JSON 被截断。"
        "思考阶段每 12s 发送 SSE comment 心跳，避免 Vite 代理空等掐连接。"
    ),
)
async def ai_generate_outline_preview_stream(
    payload: PlotOutlinePreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """长连接推送大纲预览。DB 访问在生成器启动前完成。"""
    work = _preview_work_namespace(payload)
    chapter_count = _preview_chapter_count(payload, work)
    agent = PlotAgent()
    session = await agent.prepare_outline_session(
        db,
        work=work,
        total_volumes=payload.total_volumes,
        target_chapter_count=chapter_count,
        extra_hint=payload.extra_hint,
    )
    if session is None:
        async def _fail():
            """装配失败时立刻结束 SSE，避免空响应。"""
            yield _sse("error", {"error": "无法装配大纲请求"})

        return StreamingResponse(
            _fail(),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

    llm = get_llm_service()

    async def event_gen():
        """按卷流式生成：每卷独立 LLM 调用，完成后立刻推 volume 事件。"""
        yield _sse("started", {
            "model": session.model_name,
            "chapter_count": sum(session.chapter_counts),
            "total_volumes": session.total_volumes,
        })
        volumes: list[PlotVolume] = []
        raw_parts: list[str] = []
        for i, n_ch in enumerate(session.chapter_counts):
            vol_no = i + 1
            yield _sse("volume_started", {
                "vol_no": vol_no,
                "total": session.total_volumes,
                "chapter_count": n_ch,
            })
            parsed_vol: PlotVolume | None = None
            last_raw = ""
            last_error: str | None = None
            for attempt in range(OUTLINE_VOLUME_ATTEMPTS):
                if attempt > 0:
                    yield _sse("volume_retry", {
                        "vol_no": vol_no,
                        "attempt": attempt + 1,
                        "total_attempts": OUTLINE_VOLUME_ATTEMPTS,
                        "total": session.total_volumes,
                    })
                req = agent.make_one_volume_request(
                    session, i, volumes, attempt=attempt,
                )
                req.stream = True
                vol_raw = ""
                failed_msg: str | None = None
                async for kind, item in _pump_one_stream(llm, req, session.cfg):
                    if kind == "keepalive":
                        yield ": keepalive\n\n"
                    elif kind == "delta":
                        yield _sse("llm_delta", {"content": item, "vol_no": vol_no})
                    elif kind == "error":
                        failed_msg = str(item)
                        break
                    else:
                        vol_raw = str(item or "")
                if failed_msg:
                    last_error = failed_msg
                    logger.warning(
                        "outline preview 第 %d 卷第 %d 次 LLM 失败: %s",
                        vol_no, attempt + 1, failed_msg,
                    )
                    continue
                last_raw = vol_raw
                parsed_vol = parse_one_volume(vol_raw, vol_no)
                if parsed_vol is not None:
                    break
                logger.warning(
                    "outline preview 第 %d 卷第 %d 次解析为空 raw_len=%d",
                    vol_no, attempt + 1, len(vol_raw),
                )
            raw_parts.append(last_raw)
            if parsed_vol is None:
                if not volumes:
                    yield _sse("error", {
                        "error": last_error or f"第 {vol_no} 卷多次未能解析出大纲",
                    })
                    return
                logger.warning(
                    "outline preview 第 %d 卷失败，返回已连续完成的 %d 卷",
                    vol_no, len(volumes),
                )
                break
            volumes.append(parsed_vol)
            yield _sse("volume", {"volume": parsed_vol.model_dump()})

        raw = "\n".join(raw_parts)
        yield _sse("done", {
            "volumes": [v.model_dump() for v in volumes],
            "model_used": session.model_name,
            "raw_content": raw[:4000],
        })

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


async def _pump_one_stream(llm, req, cfg):
    """单次 LLM 流：yield (keepalive|delta|error|end, payload)，含 12s 心跳。"""
    queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

    async def pump() -> None:
        try:
            async for delta in llm.stream(req, cfg):
                if delta:
                    await queue.put(("delta", delta))
            await queue.put(("end", None))
        except Exception as e:  # noqa: BLE001
            logger.warning("outline preview stream LLM 失败: %s", e)
            await queue.put(("error", str(e)))

    task = asyncio.create_task(pump())
    raw_chunks: list[str] = []
    try:
        while True:
            try:
                kind, payload_item = await asyncio.wait_for(queue.get(), timeout=12.0)
            except asyncio.TimeoutError:
                yield ("keepalive", None)
                continue
            if kind == "delta":
                text = str(payload_item)
                raw_chunks.append(text)
                yield ("delta", text)
                await asyncio.sleep(0)
            elif kind == "error":
                yield ("error", payload_item)
                return
            else:
                yield ("end", "".join(raw_chunks))
                return
    finally:
        if not task.done():
            task.cancel()


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
    created_nodes = await outline_service.bulk_create_volumes(
        db, work_id, payload.volumes
    )
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
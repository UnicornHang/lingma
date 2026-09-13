"""RAG 向量记忆 API"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.character import Character
from app.models.chapter import Chapter
from app.models.world import WorldBible
from app.schemas.rag import (
    RagHealthResponse,
    RagIndexRequest,
    RagIndexResponse,
    RagSearchRequest,
    RagSearchResponse,
)
from app.services.rag_service import get_rag_service, rag_search_with_stats
from app.services.vector_store import health_check

router = APIRouter()


@router.post(
    "/rag/search",
    response_model=RagSearchResponse,
    summary="RAG 检索(跨 character/world/chapter 三类)",
)
async def rag_search_endpoint(
    payload: RagSearchRequest,
) -> RagSearchResponse:
    hits, backend, ms = await rag_search_with_stats(
        work_id=payload.work_id,
        query=payload.query,
        top_k=payload.top_k,
        target_types=payload.target_types,
    )
    return RagSearchResponse(
        hits=hits,
        backend=backend,
        query_ms=round(ms, 2),
        message=("RAG 不可用,返回空结果" if backend == "disabled" else None),
    )


@router.post(
    "/rag/index",
    response_model=RagIndexResponse,
    summary="RAG 索引(运维/调试用,正常由 service 自动触发)",
)
async def rag_index_endpoint(
    payload: RagIndexRequest,
    db: AsyncSession = Depends(get_db),
) -> RagIndexResponse:
    svc = get_rag_service()
    indexed = 0
    if payload.target_type == "character":
        result = await db.get(Character, payload.target_id)
        if result is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "角色不存在")
        indexed = await svc.index_character(db, result)
    elif payload.target_type == "world":
        result = await db.get(WorldBible, payload.target_id)
        if result is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "世界书不存在")
        indexed = await svc.index_world(db, result)
    elif payload.target_type == "chapter":
        result = await db.get(Chapter, payload.target_id)
        if result is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "章节不存在")
        indexed = await svc.index_chapter_summary(db, result)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"未知 target_type: {payload.target_type}")

    from app.services.embedding_service import get_embedding_service
    from app.services.vector_store import get_vector_store

    es = get_embedding_service()
    vs = get_vector_store()
    backend = "chroma" if (es.is_available() and vs.is_available()) else "disabled"
    return RagIndexResponse(
        indexed_chunks=indexed,
        backend=backend,
        ms=0.0,
        message=("RAG 不可用,索引跳过" if backend == "disabled" else None),
    )


@router.get(
    "/rag/health",
    response_model=RagHealthResponse,
    summary="RAG 健康检查",
)
async def rag_health_endpoint() -> RagHealthResponse:
    h = health_check()
    available = bool(h["vector_store_available"] and h["embedding_available"])
    msg_parts = []
    if not h["vector_store_available"]:
        msg_parts.append("chromadb 不可用")
    if not h["embedding_available"]:
        msg_parts.append("sentence-transformers 不可用")
    if not h["rag_enabled"]:
        msg_parts.append("RAG 总开关关闭")
    msg = "; ".join(msg_parts) if msg_parts else "ok"
    return RagHealthResponse(
        available=available,
        vector_store_available=h["vector_store_available"],
        embedding_available=h["embedding_available"],
        embedding_model=h["embedding_model"],
        vector_store_path=h["vector_store_path"],
        rag_enabled=h["rag_enabled"],
        message=msg,
    )
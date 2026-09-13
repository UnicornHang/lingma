"""RAG Service - 段落级向量索引与检索

对应 PRD §4.11:
- 段落级 chunking:200-500 字(配置项)
- 三类语料:character / world / chapter summary
- 检索时三类合并排序取 top_k

设计目标:
- 优雅降级:chromadb/sentence-transformers 不可用时所有方法返回空
- 不阻塞业务:index/search 失败均 log warning,不抛
- 单例服务:无状态,全局一个实例即可
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.character import Character
from app.models.chapter import Chapter
from app.models.world import WorldBible
from app.schemas.rag import RagHit
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import (
    collection_name,
    get_vector_store,
)

logger = logging.getLogger(__name__)


# ==================== Chunking ====================


_PARAGRAPH_SEPARATORS = re.compile(r"\n\n+|(?<=[。！？!?])\n")


def _chunk_text(
    text: str,
    *,
    min_chars: int | None = None,
    max_chars: int | None = None,
) -> list[str]:
    """段落级 chunking。

    策略:
    1. 按段落分隔符切分(\\n\\n 或句末换行)
    2. 短段落(<min_chars)合并
    3. 长段落(>max_chars)二次切分(按句子)
    4. 极短文本(<min_chars 整段)作为单 chunk 返回

    Args:
        text: 输入文本
        min_chars: 段落最小字符数(默认 settings.rag_chunk_min_chars)
        max_chars: 段落最大字符数(默认 settings.rag_chunk_max_chars)

    Returns:
        list[str]: chunk 列表(已 strip,空 chunk 过滤)
    """
    if not text or not text.strip():
        return []
    min_c = min_chars if min_chars is not None else settings.rag_chunk_min_chars
    max_c = max_chars if max_chars is not None else settings.rag_chunk_max_chars

    # 1) 切分
    raw_parts = _PARAGRAPH_SEPARATORS.split(text)
    raw_parts = [p.strip() for p in raw_parts if p and p.strip()]
    if not raw_parts:
        return [text.strip()] if text.strip() else []

    # 2) 合并短段落(buf <= min_c 时继续合并,直到 > min_c)
    merged: list[str] = []
    buf = ""
    for part in raw_parts:
        if not buf:
            buf = part
        elif len(buf) <= min_c:
            buf = buf + "\n\n" + part
        else:
            merged.append(buf)
            buf = part
    if buf:
        merged.append(buf)

    # 3) 二次切分长段落
    final: list[str] = []
    for chunk in merged:
        if len(chunk) <= max_c:
            final.append(chunk)
        else:
            # 按句子切
            sentences = re.split(r"(?<=[。！？!?])\s*", chunk)
            cur = ""
            for s in sentences:
                if not s:
                    continue
                if len(cur) + len(s) + 1 > max_c and cur:
                    final.append(cur.strip())
                    cur = s
                else:
                    cur = (cur + " " + s).strip() if cur else s
            if cur:
                final.append(cur.strip())

    # 过滤空
    return [c for c in final if c]


# ==================== Service ====================


class RagService:
    """RAG 业务层(单例)

    - index_character / index_world / index_chapter_summary:索引或 reindex
    - search:跨三类 collection 合并排序取 top_k
    - delete_character / delete_world / delete_chapter:清理对应 collection
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

    # ----- index -----

    async def index_character(self, db: AsyncSession, character: Character) -> int:
        """索引一个角色卡(全文 + raw_text)。返回写入的 chunk 数。

        - 不可用时返回 0
        - 失败 log warning,不抛
        """
        if not settings.rag_enabled:
            return 0
        texts = _character_texts(character)
        if not texts:
            return 0
        return await _upsert_chunks(
            work_id=character.work_id,
            target_type="character",
            target_id=str(character.id),
            chunks=texts,
            metadata={"character_id": str(character.id), "character_name": character.name},
        )

    async def index_world(self, db: AsyncSession, world: WorldBible) -> int:
        """索引一个世界书的 raw_text。"""
        if not settings.rag_enabled:
            return 0
        text = (world.raw_text or "").strip()
        if not text:
            return 0
        return await _upsert_chunks(
            work_id=world.work_id,
            target_type="world",
            target_id=str(world.id),
            chunks=_chunk_text(text),
            metadata={"world_id": str(world.id)},
        )

    async def index_chapter_summary(self, db: AsyncSession, chapter: Chapter) -> int:
        """索引一个章节摘要(summary 缺失时用 plain_content 前 300 字兜底)。"""
        if not settings.rag_enabled:
            return 0
        text = (chapter.summary or "").strip()
        if not text:
            plain = (chapter.plain_content or "").strip()
            text = plain[:300] if plain else ""
        if not text:
            return 0
        return await _upsert_chunks(
            work_id=chapter.work_id,
            target_type="chapter",
            target_id=str(chapter.id),
            chunks=[text],  # 摘要通常 < 500 字,直接单 chunk
            metadata={
                "chapter_id": str(chapter.id),
                "chapter_title": chapter.title or "",
            },
        )

    # ----- search -----

    async def search(
        self,
        work_id: UUID,
        query: str,
        *,
        top_k: int | None = None,
        target_types: Iterable[str] | None = None,
    ) -> list[RagHit]:
        """跨三类 collection 检索,合并后取 top_k。

        Args:
            work_id: 作品 id
            query: 查询文本
            top_k: 返回条数(默认 settings.rag_top_k)
            target_types: 要检索的类型子集;None = 全 3 类

        Returns:
            list[RagHit],按 score 升序(距离越近越相关);不可用时返回空
        """
        if not settings.rag_enabled or not query or not query.strip():
            return []
        es = get_embedding_service()
        if not es.is_available():
            return []
        vs = get_vector_store()
        if not vs.is_available():
            return []

        k = top_k if top_k is not None else settings.rag_top_k
        types = list(target_types) if target_types else ["character", "world", "chapter"]

        # 1) embed query(一次)
        query_vec = es.embed_query(query)
        if not query_vec:
            return []

        # 2) 各类型 collection 各取 top_k,合并
        all_hits: list[RagHit] = []
        for t in types:
            coll = vs.get_or_create_collection(collection_name(t, work_id))
            if coll is None:
                continue
            try:
                raw = coll.query(
                    query_embeddings=[query_vec],
                    n_results=k,
                )
                hits = _chroma_response_to_hits(raw, t)
                all_hits.extend(hits)
            except Exception as e:
                logger.warning("RAG query %s 失败: %s", t, e)
                continue

        # 3) 合并排序:按 score 升序(距离越小越相关),取 top_k
        all_hits.sort(key=lambda h: h.score)
        return all_hits[:k]

    # ----- delete -----

    def delete_collection_for_work(self, work_id: UUID, target_type: str) -> bool:
        """删除某个 work 的某类 collection(物理清理,不可恢复)。"""
        vs = get_vector_store()
        return vs.delete_collection(collection_name(target_type, work_id))


# ==================== 内部辅助 ====================


def _character_texts(character: Character) -> list[str]:
    """从 Character 提取可索引文本。

    优先用 raw_text;为空时拼接 basic_info/personality/backstory 等结构化字段。
    """
    raw = (character.raw_text or "").strip()
    if raw:
        return _chunk_text(raw)
    # 兜底:拼接结构化字段
    parts: list[str] = []
    if character.basic_info:
        parts.append(json.dumps(character.basic_info, ensure_ascii=False))
    if character.personality:
        parts.append(json.dumps(character.personality, ensure_ascii=False))
    if character.backstory:
        parts.append(json.dumps(character.backstory, ensure_ascii=False))
    if character.arc:
        parts.append(json.dumps(character.arc, ensure_ascii=False))
    return _chunk_text("\n\n".join(parts))


def _chroma_response_to_hits(raw: dict, target_type: str) -> list[RagHit]:
    """把 chromadb query 返回值转 RagHit 列表。

    chromadb query 返回结构:
    {
        "ids": [["id1", "id2", ...]],
        "distances": [[0.1, 0.2, ...]],
        "documents": [["doc1", "doc2", ...]],
        "metadatas": [[{"k":"v"}, ...]],
    }
    """
    hits: list[RagHit] = []
    if not raw or not raw.get("ids") or not raw["ids"][0]:
        return hits
    ids = raw["ids"][0]
    distances = (raw.get("distances") or [[]])[0]
    documents = (raw.get("documents") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]
    for i, doc_id in enumerate(ids):
        # doc_id 格式约定:{target_type}:{target_id}:{chunk_index}
        parts = doc_id.split(":", 2)
        target_id = parts[1] if len(parts) >= 2 else doc_id
        chunk_index = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
        score = float(distances[i]) if i < len(distances) else 0.0
        text = documents[i] if i < len(documents) else ""
        meta = metadatas[i] if i < len(metadatas) else {}
        if not isinstance(meta, dict):
            meta = {}
        hits.append(RagHit(
            target_type=target_type,
            target_id=target_id,
            chunk_index=chunk_index,
            text=text,
            score=score,
            metadata=meta,
        ))
    return hits


async def _upsert_chunks(
    *,
    work_id: UUID,
    target_type: str,
    target_id: str,
    chunks: list[str],
    metadata: dict[str, Any],
) -> int:
    """把 chunks 写入对应 collection(先删旧,再批量写入)。"""
    if not chunks:
        return 0
    es = get_embedding_service()
    vs = get_vector_store()
    if not es.is_available() or not vs.is_available():
        return 0

    coll = vs.get_or_create_collection(collection_name(target_type, work_id))
    if coll is None:
        return 0

    # 1) 删旧
    try:
        coll.delete(where={"target_id": target_id})
    except Exception as e:
        # 首次写入时旧记录不存在 → 不阻断
        logger.debug("RAG delete old chunks (no-op expected first time): %s", e)

    # 2) embed
    vectors = es.embed_documents(chunks)
    if not vectors or len(vectors) != len(chunks):
        logger.warning(
            "RAG embed_documents 长度不匹配: chunks=%d, vectors=%d",
            len(chunks), len(vectors),
        )
        return 0

    # 3) upsert
    ids = [f"{target_type}:{target_id}:{i}" for i in range(len(chunks))]
    metadatas = [{**metadata, "target_id": target_id, "chunk_index": i}
                 for i in range(len(chunks))]
    try:
        coll.upsert(
            ids=ids,
            embeddings=vectors,
            documents=chunks,
            metadatas=metadatas,
        )
        logger.info(
            "RAG index: type=%s, target_id=%s, chunks=%d, work=%s",
            target_type, target_id, len(chunks), work_id,
        )
        return len(chunks)
    except Exception as e:
        logger.warning("RAG upsert 失败: %s", e)
        return 0


# ==================== 单例 ====================

_instance: RagService | None = None
_instance_lock = threading.Lock()


def get_rag_service() -> RagService:
    """获取全局单例。"""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = RagService()
    return _instance


# ==================== 调试辅助 ====================


async def rag_search_with_stats(
    work_id: UUID,
    query: str,
    *,
    top_k: int | None = None,
    target_types: Iterable[str] | None = None,
) -> tuple[list[RagHit], str, float]:
    """带统计信息的搜索(供 API 端点使用)。"""
    start = time.time()
    es = get_embedding_service()
    vs = get_vector_store()
    backend = "chroma" if (es.is_available() and vs.is_available()) else "disabled"
    hits = await get_rag_service().search(
        work_id=work_id, query=query, top_k=top_k, target_types=target_types,
    )
    ms = (time.time() - start) * 1000
    return hits, backend, ms
"""RAG 相关的 Pydantic Schema

对应 PRD §4.11 向量记忆系统。
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============== 检索结果 ==============


RagTargetType = Literal["character", "world", "chapter"]


class RagHit(BaseModel):
    """单个检索命中"""

    target_type: RagTargetType
    target_id: str  # 字符串形式(UUID 也可)
    chunk_index: int = 0
    text: str = Field(..., max_length=4000)
    score: float = Field(..., ge=0.0, le=2.0)  # 余弦距离可 > 1
    metadata: dict = Field(default_factory=dict)


# ============== 检索请求/响应 ==============


class RagSearchRequest(BaseModel):
    """RAG 检索请求"""

    work_id: UUID
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    target_types: list[RagTargetType] | None = None  # None = 全 3 类


class RagSearchResponse(BaseModel):
    """RAG 检索响应"""

    hits: list[RagHit] = Field(default_factory=list)
    backend: Literal["chroma", "disabled"] = "disabled"
    query_ms: float = 0.0
    message: str | None = None


# ============== 索引请求/响应 ==============


RagIndexTargetType = Literal["character", "world", "chapter"]


class RagIndexRequest(BaseModel):
    """RAG 索引请求(供运维/调试用,正常路径由 service 自动触发)"""

    work_id: UUID
    target_type: RagIndexTargetType
    target_id: UUID


class RagIndexResponse(BaseModel):
    """RAG 索引响应"""

    indexed_chunks: int = 0
    backend: Literal["chroma", "disabled"] = "disabled"
    ms: float = 0.0
    message: str | None = None


# ============== 健康检查 ==============


class RagHealthResponse(BaseModel):
    """RAG 健康检查"""

    model_config = ConfigDict(extra="forbid")

    available: bool = False
    vector_store_available: bool = False
    embedding_available: bool = False
    embedding_model: str = ""
    vector_store_path: str = ""
    rag_enabled: bool = True
    message: str = ""
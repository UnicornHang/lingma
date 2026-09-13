"""RAG Service 单测

覆盖:
- _chunk_text 段落级拆分/合并/二次切分
- is_available=False 时所有 index/search 方法返回 0/空
- collection_name 命名约定
- RagService 单例
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.services.rag_service import (
    RagService,
    _chunk_text,
    get_rag_service,
)


# ============== Chunking 测试 ==============


def test_rag_chunk_text_splits_by_paragraph():
    """1000 字段落 → 拆成 200-500 字 chunk。"""
    text = "第一段文字" * 50 + "\n\n" + "第二段文字" * 50 + "\n\n" + "第三段文字" * 50
    chunks = _chunk_text(text, min_chars=200, max_chars=500)
    assert len(chunks) >= 2
    for c in chunks:
        # 允许 ±50 字波动(切分位置)
        assert len(c) <= 600


def test_rag_chunk_text_merges_short_paragraphs():
    """多个短段(< min_chars)应被合并。"""
    text = "短段一。" + "\n\n" + "短段二。" + "\n\n" + "短段三。"
    chunks = _chunk_text(text, min_chars=10, max_chars=500)
    # 三个短段总长 < 10 → 应合并为 1 段
    assert len(chunks) == 1


def test_rag_chunk_text_handles_empty_input():
    assert _chunk_text("") == []
    assert _chunk_text("   \n\n   ") == []
    assert _chunk_text(None) == []


def test_rag_chunk_text_handles_very_long_paragraph():
    """超长段落(> max_chars)应被二次切分。"""
    long = "长句子。" * 200  # 800 字
    chunks = _chunk_text(long, min_chars=100, max_chars=300)
    assert len(chunks) >= 2


def test_rag_chunk_text_splits_by_sentence_boundary():
    """二次切分应按句子边界(。！？)。"""
    text = "第一句。" * 30 + "第二句。" * 30 + "第三句。" * 30
    chunks = _chunk_text(text, min_chars=50, max_chars=150)
    # 每段应包含整句(不切断句子)
    for c in chunks:
        # 段末应是完整句子(以 。！？ 结尾)
        assert c.rstrip()[-1] in "。！？.!?", f"chunk 未以句子结尾: {c[-30:]}"


# ============== Service 降级测试 ==============


def test_rag_service_returns_zero_when_disabled(monkeypatch):
    """settings.rag_enabled=False → index_character 返回 0,不调用 embedding。"""
    from app.config import settings
    monkeypatch.setattr(settings, "rag_enabled", False)
    svc = RagService()
    # 即便传 character 也立即返回
    character = SimpleNamespace(id=uuid4(), work_id=uuid4(), name="x", raw_text="一段文本")
    db = AsyncMock()
    import asyncio
    result = asyncio.run(svc.index_character(db, character))
    assert result == 0


def test_rag_service_search_returns_empty_when_disabled(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "rag_enabled", False)
    svc = RagService()
    import asyncio
    result = asyncio.run(svc.search(uuid4(), "query"))
    assert result == []


def test_rag_service_search_returns_empty_when_embedding_unavailable(monkeypatch):
    """is_available=False → 返回空 list,不抛。"""
    from app.services.embedding_service import get_embedding_service
    from app.services.vector_store import get_vector_store

    es = get_embedding_service()
    monkeypatch.setattr(es, "is_available", lambda: False)

    svc = RagService()
    import asyncio
    result = asyncio.run(svc.search(uuid4(), "query"))
    assert result == []


def test_rag_service_index_returns_zero_when_unavailable(monkeypatch):
    """embedding 不可用 → index_character 返回 0,不抛。"""
    from app.services.embedding_service import get_embedding_service

    es = get_embedding_service()
    monkeypatch.setattr(es, "is_available", lambda: False)

    svc = RagService()
    character = SimpleNamespace(
        id=uuid4(), work_id=uuid4(), name="x", raw_text="一段文本",
        basic_info={}, personality={}, backstory={}, arc={},
    )
    db = AsyncMock()
    import asyncio
    result = asyncio.run(svc.index_character(db, character))
    assert result == 0


def test_rag_service_handles_empty_character_text(monkeypatch):
    """raw_text 空且结构化字段也空 → 不写入,返回 0。"""
    from app.services.embedding_service import get_embedding_service
    from app.services.vector_store import get_vector_store

    es = get_embedding_service()
    monkeypatch.setattr(es, "is_available", lambda: True)
    vs = get_vector_store()
    monkeypatch.setattr(vs, "is_available", lambda: True)

    svc = RagService()
    character = SimpleNamespace(
        id=uuid4(), work_id=uuid4(), name="空角色",
        raw_text="", basic_info={}, personality={}, backstory={}, arc={},
    )
    db = AsyncMock()
    import asyncio
    result = asyncio.run(svc.index_character(db, character))
    assert result == 0


# ============== 单例 ==============


def test_get_rag_service_returns_singleton():
    a = get_rag_service()
    b = get_rag_service()
    assert a is b


# ============== _character_texts 兜底测试 ==============


def test_character_texts_uses_raw_text_when_available(monkeypatch):
    """raw_text 存在时直接 chunk。"""
    from app.services.rag_service import _character_texts

    character = SimpleNamespace(
        raw_text="这是 raw_text 内容。" * 100,  # ~700 字,会被拆 chunk
        basic_info={"age": "18"},
    )
    texts = _character_texts(character)
    assert len(texts) >= 1


def test_character_texts_fallback_to_structured_fields(monkeypatch):
    """raw_text 空时,拼接 basic_info/personality/backstory/arc。"""
    from app.services.rag_service import _character_texts

    character = SimpleNamespace(
        raw_text="",
        basic_info={"age": "18", "occupation": "修士"},
        personality={"traits": ["坚毅"]},
        backstory={"origin": "出身寒门"},
        arc={"start_state": "无名小卒"},
    )
    texts = _character_texts(character)
    assert len(texts) >= 1
    assert "18" in texts[0] or "修士" in texts[0]


def test_character_texts_empty_when_no_data(monkeypatch):
    from app.services.rag_service import _character_texts

    character = SimpleNamespace(
        raw_text="",
        basic_info={},
        personality={},
        backstory={},
        arc={},
    )
    texts = _character_texts(character)
    assert texts == []
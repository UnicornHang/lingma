"""VectorStore 单测

覆盖:
- chromadb 未装 → is_available()=False, 所有方法 no-op
- collection_name 命名约定
- health_check 返回完整字典结构
- 单例
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.vector_store import VectorStore, collection_name, health_check


def _make_unavailable_store(monkeypatch):
    """构造一个模拟 chromadb 不可用的 VectorStore。"""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "chromadb" or name.startswith("chromadb."):
            raise ImportError("simulated chromadb missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    svc = VectorStore()
    return svc


def test_vector_store_is_available_false_when_chromadb_missing(monkeypatch):
    svc = _make_unavailable_store(monkeypatch)
    assert svc.is_available() is False


def test_vector_store_get_or_create_returns_none_when_unavailable(monkeypatch):
    svc = _make_unavailable_store(monkeypatch)
    assert svc.get_or_create_collection("lingma_character_abc") is None


def test_vector_store_delete_returns_false_when_unavailable(monkeypatch):
    svc = _make_unavailable_store(monkeypatch)
    assert svc.delete_collection("lingma_character_abc") is False


def test_vector_store_list_collections_empty_when_unavailable(monkeypatch):
    svc = _make_unavailable_store(monkeypatch)
    assert svc.list_collections() == []


def test_collection_name_convention():
    work_id = uuid4()
    name = collection_name("character", work_id)
    assert name == f"lingma_character_{work_id}"


def test_collection_name_accepts_string_work_id():
    name = collection_name("world", "abc-123")
    assert name == "lingma_world_abc-123"


def test_get_vector_store_returns_singleton():
    from app.services.vector_store import get_vector_store

    a = get_vector_store()
    b = get_vector_store()
    assert a is b


def test_health_check_returns_dict():
    """health_check 返回字典,即使依赖不可用也不抛异常。"""
    h = health_check()
    assert isinstance(h, dict)
    assert "vector_store_available" in h
    assert "embedding_available" in h
    assert "embedding_model" in h
    assert "vector_store_path" in h
    assert "rag_enabled" in h
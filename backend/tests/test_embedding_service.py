"""EmbeddingService 单测

覆盖:
- sentence_transformers 未装 → is_available()=False, embed 返回空
- 不可用时 embed_query 返回空
- 单例重复调用不重复初始化
"""
from __future__ import annotations

import pytest

from app.services.embedding_service import EmbeddingService


def _make_unavailable_service(monkeypatch):
    """构造一个模拟 sentence_transformers 不可用的 EmbeddingService。"""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "sentence_transformers" or name.startswith("sentence_transformers."):
            raise ImportError("simulated sentence_transformers missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    svc = EmbeddingService()
    return svc


def test_embedding_service_is_available_false_when_sentence_transformers_missing(monkeypatch):
    svc = _make_unavailable_service(monkeypatch)
    assert svc.is_available() is False


def test_embedding_service_embed_query_returns_empty_when_unavailable(monkeypatch):
    svc = _make_unavailable_service(monkeypatch)
    # 即便 is_available 返回 False 后,embed_query 也应返回空
    vec = svc.embed_query("一段文本")
    assert vec == []


def test_embedding_service_embed_documents_returns_empty_when_unavailable(monkeypatch):
    svc = _make_unavailable_service(monkeypatch)
    vectors = svc.embed_documents(["文本1", "文本2"])
    assert vectors == []


def test_embedding_service_embed_query_empty_input_returns_empty(monkeypatch):
    svc = _make_unavailable_service(monkeypatch)
    assert svc.embed_query("") == []
    assert svc.embed_documents([]) == []


def test_get_embedding_service_returns_singleton():
    from app.services.embedding_service import get_embedding_service

    a = get_embedding_service()
    b = get_embedding_service()
    assert a is b


def test_embedding_service_caches_failure(monkeypatch):
    """is_available() 探测失败一次后,后续直接返回 False(不应反复尝试 import)"""
    svc = _make_unavailable_service(monkeypatch)
    assert svc.is_available() is False
    assert svc.is_available() is False
    # 第三次仍返回 False(不再触发 import 探测)
    assert svc._available is False
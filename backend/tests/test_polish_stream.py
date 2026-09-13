"""SSE 流式去味单元测试

覆盖:
- detected 事件立即发出(findings + counts + stats)
- 无 findings 时直接 done,不调 LLM
- LLM 流式 delta 逐条转发
- JSON 解析成功 → done 含 rewrites
- JSON 解析失败 → done 含空 rewrites + summary 提示
- LLM 抛异常 → error 事件 + fallback payload
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    """解析 SSE 流,返回 [(event, data_dict), ...]。"""
    events: list[tuple[str, dict]] = []
    cur_event: str | None = None
    cur_data: list[str] = []
    for line in raw.split("\n"):
        if line.startswith("event:"):
            cur_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            cur_data.append(line[len("data:"):].strip())
        elif line == "" and cur_event is not None:
            # 一条事件结束
            data_str = "\n".join(cur_data)
            try:
                data = json.loads(data_str) if data_str else {}
            except json.JSONDecodeError:
                data = {"_raw": data_str}
            events.append((cur_event, data))
            cur_event = None
            cur_data = []
    return events


def _chunk_stream(chunks: list[str]) -> AsyncIterator[str]:
    """构造 async generator 模拟 LLM 流。"""

    async def _gen():
        for c in chunks:
            yield c

    return _gen()


# ============== Fixtures ==============


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


def _make_mock_cfg():
    cfg = MagicMock()
    cfg.model = "mock-model"
    cfg.provider.value = "mock"
    return cfg


# ============== 测试 ==============


async def test_stream_returns_text_event_stream_header(client):
    """响应 Content-Type 必须是 text/event-stream。"""
    with patch("app.api.v1.chapters.resolve_provider_config", new=AsyncMock(return_value=_make_mock_cfg())):
        # 用一个立即返回 [done] 的 mock 路径,只需验证 header
        async def empty_stream(*args, **kwargs):
            if False:
                yield ""

        with patch("app.services.llm_service.LLMService.stream", return_value=empty_stream(None, None)):
            r = await client.post(
                "/api/v1/chapters/polish/stream",
                json={"text": "短文本测试"},
            )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")


async def test_stream_no_findings_done_immediately(client):
    """无 findings → 直接 done,不调 LLM。"""
    # 输入故意写得「干净」让检测器找不到任何 finding
    clean_text = "他推开木门。"

    with patch("app.api.v1.chapters.resolve_provider_config", new=AsyncMock(return_value=_make_mock_cfg())), \
         patch("app.services.llm_service.LLMService.stream", side_effect=AssertionError("LLM 不应被调用")):
        r = await client.post(
            "/api/v1/chapters/polish/stream",
            json={"text": clean_text},
        )
    assert r.status_code == 200
    events = _parse_sse(r.text)
    types = [t for t, _ in events]

    assert types[0] == "detected"
    assert types[-1] == "done"
    done = next(d for e, d in events if e == "done")
    assert done["polished_text"] == clean_text
    assert done["rewrites"] == []


async def test_stream_emits_detected_then_llm_started_then_delta_then_done(client):
    """正常路径事件序列:detected → llm_started → llm_delta* → done。"""
    # 「并不是…而是…」是已知的 neg-pos-flip 检测触发器
    text = "他并不是为了报仇,而是为了那笔遗产。"

    fake_chunks = ['{"rewrites": [{"category": "neg-pos-flip", "original": "并不是为了报仇,而是为了那笔遗产", "rewritten": "为那笔遗产而来", "reason": "去双重否定"}], "summary": "已精简"}']

    with patch("app.api.v1.chapters.resolve_provider_config", new=AsyncMock(return_value=_make_mock_cfg())), \
         patch("app.services.llm_service.LLMService.stream", return_value=_chunk_stream(fake_chunks)):
        r = await client.post(
            "/api/v1/chapters/polish/stream",
            json={"text": text},
        )

    assert r.status_code == 200
    events = _parse_sse(r.text)
    types = [t for t, _ in events]

    assert types[0] == "detected"
    assert "llm_started" in types
    assert "llm_delta" in types
    assert types[-1] == "done"


async def test_stream_done_payload_contains_rewrites(client):
    """正常路径 done 事件含 rewrites + polished_text。"""
    text = "他并不是为了报仇,而是为了那笔遗产。"

    chunks = ['{"rewrites": [{"category": "neg-pos-flip", "original": "并不是为了报仇,而是为了那笔遗产", "rewritten": "为那笔遗产而来", "reason": "r"}], "summary": "改完"}']

    with patch("app.api.v1.chapters.resolve_provider_config", new=AsyncMock(return_value=_make_mock_cfg())), \
         patch("app.services.llm_service.LLMService.stream", return_value=_chunk_stream(chunks)):
        r = await client.post(
            "/api/v1/chapters/polish/stream",
            json={"text": text},
        )
    events = _parse_sse(r.text)
    done = next(d for e, d in events if e == "done")
    assert len(done["rewrites"]) == 1
    assert done["rewrites"][0]["rewritten"] == "为那笔遗产而来"
    assert done["polished_text"] != text


async def test_stream_json_parse_failure_returns_empty_rewrites(client):
    """LLM 输出非 JSON → done 含空 rewrites + summary 提示。"""
    text = "他并不是为了报仇,而是为了那笔遗产。"

    chunks = ["这不是 JSON 内容,只是一段纯文本。"]

    with patch("app.api.v1.chapters.resolve_provider_config", new=AsyncMock(return_value=_make_mock_cfg())), \
         patch("app.services.llm_service.LLMService.stream", return_value=_chunk_stream(chunks)):
        r = await client.post(
            "/api/v1/chapters/polish/stream",
            json={"text": text},
        )
    events = _parse_sse(r.text)
    done = next(d for e, d in events if e == "done")
    assert done["rewrites"] == []
    assert "JSON" in done["summary"] or "解析" in done["summary"]


async def test_stream_llm_exception_emits_error_with_fallback(client):
    """LLM 流式抛异常 → error 事件 + fallback payload。"""
    text = "他并不是为了报仇,而是为了那笔遗产。"

    async def failing_stream(*args, **kwargs):
        raise RuntimeError("LLM boom")
        yield ""  # noqa: 让 async gen 合法

    with patch("app.api.v1.chapters.resolve_provider_config", new=AsyncMock(return_value=_make_mock_cfg())), \
         patch("app.services.llm_service.LLMService.stream", side_effect=failing_stream):
        r = await client.post(
            "/api/v1/chapters/polish/stream",
            json={"text": text},
        )
    events = _parse_sse(r.text)
    error = next((d for e, d in events if e == "error"), None)
    assert error is not None
    assert error["phase"] == "llm"
    assert "fallback" in error
    assert error["fallback"]["polished_text"] == text


async def test_stream_detected_event_includes_findings_stats(client):
    """detected 事件 payload 必须包含 findings + blocking_count + stats。"""
    text = "他并不是为了报仇,而是为了那笔遗产。"

    chunks = ['{"rewrites": [], "summary": "无"}']

    with patch("app.api.v1.chapters.resolve_provider_config", new=AsyncMock(return_value=_make_mock_cfg())), \
         patch("app.services.llm_service.LLMService.stream", return_value=_chunk_stream(chunks)):
        r = await client.post(
            "/api/v1/chapters/polish/stream",
            json={"text": text},
        )
    events = _parse_sse(r.text)
    detected = next(d for e, d in events if e == "detected")
    assert "findings" in detected
    assert "blocking_count" in detected
    assert "advisory_count" in detected
    assert "stats" in detected
    assert isinstance(detected["blocking_count"], int)
    assert detected["blocking_count"] >= 1  # 必然检出 neg-pos-flip
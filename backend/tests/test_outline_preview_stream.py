"""大纲预览 SSE：心跳保活路径的事件序列。"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


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
            data_str = "\n".join(cur_data)
            try:
                data = json.loads(data_str) if data_str else {}
            except json.JSONDecodeError:
                data = {"_raw": data_str}
            events.append((cur_event, data))
            cur_event = None
            cur_data = []
    return events


def _preview_payload() -> dict:
    """向导预览最小请求体。"""
    return {
        "work_preview": {
            "title": "我有一枪，可问长生",
            "genre": "fantasy",
            "logline": "凡人以枪杀仙",
            "style_keywords": ["热血"],
            "target_audience": ["男频"],
            "target_word_count": 100_000,
        },
        "total_volumes": 2,
        "target_chapter_count": 4,
    }


async def _chunk_stream(chunks: list[str]):
    """模拟 LLM 流式输出。"""
    for c in chunks:
        yield c


_VOL1_JSON = (
    '{"volumes":[{"vol_no":1,"vol_title":"第一卷 · 少年枪鸣","summary":"家破",'
    '"chapters":[{"title":"十年磨枪","summary":"习武","target_word_count":3000,'
    '"beats":["练枪","立志","亲授"],"characters_involved":["沈砚"],'
    '"world_refs":[],"key_events":["枪成"]}]}]}'
)
_VOL2_JSON = (
    '{"volumes":[{"vol_no":2,"vol_title":"第二卷 · 血路独行","summary":"寻亲",'
    '"chapters":[{"title":"残垣独醒","summary":"苏醒","target_word_count":3000}]}]}'
)


def _volume_streams():
    """两卷各一次 LLM 流，避免 exhaust 后第二次空读。"""
    return [_chunk_stream([_VOL1_JSON]), _chunk_stream([_VOL2_JSON])]


@pytest.mark.asyncio
async def test_outline_preview_stream_done_contains_volumes(client):
    """SSE 按卷推送，done 带回全部卷。"""
    from app.services.llm_service import LLMService

    streams = _volume_streams()
    with patch.object(LLMService, "stream", side_effect=lambda *_a, **_k: streams.pop(0)):
        r = await client.post("/api/v1/outline/ai-preview/stream", json=_preview_payload())
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    events = _parse_sse(r.text)
    types = [t for t, _ in events]
    assert types[0] == "started"
    assert types.count("volume_started") == 2
    assert types.count("volume") == 2
    assert "llm_delta" in types
    assert types[-1] == "done"
    done = next(d for e, d in events if e == "done")
    assert [v["vol_title"] for v in done["volumes"]] == [
        "第一卷 · 少年枪鸣",
        "第二卷 · 血路独行",
    ]


@pytest.mark.asyncio
async def test_outline_preview_stream_llm_error_emits_error(client):
    """LLM 抛错 → error 事件。"""

    async def failing_stream(*_args, **_kwargs):
        raise RuntimeError("LLM boom")
        yield ""  # noqa: 让 async gen 合法

    from app.services.llm_service import LLMService

    with patch.object(LLMService, "stream", side_effect=failing_stream):
        r = await client.post("/api/v1/outline/ai-preview/stream", json=_preview_payload())
    assert r.status_code == 200
    events = _parse_sse(r.text)
    error = next((d for e, d in events if e == "error"), None)
    assert error is not None
    assert "LLM boom" in str(error.get("error", ""))


@pytest.mark.asyncio
async def test_outline_preview_retries_then_parses_volume(client):
    """第一卷前两次无法解析，第三次成功后继续第二卷。"""
    from app.services.llm_service import LLMService

    streams = [
        _chunk_stream(["<think>planning</think>"]),
        _chunk_stream(["not json"]),
        _chunk_stream([_VOL1_JSON]),
        _chunk_stream([_VOL2_JSON]),
    ]
    with patch.object(LLMService, "stream", side_effect=lambda *_a, **_k: streams.pop(0)):
        r = await client.post("/api/v1/outline/ai-preview/stream", json=_preview_payload())
    events = _parse_sse(r.text)
    types = [t for t, _ in events]
    assert "volume_retry" in types
    done = next(d for e, d in events if e == "done")
    assert [v["vol_no"] for v in done["volumes"]] == [1, 2]


@pytest.mark.asyncio
async def test_outline_preview_does_not_skip_to_later_volume(client):
    """第一卷三次都解析失败时不得跳去生成第二卷。"""
    from app.services.llm_service import LLMService

    streams = [
        _chunk_stream(["nope"]),
        _chunk_stream(["still nope"]),
        _chunk_stream(["nope again"]),
        _chunk_stream([_VOL2_JSON]),
    ]
    with patch.object(LLMService, "stream", side_effect=lambda *_a, **_k: streams.pop(0)):
        r = await client.post("/api/v1/outline/ai-preview/stream", json=_preview_payload())
    events = _parse_sse(r.text)
    types = [t for t, _ in events]
    assert types.count("volume") == 0
    assert types[-1] == "error"
    assert _VOL2_JSON not in r.text
    assert len(streams) == 1

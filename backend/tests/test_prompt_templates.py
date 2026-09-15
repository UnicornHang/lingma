"""[P4] Prompt 模板管理测试。"""
from __future__ import annotations

import pytest

from app.services.prompt_template_service import render_placeholders


def test_render_placeholders():
    """简单 {{var}} 替换。"""
    text = "目标 {{target_words}} 字,共 {{persona_count}} 人"
    out = render_placeholders(
        text, {"target_words": "3000", "persona_count": "5"}
    )
    assert out == "目标 3000 字,共 5 人"
    # 缺失保留原样
    assert "{{missing}}" in render_placeholders("x={{missing}}", {})


@pytest.mark.asyncio
async def test_list_and_update_prompt(client):
    """列出 6 个模板,更新 writer,重置。"""
    listed = await client.get("/api/v1/settings/prompts")
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert len(items) == 6
    types = {i["agent_type"] for i in items}
    assert types == {"writer", "plot", "world", "character", "editor", "critic"}

    writer = next(i for i in items if i["agent_type"] == "writer")
    assert "{{target_words}}" in writer["system_prompt"] or "字" in writer["system_prompt"]

    updated = await client.patch(
        "/api/v1/settings/prompts/writer",
        json={"system_prompt": "你是自定义作家。目标 {{target_words}} 字。" * 2},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["is_customized"] is True
    assert "自定义作家" in body["system_prompt"]

    disabled = await client.patch(
        "/api/v1/settings/prompts/writer",
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    reset = await client.post("/api/v1/settings/prompts/writer/reset")
    assert reset.status_code == 200, reset.text
    assert reset.json()["enabled"] is True
    assert reset.json()["is_customized"] is False


@pytest.mark.asyncio
async def test_unknown_agent_404(client):
    """未知 agent 返回 404。"""
    r = await client.get("/api/v1/settings/prompts/unknown")
    assert r.status_code == 404

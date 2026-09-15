"""世界观一致性检查:启发式 + API。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.chapter import Chapter
from app.models.work import Genre, Work, WorkStatus
from app.models.world import WorldBible
from app.prompts.world_prompts import (
    build_consistency_system_prompt,
    build_consistency_user_prompt,
)
from app.services.world_consistency import (
    extract_rule_lines,
    heuristic_scan,
    is_world_empty,
    merge_issues,
    parse_llm_issues,
)


def test_consistency_system_prompt_json_only():
    sys_p = build_consistency_system_prompt()
    assert "只输出 JSON" in sys_p
    assert "power_system_violation" in sys_p


def test_consistency_user_prompt_includes_world_and_text():
    user_p = build_consistency_user_prompt(
        work_title="仙逆",
        world_brief="筑基期无法飞行",
        text="筑基期修士飞行千里",
        chapter_title="第一章",
    )
    assert "仙逆" in user_p
    assert "筑基期无法飞行" in user_p
    assert "飞行千里" in user_p
    assert "第一章" in user_p


def test_heuristic_flags_forbidden_action():
    """PRD 例:设定禁止飞行,正文写飞行 → 冲突。"""
    bible = SimpleNamespace(
        raw_text="凡人无法踏空。筑基期无法飞行。",
        rules=[{"description": "筑基期无法飞行"}],
        power_system={"rules": ["金丹以下不能御剑"]},
        geography={},
        factions=[],
        timeline=[],
        culture={},
    )
    rules = extract_rule_lines(bible)
    issues = heuristic_scan("筑基期修士飞行千里,御剑而去。", rules)
    assert issues
    texts = " ".join(i.rule_violated + i.text for i in issues)
    assert "飞行" in texts or "御剑" in texts
    assert all(i.source == "heuristic" for i in issues)


def test_heuristic_no_false_positive_when_text_obeys():
    bible = SimpleNamespace(
        raw_text="筑基期无法飞行",
        rules=[],
        power_system={},
        geography={},
        factions=[],
        timeline=[],
        culture={},
    )
    rules = extract_rule_lines(bible)
    issues = heuristic_scan("金丹期修士御剑而行。", rules)
    assert issues == []


def test_parse_llm_issues_skips_invalid():
    issues, summary = parse_llm_issues(
        {
            "summary": "1 处冲突",
            "issues": [
                {
                    "type": "power_system_violation",
                    "severity": "error",
                    "text": "飞行千里",
                    "rule_violated": "筑基期无法飞行",
                    "suggestion": "改为金丹期",
                    "dimension": "power_system",
                },
                {"type": "other"},
                "not-a-dict",
            ],
        }
    )
    assert summary == "1 处冲突"
    assert len(issues) == 1
    assert issues[0].suggestion.startswith("改为")


def test_merge_issues_dedupes():
    from app.schemas.world import ConsistencyIssue

    a = ConsistencyIssue(
        type="rule_violation",
        severity="error",
        text="飞行",
        rule_violated="无法飞行",
        suggestion="改",
        source="heuristic",
    )
    b = ConsistencyIssue(
        type="rule_violation",
        severity="warning",
        text="飞行",
        rule_violated="无法飞行",
        suggestion="LLM 建议",
        source="llm",
    )
    merged = merge_issues([a], [b])
    assert len(merged) == 1
    assert merged[0].source == "heuristic"


def test_is_world_empty():
    empty = SimpleNamespace(
        raw_text="  ",
        geography={},
        factions=[],
        power_system={},
        timeline=[],
        rules=[],
        culture={},
    )
    assert is_world_empty(empty) is True
    empty.raw_text = "有内容"
    assert is_world_empty(empty) is False


@pytest.mark.asyncio
async def test_check_consistency_api_heuristic(client, db_session):
    """无 LLM 有效 JSON 时,启发式仍能检出冲突。"""
    work = Work(
        id=uuid4(),
        title="测试作品",
        genre=Genre.FANTASY,
        logline="",
        target_word_count=10000,
        style_keywords=[],
        target_audience=[],
        status=WorkStatus.DRAFT,
        word_count=0,
        settings={},
    )
    db_session.add(work)
    await db_session.flush()
    bible = WorldBible(
        id=uuid4(),
        work_id=work.id,
        geography={},
        factions=[],
        power_system={"rules": ["筑基期无法飞行"]},
        timeline=[],
        rules=[{"description": "凡人无法踏空"}],
        culture={},
        raw_text="筑基期无法飞行。",
        is_indexed=False,
    )
    db_session.add(bible)
    await db_session.commit()

    with patch(
        "app.agents.world_agent.WorldAgent.check_consistency",
        new=AsyncMock(return_value=([], "", "mock", "")),
    ):
        r = await client.post(
            f"/api/v1/works/{work.id}/world/check-consistency",
            json={"text": "筑基期修士飞行千里"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["world_empty"] is False
    assert body["issue_count"] >= 1
    assert body["passed"] is False
    assert any("飞行" in i["text"] or "飞行" in i["rule_violated"] for i in body["issues"])


@pytest.mark.asyncio
async def test_check_consistency_empty_world(client, db_session):
    work = Work(
        id=uuid4(),
        title="空世界",
        genre=Genre.OTHER,
        logline="",
        target_word_count=1000,
        style_keywords=[],
        target_audience=[],
        status=WorkStatus.DRAFT,
        word_count=0,
        settings={},
    )
    db_session.add(work)
    await db_session.commit()

    r = await client.post(
        f"/api/v1/works/{work.id}/world/check-consistency",
        json={"text": "随便写点"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["world_empty"] is True
    assert body["issue_count"] == 0
    assert body["passed"] is True


@pytest.mark.asyncio
async def test_check_consistency_chapter_id(client, db_session):
    work = Work(
        id=uuid4(),
        title="章节校验",
        genre=Genre.FANTASY,
        logline="",
        target_word_count=1000,
        style_keywords=[],
        target_audience=[],
        status=WorkStatus.DRAFT,
        word_count=0,
        settings={},
    )
    db_session.add(work)
    await db_session.flush()
    db_session.add(
        WorldBible(
            id=uuid4(),
            work_id=work.id,
            geography={},
            factions=[],
            power_system={},
            timeline=[],
            rules=["筑基期无法飞行"],
            culture={},
            raw_text="筑基期无法飞行",
            is_indexed=False,
        )
    )
    ch = Chapter(
        id=uuid4(),
        work_id=work.id,
        title="第一章",
        content={},
        plain_content="筑基期修士飞行千里",
        summary="",
        key_events=[],
        word_count=10,
        status="draft",
        version=1,
    )
    db_session.add(ch)
    await db_session.commit()

    with patch(
        "app.agents.world_agent.WorldAgent.check_consistency",
        new=AsyncMock(return_value=([], "", "mock", "")),
    ):
        r = await client.post(
            f"/api/v1/works/{work.id}/world/check-consistency",
            json={"chapter_id": str(ch.id)},
        )
    assert r.status_code == 200, r.text
    assert r.json()["issue_count"] >= 1
    assert r.json()["checked_chars"] > 0

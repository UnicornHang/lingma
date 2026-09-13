"""World Agent Prompt 模板 & 真实 LLM 校验测试

覆盖:
- 6 维度关键词在 system prompt 中存在
- 禁 thinking aloud / 禁 markdown fence
- user prompt 注入 work 元信息与已有 world
- extra_hint / focus_dimension 行为
- agent.suggest() 在 mock 模式下不抛异常
- agent.suggest() 对非法 JSON 容错
- agent.suggest() 对合法 JSON 强 schema 校验通过
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from app.agents.world_agent import WorldAgent
from app.prompts.world_prompts import (
    build_world_system_prompt,
    build_world_user_prompt,
)
from app.schemas.world import WorldBibleSuggestion


# ============== Prompt 模板测试 ==============


def test_world_system_prompt_contains_six_dimensions():
    sys_p = build_world_system_prompt()
    for dim in ("geography", "factions", "power_system", "timeline", "rules", "culture"):
        assert dim in sys_p, f"system prompt 缺少维度关键词: {dim}"


def test_world_system_prompt_forbids_thinking_aloud():
    sys_p = build_world_system_prompt()
    assert "禁止 thinking aloud" in sys_p


def test_world_system_prompt_forbids_markdown_fence():
    sys_p = build_world_system_prompt()
    assert "markdown fence" in sys_p


def test_world_user_prompt_includes_work_meta():
    work = SimpleNamespace(
        title="仙逆",
        genre="xianxia",
        logline="少年修仙逆天改命",
        style_keywords=["热血", "升级流"],
        target_audience=["男频"],
        notes="",
    )
    user_p = build_world_user_prompt(
        work=work, existing_world=None, focus_dimension="all"
    )
    assert "仙逆" in user_p
    assert "xianxia" in user_p
    assert "少年修仙逆天改命" in user_p
    assert "热血" in user_p
    assert "升级流" in user_p


def test_world_user_prompt_includes_existing_world():
    work = SimpleNamespace(
        title="测试", genre="fantasy", logline="简介",
        style_keywords=[], target_audience=[], notes="",
    )
    existing = SimpleNamespace(
        geography={"regions": ["东洲"]},
        factions={"factions": ["青云宗"]},
        power_system={"tiers": [{"tier_name": "炼气"}]},
        timeline={"events": [{"event_name": "开天辟地"}]},
        rules={"entries": [{"description": "凡人不可修仙"}]},
        culture={"languages": ["古汉语"]},
        raw_text="",
    )
    user_p = build_world_user_prompt(
        work=work, existing_world=existing, focus_dimension="all"
    )
    assert "已有世界书" in user_p
    assert "青云宗" in user_p
    assert "东洲" in user_p


def test_world_user_prompt_extra_hint_appended():
    work = SimpleNamespace(
        title="测试", genre="fantasy", logline="",
        style_keywords=[], target_audience=[], notes="",
    )
    user_p = build_world_user_prompt(
        work=work, existing_world=None, focus_dimension="all",
        extra_hint="重点突出修仙门派之间的矛盾",
    )
    assert "用户附加要求" in user_p
    assert "重点突出修仙门派之间的矛盾" in user_p


def test_world_user_prompt_focus_geography_marks_only_geography():
    work = SimpleNamespace(
        title="测试", genre="xianxia", logline="",
        style_keywords=[], target_audience=[], notes="",
    )
    user_p = build_world_user_prompt(
        work=work, existing_world=None, focus_dimension="geography"
    )
    assert "仅 geography 维度" in user_p
    assert "其他维度留空字典" in user_p


# ============== Agent 真实方法测试(使用 mock LLMService) ==============


def _stub_work() -> SimpleNamespace:
    return SimpleNamespace(
        title="测试作品",
        genre="fantasy",
        logline="一句话",
        style_keywords=["玄幻"],
        target_audience=["男频"],
        notes="",
        id=uuid4(),
    )


def _mock_db_with_work(work: SimpleNamespace, existing_world=None, configs=None):
    """构造 mock db。
    第 1 次 db.execute → scalar_one_or_none = work (用于 _load_work)
    第 2 次 db.execute → scalar_one_or_none = existing_world (用于 _load_existing_world)
    第 3 次 db.execute → scalars().all() = configs (用于 resolve_provider_config)
    """
    call_log = []

    def make_exec_result():
        idx = len(call_log)
        call_log.append(idx)
        m = AsyncMock()
        if idx == 0:
            m.scalar_one_or_none = lambda: work
        elif idx == 1:
            m.scalar_one_or_none = lambda: existing_world
        else:
            # resolve_provider_config 路径: result.scalars().all()
            scalars_mock = AsyncMock()
            scalars_mock.all = lambda: (configs or [])
            m.scalars = lambda: scalars_mock
        return m

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=lambda *a, **kw: make_exec_result())
    return db


def _patch_llm_service(content: str | None):
    """patch LLMService.chat 返回指定内容。None 表示 mock 路径。"""
    return patch(
        "app.agents.world_agent.get_llm_service",
        return_value=_MockLLMService(content),
    )


class _MockLLMService:
    def __init__(self, content):
        self._content = content

    async def chat(self, req, cfg):
        if self._content is None:
            # 模拟 mock provider:不返回 JSON
            return SimpleNamespace(content="这是一段非 JSON 的文本回复。", model="mock")
        return SimpleNamespace(content=self._content, model="mock")


@pytest.mark.asyncio
async def test_world_agent_suggest_handles_missing_work():
    db = AsyncMock()
    exec_result = AsyncMock()
    exec_result.scalar_one_or_none = lambda: None
    db.execute = AsyncMock(return_value=exec_result)

    agent = WorldAgent()
    suggestion, model_used, raw = await agent.suggest(db, work_id=uuid4())
    assert isinstance(suggestion, WorldBibleSuggestion)
    assert suggestion.geography == {}
    assert model_used == "mock"
    assert raw == ""


@pytest.mark.asyncio
async def test_world_agent_suggest_returns_empty_when_no_json():
    db = _mock_db_with_work(_stub_work())
    with _patch_llm_service(None):
        agent = WorldAgent()
        suggestion, model_used, raw = await agent.suggest(db, work_id=uuid4())
    assert isinstance(suggestion, WorldBibleSuggestion)
    # LLM 没返回 JSON → 全空
    assert suggestion.geography == {}
    assert suggestion.factions == {}


@pytest.mark.asyncio
async def test_world_agent_suggest_rejects_invalid_json():
    db = _mock_db_with_work(_stub_work())
    with _patch_llm_service("这不是一个 JSON {{{"):
        agent = WorldAgent()
        suggestion, model_used, raw = await agent.suggest(db, work_id=uuid4())
    assert isinstance(suggestion, WorldBibleSuggestion)
    assert all(
        getattr(suggestion, dim) == {}
        for dim in ("geography", "factions", "power_system", "timeline", "rules", "culture")
    )


@pytest.mark.asyncio
async def test_world_agent_suggest_validates_llm_json_with_six_dimensions():
    valid_json = """{
        "suggestion": {
            "geography": {"regions": [{"name": "东洲", "description": "灵气浓郁之地"}]},
            "factions": {"factions": [{"name": "青云宗", "type": "修仙门派"}]},
            "power_system": {"name": "九转玄功", "tiers": [{"tier_name": "炼气", "tier_level": 1}]},
            "timeline": {"events": [{"event_name": "开天辟地"}]},
            "rules": {"entries": [{"description": "凡人不可修仙"}]},
            "culture": {"languages": ["古汉语"]}
        }
    }"""
    db = _mock_db_with_work(_stub_work())
    with _patch_llm_service(valid_json):
        agent = WorldAgent()
        suggestion, model_used, raw = await agent.suggest(db, work_id=uuid4())
    assert isinstance(suggestion, WorldBibleSuggestion)
    assert "regions" in suggestion.geography
    assert "factions" in suggestion.factions
    assert "tiers" in suggestion.power_system
    assert "events" in suggestion.timeline
    assert "entries" in suggestion.rules
    assert "languages" in suggestion.culture


@pytest.mark.asyncio
async def test_world_agent_suggest_handles_flat_dict_no_suggestion_key():
    """LLM 直接返回顶层 dict(没有 suggestion 键)也应能解析。"""
    flat_json = """{
        "geography": {"regions": ["东洲"]},
        "factions": {"factions": ["青云宗"]}
    }"""
    db = _mock_db_with_work(_stub_work())
    with _patch_llm_service(flat_json):
        agent = WorldAgent()
        suggestion, model_used, raw = await agent.suggest(db, work_id=uuid4())
    assert suggestion.geography == {"regions": ["东洲"]}
    assert suggestion.factions == {"factions": ["青云宗"]}


@pytest.mark.asyncio
async def test_world_agent_suggest_handles_markdown_fence():
    """LLM 输出包了 ```json fence 也应被容错抽取。"""
    fenced = """好的,以下是 JSON:
```json
{"suggestion": {"geography": {"regions": ["东洲"]}}}
```
"""
    db = _mock_db_with_work(_stub_work())
    with _patch_llm_service(fenced):
        agent = WorldAgent()
        suggestion, _, _ = await agent.suggest(db, work_id=uuid4())
    assert "regions" in suggestion.geography


@pytest.mark.asyncio
async def test_world_agent_suggest_keeps_partial_dim_when_one_invalid():
    """LLM 返回部分维度合法、部分维度类型错误时,合法维度应保留。"""
    partial = """{
        "geography": {"regions": ["东洲"]},
        "factions": "not a dict",
        "power_system": {"tiers": []}
    }"""
    db = _mock_db_with_work(_stub_work())
    with _patch_llm_service(partial):
        agent = WorldAgent()
        suggestion, _, _ = await agent.suggest(db, work_id=uuid4())
    # 因为顶层 extra="ignore",Pydantic 会尝试强转;实际行为可能是 factions="not a dict" 被丢弃
    # 至少应保留 geography/power_system
    assert "regions" in suggestion.geography
    assert "tiers" in suggestion.power_system
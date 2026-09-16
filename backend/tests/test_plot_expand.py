"""PlotAgent 扩写本章细纲。"""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.plot_agent import PlotAgent, parse_expand_payload
from app.models.outline import OutlineNodeType
from app.prompts.plot_prompts import (
    build_plot_expand_system_prompt,
    build_plot_expand_user_prompt,
)


def test_expand_system_prompt_forbids_body_and_fence():
    sys_p = build_plot_expand_system_prompt()
    assert "禁止写章节正文" in sys_p
    assert "must_happen" in sys_p
    assert "markdown fence" in sys_p


def test_expand_user_prompt_includes_current_constraints():
    work = SimpleNamespace(
        title="测试书",
        genre="fantasy",
        logline="少年出山",
        notes="",
    )
    user = build_plot_expand_user_prompt(
        work=work,
        node_title="第1章",
        node_type="chapter",
        summary="主角出门",
        beats=["上路"],
        characters_involved=["林墨"],
        target_word_count=3000,
        constraints={"must_happen": ["遇见旧人"], "must_not_happen": [], "end_hook_debt": "夜雨"},
        parent_title="第一卷",
        knowledge_brief="【知情范围】林墨未知：玉佩是诅咒",
        extra_hint="加强冲突",
    )
    assert "遇见旧人" in user
    assert "知情范围" in user
    assert "加强冲突" in user


def test_parse_expand_payload_accepts_string_beats():
    raw = """
    {
      "title": "第1章 风起",
      "summary": "主角在山道遭遇袭击，被迫亮出玉佩。",
      "beats": ["遇袭", "亮玉佩", "脱身"],
      "characters_involved": ["林墨"],
      "target_word_count": 3200,
      "write_constraints": {
        "must_happen": ["玉佩显灵"],
        "must_not_happen": ["暴露真实身份"],
        "time_anchor": "入夜前",
        "stop_point": "逃入客栈",
        "end_hook_debt": "客栈掌柜眼熟玉佩",
        "word_count_min": null,
        "word_count_max": null
      }
    }
    """
    got = parse_expand_payload(raw)
    assert got is not None
    assert got.title.startswith("第1章")
    assert "玉佩显灵" in got.write_constraints.must_happen
    assert got.beats == ["遇袭", "亮玉佩", "脱身"]


def test_parse_expand_payload_coerces_object_beats():
    raw = '{"title":"章","summary":"","beats":[{"title":"开场"},{"summary":"冲突"}],"characters_involved":[],"target_word_count":3000,"write_constraints":{"must_happen":["对决"],"must_not_happen":[],"time_anchor":"","stop_point":"","end_hook_debt":""}}'
    got = parse_expand_payload(raw)
    assert got is not None
    assert got.beats == ["开场", "冲突"]


def test_parse_expand_payload_accepts_think_wrapped_json():
    raw = (
        "<think>先规划节拍再输出</think>\n"
        '{"title":"第1章 青山枪童","summary":"沈砚苦练枪法。",'
        '"beats":["练枪","立志"],"characters_involved":["沈砚"],'
        '"target_word_count":3000,'
        '"write_constraints":{"must_happen":["立志考核"],"must_not_happen":[],'
        '"time_anchor":"夜","stop_point":"加练","end_hook_debt":"考核将至",'
        '"word_count_min":null,"word_count_max":null}}'
    )
    got = parse_expand_payload(raw)
    assert got is not None
    assert got.title == "第1章 青山枪童"
    assert "立志考核" in got.write_constraints.must_happen


def test_parse_expand_payload_coerces_loose_constraints():
    raw = (
        '{"title":"第2章 校场夺魁","summary":"修士贬为凡人把戏。",'
        '"beats":[{"title":"夺魁"},{"summary":"被辱"}],'
        '"characters_involved":"沈砚、青衣修士",'
        '"target_word_count":0,'
        '"write_constraints":{"must_happen":"强压怒火；握枪立誓",'
        '"must_not_happen":[],"time_anchor":"","stop_point":"","end_hook_debt":"",'
        '"word_count_min":0,"word_count_max":""}}'
    )
    got = parse_expand_payload(raw)
    assert got is not None
    assert got.target_word_count == 3000
    assert got.beats == ["夺魁", "被辱"]
    assert "沈砚" in got.characters_involved
    assert "强压怒火" in got.write_constraints.must_happen
    assert got.write_constraints.word_count_min is None


def test_expand_system_prompt_forbids_think_and_inner_quotes():
    sys_p = build_plot_expand_system_prompt()
    assert "<think>" in sys_p
    assert "禁止英文双引号" in sys_p
    assert sys_p.startswith("你是网文主编")


@pytest.mark.asyncio
async def test_expand_rejects_volume_node():
    agent = PlotAgent()
    node = SimpleNamespace(
        id=uuid4(),
        work_id=uuid4(),
        type=OutlineNodeType.VOLUME,
        parent_id=None,
        title="第一卷",
        summary="",
        beats=[],
        characters_involved=[],
        target_word_count=3000,
        write_constraints={},
    )
    result, model = await agent.expand_chapter_outline(SimpleNamespace(), node=node)
    assert result is None
    assert model == "mock"

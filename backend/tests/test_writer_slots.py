"""提交 B — WriterAgent slot 装配 + Reference Gate + 文风裁决 测试

覆盖:
- 文风裁决:命中 / 未知 / 空
- 世界条目解析:dict/list 形态、命中 / miss / 部分命中
- slot 装配顺序、截断、metadata
- 章节角色解析:开篇/高潮/默认
- Reference Gate 路由:opening 触发世界书全文,reveal 触发 world_refs
- build_user_prompt 兼容性:签名不变、所有 slot 标题都在输出里
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.prompts.writer_prompts import build_user_prompt
from app.prompts.writer_slots import (
    PromptAssembly,
    PromptSlot,
    assemble_writer_slots,
    resolve_world_refs,
)
from app.prompts.writer_style_profiles import (
    STYLE_KEYWORD_PROFILES,
    resolve_style,
)
from app.services.chapter_role_resolver import (
    ChapterRole,
    apply_reference_gate,
    references_for_role,
    resolve_chapter_role,
)


# ==================== 测试夹具 ====================


def _stub_work(
    title: str = "测试作品",
    genre: str = "fantasy",
    logline: str = "一句话简介",
    style_keywords: list[str] | None = None,
    target_audience: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        title=title,
        genre=genre,
        logline=logline,
        style_keywords=style_keywords if style_keywords is not None else ["热血"],
        target_audience=target_audience if target_audience is not None else ["男频"],
    )


def _stub_chapter(
    title: str = "第1章 穿越",
    word_count: int = 3000,
    summary: str = "主角穿越到异世界",
) -> SimpleNamespace:
    return SimpleNamespace(
        title=title,
        word_count=word_count,
        summary=summary,
    )


def _stub_outline(
    title: str = "第1章 穿越",
    summary: str = "主角穿越",
    world_refs: list[str] | None = None,
    characters_involved: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        title=title,
        type="chapter",
        summary=summary,
        beats=["冲突展开", "高潮转折"],
        world_refs=world_refs if world_refs is not None else [],
        characters_involved=characters_involved if characters_involved is not None else [],
    )


def _stub_world(
    raw_text: str = "",
    *,
    factions: dict | list | None = None,
    geography: dict | list | None = None,
    power_system: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        geography=geography or {},
        factions=factions or [],
        power_system=power_system or {},
        timeline=[],
        rules=[],
        culture={},
        raw_text=raw_text,
        is_indexed=False,
    )


# ==================== 文风裁决 ====================


def test_resolve_style_known_keyword():
    """已知关键词应命中 profile"""
    out = resolve_style(["热血"])
    assert "节奏紧凑" in out
    assert "热血" in out


def test_resolve_style_unknown_keyword_falls_through():
    """未知关键词应降级标注,不能抛"""
    out = resolve_style(["不存在的词"])
    assert "无内置模板" in out
    assert "不存在的词" in out


def test_resolve_style_empty_list_returns_default_tone():
    """空列表走默认基调 + AI 痕迹禁令"""
    out = resolve_style([])
    assert "AI 模板痕迹" in out or "AI痕迹" in out or "模板痕迹" in out


def test_resolve_style_none_returns_default_tone():
    out = resolve_style(None)
    assert "AI 模板痕迹" in out or "AI痕迹" in out or "模板痕迹" in out


def test_resolve_style_mixed_hit_and_miss():
    """已知 + 未知混合:hit 在前,miss 标注在中间,默认基调在末尾"""
    out = resolve_style(["热血", "黑光", "幽默"])
    assert "热血" in out
    assert "幽默" in out
    assert "黑光" in out  # 在 miss 列表中


# ==================== 世界条目解析 ====================


def test_resolve_world_refs_hit_in_factions_dict():
    """名字在 factions dict 中命中"""
    world = _stub_world(factions={"青云宗": {"简介": "正道第一大派,以剑道闻名"}})
    refs = resolve_world_refs(world, ["青云宗"])
    assert len(refs) == 1
    assert refs[0].name == "青云宗"
    assert refs[0].category == "势力"
    assert "正道第一大派" in refs[0].content


def test_resolve_world_refs_hit_in_factions_list_of_dict():
    """factions 是 list[dict] 时也能解析"""
    world = _stub_world(factions=[
        {"name": "青云宗", "简介": "正道第一大派"},
        {"name": "幽冥殿", "简介": "魔道势力"},
    ])
    refs = resolve_world_refs(world, ["青云宗"])
    assert len(refs) == 1
    assert refs[0].name == "青云宗"


def test_resolve_world_refs_miss_returns_empty():
    world = _stub_world(factions={"青云宗": {"简介": "..."}})
    refs = resolve_world_refs(world, ["不存在的势力"])
    assert refs == []


def test_resolve_world_refs_partial_hit():
    """部分命中:命中的返回,未命中的丢弃"""
    world = _stub_world(factions={"青云宗": {"简介": "正道第一大派"}})
    refs = resolve_world_refs(world, ["青云宗", "不存在的势力"])
    assert len(refs) == 1
    assert refs[0].name == "青云宗"


def test_resolve_world_refs_empty_names():
    world = _stub_world(factions={"青云宗": {"简介": "..."}})
    assert resolve_world_refs(world, []) == []
    assert resolve_world_refs(world, None) == []


def test_resolve_world_refs_none_world():
    assert resolve_world_refs(None, ["青云宗"]) == []


def test_resolve_world_refs_hit_in_power_system():
    """power_system 字段(dict)的命中"""
    world = _stub_world(power_system={
        "灵气": {"描述": "天地间流动的能量,可被修炼者吸纳"},
    })
    refs = resolve_world_refs(world, ["灵气"])
    assert len(refs) == 1
    assert refs[0].category == "力量体系"
    assert "能量" in refs[0].content


# ==================== Slot 装配顺序 ====================


def test_assemble_slots_order_is_stable():
    """核心 slot 顺序应稳定(防止回归)"""
    asm = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=_stub_outline(),
        world=None,
        characters=[SimpleNamespace(name="林轩", role="主角", raw_text="少年天才")],
        previous_summary="上一章摘要",
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
    )
    titles = asm.slot_titles()
    assert titles[0] == "【作品总览】"
    assert titles[1] == "【文风裁决】"
    assert "【本章大纲】" in titles
    assert "【出场角色】" in titles
    assert "【上一章摘要】" in titles
    assert titles[-1] == "【本章任务】"


def test_assemble_continuity_slots_before_prose_context():
    """约束锁、角色状态、知情范围必须出现在任务 slot 之前。"""
    from app.schemas.tracking import (
        CharacterRuntimeState,
        TimelineEvent,
        WriteConstraints,
        WriterContextCard,
    )

    card = WriterContextCard(
        constraints=WriteConstraints(
            must_happen=["当面对质"],
            must_not_happen=["说出凶手身份"],
        ),
        character_states=[
            CharacterRuntimeState(
                character_id="1",
                name="林轩",
                unknown_facts=["信是哥哥寄的"],
            )
        ],
        author_timeline=[TimelineEvent(text="凶手是哥哥")],
        reader_timeline=[TimelineEvent(text="主角收到匿名信")],
    )
    asm = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=_stub_outline(),
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
        continuity=card,
    )
    titles = asm.slot_titles()
    assert titles.index("【本章约束锁】") < titles.index("【本章大纲】")
    assert "【角色当前状态】" in titles
    assert "【知情范围】" in titles
    assert "不得把作者真相写成角色已知" in asm.user_text
    assert "当面对质" in asm.user_text
    assert "信是哥哥寄的" in asm.user_text


def test_slot_truncation_keeps_truncated_marker_in_metadata():
    """超长 slot 应被截断并在 metadata.truncated 记录"""
    # 12 字 × 200 = 2400 字 > 1200,确保触发截断
    long_text = "这段文字很长很长很长很长很长很长很长很长很长很长" * 100
    assert len(long_text) > 1200  # 防御
    from app.services.chapter_role_resolver import (
        ChapterRole, references_for_role,
    )
    hints = references_for_role(ChapterRole.OPENING, None)
    asm = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=_stub_world(raw_text=long_text),
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
        reference_hints=hints,
    )
    assert "【世界书(节选)】" in asm.truncated_slots


def test_assemble_slots_no_outline_no_outline_slot():
    """outline=None 时不出现【本章大纲】slot"""
    asm = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
    )
    titles = asm.slot_titles()
    assert "【本章大纲】" not in titles


def test_assemble_slots_continue_mode_has_existing_tail_slot():
    """续写模式:existing_tail slot 出现"""
    asm = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail="他猛然抬头。",
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
    )
    titles = asm.slot_titles()
    has_tail = any("本章已有正文" in t for t in titles)
    assert has_tail
    assert asm.metadata["has_existing_tail"] is True


def test_assemble_slots_metadata_records_world_refs_resolved():
    """metadata.world_refs_resolved 记录解析到的名字"""
    world = _stub_world(factions={"青云宗": {"简介": "正道第一大派"}})
    asm = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=_stub_outline(world_refs=["青云宗"]),
        world=world,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=["青云宗"],
    )
    assert "青云宗" in asm.metadata["world_refs_resolved"]


def test_assemble_slots_world_refs_slot_appears_when_resolved():
    """解析到 world_refs 时【世界条目(精准)】slot 出现"""
    world = _stub_world(factions={"青云宗": {"简介": "正道第一大派"}})
    asm = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=_stub_outline(world_refs=["青云宗"]),
        world=world,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=["青云宗"],
    )
    titles = asm.slot_titles()
    has_refs_slot = any("世界条目" in t for t in titles)
    assert has_refs_slot


def test_assemble_slots_no_world_full_slot_when_reference_gate_disabled():
    """默认 transition 角色(Reference Gate 不开)时,无世界书全文 slot"""
    asm = assemble_writer_slots(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=_stub_world(raw_text="一段世界书内容"),
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
    )
    titles = asm.slot_titles()
    # 没 reference_hints 时,默认逻辑不开 world_full
    has_world_full = any("世界书" in t for t in titles)
    assert not has_world_full


# ==================== PromptSlot 单独测试 ====================


def test_prompt_slot_render_empty_body_returns_empty():
    s = PromptSlot(title="【空】", body="   ")
    assert s.render() == ""


def test_prompt_slot_render_includes_title_and_body():
    s = PromptSlot(title="【测试】", body="内容", max_chars=100)
    out = s.render()
    assert "【测试】" in out
    assert "内容" in out


def test_prompt_slot_truncates_long_body():
    body = "x" * 5000
    s = PromptSlot(title="【测试】", body=body, max_chars=100)
    out = s.render()
    assert "已截断" in out
    assert len(out) < 200  # 实际渲染远小于原 body


# ==================== build_user_prompt 兼容性 ====================


def test_build_user_prompt_unchanged_signature_compat():
    """原签名调用方式仍可用(所有参数都是 keyword-only,旧测试可直接通过)"""
    prompt = build_user_prompt(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=None,
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=None,
        world_refs=None,
    )
    assert "测试作品" in prompt
    assert "现在请开始撰写本章正文" in prompt


def test_build_user_prompt_all_slot_titles_present():
    """完整输入下,所有 slot 标题应出现在输出里"""
    prompt = build_user_prompt(
        work=_stub_work(style_keywords=["热血"]),
        chapter=_stub_chapter(),
        outline=_stub_outline(world_refs=["青云宗"], characters_involved=["林轩"]),
        world=_stub_world(
            raw_text="一段世界书全文",
            factions={"青云宗": {"简介": "正道第一大派"}},
        ),
        characters=[SimpleNamespace(name="林轩", role="主角", raw_text="少年天才")],
        previous_summary="上一章摘要",
        existing_tail="已有正文末尾",
        target_word_count=3000,
        same_volume_outline=[_stub_outline(title="第2章 入门")],
        world_refs=["青云宗"],
    )
    assert "【作品总览】" in prompt
    assert "【文风裁决】" in prompt
    assert "【本章大纲】" in prompt
    assert "【同卷其他章节" in prompt
    assert "【世界条目(精准)】" in prompt
    assert "【出场角色】" in prompt
    assert "【上一章摘要】" in prompt
    assert "【本章已有正文" in prompt
    assert "【本章任务】" in prompt


def test_build_user_prompt_continue_mode_special_phrase():
    """续写模式:专用措辞出现,默认措辞不出现"""
    tail = "他猛然抬头。"
    prompt = build_user_prompt(
        work=_stub_work(),
        chapter=_stub_chapter(),
        existing_tail=tail,
    )
    assert "现在请从上述已有正文的末尾自然续写" in prompt
    assert "现在请开始撰写本章正文" not in prompt


# ==================== 章节角色解析 ====================


def test_chapter_role_resolver_opening_keyword():
    outline = _stub_outline(title="第1章 穿越")
    assert resolve_chapter_role(outline) == ChapterRole.OPENING


def test_chapter_role_resolver_reveal_keyword():
    outline = _stub_outline(title="第5章 真相大白")
    assert resolve_chapter_role(outline) == ChapterRole.REVEAL


def test_chapter_role_resolver_climax_keyword():
    outline = _stub_outline(title="第20章 决战")
    assert resolve_chapter_role(outline) == ChapterRole.CLIMAX


def test_chapter_role_resolver_default_is_transition():
    outline = _stub_outline(title="第8章 修炼日常")
    assert resolve_chapter_role(outline) == ChapterRole.TRANSITION


def test_chapter_role_resolver_no_outline_is_transition():
    assert resolve_chapter_role(None) == ChapterRole.TRANSITION


def test_chapter_role_resolver_no_match_is_transition():
    outline = _stub_outline(title="某章", summary="无关键词的章节")
    assert resolve_chapter_role(outline) == ChapterRole.TRANSITION


# ==================== Reference Gate 路由 ====================


def test_references_for_opening_includes_world_full():
    hints = references_for_role(ChapterRole.OPENING, None)
    assert hints.must_read_world_full is True
    assert hints.must_read_world_refs is False


def test_references_for_reveal_includes_world_refs():
    hints = references_for_role(ChapterRole.REVEAL, None)
    assert hints.must_read_world_full is False
    assert hints.must_read_world_refs is True


def test_references_for_climax_includes_characters_all():
    hints = references_for_role(ChapterRole.CLIMAX, None)
    assert hints.must_read_characters_all is True
    assert hints.must_read_world_refs is True


def test_references_for_transition_default():
    hints = references_for_role(ChapterRole.TRANSITION, None)
    assert hints.must_read_world_full is False
    assert hints.must_read_world_refs is True


def test_apply_reference_gate_opening_keeps_world_full():
    world = _stub_world(raw_text="世界书全文内容")
    eff_world, eff_chars = apply_reference_gate(
        outline=None, world=world, characters=[], hints=references_for_role(ChapterRole.OPENING, None),
    )
    assert eff_world is not None
    assert eff_world.raw_text == "世界书全文内容"


def test_apply_reference_gate_transition_keeps_world_when_has_struct():
    """transition 角色下,只要 world 有结构化字段就保留(供 world_refs 解析)"""
    world = _stub_world(factions={"青云宗": {"简介": "..."}})
    eff_world, _ = apply_reference_gate(
        outline=None, world=world, characters=[], hints=references_for_role(ChapterRole.TRANSITION, None),
    )
    assert eff_world is not None


def test_apply_reference_gate_none_world_stays_none():
    eff_world, _ = apply_reference_gate(
        outline=None, world=None, characters=[], hints=references_for_role(ChapterRole.OPENING, None),
    )
    assert eff_world is None

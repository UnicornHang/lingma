"""Writer Agent Prompt 模板测试

覆盖:
- continue 模式下 existing_tail 块被正确插入
- generate 模式下 existing_tail 块不出现
- target_word_count 参数覆盖 chapter.word_count 默认值
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.prompts.writer_prompts import build_system_prompt, build_user_prompt


def _stub_work() -> SimpleNamespace:
    return SimpleNamespace(
        title="测试作品",
        genre="fantasy",
        logline="一句话简介",
        style_keywords=["热血", "升级流"],
        target_audience=["男频"],
    )


def _stub_chapter(word_count: int = 3000, summary: str = "主角穿越到异世界") -> SimpleNamespace:
    return SimpleNamespace(
        title="第1章 穿越",
        word_count=word_count,
        summary=summary,
    )


def test_build_system_prompt_includes_target_words():
    out = build_system_prompt(target_words=800)
    assert "800" in out
    assert "本章目标" in out


def test_build_user_prompt_generate_mode_no_existing_tail():
    """generate 模式（无 existing_tail）应输出原始提示词"""
    prompt = build_user_prompt(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=None,
        previous_summary=None,
    )
    assert "本章已有正文" not in prompt
    assert "现在请开始撰写本章正文" in prompt
    assert "测试作品" in prompt


def test_build_user_prompt_continue_mode_appends_existing_tail():
    """continue 模式（有 existing_tail）应注入续写块与专用措辞"""
    tail = "……他猛然抬头,只见一把寒光剑直逼咽喉。"
    prompt = build_user_prompt(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=None,
        previous_summary=None,
        existing_tail=tail,
        target_word_count=800,
    )
    # 续写块
    assert "本章已有正文" in prompt
    assert tail in prompt
    assert "不要重复" in prompt
    # 续写专用措辞
    assert "现在请从上述已有正文的末尾自然续写" in prompt
    # 默认措辞不出现
    assert "现在请开始撰写本章正文" not in prompt
    # target_word_count 生效
    assert "800" in prompt


def test_build_user_prompt_target_word_count_overrides_chapter():
    """target_word_count 参数应覆盖 chapter.word_count 的默认值"""
    prompt = build_user_prompt(
        work=_stub_work(),
        chapter=_stub_chapter(word_count=5000),
        outline=None,
        world=None,
        characters=None,
        previous_summary=None,
        target_word_count=800,
    )
    assert "800" in prompt
    assert "5000" not in prompt


@pytest.mark.parametrize("empty_value", [None, ""])
def test_build_user_prompt_falsy_existing_tail_treated_as_no_tail(empty_value):
    """空字符串 / None existing_tail 应被当作 continue=false 处理"""
    prompt = build_user_prompt(
        work=_stub_work(),
        chapter=_stub_chapter(),
        outline=None,
        world=None,
        characters=None,
        previous_summary=None,
        existing_tail=empty_value,
    )
    assert "本章已有正文" not in prompt
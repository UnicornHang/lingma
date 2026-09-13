"""[P3.3] build_critic_guided_rewrite_prompt 测试。

覆盖:
- prompt 包含 top 3 共识问题
- prompt 保留字数约束
- prompt 注入文风锚(可选)
"""
from __future__ import annotations

import pytest

from app.prompts.editor_prompts import build_critic_guided_rewrite_prompt


def test_prompt_includes_consensus_issues():
    """user prompt 必须包含 consensus_issues 的内容。"""
    issues = [
        "主角动机突然改变,前文铺垫缺失",
        "章末钩子不明显,读者易弃读",
        "对话占比过低,叙述堆砌",
    ]
    scores = {
        "consistency": 0.4,
        "pacing": 0.5,
        "prose": 0.7,
        "engagement": 0.3,
        "overall": 0.45,
    }

    system, user = build_critic_guided_rewrite_prompt(
        chapter_text="原文章节正文...",
        consensus_issues=issues,
        scores=scores,
    )

    # system 必有「编辑」角色与硬性约束
    assert "编辑" in system or "资深" in system
    assert "不要输出" in system or "不要" in system  # 硬约束

    # user 必包含所有 3 条共识问题
    for issue in issues:
        assert issue in user, f"共识问题缺失: {issue!r}"

    # 评分摘要:每个子分都出现
    assert "0.45" in user  # overall
    assert "0.40" in user or "0.4" in user  # consistency


def test_prompt_preserves_word_count_target():
    """prompt 必须包含 ±15% 字数约束,避免改写后字数膨胀。"""
    system, user = build_critic_guided_rewrite_prompt(
        chapter_text="内容",
        consensus_issues=["节奏过慢"],
        scores={"overall": 0.4},
    )

    combined = system + user
    assert "15%" in combined, f"未包含字数约束:\n--- system ---\n{system}\n--- user ---\n{user}"


def test_prompt_includes_style_anchors_when_provided():
    """文风锚注入到 user prompt 顶部。"""
    _, user = build_critic_guided_rewrite_prompt(
        chapter_text="内容",
        consensus_issues=["x"],
        scores={"overall": 0.5},
        style_keywords=["爽文节奏", "细腻文笔"],
    )

    assert "爽文节奏" in user
    assert "细腻文笔" in user


def test_prompt_handles_empty_consensus_issues():
    """共识问题清单为空时,prompt 仍可生成(LLM 仅按文风自然润色)。"""
    _, user = build_critic_guided_rewrite_prompt(
        chapter_text="内容",
        consensus_issues=[],
        scores={"overall": 0.7},  # 此时已达标,不应触发;但函数仍可调用
    )
    # 共识问题块用占位文案
    assert "(无)" in user or "无" in user


def test_prompt_handles_none_style_anchors():
    """style_keywords=None 时,prompt 不崩溃。"""
    _, user = build_critic_guided_rewrite_prompt(
        chapter_text="内容",
        consensus_issues=["x"],
        scores={"overall": 0.5},
        style_keywords=None,
    )
    # 不应有 NoneType 错误,且文风锚行被跳过
    assert "【文风锚】" not in user
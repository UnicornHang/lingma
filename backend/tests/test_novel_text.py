"""网文正文后处理：剥泄漏、切自然段。"""
from __future__ import annotations

from app.services.novel_text import (
    is_leaked_rewrite,
    normalize_novel_paragraphs,
    plain_to_tiptap_doc,
    strip_prompt_leaks,
)


def test_strip_prompt_leaks_removes_editor_placeholder():
    """润色 JSON 样例不得残留在正文里。"""
    raw = "碗口粗的窟窿边缘焦黑<改写后片段;若判定无需改写,填原文>那是枪身高速震荡留下的痕迹。"
    out = strip_prompt_leaks(raw)
    assert "改写后片段" not in out
    assert "若判定无需改写" not in out
    assert "焦黑" in out
    assert "枪身" in out


def test_is_leaked_rewrite_detects_placeholder():
    assert is_leaked_rewrite("<改写后片段;若判定无需改写,填原文>")
    assert is_leaked_rewrite("若判定无需改写,填原文")
    assert not is_leaked_rewrite("那一瞬的压力让他肩背绷紧")


def test_normalize_splits_dialogue_and_scene():
    """对话与场景切换必须另起一段。"""
    wall = (
        "沈砚收枪而立。"
        "「砚哥儿，今晚沈家摆宴。」陈小虎追上来。"
        "他点了点头。"
        "—— 沈家后院，练武场。"
        "月光很薄。"
    )
    out = normalize_novel_paragraphs(wall)
    paras = [p for p in out.split("\n\n") if p.strip()]
    assert len(paras) >= 3
    assert any(p.startswith("「") or "砚哥儿" in p for p in paras)
    assert any(p.startswith("——") for p in paras)


def test_plain_to_tiptap_has_multiple_paragraphs():
    """墙式正文入库后必须是多段 TipTap。"""
    wall = "第一句结束。第二句也结束。第三句还在继续写动作。" * 3
    doc = plain_to_tiptap_doc(wall)
    nodes = doc["content"]
    assert len(nodes) >= 2
    assert all(n["type"] == "paragraph" for n in nodes)

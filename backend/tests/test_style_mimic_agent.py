"""仿文 Agent：画像解析与启发式。"""
from types import SimpleNamespace

from app.agents.style_mimic_agent import (
    heuristic_style_from_text,
    parse_style_mimic_payload,
)
from app.prompts.style_mimic_prompts import build_style_mimic_system_prompt
from app.prompts.writer_slots import _format_style_memory_slot, assemble_writer_slots
from app.schemas.style_mimic import StyleMemoryCard, StylePortrait, StyleSnippet

def test_system_prompt_forbids_plot_copy():
    sys_p = build_style_mimic_system_prompt()
    assert "专有名词" in sys_p
    assert "writing_directives" in sys_p
    assert "markdown fence" in sys_p


def test_parse_style_mimic_payload_ok():
    raw = """
    {
      "portrait": {
        "narrative_pov": "第三人称有限",
        "avg_sentence_len": "偏短",
        "dialogue_density": "高",
        "rhetoric_habits": ["短句", "动词驱动"],
        "pacing_tags": ["快切"],
        "emotional_style": "外化动作",
        "lexicon_notes": "口语化"
      },
      "writing_directives": "用短句推进冲突，对话自然，禁止堆砌形容词。",
      "snippets": [{"tag": "对话", "text": "「走。」他没有回头。"}]
    }
    """
    got = parse_style_mimic_payload(raw)
    assert got is not None
    portrait, directives, snippets = got
    assert portrait.avg_sentence_len == "偏短"
    assert "短句" in directives
    assert snippets[0].tag == "对话"


def test_parse_style_mimic_payload_rejects_garbage():
    assert parse_style_mimic_payload("不是 JSON") is None


def test_heuristic_style_from_text_produces_portrait():
    sample = (
        "他推开门。「你来了。」她说。风声很急。他没有回答，只是把刀收回鞘里。"
        "走廊尽头有灯。脚步声越来越近。他停住，听了一会儿，又继续往前走。"
    ) * 8
    portrait, directives, snippets = heuristic_style_from_text(sample)
    assert portrait.dialogue_density in {"高", "中", "低"}
    assert portrait.avg_sentence_len in {"偏短", "中等", "偏长"}
    assert "专有名词" in directives
    assert isinstance(snippets, list)


def test_format_style_memory_slot_empty():
    assert _format_style_memory_slot(None) == ""


def test_assemble_writer_slots_includes_style_memory():
    work = SimpleNamespace(
        title="测",
        genre="fantasy",
        logline="简介",
        style_keywords=["热血"],
        target_audience=["男频"],
    )
    chapter = SimpleNamespace(title="第1章", word_count=0, summary="")
    memory = StyleMemoryCard(
        source_label="参考甲",
        writing_directives="短句推进，对话密。",
        portrait=StylePortrait(
            narrative_pov="第三人称",
            avg_sentence_len="偏短",
            dialogue_density="高",
        ),
        snippets=[StyleSnippet(tag="对话", text="「走。」")],
    )
    asm = assemble_writer_slots(
        work=work,
        chapter=chapter,
        outline=None,
        world=None,
        characters=[],
        previous_summary=None,
        existing_tail=None,
        target_word_count=3000,
        same_volume_outline=[],
        world_refs=None,
        style_memory=memory,
    )
    titles = asm.slot_titles()
    assert "【仿文风格记忆】" in titles
    assert titles.index("【文风裁决】") < titles.index("【仿文风格记忆】")
    assert "参考甲" in asm.user_text
    assert "学句式与节奏" in asm.user_text

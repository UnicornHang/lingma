"""Critic Agent 的 Prompt 模板

SYSTEM：5 Persona 评审纪律（JSON / 4 维度评分 / 不 thinking aloud / 不 markdown fence）。
USER：作品上下文 + 章节元信息 + 待评正文 + persona 列表 + extra_hint。

5 Persona × 4 维度评分模型：
- shuangwen (爽文党): 节奏爽感/主角打脸/升级
- wenqing (文青党): 文笔/意象/留白/隐喻
- kaoju (考据党): 设定自洽/人物言行一致/力量体系无 bug
- mengxin (萌新读者): 500 字入戏/钩子/顺畅度
- zhubian (主编): 结构(钩子/冲突/高潮/留白)/节奏/市场卖点

4 维度：consistency 一致性 / pacing 节奏 / prose 文笔 / engagement 代入感
"""
from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from app.models.work import Work

_EMPTY = "（未指定）"

# ============== Persona 关注点定义 ==============

_PERSONA_INSTRUCTIONS: dict[str, str] = {
    "shuangwen": (
        "爽文党:你只在意节奏爽感、主角打脸/升级/变强的爽点密度。"
        "对 OOC、逻辑硬伤、文笔差次要宽容(只要爽就行)。"
        "判断标准:每 1500 字是否有一个明确的爽点(打脸/复仇/逆袭/突破/装逼打脸)。"
    ),
    "wenqing": (
        "文青党:你只在意文笔、意象、留白、隐喻、诗性表达。"
        "对爽点密度、节奏慢、人物对话偏书面等次要宽容。"
        "判断标准:是否有让人想摘抄的金句?是否有画面感?是否有余韵?"
    ),
    "kaoju": (
        "考据党:你只在意设定自洽、人物言行一致性、力量体系无 bug、世界规则连贯。"
        "对文笔、爽感、节奏次要宽容。"
        "判断标准:本章出现的所有设定/规则/人物性格是否与前文矛盾?是否有物理/逻辑硬伤?"
    ),
    "mengxin": (
        "萌新读者(路人视角):你只看 500 字内能否入戏,后续读起来是否顺畅,是否有钩子。"
        "对深奥设定、文青笔法、复杂剧情次要宽容。"
        "判断标准:网文小白用户能看下去吗?会不会在前 500 字就弃读?"
    ),
    "zhubian": (
        "主编(综合):你从结构(开篇钩子/冲突/高潮/留白)、节奏、市场卖点三方面评判。"
        "判断标准:是否符合网文爆款结构?有没有卖点(标签/爽点/新颖设定)?"
        "市场潜力如何?能否签约/上榜?"
    ),
}


def get_persona_instruction(persona: str) -> str:
    return _PERSONA_INSTRUCTIONS.get(persona, _PERSONA_INSTRUCTIONS["zhubian"])


ALL_PERSONAS = list(_PERSONA_INSTRUCTIONS.keys())


# ============== Prompt 构建 ==============


def build_critic_system_prompt(personas: Iterable[str]) -> str:
    persona_list = list(personas)
    persona_blocks = "\n\n".join(
        f"### {p}\n{get_persona_instruction(p)}" for p in persona_list
    )

    return dedent(
        f"""\
        你是一位资深网文评审系统,需要**同时以 {len(persona_list)} 种 Persona 视角**对一段章节正文进行独立评分。

        【本次评审的 Persona】
        {persona_blocks}

        【输出纪律 - 严格遵守】
        1. **只输出 JSON 对象**,禁止任何 markdown fence(``` / ```json / ```JSON)。
        2. **禁止 thinking aloud**:不要输出 "Let me"、"I should"、"Wait"、"好的" 等过渡句。
        3. JSON 顶层结构:{{"persona_scores": [{{...}}, ...]}},长度严格等于 persona 数。
        4. 每个 persona_score 字段(英文 key,不得增减):
           - persona (str, 必须等于本次输入的 persona 之一)
           - consistency (float, 0.0-1.0, 一致性)
           - pacing (float, 0.0-1.0, 节奏)
           - prose (float, 0.0-1.0, 文笔)
           - engagement (float, 0.0-1.0, 代入感/可读性)
           - comment (str, ≤300 字,一句解释该 persona 的总体判断)
           - top_issues (list[str], 最多 5 条具体问题;可空 list)
        5. 每个 persona 必须**独立评判**,不要受其他 persona 影响。
        6. 分数使用浮点 0.0-1.0(如 0.78 表示 B+ 水平),允许 0.05 精度。
        7. 实在没问题的章节,score 也应给到 0.70+;严苛情况下可低至 0.30。

        【风格适配】
        - 紧贴作品的类型与目标读者。
        - 评论要具体(可引用原文 1-3 字短语),不要空泛。
        - top_issues 要可操作(指出"哪里"和"如何改进"),不要只说"写得不够好"。
        """
    ).strip()


def build_critic_user_prompt(
    *,
    work: "Work",
    chapter_title: str,
    chapter_summary: str,
    content: str,
    personas: Iterable[str],
    extra_hint: str | None = None,
    content_max_chars: int = 6000,
) -> str:
    """构造 Critic 的 user prompt。

    - content: 待评正文(>content_max_chars 时截断,加省略标记)
    - personas: 本次要评审的 persona 列表
    - content_max_chars: 默认 6000 字上限,避免 prompt 过长
    """
    genre = work.genre.value if hasattr(work.genre, "value") else (work.genre or _EMPTY)
    style_keywords = "、".join(work.style_keywords or []) or _EMPTY
    target_audience = "、".join(work.target_audience or []) or _EMPTY

    persona_list = list(personas)
    persona_names = "、".join(persona_list)

    if len(content) > content_max_chars:
        truncated = content[:content_max_chars] + "\n...(后续省略)..."
    else:
        truncated = content

    extra_text = (
        f"\n【用户附加要求】\n{extra_hint.strip()}\n"
        if extra_hint and extra_hint.strip()
        else ""
    )

    return dedent(
        f"""\
        【作品标题】{work.title}
        【类型】{genre}
        【风格关键词】{style_keywords}
        【目标读者】{target_audience}
        【备注】{work.notes or _EMPTY}

        【待评章节】{chapter_title}
        【章节摘要】{chapter_summary or _EMPTY}

        【本次 Persona 列表】{persona_names}
        {extra_text}
        【待评正文(共 {len(content)} 字)】
        {truncated}

        现在请按上述 persona 列表,独立评判每个 persona 的 4 维分数,并给出 comment + top_issues。
        直接输出 JSON。
        """
    ).strip()
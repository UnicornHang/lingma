"""Writer Agent 的 Prompt 模板

SYSTEM 角色由小说风格 + 写作要求构成；
USER 角色由章节上下文(标题 / 大纲 / 世界书 / 角色)构成。

[提交 B] ``build_user_prompt`` 现在委托给 ``writer_slots.assemble_writer_slots``
做确定性 slot 装配;签名与外部行为保持兼容。
"""
from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.character import Character
    from app.models.chapter import Chapter
    from app.models.outline import OutlineNode
    from app.models.work import Work
    from app.models.world import WorldBible

    from app.schemas.rag import RagHit
    from app.schemas.style_mimic import StyleMemoryCard
    from app.schemas.tracking import WriterContextCard
    from app.services.chapter_role_resolver import ReferenceHints


# 用 sentinel 避免在 f-string 内出现单引号
_EMPTY = "（未指定）"
_NONE_DESC = "（无）"


def build_system_prompt(target_words: int) -> str:
    """构造 Writer system prompt;target_words 写入字数约束。"""
    return dedent(
        f"""\
        你是一位资深网络小说作家，擅长中长篇创作。请遵循以下原则：

        1. 语言风格：贴合目标读者（男频/女频/不限），节奏紧凑，画面感强。
        2. 叙事视角：以大纲指定的视角为准，保持一致。
        3. 字数控制：本章目标 {target_words} 字，可上下浮动 20%。
        4. 结构要求：开篇钩子 → 冲突展开 → 高潮/转折 → 结尾留白。
        5. 不要复述上一章；不要加入 OOC 解释；不要输出元数据。
        6. 输出格式：直接输出正文，纯文本，不需要标题或 Markdown 装饰。
        7. 严禁抄袭已有作品。如遇敏感内容请合理化处理。

        【排版】
        11. 必须用空行分段。一段只写 1～3 句，不要把整章糊成一块。
        12. 每句对话单独成段。场景切换单独一行写「——」。
        13. 禁止把提示词、JSON、尖括号占位、XML/HTML 写进正文。

        【句法】
        14. 一句一事：谁做什么，因果要接上。禁止半截比喻、禁止主语偷换。
        15. 禁止「不是A，是B」「那不是X，那是Y」「与其说…不如说」对照句。
        16. 禁止章尾鸡汤（拳头的意义、命运的齿轮、这一夜注定、他终于明白）。
        17. 角色只能根据已知信息行动，不要替角色知道作者真相。

        【重要 - 输出纪律】
        8. **不要 thinking aloud**！严禁在正文中夹杂「Let me / I should / Wait / Maybe / I'll aim / try again」等英文思考片段。
        9. 如确需推理过程，必须包裹在 <think>...</think> 块中(且该块在正文输出前完成)。
        10. 直接开始第一句正文 —— 不要"Listo:"、"好的我开始写"、"Chapter X:" 之类的过渡句。
        """
    ).strip()


# 可编辑模板默认值(占位符版) —— Prompt 设置页与 resolve 共用
WRITER_SYSTEM_TEMPLATE = build_system_prompt(99999).replace("99999", "{{target_words}}")


# 向后兼容旧 import
SYSTEM_PROMPT = build_system_prompt(3000)


def _join_list(items, sep="、", empty=_EMPTY) -> str:
    if not items:
        return empty
    return sep.join(str(x) for x in items)


def build_user_prompt(
    *,
    work: "Work",
    chapter: "Chapter",
    outline: "OutlineNode | None" = None,
    world: "WorldBible | None" = None,
    characters: "list[Character] | None" = None,
    previous_summary: "str | None" = None,
    existing_tail: "str | None" = None,
    target_word_count: "int | None" = None,
    same_volume_outline: "list[OutlineNode] | None" = None,
    world_refs: "list[str] | None" = None,
    reference_hints: "ReferenceHints | None" = None,
    rag_hits: "list[RagHit] | None" = None,
    continuity: "WriterContextCard | None" = None,
    style_memory: "StyleMemoryCard | None" = None,
) -> str:
    """[提交 B] 委托给 ``assemble_writer_slots`` 做确定性 slot 装配。

    签名与原版完全兼容;新增可选参数 ``reference_hints``(由 WriterAgent 传入)
    与 ``rag_hits``(由 WriterAgent 在 RAG 检索后传入;None/空 时跳过 RAG slot)、
    ``style_memory``(仿文风格记忆;未启用则跳过)。
    """
    from app.prompts.writer_slots import assemble_writer_slots

    assembly = assemble_writer_slots(
        work=work,
        chapter=chapter,
        outline=outline,
        world=world,
        characters=characters or [],
        previous_summary=previous_summary,
        existing_tail=existing_tail,
        target_word_count=target_word_count,
        same_volume_outline=same_volume_outline or [],
        world_refs=world_refs,
        reference_hints=reference_hints,
        rag_hits=rag_hits,
        continuity=continuity,
        style_memory=style_memory,
    )
    return assembly.user_text
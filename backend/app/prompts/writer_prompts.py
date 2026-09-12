"""Writer Agent 的 Prompt 模板

SYSTEM 角色由小说风格 + 写作要求构成；
USER 角色由章节上下文（标题 / 大纲 / 世界书 / 角色）构成。
"""
from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.character import Character
    from app.models.chapter import Chapter
    from app.models.outline import OutlineNode
    from app.models.work import Work
    from app.models.world import WorldBible

# 用 sentinel 避免在 f-string 内出现单引号
_EMPTY = "（未指定）"
_NONE_DESC = "（无）"


def build_system_prompt(target_words: int) -> str:
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

        【重要 - 输出纪律】
        8. **不要 thinking aloud**！严禁在正文中夹杂「Let me / I should / Wait / Maybe / I'll aim / try again」等英文思考片段。
        9. 如确需推理过程，必须包裹在 <think>...</think> 块中(且该块在正文输出前完成)。
        10. 直接开始第一句正文 —— 不要"Listo:"、"好的我开始写"、"Chapter X:" 之类的过渡句。
        """
    ).strip()


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
) -> str:
    parts: list[str] = []

    # 作品总览
    genre = work.genre.value if hasattr(work.genre, "value") else (work.genre or _EMPTY)
    parts.append(
        f"【作品】{work.title}\n"
        f"【类型】{genre}\n"
        f"【一句话简介】{work.logline or _EMPTY}\n"
        f"【风格关键词】{_join_list(work.style_keywords or [])}\n"
        f"【目标读者】{_join_list(work.target_audience or [])}\n"
    )

    # 大纲定位
    if outline:
        beats = outline.beats or []
        beats_text = "\n".join(f"  - {b}" for b in beats) if beats else f"  {_NONE_DESC}"
        parts.append(
            f"【本章大纲】\n"
            f"标题：{outline.title}\n"
            f"类型：{outline.type}\n"
            f"简介：{outline.summary or _NONE_DESC}\n"
            f"节拍：\n{beats_text}\n"
        )

    # 世界书
    if world and world.raw_text:
        parts.append(f"【世界书（节选）】\n{world.raw_text[:1500]}\n")

    # 角色
    if characters:
        char_lines = []
        for c in characters[:8]:
            desc = (c.raw_text or "").replace("\n", " ")[:120]
            char_lines.append(f"  - {c.name}（{c.role}）：{desc or _NONE_DESC}")
        parts.append("【出场角色】\n" + "\n".join(char_lines) + "\n")

    # 上一章摘要
    if previous_summary:
        parts.append(f"【上一章摘要】\n{previous_summary}\n")

    # 已有正文尾段（续写模式）
    if existing_tail:
        parts.append(
            f"【本章已有正文（请从末尾自然续写，不要重复、不要总结前文）】\n"
            f"{existing_tail}\n"
        )

    # 任务指令
    target_words = target_word_count or chapter.word_count or 3000
    tail_hint = (
        "现在请从上述已有正文的末尾自然续写，不要重复、不要总结前文："
        if existing_tail
        else "现在请开始撰写本章正文："
    )
    parts.append(
        f"\n【本章任务】\n"
        f"标题：{chapter.title}\n"
        f"目标字数：约 {target_words} 字\n"
        f"摘要要求：{chapter.summary or _NONE_DESC}\n\n"
        f"{tail_hint}"
    )

    return "\n".join(parts)
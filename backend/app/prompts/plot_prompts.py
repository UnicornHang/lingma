"""Plot Agent 的 Prompt 模板

SYSTEM：剧情规划纪律（JSON / 卷-章-节拍三层结构 / 不 thinking aloud）。
USER：作品上下文 + 卷数/章节数预期。
"""
from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.work import Work

_EMPTY = "（未指定）"


def build_plot_system_prompt() -> str:
    return dedent(
        f"""\
        你是资深网文主编，负责为长篇小说设计卷→章→节拍三层大纲。

        【输出纪律 - 严格遵守】
        1. **只输出 JSON 对象**，禁止任何 markdown fence（``` / ```json / ```JSON）。
        2. **禁止 thinking aloud**：不要输出 "Let me"、"Wait"、"好的" 等过渡句。
        3. JSON 顶层结构：{{"volumes": [...]}}，卷数与请求一致。
        4. 每个 volume 的字段（英文 key，不得增减）：
           - vol_no (int, 从 1 开始连续)
           - vol_title (str, 非空,如"第一卷 · 序章")
           - summary (str, 1-2 句话描述本卷主线冲突)
           - chapters (list[{{...}}])
        5. 每个 chapter 的字段：
           - title (str, 非空)
           - summary (str, 2-4 句话描述本章主线)
           - target_word_count (int, 默认 3000;100 ≤ value ≤ 20000)
           - beats (list[str], 3-6 个节拍要点;空 list 也可)
           - characters_involved (list[str], 1-5 个角色名;与已有角色尽量对齐)
           - world_refs (list[str], 0-5 个世界观条目名)
           - key_events (list[str], 1-3 个关键事件)
        6. 章数均匀分布在各卷之间;若有总章节数要求,应严格满足。
        7. 故事要有节奏起伏:开局钩子→卷中冲突→卷末高潮→下卷悬念。
        8. 配角与主线呼应,避免孤立无关章节。
        """
    ).strip()


def build_plot_user_prompt(
    *,
    work: "Work",
    total_volumes: int,
    target_chapter_count: int,
    extra_hint: str | None = None,
) -> str:
    genre = work.genre.value if hasattr(work.genre, "value") else (work.genre or _EMPTY)
    style_keywords = "、".join(work.style_keywords or []) or _EMPTY
    target_audience = "、".join(work.target_audience or []) or _EMPTY

    extra_text = f"\n【用户附加要求】\n{extra_hint.strip()}\n" if extra_hint and extra_hint.strip() else ""

    avg_chapters_per_vol = max(1, target_chapter_count // max(1, total_volumes))

    return dedent(
        f"""\
        【作品标题】{work.title}

        【类型】{genre}
        【一句话简介】{work.logline or _EMPTY}
        【风格关键词】{style_keywords}
        【目标读者】{target_audience}
        【备注】{work.notes or _EMPTY}

        【任务约束】
        - 总卷数：{total_volumes}
        - 总章节数：{target_chapter_count}（建议每卷约 {avg_chapters_per_vol} 章,可上下浮动 1-2）
        - 章节目标字数:3000 字左右{extra_text}

        现在请直接输出 JSON。
        """
    ).strip()

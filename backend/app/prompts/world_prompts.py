"""World Agent 的 Prompt 模板

SYSTEM：世界观设计纪律（JSON / 6 维度严格 schema / 不 thinking aloud / 不 markdown fence）。
USER：作品上下文 + 已有世界书内容 + 当前任务（6 维度 or 单维度）+ 用户附加 hint。

6 维度（与 WorldBibleSuggestion 一一对应）：
- geography：地理/区域
- factions：势力/组织
- power_system：力量体系/魔法/修炼
- timeline：历史时间线
- rules：世界规则/禁忌
- culture：文化/语言/信仰
"""
from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.work import Work
    from app.models.world import WorldBible

_EMPTY = "（未指定）"

_ALL_DIMENSIONS = ("geography", "factions", "power_system", "timeline", "rules", "culture")


def build_world_system_prompt() -> str:
    return dedent(
        """\
        你是资深网文世界观设计师,负责为长篇小说设计完整的「世界书」。

        【输出纪律 - 严格遵守】
        1. **只输出 JSON 对象**,禁止任何 markdown fence(``` / ```json / ```JSON)。
        2. **禁止 thinking aloud**:不要输出 "Let me"、"I should"、"Wait"、"好的" 等过渡句。
        3. JSON 顶层结构:{"suggestion": {...}} 或 {...}(任选一种,系统都支持)。
        4. 顶层 schema 严格使用以下 6 个英文 key,顺序不限:
           - geography (object): 地理/区域,至少包含 regions 字段
           - factions (object): 势力/组织,至少包含 factions 字段
           - power_system (object): 力量体系,至少包含 tiers/rules/resources 字段
           - timeline (object): 历史时间线,至少包含 events 字段
           - rules (object): 世界规则/禁忌,至少包含 entries 字段
           - culture (object): 文化/语言/信仰,至少包含 languages/customs 字段
        5. 每个维度的 value 必须是 object(不得是数组或字符串),即使留空也用 `{}`。
        6. 字段内部 value 字符串保持中文,长度 20-150 字为宜。
        7. **维度留空时返回空字典 `{}`**,不要瞎填。
        8. 不要给字段填 "无"、"N/A"、"待定" 等占位 — 实在没有就留空字典。

        【风格适配】
        - 紧贴作品的类型与风格关键词。
        - 力量体系要自洽:有清晰的等级划分与升级路径(网文常见 9-12 阶)。
        - 势力之间应有矛盾与利益冲突,避免全是盟友。
        - 时间线要按"纪元→年份→事件"三段式组织,便于后续章节检索。
        - 规则条目宜精不宜多,5-12 条最佳。
        """
    ).strip()


def build_world_user_prompt(
    *,
    work: "Work",
    existing_world: "WorldBible | None",
    focus_dimension: str = "all",
    extra_hint: str | None = None,
) -> str:
    """构造 World Agent 的 user prompt。

    - work: 作品上下文
    - existing_world: 已有世界书(可避免重复;None 时表示全新生成)
    - focus_dimension: 6 维度之一 或 "all"
    - extra_hint: 用户附加要求
    """
    genre = work.genre.value if hasattr(work.genre, "value") else (work.genre or _EMPTY)
    style_keywords = "、".join(work.style_keywords or []) or _EMPTY
    target_audience = "、".join(work.target_audience or []) or _EMPTY

    existing_block = ""
    if existing_world is not None:
        chunks: list[str] = []
        if existing_world.geography:
            chunks.append(f"geography: {_short(existing_world.geography, 400)}")
        if existing_world.factions:
            chunks.append(f"factions: {_short(existing_world.factions, 400)}")
        if existing_world.power_system:
            chunks.append(f"power_system: {_short(existing_world.power_system, 400)}")
        if existing_world.timeline:
            chunks.append(f"timeline: {_short(existing_world.timeline, 400)}")
        if existing_world.rules:
            chunks.append(f"rules: {_short(existing_world.rules, 400)}")
        if existing_world.culture:
            chunks.append(f"culture: {_short(existing_world.culture, 400)}")
        if existing_world.raw_text:
            chunks.append(f"raw_text: {existing_world.raw_text[:600]}")
        if chunks:
            existing_block = "\n".join(chunks)

    focus_text = {
        "all": "全部 6 维度（geography/factions/power_system/timeline/rules/culture）",
        "geography": "仅 geography 维度（其他维度留空字典 {}）",
        "factions": "仅 factions 维度（其他维度留空字典 {}）",
        "power_system": "仅 power_system 维度（其他维度留空字典 {}）",
        "timeline": "仅 timeline 维度（其他维度留空字典 {}）",
        "rules": "仅 rules 维度（其他维度留空字典 {}）",
        "culture": "仅 culture 维度（其他维度留空字典 {}）",
    }.get(focus_dimension, "全部 6 维度")

    extra_text = f"\n【用户附加要求】\n{extra_hint.strip()}\n" if extra_hint and extra_hint.strip() else ""

    existing_section = ""
    if existing_block:
        existing_section = dedent(
            f"""\
            【已有世界书（请补充而非重复）】
            {existing_block}

            """
        )

    return dedent(
        f"""\
        【作品标题】{work.title}
        【类型】{genre}
        【一句话简介】{work.logline or _EMPTY}
        【风格关键词】{style_keywords}
        【目标读者】{target_audience}
        【备注】{work.notes or _EMPTY}

        {existing_section}【本次任务】{extra_text}
        请生成世界书,焦点:{focus_text}。

        现在请直接输出 JSON。
        """
    ).strip()


def _short(value, max_chars: int) -> str:
    """把 dict/list/str 简短化为单行预览。"""
    if isinstance(value, str):
        return value[:max_chars]
    try:
        import json
        return json.dumps(value, ensure_ascii=False)[:max_chars]
    except Exception:
        return str(value)[:max_chars]


def build_consistency_system_prompt() -> str:
    """世界观一致性检查专用 system prompt(与世界书生成模板分离)。"""
    return dedent(
        """\
        你是网文世界观一致性审校员。对照「世界书」检查「待检正文」是否违反设定。

        【输出纪律】
        1. 只输出 JSON 对象,禁止 markdown fence,禁止 thinking aloud。
        2. 顶层结构:{"issues":[...],"summary":"..."}。
        3. 每条 issue 字段(不得增减):
           - type (str): geography_conflict | faction_conflict | power_system_violation | timeline_conflict | rule_violation | culture_conflict | other
           - severity (str): error | warning | info
           - text (str): 正文中的冲突片段,尽量原文摘录,≤80 字
           - rule_violated (str): 被违反的世界书规则/设定
           - suggestion (str): 可执行的修改建议
           - dimension (str): geography | factions | power_system | timeline | rules | culture | other
        4. 没有冲突时 issues 必须是空数组 [],summary 写「未发现与世界书冲突」。
        5. 不要发明世界书里没有的规则;只报告有依据的冲突。
        6. 最多 12 条;同类冲突合并。
        """
    ).strip()


def build_consistency_user_prompt(
    *,
    work_title: str,
    world_brief: str,
    text: str,
    chapter_title: str | None = None,
    content_max_chars: int = 6000,
) -> str:
    """构造一致性检查 user prompt。"""
    body = text if len(text) <= content_max_chars else text[:content_max_chars] + "\n...(后续省略)..."
    chapter_line = f"【章节标题】{chapter_title}\n" if chapter_title else ""
    world_block = world_brief.strip() or "（世界书为空）"
    return dedent(
        f"""\
        【作品】{work_title}
        {chapter_line}【世界书】
        {world_block}

        【待检正文】
        {body}

        请对照世界书检查正文,直接输出 JSON。
        """
    ).strip()
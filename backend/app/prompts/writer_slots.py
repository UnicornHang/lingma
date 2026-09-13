"""Writer Prompt Slot 装配器。

把 WriterAgent 的 user prompt 从隐式 ``parts.append(...)`` 升级为 **确定性 slot 装配**:
- 每个 slot 有固定标题、内部文本、字数上限
- slot 顺序由"LLM 必读优先级"决定,**不允许改动**
- 装配结果可审计(打印 slot 数、总字数、截断列表)

参照 oh-story-claudecode 的 build_writer_prompt.py 模式。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Optional

from app.prompts.writer_style_profiles import resolve_style

if TYPE_CHECKING:
    from app.models.character import Character
    from app.models.chapter import Chapter
    from app.models.outline import OutlineNode
    from app.models.work import Work
    from app.models.world import WorldBible

    from app.services.chapter_role_resolver import ReferenceHints

_EMPTY = "（未指定）"
_NONE_DESC = "（无）"


# ==================== Slot 数据结构 ====================


@dataclass(frozen=True)
class PromptSlot:
    """单个 prompt 段。

    - ``title``: 在 user prompt 中以【...】形式呈现
    - ``body``: 实际内容(可为空,空 slot 不渲染)
    - ``max_chars``: 软上限;超出按 max_chars 截断并在 ``metadata.truncated`` 记录
    - ``required``: 是否为 Reference Gate 强制 slot(advisory 标记,目前不阻断)
    """

    title: str
    body: str
    max_chars: int = 2000
    required: bool = False

    def render(self) -> str:
        if not self.body.strip():
            return ""
        text = self.body
        if len(text) > self.max_chars:
            half = self.max_chars // 2
            text = text[:half] + "\n…(已截断,后续省略)…\n" + text[-half:]
        return f"{self.title}\n{text}"


@dataclass
class PromptAssembly:
    """完整 prompt 装配结果。"""

    system: str
    slots: list[PromptSlot]
    metadata: dict = field(default_factory=dict)

    @property
    def user_text(self) -> str:
        return "\n\n".join(s.render() for s in self.slots if s.body.strip())

    @property
    def total_chars(self) -> int:
        return len(self.user_text)

    @property
    def truncated_slots(self) -> list[str]:
        return list(self.metadata.get("truncated", []))

    def slot_titles(self) -> list[str]:
        return [s.title for s in self.slots]


# ==================== 世界条目解析 ====================


@dataclass(frozen=True)
class ResolvedRef:
    """世界条目解析结果"""

    name: str
    category: str
    content: str


# WorldBible 字段 → (category 中文名, dict 还是 list)
_WORLD_FIELDS: list[tuple[str, str, str]] = [
    # (attr, category_zh, container_type)
    ("factions", "势力", "dict_or_list"),
    ("geography", "地理", "dict_or_list"),
    ("power_system", "力量体系", "dict"),
    ("timeline", "时间线", "list"),
    ("rules", "世界规则", "list"),
    ("culture", "文化", "dict"),
]


def _coerce_dict(value) -> dict:
    """把 factions/geography 等可能是 dict 或 list 的字段统一成 dict。"""
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        out: dict = {}
        for i, item in enumerate(value):
            if isinstance(item, dict):
                # 取第一个字符串字段当 key
                name = item.get("name") or item.get("名称") or item.get("标题") or f"#{i}"
                content = {k: v for k, v in item.items() if k != name}
                out[str(name)] = content or item
            elif isinstance(item, str):
                out[item] = item
        return out
    return {}


def _format_value(value, max_chars: int = 250) -> str:
    """把 dict/list/str 统一成单行字符串,过长截断。"""
    if isinstance(value, str):
        return value[:max_chars]
    if isinstance(value, dict):
        # 尝试常见字段:简介/描述/desc/description/设定
        for key in ("简介", "描述", "desc", "description", "设定", "介绍"):
            if key in value and isinstance(value[key], str):
                return value[key][:max_chars]
        # 否则把所有 key: value 拼起来
        parts = []
        for k, v in list(value.items())[:6]:
            if isinstance(v, str):
                parts.append(f"{k}={v[:80]}")
            elif isinstance(v, (int, float, bool)):
                parts.append(f"{k}={v}")
        s = "; ".join(parts)
        return s[:max_chars] if s else str(value)[:max_chars]
    if isinstance(value, list):
        s = "、".join(str(x) for x in value[:8])
        return s[:max_chars]
    return str(value)[:max_chars]


def resolve_world_refs(
    world: Optional["WorldBible"],
    names: Iterable[str] | None,
    *,
    per_entry_max_chars: int = 250,
) -> list[ResolvedRef]:
    """从 WorldBible JSON blob 解析指定名字的世界条目。

    行为:
    - names 为空/None → 返回 []
    - world 为 None → 返回 []
    - 名字在 factions/geography/power_system/timeline/rules/culture 任一字段命中 → 返回
    - 多个字段都有同名字段时,选第一个匹配的(category 顺序由 _WORLD_FIELDS 决定)
    """
    if world is None or not names:
        return []
    name_list = [n for n in names if n]
    if not name_list:
        return []
    resolved: list[ResolvedRef] = []
    seen: set[str] = set()
    for attr, category, container in _WORLD_FIELDS:
        value = getattr(world, attr, None)
        if not value:
            continue
        if container == "dict":
            d = value if isinstance(value, dict) else {}
        else:
            d = _coerce_dict(value)
        for name in name_list:
            if name in seen:
                continue
            if name in d:
                resolved.append(
                    ResolvedRef(
                        name=name,
                        category=category,
                        content=_format_value(d[name], max_chars=per_entry_max_chars),
                    )
                )
                seen.add(name)
    return resolved


# ==================== Slot 装配 ====================


def _join_list(items: Iterable, sep: str = "、", empty: str = _EMPTY) -> str:
    items_list = [str(x) for x in (items or []) if x]
    if not items_list:
        return empty
    return sep.join(items_list)


def _format_work_slot(work: "Work") -> str:
    genre = work.genre.value if hasattr(work.genre, "value") else (work.genre or _EMPTY)
    return (
        f"标题：{work.title}\n"
        f"类型：{genre}\n"
        f"一句话简介：{work.logline or _EMPTY}\n"
        f"目标读者：{_join_list(work.target_audience or [])}"
    )


def _format_outline_slot(outline: Optional["OutlineNode"]) -> str:
    if outline is None:
        return ""
    beats = outline.beats or []
    beats_text = "\n".join(f"  - {b}" for b in beats) if beats else f"  {_NONE_DESC}"
    return (
        f"标题：{outline.title}\n"
        f"类型：{outline.type}\n"
        f"简介：{outline.summary or _NONE_DESC}\n"
        f"节拍：\n{beats_text}\n"
        f"涉及角色：{_join_list(outline.characters_involved or [])}\n"
        f"涉及世界条目：{_join_list(outline.world_refs or [])}"
    )


def _format_same_volume_slot(same_volume_outline: list["OutlineNode"]) -> str:
    if not same_volume_outline:
        return ""
    lines = []
    for sib in same_volume_outline[:15]:
        summary_1line = (sib.summary or "").split("\n")[0][:80]
        lines.append(f"  - {sib.title}：{summary_1line or _NONE_DESC}")
    return "\n".join(lines)


def _format_world_full_slot(world: Optional["WorldBible"], max_chars: int = 1200) -> str:
    if world is None or not world.raw_text:
        return ""
    text = world.raw_text.strip()
    if len(text) > max_chars:
        half = max_chars // 2
        text = text[:half] + "\n…(节选,后续省略)…\n" + text[-half:]
    return text


def _format_world_refs_slot(refs: list[ResolvedRef]) -> str:
    if not refs:
        return ""
    lines = []
    for ref in refs:
        lines.append(f"  - [{ref.category}] {ref.name}：{ref.content}")
    return "\n".join(lines)


def _format_characters_slot(characters: list["Character"]) -> str:
    if not characters:
        return ""
    lines = []
    for c in characters[:8]:
        desc = (c.raw_text or "").replace("\n", " ")[:120]
        lines.append(f"  - {c.name}（{c.role}）：{desc or _NONE_DESC}")
    return "\n".join(lines)


def _format_task_slot(
    chapter: "Chapter",
    target_word_count: Optional[int],
    has_existing_tail: bool,
) -> str:
    target_words = target_word_count or chapter.word_count or 3000
    tail_hint = (
        "现在请从上述已有正文的末尾自然续写，不要重复、不要总结前文："
        if has_existing_tail
        else "现在请开始撰写本章正文："
    )
    return (
        f"标题：{chapter.title}\n"
        f"目标字数：约 {target_words} 字\n"
        f"摘要要求：{chapter.summary or _NONE_DESC}\n\n"
        f"{tail_hint}"
    )


# ==================== 主入口 ====================


def assemble_writer_slots(
    *,
    work: "Work",
    chapter: "Chapter",
    outline: Optional["OutlineNode"],
    world: Optional["WorldBible"],
    characters: list["Character"],
    previous_summary: Optional[str],
    existing_tail: Optional[str],
    target_word_count: Optional[int],
    same_volume_outline: list["OutlineNode"],
    world_refs: Optional[list[str]],
    reference_hints: Optional["ReferenceHints"] = None,
) -> PromptAssembly:
    """装配完整的 WriterAgent user prompt(11 个有序 slot)。

    顺序(不可改):
    1. 作品总览
    2. 文风裁决
    3. 本章大纲
    4. Reference Gate 必读(advice)
    5. 同卷其他章节
    6. 世界书全文(节选,受 hints.must_read_world_full 控制)
    7. 世界条目(精准,resolve_world_refs)
    8. 出场角色
    9. 上一章摘要
    10. 本章已有正文(续写模式)
    11. 本章任务
    """
    slots: list[PromptSlot] = []
    truncated: list[str] = []

    # 1. 作品总览
    work_body = _format_work_slot(work)
    slots.append(PromptSlot(
        title="【作品总览】",
        body=work_body,
        max_chars=600,
    ))

    # 2. 文风裁决(总是存在,即使空 keywords 也有默认基调)
    style_body = resolve_style(work.style_keywords or [])
    slots.append(PromptSlot(
        title="【文风裁决】",
        body=style_body,
        max_chars=800,
    ))

    # 3. 本章大纲
    if outline:
        slots.append(PromptSlot(
            title="【本章大纲】",
            body=_format_outline_slot(outline),
            max_chars=1500,
        ))

    # 4. Reference Gate 必读(advice)
    if reference_hints is not None:
        must_lines = []
        if reference_hints.must_read_world_full:
            must_lines.append("- 必读：【世界书全文】(见下方 slot)")
        if reference_hints.must_read_world_refs:
            must_lines.append("- 必读：【世界条目(精准)】(见下方 slot)")
        if reference_hints.must_read_characters_all:
            must_lines.append("- 必读：所有【出场角色】卡(见下方 slot)")
        elif reference_hints.must_read_characters_focused:
            must_lines.append("- 必读：聚焦【出场角色】卡(见下方 slot)")
        must_lines.append(f"- 章节角色判定：{reference_hints.role.value}")
        if reference_hints.notes:
            must_lines.append(f"- 理由：{reference_hints.notes}")
        slots.append(PromptSlot(
            title="【Reference Gate 必读】",
            body="\n".join(must_lines),
            max_chars=600,
            required=True,
        ))

    # 5. 同卷其他章节
    same_vol_body = _format_same_volume_slot(same_volume_outline)
    if same_vol_body:
        slots.append(PromptSlot(
            title="【同卷其他章节(上下文连贯)】",
            body=same_vol_body,
            max_chars=1500,
        ))

    # 6. 世界书全文 —— 严格按 Reference Gate 控制
    #    reference_hints=None 时走 TRANSITION 默认(不开 world_full,节省 token)
    world_full_enabled = (
        reference_hints is not None and reference_hints.must_read_world_full
    )
    if world_full_enabled:
        body = _format_world_full_slot(world, max_chars=1200)
        if body:
            slots.append(PromptSlot(
                title="【世界书(节选)】",
                body=body,
                max_chars=1200,
            ))

    # 7. 世界条目(精准)
    refs = resolve_world_refs(world, world_refs)
    if refs:
        slots.append(PromptSlot(
            title="【世界条目(精准)】",
            body=_format_world_refs_slot(refs),
            max_chars=1500,
        ))

    # 8. 出场角色
    char_body = _format_characters_slot(characters)
    if char_body:
        slots.append(PromptSlot(
            title="【出场角色】",
            body=char_body,
            max_chars=1500,
        ))

    # 9. 上一章摘要
    if previous_summary:
        slots.append(PromptSlot(
            title="【上一章摘要】",
            body=previous_summary,
            max_chars=600,
        ))

    # 10. 本章已有正文(续写模式)
    if existing_tail:
        slots.append(PromptSlot(
            title="【本章已有正文(请从末尾自然续写,不要重复、不要总结前文)】",
            body=existing_tail,
            max_chars=2000,
        ))

    # 11. 本章任务
    task_body = _format_task_slot(
        chapter, target_word_count, existing_tail is not None
    )
    slots.append(PromptSlot(
        title="【本章任务】",
        body=task_body,
        max_chars=400,
    ))

    # 渲染时记录被截断的 slot
    final_slots: list[PromptSlot] = []
    for s in slots:
        if len(s.body) > s.max_chars:
            truncated.append(s.title)
        final_slots.append(s)

    return PromptAssembly(
        system="",  # 由 caller 拼接(build_user_prompt 会拼上 build_system_prompt)
        slots=final_slots,
        metadata={
            "truncated": truncated,
            "slot_count": len(final_slots),
            "has_existing_tail": existing_tail is not None,
            "has_world": world is not None,
            "world_refs_resolved": [r.name for r in refs],
        },
    )

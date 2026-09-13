"""章节角色(故事层面)解析 + Reference Gate。

为什么需要这个:``task_type``(continue/generate)是 **技术** 维度,
但章节是"开篇"还是"反转"是 **故事** 维度。本模块按 outline 标题/summary
启发式判断章节在故事结构中的位置,然后路由不同的 references。

第一版用关键词匹配,不修改模型字段。后续可在 ``OutlineNode`` 上加
``chapter_role`` 字段做持久化,接口签名不变。

Reference Gate 行为:
- 按章节角色返回 **必须读的 references**(口吻提示)
- 现在是 advisory 级别:返回空不阻断,只记录 warning 日志
- 后续接入密度统计后可升级为 blocking
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.character import Character
    from app.models.outline import OutlineNode
    from app.models.world import WorldBible

logger = logging.getLogger(__name__)


class ChapterRole(str, Enum):
    """章节在故事中的结构位置"""

    OPENING = "opening"          # 开篇/楔子/第 1 章
    REVEAL = "reveal"            # 真相/揭露/身世揭晓
    CLIMAX = "climax"            # 高潮/决战/对决
    TRANSITION = "transition"    # 日常/过渡/修炼(默认)


# 关键词 → 角色 路由。第一个命中的胜出。
_CHAPTER_ROLE_KEYWORDS: dict[ChapterRole, list[str]] = {
    ChapterRole.OPENING: [
        "开篇", "序章", "楔子", "第1章", "第一章", "第 1 章", "故事开始",
        "序幕", "缘起", "开端",
    ],
    ChapterRole.REVEAL: [
        "真相", "揭露", "揭晓", "身世", "秘密", "谜底", "浮现",
        "原来", "原来如此", "真相大白", "阴谋",
    ],
    ChapterRole.CLIMAX: [
        "决战", "高潮", "对决", "爆发", "死战", "总攻", "终极",
        "boss战", "boss 战", "摊牌",
    ],
    ChapterRole.TRANSITION: [
        "日常", "过渡", "修炼", "赶路", "休整", "沉淀",
    ],
}


def resolve_chapter_role(outline: Optional["OutlineNode"]) -> ChapterRole:
    """根据 outline 标题 + summary 启发式判断章节角色。

    规则:
    1. 标题命中关键词 → 直接返回对应角色
    2. summary 命中关键词 → 同上
    3. 都没命中 → 默认 TRANSITION
    """
    if outline is None:
        return ChapterRole.TRANSITION

    # 标题权重最高
    title = outline.title or ""
    for role, kws in _CHAPTER_ROLE_KEYWORDS.items():
        for kw in kws:
            if kw in title:
                return role

    # summary 次之
    summary = outline.summary or ""
    if summary:
        for role, kws in _CHAPTER_ROLE_KEYWORDS.items():
            for kw in kws:
                if kw in summary:
                    return role

    return ChapterRole.TRANSITION


@dataclass(frozen=True)
class ReferenceHints:
    """Reference Gate 输出:必须读的 references 列表(字符串标题)+ metadata。"""

    role: ChapterRole
    must_read_world_full: bool = False    # 是否必须读世界书全文
    must_read_world_refs: bool = False    # 是否必须读 outline.world_refs
    must_read_characters_all: bool = False  # 是否必须读所有出场角色
    must_read_characters_focused: bool = True  # 是否聚焦已聚焦的角色
    notes: str = ""                       # 给 LLM 的额外提示


def references_for_role(
    role: ChapterRole,
    outline: Optional["OutlineNode"],
) -> ReferenceHints:
    """根据章节角色返回必须读的 references 路由。

    路由规则:
    - OPENING   → 世界书全文(第一印象)+ 聚焦角色
    - REVEAL    → outline.world_refs(被揭露的内容)
    - CLIMAX    → outline.world_refs + 全部出场角色
    - TRANSITION → outline.world_refs(为下一章铺垫)
    """
    if role == ChapterRole.OPENING:
        return ReferenceHints(
            role=role,
            must_read_world_full=True,
            must_read_world_refs=False,
            must_read_characters_all=False,
            must_read_characters_focused=True,
            notes="开篇章节:第一印象很重要,务必读完世界书总览与聚焦角色设定,"
                  "让读者 500 字内进入世界观。",
        )
    if role == ChapterRole.REVEAL:
        return ReferenceHints(
            role=role,
            must_read_world_full=False,
            must_read_world_refs=True,
            must_read_characters_all=False,
            must_read_characters_focused=True,
            notes="揭示章节:务必读 outline.world_refs 涉及的世界条目,"
                  "确保被揭露的内容与世界观一致。",
        )
    if role == ChapterRole.CLIMAX:
        return ReferenceHints(
            role=role,
            must_read_world_full=False,
            must_read_world_refs=True,
            must_read_characters_all=True,
            must_read_characters_focused=True,
            notes="高潮章节:所有出场角色设定都要读到,"
                  "确保战斗/对决符合角色能力与世界规则。",
        )
    # TRANSITION 默认
    return ReferenceHints(
        role=role,
        must_read_world_full=False,
        must_read_world_refs=True,
        must_read_characters_all=False,
        must_read_characters_focused=True,
        notes="过渡章节:聚焦 outline.world_refs 为下一章做铺垫。",
    )


def apply_reference_gate(
    outline: Optional["OutlineNode"],
    world: Optional["WorldBible"],
    characters: list["Character"],
    hints: ReferenceHints,
) -> tuple[Optional["WorldBible"], list["Character"]]:
    """根据 ReferenceHints 实际筛选/裁剪 world 与 characters。

    - must_read_world_full=True 时保留完整 world(raw_text 后续按 max_chars 截)
    - must_read_world_full=False 时若 world 没东西就不传
    - must_read_characters_all=True 保留全部 characters(由 caller 限定上限)
    - must_read_characters_all=False 保留全部(此处不缩,留给上层聚焦逻辑)

    返回: (effective_world, effective_characters)
    """
    # characters 列表直接交给上层聚焦逻辑;这里只做白名单标记
    effective_characters = list(characters) if characters else []

    # world:OPENING 用 raw_text 全量;其他若没有内容则置 None
    if world is None:
        effective_world: Optional["WorldBible"] = None
    elif hints.must_read_world_full:
        effective_world = world
    elif world.raw_text and len(world.raw_text.strip()) > 0:
        effective_world = world  # 保留,后面 slot 自己截
    else:
        # 没 raw_text 但有结构化字段时仍保留(供 world_refs 解析)
        has_struct = any([
            world.geography, world.factions, world.power_system,
            world.timeline, world.rules, world.culture,
        ])
        effective_world = world if has_struct else None

    if effective_world is None and (outline and outline.world_refs):
        logger.warning(
            "Reference Gate: outline.world_refs=%s 非空但 world 为空,"
            "世界条目将无法解析。建议在世界书管理界面补全。",
            outline.world_refs,
        )

    return effective_world, effective_characters

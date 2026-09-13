"""[P3.4] 卷分组 —— 把章节按 OutlineNode 树分组,无大纲则回退到单卷。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from app.models.chapter import Chapter
from app.models.outline import OutlineNode, OutlineNodeType


@dataclass
class Volume:
    """导出用卷:含章节列表与卷名。

    `title` 来源:
    - 有 outline 时:根 OutlineNode(VOLUME 类型)的 title
    - 无 outline 时:作品级默认 "正文"
    """

    title: str
    chapters: list[Chapter] = field(default_factory=list)


def _build_outline_index(
    nodes: Sequence[OutlineNode],
) -> tuple[dict[str, OutlineNode], dict[str, list[str]]]:
    """建两个索引:
    - id -> node: 用于 O(1) 查节点
    - id -> [child ids 顺序]: 用于递归走子节点

    假设 caller 已经按 (order asc, created_at asc) 排序。
    """
    by_id: dict[str, OutlineNode] = {str(n.id): n for n in nodes}
    children_map: dict[str, list[str]] = {str(n.id): [] for n in nodes}
    for n in nodes:
        if n.parent_id is not None:
            key = str(n.parent_id)
            if key in children_map:
                children_map[key].append(str(n.id))
    return by_id, children_map


def _find_root_volume_chain(
    node_id: str,
    by_id: dict[str, OutlineNode],
) -> list[OutlineNode]:
    """从任意节点向上找最近的 VOLUME 类型祖先链(包含自身若是 VOLUME)。"""
    chain: list[OutlineNode] = []
    cur = by_id.get(node_id)
    while cur is not None:
        if cur.type == OutlineNodeType.VOLUME:
            chain.append(cur)
        cur = by_id.get(str(cur.parent_id)) if cur.parent_id else None
    # 从 root → leaf 顺序反转
    return list(reversed(chain))


def _walk_root_volumes(
    by_id: dict[str, OutlineNode],
    children_map: dict[str, list[str]],
) -> list[OutlineNode]:
    """按 (order, created_at) 顺序遍历所有 VOLUME 根节点,以及它们的子节点。"""
    roots = [
        n for n in by_id.values()
        if n.parent_id is None and n.type == OutlineNodeType.VOLUME
    ]
    # 兜底:即使没有任何根 VOLUME,只要存在节点就按 (order, created_at) 输出
    if not roots:
        roots = sorted(
            [n for n in by_id.values() if n.parent_id is None],
            key=lambda n: (n.order, n.created_at),
        )
    # 在每个 root 下收集所有后代 VOLUME(可能存在嵌套卷,如"上卷/中卷/下卷")
    ordered: list[OutlineNode] = []

    def visit(node: OutlineNode) -> None:
        ordered.append(node)
        for child_id in children_map.get(str(node.id), []):
            child = by_id.get(child_id)
            if child is None:
                continue
            if child.type == OutlineNodeType.VOLUME:
                visit(child)
            else:
                # CHAPTER/BEAT 节点不作为独立卷,直接挂到当前卷下
                pass

    for r in roots:
        visit(r)
    return ordered


def group_chapters_by_volume(
    chapters: Sequence[Chapter],
    outline_nodes: Sequence[OutlineNode],
) -> list[Volume]:
    """把章节按 outline 分卷。

    规则:
    1. 如果 outline_nodes 为空 → 单卷(作品正文),按 chapters 顺序
    2. 否则按 outline 根 VOLUME 顺序建卷,每章挂到其 outline_node_id
       所属的最近 VOLUME 祖先
    3. outline_node_id 为 None 的章节 → 归入末尾"未分类"卷
    """
    if not outline_nodes:
        return [Volume(title="正文", chapters=list(chapters))]

    by_id, children_map = _build_outline_index(outline_nodes)
    ordered_volumes = _walk_root_volumes(by_id, children_map)

    # 初始化所有卷
    volume_by_node_id: dict[str, Volume] = {
        str(v.id): Volume(title=v.title) for v in ordered_volumes
    }
    # 维护输出顺序
    volumes_out: list[Volume] = list(volume_by_node_id.values())
    uncategorized = Volume(title="未分类")
    has_uncategorized = False

    for ch in chapters:
        if ch.outline_node_id is None:
            uncategorized.chapters.append(ch)
            has_uncategorized = True
            continue
        chain = _find_root_volume_chain(str(ch.outline_node_id), by_id)
        # 取链尾(最近的 VOLUME)
        target = chain[-1] if chain else None
        if target is None:
            uncategorized.chapters.append(ch)
            has_uncategorized = True
            continue
        vol = volume_by_node_id.get(str(target.id))
        if vol is None:
            # 章节的 outline_node 找不到对应 VOLUME 祖先(数据异常) → 兜底
            uncategorized.chapters.append(ch)
            has_uncategorized = True
        else:
            vol.chapters.append(ch)

    # 过滤掉没有任何章节的空卷(避免大綱中预留了章节但还没写的节点产生空 heading)
    volumes_out = [v for v in volumes_out if v.chapters]

    if has_uncategorized:
        volumes_out.append(uncategorized)

    return volumes_out

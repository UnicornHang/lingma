"""写正文前的细纲门禁：无对应章纲不得首次落笔。"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter
from app.models.outline import OutlineNode, OutlineNodeType


class OutlineGateError(Exception):
    """细纲不足，应返回 409 并提示补纲。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


async def resolve_outline_for_write(
    db: AsyncSession,
    chapter: Chapter,
    outline_node_id: UUID | None = None,
) -> OutlineNode:
    """解析本章细纲；不满足写作条件时抛 OutlineGateError。"""
    node_id = outline_node_id or chapter.outline_node_id
    if node_id is None:
        raise OutlineGateError("尚未关联章纲。请先在大纲中创建本章细纲并关联后再写正文。")

    node = await db.get(OutlineNode, node_id)
    if node is None or node.work_id != chapter.work_id:
        raise OutlineGateError("章纲不存在或不属于当前作品，请重新关联细纲。")
    if node.type == OutlineNodeType.VOLUME:
        raise OutlineGateError("当前关联的是卷纲。请关联到具体章节细纲后再写正文。")

    constraints = node.write_constraints if isinstance(node.write_constraints, dict) else {}
    must_happen = constraints.get("must_happen") or []
    has_spec = bool(
        (node.summary or "").strip()
        or (node.beats or [])
        or (isinstance(must_happen, list) and any(str(x).strip() for x in must_happen))
    )
    if not has_spec:
        raise OutlineGateError(
            "细纲内容为空（缺少简介、节拍或「必须发生」）。请先补纲，再写正文。"
        )
    return node

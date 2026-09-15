"""细纲写作门禁。"""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.outline import OutlineNodeType
from app.services.outline_gate import OutlineGateError, resolve_outline_for_write


class _FakeDb:
    def __init__(self, node=None):
        self.node = node

    async def get(self, _cls, _id):
        return self.node


def _chapter(**kwargs):
    data = {"work_id": uuid4(), "outline_node_id": None}
    data.update(kwargs)
    return SimpleNamespace(**data)


def _node(**kwargs):
    data = {
        "work_id": uuid4(),
        "type": OutlineNodeType.CHAPTER,
        "summary": "主角对质",
        "beats": ["冲突"],
        "write_constraints": {"must_happen": ["摊牌"]},
    }
    data.update(kwargs)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_gate_rejects_missing_outline():
    ch = _chapter()
    with pytest.raises(OutlineGateError, match="尚未关联章纲"):
        await resolve_outline_for_write(_FakeDb(), ch)


@pytest.mark.asyncio
async def test_gate_rejects_volume_node():
    work_id = uuid4()
    node = _node(work_id=work_id, type=OutlineNodeType.VOLUME)
    ch = _chapter(work_id=work_id, outline_node_id=uuid4())
    with pytest.raises(OutlineGateError, match="卷纲"):
        await resolve_outline_for_write(_FakeDb(node), ch)


@pytest.mark.asyncio
async def test_gate_rejects_empty_spec():
    work_id = uuid4()
    node = _node(work_id=work_id, summary="", beats=[], write_constraints={})
    ch = _chapter(work_id=work_id, outline_node_id=uuid4())
    with pytest.raises(OutlineGateError, match="细纲内容为空"):
        await resolve_outline_for_write(_FakeDb(node), ch)


@pytest.mark.asyncio
async def test_gate_accepts_chapter_with_must_happen():
    work_id = uuid4()
    node = _node(work_id=work_id, summary="", beats=[], write_constraints={"must_happen": ["对决"]})
    ch = _chapter(work_id=work_id, outline_node_id=uuid4())
    got = await resolve_outline_for_write(_FakeDb(node), ch)
    assert got is node

"""[P3.5] 作品 JSON 包导入/导出服务。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter, ChapterStatus
from app.models.character import Character
from app.models.outline import OutlineNode, OutlineNodeType
from app.models.work import Genre, Work, WorkStatus
from app.models.world import WorldBible
from app.schemas.work_package import (
    FORMAT_VERSION,
    ImportMode,
    WorkImportResult,
    WorkPackage,
)
from app.services import work_service

logger = logging.getLogger(__name__)


def _enum_value(v: Any) -> str:
    """枚举或字符串统一为 str。"""
    return v.value if hasattr(v, "value") else str(v)


def _serialize_work(work: Work) -> dict[str, Any]:
    """序列化作品主信息。"""
    return {
        "id": str(work.id),
        "title": work.title,
        "genre": _enum_value(work.genre),
        "target_word_count": work.target_word_count,
        "logline": work.logline,
        "style_keywords": work.style_keywords or [],
        "target_audience": work.target_audience or [],
        "status": _enum_value(work.status),
        "word_count": work.word_count,
        "settings": work.settings or {},
        "created_at": work.created_at.isoformat() if work.created_at else None,
        "updated_at": work.updated_at.isoformat() if work.updated_at else None,
    }


def _serialize_chapter(ch: Chapter) -> dict[str, Any]:
    """序列化章节(不含版本历史,减小包体积)。"""
    return {
        "id": str(ch.id),
        "outline_node_id": str(ch.outline_node_id) if ch.outline_node_id else None,
        "title": ch.title,
        "content": ch.content or {},
        "plain_content": ch.plain_content or "",
        "summary": ch.summary or "",
        "key_events": ch.key_events or [],
        "word_count": ch.word_count,
        "status": _enum_value(ch.status),
        "version": ch.version,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
        "updated_at": ch.updated_at.isoformat() if ch.updated_at else None,
    }


def _serialize_character(c: Character) -> dict[str, Any]:
    """序列化角色卡。"""
    return {
        "id": str(c.id),
        "name": c.name,
        "role": c.role,
        "basic_info": c.basic_info or {},
        "personality": c.personality or {},
        "backstory": c.backstory or {},
        "relationships": c.relationships or [],
        "arc": c.arc or {},
        "voice_samples": c.voice_samples or [],
        "appearance_count": c.appearance_count,
        "raw_text": c.raw_text or "",
    }


def _serialize_outline(n: OutlineNode) -> dict[str, Any]:
    """序列化大纲节点。"""
    return {
        "id": str(n.id),
        "parent_id": str(n.parent_id) if n.parent_id else None,
        "type": _enum_value(n.type),
        "title": n.title,
        "summary": n.summary or "",
        "beats": n.beats or [],
        "characters_involved": n.characters_involved or [],
        "world_refs": n.world_refs or [],
        "target_word_count": n.target_word_count,
        "order": n.order,
    }


def _serialize_world(w: WorldBible) -> dict[str, Any]:
    """序列化世界观。"""
    return {
        "id": str(w.id),
        "geography": w.geography or {},
        "factions": w.factions or [],
        "power_system": w.power_system or {},
        "timeline": w.timeline or [],
        "rules": w.rules or [],
        "culture": w.culture or {},
        "raw_text": w.raw_text or "",
    }


async def export_work_package(db: AsyncSession, work_id: UUID) -> WorkPackage:
    """导出完整作品包。"""
    work = await work_service.get_work(db, work_id)
    # selectin 已加载关系;显式访问保证懒加载触发
    chapters = sorted(
        work.chapters or [],
        key=lambda c: c.created_at or datetime.min.replace(tzinfo=timezone.utc),
    )
    outlines = sorted(work.outline_nodes or [], key=lambda n: (n.order, str(n.id)))
    characters = list(work.characters or [])
    world = work.world_bible

    return WorkPackage(
        format_version=FORMAT_VERSION,
        exported_at=datetime.now(tz=timezone.utc),
        work_info=_serialize_work(work),
        world_bible=_serialize_world(world) if world else None,
        characters=[_serialize_character(c) for c in characters],
        outline=[_serialize_outline(n) for n in outlines],
        chapters=[_serialize_chapter(c) for c in chapters],
        settings=work.settings or {},
    )


def parse_work_package(raw: dict[str, Any]) -> WorkPackage:
    """校验并解析上传的 JSON 包。"""
    if not isinstance(raw, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="导入文件必须是 JSON 对象",
        )
    if "work_info" not in raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少 work_info 字段",
        )
    version = str(raw.get("format_version", ""))
    if version and not version.startswith("1."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的 format_version: {version}",
        )
    try:
        return WorkPackage.model_validate(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"作品包解析失败: {exc}",
        ) from exc


def _parse_genre(value: Any) -> Genre:
    """解析题材枚举,未知值回退 OTHER。"""
    try:
        return Genre(value)
    except (ValueError, TypeError):
        return Genre.OTHER


def _parse_work_status(value: Any) -> WorkStatus:
    """解析作品状态。"""
    try:
        return WorkStatus(value)
    except (ValueError, TypeError):
        return WorkStatus.DRAFT


def _parse_chapter_status(value: Any) -> ChapterStatus:
    """解析章节状态。"""
    try:
        return ChapterStatus(value)
    except (ValueError, TypeError):
        return ChapterStatus.DRAFT


def _parse_outline_type(value: Any) -> OutlineNodeType:
    """解析大纲节点类型。"""
    try:
        return OutlineNodeType(value)
    except (ValueError, TypeError):
        return OutlineNodeType.CHAPTER


def _plain_to_tiptap(text: str) -> dict[str, Any]:
    """纯文本 → 最小 TipTap JSON。"""
    paragraphs = text.split("\n") if text else [""]
    content = []
    for p in paragraphs:
        content.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": p}] if p else [],
            }
        )
    return {"type": "doc", "content": content or [{"type": "paragraph"}]}


async def _create_children(
    db: AsyncSession,
    work: Work,
    package: WorkPackage,
    *,
    id_map: dict[str, UUID],
) -> None:
    """按包内容写入大纲/角色/世界/章节;大纲与章节 id 通过 id_map 重映射。"""

    # 1) 大纲:先建全部节点(新 UUID),再二次回填 parent_id
    outline_items = package.outline or []
    for node in outline_items:
        old_id = str(node.get("id") or uuid4())
        new_id = uuid4()
        id_map[old_id] = new_id
        db.add(
            OutlineNode(
                id=new_id,
                work_id=work.id,
                parent_id=None,
                type=_parse_outline_type(node.get("type")),
                title=str(node.get("title") or "未命名节点")[:200],
                summary=str(node.get("summary") or ""),
                beats=node.get("beats") or [],
                characters_involved=node.get("characters_involved") or [],
                world_refs=node.get("world_refs") or [],
                target_word_count=int(node.get("target_word_count") or 3000),
                order=int(node.get("order") or 0),
            )
        )
    await db.flush()

    for node in outline_items:
        old_id = str(node.get("id") or "")
        old_parent = node.get("parent_id")
        if not old_id or not old_parent:
            continue
        new_id = id_map.get(old_id)
        new_parent = id_map.get(str(old_parent))
        if new_id and new_parent:
            result = await db.execute(select(OutlineNode).where(OutlineNode.id == new_id))
            row = result.scalar_one_or_none()
            if row:
                row.parent_id = new_parent
    await db.flush()

    # 2) 角色
    for c in package.characters or []:
        db.add(
            Character(
                id=uuid4(),
                work_id=work.id,
                name=str(c.get("name") or "未命名角色")[:100],
                role=str(c.get("role") or "supporting")[:20],
                basic_info=c.get("basic_info") or {},
                personality=c.get("personality") or {},
                backstory=c.get("backstory") or {},
                relationships=c.get("relationships") or [],
                arc=c.get("arc") or {},
                voice_samples=c.get("voice_samples") or [],
                appearance_count=int(c.get("appearance_count") or 0),
                raw_text=str(c.get("raw_text") or ""),
                is_indexed=False,
            )
        )

    # 3) 世界观
    wb = package.world_bible
    if wb:
        db.add(
            WorldBible(
                id=uuid4(),
                work_id=work.id,
                geography=wb.get("geography") or {},
                factions=wb.get("factions") or [],
                power_system=wb.get("power_system") or {},
                timeline=wb.get("timeline") or [],
                rules=wb.get("rules") or [],
                culture=wb.get("culture") or {},
                raw_text=str(wb.get("raw_text") or ""),
                is_indexed=False,
            )
        )

    # 4) 章节
    for ch in package.chapters or []:
        plain = str(ch.get("plain_content") or "")
        content = ch.get("content") if isinstance(ch.get("content"), dict) else None
        if not content:
            content = _plain_to_tiptap(plain)
        outline_ref = ch.get("outline_node_id")
        mapped_outline = id_map.get(str(outline_ref)) if outline_ref else None
        db.add(
            Chapter(
                id=uuid4(),
                work_id=work.id,
                outline_node_id=mapped_outline,
                title=str(ch.get("title") or "未命名章节")[:200],
                content=content,
                plain_content=plain,
                summary=str(ch.get("summary") or ""),
                key_events=ch.get("key_events") or [],
                word_count=int(ch.get("word_count") or len(plain)),
                status=_parse_chapter_status(ch.get("status")),
                version=int(ch.get("version") or 1),
            )
        )
    await db.flush()


async def import_work_package(
    db: AsyncSession,
    package: WorkPackage,
    *,
    mode: ImportMode = "create",
) -> WorkImportResult:
    """导入作品包。

    - create: 始终新建作品与子实体(新 UUID)
    - overwrite: 若 work_info.id 已存在则删除后重建;否则等同 create
    """
    info = package.work_info or {}
    title = str(info.get("title") or "导入作品")[:100]
    source_id_raw = info.get("id")
    source_id: UUID | None = None
    if source_id_raw:
        try:
            source_id = UUID(str(source_id_raw))
        except ValueError:
            source_id = None

    applied_mode: ImportMode = "create"
    if mode == "overwrite" and source_id is not None:
        existing = await db.execute(select(Work).where(Work.id == source_id))
        old = existing.scalar_one_or_none()
        if old:
            await db.delete(old)
            await db.flush()
            applied_mode = "overwrite"

    work = Work(
        id=source_id if applied_mode == "overwrite" and source_id else uuid4(),
        title=title,
        genre=_parse_genre(info.get("genre")),
        target_word_count=int(info.get("target_word_count") or 1_000_000),
        logline=str(info.get("logline") or "")[:500],
        style_keywords=info.get("style_keywords") or [],
        target_audience=info.get("target_audience") or [],
        status=_parse_work_status(info.get("status")),
        word_count=int(info.get("word_count") or 0),
        settings=package.settings or info.get("settings") or {},
    )
    db.add(work)
    await db.flush()

    id_map: dict[str, UUID] = {}
    await _create_children(db, work, package, id_map=id_map)

    # 若 word_count 为 0,按章节合计回填
    if work.word_count <= 0:
        work.word_count = sum(int(c.get("word_count") or 0) for c in (package.chapters or []))

    await db.flush()
    await db.refresh(work)

    return WorkImportResult(
        work_id=work.id,
        title=work.title,
        mode=applied_mode,
        chapter_count=len(package.chapters or []),
        character_count=len(package.characters or []),
        outline_count=len(package.outline or []),
        has_world_bible=package.world_bible is not None,
        message=(
            f"{'覆盖导入' if applied_mode == 'overwrite' else '新建导入'}成功: "
            f"《{work.title}》"
        ),
    )


async def import_txt_as_work(
    db: AsyncSession,
    *,
    title: str,
    text: str,
    genre: Genre = Genre.OTHER,
) -> WorkImportResult:
    """将纯 TXT 按空行分段导入为新作品(每段一章)。"""
    chunks = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TXT 内容为空",
        )

    chapters_payload = []
    for i, chunk in enumerate(chunks, start=1):
        first_line = chunk.split("\n", 1)[0][:80]
        chapter_title = first_line if len(first_line) <= 40 else f"第{i}章"
        chapters_payload.append(
            {
                "title": chapter_title,
                "plain_content": chunk,
                "content": _plain_to_tiptap(chunk),
                "word_count": len(chunk),
                "status": "draft",
                "version": 1,
            }
        )

    package = WorkPackage(
        format_version=FORMAT_VERSION,
        exported_at=datetime.now(tz=timezone.utc),
        work_info={
            "title": title[:100] or "TXT 导入作品",
            "genre": genre.value,
            "logline": "",
            "target_word_count": 1_000_000,
            "style_keywords": [],
            "target_audience": [],
            "status": "draft",
            "word_count": sum(c["word_count"] for c in chapters_payload),
        },
        chapters=chapters_payload,
    )
    return await import_work_package(db, package, mode="create")

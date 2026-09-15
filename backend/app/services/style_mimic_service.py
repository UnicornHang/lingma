"""仿文风格画像服务：CRUD + Writer 短卡派生。"""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.style_profile import StyleProfile
from app.models.work import Work
from app.schemas.style_mimic import (
    StyleMemoryCard,
    StylePortrait,
    StyleProfileRead,
    StyleProfileUpdate,
    StyleSnippet,
)


async def _require_work(db: AsyncSession, work_id: UUID) -> Work:
    """作品不存在则 404。"""
    work = await db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作品不存在")
    return work


async def get_style_profile(
    db: AsyncSession, work_id: UUID
) -> StyleProfile | None:
    """按作品取风格画像（可为空）。"""
    await _require_work(db, work_id)
    result = await db.execute(
        select(StyleProfile).where(StyleProfile.work_id == work_id)
    )
    return result.scalar_one_or_none()


async def get_style_profile_or_404(
    db: AsyncSession, work_id: UUID
) -> StyleProfile:
    """取画像，没有则 404。"""
    profile = await get_style_profile(db, work_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="尚未生成仿文风格画像，请先粘贴样本分析",
        )
    return profile


async def upsert_style_profile(
    db: AsyncSession,
    work_id: UUID,
    *,
    portrait: StylePortrait,
    writing_directives: str,
    snippets: list[StyleSnippet],
    source_label: str,
    source_char_count: int,
    enabled: bool = True,
) -> StyleProfile:
    """创建或覆盖本作品风格画像（不存样本原文）。"""
    await _require_work(db, work_id)
    existing = await get_style_profile(db, work_id)
    payload_portrait = portrait.model_dump()
    payload_snippets = [s.model_dump() for s in snippets]

    if existing is None:
        existing = StyleProfile(
            work_id=work_id,
            source_label=source_label or "",
            source_char_count=source_char_count,
            portrait=payload_portrait,
            writing_directives=writing_directives or "",
            snippets=payload_snippets,
            enabled=enabled,
        )
        db.add(existing)
    else:
        existing.source_label = source_label or existing.source_label
        existing.source_char_count = source_char_count
        existing.portrait = payload_portrait
        existing.writing_directives = writing_directives or ""
        existing.snippets = payload_snippets
        existing.enabled = enabled

    await db.flush()
    await db.refresh(existing)
    return existing


async def update_style_profile(
    db: AsyncSession, work_id: UUID, payload: StyleProfileUpdate
) -> StyleProfile:
    """部分更新启用状态 / 来源标签。"""
    profile = await get_style_profile_or_404(db, work_id)
    if payload.enabled is not None:
        profile.enabled = payload.enabled
    if payload.source_label is not None:
        profile.source_label = payload.source_label
    await db.flush()
    await db.refresh(profile)
    return profile


async def delete_style_profile(db: AsyncSession, work_id: UUID) -> None:
    """删除风格画像。"""
    profile = await get_style_profile(db, work_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="没有可删除的风格画像",
        )
    await db.delete(profile)
    await db.flush()


def to_read_model(profile: StyleProfile) -> StyleProfileRead:
    """ORM → 读模型。"""
    portrait = StylePortrait.model_validate(profile.portrait or {})
    snippets = [StyleSnippet.model_validate(s) for s in (profile.snippets or [])]
    return StyleProfileRead(
        id=profile.id,
        work_id=profile.work_id,
        source_label=profile.source_label or "",
        source_char_count=profile.source_char_count or 0,
        portrait=portrait,
        writing_directives=profile.writing_directives or "",
        snippets=snippets,
        enabled=bool(profile.enabled),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def to_memory_card(profile: StyleProfile) -> StyleMemoryCard | None:
    """仅启用时返回 Writer 短卡。"""
    if not profile.enabled:
        return None
    return StyleMemoryCard(
        source_label=profile.source_label or "",
        writing_directives=profile.writing_directives or "",
        portrait=StylePortrait.model_validate(profile.portrait or {}),
        snippets=[StyleSnippet.model_validate(s) for s in (profile.snippets or [])],
    )


async def load_writer_style_memory(
    db: AsyncSession, work_id: UUID
) -> StyleMemoryCard | None:
    """Writer 写前加载：无画像或未启用则 None。"""
    result = await db.execute(
        select(StyleProfile).where(StyleProfile.work_id == work_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        return None
    return to_memory_card(profile)

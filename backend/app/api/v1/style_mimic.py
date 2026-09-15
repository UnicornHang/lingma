"""仿文风格画像 API。"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.style_mimic_agent import StyleMimicAgent, _prepare_sample
from app.deps import get_db
from app.schemas.style_mimic import (
    StyleMimicAnalyzeRequest,
    StyleMimicAnalyzeResponse,
    StyleProfileRead,
    StyleProfileUpdate,
)
from app.services import style_mimic_service

router = APIRouter()


@router.post(
    "/works/{work_id}/style-mimic/analyze",
    response_model=StyleMimicAnalyzeResponse,
    summary="仿文：粘贴样本分析风格画像",
)
async def analyze_style_mimic(
    work_id: UUID,
    payload: StyleMimicAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> StyleMimicAnalyzeResponse:
    """分析用户自备样本；默认落库并启用。不写入连续性账本。"""
    agent = StyleMimicAgent()
    try:
        portrait, directives, snippets, model_used, used_heuristic = (
            await agent.analyze_sample(
                db,
                sample_text=payload.sample_text,
                source_label=payload.source_label,
                work_id=work_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    source_chars = len(_prepare_sample(payload.sample_text))
    profile_read: StyleProfileRead | None = None
    if payload.save:
        profile = await style_mimic_service.upsert_style_profile(
            db,
            work_id,
            portrait=portrait,
            writing_directives=directives,
            snippets=snippets,
            source_label=payload.source_label,
            source_char_count=source_chars,
            enabled=payload.enabled,
        )
        await db.commit()
        profile_read = style_mimic_service.to_read_model(profile)

    return StyleMimicAnalyzeResponse(
        portrait=portrait,
        writing_directives=directives,
        snippets=snippets,
        source_char_count=source_chars,
        model_used=model_used,
        used_heuristic=used_heuristic,
        profile=profile_read,
    )


@router.get(
    "/works/{work_id}/style-mimic",
    response_model=StyleProfileRead | None,
    summary="获取本作品仿文风格画像",
)
async def get_style_mimic(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StyleProfileRead | None:
    """读取已保存的风格画像；尚未生成时返回 null。"""
    profile = await style_mimic_service.get_style_profile(db, work_id)
    if profile is None:
        return None
    return style_mimic_service.to_read_model(profile)


@router.patch(
    "/works/{work_id}/style-mimic",
    response_model=StyleProfileRead,
    summary="更新仿文画像启用状态或来源标签",
)
async def patch_style_mimic(
    work_id: UUID,
    payload: StyleProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> StyleProfileRead:
    """开关写前注入，或改来源标签。"""
    profile = await style_mimic_service.update_style_profile(db, work_id, payload)
    await db.commit()
    return style_mimic_service.to_read_model(profile)


@router.delete(
    "/works/{work_id}/style-mimic",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除仿文风格画像",
)
async def delete_style_mimic(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """清除风格记忆；不影响风格关键词与账本。"""
    await style_mimic_service.delete_style_profile(db, work_id)
    await db.commit()

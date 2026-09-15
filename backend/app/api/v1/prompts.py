"""[P4] Prompt 模板 API —— /settings/prompts"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.prompt_template import (
    PromptTemplateListResponse,
    PromptTemplateRead,
    PromptTemplateUpdate,
)
from app.services import prompt_template_service

router = APIRouter()


@router.get(
    "",
    response_model=PromptTemplateListResponse,
    summary="列出 6 个 Agent 的 Prompt 模板",
)
async def list_prompts_endpoint(
    db: AsyncSession = Depends(get_db),
) -> PromptTemplateListResponse:
    """返回全部 Agent 模板(首次访问时写入内置默认)。"""
    items = await prompt_template_service.list_templates(db)
    await db.commit()
    return PromptTemplateListResponse(items=items)


@router.get(
    "/{agent_type}",
    response_model=PromptTemplateRead,
    summary="获取单个 Agent 的 Prompt 模板",
)
async def get_prompt_endpoint(
    agent_type: str,
    db: AsyncSession = Depends(get_db),
) -> PromptTemplateRead:
    item = await prompt_template_service.get_template(db, agent_type)
    await db.commit()
    return item


@router.patch(
    "/{agent_type}",
    response_model=PromptTemplateRead,
    summary="更新 Agent Prompt 模板",
)
async def update_prompt_endpoint(
    agent_type: str,
    payload: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
) -> PromptTemplateRead:
    item = await prompt_template_service.update_template(db, agent_type, payload)
    await db.commit()
    return item


@router.post(
    "/{agent_type}/reset",
    response_model=PromptTemplateRead,
    status_code=status.HTTP_200_OK,
    summary="重置为代码内置默认 Prompt",
)
async def reset_prompt_endpoint(
    agent_type: str,
    db: AsyncSession = Depends(get_db),
) -> PromptTemplateRead:
    item = await prompt_template_service.reset_template(db, agent_type)
    await db.commit()
    return item

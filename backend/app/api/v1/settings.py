"""设置 API（应用设置 + LLM API 配置）"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.setting import (
    ApiConfigCreate,
    ApiConfigRead,
    ApiConfigUpdate,
    ApiKeyReveal,
    ProviderModelsRequest,
    ProviderModelsResponse,
    SettingsBundle,
    SettingsUpdate,
)
from app.services import setting_service
from app.services.llm_service import LLMError, list_provider_models

router = APIRouter()


# ===== 应用设置 =====


@router.get(
    "/",
    response_model=SettingsBundle,
    summary="获取应用全局设置",
)
async def get_settings_endpoint(db: AsyncSession = Depends(get_db)) -> SettingsBundle:
    return await setting_service.get_settings(db)


@router.patch(
    "/",
    response_model=SettingsBundle,
    summary="更新应用全局设置",
)
async def update_settings_endpoint(
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> SettingsBundle:
    bundle = await setting_service.update_settings(db, payload)
    await db.commit()
    return bundle


# ===== API 配置 =====


@router.get(
    "/api-configs",
    response_model=List[ApiConfigRead],
    summary="列出所有 LLM API 配置",
)
async def list_api_configs_endpoint(
    db: AsyncSession = Depends(get_db),
) -> List[ApiConfigRead]:
    configs = await setting_service.list_api_configs(db)
    return [setting_service.to_api_config_read(c) for c in configs]


@router.post(
    "/api-configs",
    response_model=ApiConfigRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建 LLM API 配置",
)
async def create_api_config_endpoint(
    payload: ApiConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiConfigRead:
    config = await setting_service.create_api_config(db, payload)
    await db.commit()
    await db.refresh(config)
    return setting_service.to_api_config_read(config)


@router.patch(
    "/api-configs/{config_id}",
    response_model=ApiConfigRead,
    summary="更新 LLM API 配置",
)
async def update_api_config_endpoint(
    config_id: UUID,
    payload: ApiConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiConfigRead:
    config = await setting_service.update_api_config(db, config_id, payload)
    await db.commit()
    await db.refresh(config)
    return setting_service.to_api_config_read(config)


@router.delete(
    "/api-configs/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 LLM API 配置",
)
async def delete_api_config_endpoint(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await setting_service.delete_api_config(db, config_id)
    await db.commit()


@router.post(
    "/api-configs/{config_id}/reveal",
    response_model=ApiKeyReveal,
    summary="一次性显示明文 API Key",
)
async def reveal_api_key_endpoint(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiKeyReveal:
    """⚠️ 谨慎调用，明文 Key 不会持久化返回"""
    return await setting_service.reveal_api_key(db, config_id)


@router.post(
    "/api-configs/models",
    response_model=ProviderModelsResponse,
    summary="拉取 Provider 可用模型清单（不持久化）",
)
async def list_provider_models_endpoint(
    payload: ProviderModelsRequest,
) -> ProviderModelsResponse:
    """用于前端配置表单的「获取模型列表」按钮。

    - OpenAI 兼容（OpenAI / DeepSeek / Qwen / MiniMax / LMStudio / vLLM）：GET {base_url}/models
    - Ollama：GET {base_url}/api/tags
    - Anthropic：返回内置静态清单
    """
    try:
        result = await list_provider_models(
            provider=payload.provider,
            base_url=payload.base_url,
            api_key=payload.api_key,
        )
    except LLMError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ProviderModelsResponse(models=result.models, source=result.source, note=result.note)
"""设置 API（应用设置 + LLM API 配置）"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.setting import (
    ApiConfigCreate,
    ApiConfigRead,
    ApiConfigUpdate,
    ApiKeyReveal,
    SettingsBundle,
    SettingsUpdate,
)
from app.services import setting_service

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
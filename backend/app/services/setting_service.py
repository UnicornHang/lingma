"""Setting 业务逻辑层（应用设置 + API 配置）"""
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_config import APIConfig, Provider
from app.models.setting import Setting
from app.schemas.setting import (
    ApiConfigCreate,
    ApiConfigRead,
    ApiConfigUpdate,
    ApiKeyReveal,
    SettingsBundle,
    SettingsUpdate,
)
from app.services.crypto_service import decrypt, encrypt


# ==================== 应用设置（key-value 单例）====================


SETTINGS_KEY = "app_settings"


def _bundle_to_value(b: SettingsBundle) -> dict:
    return b.model_dump()


def _value_to_bundle(v: dict) -> SettingsBundle:
    return SettingsBundle(**v) if v else SettingsBundle()


async def get_settings(db: AsyncSession) -> SettingsBundle:
    """获取应用设置"""
    result = await db.execute(select(Setting).where(Setting.key == SETTINGS_KEY))
    setting = result.scalar_one_or_none()
    if not setting:
        return SettingsBundle()
    return _value_to_bundle(setting.value)


async def update_settings(db: AsyncSession, payload: SettingsUpdate) -> SettingsBundle:
    """更新应用设置"""
    result = await db.execute(select(Setting).where(Setting.key == SETTINGS_KEY))
    setting = result.scalar_one_or_none()

    current = _value_to_bundle(setting.value if setting else {})
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(current, k, v)

    if setting is None:
        setting = Setting(key=SETTINGS_KEY, value=_bundle_to_value(current), encrypted=False)
        db.add(setting)
    else:
        setting.value = _bundle_to_value(current)

    await db.flush()
    return current


# ==================== API 配置 ====================


def _mask_key(encrypted: str | None) -> str:
    """脱敏 API Key"""
    if not encrypted:
        return "(未设置)"
    plain = decrypt(encrypted)
    if not plain:
        return "(解密失败)"
    if len(plain) <= 8:
        return "***"
    return f"{plain[:4]}...{plain[-4:]}"


async def list_api_configs(db: AsyncSession) -> Sequence[APIConfig]:
    """列出所有 API 配置"""
    result = await db.execute(select(APIConfig).order_by(APIConfig.created_at.asc()))
    return result.scalars().all()


async def get_api_config(db: AsyncSession, config_id: UUID) -> APIConfig:
    """获取单个 API 配置"""
    result = await db.execute(select(APIConfig).where(APIConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API 配置不存在")
    return config


async def create_api_config(db: AsyncSession, payload: ApiConfigCreate) -> APIConfig:
    """创建 API 配置（加密 Key）"""
    encrypted = None
    if payload.api_key:
        encrypted = encrypt(payload.api_key.get_secret_value())

    try:
        provider_enum = Provider(payload.provider)
    except ValueError:
        provider_enum = Provider.CUSTOM

    config = APIConfig(
        name=payload.name,
        provider=provider_enum,
        api_key_encrypted=encrypted,
        base_url=payload.base_url or "",
        model_name=payload.model_name,
        enabled=payload.enabled,
        max_context_tokens=payload.max_context_tokens,
        cost_per_1k_input=payload.cost_per_1k_input,
        cost_per_1k_output=payload.cost_per_1k_output,
        agent_assignments=payload.agent_assignments,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


async def update_api_config(
    db: AsyncSession, config_id: UUID, payload: ApiConfigUpdate
) -> APIConfig:
    """更新 API 配置"""
    config = await get_api_config(db, config_id)
    data = payload.model_dump(exclude_unset=True)

    if "api_key" in data and data["api_key"] is not None:
        config.api_key_encrypted = encrypt(data["api_key"].get_secret_value())
        data.pop("api_key")

    for key, value in data.items():
        setattr(config, key, value)

    await db.flush()
    await db.refresh(config)
    return config


async def delete_api_config(db: AsyncSession, config_id: UUID) -> None:
    """删除 API 配置"""
    config = await get_api_config(db, config_id)
    await db.delete(config)
    await db.flush()


async def reveal_api_key(db: AsyncSession, config_id: UUID) -> ApiKeyReveal:
    """解出明文 API Key（仅一次性）"""
    config = await get_api_config(db, config_id)
    return ApiKeyReveal(api_key=decrypt(config.api_key_encrypted or ""))


def to_api_config_read(config: APIConfig) -> ApiConfigRead:
    """ORM -> Read Schema（带脱敏）"""
    return ApiConfigRead(
        id=config.id,
        name=config.name,
        provider=config.provider.value if isinstance(config.provider, Provider) else str(config.provider),
        masked_key=_mask_key(config.api_key_encrypted),
        base_url=config.base_url or "",
        model_name=config.model_name,
        enabled=config.enabled,
        max_context_tokens=config.max_context_tokens,
        cost_per_1k_input=config.cost_per_1k_input,
        cost_per_1k_output=config.cost_per_1k_output,
        agent_assignments=config.agent_assignments or [],
        created_at=config.created_at,
        updated_at=config.updated_at,
    )
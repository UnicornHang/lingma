"""Setting 业务逻辑层（应用设置 + API 配置 + StylePreset）"""
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_config import APIConfig, Provider
from app.models.setting import Setting, StylePreset
from app.schemas.setting import (
    ApiConfigCreate,
    ApiConfigRead,
    ApiConfigUpdate,
    ApiKeyReveal,
    SettingsBundle,
    SettingsUpdate,
    StylePresetCreate,
    StylePresetUpdate,
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


# ==================== StylePreset 写作风格预设 ====================


# 启动时注入的 4 套内置预设(name 是自然主键,upsert 语义)
_BUILTIN_PRESETS = [
    {
        "name": "默认基调",
        "description": "系统默认,无明确风格偏好",
        "style_keywords": [],
        "target_audience": ["不限"],
        "target_word_count": 3000,
    },
    {
        "name": "仙侠玄幻",
        "description": "修真世界,长篇热血,升级打怪",
        "style_keywords": ["热血", "修仙", "升级", "宗门"],
        "target_audience": ["男频"],
        "target_word_count": 3500,
    },
    {
        "name": "都市言情",
        "description": "现代都市,情感细腻,人物刻画",
        "style_keywords": ["细腻", "情感", "都市", "现实"],
        "target_audience": ["女频"],
        "target_word_count": 2500,
    },
    {
        "name": "科幻硬核",
        "description": "硬科幻,逻辑严谨,概念驱动",
        "style_keywords": ["理性", "硬科幻", "概念", "逻辑"],
        "target_audience": ["不限"],
        "target_word_count": 3000,
    },
]


async def ensure_builtin_presets(db: AsyncSession) -> None:
    """启动时确保内置预设存在（idempotent upsert）。"""
    for preset_data in _BUILTIN_PRESETS:
        result = await db.execute(
            select(StylePreset).where(StylePreset.name == preset_data["name"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            db.add(StylePreset(is_builtin=True, **preset_data))
        elif not existing.is_builtin:
            # 用户曾用同名预设,标记为 builtin 并合并
            existing.is_builtin = True
            for k, v in preset_data.items():
                setattr(existing, k, v)
    await db.flush()


async def list_style_presets(db: AsyncSession) -> Sequence[StylePreset]:
    """列出所有风格预设(builtin 在前,然后按创建时间)。"""
    result = await db.execute(
        select(StylePreset).order_by(
            StylePreset.is_builtin.desc(),
            StylePreset.created_at.asc(),
        )
    )
    return result.scalars().all()


async def get_style_preset(db: AsyncSession, preset_id: UUID) -> StylePreset:
    """获取单个预设。"""
    result = await db.execute(
        select(StylePreset).where(StylePreset.id == preset_id)
    )
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"风格预设 {preset_id} 不存在",
        )
    return preset


async def create_style_preset(
    db: AsyncSession, payload: StylePresetCreate
) -> StylePreset:
    """新建风格预设。"""
    preset = StylePreset(
        name=payload.name,
        description=payload.description,
        style_keywords=payload.style_keywords,
        target_audience=payload.target_audience,
        target_word_count=payload.target_word_count,
        is_builtin=False,
    )
    db.add(preset)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"风格预设名 '{payload.name}' 已存在",
        ) from e
    await db.refresh(preset)
    return preset


async def update_style_preset(
    db: AsyncSession, preset_id: UUID, payload: StylePresetUpdate
) -> StylePreset:
    """更新风格预设。"""
    preset = await get_style_preset(db, preset_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(preset, key, value)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"风格预设名冲突",
        ) from e
    await db.refresh(preset)
    return preset


async def delete_style_preset(db: AsyncSession, preset_id: UUID) -> None:
    """删除风格预设（builtin 不允许删）。"""
    preset = await get_style_preset(db, preset_id)
    if preset.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="内置预设不可删除",
        )
    await db.delete(preset)
    await db.flush()


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
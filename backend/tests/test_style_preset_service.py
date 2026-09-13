"""StylePreset 写作风格预设 - 业务层单测

覆盖:
- 内置预设 ensure_builtin_presets idempotent
- list_style_presets 返回 builtin 在前
- create/get/update/delete 正常路径
- create 同名冲突 409
- delete 内置预设 403
- update 不存在的 id 404
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.setting_service import (
    create_style_preset,
    delete_style_preset,
    ensure_builtin_presets,
    get_style_preset,
    list_style_presets,
    update_style_preset,
)
from app.schemas.setting import StylePresetCreate, StylePresetUpdate


# ============== Fixtures ==============


@pytest.fixture
async def db():
    """每次测试拿到干净 db,清空 style_presets 表。"""
    from app.db.session import async_session_factory
    from app.models.setting import StylePreset
    from sqlalchemy import delete as sa_delete

    async with async_session_factory() as session:
        yield session
        await session.execute(sa_delete(StylePreset))
        await session.commit()


# ============== ensure_builtin_presets ==============


async def test_ensure_builtin_presets_creates_defaults(db: AsyncSession):
    """首次调用 → 创建 4 个内置预设。"""
    await ensure_builtin_presets(db)
    presets = await list_style_presets(db)
    names = {p.name for p in presets}
    assert "默认基调" in names
    assert "仙侠玄幻" in names
    assert "都市言情" in names
    assert "科幻硬核" in names
    assert len(presets) >= 4


async def test_ensure_builtin_presets_idempotent(db: AsyncSession):
    """连续两次调用 → 不会重复创建。"""
    await ensure_builtin_presets(db)
    first_count = len(await list_style_presets(db))
    await ensure_builtin_presets(db)
    second_count = len(await list_style_presets(db))
    assert first_count == second_count


async def test_builtin_presets_marked_is_builtin(db: AsyncSession):
    """内置预设 is_builtin=True。"""
    await ensure_builtin_presets(db)
    presets = await list_style_presets(db)
    builtin_names = {p.name for p in presets if p.is_builtin}
    assert "仙侠玄幻" in builtin_names


# ============== list_style_presets ==============


async def test_list_presets_orders_builtin_first(db: AsyncSession):
    """list 输出 builtin 在前,后按创建时间。"""
    await ensure_builtin_presets(db)
    user_preset = await create_style_preset(
        db,
        StylePresetCreate(
            name="我的自定义",
            style_keywords=["x"],
            target_audience=["y"],
        ),
    )
    presets = await list_style_presets(db)
    # 第一个应是 builtin
    assert presets[0].is_builtin
    # 用户自定义应在最后
    assert presets[-1].id == user_preset.id


# ============== create_style_preset ==============


async def test_create_style_preset_basic(db: AsyncSession):
    """创建自定义预设 → 正常返回 + is_builtin=False。"""
    preset = await create_style_preset(
        db,
        StylePresetCreate(
            name="我的玄幻",
            description="热血升级流",
            style_keywords=["热血", "升级"],
            target_audience=["男频"],
            target_word_count=4000,
        ),
    )
    assert preset.id is not None
    assert preset.name == "我的玄幻"
    assert preset.is_builtin is False
    assert preset.target_word_count == 4000


async def test_create_style_preset_duplicate_name_409(db: AsyncSession):
    """同名 → 409。"""
    await create_style_preset(
        db,
        StylePresetCreate(name="冲突名", style_keywords=[]),
    )
    with pytest.raises(HTTPException) as exc:
        await create_style_preset(
            db,
            StylePresetCreate(name="冲突名", style_keywords=[]),
        )
    assert exc.value.status_code == 409


async def test_create_style_preset_default_word_count(db: AsyncSession):
    """不传 target_word_count → 默认 3000。"""
    preset = await create_style_preset(
        db,
        StylePresetCreate(name="无字数", style_keywords=[]),
    )
    assert preset.target_word_count == 3000


# ============== get_style_preset ==============


async def test_get_style_preset_success(db: AsyncSession):
    """获取存在的预设。"""
    created = await create_style_preset(
        db,
        StylePresetCreate(name="get 测试", style_keywords=["a"]),
    )
    fetched = await get_style_preset(db, created.id)
    assert fetched.id == created.id
    assert fetched.name == "get 测试"


async def test_get_style_preset_not_found_404(db: AsyncSession):
    """不存在的 id → 404。"""
    with pytest.raises(HTTPException) as exc:
        await get_style_preset(db, uuid4())
    assert exc.value.status_code == 404


# ============== update_style_preset ==============


async def test_update_style_preset_partial(db: AsyncSession):
    """部分更新 → 只改指定字段。"""
    created = await create_style_preset(
        db,
        StylePresetCreate(
            name="待更新",
            style_keywords=["a"],
            target_audience=["不限"],
            target_word_count=3000,
        ),
    )
    updated = await update_style_preset(
        db,
        created.id,
        StylePresetUpdate(target_word_count=5000),
    )
    assert updated.target_word_count == 5000
    # 其他字段保持
    assert updated.name == "待更新"
    assert updated.style_keywords == ["a"]


async def test_update_style_preset_not_found_404(db: AsyncSession):
    with pytest.raises(HTTPException) as exc:
        await update_style_preset(
            db,
            uuid4(),
            StylePresetUpdate(name="不存在"),
        )
    assert exc.value.status_code == 404


# ============== delete_style_preset ==============


async def test_delete_style_preset_success(db: AsyncSession):
    """删除自定义预设 → 成功。"""
    created = await create_style_preset(
        db,
        StylePresetCreate(name="待删", style_keywords=[]),
    )
    await delete_style_preset(db, created.id)
    with pytest.raises(HTTPException) as exc:
        await get_style_preset(db, created.id)
    assert exc.value.status_code == 404


async def test_delete_builtin_preset_403(db: AsyncSession):
    """删除内置预设 → 403。"""
    await ensure_builtin_presets(db)
    presets = await list_style_presets(db)
    builtin = next(p for p in presets if p.is_builtin)
    with pytest.raises(HTTPException) as exc:
        await delete_style_preset(db, builtin.id)
    assert exc.value.status_code == 403


async def test_delete_style_preset_not_found_404(db: AsyncSession):
    with pytest.raises(HTTPException) as exc:
        await delete_style_preset(db, uuid4())
    assert exc.value.status_code == 404
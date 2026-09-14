"""[P3.5] 系统备份服务 —— tar.gz 归档 / 恢复 / 保留策略。

备份内容(与 scripts/backup.sh 对齐):
- SQLite 数据库目录(works/)
- Chroma 向量库目录(vector_store/)

不打包 .env(含明文 API Key);API Key 已在 DB 中加密存储。
"""
from __future__ import annotations

import logging
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.setting import Setting
from app.models.work import Work
from app.schemas.backup import (
    BackupCreateResponse,
    BackupInfo,
    BackupListResponse,
    BackupPrefs,
    BackupPrefsUpdate,
    BackupRestoreResponse,
    ClearDataResponse,
)

logger = logging.getLogger(__name__)

BACKUP_PREFS_KEY = "backup_prefs"
BACKUP_NAME_PREFIX = "zhimeng_"
BACKUP_SUFFIX = ".tar.gz"


def resolve_backup_dir() -> Path:
    """解析并确保备份目录存在。"""
    path = Path(settings.backup_dir).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_db_file() -> Path:
    """从 DATABASE_URL 提取 SQLite 文件路径。"""
    raw = settings.database_url.replace("sqlite+aiosqlite:///", "").replace(
        "sqlite:///", ""
    )
    if not raw or raw.startswith(":"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="当前数据库不是可备份的文件型 SQLite",
        )
    return Path(raw).expanduser().resolve()


def resolve_works_dir() -> Path:
    """作品数据目录(含 zhimeng.db)。"""
    return resolve_db_file().parent


def resolve_vector_dir() -> Path:
    """向量库目录。"""
    return Path(settings.vector_store_path).expanduser().resolve()


def get_backup_file_path(filename: str) -> Path:
    """校验文件名并返回绝对路径(防路径穿越)。"""
    name = Path(filename).name
    if not name.startswith(BACKUP_NAME_PREFIX) or not name.endswith(BACKUP_SUFFIX):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非法备份文件名",
        )
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非法备份文件名",
        )
    root = resolve_backup_dir()
    path = (root / name).resolve()
    if path.parent != root:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非法备份路径",
        )
    return path


def _info_from_path(path: Path) -> BackupInfo:
    """从文件构造 BackupInfo。"""
    stat = path.stat()
    return BackupInfo(
        filename=path.name,
        size_bytes=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        path=str(path),
    )


async def get_backup_prefs(db: AsyncSession) -> BackupPrefs:
    """读取备份偏好(无记录则用默认值)。"""
    result = await db.execute(select(Setting).where(Setting.key == BACKUP_PREFS_KEY))
    row = result.scalar_one_or_none()
    if not row:
        return BackupPrefs(keep_count=settings.backup_keep_default)
    return BackupPrefs(**row.value)


async def update_backup_prefs(
    db: AsyncSession, payload: BackupPrefsUpdate
) -> BackupPrefs:
    """更新备份偏好。"""
    current = await get_backup_prefs(db)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(current, k, v)

    result = await db.execute(select(Setting).where(Setting.key == BACKUP_PREFS_KEY))
    row = result.scalar_one_or_none()
    value = current.model_dump()
    if row is None:
        db.add(Setting(key=BACKUP_PREFS_KEY, value=value, encrypted=False))
    else:
        row.value = value
    await db.flush()
    return current


async def _checkpoint_sqlite(db: AsyncSession) -> None:
    """尽量刷盘 WAL,使文件拷贝一致(不 commit,由调用方控制事务)。"""
    try:
        await db.execute(text("PRAGMA wal_checkpoint(FULL)"))
        await db.flush()
    except Exception as exc:  # noqa: BLE001 — 检查点失败不阻断备份
        logger.warning("SQLite wal_checkpoint 失败,继续文件拷贝: %s", exc)


def list_backup_files() -> list[BackupInfo]:
    """列出备份目录下全部归档(按时间倒序)。"""
    root = resolve_backup_dir()
    items = [
        _info_from_path(p)
        for p in root.glob(f"{BACKUP_NAME_PREFIX}*{BACKUP_SUFFIX}")
        if p.is_file()
    ]
    items.sort(key=lambda x: x.created_at, reverse=True)
    return items


async def list_backups(db: AsyncSession) -> BackupListResponse:
    """聚合列表响应。"""
    prefs = await get_backup_prefs(db)
    items = list_backup_files()
    return BackupListResponse(
        backup_dir=str(resolve_backup_dir()),
        prefs=prefs,
        last_backup_at=items[0].created_at if items else None,
        items=items,
    )


def prune_backups(keep_count: int) -> int:
    """按保留份数删除最旧备份,返回删除数量。"""
    items = list_backup_files()
    if len(items) <= keep_count:
        return 0
    removed = 0
    for info in items[keep_count:]:
        path = get_backup_file_path(info.filename)
        try:
            path.unlink(missing_ok=True)
            removed += 1
        except OSError as exc:
            logger.warning("删除旧备份失败 %s: %s", path, exc)
    return removed


async def create_backup(db: AsyncSession) -> BackupCreateResponse:
    """创建一份 tar.gz 备份并执行保留策略。"""
    await _checkpoint_sqlite(db)

    works_dir = resolve_works_dir()
    vector_dir = resolve_vector_dir()
    backup_dir = resolve_backup_dir()

    if not works_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"作品数据目录不存在: {works_dir}",
        )

    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{BACKUP_NAME_PREFIX}{stamp}{BACKUP_SUFFIX}"
    target = backup_dir / filename

    # 先拷到临时目录再打包,避免对正在写入的路径直接 tar
    with tempfile.TemporaryDirectory(prefix="zhimeng_bak_") as tmp:
        tmp_path = Path(tmp)
        works_dst = tmp_path / "works"
        vector_dst = tmp_path / "vector_store"
        shutil.copytree(works_dir, works_dst, dirs_exist_ok=True)
        if vector_dir.exists():
            shutil.copytree(vector_dir, vector_dst, dirs_exist_ok=True)
        else:
            vector_dst.mkdir(parents=True, exist_ok=True)

        with tarfile.open(target, "w:gz") as tar:
            tar.add(works_dst, arcname="works")
            tar.add(vector_dst, arcname="vector_store")

    prefs = await get_backup_prefs(db)
    pruned = prune_backups(prefs.keep_count)
    logger.info("备份完成: %s (pruned=%s)", target, pruned)
    return BackupCreateResponse(backup=_info_from_path(target), pruned=pruned)


async def delete_backup(filename: str) -> None:
    """删除指定备份。"""
    path = get_backup_file_path(filename)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"备份不存在: {filename}",
        )
    path.unlink()


async def restore_backup(db: AsyncSession, filename: str) -> BackupRestoreResponse:
    """从归档恢复 works/ 与 vector_store/。

    恢复后当前进程的 ORM 连接可能仍指向旧映射 —— 调用方应提示重启后端。
    """
    path = get_backup_file_path(filename)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"备份不存在: {filename}",
        )

    works_dir = resolve_works_dir()
    vector_dir = resolve_vector_dir()

    # 恢复前再做一次即时备份,便于回滚误操作
    try:
        await create_backup(db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("恢复前自动备份失败(继续恢复): %s", exc)

    with tempfile.TemporaryDirectory(prefix="zhimeng_restore_") as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(path, "r:gz") as tar:
            # Python 3.12+ 推荐 filter;兼容旧版本时忽略
            try:
                tar.extractall(tmp_path, filter="data")
            except TypeError:
                tar.extractall(tmp_path)

        src_works = tmp_path / "works"
        src_vector = tmp_path / "vector_store"
        if not src_works.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="备份包缺少 works/ 目录",
            )

        # 直接替换磁盘文件;调用方应重启后端以刷新连接池
        if works_dir.exists():
            shutil.rmtree(works_dir)
        shutil.copytree(src_works, works_dir)

        if vector_dir.exists():
            shutil.rmtree(vector_dir)
        if src_vector.exists():
            shutil.copytree(src_vector, vector_dir)
        else:
            vector_dir.mkdir(parents=True, exist_ok=True)

    return BackupRestoreResponse(
        filename=filename,
        message="数据已恢复到磁盘。请重启后端服务以重新加载数据库连接。",
        requires_restart=True,
    )


async def clear_all_work_data(db: AsyncSession) -> ClearDataResponse:
    """清理全部作品数据(级联章节/角色/大纲/世界书),保留设置与 API Key。"""
    result = await db.execute(select(Work))
    works = list(result.scalars().all())
    count = len(works)
    for work in works:
        await db.delete(work)
    await db.flush()

    # 清空向量库目录(重建空目录)
    vector_dir = resolve_vector_dir()
    if vector_dir.exists():
        shutil.rmtree(vector_dir)
    vector_dir.mkdir(parents=True, exist_ok=True)

    return ClearDataResponse(
        deleted_works=count,
        message=f"已删除 {count} 部作品及相关向量索引;系统设置与 API Key 已保留。",
    )

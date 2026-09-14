"""[P3.5] 系统备份 API —— /settings/backup/*"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.backup import (
    BackupCreateResponse,
    BackupListResponse,
    BackupPrefs,
    BackupPrefsUpdate,
    BackupRestoreResponse,
    ClearDataResponse,
)
from app.services import backup_service

router = APIRouter()


@router.get(
    "",
    response_model=BackupListResponse,
    summary="列出备份归档与偏好",
)
async def list_backups_endpoint(
    db: AsyncSession = Depends(get_db),
) -> BackupListResponse:
    """列出备份目录下的归档,并返回当前偏好。"""
    return await backup_service.list_backups(db)


@router.patch(
    "/prefs",
    response_model=BackupPrefs,
    summary="更新备份偏好(自动备份/周期/保留份数)",
)
async def update_backup_prefs_endpoint(
    payload: BackupPrefsUpdate,
    db: AsyncSession = Depends(get_db),
) -> BackupPrefs:
    """更新自动备份开关、周期与保留份数。"""
    prefs = await backup_service.update_backup_prefs(db, payload)
    await db.commit()
    return prefs


@router.post(
    "",
    response_model=BackupCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="立即创建一份系统备份",
)
async def create_backup_endpoint(
    db: AsyncSession = Depends(get_db),
) -> BackupCreateResponse:
    """打包 works/ + vector_store/ 为 tar.gz,并按保留策略清理旧档。"""
    result = await backup_service.create_backup(db)
    await db.commit()
    return result


@router.post(
    "/danger/clear-works",
    response_model=ClearDataResponse,
    summary="危险操作:清空全部作品数据(保留设置与 API Key)",
)
async def clear_works_endpoint(
    db: AsyncSession = Depends(get_db),
) -> ClearDataResponse:
    """删除全部作品及向量索引,保留系统设置与 API Key。"""
    result = await backup_service.clear_all_work_data(db)
    await db.commit()
    return result


@router.get(
    "/{filename}/download",
    summary="下载备份文件",
    responses={200: {"content": {"application/gzip": {}}}},
)
async def download_backup_endpoint(filename: str) -> FileResponse:
    """下载指定备份归档。"""
    path = backup_service.get_backup_file_path(filename)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"备份不存在: {filename}",
        )
    return FileResponse(
        path=path,
        media_type="application/gzip",
        filename=path.name,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{path.name}\"; "
                f"filename*=UTF-8''{quote(path.name)}"
            )
        },
    )


@router.post(
    "/{filename}/restore",
    response_model=BackupRestoreResponse,
    summary="从指定备份恢复(建议随后重启后端)",
)
async def restore_backup_endpoint(
    filename: str,
    db: AsyncSession = Depends(get_db),
) -> BackupRestoreResponse:
    """恢复归档到磁盘;返回 requires_restart=true 提示重启。"""
    return await backup_service.restore_backup(db, filename)


@router.delete(
    "/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除指定备份",
)
async def delete_backup_endpoint(filename: str) -> None:
    """删除指定备份文件。"""
    await backup_service.delete_backup(filename)

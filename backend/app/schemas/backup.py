"""[P3.5] 系统备份 Schema"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


BackupInterval = Literal["daily", "weekly", "monthly"]


class BackupPrefs(BaseModel):
    """备份偏好(持久化到 SettingsBundle 同级的 settings 键)。"""

    auto_backup: bool = Field(default=False, description="是否启用自动备份")
    interval: BackupInterval = Field(default="daily", description="自动备份周期")
    keep_count: int = Field(default=10, ge=1, le=100, description="保留份数")


class BackupPrefsUpdate(BaseModel):
    """更新备份偏好(全部可选)。"""

    auto_backup: bool | None = None
    interval: BackupInterval | None = None
    keep_count: int | None = Field(None, ge=1, le=100)


class BackupInfo(BaseModel):
    """单条备份归档元数据。"""

    filename: str
    size_bytes: int
    created_at: datetime
    path: str


class BackupListResponse(BaseModel):
    """备份列表 + 当前偏好 + 目录信息。"""

    backup_dir: str
    prefs: BackupPrefs
    last_backup_at: datetime | None = None
    items: list[BackupInfo]


class BackupCreateResponse(BaseModel):
    """立即备份结果。"""

    backup: BackupInfo
    pruned: int = Field(0, description="本次因保留策略删除的旧备份数")


class BackupRestoreResponse(BaseModel):
    """恢复结果。"""

    filename: str
    message: str
    requires_restart: bool = True


class ClearDataResponse(BaseModel):
    """清理作品数据结果(保留 API Key / 系统设置)。"""

    deleted_works: int
    message: str

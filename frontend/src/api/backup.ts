/** [P3.5] 系统备份 + 作品导入 API */
import { http } from './client';
import { downloadBlob } from './export';

export type BackupInterval = 'daily' | 'weekly' | 'monthly';
export type ImportMode = 'create' | 'overwrite';

export interface BackupPrefs {
  auto_backup: boolean;
  interval: BackupInterval;
  keep_count: number;
}

export type BackupPrefsUpdate = Partial<BackupPrefs>;

export interface BackupInfo {
  filename: string;
  size_bytes: number;
  created_at: string;
  path: string;
}

export interface BackupListResponse {
  backup_dir: string;
  prefs: BackupPrefs;
  last_backup_at: string | null;
  items: BackupInfo[];
}

export interface BackupCreateResponse {
  backup: BackupInfo;
  pruned: number;
}

export interface BackupRestoreResponse {
  filename: string;
  message: string;
  requires_restart: boolean;
}

export interface ClearDataResponse {
  deleted_works: number;
  message: string;
}

export interface WorkImportResult {
  work_id: string;
  title: string;
  mode: ImportMode;
  chapter_count: number;
  character_count: number;
  outline_count: number;
  has_world_bible: boolean;
  message: string;
}

export const backupApi = {
  /** 列出备份与偏好 */
  list: () => http.get<BackupListResponse>('/settings/backup'),

  /** 更新偏好 */
  updatePrefs: (data: BackupPrefsUpdate) =>
    http.patch<BackupPrefs>('/settings/backup/prefs', data),

  /** 立即备份 */
  create: () => http.post<BackupCreateResponse>('/settings/backup'),

  /** 恢复 */
  restore: (filename: string) =>
    http.post<BackupRestoreResponse>(
      `/settings/backup/${encodeURIComponent(filename)}/restore`
    ),

  /** 删除 */
  remove: (filename: string) =>
    http.delete<void>(`/settings/backup/${encodeURIComponent(filename)}`),

  /** 清空全部作品 */
  clearWorks: () =>
    http.post<ClearDataResponse>('/settings/backup/danger/clear-works'),

  /** 下载备份文件到本地 */
  async download(filename: string): Promise<void> {
    const API_BASE = (import.meta.env.VITE_API_BASE || '/api/v1') as string;
    const url = `${API_BASE}/settings/backup/${encodeURIComponent(filename)}/download`;
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) {
      throw new Error(`下载失败: HTTP ${res.status}`);
    }
    const blob = await res.blob();
    downloadBlob(blob, filename);
  },
};

/**
 * 上传 JSON 作品包或 TXT 导入为新作品。
 */
export async function importWorkFile(
  file: File,
  options: { mode?: ImportMode; title?: string; genre?: string } = {}
): Promise<WorkImportResult> {
  const API_BASE = (import.meta.env.VITE_API_BASE || '/api/v1') as string;
  const form = new FormData();
  form.append('file', file);
  form.append('mode', options.mode ?? 'create');
  if (options.title) form.append('title', options.title);
  if (options.genre) form.append('genre', options.genre);

  const res = await fetch(`${API_BASE}/works/import`, {
    method: 'POST',
    body: form,
    credentials: 'include',
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(`导入失败: ${detail}`);
  }
  return (await res.json()) as WorkImportResult;
}

/** 下载作品 JSON 包 */
export async function downloadWorkPackage(workId: string, title?: string): Promise<void> {
  const API_BASE = (import.meta.env.VITE_API_BASE || '/api/v1') as string;
  const res = await fetch(`${API_BASE}/works/${workId}/package`, {
    credentials: 'include',
  });
  if (!res.ok) {
    throw new Error(`导出 JSON 包失败: HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const safe = (title || 'work').replace(/[^\w\u4e00-\u9fff-]+/g, '_').slice(0, 40);
  downloadBlob(blob, `${safe}_package.json`);
}

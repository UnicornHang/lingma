/** [P3.5] 设置 → 数据与备份面板 */
import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Button,
  InputNumber,
  Radio,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Upload,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  AlertTriangle,
  Database,
  Download,
  HardDrive,
  RefreshCw,
  RotateCcw,
  Settings,
  Trash2,
  Upload as UploadIcon,
} from 'lucide-react';

import {
  backupApi,
  importWorkFile,
  type BackupInfo,
  type BackupInterval,
  type ImportMode,
} from '@/api/backup';

/** 格式化字节为可读大小 */
function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

/** 格式化 ISO 时间为本地可读 */
function formatTime(iso: string | null | undefined): string {
  if (!iso) return '暂无';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function BackupSettings() {
  const { modal } = App.useApp();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importMode, setImportMode] = useState<ImportMode>('create');
  const [importing, setImporting] = useState(false);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['backups'],
    queryFn: () => backupApi.list(),
  });

  const createMut = useMutation({
    mutationFn: () => backupApi.create(),
    onSuccess: (res) => {
      message.success(
        `备份完成: ${res.backup.filename}` +
          (res.pruned > 0 ? `（清理 ${res.pruned} 份旧档）` : '')
      );
      void qc.invalidateQueries({ queryKey: ['backups'] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const prefsMut = useMutation({
    mutationFn: backupApi.updatePrefs,
    onSuccess: () => {
      message.success('备份偏好已保存');
      void qc.invalidateQueries({ queryKey: ['backups'] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const restoreMut = useMutation({
    mutationFn: (filename: string) => backupApi.restore(filename),
    onSuccess: (res) => {
      modal.warning({
        title: '恢复完成',
        content: res.message,
      });
      void qc.invalidateQueries({ queryKey: ['backups'] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: (filename: string) => backupApi.remove(filename),
    onSuccess: () => {
      message.success('已删除备份');
      void qc.invalidateQueries({ queryKey: ['backups'] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const clearMut = useMutation({
    mutationFn: () => backupApi.clearWorks(),
    onSuccess: (res) => {
      message.success(res.message);
      void qc.invalidateQueries({ queryKey: ['works'] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  function confirmRestore(filename: string): void {
    modal.confirm({
      title: '确认恢复此备份？',
      content:
        '将覆盖当前作品数据库与向量库。恢复前会自动再做一份安全备份。完成后建议重启后端。',
      okText: '恢复',
      okType: 'danger',
      onOk: () => restoreMut.mutateAsync(filename),
    });
  }

  function confirmDelete(filename: string): void {
    modal.confirm({
      title: '删除备份？',
      content: filename,
      okText: '删除',
      okType: 'danger',
      onOk: () => deleteMut.mutateAsync(filename),
    });
  }

  function confirmClear(): void {
    modal.confirm({
      title: '清理全部作品数据？',
      content: '将删除所有作品、章节、角色与向量索引。系统设置与 API Key 会保留。此操作不可撤销。',
      okText: '确认清理',
      okType: 'danger',
      onOk: () => clearMut.mutateAsync(),
    });
  }

  async function handleImportFile(file: File): Promise<void> {
    setImporting(true);
    try {
      const result = await importWorkFile(file, { mode: importMode });
      message.success(result.message);
      void qc.invalidateQueries({ queryKey: ['works'] });
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e));
    } finally {
      setImporting(false);
    }
  }

  const columns: ColumnsType<BackupInfo> = [
    {
      title: '文件名',
      dataIndex: 'filename',
      ellipsis: true,
    },
    {
      title: '大小',
      dataIndex: 'size_bytes',
      width: 100,
      render: (v: number) => formatBytes(v),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 180,
      render: (v: string) => formatTime(v),
    },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      render: (_, row) => (
        <Space size="small">
          <Button
            size="small"
            icon={<Download size={14} />}
            onClick={() =>
              backupApi.download(row.filename).catch((e: Error) => message.error(e.message))
            }
          >
            下载
          </Button>
          <Button
            size="small"
            icon={<RotateCcw size={14} />}
            loading={restoreMut.isPending}
            onClick={() => confirmRestore(row.filename)}
          >
            恢复
          </Button>
          <Button
            size="small"
            danger
            icon={<Trash2 size={14} />}
            onClick={() => confirmDelete(row.filename)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const prefs = data?.prefs;

  return (
    <div className="flex-1 h-full overflow-y-auto p-8 flex flex-col gap-6">
      <div>
        <h1 className="text-headline-lg font-bold text-on-surface">数据与备份</h1>
        <p className="text-body-md text-on-surface-variant mt-1">
          系统快照、作品包导入导出、危险区清理
        </p>
      </div>

      {/* 手动备份 */}
      <div className="surface-card p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2 pb-3 border-b border-outline-variant/40">
          <HardDrive size={20} className="text-primary" />
          <h2 className="text-headline-sm font-semibold text-on-surface">手动备份</h2>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <Button
            type="primary"
            icon={<Database size={16} />}
            loading={createMut.isPending}
            onClick={() => createMut.mutate()}
            data-testid="backup-create"
          >
            立即备份
          </Button>
          <Button
            icon={<RefreshCw size={16} />}
            loading={isFetching}
            onClick={() => void refetch()}
          >
            刷新列表
          </Button>
          <span className="text-body-sm text-on-surface-variant">
            上次备份：{formatTime(data?.last_backup_at)}
          </span>
        </div>
        <p className="text-body-sm text-on-surface-variant">
          备份目录：
          <Tag className="ml-1">{data?.backup_dir ?? '...'}</Tag>
        </p>
      </div>

      {/* 自动备份偏好 */}
      <div className="surface-card p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2 pb-3 border-b border-outline-variant/40">
          <Settings size={20} className="text-primary" />
          <h2 className="text-headline-sm font-semibold text-on-surface">自动备份</h2>
        </div>
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-body-md text-on-surface">启用</span>
            <Switch
              checked={prefs?.auto_backup ?? false}
              loading={prefsMut.isPending}
              onChange={(v) => prefsMut.mutate({ auto_backup: v })}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-body-md text-on-surface">周期</span>
            <Select<BackupInterval>
              style={{ width: 120 }}
              value={prefs?.interval ?? 'daily'}
              disabled={prefsMut.isPending}
              options={[
                { value: 'daily', label: '每天' },
                { value: 'weekly', label: '每周' },
                { value: 'monthly', label: '每月' },
              ]}
              onChange={(v) => prefsMut.mutate({ interval: v })}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-body-md text-on-surface">保留份数</span>
            <InputNumber
              min={1}
              max={100}
              value={prefs?.keep_count ?? 10}
              disabled={prefsMut.isPending}
              onChange={(v) => {
                if (typeof v === 'number') prefsMut.mutate({ keep_count: v });
              }}
            />
          </div>
        </div>
        <p className="text-body-sm text-on-surface-variant">
          启用后，后端会按周期自动创建 tar.gz 快照，并按保留份数清理旧档。
        </p>
      </div>

      {/* 历史备份 */}
      <div className="surface-card p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2 pb-3 border-b border-outline-variant/40">
          <Database size={20} className="text-primary" />
          <h2 className="text-headline-sm font-semibold text-on-surface">历史备份</h2>
        </div>
        <Table<BackupInfo>
          rowKey="filename"
          loading={isLoading}
          columns={columns}
          dataSource={data?.items ?? []}
          pagination={{ pageSize: 8, hideOnSinglePage: true }}
          locale={{ emptyText: '暂无备份，点击「立即备份」创建第一份' }}
          size="middle"
        />
      </div>

      {/* 作品导入 */}
      <div className="surface-card p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2 pb-3 border-b border-outline-variant/40">
          <UploadIcon size={20} className="text-primary" />
          <h2 className="text-headline-sm font-semibold text-on-surface">导入作品</h2>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <span className="text-body-md text-on-surface">导入模式</span>
          <Radio.Group
            value={importMode}
            onChange={(e) => setImportMode(e.target.value as ImportMode)}
            options={[
              { value: 'create', label: '新建' },
              { value: 'overwrite', label: '同 ID 覆盖' },
            ]}
          />
        </div>
        <Upload.Dragger
          accept=".json,.txt"
          multiple={false}
          showUploadList={false}
          disabled={importing}
          beforeUpload={(file) => {
            void handleImportFile(file);
            return false;
          }}
        >
          <p className="ant-upload-drag-icon">
            <UploadIcon size={32} className="text-primary mx-auto" />
          </p>
          <p className="text-body-md text-on-surface">
            {importing ? '导入中…' : '点击或拖拽 JSON 作品包 / TXT 到此处'}
          </p>
          <p className="text-body-sm text-on-surface-variant">
            JSON 为完整项目包；TXT 按空行分段为章节
          </p>
        </Upload.Dragger>
        <input ref={fileInputRef} type="file" className="hidden" />
      </div>

      {/* 危险区 */}
      <div className="surface-card p-6 flex flex-col gap-4 border border-error/30">
        <div className="flex items-center gap-2 pb-3 border-b border-outline-variant/40">
          <AlertTriangle size={20} className="text-error" />
          <h2 className="text-headline-sm font-semibold text-on-surface">危险区</h2>
        </div>
        <p className="text-body-sm text-on-surface-variant">
          清理全部作品数据。API Key 与系统设置不会被删除。
        </p>
        <Button
          danger
          icon={<Trash2 size={16} />}
          loading={clearMut.isPending}
          onClick={confirmClear}
          data-testid="backup-clear-works"
        >
          清理全部数据
        </Button>
      </div>
    </div>
  );
}

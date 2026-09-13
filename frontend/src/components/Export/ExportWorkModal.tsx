/** [P3.4] 作品导出 Modal —— 选格式 → 后端拉流 → 浏览器下载。 */
import { useState } from 'react';
import { Button, Checkbox, Modal, Radio, Space, Spin, Tag, Typography, message } from 'antd';
import { Download, FileText, BookOpen, AlertCircle } from 'lucide-react';

import { downloadBlob, exportWork, type ExportFormat } from '@/api/export';

const { Text } = Typography;

interface ExportWorkModalProps {
  open: boolean;
  onClose: () => void;
  workId: string;
  workTitle: string;
}

interface SuccessInfo {
  filename: string;
  chapterCount: number;
  volumeCount: number;
  byteSize: number;
}

export function ExportWorkModal({
  open,
  onClose,
  workId,
  workTitle,
}: ExportWorkModalProps) {
  const [format, setFormat] = useState<ExportFormat>('docx');
  const [includeOutline, setIncludeOutline] = useState(true);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [success, setSuccess] = useState<SuccessInfo | null>(null);

  function reset(): void {
    setErrorMsg(null);
    setSuccess(null);
    setBusy(false);
  }

  function handleClose(): void {
    if (busy) return; // 正在导出时禁止关闭
    reset();
    onClose();
  }

  async function handleExport(): Promise<void> {
    setBusy(true);
    setErrorMsg(null);
    setSuccess(null);
    try {
      const { blob, headers } = await exportWork(workId, format, {
        include_outline: includeOutline,
      });
      downloadBlob(blob, headers.filename);
      setSuccess({
        filename: headers.filename,
        chapterCount: headers.chapterCount,
        volumeCount: headers.volumeCount,
        byteSize: headers.contentLength,
      });
      message.success(`已下载 ${headers.filename}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrorMsg(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onCancel={handleClose}
      title={
        <Space>
          <Download size={18} />
          <span>导出作品</span>
        </Space>
      }
      footer={
        success ? (
          <Button type="primary" onClick={handleClose}>
            完成
          </Button>
        ) : (
          <Space>
            <Button onClick={handleClose} disabled={busy}>
              取消
            </Button>
            <Button
              type="primary"
              icon={busy ? <Spin size="small" /> : <Download size={16} />}
              onClick={handleExport}
              disabled={busy}
              data-testid="export-submit"
            >
              {busy ? '导出中...' : '开始导出'}
            </Button>
          </Space>
        )
      }
      destroyOnHidden
      maskClosable={!busy}
    >
      <div data-testid="export-work-modal">
        <Text type="secondary" className="block mb-3">
          《{workTitle}》
        </Text>

        {/* 格式选择 */}
        <div className="mb-4">
          <div className="text-body-sm text-on-surface mb-2">格式</div>
          <Radio.Group
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
            disabled={busy}
          >
            <Space direction="vertical">
              <Radio value="docx" data-testid="export-format-docx">
                <Space>
                  <FileText size={16} />
                  <span>DOCX</span>
                  <Tag color="blue">Word 兼容</Tag>
                </Space>
              </Radio>
              <Radio value="epub" data-testid="export-format-epub">
                <Space>
                  <BookOpen size={16} />
                  <span>EPUB</span>
                  <Tag color="purple">电子阅读器</Tag>
                </Space>
              </Radio>
            </Space>
          </Radio.Group>
        </div>

        {/* 分卷选项 */}
        <div className="mb-3">
          <Checkbox
            checked={includeOutline}
            onChange={(e) => setIncludeOutline(e.target.checked)}
            disabled={busy}
            data-testid="export-include-outline"
          >
            按大纲分卷(无大纲时回退为单卷)
          </Checkbox>
        </div>

        {/* 错误展示 */}
        {errorMsg && (
          <div
            className="surface-card p-3 flex items-start gap-2 mb-3"
            data-testid="export-error"
          >
            <AlertCircle size={16} className="text-error mt-0.5 shrink-0" />
            <Text type="danger" className="text-body-sm">
              {errorMsg}
            </Text>
          </div>
        )}

        {/* 成功展示 */}
        {success && (
          <div
            className="surface-card p-3"
            data-testid="export-success"
          >
            <div className="text-body-sm">
              <div className="font-medium mb-1">导出成功</div>
              <Text type="secondary" className="block">
                文件: <span className="font-mono">{success.filename}</span>
              </Text>
              <Text type="secondary" className="block">
                大小: {(success.byteSize / 1024).toFixed(1)} KB ·{' '}
                {success.chapterCount} 章
                {success.volumeCount > 1 && ` · ${success.volumeCount} 卷`}
              </Text>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

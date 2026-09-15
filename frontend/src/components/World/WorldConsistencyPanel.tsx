/** 世界观一致性检查结果面板 */
import { useEffect, useState } from 'react';
import { Alert, Button, Empty, Input, Tag } from 'antd';
import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

import {
  worldApi,
  type ConsistencyCheckResponse,
  type ConsistencyIssue,
} from '@/api/world';

interface WorldConsistencyPanelProps {
  workId: string;
  /** 有章节时优先按章节正文检查 */
  chapterId?: string;
  /** 覆盖待检文本(编辑器未保存草稿) */
  text?: string;
  autoCheck?: boolean;
}

const SEVERITY_COLOR: Record<ConsistencyIssue['severity'], string> = {
  error: 'error',
  warning: 'warning',
  info: 'processing',
};

const TYPE_LABEL: Record<ConsistencyIssue['type'], string> = {
  geography_conflict: '地理',
  faction_conflict: '势力',
  power_system_violation: '力量体系',
  timeline_conflict: '时间线',
  rule_violation: '规则',
  culture_conflict: '文化',
  other: '其他',
};

/**
 * 对照世界书展示冲突列表,支持手动复检。
 */
export function WorldConsistencyPanel({
  workId,
  chapterId,
  text,
  autoCheck = false,
}: WorldConsistencyPanelProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ConsistencyCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sample, setSample] = useState(text ?? '');

  async function runCheck(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const payloadText = (text ?? sample).trim();
      const data = await worldApi.checkConsistency(workId, {
        text: payloadText || undefined,
        chapter_id: chapterId,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '检查失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (autoCheck && workId) {
      void runCheck();
    }
    // 仅在进入面板 / 章节切换时自动跑
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoCheck, workId, chapterId]);

  return (
    <div className="flex flex-col gap-3" data-testid="world-consistency-panel">
      <div className="flex items-center justify-between">
        <span className="chip-tertiary">世界观一致性</span>
        <Button
          size="small"
          type="primary"
          loading={loading}
          icon={<ShieldAlert size={14} />}
          onClick={() => void runCheck()}
          data-testid="world-consistency-run"
        >
          {result ? '重新检查' : '开始检查'}
        </Button>
      </div>

      {!chapterId && (
        <Input.TextArea
          rows={6}
          value={sample}
          onChange={(e) => setSample(e.target.value)}
          placeholder="粘贴要检查的章节正文；留空则对世界书做内部自检"
          data-testid="world-consistency-sample"
        />
      )}

      {error && <Alert type="error" message={error} showIcon />}

      {result && (
        <>
          <div className="flex items-center gap-2 text-body-sm text-on-surface-variant">
            {result.passed ? (
              <CheckCircle2 size={16} className="text-tertiary" />
            ) : (
              <AlertTriangle size={16} className="text-error" />
            )}
            <span>{result.summary}</span>
            <Tag>{result.issue_count} 项</Tag>
            <span className="font-code-sm">{result.model_used}</span>
          </div>

          {result.world_empty && (
            <Alert
              type="info"
              showIcon
              message="世界书还是空的，先去世界观圣经补设定再检查。"
            />
          )}

          {result.issues.length === 0 && !result.world_empty ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未发现冲突" />
          ) : (
            <ul className="flex flex-col gap-2">
              {result.issues.map((issue, i) => (
                <li
                  key={`${issue.type}-${i}`}
                  className="p-3 rounded-lg bg-surface-container-lowest border border-outline-variant/40"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Tag color={SEVERITY_COLOR[issue.severity]}>
                      {issue.severity === 'error' ? '冲突' : issue.severity === 'warning' ? '警告' : '提示'}
                    </Tag>
                    <Tag>{TYPE_LABEL[issue.type]}</Tag>
                    <span className="font-code-sm text-outline">{issue.source}</span>
                  </div>
                  <p className="text-body-sm text-on-surface">「{issue.text}」</p>
                  <p className="text-body-sm text-on-surface-variant mt-1">
                    违反：{issue.rule_violated}
                  </p>
                  {issue.suggestion && (
                    <p className="text-body-sm text-primary mt-1">建议：{issue.suggestion}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {!result && !loading && !error && (
        <p className="text-body-sm text-on-surface-variant">
          对照世界书检查正文是否违反力量体系、地理或禁忌规则。
        </p>
      )}
    </div>
  );
}

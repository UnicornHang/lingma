import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  App as AntApp,
  Button,
  Empty,
  Input,
  Space,
  Switch,
  Tag,
  Typography,
} from 'antd';
import { Feather, Trash2 } from 'lucide-react';

import {
  styleMimicApi,
  type StyleMimicAnalyzeResponse,
  type StyleProfile,
} from '@/api';

const { TextArea } = Input;
const { Paragraph, Text } = Typography;

interface StyleMimicPanelProps {
  workId: string;
}

/**
 * 仿文 MVP：粘贴数章样本 → 生成风格画像 → 启用后 Writer 写前注入。
 */
export function StyleMimicPanel({ workId }: StyleMimicPanelProps) {
  const { message } = AntApp.useApp();
  const queryClient = useQueryClient();
  const [sampleText, setSampleText] = useState('');
  const [sourceLabel, setSourceLabel] = useState('');
  const [preview, setPreview] = useState<StyleMimicAnalyzeResponse | null>(null);

  const profileQuery = useQuery({
    queryKey: ['style-mimic', workId],
    queryFn: () => styleMimicApi.get(workId),
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      styleMimicApi.analyze(workId, {
        sample_text: sampleText,
        source_label: sourceLabel.trim() || undefined,
        save: true,
        enabled: true,
      }),
    onSuccess: (res) => {
      setPreview(res);
      setSampleText('');
      queryClient.invalidateQueries({ queryKey: ['style-mimic', workId] });
      message.success(
        res.used_heuristic
          ? '已生成启发式画像（未走 LLM），写前将按此风格注入'
          : '风格画像已生成并启用',
      );
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '分析失败');
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (enabled: boolean) => styleMimicApi.update(workId, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['style-mimic', workId] });
      message.success('已更新启用状态');
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '更新失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => styleMimicApi.remove(workId),
    onSuccess: () => {
      setPreview(null);
      queryClient.invalidateQueries({ queryKey: ['style-mimic', workId] });
      message.success('已清除仿文风格记忆');
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '删除失败');
    },
  });

  const profile: StyleProfile | null = profileQuery.data ?? null;
  const display = profile ?? (preview?.profile ?? null);
  const canAnalyze = sampleText.trim().length >= 200;

  return (
    <section className="surface-card p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4 pb-3 border-b border-outline-variant/30">
        <div className="flex flex-col gap-1">
          <h2 className="text-headline-sm font-semibold text-on-surface flex items-center gap-2">
            <Feather size={18} className="text-primary" />
            仿文风格记忆
          </h2>
          <Paragraph type="secondary" style={{ marginBottom: 0 }} className="text-body-sm">
            粘贴你自备的参考小说若干章，学习文笔与节奏。只存风格画像与短片段，不写入连续性账本；
            写正文时学技法，不照抄专有名词与桥段。
          </Paragraph>
        </div>
        {display && (
          <Space>
            <Text type="secondary">写前注入</Text>
            <Switch
              checked={display.enabled}
              loading={toggleMutation.isPending}
              onChange={(v) => toggleMutation.mutate(v)}
            />
          </Space>
        )}
      </div>

      {profileQuery.isLoading ? (
        <Text type="secondary">加载中…</Text>
      ) : display ? (
        <div className="flex flex-col gap-3 rounded-lg bg-surface-container/50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Tag color={display.enabled ? 'processing' : 'default'}>
              {display.enabled ? '已启用' : '已关闭'}
            </Tag>
            {display.source_label && <Tag>{display.source_label}</Tag>}
            <Text type="secondary" className="text-label-sm">
              样本约 {display.source_char_count.toLocaleString()} 字
            </Text>
          </div>
          <Paragraph style={{ marginBottom: 0 }}>{display.writing_directives}</Paragraph>
          <div className="flex flex-wrap gap-2">
            {display.portrait.avg_sentence_len && (
              <Tag>句长·{display.portrait.avg_sentence_len}</Tag>
            )}
            {display.portrait.dialogue_density && (
              <Tag>对话·{display.portrait.dialogue_density}</Tag>
            )}
            {display.portrait.narrative_pov && (
              <Tag>{display.portrait.narrative_pov}</Tag>
            )}
            {display.portrait.pacing_tags?.slice(0, 4).map((t) => (
              <Tag key={t}>{t}</Tag>
            ))}
          </div>
          {display.snippets?.length > 0 && (
            <div className="flex flex-col gap-1">
              <Text strong className="text-label-sm">
                技法片段
              </Text>
              {display.snippets.slice(0, 5).map((s, i) => (
                <Text key={`${s.tag}-${i}`} type="secondary" className="text-body-sm">
                  [{s.tag}] {s.text}
                </Text>
              ))}
            </div>
          )}
          <div>
            <Button
              danger
              size="small"
              icon={<Trash2 size={14} />}
              loading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              清除画像
            </Button>
          </div>
        </div>
      ) : (
        <Empty description="尚未生成风格画像" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}

      <div className="flex flex-col gap-3">
        <Input
          placeholder="来源标签（可选，如书名，仅作备注）"
          value={sourceLabel}
          onChange={(e) => setSourceLabel(e.target.value)}
          maxLength={200}
        />
        <TextArea
          value={sampleText}
          onChange={(e) => setSampleText(e.target.value)}
          placeholder="粘贴参考小说若干章正文（至少 200 字，建议 2000–12000 字）。请使用你有权学习的文本。"
          autoSize={{ minRows: 6, maxRows: 14 }}
          maxLength={20000}
          showCount
        />
        <div className="flex items-center justify-between gap-3">
          <Text type="secondary" className="text-label-sm">
            {canAnalyze ? '可开始分析' : `还需 ${Math.max(0, 200 - sampleText.trim().length)} 字`}
          </Text>
          <Button
            type="primary"
            loading={analyzeMutation.isPending}
            disabled={!canAnalyze}
            onClick={() => analyzeMutation.mutate()}
          >
            {display ? '重新分析并覆盖' : '分析并启用'}
          </Button>
        </div>
      </div>
    </section>
  );
}

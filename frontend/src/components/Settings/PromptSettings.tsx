/** [P4] 设置 → Prompt 模板编辑面板 */
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App, Button, Input, Switch, Tag, message } from 'antd';
import { FileCode2, RefreshCw, Save } from 'lucide-react';

import {
  promptsApi,
  type PromptAgentType,
} from '@/api/prompts';

const AGENT_ORDER: PromptAgentType[] = [
  'writer',
  'plot',
  'world',
  'character',
  'editor',
  'critic',
];

export function PromptSettings() {
  const { modal } = App.useApp();
  const qc = useQueryClient();
  const [active, setActive] = useState<PromptAgentType>('writer');
  const [draft, setDraft] = useState('');
  const [dirty, setDirty] = useState(false);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['prompt-templates'],
    queryFn: () => promptsApi.list(),
  });

  const current = items.find((i) => i.agent_type === active) ?? null;

  useEffect(() => {
    if (current && !dirty) {
      setDraft(current.system_prompt);
    }
  }, [current, dirty]);

  function selectAgent(type: PromptAgentType): void {
    if (dirty) {
      modal.confirm({
        title: '放弃未保存的修改？',
        onOk: () => {
          setDirty(false);
          setActive(type);
        },
      });
      return;
    }
    setActive(type);
  }

  const saveMut = useMutation({
    mutationFn: () =>
      promptsApi.update(active, { system_prompt: draft }),
    onSuccess: () => {
      message.success('Prompt 已保存');
      setDirty(false);
      void qc.invalidateQueries({ queryKey: ['prompt-templates'] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const enableMut = useMutation({
    mutationFn: (enabled: boolean) => promptsApi.update(active, { enabled }),
    onSuccess: (row) => {
      message.success(row.enabled ? '已启用自定义 Prompt' : '已回退到代码默认');
      void qc.invalidateQueries({ queryKey: ['prompt-templates'] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const resetMut = useMutation({
    mutationFn: () => promptsApi.reset(active),
    onSuccess: (row) => {
      message.success('已重置为内置默认');
      setDraft(row.system_prompt);
      setDirty(false);
      void qc.invalidateQueries({ queryKey: ['prompt-templates'] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  function confirmReset(): void {
    modal.confirm({
      title: '重置为内置默认？',
      content: '当前自定义内容将被覆盖，此操作不可撤销。',
      okText: '重置',
      okType: 'danger',
      onOk: () => resetMut.mutateAsync(),
    });
  }

  return (
    <div className="flex-1 h-full overflow-hidden flex flex-col">
      <div className="px-8 pt-8 pb-4">
        <h1 className="text-headline-lg font-bold text-on-surface">Prompt 模板</h1>
        <p className="text-body-md text-on-surface-variant mt-1">
          自定义 6 个 Agent 的 System Prompt。支持占位符，关闭启用后回退代码默认。
        </p>
      </div>

      <div className="flex-1 min-h-0 flex px-8 pb-8 gap-4">
        {/* Agent 列表 */}
        <aside className="w-[220px] flex-shrink-0 surface-card p-3 flex flex-col gap-1 overflow-y-auto">
          {AGENT_ORDER.map((type) => {
            const item = items.find((i) => i.agent_type === type);
            const selected = active === type;
            return (
              <button
                key={type}
                type="button"
                onClick={() => selectAgent(type)}
                className={`text-left px-3 py-2 rounded-lg transition-colors ${
                  selected
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-surface-container-high text-on-surface'
                }`}
              >
                <div className="text-label-md font-medium">
                  {item?.name ?? type}
                </div>
                <div className="flex items-center gap-1 mt-1">
                  {item?.is_customized && <Tag color="blue">已改</Tag>}
                  {item && !item.enabled && <Tag>已禁用</Tag>}
                </div>
              </button>
            );
          })}
        </aside>

        {/* 编辑区 */}
        <section className="flex-1 min-w-0 surface-card p-5 flex flex-col gap-4 overflow-hidden">
          {isLoading || !current ? (
            <div className="text-on-surface-variant">加载中…</div>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <FileCode2 size={20} className="text-primary" />
                <h2 className="text-headline-sm font-semibold text-on-surface">
                  {current.name}
                </h2>
                {current.is_customized && <Tag color="blue">相对默认已修改</Tag>}
                <div className="ml-auto flex items-center gap-2">
                  <span className="text-body-sm text-on-surface-variant">启用</span>
                  <Switch
                    checked={current.enabled}
                    loading={enableMut.isPending}
                    onChange={(v) => enableMut.mutate(v)}
                  />
                </div>
              </div>

              <p className="text-body-sm text-on-surface-variant">
                {current.description}
              </p>

              {current.variables.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-label-sm text-on-surface-variant">占位符</span>
                  {current.variables.map((v) => (
                    <Tag key={v} className="font-mono">
                      {`{{${v}}}`}
                    </Tag>
                  ))}
                </div>
              )}

              <Input.TextArea
                value={draft}
                onChange={(e) => {
                  setDraft(e.target.value);
                  setDirty(true);
                }}
                autoSize={{ minRows: 16, maxRows: 28 }}
                className="font-mono text-sm"
                data-testid="prompt-editor"
              />

              <div className="flex items-center gap-3 pt-1">
                <Button
                  type="primary"
                  icon={<Save size={16} />}
                  disabled={!dirty || draft.trim().length < 20}
                  loading={saveMut.isPending}
                  onClick={() => saveMut.mutate()}
                  data-testid="prompt-save"
                >
                  保存
                </Button>
                <Button
                  icon={<RefreshCw size={16} />}
                  loading={resetMut.isPending}
                  onClick={confirmReset}
                  data-testid="prompt-reset"
                >
                  重置默认
                </Button>
                {dirty && (
                  <span className="text-body-sm text-amber-600">有未保存修改</span>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

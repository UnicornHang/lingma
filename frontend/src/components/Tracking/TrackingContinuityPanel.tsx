import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Empty, Form, Input, Select, Tag } from 'antd';

import { charactersApi } from '@/api/characters';
import {
  trackingApi,
  type CharacterRuntimeState,
  type ForeshadowItem,
  type TrackingStateRead,
} from '@/api/tracking';
import { CharacterRuntimeEditor } from '@/components/Tracking/CharacterRuntimeEditor';

type PanelMode = 'characters' | 'foreshadows';

interface TrackingContinuityPanelProps {
  workId: string;
  outlineNodeId?: string | null;
  chapterId?: string | null;
  mode: PanelMode;
}

/** 章节侧栏：角色运行时状态 / 伏笔账本（权威在后端 JSON）。 */
export function TrackingContinuityPanel({
  workId,
  outlineNodeId,
  chapterId,
  mode,
}: TrackingContinuityPanelProps) {
  const qc = useQueryClient();
  const [form] = Form.useForm();
  const query = useQuery({
    queryKey: ['tracking', workId, outlineNodeId],
    queryFn: () => trackingApi.get(workId, outlineNodeId ?? undefined),
    enabled: !!workId,
  });

  const commitMutation = useMutation({
    mutationFn: (note: string) =>
      trackingApi.commit(workId, {
        chapter_id: chapterId ?? undefined,
        note,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tracking', workId] }),
  });

  const plantMutation = useMutation({
    mutationFn: (values: { title: string; description?: string; status?: ForeshadowItem['status'] }) =>
      trackingApi.upsertForeshadow(workId, {
        title: values.title,
        description: values.description,
        status: values.status,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tracking', workId] });
      form.resetFields();
    },
  });

  const charsQuery = useQuery({
    queryKey: ['characters', workId],
    queryFn: () => charactersApi.list(workId),
    enabled: !!workId && mode === 'characters',
  });

  const runtimeMutation = useMutation({
    mutationFn: (next: CharacterRuntimeState) =>
      trackingApi.commit(workId, {
        chapter_id: chapterId ?? undefined,
        character_updates: [
          {
            character_id: next.character_id,
            name: next.name,
            location: next.location,
            goal: next.goal,
            known_facts: next.known_facts,
            unknown_facts: next.unknown_facts,
            open_threads: next.open_threads,
          },
        ],
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tracking', workId] }),
  });

  if (query.isLoading) {
    return <p className="text-body-sm text-on-surface-variant">加载连续性账本…</p>;
  }
  if (query.error) {
    return <p className="text-body-sm text-error">{(query.error as Error).message}</p>;
  }

  const data = query.data as TrackingStateRead | undefined;
  if (!data) return <Empty description="暂无追踪数据" />;

  if (mode === 'characters') {
    const states = data.character_states;
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className="chip-tertiary">角色当前状态</span>
          <span className="font-code-sm text-outline">rev {data.revision}</span>
        </div>
        <p className="text-body-xs text-on-surface-variant">
          人设看角色卡；这里只记位置、目标、已知与未知。写正文时不得把作者真相写成角色已知。
        </p>
        {states.length === 0 ? (
          <Empty description="尚无运行时状态，从下方选择角色写入" />
        ) : (
          states.map((s) => (
            <CharacterRuntimeEditor
              key={`${s.character_id}-${data.revision}`}
              state={s}
              saving={runtimeMutation.isPending}
              onSave={(next) => runtimeMutation.mutate(next)}
            />
          ))
        )}
        <Select
          placeholder="添加角色运行时状态"
          className="w-full"
          options={(charsQuery.data?.items ?? []).map((c) => ({
            value: c.id,
            label: c.name,
          }))}
          onChange={(cid) => {
            const card = charsQuery.data?.items.find((c) => c.id === cid);
            if (!card) return;
            runtimeMutation.mutate({
              character_id: card.id,
              name: card.name,
              location: '',
              goal: '',
              known_facts: [],
              unknown_facts: [],
              open_threads: [],
            });
          }}
        />
        <Input.TextArea
          rows={2}
          placeholder="本章连续性备注（写入账本，不进全文 prompt）"
          onBlur={(e) => {
            const note = e.target.value.trim();
            if (note) commitMutation.mutate(note);
          }}
        />
        {(data.author_timeline.length > 0 || data.reader_timeline.length > 0) && (
          <div className="text-body-xs text-on-surface-variant flex flex-col gap-1">
            <div>作者真相：{data.author_timeline.map((t) => t.text).join('；') || '—'}</div>
            <div>读者已知：{data.reader_timeline.map((t) => t.text).join('；') || '—'}</div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="chip-primary">伏笔账本</span>
        <span className="font-code-sm text-outline">{data.foreshadows.length} 条</span>
      </div>
      {data.foreshadows.length === 0 ? (
        <Empty description="还没有伏笔，在下方登记" />
      ) : (
        data.foreshadows.map((fs) => (
          <div key={fs.id} className="p-2 rounded bg-surface-container-lowest text-body-sm">
            <div className="flex items-center gap-2">
              <Tag color={fs.status === 'open' ? 'processing' : fs.status === 'paid' ? 'success' : 'error'}>
                {fs.status}
              </Tag>
              <span className="font-semibold">{fs.title}</span>
            </div>
            {fs.description && <p className="mt-1 text-on-surface-variant">{fs.description}</p>}
          </div>
        ))
      )}
      <Form
        form={form}
        layout="vertical"
        onFinish={(values) => plantMutation.mutate(values)}
        initialValues={{ status: 'open' }}
      >
        <Form.Item name="title" label="伏笔标题" rules={[{ required: true, message: '请填写标题' }]}>
          <Input placeholder="如：旧玉佩来历" />
        </Form.Item>
        <Form.Item name="description" label="说明">
          <Input.TextArea rows={2} maxLength={500} />
        </Form.Item>
        <Form.Item name="status" label="状态">
          <Select
            options={[
              { value: 'open', label: '未收' },
              { value: 'paid', label: '已兑现' },
              { value: 'broken', label: '断线' },
            ]}
          />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={plantMutation.isPending}>
          写入账本
        </Button>
      </Form>
    </div>
  );
}

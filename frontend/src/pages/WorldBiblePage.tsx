import { useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { App, Spin, Empty, Form, Input, Button, Tabs, Tag } from 'antd';
import {
  ArrowLeft,
  Globe,
  Save,
  CheckCircle2,
} from 'lucide-react';

import { worldApi } from '@/api';

export default function WorldBiblePage() {
  const { id: workId } = useParams<{ id: string }>();
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm();

  const bibleQuery = useQuery({
    queryKey: ['world', workId],
    queryFn: () => worldApi.getOrCreate(workId!),
    enabled: !!workId,
  });

  const updateMutation = useMutation({
    mutationFn: (data: { raw_text?: string; geography?: Record<string, unknown>; factions?: unknown[]; power_system?: Record<string, unknown>; rules?: unknown[]; culture?: Record<string, unknown> }) =>
      worldApi.update(workId!, data),
    onSuccess: () => {
      message.success('已保存世界书');
      qc.invalidateQueries({ queryKey: ['world', workId] });
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '保存失败');
    },
  });

  useEffect(() => {
    if (bibleQuery.data) {
      form.setFieldsValue({
        raw_text: bibleQuery.data.raw_text ?? '',
      });
    }
  }, [bibleQuery.data, form]);

  if (!workId) return <Empty description="缺少作品 ID" />;
  if (bibleQuery.isLoading) {
    return <div className="flex items-center justify-center h-full"><Spin size="large" /></div>;
  }
  if (bibleQuery.error) {
    return <div className="p-8 text-error">加载失败：{(bibleQuery.error as Error).message}</div>;
  }

  const bible = bibleQuery.data!;

  const save = async () => {
    const v = await form.validateFields();
    await updateMutation.mutateAsync({ raw_text: v.raw_text ?? '' });
  };

  return (
    <div className="w-full h-full overflow-y-auto bg-surface-container-low">
      <div className="p-8 flex flex-col gap-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between">
          <Link to={`/works/${workId}`}>
            <Button type="text" icon={<ArrowLeft size={16} />}>
              返回作品
            </Button>
          </Link>
          <Button
            type="primary"
            icon={<Save size={16} />}
            loading={updateMutation.isPending}
            onClick={save}
          >
            保存
          </Button>
        </div>

        <div className="flex items-center gap-3">
          <Globe size={28} className="text-primary" />
          <h1 className="text-display font-bold text-on-surface">世界观圣经</h1>
          {bible.is_indexed && (
            <Tag icon={<CheckCircle2 size={14} />} color="success">已向量化</Tag>
          )}
        </div>

        <Tabs
          defaultActiveKey="raw"
          items={[
            {
              key: 'raw',
              label: '自然语言',
              children: (
                <Form form={form} layout="vertical">
                  <Form.Item
                    label="世界书正文"
                    name="raw_text"
                    tooltip="Writer / Critic Agent 会读取这部分作为上下文"
                  >
                    <Input.TextArea
                      rows={20}
                      placeholder={
                        '示例：\n' +
                        '## 地理\n骊珠洞天位于大骊王朝境内，是一处上古遗留的小洞天……\n\n' +
                        '## 修炼体系\n修士境界分为练气、筑基、金丹、元婴、化神……\n\n' +
                        '## 势力\n- 落魄山：陈平安的山门\n- 真武山：敌对宗门'
                      }
                      maxLength={20000}
                      showCount
                    />
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'structured',
              label: '结构化（开发中）',
              children: (
                <div className="surface-card p-6 flex flex-col gap-3">
                  <p className="text-body-md text-on-surface">
                    结构化字段（地理 / 势力 / 修炼体系 / 时间线 / 规则 / 文化）的可视化编辑器将在 P2 阶段实现，
                    目前通过 <code>GET /api/v1/works/{workId}/world</code> 直接读写 JSON。
                  </p>
                  <pre className="bg-surface-container-low p-4 rounded text-code-sm overflow-auto">
{JSON.stringify(
  {
    geography: bible.geography,
    factions: bible.factions,
    power_system: bible.power_system,
    timeline: bible.timeline,
    rules: bible.rules,
    culture: bible.culture,
  },
  null,
  2,
)}
                  </pre>
                </div>
              ),
            },
          ]}
        />
      </div>
    </div>
  );
}
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Spin,
  Empty,
  Modal,
  Form,
  Input,
  Select,
  Button,
  InputNumber,
  Radio,
  Tag,
  Card,
  Space,
  Divider,
} from 'antd';
import {
  Plus,
  Search,
  Edit,
  Trash2,
  ArrowLeft,
  Star,
  Users,
  MoreHorizontal,
  Sparkles,
  Check,
  X,
} from 'lucide-react';

import {
  charactersApi,
  type Character,
  type CharacterCard,
  type CharacterRole,
  type CharacterSuggestFocus,
} from '@/api';

const ROLE_CHIP: Record<string, string> = {
  protagonist: 'chip-primary',
  antagonist: 'chip-error',
  supporting: 'chip-tertiary',
  narrator: 'chip-secondary',
};

const ROLE_LABEL: Record<CharacterRole, string> = {
  protagonist: '主角',
  antagonist: '反派',
  supporting: '配角',
  narrator: '叙述者',
};

export default function CharactersPage() {
  const { id: workId } = useParams<{ id: string }>();
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [keyword, setKeyword] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [, setEditing] = useState<Character | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [aiCards, setAiCards] = useState<CharacterCard[]>([]);
  const [aiForm] = Form.useForm();

  const listQuery = useQuery({
    queryKey: ['characters', workId],
    queryFn: () => charactersApi.list(workId!),
    enabled: !!workId,
  });

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; role: string; raw_text?: string }) =>
      charactersApi.create({ work_id: workId!, name: payload.name, role: payload.role, raw_text: payload.raw_text ?? '' }),
    onSuccess: () => {
      message.success('已创建角色');
      qc.invalidateQueries({ queryKey: ['characters', workId] });
      setModalOpen(false);
      form.resetFields();
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '创建失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => charactersApi.delete(id),
    onSuccess: () => {
      message.success('已删除');
      qc.invalidateQueries({ queryKey: ['characters', workId] });
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '删除失败');
    },
  });

  const aiSuggestMutation = useMutation({
    mutationFn: (payload: { count: number; focus: CharacterSuggestFocus; extra_hint?: string }) =>
      charactersApi.aiSuggest(workId!, payload),
  });

  const aiAcceptMutation = useMutation({
    mutationFn: (card: CharacterCard) =>
      charactersApi.create({
        work_id: workId!,
        name: card.name,
        role: card.role,
        raw_text: card.raw_text,
        basic_info: card.basic_info as unknown as Record<string, unknown>,
        personality: card.personality as unknown as Record<string, unknown>,
        backstory: card.backstory as unknown as Record<string, unknown>,
        relationships: card.relationships as unknown[],
        arc: card.arc as unknown as Record<string, unknown>,
        voice_samples: card.voice_samples,
      }),
    onSuccess: (created) => {
      message.success(`已采纳「${created.name}」`);
      qc.invalidateQueries({ queryKey: ['characters', workId] });
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '采纳失败');
    },
  });

  const [form] = Form.useForm();

  if (!workId) return <Empty description="缺少作品 ID" />;
  if (listQuery.isLoading) {
    return <div className="flex items-center justify-center h-full"><Spin size="large" /></div>;
  }
  if (listQuery.error) {
    return <div className="p-8 text-error">加载失败：{(listQuery.error as Error).message}</div>;
  }

  const all = listQuery.data?.items ?? [];
  const filtered = keyword
    ? all.filter((c) => c.name.includes(keyword))
    : all;

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ name: '', role: 'supporting', raw_text: '' });
    setModalOpen(true);
  };

  const submit = async () => {
    try {
      const v = await form.validateFields();
      await createMutation.mutateAsync(v);
    } catch {/* noop */}
  };

  const openAi = () => {
    aiForm.resetFields();
    aiForm.setFieldsValue({ count: 3, focus: 'supporting', extra_hint: '' });
    setAiCards([]);
    setAiOpen(true);
  };

  const submitAi = async () => {
    try {
      const v = await aiForm.validateFields();
      const resp = await aiSuggestMutation.mutateAsync(v);
      if (!resp.cards.length) {
        message.warning('AI 未能生成有效角色（输出格式异常），请重试');
        return;
      }
      setAiCards(resp.cards);
      message.success(`已生成 ${resp.cards.length} 张角色建议`);
    } catch (err) {
      if (err instanceof Error) message.error(err.message);
    }
  };

  const acceptAi = async (card: CharacterCard) => {
    await aiAcceptMutation.mutateAsync(card);
    setAiCards((prev) => prev.filter((c) => c.name !== card.name));
  };

  const rejectAi = (card: CharacterCard) => {
    setAiCards((prev) => prev.filter((c) => c.name !== card.name));
  };

  return (
    <div className="w-full h-full overflow-y-auto bg-surface-container-low">
      <div className="p-8 flex flex-col gap-6 max-w-6xl mx-auto">
        <div className="flex items-center justify-between">
          <Link to={`/works/${workId}`}>
            <Button type="text" icon={<ArrowLeft size={16} />}>
              返回作品
            </Button>
          </Link>
          <Space>
            <Button icon={<Sparkles size={16} />} onClick={openAi}>
              AI 推荐
            </Button>
            <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
              新增角色
            </Button>
          </Space>
        </div>

        <div className="flex items-center gap-3">
          <Users size={28} className="text-primary" />
          <h1 className="text-display font-bold text-on-surface">角色档案</h1>
          <span className="text-body-sm text-on-surface-variant">
            {all.length} 个角色 · {all.filter((c) => c.role === 'protagonist').length} 主角
          </span>
        </div>

        {/* 搜索栏 */}
        <Input
          allowClear
          prefix={<Search size={18} className="text-outline" />}
          placeholder="按名称筛选"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="!w-72"
        />

        {filtered.length === 0 ? (
          <Empty description="该作品还没有角色档案" />
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {filtered.map((c) => (
              <CharacterCardView
                key={c.id}
                character={c}
                onDelete={() => {
                  Modal.confirm({
                    title: `确认删除角色「${c.name}」？`,
                    okType: 'danger',
                    onOk: () => deleteMutation.mutateAsync(c.id),
                  });
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* 新增角色 Modal */}
      <Modal
        title="新增角色"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={submit}
        confirmLoading={createMutation.isPending}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item label="姓名" name="name" rules={[{ required: true, min: 1, max: 100 }]}>
            <Input placeholder="如：陈平安" />
          </Form.Item>
          <Form.Item label="定位" name="role" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'protagonist', label: '主角' },
                { value: 'antagonist',  label: '反派' },
                { value: 'supporting',  label: '配角' },
                { value: 'narrator',    label: '叙事者' },
              ]}
            />
          </Form.Item>
          <Form.Item label="背景描述" name="raw_text">
            <Input.TextArea rows={4} maxLength={10000} showCount placeholder="外貌、性格、背景、口癖……" />
          </Form.Item>
        </Form>
      </Modal>

      {/* AI 推荐 Modal */}
      <Modal
        title={
          <Space>
            <Sparkles size={18} className="text-primary" />
            AI 角色设计
          </Space>
        }
        open={aiOpen}
        onCancel={() => setAiOpen(false)}
        footer={null}
        width={820}
        destroyOnClose
      >
        {aiCards.length === 0 ? (
          <Spin spinning={aiSuggestMutation.isPending} tip="AI 正在设计角色...">
            <Form form={aiForm} layout="vertical" className="!pt-2">
              <Form.Item label="生成数量" name="count" rules={[{ required: true }]}>
                <InputNumber min={1} max={10} className="!w-32" />
              </Form.Item>
              <Form.Item label="焦点" name="focus" rules={[{ required: true }]}>
                <Radio.Group
                  options={[
                    { value: 'protagonist', label: '主角' },
                    { value: 'antagonist', label: '反派' },
                    { value: 'supporting', label: '配角' },
                    { value: 'all', label: '混合' },
                  ]}
                />
              </Form.Item>
              <Form.Item label="附加要求（可选）" name="extra_hint">
                <Input.TextArea
                  rows={3}
                  maxLength={500}
                  showCount
                  placeholder="例：加一个身世神秘的女主，擅长音律"
                />
              </Form.Item>
              <Divider />
              <div className="flex justify-end">
                <Button type="primary" onClick={submitAi} loading={aiSuggestMutation.isPending}>
                  生成
                </Button>
              </div>
            </Form>
          </Spin>
        ) : (
          <div className="flex flex-col gap-3 max-h-[60vh] overflow-y-auto !pr-1">
            <div className="text-body-sm text-on-surface-variant">
              共生成 {aiCards.length} 张建议，挑选需要的角色「采纳」，其他「放弃」。
            </div>
            {aiCards.map((card) => (
              <CharacterSuggestionCard
                key={card.name}
                card={card}
                accepting={aiAcceptMutation.isPending && aiAcceptMutation.variables?.name === card.name}
                onAccept={() => acceptAi(card)}
                onReject={() => rejectAi(card)}
              />
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}

function CharacterCardView({ character, onDelete }: { character: Character; onDelete: () => void }) {
  const initial = character.name.charAt(0);
  const roleLabel = ROLE_LABEL[character.role] ?? character.role;
  const chip = ROLE_CHIP[character.role] ?? 'chip-secondary';

  return (
    <div className="surface-card p-4 flex flex-col gap-3 group">
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center text-headline-md font-bold">
          {initial}
        </div>
        <div className="flex-1 flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <h3 className="text-headline-sm font-semibold text-on-surface flex-1 truncate">
              {character.name}
            </h3>
            <Star size={16} className="text-primary" fill="currentColor" />
          </div>
          <span className={`${chip} w-fit`}>{roleLabel}</span>
        </div>
        <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity">
          <Button type="text" shape="circle" size="small" icon={<Edit size={14} />} title="编辑" />
          <Button
            type="text"
            shape="circle"
            size="small"
            danger
            icon={<Trash2 size={14} />}
            onClick={onDelete}
            title="删除"
          />
          <Button type="text" shape="circle" size="small" icon={<MoreHorizontal size={14} />} title="更多" />
        </div>
      </div>

      {character.raw_text ? (
        <p className="text-body-sm text-on-surface-variant line-clamp-3">
          {character.raw_text}
        </p>
      ) : (
        <p className="text-body-sm text-on-surface-low italic">（暂无描述）</p>
      )}

      <div className="pt-2 border-t border-outline-variant/30 flex items-center justify-between font-code-sm text-on-surface-variant">
        <span>出场 {character.appearance_count} 次</span>
        <span className={character.is_indexed ? 'text-tertiary' : 'text-outline'}>
          {character.is_indexed ? '已向量化' : '待索引'}
        </span>
      </div>
    </div>
  );
}

function CharacterSuggestionCard({
  card,
  accepting,
  onAccept,
  onReject,
}: {
  card: CharacterCard;
  accepting: boolean;
  onAccept: () => void;
  onReject: () => void;
}) {
  const focusLabel = ROLE_LABEL[card.role];
  return (
    <Card
      size="small"
      title={
        <Space>
          <span className="font-semibold text-on-surface">{card.name}</span>
          <Tag color={card.role === 'protagonist' ? 'magenta' : card.role === 'antagonist' ? 'red' : 'blue'}>
            {focusLabel}
          </Tag>
        </Space>
      }
      extra={
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<Check size={14} />}
            onClick={onAccept}
            loading={accepting}
          >
            采纳
          </Button>
          <Button size="small" icon={<X size={14} />} onClick={onReject}>
            放弃
          </Button>
        </Space>
      }
    >
      <div className="grid grid-cols-2 gap-3 text-body-sm">
        <Section title="基础信息" text={describeBasic(card)} />
        <Section title="性格" tags={card.personality.traits} />
        <Section title="身世" text={describeBackstory(card)} />
        <Section title="人物弧" text={describeArc(card)} />
        {card.relationships.length > 0 && (
          <div className="col-span-2">
            <Section title="人物关系" text={card.relationships.map((r) => `${r.target_character}（${r.relation}）：${r.dynamic}`).join('\n')} />
          </div>
        )}
        {card.voice_samples.length > 0 && (
          <div className="col-span-2">
            <Section title="代表性台词" text={card.voice_samples.map((s) => `「${s}」`).join('\n')} />
          </div>
        )}
        {card.raw_text && (
          <div className="col-span-2">
            <Section title="人设描述" text={card.raw_text} />
          </div>
        )}
      </div>
    </Card>
  );
}

function Section({ title, text, tags }: { title: string; text?: string; tags?: string[] }) {
  return (
    <div>
      <div className="text-body-xs text-on-surface-variant mb-1">{title}</div>
      {tags ? (
        <div className="flex flex-wrap gap-1">
          {tags.map((t) => (
            <Tag key={t}>{t}</Tag>
          ))}
        </div>
      ) : (
        <div className="whitespace-pre-wrap text-on-surface">{text}</div>
      )}
    </div>
  );
}

function describeBasic(card: CharacterCard): string {
  const parts: string[] = [];
  if (card.basic_info.age) parts.push(card.basic_info.age);
  if (card.basic_info.occupation) parts.push(card.basic_info.occupation);
  if (card.basic_info.appearance) parts.push(card.basic_info.appearance);
  if (card.basic_info.background) parts.push(card.basic_info.background);
  return parts.join(' · ') || '（无）';
}

function describeBackstory(card: CharacterCard): string {
  const parts: string[] = [];
  if (card.backstory.origin) parts.push(card.backstory.origin);
  if (card.backstory.key_events.length) parts.push(card.backstory.key_events.join('；'));
  if (card.backstory.secrets.length) parts.push('秘密：' + card.backstory.secrets.join('；'));
  return parts.join('\n') || '（无）';
}

function describeArc(card: CharacterCard): string {
  const parts: string[] = [];
  if (card.arc.start_state) parts.push(card.arc.start_state);
  if (card.arc.key_transformations.length) parts.push(card.arc.key_transformations.join('；'));
  if (card.arc.end_state) parts.push(card.arc.end_state);
  return parts.join(' → ') || '（无）';
}

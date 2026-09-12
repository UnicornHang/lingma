import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { App, Spin, Empty, Modal, Form, Input, Select, Button } from 'antd';
import {
  Plus,
  Search,
  Edit,
  Trash2,
  ArrowLeft,
  Star,
  Users,
  MoreHorizontal,
} from 'lucide-react';

import { charactersApi, type Character } from '@/api';

const ROLE_LABEL: Record<string, string> = {
  protagonist: '主角',
  antagonist: '反派',
  supporting: '配角',
  narrator: '叙事者',
};

const ROLE_CHIP: Record<string, string> = {
  protagonist: 'chip-primary',
  antagonist: 'chip-error',
  supporting: 'chip-tertiary',
  narrator: 'chip-secondary',
};

export default function CharactersPage() {
  const { id: workId } = useParams<{ id: string }>();
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [keyword, setKeyword] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [, setEditing] = useState<Character | null>(null);
  const [form] = Form.useForm();

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

  return (
    <div className="w-full h-full overflow-y-auto bg-surface-container-low">
      <div className="p-8 flex flex-col gap-6 max-w-6xl mx-auto">
        <div className="flex items-center justify-between">
          <Link
            to={`/works/${workId}`}
            className="inline-flex items-center gap-1 text-on-surface-variant hover:text-on-surface text-label-md"
          >
            <ArrowLeft size={16} /> 返回作品
          </Link>
          <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
            新增角色
          </Button>
        </div>

        <div className="flex items-center gap-3">
          <Users size={28} className="text-primary" />
          <h1 className="text-display font-bold text-on-surface">角色档案</h1>
          <span className="text-body-sm text-on-surface-variant">
            {all.length} 个角色 · {all.filter((c) => c.role === 'protagonist').length} 主角
          </span>
        </div>

        {/* 搜索栏 */}
        <div className="flex items-center px-3 h-9 rounded-lg border border-outline-variant/50 bg-surface-container-lowest w-72">
          <Search size={18} className="text-outline" />
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="按名称筛选"
            className="flex-1 outline-none ml-2 bg-transparent text-body-md text-on-surface"
          />
        </div>

        {filtered.length === 0 ? (
          <Empty description="该作品还没有角色档案" />
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {filtered.map((c) => (
              <CharacterCard
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
    </div>
  );
}

function CharacterCard({ character, onDelete }: { character: Character; onDelete: () => void }) {
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
          <button className="p-1 text-outline hover:text-on-surface" title="编辑">
            <Edit size={14} />
          </button>
          <button
            onClick={onDelete}
            className="p-1 text-outline hover:text-error"
            title="删除"
          >
            <Trash2 size={14} />
          </button>
          <button className="p-1 text-outline" title="更多">
            <MoreHorizontal size={14} />
          </button>
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
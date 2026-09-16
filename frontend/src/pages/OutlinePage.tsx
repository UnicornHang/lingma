import { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { App, Spin, Empty, Modal, Form, Input, Select, InputNumber, Button } from 'antd';
import {
  Plus,
  ChevronDown,
  ChevronRight,
  Trash2,
  ArrowLeft,
  Sparkles,
  Network,
  FileText,
  Pencil,
  PenLine,
  Wand2,
} from 'lucide-react';

import {
  outlineApi,
  type OutlineTreeNode,
  type OutlineNodeCreate,
  type OutlineNodeUpdate,
  type PlotChapterExpand,
} from '@/api';
import { findFirstChapterNode } from '@/utils/outline';
import { openOrCreateChapterForNode } from '@/utils/writeChapter';

/** 把多行文本拆成约束列表。 */
function splitLines(value: unknown): string[] {
  if (typeof value !== 'string') return [];
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}

export default function OutlinePage() {
  const { id: workId } = useParams<{ id: string }>();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [modalOpen, setModalOpen] = useState(false);
  const [editingNode, setEditingNode] = useState<OutlineTreeNode | null>(null);
  const [expandTarget, setExpandTarget] = useState<OutlineTreeNode | null>(null);
  const [expandSuggestion, setExpandSuggestion] = useState<PlotChapterExpand | null>(null);
  const [form] = Form.useForm();

  const treeQuery = useQuery({
    queryKey: ['outline-tree', workId],
    queryFn: () => outlineApi.tree(workId!),
    enabled: !!workId,
  });

  const createMutation = useMutation({
    mutationFn: (payload: OutlineNodeCreate) => outlineApi.create(payload),
    onSuccess: () => {
      message.success('已创建大纲节点');
      qc.invalidateQueries({ queryKey: ['outline-tree', workId] });
      setModalOpen(false);
      form.resetFields();
      setEditingNode(null);
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ nodeId, payload }: { nodeId: string; payload: OutlineNodeUpdate }) =>
      outlineApi.update(nodeId, payload),
    onSuccess: () => {
      message.success('已更新大纲节点');
      qc.invalidateQueries({ queryKey: ['outline-tree', workId] });
      setModalOpen(false);
      form.resetFields();
      setEditingNode(null);
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '更新失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (nodeId: string) => outlineApi.delete(nodeId),
    onSuccess: () => {
      message.success('已删除');
      qc.invalidateQueries({ queryKey: ['outline-tree', workId] });
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '删除失败');
    },
  });

  const writeChapterMutation = useMutation({
    mutationFn: (node: OutlineTreeNode) => openOrCreateChapterForNode(workId!, node),
    onSuccess: (chapter) => navigate(`/editor/${chapter.id}`),
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '无法打开章节');
    },
  });

  const expandMutation = useMutation({
    mutationFn: (node: OutlineTreeNode) => outlineApi.aiExpand(node.id),
    onSuccess: (resp) => {
      setExpandSuggestion(resp.suggestion);
      message.success(`细纲扩写完成（${resp.model_used}），请确认后采用`);
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '扩写失败');
      setExpandTarget(null);
      setExpandSuggestion(null);
    },
  });

  const applyExpandMutation = useMutation({
    mutationFn: async () => {
      if (!expandTarget || !expandSuggestion) {
        throw new Error('没有可采用的扩写结果');
      }
      const wc = expandSuggestion.write_constraints;
      return outlineApi.update(expandTarget.id, {
        title: expandSuggestion.title,
        summary: expandSuggestion.summary,
        beats: expandSuggestion.beats,
        characters_involved: expandSuggestion.characters_involved,
        target_word_count: expandSuggestion.target_word_count,
        write_constraints: {
          word_count_min: wc?.word_count_min ?? null,
          word_count_max: wc?.word_count_max ?? null,
          must_happen: wc?.must_happen ?? [],
          must_not_happen: wc?.must_not_happen ?? [],
          time_anchor: wc?.time_anchor ?? '',
          stop_point: wc?.stop_point ?? '',
          end_hook_debt: wc?.end_hook_debt ?? '',
        },
      });
    },
    onSuccess: () => {
      message.success('已采用扩写细纲');
      qc.invalidateQueries({ queryKey: ['outline-tree', workId] });
      setExpandTarget(null);
      setExpandSuggestion(null);
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '写入失败');
    },
  });

  const toggle = (nid: string) => setExpanded((prev) => ({ ...prev, [nid]: !prev[nid] }));

  if (!workId) return <Empty description="缺少作品 ID" />;
  if (treeQuery.isLoading) {
    return <div className="flex items-center justify-center h-full"><Spin size="large" /></div>;
  }
  if (treeQuery.error) {
    return <div className="p-8 text-error">加载失败：{(treeQuery.error as Error).message}</div>;
  }

  const tree = treeQuery.data?.nodes ?? [];
  const firstChapter = findFirstChapterNode(tree);

  const openCreate = (parent?: OutlineTreeNode) => {
    setEditingNode(null);
    form.resetFields();
    form.setFieldsValue({
      type: parent ? 'chapter' : 'volume',
      parent_id: parent?.id,
      title: '',
      summary: '',
      beats: [],
      target_word_count: 3000,
      order: 0,
      must_happen: '',
      must_not_happen: '',
      end_hook_debt: '',
    });
    setModalOpen(true);
  };

  /** 打开已有节点，回填约束锁以便补纲。 */
  const openEdit = (node: OutlineTreeNode) => {
    setEditingNode(node);
    const wc = node.write_constraints;
    form.setFieldsValue({
      type: node.type,
      parent_id: node.parent_id,
      title: node.title,
      summary: node.summary ?? '',
      target_word_count: node.target_word_count,
      order: node.order,
      must_happen: (wc?.must_happen ?? []).join('\n'),
      must_not_happen: (wc?.must_not_happen ?? []).join('\n'),
      end_hook_debt: wc?.end_hook_debt ?? '',
    });
    setModalOpen(true);
  };

  /** 触发 PlotAgent 扩写；卷纲不可扩。 */
  const openExpand = (node: OutlineTreeNode) => {
    if (node.type === 'volume') {
      message.warning('请选择章纲或节拍再扩写细纲');
      return;
    }
    setExpandTarget(node);
    setExpandSuggestion(null);
    expandMutation.mutate(node);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const mustHappen = splitLines(values.must_happen);
      const mustNot = splitLines(values.must_not_happen);
      const writeConstraints = {
        word_count_min: editingNode?.write_constraints?.word_count_min ?? null,
        word_count_max: editingNode?.write_constraints?.word_count_max ?? null,
        must_happen: mustHappen,
        must_not_happen: mustNot,
        time_anchor: editingNode?.write_constraints?.time_anchor ?? '',
        stop_point: editingNode?.write_constraints?.stop_point ?? '',
        end_hook_debt: values.end_hook_debt ?? '',
      };
      if (editingNode) {
        await updateMutation.mutateAsync({
          nodeId: editingNode.id,
          payload: {
            type: values.type,
            parent_id: values.parent_id ?? null,
            title: values.title,
            summary: values.summary ?? '',
            target_word_count: values.target_word_count ?? 3000,
            order: values.order ?? 0,
            write_constraints: writeConstraints,
          },
        });
        return;
      }
      await createMutation.mutateAsync({
        work_id: workId,
        type: values.type,
        parent_id: values.parent_id ?? null,
        title: values.title,
        summary: values.summary ?? '',
        beats: values.beats ?? [],
        target_word_count: values.target_word_count ?? 3000,
        order: values.order ?? 0,
        write_constraints: writeConstraints,
      });
    } catch {
      /* 表单校验失败 */
    }
  };

  return (
    <div className="w-full h-full overflow-y-auto bg-surface-container-low">
      <div className="p-8 flex flex-col gap-6 max-w-4xl mx-auto">
        <div className="flex items-center justify-between">
          <Link to={`/works/${workId}`}>
            <Button type="text" icon={<ArrowLeft size={16} />}>
              返回作品
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Button
              type="primary"
              icon={<PenLine size={16} />}
              loading={writeChapterMutation.isPending}
              onClick={() => {
                if (!firstChapter) {
                  message.warning('请先新增一卷章纲');
                  openCreate();
                  return;
                }
                writeChapterMutation.mutate(firstChapter);
              }}
            >
              写第 1 章
            </Button>
            <Button icon={<Plus size={16} />} onClick={() => openCreate()}>
              新增卷/章
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Network size={28} className="text-primary" />
          <h1 className="text-display font-bold text-on-surface">大纲架构</h1>
          <span className="text-body-sm text-on-surface-variant">
            {tree.length} 卷 · {countNodes(tree)} 节点
          </span>
        </div>

        {tree.length === 0 ? (
          <Empty
            description="尚未创建大纲。向导创建的作品会自带起步一卷一章；也可手动新增。"
          >
            <Button type="primary" icon={<Plus size={16} />} onClick={() => openCreate()}>
              新增卷/章
            </Button>
          </Empty>
        ) : (
          <div className="surface-card p-6 flex flex-col gap-1">
            {tree.map((node) => (
              <OutlineRow
                key={node.id}
                node={node}
                depth={0}
                expanded={expanded}
                onToggle={toggle}
                onAddChild={(parent) => openCreate(parent)}
                onEdit={openEdit}
                onExpand={openExpand}
                onWriteChapter={(node) => writeChapterMutation.mutate(node)}
                onDelete={(nid) => {
                  Modal.confirm({
                    title: '确认删除该节点？',
                    content: '将级联删除其下所有子节点',
                    okType: 'danger',
                    onOk: () => deleteMutation.mutateAsync(nid),
                  });
                }}
              />
            ))}
          </div>
        )}
      </div>

      <Modal
        title={editingNode ? `编辑 ${editingNode.title}` : '新增大纲节点'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item label="类型" name="type" rules={[{ required: true }]}>
            <Select
              disabled={!!editingNode}
              options={[
                { value: 'volume',  label: '卷' },
                { value: 'chapter', label: '章' },
                { value: 'beat',    label: '节拍' },
              ]}
            />
          </Form.Item>
          <Form.Item label="标题" name="title" rules={[{ required: true, min: 1, max: 200 }]}>
            <Input placeholder="如：第一卷·少年游 / 第 11 章 意外来客" />
          </Form.Item>
          <Form.Item label="简介" name="summary">
            <Input.TextArea rows={3} maxLength={2000} showCount />
          </Form.Item>
          <Form.Item label="目标字数" name="target_word_count">
            <InputNumber min={100} max={20000} step={100} className="w-full" />
          </Form.Item>
          <Form.Item label="排序" name="order">
            <InputNumber min={0} max={10000} className="w-full" />
          </Form.Item>
          <Form.Item
            label="必须发生"
            name="must_happen"
            tooltip="每行一条。写正文时作为约束锁，优先于写作技法。"
          >
            <Input.TextArea rows={2} placeholder="每行一条本章必须发生的变化" />
          </Form.Item>
          <Form.Item label="禁止发生" name="must_not_happen">
            <Input.TextArea rows={2} placeholder="每行一条本章禁止发生的事" />
          </Form.Item>
          <Form.Item label="章尾新债" name="end_hook_debt">
            <Input placeholder="本章结束时留给下一章的期待" />
          </Form.Item>
          <Form.Item label="父节点 ID" name="parent_id" tooltip="留空表示顶级节点">
            <Input placeholder="可选，填写已存在节点的 UUID" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={expandTarget ? `扩写细纲 · ${expandTarget.title}` : '扩写细纲'}
        open={!!expandTarget}
        onCancel={() => {
          if (expandMutation.isPending || applyExpandMutation.isPending) return;
          setExpandTarget(null);
          setExpandSuggestion(null);
        }}
        okText="采用并写入"
        cancelText="丢弃"
        onOk={() => applyExpandMutation.mutate()}
        confirmLoading={applyExpandMutation.isPending}
        okButtonProps={{ disabled: !expandSuggestion || expandMutation.isPending }}
        width={720}
        destroyOnClose
      >
        {expandMutation.isPending && !expandSuggestion ? (
          <div className="flex items-center justify-center py-10">
            <Spin tip="PlotAgent 正在扩写细纲…" />
          </div>
        ) : expandSuggestion ? (
          <ExpandPreview current={expandTarget} suggestion={expandSuggestion} />
        ) : (
          <Empty description="暂无扩写结果" />
        )}
      </Modal>
    </div>
  );
}

function ExpandPreview({
  current,
  suggestion,
}: {
  current: OutlineTreeNode | null;
  suggestion: PlotChapterExpand;
}) {
  const wc = suggestion.write_constraints;
  return (
    <div className="flex flex-col gap-4 max-h-[60vh] overflow-y-auto pr-1">
      <p className="text-body-sm text-on-surface-variant">
        以下为 PlotAgent 建议，确认后才会写入大纲。不会自动生成正文。
      </p>
      <CompareBlock label="标题" before={current?.title} after={suggestion.title} />
      <CompareBlock label="简介" before={current?.summary} after={suggestion.summary} />
      <CompareBlock
        label="节拍"
        before={(current?.beats ?? []).join('；')}
        after={(suggestion.beats ?? []).join('；')}
      />
      <CompareBlock
        label="必须发生"
        before={(current?.write_constraints?.must_happen ?? []).join('；')}
        after={(wc?.must_happen ?? []).join('；')}
      />
      <CompareBlock
        label="禁止发生"
        before={(current?.write_constraints?.must_not_happen ?? []).join('；')}
        after={(wc?.must_not_happen ?? []).join('；')}
      />
      <CompareBlock
        label="章尾新债"
        before={current?.write_constraints?.end_hook_debt}
        after={wc?.end_hook_debt}
      />
      <CompareBlock
        label="目标字数"
        before={String(current?.target_word_count ?? '')}
        after={String(suggestion.target_word_count)}
      />
    </div>
  );
}

function CompareBlock({
  label,
  before,
  after,
}: {
  label: string;
  before?: string | null;
  after?: string | null;
}) {
  return (
    <div className="rounded-lg border border-outline-variant/40 p-3 flex flex-col gap-2">
      <span className="text-label-md font-semibold text-on-surface">{label}</span>
      <div className="grid grid-cols-2 gap-3 text-body-sm">
        <div>
          <div className="text-label-sm text-on-surface-variant mb-1">当前</div>
          <p className="text-on-surface-variant whitespace-pre-wrap">{before?.trim() || '（空）'}</p>
        </div>
        <div>
          <div className="text-label-sm text-primary mb-1">建议</div>
          <p className="text-on-surface whitespace-pre-wrap">{after?.trim() || '（空）'}</p>
        </div>
      </div>
    </div>
  );
}

function OutlineRow({
  node,
  depth,
  expanded,
  onToggle,
  onAddChild,
  onEdit,
  onExpand,
  onWriteChapter,
  onDelete,
}: {
  node: OutlineTreeNode;
  depth: number;
  expanded: Record<string, boolean>;
  onToggle: (id: string) => void;
  onAddChild: (parent: OutlineTreeNode) => void;
  onEdit: (node: OutlineTreeNode) => void;
  onExpand: (node: OutlineTreeNode) => void;
  onWriteChapter: (node: OutlineTreeNode) => void;
  onDelete: (id: string) => void;
}) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = expanded[node.id] ?? depth < 1;

  return (
    <div className="flex flex-col">
      <div
        className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-surface-container group"
        style={{ paddingLeft: `${depth * 24 + 8}px` }}
      >
        <Button
          type="text"
          shape="circle"
          size="small"
          onClick={() => onToggle(node.id)}
          icon={hasChildren ? (isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />) : <span className="w-4" />}
        />
        {node.type === 'volume' && <Sparkles size={16} className="text-primary" />}
        {node.type === 'chapter' && <FileText size={16} className="text-tertiary" />}
        {node.type === 'beat' && <span className="w-4 h-4 rounded-full bg-outline/40" />}
        <span className="text-label-md text-on-surface flex-1 truncate">{node.title}</span>
        <span className="font-code-sm text-on-surface-variant">
          目标 {node.target_word_count.toLocaleString()} 字
        </span>
        <div className="flex items-center gap-1">
          {node.type === 'chapter' && (
            <Button
              type="link"
              size="small"
              icon={<PenLine size={14} />}
              onClick={() => onWriteChapter(node)}
            >
              写本章
            </Button>
          )}
          <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity">
            {node.type !== 'volume' && (
              <Button
                type="text"
                shape="circle"
                size="small"
                onClick={() => onExpand(node)}
                icon={<Wand2 size={14} />}
                title="AI 扩写细纲"
              />
            )}
            <Button
              type="text"
              shape="circle"
              size="small"
              onClick={() => onEdit(node)}
              icon={<Pencil size={14} />}
              title="编辑约束锁"
            />
            <Button
              type="text"
              shape="circle"
              size="small"
              onClick={() => onAddChild(node)}
              icon={<Plus size={14} />}
              title="新增子节点"
            />
            <Button
              type="text"
              shape="circle"
              size="small"
              danger
              onClick={() => onDelete(node.id)}
              icon={<Trash2 size={14} />}
              title="删除"
            />
          </div>
        </div>
      </div>
      {hasChildren && isExpanded && (
        <div className="flex flex-col">
          {node.children.map((child) => (
            <OutlineRow
              key={child.id}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              onToggle={onToggle}
              onAddChild={onAddChild}
              onEdit={onEdit}
              onExpand={onExpand}
              onWriteChapter={onWriteChapter}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function countNodes(tree: OutlineTreeNode[]): number {
  let total = 0;
  for (const n of tree) {
    total += 1 + (n.children ? countNodes(n.children) : 0);
  }
  return total;
}

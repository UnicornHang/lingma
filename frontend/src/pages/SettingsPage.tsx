import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Spin,
  Empty,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Button,
  Tag,
  AutoComplete,
  Tooltip,
} from 'antd';
import {
  Sliders,
  Network,
  FileText,
  Palette,
  Database,
  Info,
  Settings,
  Plus,
  Trash2,
  Edit,
  Eye,
  EyeOff,
  Power,
  RefreshCw,
} from 'lucide-react';

import {
  apiConfigsApi,
  PROVIDERS,
  AGENT_TYPES,
  type ApiConfig,
  type ApiConfigCreate,
  type ProviderValue,
} from '@/api';

const SUBNAV = [
  { to: '/settings/general', icon: Sliders, label: '常规设置' },
  { to: '/settings/llm', icon: Network, label: 'LLM API 配置', accent: true },
  { to: '/settings/writing', icon: FileText, label: '写作偏好' },
  { to: '/settings/appearance', icon: Palette, label: '外观主题' },
  { to: '/settings/backup', icon: Database, label: '数据与备份' },
  { to: '/settings/about', icon: Info, label: '关于织梦' },
];

function SubNav() {
  return (
    <aside className="w-[240px] flex-shrink-0 h-full bg-surface-container-low border-r border-outline-variant/30 overflow-y-auto p-6 flex flex-col gap-1">
      <span className="px-3 text-label-sm uppercase tracking-wider text-outline">
        系统设置
      </span>
      {SUBNAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `nav-item ${isActive ? 'nav-item-active' : ''}`
          }
        >
          <item.icon size={20} />
          <span className="text-label-md">{item.label}</span>
          {item.accent && (
            <span className="ml-auto w-2 h-2 rounded-full bg-tertiary dot-pulse" />
          )}
        </NavLink>
      ))}
    </aside>
  );
}

function SettingsPlaceholder({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="flex-1 h-full overflow-y-auto p-8 flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-headline-lg font-bold text-on-surface">{title}</h1>
          <p className="text-body-md text-on-surface-variant">{desc}</p>
        </div>
      </div>
      <div className="surface-card p-6 flex flex-col gap-4">
        <div className="flex items-center gap-1 pb-3 border-b border-outline-variant/40">
          <Settings size={20} className="text-primary" />
          <h2 className="text-headline-sm font-semibold text-on-surface">功能区</h2>
        </div>
        <div className="h-32 rounded-lg bg-surface-container-lowest border border-dashed border-outline-variant/40 flex items-center justify-center text-on-surface-low">
          详细配置项由后续子页面填充
        </div>
      </div>
    </div>
  );
}

function GeneralSettings() {
  return <SettingsPlaceholder title="常规设置" desc="个性化界面、写作与 Agent 的全局默认值，仅在本机生效。" />;
}

function WritingSettings() {
  return (
    <SettingsPlaceholder
      title="写作偏好"
      desc="管理写作预设、风格关键词与体裁受众，作用于所有 Agent 的提示词组装。"
    />
  );
}
function AppearanceSettings() {
  return <SettingsPlaceholder title="外观主题" desc="主题、密度、字体与色彩，实时预览并立即生效。" />;
}
function BackupSettings() {
  return <SettingsPlaceholder title="数据与备份" desc="查看本地数据占用、即时备份或恢复、清理不再需要的内容。" />;
}
function AboutSettings() {
  return <SettingsPlaceholder title="关于织梦" desc="项目信息、技术栈、开源协议与社区入口。" />;
}

// =================================================================
// ============== LLM API 配置 —— 真实数据版 ==============
// =================================================================

const PROVIDER_MAP = new Map(PROVIDERS.map((p) => [p.value, p]));

function providerMeta(value: string) {
  return PROVIDER_MAP.get(value as ProviderValue) ?? PROVIDERS[PROVIDERS.length - 1];
}

function LLMSettings() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ApiConfig | null>(null);
  const [revealMap, setRevealMap] = useState<Record<string, string>>({});
  const [form] = Form.useForm();

  const listQuery = useQuery({
    queryKey: ['api-configs'],
    queryFn: () => apiConfigsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: ApiConfigCreate) => apiConfigsApi.create(data),
    onSuccess: () => {
      message.success('已新增 API 配置');
      qc.invalidateQueries({ queryKey: ['api-configs'] });
      closeModal();
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof apiConfigsApi.update>[1] }) =>
      apiConfigsApi.update(id, data),
    onSuccess: () => {
      message.success('已保存');
      qc.invalidateQueries({ queryKey: ['api-configs'] });
      closeModal();
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '保存失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiConfigsApi.delete(id),
    onSuccess: () => {
      message.success('已删除');
      qc.invalidateQueries({ queryKey: ['api-configs'] });
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : '删除失败');
    },
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      name: '',
      provider: 'openai',
      api_key: '',
      base_url: '',
      model_name: 'gpt-4o-mini',
      enabled: true,
      max_context_tokens: 32000,
      cost_per_1k_input: 0,
      cost_per_1k_output: 0,
      agent_assignments: ['writer'],
    });
    setModalOpen(true);
  };

  const openEdit = (cfg: ApiConfig) => {
    setEditing(cfg);
    form.resetFields();
    form.setFieldsValue({
      name: cfg.name,
      provider: cfg.provider,
      api_key: '', // 编辑时不回填原 Key，留空表示不修改
      base_url: cfg.base_url,
      model_name: cfg.model_name,
      enabled: cfg.enabled,
      max_context_tokens: cfg.max_context_tokens,
      cost_per_1k_input: cfg.cost_per_1k_input,
      cost_per_1k_output: cfg.cost_per_1k_output,
      agent_assignments: cfg.agent_assignments,
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
    form.resetFields();
  };

  const submit = async () => {
    try {
      const v = await form.validateFields();
      const data: ApiConfigCreate = {
        name: v.name,
        provider: v.provider,
        api_key: v.api_key || undefined,
        base_url: v.base_url || undefined,
        model_name: v.model_name,
        enabled: v.enabled,
        max_context_tokens: v.max_context_tokens,
        cost_per_1k_input: v.cost_per_1k_input,
        cost_per_1k_output: v.cost_per_1k_output,
        agent_assignments: v.agent_assignments ?? [],
      };
      if (editing) {
        // 编辑时 api_key 留空 → 后端保留原值
        if (!data.api_key) delete data.api_key;
        updateMutation.mutate({ id: editing.id, data });
      } else {
        createMutation.mutate(data);
      }
    } catch {/* 表单校验失败 */}
  };

  const toggleReveal = async (cfg: ApiConfig) => {
    if (revealMap[cfg.id]) {
      setRevealMap((m) => {
        const n = { ...m };
        delete n[cfg.id];
        return n;
      });
      return;
    }
    try {
      const { api_key } = await apiConfigsApi.reveal(cfg.id);
      setRevealMap((m) => ({ ...m, [cfg.id]: api_key || '(空)' }));
    } catch (e) {
      message.error(e instanceof Error ? e.message : '获取 Key 失败');
    }
  };

  const confirmDelete = (cfg: ApiConfig) => {
    Modal.confirm({
      title: `删除「${cfg.name}」？`,
      content: '将同时解除该 Provider 与所有 Agent 的关联，已保存的章节不受影响。',
      okType: 'danger',
      onOk: () => deleteMutation.mutateAsync(cfg.id),
    });
  };

  if (listQuery.isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }
  if (listQuery.error) {
    return (
      <div className="flex-1 p-8 text-error">
        加载失败：{(listQuery.error as Error).message}
      </div>
    );
  }

  const configs = listQuery.data ?? [];
  const readyCount = configs.filter((c) => c.enabled).length;

  return (
    <div className="flex-1 h-full overflow-y-auto p-8 flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-headline-lg font-bold text-on-surface">LLM API 配置</h1>
          <p className="text-body-md text-on-surface-variant">
            接入 OpenAI / Anthropic / DeepSeek / Ollama / 自定义网关。所有密钥使用 AES-256-GCM 加密存储于本机。
          </p>
        </div>
        <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
          新增 Provider
        </Button>
      </div>

      <div className="px-4 py-3 rounded-xl bg-tertiary-container/30 border border-tertiary-container flex items-center gap-4">
        <span className="w-7 h-7 rounded-full bg-tertiary text-white flex items-center justify-center font-bold">
          ✓
        </span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-label-lg font-semibold text-on-surface">
              {readyCount} / {configs.length} 通道就绪
            </span>
            <span className="font-code-sm text-on-surface-variant">
              {configs.length === 0 ? '尚未配置任何 LLM' : 'fallback chain 由 agent_assignments 决定'}
            </span>
          </div>
          <p className="text-body-sm text-on-surface-variant mt-0.5">
            所有 API 调用均直连 Provider，无中间代理
          </p>
        </div>
      </div>

      {configs.length === 0 ? (
        <Empty
          description={
            <span className="text-body-md text-on-surface-variant">
              还没有任何 LLM Provider。点击右上「新增 Provider」开始接入。
            </span>
          }
        >
          <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
            新增第一个 Provider
          </Button>
        </Empty>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {configs.map((cfg) => (
            <ApiConfigCard
              key={cfg.id}
              cfg={cfg}
              revealedKey={revealMap[cfg.id]}
              onEdit={() => openEdit(cfg)}
              onDelete={() => confirmDelete(cfg)}
              onToggleReveal={() => toggleReveal(cfg)}
            />
          ))}
        </div>
      )}

      <Modal
        title={editing ? `编辑「${editing.name}」` : '新增 LLM Provider'}
        open={modalOpen}
        onCancel={closeModal}
        onOk={submit}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        okText={editing ? '保存' : '创建'}
        cancelText="取消"
        destroyOnClose
        centered={false}
        style={{ top: 24 }}
        width={560}
      >
        <ApiConfigForm form={form} isEdit={!!editing} />
      </Modal>
    </div>
  );
}

function ApiConfigForm({ form, isEdit }: { form: ReturnType<typeof Form.useForm>[0]; isEdit: boolean }) {
  const { message } = App.useApp();
  const [modelOptions, setModelOptions] = useState<string[]>([]);
  const [fetching, setFetching] = useState(false);
  const [modelSource, setModelSource] = useState<'api' | 'static' | null>(null);

  const fetchModels = async () => {
    try {
      const v = (await form.validateFields(['provider', 'base_url'])) as {
        provider: string;
        base_url?: string;
      };
      // 编辑模式下 api_key 留空表示不修改, 这种情况下不传 api_key, 由后端不强制要求
      let apiKey: string | undefined;
      if (!isEdit) {
        const keyField = (await form
          .validateFields(['api_key'])
          .catch(() => ({}))) as { api_key?: string };
        apiKey = keyField.api_key || undefined;
      }
      setFetching(true);
      try {
        const r = await apiConfigsApi.listModels({
          provider: v.provider,
          base_url: v.base_url || undefined,
          api_key: apiKey,
        });
        setModelOptions(r.models);
        setModelSource(r.source);
        if (r.models.length === 0) {
          message.warning(r.note ?? 'Provider 未返回任何模型');
        } else {
          message.success(
            r.source === 'static'
              ? `已加载内置静态清单 (${r.models.length} 个)`
              : `从 Provider API 拉取到 ${r.models.length} 个模型${r.note ? ` · ${r.note}` : ''}`
          );
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : '拉取失败';
        message.error(msg);
      } finally {
        setFetching(false);
      }
    } catch {
      /* 表单校验失败, 已有红字提示 */
    }
  };

  return (
    <Form form={form} layout="vertical" className="mt-2">
      <Form.Item label="备注名" name="name" rules={[{ required: true, min: 1, max: 100 }]}>
        <Input placeholder="如：主力 OpenAI / 备用 DeepSeek / 本地 Ollama" />
      </Form.Item>

      <Form.Item label="Provider" name="provider" rules={[{ required: true }]}>
        <Select
          options={PROVIDERS.map((p) => ({ value: p.value, label: p.label }))}
          onChange={(v) => {
            const meta = providerMeta(v as string);
            form.setFieldValue('base_url', meta.defaultBaseUrl);
            // 切换 Provider 时清空旧清单
            setModelOptions([]);
            setModelSource(null);
          }}
        />
      </Form.Item>

      <Form.Item
        label="API Key"
        name="api_key"
        tooltip={isEdit ? '留空表示不修改' : '将被 AES-256-GCM 加密存储'}
      >
        <Input.Password
          placeholder={isEdit ? '留空保持原值' : 'sk-...'}
          autoComplete="off"
        />
      </Form.Item>

      <Form.Item label="Base URL" name="base_url" tooltip="自定义网关或本地推理地址">
        <Input placeholder="可留空，将使用 Provider 默认值" />
      </Form.Item>

      <Form.Item
        label={
          <div className="flex items-center justify-between">
            <span>模型名</span>
            <Tooltip title={isEdit ? '编辑时若未填 Key，将尝试不带 Key 拉取' : '从 Provider API 拉取可用模型'}>
              <Button
                size="small"
                type="link"
                icon={<RefreshCw size={14} className={fetching ? 'animate-spin' : ''} />}
                onClick={fetchModels}
                loading={fetching}
                style={{ padding: 0, height: 'auto' }}
              >
                {modelOptions.length > 0 ? `刷新 (${modelOptions.length})` : '获取列表'}
              </Button>
            </Tooltip>
          </div>
        }
        name="model_name"
        rules={[{ required: true }]}
        extra={
          modelSource === 'static'
            ? '当前模型清单来自内置静态数据，Anthropic 不暴露 /models 端点'
            : modelSource === 'api'
              ? '当前模型清单来自 Provider API'
              : null
        }
      >
        <AutoComplete
          placeholder="如：gpt-4o-mini / deepseek-chat / qwen2.5:14b / MiniMax-Plus"
          options={modelOptions.map((m) => ({ value: m }))}
          filterOption={(input, option) =>
            (option?.value as string).toLowerCase().includes(input.toLowerCase())
          }
          allowClear
        />
      </Form.Item>

      <div className="grid grid-cols-2 gap-3">
        <Form.Item label="最大上下文 Tokens" name="max_context_tokens">
          <InputNumber min={1000} max={200000} step={1000} className="w-full" />
        </Form.Item>
        <Form.Item label="启用" name="enabled" valuePropName="checked">
          <Switch />
        </Form.Item>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Form.Item label="输入 ¥ / 1k tokens" name="cost_per_1k_input">
          <InputNumber min={0} step={0.001} className="w-full" />
        </Form.Item>
        <Form.Item label="输出 ¥ / 1k tokens" name="cost_per_1k_output">
          <InputNumber min={0} step={0.001} className="w-full" />
        </Form.Item>
      </div>

      <Form.Item
        label="分配给 Agent"
        name="agent_assignments"
        tooltip="勾选后，该 Provider 会用于对应 Agent 的生成任务"
      >
        <Select
          mode="multiple"
          placeholder="至少选择一个 Agent"
          options={AGENT_TYPES.map((a) => ({ value: a.value, label: a.label }))}
        />
      </Form.Item>
    </Form>
  );
}

function ApiConfigCard({
  cfg,
  revealedKey,
  onEdit,
  onDelete,
  onToggleReveal,
}: {
  cfg: ApiConfig;
  revealedKey?: string;
  onEdit: () => void;
  onDelete: () => void;
  onToggleReveal: () => void;
}) {
  const meta = providerMeta(cfg.provider);
  const assignedAgents = (cfg.agent_assignments ?? []).map((v) => {
    const a = AGENT_TYPES.find((x) => x.value === v);
    return a?.label.split('（')[0] ?? v;
  });

  return (
    <div className={`${cfg.enabled ? 'surface-card' : 'surface-card opacity-70'} p-5 flex flex-col gap-3`}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold text-headline-sm"
            style={{ background: meta.color }}
          >
            {meta.label.charAt(0)}
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-label-lg font-semibold text-on-surface">{cfg.name}</span>
              <span className="font-code-sm text-on-surface-variant">{meta.label}</span>
            </div>
            <span className="font-code-sm text-on-surface-variant">
              {cfg.model_name || '未指定模型'}
            </span>
          </div>
        </div>
        <span className={cfg.enabled ? 'chip-tertiary' : 'chip-secondary'}>
          {cfg.enabled ? '启用' : '已停用'}
        </span>
      </div>

      {/* Key */}
      <div className="flex items-center px-3 h-9 rounded-lg border border-outline-variant/50 bg-surface-container-lowest font-code-sm">
        <span className="flex-1 truncate text-on-surface">
          {revealedKey ?? cfg.masked_key ?? '(未设置)'}
        </span>
        <button
          onClick={onToggleReveal}
          className="text-outline hover:text-on-surface"
          title={revealedKey ? '隐藏' : '一次性显示明文'}
        >
          {revealedKey ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>

      {/* Base URL */}
      {cfg.base_url && (
        <div className="flex items-center px-3 h-9 rounded-lg border border-outline-variant/50 bg-surface-container-lowest font-code-sm text-on-surface-variant">
          <span className="truncate">{cfg.base_url}</span>
        </div>
      )}

      {/* Agent 分配 */}
      {assignedAgents.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-label-sm text-on-surface-variant">分配给：</span>
          {assignedAgents.map((label) => (
            <Tag key={label} color="blue" className="!m-0">
              {label}
            </Tag>
          ))}
        </div>
      )}

      {/* 成本 & 上下文 */}
      <div className="grid grid-cols-3 gap-2 font-code-sm text-on-surface-variant">
        <div className="flex flex-col">
          <span className="text-label-sm">上下文</span>
          <span className="text-on-surface">{cfg.max_context_tokens.toLocaleString()}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-label-sm">输入 ¥/1k</span>
          <span className="text-on-surface">{cfg.cost_per_1k_input.toFixed(3)}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-label-sm">输出 ¥/1k</span>
          <span className="text-on-surface">{cfg.cost_per_1k_output.toFixed(3)}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-2 pt-3 border-t border-outline-variant/30">
        <Button
          size="small"
          icon={<Edit size={14} />}
          onClick={onEdit}
        >
          编辑
        </Button>
        <Button size="small" icon={<Power size={14} />}>
          {cfg.enabled ? '停用' : '启用'}
        </Button>
        <Button
          size="small"
          danger
          icon={<Trash2 size={14} />}
          className="ml-auto"
          onClick={onDelete}
        >
          删除
        </Button>
      </div>
    </div>
  );
}

// =================================================================

export default function SettingsPage() {
  const location = useLocation();
  return (
    <div className="flex w-full h-full">
      <SubNav />
      {renderContent(location.pathname)}
    </div>
  );
}

function renderContent(pathname: string) {
  if (pathname.startsWith('/settings/llm')) return <LLMSettings />;
  if (pathname.startsWith('/settings/writing')) return <WritingSettings />;
  if (pathname.startsWith('/settings/appearance')) return <AppearanceSettings />;
  if (pathname.startsWith('/settings/backup')) return <BackupSettings />;
  if (pathname.startsWith('/settings/about')) return <AboutSettings />;
  return <GeneralSettings />;
}
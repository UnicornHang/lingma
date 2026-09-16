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
  Slider,
  Radio,
  Space,
} from 'antd';
import {
  Sliders,
  Network,
  FileText,
  FileCode2,
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
  Star,
  Check,
  X as XIcon,
} from 'lucide-react';

import {
  apiConfigsApi,
  PROVIDERS,
  AGENT_TYPES,
  settingsApi,
  stylePresetsApi,
  type ApiConfig,
  type ApiConfigCreate,
  type ProviderValue,
  type SettingsBundle,
  type StylePreset,
  type StylePresetCreate,
} from '@/api';
import { BackupSettings } from '@/components/Settings/BackupSettings';
import { PromptSettings } from '@/components/Settings/PromptSettings';

const SUBNAV = [
  { to: '/settings/general', icon: Sliders, label: '常规设置' },
  { to: '/settings/llm', icon: Network, label: 'LLM API 配置', accent: true },
  { to: '/settings/prompts', icon: FileCode2, label: 'Prompt 模板' },
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

// =================================================================
// ============== 常规设置 (GeneralSettings) ==============
// =================================================================

function GeneralSettings() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const settingsQ = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsApi.get(),
  });
  const presetsQ = useQuery({
    queryKey: ['style-presets'],
    queryFn: () => stylePresetsApi.list(),
  });
  const apisQ = useQuery({
    queryKey: ['api-configs'],
    queryFn: () => apiConfigsApi.list(),
  });

  const updateMut = useMutation({
    mutationFn: (data: Partial<SettingsBundle>) => settingsApi.update(data),
    onSuccess: () => {
      message.success('已保存');
      qc.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (e: unknown) => message.error(e instanceof Error ? e.message : '保存失败'),
  });

  if (settingsQ.isLoading || presetsQ.isLoading || apisQ.isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }
  if (settingsQ.error) {
    return <div className="flex-1 p-8 text-error">加载失败：{(settingsQ.error as Error).message}</div>;
  }

  const settings = settingsQ.data!;
  const presets = presetsQ.data ?? [];
  const apis = (apisQ.data ?? []).filter((c) => c.enabled);

  return (
    <div className="flex-1 h-full overflow-y-auto p-8 flex flex-col gap-6">
      <div>
        <h1 className="text-headline-lg font-bold text-on-surface">常规设置</h1>
        <p className="text-body-md text-on-surface-variant mt-1">
          个性化界面、写作与 Agent 的全局默认值，仅在本机生效。
        </p>
      </div>

      <SectionCard title="写作默认值" icon={<FileText size={20} className="text-primary" />}>
        <Form layout="vertical" className="!mt-2">
          <Form.Item label="默认目标字数（新建章节时自动填入）">
            <InputNumber
              min={500}
              max={20000}
              step={500}
              value={settings.default_target_word_count}
              onChange={(v) =>
                v != null && updateMut.mutate({ default_target_word_count: Number(v) })
              }
              className="!w-48"
            />
          </Form.Item>
          <Form.Item label="默认写作风格预设" tooltip="用于章节生成时的提示词风格关键词">
            <Select
              allowClear
              placeholder="未选择"
              value={settings.active_preset ?? undefined}
              onChange={(v) =>
                updateMut.mutate({ active_preset: v ? String(v) : null })
              }
              className="!w-64"
              options={presets.map((p) => ({
                value: p.name,
                label: (
                  <span>
                    {p.is_builtin && <Star size={12} className="inline mr-1 text-tertiary" />}
                    {p.name}
                  </span>
                ),
              }))}
            />
          </Form.Item>
          <Form.Item label="默认 LLM 模型" tooltip="新建章节时优先使用的 Provider/模型">
            <Select
              allowClear
              placeholder="未指定"
              value={settings.default_model ?? undefined}
              onChange={(v) =>
                updateMut.mutate({ default_model: v ? String(v) : null })
              }
              className="!w-80"
              options={apis.map((a) => ({
                value: a.model_name,
                label: `${a.name} · ${a.model_name}`,
              }))}
            />
          </Form.Item>
          <Form.Item label="自动保存间隔（秒）">
            <div className="flex items-center gap-3 !w-80">
              <Slider
                min={5}
                max={600}
                step={5}
                value={settings.auto_save_interval}
                onChangeComplete={(v) => updateMut.mutate({ auto_save_interval: v })}
                className="!flex-1"
              />
              <span className="font-code-sm text-on-surface-variant w-12 text-right">
                {settings.auto_save_interval}s
              </span>
            </div>
          </Form.Item>
        </Form>
      </SectionCard>
    </div>
  );
}

// =================================================================
// ============== 写作偏好 (WritingSettings) ==============
// =================================================================

function WritingSettings() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const presetsQ = useQuery({
    queryKey: ['style-presets'],
    queryFn: () => stylePresetsApi.list(),
  });
  const settingsQ = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsApi.get(),
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<StylePreset | null>(null);
  const [form] = Form.useForm();

  const createMut = useMutation({
    mutationFn: (data: StylePresetCreate) => stylePresetsApi.create(data),
    onSuccess: () => {
      message.success('已新建预设');
      qc.invalidateQueries({ queryKey: ['style-presets'] });
      closeModal();
    },
    onError: (e: unknown) => message.error(e instanceof Error ? e.message : '新建失败'),
  });
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<StylePresetCreate> }) =>
      stylePresetsApi.update(id, data),
    onSuccess: () => {
      message.success('已保存');
      qc.invalidateQueries({ queryKey: ['style-presets'] });
      closeModal();
    },
    onError: (e: unknown) => message.error(e instanceof Error ? e.message : '保存失败'),
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => stylePresetsApi.delete(id),
    onSuccess: () => {
      message.success('已删除');
      qc.invalidateQueries({ queryKey: ['style-presets'] });
    },
    onError: (e: unknown) => message.error(e instanceof Error ? e.message : '删除失败'),
  });
  const setDefaultMut = useMutation({
    mutationFn: (name: string | null) => settingsApi.update({ active_preset: name }),
    onSuccess: () => {
      message.success('已切换默认预设');
      qc.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (e: unknown) => message.error(e instanceof Error ? e.message : '切换失败'),
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      name: '',
      description: '',
      style_keywords: [],
      target_audience: [],
      target_word_count: 3000,
    });
    setModalOpen(true);
  };

  const openEdit = (p: StylePreset) => {
    setEditing(p);
    form.resetFields();
    form.setFieldsValue({
      name: p.name,
      description: p.description ?? '',
      style_keywords: p.style_keywords,
      target_audience: p.target_audience,
      target_word_count: p.target_word_count,
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
      const data: StylePresetCreate = {
        name: v.name,
        description: v.description || undefined,
        style_keywords: v.style_keywords ?? [],
        target_audience: v.target_audience ?? [],
        target_word_count: v.target_word_count,
      };
      if (editing) updateMut.mutate({ id: editing.id, data });
      else createMut.mutate(data);
    } catch {/* 表单校验失败 */}
  };

  const confirmDelete = (p: StylePreset) => {
    Modal.confirm({
      title: `删除预设「${p.name}」？`,
      content: '删除后引用此预设的作品将自动回退到「默认基调」。',
      okType: 'danger',
      onOk: () => deleteMut.mutateAsync(p.id),
    });
  };

  if (presetsQ.isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  const presets = presetsQ.data ?? [];
  const activePreset = settingsQ.data?.active_preset ?? null;

  return (
    <div className="flex-1 h-full overflow-y-auto p-8 flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-headline-lg font-bold text-on-surface">写作偏好</h1>
          <p className="text-body-md text-on-surface-variant">
            管理写作预设、风格关键词与体裁受众，作用于所有 Agent 的提示词组装。
          </p>
        </div>
        <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
          新建预设
        </Button>
      </div>

      <SectionCard title="风格预设列表" icon={<FileText size={20} className="text-primary" />}>
        {presets.length === 0 ? (
          <Empty description="还没有任何预设" />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {presets.map((p) => (
              <PresetCard
                key={p.id}
                preset={p}
                isDefault={activePreset === p.name}
                onEdit={() => openEdit(p)}
                onDelete={() => confirmDelete(p)}
                onSetDefault={() => setDefaultMut.mutate(p.name)}
                onClearDefault={() => setDefaultMut.mutate(null)}
              />
            ))}
          </div>
        )}
      </SectionCard>

      <Modal
        title={editing ? `编辑预设「${editing.name}」` : '新建写作风格预设'}
        open={modalOpen}
        onCancel={closeModal}
        onOk={submit}
        confirmLoading={createMut.isPending || updateMut.isPending}
        okText={editing ? '保存' : '创建'}
        cancelText="取消"
        destroyOnClose
        width={560}
      >
        <PresetForm form={form} isEdit={!!editing} />
      </Modal>
    </div>
  );
}

function PresetCard({
  preset,
  isDefault,
  onEdit,
  onDelete,
  onSetDefault,
  onClearDefault,
}: {
  preset: StylePreset;
  isDefault: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onSetDefault: () => void;
  onClearDefault: () => void;
}) {
  return (
    <div className={`surface-card p-4 flex flex-col gap-3 ${isDefault ? 'ring-2 ring-tertiary' : ''}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-label-lg font-semibold text-on-surface truncate">
              {preset.name}
            </span>
            {preset.is_builtin && (
              <Tag color="blue" className="!m-0">内置</Tag>
            )}
            {isDefault && (
              <Tag color="gold" className="!m-0">默认</Tag>
            )}
          </div>
          {preset.description && (
            <p className="text-body-sm text-on-surface-variant line-clamp-2">
              {preset.description}
            </p>
          )}
        </div>
      </div>

      {(preset.style_keywords.length > 0 || preset.target_audience.length > 0) && (
        <div className="flex flex-col gap-1.5">
          {preset.style_keywords.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-label-sm text-on-surface-variant w-14 flex-shrink-0">关键词</span>
              {preset.style_keywords.map((kw) => (
                <Tag key={kw} className="!m-0">{kw}</Tag>
              ))}
            </div>
          )}
          {preset.target_audience.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-label-sm text-on-surface-variant w-14 flex-shrink-0">受众</span>
              {preset.target_audience.map((a) => (
                <Tag key={a} color="purple" className="!m-0">{a}</Tag>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center text-body-sm text-on-surface-variant">
        <span>默认字数</span>
        <span className="ml-2 font-code-sm text-on-surface">{preset.target_word_count.toLocaleString()}</span>
      </div>

      <div className="flex items-center gap-2 pt-2 border-t border-outline-variant/30">
        <Button size="small" icon={<Edit size={14} />} onClick={onEdit}>
          编辑
        </Button>
        {isDefault ? (
          <Button size="small" icon={<XIcon size={14} />} onClick={onClearDefault}>
            取消默认
          </Button>
        ) : (
          <Button size="small" icon={<Check size={14} />} onClick={onSetDefault}>
            设为默认
          </Button>
        )}
        {!preset.is_builtin && (
          <Button
            size="small"
            danger
            icon={<Trash2 size={14} />}
            className="ml-auto"
            onClick={onDelete}
          >
            删除
          </Button>
        )}
      </div>
    </div>
  );
}

function PresetForm({ form, isEdit }: { form: ReturnType<typeof Form.useForm>[0]; isEdit: boolean }) {
  return (
    <Form form={form} layout="vertical" className="!mt-2">
      <Form.Item label="预设名称" name="name" rules={[{ required: true, min: 1, max: 100 }]}>
        <Input placeholder="如：仙侠玄幻 / 都市言情" disabled={isEdit} />
      </Form.Item>
      <Form.Item label="描述" name="description">
        <Input.TextArea rows={2} maxLength={500} showCount placeholder="一句话描述风格特征" />
      </Form.Item>
      <Form.Item
        label="风格关键词"
        name="style_keywords"
        tooltip="回车确认，将注入 WriterAgent 提示词"
      >
        <Select mode="tags" placeholder="如：热血、修仙、升级" />
      </Form.Item>
      <Form.Item label="目标读者" name="target_audience" tooltip="如：男频 / 女频 / 不限">
        <Select mode="tags" placeholder="回车确认多个标签" />
      </Form.Item>
      <Form.Item label="默认目标字数" name="target_word_count">
        <InputNumber min={500} max={20000} step={500} className="!w-full" />
      </Form.Item>
    </Form>
  );
}

// =================================================================
// ============== 外观主题 (AppearanceSettings) ==============
// =================================================================

function AppearanceSettings() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const settingsQ = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsApi.get(),
  });

  const updateMut = useMutation({
    mutationFn: (data: Partial<SettingsBundle>) => settingsApi.update(data),
    onSuccess: () => {
      message.success('已保存');
      qc.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (e: unknown) => message.error(e instanceof Error ? e.message : '保存失败'),
  });

  if (settingsQ.isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }
  const settings = settingsQ.data!;

  const update = (patch: Partial<SettingsBundle>) => updateMut.mutate(patch);

  return (
    <div className="flex-1 h-full overflow-y-auto p-8 flex flex-col gap-6">
      <div>
        <h1 className="text-headline-lg font-bold text-on-surface">外观主题</h1>
        <p className="text-body-md text-on-surface-variant mt-1">
          主题、密度、字体与色彩，实时预览并立即生效。
        </p>
      </div>

      <SectionCard title="主题" icon={<Palette size={20} className="text-primary" />}>
        <Form layout="vertical" className="!mt-2">
          <Form.Item label="配色方案">
            <Radio.Group
              value={settings.theme}
              onChange={(e) => update({ theme: e.target.value })}
              optionType="button"
            >
              <Radio.Button value="light">浅色</Radio.Button>
              <Radio.Button value="dark">深色</Radio.Button>
              <Radio.Button value="system">跟随系统</Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.Item label="界面密度">
            <Radio.Group
              value={settings.density}
              onChange={(e) => update({ density: e.target.value })}
              optionType="button"
            >
              <Radio.Button value="comfortable">舒适</Radio.Button>
              <Radio.Button value="compact">紧凑</Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.Item label="语言">
            <Select
              value={settings.language}
              onChange={(v) => update({ language: String(v) })}
              className="!w-48"
              options={[
                { value: 'zh-CN', label: '简体中文' },
                { value: 'en-US', label: 'English (US)' },
              ]}
            />
          </Form.Item>

          <Form.Item label={`字体大小（${settings.font_size}px）`}>
            <div className="flex items-center gap-3 !w-80">
              <Slider
                min={10}
                max={24}
                value={settings.font_size}
                onChangeComplete={(v) => update({ font_size: v })}
                className="!flex-1"
              />
              <span className="font-code-sm text-on-surface-variant w-10 text-right">
                {settings.font_size}px
              </span>
            </div>
          </Form.Item>
        </Form>
      </SectionCard>
    </div>
  );
}

// =================================================================
// ============== 关于 (AboutSettings) ==============
// =================================================================

function AboutSettings() {
  return (
    <div className="flex-1 h-full overflow-y-auto p-8 flex flex-col gap-6">
      <div>
        <h1 className="text-headline-lg font-bold text-on-surface">关于织梦</h1>
        <p className="text-body-md text-on-surface-variant mt-1">
          AI 协同长篇小说创作平台 · 一人即一工作室
        </p>
      </div>

      <SectionCard title="项目信息" icon={<Info size={20} className="text-primary" />}>
        <Space direction="vertical" size="middle" className="!w-full">
          <InfoRow label="项目代号" value="织梦 (ZhiMeng)" />
          <InfoRow label="版本" value="v0.1.0-beta" />
          <InfoRow label="Git 提交" value="main · latest" />
          <InfoRow label="构建日期" value="2026-09" />
        </Space>
      </SectionCard>

      <SectionCard title="技术栈" icon={<Settings size={20} className="text-primary" />}>
        <div className="grid grid-cols-2 gap-3 text-body-md">
          <InfoRow label="前端" value="React + Vite + TypeScript + Ant Design" />
          <InfoRow label="后端" value="FastAPI + SQLAlchemy 2.0 + LangGraph" />
          <InfoRow label="数据库" value="SQLite (aiosqlite)" />
          <InfoRow label="向量记忆" value="chromadb + sentence-transformers (bge-small-zh-v1.5)" />
          <InfoRow label="LLM 协议" value="OpenAI / Anthropic / Ollama / 自定义" />
          <InfoRow label="Editor" value="TipTap (ProseMirror)" />
        </div>
      </SectionCard>

      <SectionCard title="核心 Agent" icon={<Network size={20} className="text-primary" />}>
        <div className="flex flex-wrap gap-2">
          {AGENT_TYPES.map((a) => (
            <Tag key={a.value} color="blue">{a.label}</Tag>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="许可" icon={<Info size={20} className="text-primary" />}>
        <p className="text-body-md text-on-surface-variant">
          本仓库采用 AGPL-3.0 开源协议。商业使用请联系作者授权。
        </p>
      </SectionCard>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-label-sm text-on-surface-variant w-20 flex-shrink-0">
        {label}
      </span>
      <span className="font-code-sm text-on-surface">{value}</span>
    </div>
  );
}

// =================================================================
// ============== 通用组件 ==============
// =================================================================

function SectionCard({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="surface-card p-6 flex flex-col gap-4">
      <div className="flex items-center gap-1 pb-3 border-b border-outline-variant/40">
        {icon}
        <h2 className="text-headline-sm font-semibold text-on-surface">{title}</h2>
      </div>
      {children}
    </div>
  );
}

// =================================================================
// ============== LLM API 配置 (保持原有实现) ==============
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
      api_key: '',
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
      /* 表单校验失败 */
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

      {cfg.base_url && (
        <div className="flex items-center px-3 h-9 rounded-lg border border-outline-variant/50 bg-surface-container-lowest font-code-sm text-on-surface-variant">
          <span className="truncate">{cfg.base_url}</span>
        </div>
      )}

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
  if (pathname.startsWith('/settings/prompts')) return <PromptSettings />;
  if (pathname.startsWith('/settings/writing')) return <WritingSettings />;
  if (pathname.startsWith('/settings/appearance')) return <AppearanceSettings />;
  if (pathname.startsWith('/settings/backup')) return <BackupSettings />;
  if (pathname.startsWith('/settings/about')) return <AboutSettings />;
  return <GeneralSettings />;
}
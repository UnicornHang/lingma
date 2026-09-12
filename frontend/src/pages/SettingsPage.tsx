import { NavLink, useLocation } from 'react-router-dom';
import {
  Sliders,
  Network,
  FileText,
  Palette,
  Database,
  Info,
  Settings,
  Key,
  Eye,
  Trash2,
} from 'lucide-react';

const SUBNAV = [
  { to: '/settings/general',    icon: Sliders,    label: '常规设置' },
  { to: '/settings/llm',        icon: Network,    label: 'LLM API 配置', accent: true },
  { to: '/settings/writing',    icon: FileText,   label: '写作偏好' },
  { to: '/settings/appearance', icon: Palette,    label: '外观主题' },
  { to: '/settings/backup',     icon: Database,   label: '数据与备份' },
  { to: '/settings/about',      icon: Info,       label: '关于灵码' },
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
  return (
    <SettingsPlaceholder
      title="常规设置"
      desc="个性化界面、写作与 Agent 的全局默认值，仅在本机生效。"
    />
  );
}

function LLMSettings() {
  const location = useLocation();
  return (
    <div className="flex-1 h-full overflow-y-auto p-8 flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-headline-lg font-bold text-on-surface">
            LLM API 配置
          </h1>
          <p className="text-body-md text-on-surface-variant">
            接入 OpenAI / Anthropic / DeepSeek / Ollama / 自定义网关。所有密钥使用 AES-256-GCM 加密存储于本机。
          </p>
        </div>
        <button className="flex items-center gap-1 px-3 py-2 rounded-lg bg-primary text-white text-label-md font-medium hover:bg-primary-hover">
          <span>+ 新增 Provider</span>
        </button>
      </div>

      <div className="px-4 py-3 rounded-xl bg-tertiary-container/30 border border-tertiary-container flex items-center gap-4">
        <span className="w-7 h-7 rounded-full bg-tertiary text-white flex items-center justify-center font-bold">✓</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-label-lg font-semibold text-on-surface">3 / 4 通道就绪</span>
            <span className="font-code-sm text-on-surface-variant">
              fallback chain: deepseek → anthropic → ollama(local)
            </span>
          </div>
          <p className="text-body-sm text-on-surface-variant mt-0.5">
            所有 API 调用均直连 Provider，无中间代理
          </p>
        </div>
        <button className="px-3 py-1.5 rounded-lg bg-primary-container text-on-primary-container text-label-md font-medium">
          测试全部
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="surface-card-active p-6 flex flex-col gap-4">
          <ProviderCardHeader color="#10A37F" letter="O" name="OpenAI" status="ready" />
          <ProviderApiKey value="sk-proj-••••••••••••••••••••••••" />
          <ProviderModels items={['gpt-5', 'gpt-4o', 'o3-mini', '+ 4']} />
          <ProviderActions />
        </div>
        <div className="surface-card p-6 flex flex-col gap-4">
          <ProviderCardHeader color="#CB785C" letter="A" name="Anthropic" status="ready" />
          <ProviderApiKey value="sk-ant-••••••••••••••••••••••••" />
          <ProviderModels items={['claude-opus-5', 'claude-sonnet-5', 'claude-haiku-4.5']} />
          <ProviderActions />
        </div>
        <div className="surface-card p-6 flex flex-col gap-4">
          <ProviderCardHeader color="#4D8AFF" letter="D" name="DeepSeek" status="ready" />
          <ProviderApiKey value="sk-••••••••••••••••••••••••" />
          <ProviderModels items={['deepseek-chat', 'deepseek-coder']} />
          <ProviderActions />
        </div>
        <div className="surface-card p-6 flex flex-col gap-4">
          <ProviderCardHeader color="#00662B" letter="L" name="Ollama (本地)" status="down" />
          <ProviderBaseUrl value="http://127.0.0.1:11434" />
          <p className="px-3 py-2 rounded-lg bg-tertiary-container/20 text-body-sm text-on-surface-variant">
            已下载模型：qwen2.5:14b · llama3.1:8b · nomic-embed-text
          </p>
          <ProviderActions />
        </div>
      </div>

      <div className="text-body-sm text-on-surface-low">
        当前路径：<code>{location.pathname}</code>
      </div>
    </div>
  );
}

function ProviderCardHeader({
  color, letter, name, status,
}: { color: string; letter: string; name: string; status: 'ready' | 'down' }) {
  return (
    <div className="flex items-start justify-between">
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold"
          style={{ background: color }}
        >
          {letter}
        </div>
        <div className="flex flex-col">
          <span className="text-label-lg font-semibold text-on-surface">{name}</span>
          <span className="font-code-sm text-on-surface-variant">
            {name.toLowerCase().replace(/[^a-z]/g, '')}.com
          </span>
        </div>
      </div>
      <span
        className={
          status === 'ready'
            ? 'chip-tertiary flex items-center gap-1'
            : 'chip-secondary flex items-center gap-1'
        }
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            status === 'ready' ? 'bg-tertiary' : 'bg-outline'
          }`}
        />
        {status === 'ready' ? '就绪' : '未检测'}
      </span>
    </div>
  );
}

function ProviderApiKey({ value }: { value: string }) {
  return (
    <div className="flex items-center px-3 h-9 rounded-lg border border-outline-variant/50 bg-surface-container-lowest font-code-md text-code-md">
      <Key size={18} className="text-outline" />
      <span className="flex-1 ml-2 truncate text-on-surface">{value}</span>
      <button className="text-outline hover:text-on-surface">
        <Eye size={18} />
      </button>
    </div>
  );
}

function ProviderBaseUrl({ value }: { value: string }) {
  return (
    <div className="flex items-center px-3 h-9 rounded-lg border border-outline-variant/50 bg-surface-container-lowest font-code-md text-code-md text-on-surface">
      <span>{value}</span>
    </div>
  );
}

function ProviderModels({ items }: { items: string[] }) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      <span className="text-label-sm text-on-surface-variant">已启用模型：</span>
      {items.map((m) => (
        <span key={m} className="chip-primary">
          {m}
        </span>
      ))}
    </div>
  );
}

function ProviderActions() {
  return (
    <div className="flex items-center gap-2 mt-2 pt-3 border-t border-outline-variant/30">
      <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-container text-on-surface text-label-md hover:bg-surface-container-high">
        高级
      </button>
      <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-container text-on-surface text-label-md hover:bg-surface-container-high">
        测试连通
      </button>
      <button className="ml-auto text-outline hover:text-error">
        <Trash2 size={20} />
      </button>
    </div>
  );
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
  return (
    <SettingsPlaceholder
      title="外观主题"
      desc="主题、密度、字体与色彩，实时预览并立即生效。"
    />
  );
}

function BackupSettings() {
  return (
    <SettingsPlaceholder
      title="数据与备份"
      desc="查看本地数据占用、即时备份或恢复、清理不再需要的内容。"
    />
  );
}

function AboutSettings() {
  return (
    <SettingsPlaceholder
      title="关于灵码"
      desc="项目信息、技术栈、开源协议与社区入口。"
    />
  );
}

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
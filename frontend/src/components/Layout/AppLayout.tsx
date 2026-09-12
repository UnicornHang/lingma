import { Outlet, Link, useLocation, NavLink } from 'react-router-dom';
import { Input, Tooltip } from 'antd';
import {
  BookOpen,
  PlusCircle,
  Edit3,
  GitBranch,
  Users,
  Globe,
  Settings as SettingsIcon,
  HelpCircle,
  Search,
  Download,
  Bell,
  User,
  Sparkles,
} from 'lucide-react';

import { useUIStore } from '@/stores/useUIStore';

// 侧边栏导航分组
const NAV_GROUPS = [
  {
    label: '创作空间',
    items: [
      { to: '/works', icon: BookOpen, label: '作品库' },
      { to: '/works/new', icon: PlusCircle, label: '新建向导' },
      { to: '/editor', icon: Edit3, label: '章节编辑' },
    ],
  },
  {
    label: '作品设定',
    items: [
      { to: '/outline', icon: GitBranch, label: '大纲架构' },
      { to: '/characters', icon: Users, label: '角色档案' },
      { to: '/world', icon: Globe, label: '世界观圣经' },
    ],
  },
];

const BOTTOM_NAV = [
  { to: '/settings', icon: SettingsIcon, label: '系统设置' },
  { to: '/help', icon: HelpCircle, label: '使用文档' },
];

export function AppLayout() {
  const location = useLocation();
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed);

  // 面包屑（从 path 推断）
  const breadcrumb = deriveBreadcrumb(location.pathname);

  return (
    <div className="app-shell">
      {/* ===== Sidebar 240px ===== */}
      <aside
        className="app-sidebar select-none"
        style={{ display: sidebarCollapsed ? 'none' : 'flex' }}
      >
        <div className="flex flex-col flex-1 min-h-0">
          {/* Logo */}
          <div className="px-6 py-6 flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-sm">
              <Sparkles size={22} className="text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-headline-sm font-semibold tracking-tight text-on-surface">
                灵码·LingMa
              </span>
              <span className="chip-secondary mt-0.5">v0.2 本地版</span>
            </div>
          </div>

          {/* 当前作品卡 */}
          <div className="mx-6 mb-4 p-3 surface-card">
            <div className="flex items-center justify-between mb-1">
              <span className="text-label-sm text-on-surface-variant">当前作品</span>
              <span className="font-code-sm text-tertiary font-medium">35.2万字</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-headline-sm font-semibold text-primary truncate">
                剑来·前传
              </span>
              <BookOpen size={18} className="text-primary" />
            </div>
          </div>

          {/* 导航分组 */}
          <nav className="flex flex-col gap-4 px-4 overflow-y-auto flex-1">
            {NAV_GROUPS.map((group) => (
              <div key={group.label} className="flex flex-col gap-1">
                <span className="px-3 text-label-sm uppercase tracking-wider text-outline">
                  {group.label}
                </span>
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/works'}
                    className={({ isActive }) =>
                      `nav-item ${isActive ? 'nav-item-active' : ''}`
                    }
                  >
                    <item.icon size={20} />
                    <span className="text-label-md">{item.label}</span>
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
        </div>

        {/* 底部 */}
        <div className="p-4 flex flex-col gap-1 border-t border-outline-variant/30">
          {BOTTOM_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'nav-item-active' : ''}`
              }
            >
              <item.icon size={20} />
              <span className="text-label-md">{item.label}</span>
            </NavLink>
          ))}
          <div className="mt-2 px-2 py-1.5 rounded-lg bg-surface-container-high/60 border border-outline-variant/40 flex items-center gap-2">
            <span className="dot-pulse" />
            <span className="font-code-sm text-on-surface-variant truncate">
              127.0.0.1:8000
            </span>
          </div>
        </div>
      </aside>

      {/* ===== Main column ===== */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header 64px */}
        <header className="app-header">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 text-on-surface-variant text-label-md">
              {breadcrumb.map((b, i) => (
                <span key={i} className="flex items-center gap-1">
                  {i > 0 && <span className="text-outline">/</span>}
                  <span className={i === breadcrumb.length - 1 ? 'text-on-surface font-semibold' : ''}>
                    {b}
                  </span>
                </span>
              ))}
            </div>
            <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-surface-container border border-outline-variant/30">
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary" />
              <span className="text-label-sm text-on-surface-variant">
                本地离线 (SQLite + Chroma)
              </span>
            </div>
          </div>

          <div className="flex-1 max-w-xl mx-8">
            <Input
              prefix={<Search size={18} className="text-outline" />}
              placeholder="搜索作品、章节、角色或设定 (Cmd+K)"
              className="rounded-lg"
              allowClear
            />
          </div>

          <div className="flex items-center gap-4">
            <Tooltip title="本月推理费用 ¥42.60 · 节省 92%">
              <div className="hidden xl:flex items-center gap-1 px-3 py-1 bg-surface-container-low rounded-lg border border-outline-variant/30">
                <span className="text-label-sm text-on-surface-variant">本月推理:</span>
                <span className="font-code-sm font-semibold text-primary">¥42.60</span>
                <span className="text-label-sm text-tertiary">(节省92%)</span>
              </div>
            </Tooltip>
            <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-container-lowest border border-outline-variant/50 text-on-surface text-label-md hover:bg-surface-container-high transition-colors">
              <Download size={18} />
              <span>导出</span>
            </button>
            <Tooltip title="通知">
              <button className="relative p-1 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container-high transition-colors">
                <Bell size={22} />
                <span className="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-error" />
              </button>
            </Tooltip>
            <Link to="/settings" className="p-1 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container-high transition-colors">
              <SettingsIcon size={22} />
            </Link>
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              <User size={18} className="text-white" />
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function deriveBreadcrumb(pathname: string): string[] {
  const map: Record<string, string> = {
    '': '启动页',
    'works': '作品库',
    'works/new': '新建作品',
    'editor': '章节编辑',
    'outline': '大纲架构',
    'characters': '角色档案',
    'world': '世界观圣经',
    'settings': '系统设置',
    'settings/general': '系统设置',
    'settings/writing': '系统设置',
    'settings/appearance': '系统设置',
    'settings/backup': '系统设置',
    'settings/llm': '系统设置',
    'settings/about': '系统设置',
    'help': '使用文档',
  };
  const segments = pathname.split('/').filter(Boolean);
  if (segments.length === 0) return ['灵码工作台', '启动页'];
  const trail: string[] = ['灵码工作台'];
  let acc = '';
  for (const s of segments) {
    acc += '/' + s;
    const lbl = map[s] ?? map[acc.slice(1)] ?? s;
    if (!trail.includes(lbl)) trail.push(lbl);
  }
  return trail;
}
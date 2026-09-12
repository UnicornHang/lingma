# 灵码 (LingMa) — 前端开发需求文档

> 项目代号：**LingMa Novel Studio**
> 文档版本：v1.0
> 文档日期：2026-09-10
> 适用模块：**前端应用（Frontend）**
> 技术栈：React 18 + Vite + TypeScript + TipTap + Ant Design 5 + Tailwind CSS + Zustand
> 配套文档：[PRD.md](PRD.md) · [BACKEND_REQUIREMENTS.md](BACKEND_REQUIREMENTS.md)

---

## 目录

1. [概述](#1-概述)
2. [技术栈与依赖](#2-技术栈与依赖)
3. [设计系统](#3-设计系统)
4. [信息架构与路由](#4-信息架构与路由)
5. [状态管理](#5-状态管理)
6. [核心页面详述](#6-核心页面详述)
7. [富文本编辑器](#7-富文本编辑器)
8. [AI 交互组件](#8-ai-交互组件)
9. [WebSocket 客户端](#9-websocket-客户端)
10. [API 客户端层](#10-api-客户端层)
11. [国际化与主题](#11-国际化与主题)
12. [性能优化](#12-性能优化)
13. [错误处理与可观测性](#13-错误处理与可观测性)
14. [无障碍与兼容性](#14-无障碍与兼容性)
15. [测试规范](#15-测试规范)
16. [部署方案](#16-部署方案)
17. [开发里程碑](#17-开发里程碑)
18. [附录](#附录)

---

## 1. 概述

### 1.1 前端定位

LingMa 前端是用户与 AI 创作系统的唯一接触面，承担以下职责：
- **可视化呈现**：作品库、大纲树、富文本、AI 对话面板
- **交互编排**：引导用户完成"创建作品 → 设定 → 大纲 → 章节"的完整流程
- **实时反馈**：WebSocket 流式接收 AI 生成内容、审校批注
- **本地优先**：所有数据本地存储，无外部追踪

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **专业而不失温度** | 类 Notion 清爽感 + 创作软件工具感 |
| **AI 隐于幕后** | AI 能力通过侧边栏、悬浮按钮呈现，不打断创作流 |
| **键盘优先** | 重度作者依赖快捷键 |
| **响应即时** | 所有操作 < 100ms 反馈 |
| **离线可用** | 已加载数据本地保留，弱网/断网可继续浏览 |

### 1.3 与后端的边界

- 前端**不直接**调用任何 LLM API
- 前端**不持久化**核心数据（仅缓存 UI 状态）
- 所有业务数据通过 REST/WebSocket 与后端交互

---

## 2. 技术栈与依赖

### 2.1 核心技术栈

| 类别 | 选型 | 版本 | 理由 |
|------|------|------|------|
| 框架 | React | 18.3+ | 生态成熟、并发渲染 |
| 构建 | Vite | 5.2+ | 启动快、HMR |
| 语言 | TypeScript | 5.4+ | 类型安全 |
| UI 库 | Ant Design | 5.18+ | 企业级、组件丰富 |
| 样式 | Tailwind CSS | 3.4+ | 灵活、可定制 |
| 状态管理 | Zustand | 4.5+ | 轻量、TS 友好 |
| 路由 | React Router | 6.23+ | 标准方案 |
| 富文本 | TipTap | 2.4+ | 强大、可扩展 |
| 图表 | ECharts | 5.5+ | 数据可视化 |
| HTTP 客户端 | Axios | 1.7+ | 拦截器完善 |
| WebSocket | 原生 + 自封装 | — | 无需额外库 |
| 表单 | React Hook Form | 7.51+ | 高性能 |
| 校验 | Zod | 3.23+ | TS 友好 |
| 国际化 | react-i18next | 14.1+ | 标准方案 |
| 图标 | Lucide React | 0.379+ | 简洁现代 |
| 代码高亮 | Shiki | 1.6+ | 编辑器内代码块 |
| 测试 | Vitest + React Testing Library | latest | Vite 生态 |
| E2E | Playwright | 1.44+ | 跨浏览器 |
| Lint | ESLint + Prettier | latest | 代码质量 |

### 2.2 package.json（关键依赖）

```json
{
  "name": "lingma-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx",
    "test": "vitest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "@tiptap/react": "^2.4.0",
    "@tiptap/starter-kit": "^2.4.0",
    "@tiptap/extension-collaboration": "^2.4.0",
    "antd": "^5.18.0",
    "@ant-design/icons": "^5.3.0",
    "tailwindcss": "^3.4.0",
    "zustand": "^4.5.0",
    "axios": "^1.7.0",
    "react-hook-form": "^7.51.0",
    "zod": "^3.23.0",
    "@hookform/resolvers": "^3.3.0",
    "react-i18next": "^14.1.0",
    "i18next": "^23.11.0",
    "echarts": "^5.5.0",
    "echarts-for-react": "^3.0.2",
    "lucide-react": "^0.379.0",
    "dayjs": "^1.11.0",
    "clsx": "^2.1.0",
    "framer-motion": "^11.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "vitest": "^1.6.0",
    "@testing-library/react": "^15.0.0",
    "@playwright/test": "^1.44.0",
    "eslint": "^9.0.0",
    "prettier": "^3.2.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

---

## 3. 设计系统

### 3.1 设计令牌

通过 Tailwind Config + CSS Variables 实现：

```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        // 主色板
        primary: {
          DEFAULT: '#5B5FE9',
          hover: '#4A4ED8',
          active: '#3D41C7',
          light: '#EEF0FF',
        },
        secondary: {
          DEFAULT: '#1F2937',
          hover: '#374151',
        },
        accent: {
          DEFAULT: '#F59E0B',
          light: '#FEF3C7',
        },
        // 语义色
        success: '#10B981',
        warning: '#F59E0B',
        danger: '#EF4444',
        info: '#3B82F6',
        // 中性色
        gray: {
          50: '#F9FAFB',
          100: '#F3F4F6',
          200: '#E5E7EB',
          300: '#D1D5DB',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',
          700: '#374151',
          800: '#1F2937',
          900: '#111827',
        },
      },
      fontFamily: {
        sans: ['Inter', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        serif: ['Source Han Serif SC', 'Noto Serif SC', 'serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '6px',
        md: '8px',
        lg: '12px',
        xl: '16px',
      },
      spacing: {
        // 8px 网格
        '4.5': '18px',
        '18': '72px',
        '88': '352px',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        hover: '0 4px 12px rgba(0,0,0,0.08)',
        modal: '0 20px 50px rgba(0,0,0,0.15)',
      },
    },
  },
};
```

### 3.2 CSS 变量（主题切换）

```css
/* src/styles/theme.css */
:root {
  --color-bg: #FFFFFF;
  --color-bg-secondary: #F9FAFB;
  --color-bg-tertiary: #F3F4F6;
  --color-text-primary: #111827;
  --color-text-secondary: #4B5563;
  --color-text-tertiary: #9CA3AF;
  --color-border: #E5E7EB;
  --color-primary: #5B5FE9;
  --color-accent: #F59E0B;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.06);
}

[data-theme='dark'] {
  --color-bg: #0F172A;
  --color-bg-secondary: #1E293B;
  --color-bg-tertiary: #334155;
  --color-text-primary: #F1F5F9;
  --color-text-secondary: #CBD5E1;
  --color-text-tertiary: #94A3B8;
  --color-border: #334155;
  --color-primary: #818CF8;
  --color-accent: #FBBF24;
}
```

### 3.3 字体策略

- **正文（小说内容）**：思源宋体 / Source Han Serif SC（衬线体，提升阅读感）
- **UI 元素**：思源黑体 / Inter（无衬线体，清晰）
- **代码 / 数据**：JetBrains Mono

### 3.4 间距与圆角

- 间距：8px 网格（4, 8, 12, 16, 24, 32, 48, 64, 96）
- 圆角：按钮 4px，卡片 6px，模态框 12px

### 3.5 通用组件（基于 Ant Design 扩展）

| 组件 | 来源 | 定制点 |
|------|------|--------|
| Button | Antd | 圆角 4px，主色应用 |
| Input / TextArea | Antd | 圆角调整 |
| Modal / Drawer | Antd | 圆角 12px，阴影加深 |
| Table | Antd | 行高紧凑 |
| Tree | Antd | 大纲树专用样式 |
| Card | Antd | 阴影用自定义 token |
| Tooltip / Popover | Antd | 默认行为 |
| Notification | Antd | 顶部居中 |

### 3.6 自研组件清单

- `<WorkCard>` - 作品卡片
- `<OutlineTree>` - 大纲树（基于 Antd Tree 定制）
- `<RichEditor>` - 富文本编辑器（基于 TipTap）
- `<AIAssistant>` - AI 助手侧边栏
- `<StreamingDisplay>` - 流式输出展示
- `<ReviewPanel>` - 编辑审校批注
- `<ScoreRadar>` - 评审评分雷达图
- `<CharacterAvatar>` - 角色头像
- `<WorldGraphView>` - 世界观图谱（基于 ECharts）

---

## 4. 信息架构与路由

### 4.1 路由结构

```typescript
// src/router.tsx
import { createBrowserRouter } from 'react-router-dom';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <WorksListPage /> },
      { path: 'onboarding', element: <OnboardingPage /> },
      { path: 'settings', element: <SettingsPage /> },
      {
        path: 'works/:workId',
        element: <WorkLayout />,
        children: [
          { index: true, element: <WorkDashboardPage /> },
          { path: 'outline', element: <OutlinePage /> },
          { path: 'world', element: <WorldBiblePage /> },
          { path: 'characters', element: <CharactersPage /> },
          { path: 'chapters/:chapterId', element: <ChapterEditPage /> },
        ],
      },
    ],
  },
  { path: '/login', element: <LoginPage /> }, // 可选本地鉴权
  { path: '*', element: <NotFoundPage /> },
]);
```

### 4.2 页面清单

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | 作品列表 | 主入口 |
| `/onboarding` | 新手引导 | 首次启动 |
| `/settings` | 设置 | 全局设置 |
| `/works/:workId` | 作品详情/仪表盘 | 默认页 |
| `/works/:workId/outline` | 大纲编辑 | 树状结构 |
| `/works/:workId/world` | 世界圣经 | 多 Tab |
| `/works/:workId/characters` | 角色管理 | 列表 + 详情 |
| `/works/:workId/chapters/:chapterId` | 章节编辑 | 三栏布局 |
| `/settings/api` | API 配置 | 子路由 |
| `/settings/prompts` | Prompt 模板 | 高级功能 |

### 4.3 导航结构

```
┌─────────────────────────────────────────────────────────┐
│  顶栏 │LingMa Logo │ 全局搜索 │ 设置 │ 帮助 │ 用户菜单│
├──────┼──────────────────────────────────────────────────┤
│      │                                                  │
│ 侧边 │  [页面内容]                                  │
│  栏 │                                                  │
│ (仅 │                                                  │
│ 作品│)                                                  │
│      │                                                  │
└──────┴──────────────────────────────────────────────────┘
```

---

## 5. 状态管理

### 5.1 Store 划分

使用 Zustand，按领域划分多个 store：

```typescript
// src/stores/
├── useAuthStore.ts        // 用户/认证
├── useWorksStore.ts       // 作品列表、当前作品
├── useEditorStore.ts      // 编辑器状态（章节内容、选中、版本）
├── useGenerationStore.ts  // 生成任务（任务列表、进度、流式 buffer）
├── useSettingsStore.ts    // 全局设置
├── useUIStore.ts          // UI 状态（侧边栏、模态框、主题）
└── useAIStore.ts          // AI 助手状态（上下文、对话历史）
```

### 5.2 Store 设计模式

```typescript
// src/stores/useEditorStore.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface EditorState {
  // 当前章节
  currentChapterId: string | null;
  content: TipTapJSON;  // TipTap JSON 文档
  plainText: string;    // 纯文本（用于字数统计、RAG）

  // 编辑状态
  isDirty: boolean;
  isSaving: boolean;
  selectedRange: { from: number; to: number } | null;

  // 版本管理
  currentVersion: number;
  versions: ChapterVersion[];

  // Actions
  setChapter: (id: string, content: TipTapJSON, plain: string) => void;
  updateContent: (content: TipTapJSON, plain: string) => void;
  save: () => Promise<void>;
  switchVersion: (no: number) => Promise<void>;
  setSelection: (range: { from: number; to: number }) => void;
}

export const useEditorStore = create<EditorState>()(
  devtools((set, get) => ({
    currentChapterId: null,
    content: null,
    plainText: '',
    isDirty: false,
    isSaving: false,
    selectedRange: null,
    currentVersion: 1,
    versions: [],

    setChapter: (id, content, plain) =>
      set({
        currentChapterId: id,
        content,
        plainText: plain,
        isDirty: false,
      }),

    updateContent: (content, plain) =>
      set({ content, plainText: plain, isDirty: true }),

    save: async () => {
      set({ isSaving: true });
      try {
        const { currentChapterId, content, plainText } = get();
        await api.chapters.update(currentChapterId!, {
          content,
          plain_content: plainText,
        });
        set({ isDirty: false });
      } finally {
        set({ isSaving: false });
      }
    },

    switchVersion: async (no) => {
      const { currentChapterId } = get();
      const chapter = await api.chapters.switchVersion(currentChapterId!, no);
      set({
        content: chapter.content,
        plainText: chapter.plain_content,
        currentVersion: no,
      });
    },

    setSelection: (range) => set({ selectedRange: range }),
  }))
);
```

### 5.3 状态同步原则

| 状态类型 | 存储位置 | 持久化 |
|----------|----------|--------|
| 业务数据（作品/章节） | 后端 | 后端 DB |
| UI 状态（侧栏展开、模态框） | Zustand | localStorage |
| 编辑器草稿 | Zustand + IndexedDB | 临时缓存 |
| 用户偏好（主题、语言） | Zustand | localStorage |
| 临时流式 Buffer | Zustand | 内存（重连可恢复） |

---

## 6. 核心页面详述

### 6.1 作品列表页（`/`）

#### 6.1.1 线框图

```
┌─────────────────────────────────────────────────────────┐
│  LingMa    🔍搜索[             ]   ⚙️设置  👤   📚文档│
├─────────────────────────────────────────────────────────┤
│  我的作品 (12)                                              │
│  [全部] [玄幻] [都市] [言情] [历史] [科幻] [悬疑]            │
│  排序：最新更新 ▼   视图：⊞网格 | ☰列表    [➕新建作品]    │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  📕封面 │ │  📗封面  │ │  📘封面  │ │  📙封面  │       │
│  │  剑来前传│ │  重生2008│ │  暖阳    │ │  银河纪元│      │
│  │ 玄幻·创作中│ │ 都市·创作中│ │ 言情·草稿  │ │ 科幻·完结  │      │
│  │  35.2万字 │ │  12.8万字 │ │  0.5万字  │ │  80万字   │      │
│  │  ▓▓▓░░░░ │ │  ▓░░░░░░ │ │  ░░░░░░░ │ │  ▓▓▓▓▓▓▓▓│      │
│  │  35% 完成 │ │  12% 完成 │ │  1% 完成  │ │  100% 完成│      │
│  │  更新2h前 │ │  更新昨日 │ │  —       │ │  已完结   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                             │
│  [加载更多]                                                  │
└─────────────────────────────────────────────────────────┘
```

#### 6.1.2 组件树

```typescript
<WorksListPage>
  <TopBar />
  <FilterBar>
    <GenreTabs />
    <SortDropdown />
    <ViewSwitcher />
    <NewWorkButton />
  </FilterBar>
  <WorksGrid>
    {works.map(w => (
      <WorkCard work={w} onClick={() => navigate(`/works/${w.id}`)} />
    ))}
  </WorksGrid>
  <EmptyState show={works.length === 0} />
</WorksListPage>
```

#### 6.1.3 交互细节

- **新建作品**：点击按钮 → 弹出 `NewWorkModal` → 4 步引导
- **搜索**：防抖 300ms，模糊匹配标题 + logline
- **筛选**：点击 Tab 即时刷新，多选
- **排序**：最新更新 / 字数 / 完成度 / 创建时间
- **视图切换**：网格 ↔ 列表，记忆到 localStorage
- **卡片操作**：右键弹出菜单（删除 / 重命名 / 导出 / 复制）
- **拖拽**：未来支持（V2）

#### 6.1.4 组件 Props

```typescript
interface WorkCardProps {
  work: Work;
  onClick: () => void;
  onContextMenu?: (e: React.MouseEvent) => void;
}
```

### 6.2 新建作品引导页（`/onboarding`）

#### 6.2.1 4 步流程

```
Step 1: 选题材      Step 2: 选风格      Step 3: 输入核心     Step 4: AI 生成大纲
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ ⚔️玄幻 │    │ 热血  │    │[一句话]│    │ 🔄加载中│
│ 🏙️都市 │    │ 轻松  │    │[关键词]│    │ 流式输出│
│ 💕言情 │    │ 悬疑  │    │[目标]  │    │ 自动保存│
│ 📜历史 │    │ 甜文  │    │        │    │         │
│ 🚀科幻 │    │  ... │    │        │    │         │
│ 🎭悬疑 │    │        │    │        │    │         │
│ +自定义 │    │        │    │        │    │         │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

#### 6.2.2 组件实现

```typescript
<OnboardingPage>
  <Steps currentStep={step} totalSteps={4} />
  {step === 0 && <GenreStep onNext={...} />}
  {step === 1 && <StyleStep onNext={...} />}
  {step === 2 && <ConceptStep onNext={...} />}
  {step === 3 && <GeneratingStep workId={createdWork.id} />}
</OnboardingPage>
```

### 6.3 章节编辑页（`/works/:workId/chapters/:chapterId`）

#### 6.3.1 三栏布局

```
┌─────────────────────────────────────────────────────────────────┐
│ ←返回 剑来前传  第一章·风起青萍  v3 ⚙   [▶续写] [📊评审] [📥导出]│
├────────┬────────────────────────────────────────┬────────────┤
│ 📚大纲 │  风起青萍                                │ 🤖 AI 助手 │
│ 240px  │  林墨独行于山道……                      │ 280px      │
│        │  ...                                    │            │
│ ▼第一卷│  ...                                    │ [上下文] │
│  ▶第1章│                                        │   □大纲  │
│   ●   │                                        │   ☑人物  │
│  ▶第2章│                                        │   □风格  │
│  ▶第3章│                                        │ ────────  │
│        │  字数: 2,847                           │ [AI 操作]│
│ ▼世界  │  状态: 已自动保存 (14:23)              │   ▷ 续写  │
│ ▼人物  │                                        │   ✎ 改写  │
│        │                                        │   ⊕ 扩写  │
│ [📊统计]│                                        │   ⊖ 缩写  │
│        │                                        │   ✨ 润色 │
│        │                                        │ ────────  │
│        │                                        │ [评审]   │
│        │                                        │   8.5/10 │
│        │                                        │   👍爽点足│
│        │                                        │   💡改进3│
└────────┴────────────────────────────────────────┴────────────┘
```

#### 6.3.2 组件树

```typescript
<ChapterEditPage>
  <ChapterTopBar
    title={chapter.title}
    version={currentVersion}
    actions={['continue', 'review', 'export', 'save']}
  />
  <ThreeColumnLayout
    left={<OutlineSidebar workId={workId} activeChapterId={chapterId} />}
    center={
      <RichEditor
        chapterId={chapterId}
        content={content}
        onChange={handleContentChange}
        onSelectionChange={setSelection}
      />
    }
    right={
      <AIAssistant
        chapterId={chapterId}
        context={context}
        onAction={handleAIAction}
      />
    }
  />
  <StatusBar
    wordCount={wordCount}
    saveStatus={saveStatus}
  />
</ChapterEditPage>
```

#### 6.3.3 关键交互

| 交互 | 触发 | 行为 |
|------|------|------|
| 选中文字 | 鼠标选中 | 弹出浮动工具栏（AI 操作快捷入口） |
| 右键菜单 | 右键点击 | 复制 / 粘贴 / AI 操作 / 格式 |
| `/ai` 命令 | 输入 `/ai` | 唤起 AI 命令面板 |
| `Ctrl+S` | 快捷键 | 手动保存 |
| `Ctrl+Shift+A` | 快捷键 | 切换 AI 助手面板 |
| `Ctrl+K` | 快捷键 | 全局搜索 |

### 6.4 大纲编辑页（`/works/:workId/outline`）

#### 6.4.1 视图模式

- **树视图**：左侧树 + 右侧详情编辑
- **时间轴视图**：横向卷轴展示进度（V2）

```
┌────────────────────────────────────────────────────────────┐
│  大纲编辑器        [树视图] [时间轴]    [🤖AI 拆分节点]    │
├──────────────────┬─────────────────────────────────────────┤
│ ▼ 📕第一卷·初入江湖│  节点详情                                  │
│   ├ 📄第1章·风起青萍│  标题：[第一章·风起青萍]              │
│   ├ 📄第2章·...    │  摘要：林墨独行山道，...               │
│   └ 📄第3章·...    │  节拍：                                      │
│ ▼ 📗第二卷·...    │   □ 主角登场                              │
│   ...               │   ☑ 第一次冲突                            │
│                    │   □ 阶段高潮                              │
│  [+ 新建节点]       │  涉及人物：[林墨] [苏婉] [云浩]            │
│                    │  目标字数：3000                            │
│                    │  [生成章节 →]                              │
└──────────────────┴─────────────────────────────────────────┘
```

### 6.5 角色管理页（`/works/:workId/characters`）

```
┌────────────────────────────────────────────────────────────┐
│  角色管理    [+新建角色]   [🤖AI设计角色]    🔍搜索角色        │
├──────────────┬─────────────────────────────────────────────┤
│ 角色列表      │  角色详情                                     │
│              │                                              │
│ [头像] 林墨   │  基本信息                                       │
│   主角·男主   │  姓名: 林墨   年龄: 18   性别: 男            │
│ [头像] 苏婉   │  外貌: 黑衣黑发，面容清冷                       │
│   女主        │  身份: 青云剑宗外门弟子                          │
│ [头像] 云浩   │                                              │
│   配角        │  性格                                          │
│ [头像] ...    │  特质: [沉默] [重情] [偏执]                    │
│              │  MBTI: INTJ                                   │
│              │  说话风格: 惜字如金...                            │
│              │                                              │
│              │  背景                                          │
│              │  出身: 孤儿出身，被师父收留                       │
│              │  ...                                          │
│              │                                              │
│              │  [💬 与角色对话]   [📋 出场记录]   [📊 分析]    │
└──────────────┴─────────────────────────────────────────────┘
```

### 6.6 世界圣经页（`/works/:workId/world`）

#### 6.6.1 多 Tab 结构

```
┌────────────────────────────────────────────────────────────┐
│  世界圣经    [🤖AI 构建]   [🔄一致性检查]                     │
├────────────────────────────────────────────────────────────┤
│ [🌍地理] [⚔️势力] [💪力量] [📅时间线] [📜规则] [🎭文化]      │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  当前 Tab：⚔️ 势力                                          │
│                                                             │
│  ┌─────────────────────────────────────┐                   │
│  │ 青云剑宗                     [编辑] │                   │
│  │ 类型: 修仙门派                       │                   │
│  │ 所在地: 东荒圣域·青云山               │                   │
│  │ 掌门: 玄清真人                        │                   │
│  │ 弟子: 3000 余人                      │                   │
│  │ 立场: 正道                           │                   │
│  │ ...                                 │                   │
│  └─────────────────────────────────────┘                   │
│  [+ 新建势力]                                               │
│                                                             │
│  [势力关系图]（可视化）                                      │
└────────────────────────────────────────────────────────────┘
```

#### 6.6.2 势力关系图组件

使用 ECharts Graph 展示：

```typescript
<WorldGraphView type="factions" data={factionRelations} />
```

### 6.7 设置页（`/settings`）

#### 6.7.1 多 Tab 结构

```
┌────────────────────────────────────────────────────────────┐
│  设置                                                       │
├────────────────────────────────────────────────────────────┤
│ [🎨界面] [🤖API配置] [✏️Prompt模板] [📊创作] [🔒安全] [⚙️高级]│
├────────────────────────────────────────────────────────────┤
│                                                             │
│  🤖 API 配置                                                │
│                                                             │
│  ┌──────────────────────────────────────────────────┐     │
│  │ 我的 Claude                            [编辑] [删除] │     │
│  │ 提供商: Anthropic                                │     │
│  │ 模型: claude-opus-5-20251101                     │     │
│  │ 用途: 写作 ✦ 编辑                                │     │
│  │ 状态: ● 已连接  上次测试: 2分钟前                 │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
│  [+ 添加 API 配置]                                          │
└────────────────────────────────────────────────────────────┘
```

#### 6.7.2 各 Tab 详细字段

| Tab | 字段 |
|-----|------|
| 界面 | 主题、语言、字体大小、自动保存间隔 |
| API 配置 | 配置列表、测试连接、模型分配 |
| Prompt 模板 | 编辑 6 个 Agent 的 Prompt、导入导出 |
| 创作 | 默认目标字数、风格关键词、章节模板 |
| 安全 | 加密开关、自动备份、清除缓存 |
| 高级 | 上下文窗口、日志查看、向量库管理 |

### 6.8 评审结果页（章节评审后展示）

```
┌────────────────────────────────────────────────────────────┐
│  📊 评审结果                                       [✕关闭]  │
├────────────────────────────────────────────────────────────┤
│                                                             │
│       雷达图                            总分: 8.5/10 (A)    │
│                                                             │
│   代入感 9.0  ★★★★☆                                     │
│   节奏    8.5  ★★★★☆                                     │
│   爽点密度 8.0  ★★★★☆                                     │
│   情感冲击 9.0  ★★★★☆                                     │
│   文笔    8.0  ★★★★☆                                     │
│                                                             │
│   ✅ 优点                                                   │
│   • 开篇悬念足，第一段即抓住读者                            │
│   • 林墨与云浩的对手戏张力十足                              │
│   • 战斗描写富有画面感                                      │
│                                                             │
│   ⚠️ 改进建议                                               │
│   • 第二章结尾节奏过快，建议在反派出场前铺垫                │
│   • 苏婉的内心戏略显单薄                                    │
│   • 中段情节可适当收紧                                      │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## 7. 富文本编辑器

### 7.1 基于 TipTap 的封装

```typescript
// src/components/RichEditor/index.tsx
import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { useEffect, useRef } from 'react';

interface RichEditorProps {
  chapterId: string;
  content: TipTapJSON | null;
  editable?: boolean;
  onChange: (json: TipTapJSON, plain: string) => void;
  onSelectionChange?: (range: { from: number; to: number }) => void;
  onSave?: () => void;
}

export function RichEditor({
  chapterId,
  content,
  editable = true,
  onChange,
  onSelectionChange,
  onSave,
}: RichEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        history: { depth: 50 },
      }),
      // 扩展：自定义 AI 标记、高亮审校建议等
    ],
    content: content || '',
    editable,
    onUpdate: ({ editor }) => {
      onChange(editor.getJSON(), editor.getText());
    },
    onSelectionUpdate: ({ editor }) => {
      const { from, to } = editor.state.selection;
      onSelectionChange?.({ from, to });
    },
  });

  // 自动保存（防抖）
  useEffect(() => {
    if (!editor) return;
    const handler = setTimeout(() => onSave?.(), 10000);
    return () => clearTimeout(handler);
  }, [editor?.state.doc]);

  return (
    <div className="rich-editor">
      <EditorContent editor={editor} className="prose prose-lg max-w-none" />
      {editor && <BubbleMenu editor={editor} />}
    </div>
  );
}
```

### 7.2 编辑器工具栏

```typescript
// src/components/RichEditor/EditorToolbar.tsx
export function EditorToolbar({ editor }: { editor: Editor }) {
  return (
    <div className="flex items-center gap-1 p-2 border-b">
      <ToolbarGroup>
        <Tooltip content="撤销 (Ctrl+Z)">
          <Button
            icon={<Undo />}
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
          />
        </Tooltip>
        <Tooltip content="重做 (Ctrl+Y)">
          <Button
            icon={<Redo />}
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
          />
        </Tooltip>
      </ToolbarGroup>
      <Divider />
      <ToolbarGroup>
        <FormatButton editor={editor} format="bold" icon={<Bold />} />
        <FormatButton editor={editor} format="italic" icon={<Italic />} />
        <FormatButton editor={editor} format="strike" icon={<Strikethrough />} />
        <FormatButton editor={editor} format="code" icon={<Code />} />
      </ToolbarGroup>
      <Divider />
      <ToolbarGroup>
        <HeadingSelector editor={editor} />
        <BlockSelector editor={editor} />
      </ToolbarGroup>
      <Divider />
      <ToolbarGroup>
        <AIDropdown editor={editor} />
      </ToolbarGroup>
    </div>
  );
}
```

### 7.3 浮动菜单（选中文字时弹出）

```typescript
// src/components/RichEditor/BubbleMenu.tsx
import { BubbleMenu } from '@tiptap/react';

export function EditorBubbleMenu({ editor }: { editor: Editor }) {
  return (
    <BubbleMenu editor={editor} tippyOptions={{ duration: 100 }}>
      <div className="bg-white shadow-lg rounded-lg p-1 flex gap-1 border">
        <Button
          size="small"
          icon={<Sparkles />}
          onClick={() => aiRewrite(editor)}
        >
          AI 改写
        </Button>
        <Button
          size="small"
          onClick={() => aiExpand(editor)}
        >
          扩写
        </Button>
        <Button size="small" onClick={() => aiShorten(editor)}>缩写</Button>
        <Button size="small" onClick={() => aiPolish(editor)}>润色</Button>
      </div>
    </BubbleMenu>
  );
}
```

### 7.4 审校批注渲染

```typescript
// 自定义 Mark：审校建议
import { Mark, mergeAttributes } from '@tiptap/core';

export const SuggestionMark = Mark.create({
  name: 'suggestion',
  addAttributes() {
    return {
      suggestionId: { default: null },
      severity: { default: 'info' },
      type: { default: 'style' },
    };
  },
  parseHTML() {
    return [{ tag: 'span[data-suggestion]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-suggestion': 'true',
        class: `suggestion-${HTMLAttributes.severity}`,
      }),
      0,
    ];
  },
});
```

### 7.5 性能优化

- 大文档（> 50KB）：使用 `Collaboration` 扩展分片加载
- 防抖保存：用户停止输入 10 秒后自动保存
- 字数统计：使用纯文本缓存，避免重复计算

---

## 8. AI 交互组件

### 8.1 AIAssistant 侧边栏

```typescript
// src/components/AIAssistant/index.tsx
interface AIAssistantProps {
  chapterId: string;
  context: AIContext;
  onAction: (action: AIAction) => void;
}

export function AIAssistant({ chapterId, context, onAction }: AIAssistantProps) {
  return (
    <aside className="ai-assistant w-72 border-l p-4 overflow-y-auto">
      <Tabs defaultActiveKey="actions">
        <TabPane tab="操作" key="actions">
          <ContextSelector value={context} onChange={...} />
          <ActionButtons chapterId={chapterId} onAction={onAction} />
        </TabPane>
        <TabPane tab="评审" key="review">
          <ReviewPanel chapterId={chapterId} />
        </TabPane>
        <TabPane tab="历史" key="history">
          <GenerationHistory />
        </TabPane>
      </Tabs>
    </aside>
  );
}
```

### 8.2 上下文选择器

```typescript
// src/components/AIAssistant/ContextSelector.tsx
export function ContextSelector({ value, onChange }) {
  const options = [
    { value: 'outline', label: '大纲', icon: <ListTree /> },
    { value: 'characters', label: '人物', icon: <Users /> },
    { value: 'world', label: '世界观', icon: <Globe /> },
    { value: 'style', label: '风格参考', icon: <Palette /> },
    { value: 'few_shot', label: '前文章节', icon: <BookOpen /> },
  ];

  return (
    <div className="space-y-2">
      <div className="text-sm text-gray-500">参考上下文</div>
      <Checkbox.Group value={value} onChange={onChange}>
        {options.map(opt => (
          <div key={opt.value} className="flex items-center gap-2 mb-1">
            <Checkbox value={opt.value}>{opt.label}</Checkbox>
          </div>
        ))}
      </Checkbox.Group>
    </div>
  );
}
```

### 8.3 操作按钮

```typescript
// src/components/AIAssistant/ActionButtons.tsx
const ACTIONS = [
  { key: 'continue', label: '续写', icon: Play, color: 'primary' },
  { key: 'rewrite', label: '改写', icon: RefreshCw },
  { key: 'expand', label: '扩写', icon: Maximize2 },
  { key: 'shorten', label: '缩写', icon: Minimize2 },
  { key: 'polish', label: '润色', icon: Sparkles },
  { key: 'translate', label: '翻译', icon: Languages },
  { key: 'suggest', label: '走向建议', icon: Compass },
];

export function ActionButtons({ chapterId, onAction }) {
  return (
    <div className="grid grid-cols-2 gap-2 mt-4">
      {ACTIONS.map(({ key, label, icon: Icon, color }) => (
        <Button
          key={key}
          icon={<Icon size={16} />}
          onClick={() => onAction(key)}
          type={color === 'primary' ? 'primary' : 'default'}
        >
          {label}
        </Button>
      ))}
    </div>
  );
}
```

### 8.4 流式输出展示

```typescript
// src/components/StreamingDisplay/index.tsx
export function StreamingDisplay({ taskId, onComplete }: StreamingProps) {
  const { content, progress, status, error } = useGenerationStream(taskId);

  return (
    <Modal
      open={status !== 'idle'}
      title={
        <div className="flex items-center gap-2">
          {status === 'running' && <Spin />}
          <span>
            {status === 'running' && 'AI 正在创作...'}
            {status === 'completed' && '生成完成'}
            {status === 'failed' && '生成失败'}
          </span>
        </div>
      }
      footer={null}
      width={700}
      closable={status !== 'running'}
    >
      <Progress percent={progress} status={status === 'failed' ? 'exception' : 'active'} />
      <div className="mt-4 max-h-96 overflow-y-auto bg-gray-50 p-4 rounded">
        <pre className="whitespace-pre-wrap font-serif text-base">
          {content || '等待内容...'}
          {status === 'running' && <span className="animate-pulse">▌</span>}
        </pre>
      </div>
      {status === 'failed' && (
        <Alert type="error" message={error} className="mt-4" />
      )}
      {status === 'completed' && (
        <div className="mt-4 flex justify-end gap-2">
          <Button onClick={() => onComplete('discard')}>放弃</Button>
          <Button type="primary" onClick={() => onComplete('accept')}>采纳</Button>
        </div>
      )}
    </Modal>
  );
}
```

### 8.5 评审结果组件

```typescript
// src/components/ReviewPanel/index.tsx
import ReactECharts from 'echarts-for-react';

export function ReviewPanel({ chapterId }: { chapterId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['review', chapterId],
    queryFn: () => api.chapters.review(chapterId),
  });

  if (isLoading) return <Spin />;
  if (!data) return <Empty />;

  const radarOption = {
    radar: {
      indicator: Object.entries(data.scores).map(([k, v]) => ({
        name: k,
        max: 10,
      })),
    },
    series: [{
      type: 'radar',
      data: [{
        value: Object.values(data.scores),
        name: '评分',
      }],
    }],
  };

  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className="text-3xl font-bold text-primary">
          {data.scores.overall.toFixed(1)}
        </div>
        <div className="text-sm text-gray-500">
          等级 {data.grade} · 综合评价
        </div>
      </div>

      <ReactECharts option={radarOption} style={{ height: 250 }} />

      <div>
        <h4 className="font-semibold mb-2">✅ 优点</h4>
        <ul className="space-y-1 text-sm">
          {data.pros.map((p, i) => (
            <li key={i} className="text-green-700">• {p}</li>
          ))}
        </ul>
      </div>

      <div>
        <h4 className="font-semibold mb-2">⚠️ 改进建议</h4>
        <ul className="space-y-1 text-sm">
          {data.cons.map((c, i) => (
            <li key={i} className="text-orange-700">• {c}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

### 8.6 角色对话界面

```typescript
// src/pages/Characters/CharacterChat.tsx
export function CharacterChat({ character }: { character: Character }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const sessionIdRef = useRef<string | null>(null);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');

    const reply = await api.characters.chat(character.id, {
      messages: [...messages, userMsg],
      session_id: sessionIdRef.current,
    });
    sessionIdRef.current = reply.session_id;
    setMessages(prev => [...prev, { role: 'assistant', content: reply.reply }]);
  };

  return (
    <div className="character-chat flex flex-col h-full">
      <CharacterHeader character={character} />
      <MessageList messages={messages} character={character} />
      <InputArea value={input} onChange={setInput} onSend={sendMessage} />
    </div>
  );
}
```

---

## 9. WebSocket 客户端

### 9.1 Hook 封装

```typescript
// src/hooks/useGenerationStream.ts
import { useEffect, useRef, useState } from 'react';
import { useGenerationStore } from '@/stores/useGenerationStore';

export function useGenerationStream(taskId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [streamBuffer, setStreamBuffer] = useState('');
  const { updateTask, completeTask, failTask } = useGenerationStore();

  useEffect(() => {
    if (!taskId) return;

    const ws = new WebSocket(
      `${import.meta.env.VITE_WS_BASE}/ws/generation/${taskId}`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WS connected', taskId);
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      switch (msg.type) {
        case 'connected':
        case 'started':
          updateTask(taskId, { status: 'running' });
          break;

        case 'progress':
          updateTask(taskId, { progress: msg.progress, step: msg.step });
          break;

        case 'chunk':
          setStreamBuffer(prev => prev + msg.content);
          break;

        case 'review':
          updateTask(taskId, { reviewSuggestions: msg.suggestions });
          break;

        case 'score':
          updateTask(taskId, { scores: msg.scores });
          break;

        case 'completed':
          completeTask(taskId, msg);
          break;

        case 'failed':
          failTask(taskId, msg.error);
          break;
      }
    };

    ws.onerror = (e) => {
      console.error('WS error', e);
    };

    ws.onclose = () => {
      console.log('WS closed', taskId);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [taskId]);

  // 控制方法
  const sendControl = (cmd: any) => {
    wsRef.current?.send(JSON.stringify(cmd));
  };

  const cancel = () => sendControl({ type: 'cancel', task_id: taskId });

  return { streamBuffer, sendControl, cancel };
}
```

### 9.2 自动重连

```typescript
// src/hooks/useWebSocket.ts
export function useWebSocket(
  url: string,
  options: { reconnect?: boolean; maxRetries?: number } = {}
) {
  const { reconnect = true, maxRetries = 5 } = options;
  const [readyState, setReadyState] = useState<WebSocket['readyState']>(WebSocket.CLOSED);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;
    setReadyState(ws.readyState);

    ws.onopen = () => {
      retryRef.current = 0;
      setReadyState(WebSocket.OPEN);
    };

    ws.onclose = () => {
      setReadyState(WebSocket.CLOSED);
      if (reconnect && retryRef.current < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retryRef.current), 30000);
        retryRef.current++;
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => ws.close();
  }, [url, reconnect, maxRetries]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { readyState, send: (data: any) => wsRef.current?.send(JSON.stringify(data)) };
}
```

---

## 10. API 客户端层

### 10.1 Axios 封装

```typescript
// src/api/client.ts
import axios, { AxiosError } from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截器
apiClient.interceptors.request.use((config) => {
  // 注入 token（如果有）
  const token = localStorage.getItem('lingma_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<ApiError>) => {
    const message = error.response?.data?.error?.message || error.message;

    // 统一错误处理
    if (error.response?.status === 401) {
      window.location.href = '/login';
    } else if (error.response?.status && error.response.status >= 500) {
      console.error('Server error:', message);
    }

    return Promise.reject(new ApiError(
      error.response?.data?.error?.code || 'UNKNOWN_ERROR',
      message,
      error.response?.status
    ));
  }
);

export class ApiError extends Error {
  constructor(public code: string, message: string, public status?: number) {
    super(message);
  }
}
```

### 10.2 模块化 API

```typescript
// src/api/works.ts
export const worksApi = {
  list: (params?: ListParams) =>
    apiClient.get<Paginated<Work>>('/works', { params }),

  get: (id: string) =>
    apiClient.get<Work>(`/works/${id}`),

  create: (data: CreateWorkInput) =>
    apiClient.post<Work>('/works', data),

  update: (id: string, data: Partial<CreateWorkInput>) =>
    apiClient.patch<Work>(`/works/${id}`, data),

  delete: (id: string) =>
    apiClient.delete<void>(`/works/${id}`),

  statistics: (id: string) =>
    apiClient.get<WorkStatistics>(`/works/${id}/statistics`),

  export: (id: string, format: ExportFormat) =>
    apiClient.get(`/works/${id}/export`, {
      params: { format },
      responseType: 'blob',
    }),
};

// src/api/chapters.ts
export const chaptersApi = {
  list: (workId: string, params?: ListParams) =>
    apiClient.get<Paginated<Chapter>>(`/works/${workId}/chapters`, { params }),

  get: (id: string) =>
    apiClient.get<Chapter>(`/chapters/${id}`),

  update: (id: string, data: Partial<Chapter>) =>
    apiClient.patch<Chapter>(`/chapters/${id}`, data),

  generate: (data: GenerateChapterInput) =>
    apiClient.post<{ task_id: string; ws_url: string }>('/chapters/generate', data),

  aiContinue: (id: string, data: AIInput) =>
    apiClient.post<{ task_id: string }>(`/chapters/${id}/ai-continue`, data),

  review: (id: string, dimensions?: string[]) =>
    apiClient.post<ReviewResult>(`/chapters/${id}/ai-review`, { dimensions }),

  // ...
};
```

### 10.3 React Query 集成

```typescript
// src/hooks/queries/useWorks.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useWorks(params?: ListParams) {
  return useQuery({
    queryKey: ['works', params],
    queryFn: () => worksApi.list(params),
    staleTime: 30_000,
  });
}

export function useWork(id: string) {
  return useQuery({
    queryKey: ['works', id],
    queryFn: () => worksApi.get(id),
    enabled: !!id,
  });
}

export function useCreateWork() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: worksApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['works'] }),
  });
}
```

---

## 11. 国际化与主题

### 11.1 i18n 配置

```typescript
// src/i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

i18n.use(initReactI18next).init({
  resources: {
    'zh-CN': { translation: zhCN },
    'en-US': { translation: enUS },
  },
  lng: localStorage.getItem('lingma_lang') || 'zh-CN',
  fallbackLng: 'zh-CN',
  interpolation: { escapeValue: false },
});

export default i18n;
```

### 11.2 主题切换

```typescript
// src/hooks/useTheme.ts
export function useTheme() {
  const theme = useSettingsStore(s => s.theme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('lingma_theme', theme);
  }, [theme]);

  return theme;
}
```

---

## 12. 性能优化

### 12.1 关键指标

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| FCP (First Contentful Paint) | < 1.5s | Lighthouse |
| LCP (Largest Contentful Paint) | < 2.5s | Lighthouse |
| TTI (Time to Interactive) | < 3.5s | Lighthouse |
| 路由切换 | < 300ms | Performance API |
| 大纲树渲染（1000 节点） | < 100ms | React Profiler |
| 编辑器输入响应 | < 50ms | 手动测量 |

### 12.2 优化策略

```typescript
// 1. 路由级 code splitting
const ChapterEditPage = lazy(() => import('@/pages/ChapterEditPage'));
const WorldBiblePage = lazy(() => import('@/pages/WorldBiblePage'));

// 2. 大纲树虚拟滚动（>100 节点时）
import { VariableSizeList } from 'react-window';

// 3. 编辑器文档分片（大文档）
// 使用 TipTap 的 Collaboration 扩展分片

// 4. 图片懒加载
<img loading="lazy" src={...} />

// 5. 防抖保存
const debouncedSave = useMemo(
  () => debounce(save, 10000),
  [save]
);

// 6. 组件 memo
const WorkCard = memo(WorkCardComponent);

// 7. 选择性订阅
const title = useEditorStore(s => s.currentChapter?.title);
```

### 12.3 打包优化

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'editor-vendor': ['@tiptap/react', '@tiptap/starter-kit'],
          'antd-vendor': ['antd', '@ant-design/icons'],
          'charts-vendor': ['echarts', 'echarts-for-react'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
});
```

### 12.4 字体与资源加载

```typescript
// 使用 font-display: swap 避免 FOIT
// 在 index.html 中 preload 关键字体
<link rel="preload" href="/fonts/SourceHanSerif.woff2" as="font" type="font/woff2" crossorigin />
```

---

## 13. 错误处理与可观测性

### 13.1 全局错误边界

```typescript
// src/components/ErrorBoundary.tsx
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props { children: ReactNode; fallback?: ReactNode; }
interface State { hasError: boolean; error?: Error; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI Error:', error, info);
    // 上报到 Sentry 或本地日志（可选）
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <Result
          status="500"
          title="页面出错了"
          subTitle={this.state.error?.message}
          extra={<Button onClick={() => location.reload()}>重新加载</Button>}
        />
      );
    }
    return this.props.children;
  }
}
```

### 13.2 用户友好的错误反馈

| 错误类型 | 用户提示 | 处理 |
|----------|----------|------|
| 网络断连 | "网络连接断开，正在重试..." | 自动重连 + Toast |
| LLM 调用失败 | "AI 服务暂时不可用，请稍后重试" | 提供重试按钮 |
| API Key 无效 | "API Key 已失效，请在设置中更新" | 跳转设置页 |
| 上下文超长 | "内容过长，请先完成上一章节" | 自动截断 |
| 生成被取消 | "已取消生成" | 无操作 |
| 未知错误 | "操作失败，请稍后重试" | 记录到日志 |

### 13.3 Toast 与 Notification 规范

```typescript
// src/utils/notify.ts
import { message, notification } from 'antd';

// 成功 - 短消息
message.success('已保存');

// 信息 - 短消息
message.info('正在生成...');

// 警告 - 短消息
message.warning('请先选择内容');

// 错误 - 通知（带详情）
notification.error({
  message: '生成失败',
  description: error.message,
  duration: 0, // 不自动关闭
  btn: <Button size="small" onClick={retry}>重试</Button>,
});
```

---

## 14. 无障碍与兼容性

### 14.1 无障碍 (a11y)

| 要求 | 实现 |
|------|------|
| 键盘导航 | 所有交互元素支持 Tab 焦点、Enter/Space 触发 |
| 焦点可见 | 自定义 `:focus-visible` 样式（紫色 outline） |
| ARIA 标签 | 复杂组件（Tree、Dropdown）添加 `aria-label` |
| 屏幕阅读 | 使用语义化 HTML（button、nav、main） |
| 颜色对比度 | 文字与背景对比度 ≥ 4.5:1 |
| 字号可调 | 支持系统字号缩放，使用相对单位（rem） |
| 动效可控 | 尊重 `prefers-reduced-motion` |

### 14.2 浏览器兼容

| 浏览器 | 最低版本 | 说明 |
|--------|----------|------|
| Chrome | 100+ | 主目标 |
| Edge | 100+ | 同 Chrome |
| Safari | 15+ | macOS/iOS |
| Firefox | 100+ | 完整支持 |

**Polyfill**：
- `core-js` 用于语法兼容
- 不支持 IE

### 14.3 响应式适配

| 断点 | 宽度 | 布局 |
|------|------|------|
| Mobile | < 768px | 仅查看，不支持编辑（V2） |
| Tablet | 768-1024px | 两栏（隐藏 AI 助手） |
| Desktop | ≥ 1024px | 三栏完整布局 |
| Wide | ≥ 1920px | 加大编辑器宽度 |

### 14.4 输入法兼容

- 中文 IME 组合输入不触发保存
- 检测 `compositionstart` / `compositionend`
- 仅在组合结束后才触发内容变更

```typescript
const handleComposition = (e: CompositionEvent) => {
  if (e.type === 'compositionend') {
    // 此时才触发内容更新
  }
};
```

---

## 15. 测试规范

### 15.1 测试层级

| 层级 | 工具 | 覆盖率目标 |
|------|------|-----------|
| 单元测试 | Vitest + React Testing Library | 核心组件 ≥ 80% |
| 集成测试 | Vitest + MSW | API mock 流程 ≥ 70% |
| E2E | Playwright | 主要流程 100% |
| 视觉回归 | Chromatic / Percy | 关键页面 |

### 15.2 单元测试示例

```typescript
// src/components/__tests__/WorkCard.test.tsx
import { render, screen } from '@testing-library/react';
import { WorkCard } from '../WorkCard';

describe('WorkCard', () => {
  const mockWork = {
    id: '1',
    title: '剑来前传',
    genre: 'fantasy',
    status: 'writing',
    word_count: 352000,
    target_word_count: 1000000,
  };

  it('renders work title and word count', () => {
    render(<WorkCard work={mockWork} onClick={() => {}} />);
    expect(screen.getByText('剑来前传')).toBeInTheDocument();
    expect(screen.getByText(/35.2万字/)).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<WorkCard work={mockWork} onClick={handleClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledWith('1');
  });
});
```

### 15.3 E2E 测试关键流程

```typescript
// e2e/chapter-generation.spec.ts
import { test, expect } from '@playwright/test';

test('user can generate a chapter', async ({ page }) => {
  // 1. 登录
  await page.goto('http://localhost:7860');
  // 2. 创建作品
  await page.click('[data-testid="new-work-btn"]');
  await page.fill('[data-testid="title-input"]', '测试作品');
  // ... 填完创建步骤
  // 3. 进入大纲
  await page.click('[data-testid="outline-tab"]');
  // 4. 创建章节节点
  await page.click('[data-testid="new-chapter-btn"]');
  // 5. 生成章节
  await page.click('[data-testid="generate-btn"]');
  // 6. 等待流式输出
  await expect(page.locator('[data-testid="streaming-content"]')).toBeVisible();
  // 7. 等待完成
  await expect(page.locator('[data-testid="generation-complete"]')).toBeVisible({ timeout: 60000 });
});
```

---

## 16. 部署方案

### 16.1 Dockerfile

```dockerfile
# 多阶段构建
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# 生产镜像
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 16.2 nginx.conf

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|svg|woff2)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
}
```

### 16.3 Docker Compose 集成

```yaml
frontend:
  build: ./frontend
  container_name: lingma-frontend
  ports:
    - "7860:80"
  depends_on:
    - backend
  restart: unless-stopped
```

### 16.4 环境变量

```bash
# .env.production
VITE_API_BASE=/api/v1
VITE_WS_BASE=ws://${window.location.host}
VITE_APP_VERSION=0.1.0
```

### 16.5 构建产物

| 资源 | 体积预算 |
|------|----------|
| 主 JS（gzip） | < 500 KB |
| 主 CSS（gzip） | < 50 KB |
| 单个 chunk | < 1 MB |
| 首屏字体 | < 200 KB |

---

## 17. 开发里程碑

### 17.1 v0.1 MVP（4 周）

| 周 | 前端任务 | 工时 |
|----|----------|------|
| W1 | Vite + React + TS 项目初始化 + Tailwind + Antd | 2d |
| W1 | 路由 + 全局 Layout + 主题系统 | 2d |
| W1 | 作品列表页（CRUD UI） | 2d |
| W2 | 新建作品引导（4 步） | 2d |
| W2 | 大纲编辑器（树 + 详情） | 3d |
| W2 | 富文本编辑器（TipTap 集成 + 工具栏） | 3d |
| W3 | 章节编辑页（三栏布局） | 3d |
| W3 | AI 助手侧边栏 + 操作按钮 | 2d |
| W3 | WebSocket 流式展示组件 | 2d |
| W4 | 设置页（API 配置 + 基础） | 2d |
| W4 | 联调后端 API + Bug 修复 | 3d |
| W4 | 单元测试 + E2E 测试 | 2d |

### 17.2 v0.5 Beta（+8 周）

| 周 | 前端任务 |
|----|----------|
| W5-W6 | 角色管理页（列表 + 详情 + 人物卡编辑） |
| W7-W8 | 世界圣经页（多 Tab + 图谱可视化） |
| W9-W10 | 编辑 Agent 批注 UI + 评审雷达图 + 走向建议 |
| W11-W12 | Prompt 模板编辑器 + 高级设置 + 统计图表 |

### 17.3 v1.0 GA（+4 周）

| 周 | 前端任务 |
|----|----------|
| W13 | 角色对话界面（Chat UI） |
| W14 | 主题切换优化 + 响应式适配 |
| W15-W16 | 性能优化（虚拟滚动、分包、缓存） + 无障碍审计 |

---

## 附录

### 附录 A：常用 Hooks 清单

| Hook | 用途 |
|------|------|
| `useWorks` | 作品列表查询 |
| `useWork(id)` | 单个作品查询 |
| `useChapters(workId)` | 章节列表 |
| `useChapter(id)` | 章节详情 |
| `useGenerationStream(taskId)` | 流式生成 |
| `useWebSocket(url)` | WS 连接管理 |
| `useTheme()` | 主题切换 |
| `useDebouncedSave(value, delay)` | 防抖保存 |
| `useMediaQuery(query)` | 响应式断点 |

### 附录 B：组件复用原则

| 原则 | 说明 |
|------|------|
| **单一职责** | 一个组件只做一件事 |
| **可组合** | 通过 children/render props 组合 |
| **Props 明确** | 必填项用 `*` 后缀，可选提供默认值 |
| **错误兜底** | 列表组件处理空状态、错误状态 |
| **加载状态** | 异步组件提供 loading 占位 |
| **Memo 优化** | 列表渲染项使用 `memo` |

### 附录 C：命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件文件 | PascalCase | `WorkCard.tsx` |
| 工具文件 | camelCase | `formatDate.ts` |
| Hook 文件 | camelCase，`use` 前缀 | `useWorks.ts` |
| Store 文件 | camelCase，`use` 前缀 | `useEditorStore.ts` |
| 类型文件 | camelCase | `work.ts` |
| 常量 | UPPER_SNAKE_CASE | `MAX_CHAPTER_WORDS` |
| CSS 类 | kebab-case | `ai-assistant-panel` |

### 附录 D：参考资源

- React 官方文档：https://react.dev/
- TipTap 文档：https://tiptap.dev/
- Ant Design：https://ant.design/
- Tailwind CSS：https://tailwindcss.com/
- Zustand：https://zustand-demo.pmnd.rs/
- React Router：https://reactrouter.com/

---

## 文档结束

> **下一步**：
> 1. 评审本前端需求文档
> 2. 同步评审 [BACKEND_REQUIREMENTS.md](BACKEND_REQUIREMENTS.md)
> 3. 创建前端项目骨架（`frontend/` 目录初始化）
> 4. 按里程碑实现并与后端联调
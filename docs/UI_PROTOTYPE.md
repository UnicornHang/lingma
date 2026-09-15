# ZhiMeng UI 原型清单（UI Prototype Inventory）

> 版本 0.3 · 2026-09-12 · **基于 stitch_zhimeng_novel_studio v0.2 设计参考重构**
> 维护者：前端 / 设计协作

本文档统一登记 ZhiMeng 全部 UI 页面的**画布尺寸、布局分区、内容清单、组件清单与状态**，作为设计与开发的"单一事实来源"。

**标准画布**：1920 × 1080（桌面端，不做移动端 — PRD 已声明 out-of-scope）
**设计参考源**：[stitch_zhimeng_novel_studio](../stitch_zhimeng_novel_studio/) 4 个 v0.2 高保真 HTML mockup
**设计系统规范**：[precision_workspace/DESIGN.md](../stitch_zhimeng_novel_studio/precision_workspace/DESIGN.md)

---

## 目录

1. [设计系统基础](#1-设计系统基础)
2. [组件库](#2-组件库)
3. [全局布局壳](#3-全局布局壳)
4. [导航结构](#4-导航结构)
5. [页面清单](#5-页面清单)
6. [状态矩阵](#6-状态矩阵)
7. [Figma 文件结构](#7-figma-文件结构)
8. [未决问题](#8-未决问题)

---

## 1. 设计系统基础

### 1.1 设计语言（Brand & Style）

**Corporate / Modern 视觉风格**：
- **静谧精确**（Calm & Precision）：克制的层级、精确的描边、显式的微对比取代装饰趋势
- **留白密度**（Airy Density）：功能面板内有充足留白，平衡专业工具密度
- **认知舒适**（Cognitive Comfort）：柔和的中性背景，长时间创作不疲劳；高清晰 sans-serif + monospace 锚点用于编程实体

### 1.2 颜色（Material 3 色板，源自 precision_workspace/DESIGN.md）

**主色系**：

| Token | Hex | 用途 |
|-------|-----|------|
| `primary` | `#5B5FE9` | 主操作按钮、激活态、选中指示 |
| `primary-container` | `#E1E0FF` | 选中背景、激活行背景 |
| `on-primary` | `#FFFFFF` | 主按钮文字 |
| `on-primary-container` | `#2E2EBE` | 选中态文字 |
| `primary-fixed-dim` | `#C0C1FF` | 次级主色 |

**Surface 体系（背景层级）**：

| Token | Hex | 层级 | 用途 |
|-------|-----|------|------|
| `background` | `#FAF8FF` | L0 | 应用主背景 |
| `surface-container-lowest` | `#FFFFFF` | L1 | 卡片、文档、编辑器 |
| `surface-container-low` | `#F2F3FF` | L1.5 | 工作区主体 |
| `surface-container` | `#EAEDFF` | L2 | 工具栏、二级面板 |
| `surface-container-high` | `#E5E7F9` | L3 | 悬浮表面、激活项 |
| `surface-container-highest` | `#DFE2F4` | L4 | 分隔背景 |
| `surface-dim` | `#D6D9EB` | L5 | 禁用背景 |

**On-Surface 文本体系**：

| Token | Hex | 用途 |
|-------|-----|------|
| `on-surface` | `#171B28` | 主文本、标题 |
| `on-surface-variant` | `#464554` | 次要文本、说明 |
| `outline` | `#767586` | 占位符、辅助 |
| `outline-variant` | `#C6C5D7` | 分割线 |

**状态色**：

| Token | Hex | 用途 |
|-------|-----|------|
| `tertiary` | `#00662B` | 成功主色、Agent 协同激活 |
| `tertiary-container` | `#DBFFDA` | 成功背景（如「写作中」徽章） |
| `tertiary-fixed` | `#6BFF8F` | 高亮背景（如建议句高亮） |
| `error` | `#BA1A1A` | 错误、删除 |
| `error-container` | `#FFDAD6` | 错误背景 |

**Inverse（反色，用于通知/工具栏深底）**：

| Token | Hex |
|-------|-----|
| `inverse-surface` | `#2C303D` |
| `inverse-on-surface` | `#EEF0FF` |
| `inverse-primary` | `#C0C1FF` |

### 1.3 字体

| Token | Family | Size / LH | Weight | Letter Spacing | 用途 |
|-------|--------|-----------|--------|----------------|------|
| `display` | Inter | 32 / 40 | 700 | -0.02em | 章节标题、Modal 大标题 |
| `headline-lg` | Inter | 24 / 32 | 600 | -0.015em | 页面主标题 |
| `headline-md` | Inter | 20 / 28 | 600 | -0.01em | 区块标题 |
| `headline-sm` | Inter | 16 / 24 | 600 | -0.005em | 卡片标题 |
| `body-lg` | Inter | 16 / 24 | 400 | — | 章节正文（行高 1.9） |
| `body-md` | Inter | 14 / 20 | 400 | — | 卡片正文 |
| `body-sm` | Inter | 12 / 16 | 400 | — | 辅助文字 |
| `label-md` | Inter | 14 / 20 | 500 | — | 按钮、菜单 |
| `label-sm` | Inter | 12 / 16 | 500 | — | Tab、徽章、节拍标签 |
| `code-md` | JetBrains Mono | 13 / 20 | 400 | — | 模型名、API Key 字段、ID |
| `code-sm` | JetBrains Mono | 11 / 16 | 500 | — | 小型 mono 标签 |

### 1.4 间距（4 倍体系）

| Token | px | 用途 |
|-------|----|------|
| `space-xs` | 4 | 图标与文本配对间距 |
| `space-sm` | 8 | 表单内边距、紧凑列表 |
| `space-md` | 12 | 工具栏分组、内联组件 |
| `space-lg` | 16 | 卡片内边距、网格间距 |
| `space-xl` | 24 | 主面板边距、节区分割 |
| `space-2xl` | 32 | 模块分隔、内容区外边距 |

### 1.5 圆角

| Token | px | 用途 |
|-------|----|------|
| `radius-sm` | 2 | 复选框、代码标签 |
| `radius` (DEFAULT) | 4 | Chip、Tag |
| `radius-md` | 6 | 按钮、输入框、菜单 |
| `radius-lg` | 8 | 卡片、面板 |
| `radius-xl` | 12 | Modal、悬浮命令栏 |
| `pill` (full) | 9999 | 圆形头像、状态徽章 |

### 1.6 阴影

| 层级 | Shadow | 用途 |
|------|--------|------|
| **L1 Card** | `0 1px 3px rgba(31,35,48,0.04), 0 1px 2px -1px rgba(31,35,48,0.02)` | 卡片、模块外壳 |
| **L2 Popover** | `0 4px 12px rgba(31,35,48,0.08)` + `1px solid #E5E7EE` | 下拉、菜单、工具面板 |
| **L3 Modal** | `0 12px 32px rgba(31,35,48,0.12)` + scrim `rgba(31,35,48,0.35)` | 居中 Modal |

---

## 2. 组件库

### 2.1 通用组件

| 组件 | 变体 | v0.2 规格 |
|------|------|-----------|
| **Button** | primary / secondary / ghost / destructive | padding `8px 16px`，height `36px`（md） |
| **IconButton** | 圆形 32×32，hover `surface-container-high` | — |
| **Input** | text / password / search / number | height `36px`，border `1px solid #E5E7EE`，focus `ring-2 ring-primary-fixed` |
| **Select** | 单选 / 多选 / 异步搜索 | 同 Input，圆角 6 |
| **Toggle** | 24×14 椭圆，开启主色填充 | — |
| **Tag / Chip** | 默认 / 选中 / 关闭 / 状态 | `radius-pill` 或 `radius-md`，height 22-28 |
| **Card** | 边框 / 悬浮 / 选中态 | radius 8，border `1px solid #E5E7EE` |
| **Modal** | 居中 Modal | radius 12，scrim `rgba(31,35,48,0.35)` |
| **Drawer** | 右侧 460px（ContextPanel 风格） | — |
| **Toast** | success / warning / error / info | — |
| **Tooltip** | 顶 / 底 / 左 / 右 | — |
| **Breadcrumb** | 路径面包屑 | 默认无前缀斜杠 |
| **StatusBadge** | success / warning / danger / neutral / active | pill，22px 高，padding 2/8 |
| **ProgressBar** | 线性 / 圆形 | 主色或 tertiary 填充 |
| **Avatar** | 椭圆 / 圆形 + 字母 fallback | 40×40 或 32×32 |
| **EmptyState** | 图标 + 标题 + 副文 + CTA | — |
| **Skeleton** | 文本 / 卡片 | — |
| **Tabs** | 下划线 / 胶囊 | — |
| **Accordion** | 折叠面板 | — |

### 2.2 业务组件（v0.2 完整列表）

| 组件 | 复用页面 | 关键规格 |
|------|----------|----------|
| **WorkCard** | WorksListPage | 4 列网格；hero 区 渐变背景 + 题材/状态 chip；进度条；进入/继续 按钮 |
| **OutlineTreeNode** | Editor Sidebar | 卷纲 + 章节 嵌套，激活态左侧 `3px × 16px primary` 强调条 |
| **ChapterOutlineCard** | Editor Sidebar | padding 8/12，hover `surface-container` |
| **EditorToolbar** | ChapterEditorPage | 880×48，bottom border，分隔线分组 |
| **EditorAIAgentSuggestionCard** | ChapterEditorPage | radius 12，bg `surface-container-low`，含原句/建议对比、置信度徽章、理由、操作按钮 |
| **BeatCard** | Editor Context Panel | 标题 + 描述 + tag 列表 |
| **CharacterVoiceCard** | Editor Context Panel | 头像 + 姓名 + MBTI 角色定位 + 语气拟合度 |
| **WorldBibleCheckCard** | Editor Context Panel | 条目 + 校验结果 |
| **ForeshadowingCard** | Editor Context Panel | 标题 + 描述 + 计划回收章节 |
| **CriticScoreCard** | Editor Context Panel | 综合评分 + 多画像分布 + 改进建议 |
| **ApiConfigCard** | SettingsApiConfigsPage | 双层结构：头部（Provider + 状态 + Toggle）+ 字段网格 3×2 + Agent 分配 + 操作 |
| **WizardStepper** | NewWorkWizardModal | 4 步圆形节点 + 连接线，已完成打勾 |
| **GenreCard** | NewWorkWizardModal | 6 选项 3×2 网格，含图标 + 题材名 + 设定库计数 |
| **AudiencePaceCard** | NewWorkWizardModal | 3 选项 横向，含描述 + 节拍指数 |
| **StyleKeywordChip** | NewWorkWizardModal | 14 项网格，选中态主色填充 + ✓ |
| **FilterChips** | WorksListPage | 全部 / 草稿 / 写作中 / 已完结 / 已归档 + 计数 |
| **SystemHealthBar** | WorksListPage 底部 | SQLite DB / Chroma 向量库状态行 |
| **MonthlyCostChip** | Header | 本月推理 ¥ + 节省 % |
| **NavRail** | 全局 | 240 宽，含 Logo + 当前作品卡 + 创作空间组 + 作品设定组 + 底部设置 + 健康指示 |
| **GlobalHeader** | 全局 | 64 高，左 breadcrumb + 状态 chip / 中 search / 右 cost + 通知 + 设置 + 头像 |

### 2.3 装饰元素

- **左侧激活强调条**（3px × 16px）：仅 `primary`，用于 OutlineTreeNode 激活态
- **双行浮层背景层**：`surface-container-lowest/95 backdrop-blur-md`，用于编辑器顶栏（编辑时滚动不卡）
- **Mini Bar Chart**：WorksListPage 标题区右侧总字数柱状图（紫色渐变 5 列）

---

## 3. 全局布局壳

### 3.1 标准画布与栅格

| 项 | 值 |
|----|----|
| 画布尺寸 | **1920 × 1080** |
| 侧栏（NavRail） | 240 × 1080 |
| 主工作区（Workspace Shell） | 1680 × 1080 |
| 主栅格列数 | 12 |
| 列宽 | 120 px |
| 列间距 | 24 px |
| 工作区内边距 | 24 px（`space-xl`） |

```
┌────────────────┬─────────────────────────────────────────────────────────┐ 0
│                │                                                         │
│   NavRail      │   Workspace Shell (1680 × 1080)                         │
│   240 × 1080   │   ┌─────────────────────────────────────────────────────┐│
│                │   │ Header (1680 × 64)                                   ││
│   侧栏固定     │   │ fixed top, bg surface-container-lowest/95 blur      ││
│                │   ├─────────────────────────────────────────────────────┤│
│                │   │ Content Viewport (1680 × 1016)                       ││
│                │   │ bg surface-container-low, padding 24                ││
│                │   │                                                     ││
│                │   │                                                     ││
│                │   └─────────────────────────────────────────────────────┘│
└────────────────┴─────────────────────────────────────────────────────────┘ 1080
```

### 3.2 NavRail（240 × 1080，固定）

| 区域 | 位置 (x, y) | 尺寸 (w, h) | 内容 |
|------|-------------|-------------|------|
| 品牌区 | 0, 0 | 240 × 80 | Logo 图标（40×40 radius 12 shadow-sm） + 「织梦·ZhiMeng」+ `v0.2 本地版` 徽章 |
| 当前作品卡 | 24, 104 | 192 × 60 | 标题「当前作品」+ 作品名 + 字数 chip + 📖 图标 |
| 创作空间组 | 24, 196 | 192 × var | 「创作空间」分组 + 3 项（作品库 / 新建向导 / 章节编辑） |
| 作品设定组 | 24, var | 192 × var | 「作品设定」分组 + 3 项（大纲架构 / 角色档案 / 世界观圣经） |
| 底部设置组 | 0, 932 | 240 × var | 系统设置 / 使用文档（顶部分隔线） |
| 服务状态 | 24, 1020 | 192 × 36 | 🟢 动画 + 「127.0.0.1:8000 活跃运行」caption |

**NavRail 行规格**：

| 状态 | 背景 | 文字 | 装饰 |
|------|------|------|------|
| Default | transparent | `on-surface-variant` | — |
| Hover | `rgba(31,35,48,0.04)` 或 `surface-container-high` | `on-surface` | — |
| **Active** | `primary-container` (#E1E0FF) | `on-primary-container` (#2E2EBE) weight 600 | 阴影 `shadow-sm` |

行高 36px，padding `0 12px`，`radius-md`。

### 3.3 GlobalHeader（1680 × 64，fixed）

| 子区 | 位置 (x, y) | 尺寸 (w, h) | 内容 |
|------|-------------|-------------|------|
| 面包屑 | 32, 0 | auto × 64 | 「织梦工作台 / 工作区」（层级用 `/` 分隔）|
| 状态徽章 | 200, 20 | auto × 24 | pill `bg surface-container` + 「本地离线 (SQLite + Chroma)」+ 🟢 图标 |
| 搜索框 | 居中 | 720 × 36 | 🔍 + 「搜索作品、章节、角色或设定 (Cmd+K)」（h-9 bg `surface-container-low`） |
| 本月推理 | 右 200 | auto × 32 | 「本月推理: ¥42.60 节省 92%」chip |
| 导出按钮 | 右 100 | auto × 32 | 📥 + 「导出」secondary |
| 通知 | 64, 16 | 32 × 32 | 🔔 IconButton（右上 8×8 红点） |
| 设置 | 32, 16 | 32 × 32 | ⚙ IconButton |
| 头像 | 0, 16 | 32 × 32 | 圆形主色背景 + 👤 |

背景：`surface-container-lowest/90`，`backdrop-blur-xl`，底边 `1px solid outline-variant/30`，fixed top。

### 3.4 Content Viewport（1680 × 1016）

- 背景：`surface-container-low` (#F2F3FF)
- 外边距：`24px`（`space-xl`）
- 内嵌模块使用白卡（`surface-container-lowest` + border 1px `#E5E7EE` + radius 8）

---

## 4. 导航结构

### 4.1 全局 NavRail 树

```
织梦·ZhiMeng (Logo)
├── 当前作品 (卡) — 读 persist 的当前作品标题与字数；未选择则引导作品库
├── ────────
├── 创作空间
│   ├── 作品库 (Works)              → /works
│   ├── 新建向导 (New Work)          → /works/new
│   └── 章节编辑 (Editor)           → /works/:id/chapters/:chapterId  [默认]
├── ────────
├── 作品设定
│   ├── 大纲架构 (Outline)          → /works/:id/outline
│   ├── 角色档案 (Characters)       → /works/:id/characters
│   └── 世界观圣经 (World Bible)    → /works/:id/world
├── ────────
├── 系统设置 (Settings)            → /settings
├── 使用文档 (Help)                → /help
└── 127.0.0.1:8000 活跃运行        (状态指示)
```

### 4.2 Settings 子导航（仅在 Settings 页可见）

Settings 页采用二级 NavRail 右侧的二级 tab：

```
系统设置 (主区)
├── 常规设置 (General)
├── LLM API 配置                    [默认激活]
├── 写作偏好
├── 外观主题
├── 数据与备份
└── 关于织梦
```

### 4.3 路由表

| Path | 页面 | NavRail 激活 |
|------|------|--------------|
| `/` | HomePage | — |
| `/works` | WorksListPage | 作品库 |
| `/works/new` | NewWorkWizardModal | 新建向导 |
| `/works/:id` | WorkDetailPage | 作品库 |
| `/works/:id/chapters/:chapterId` | ChapterEditorPage | 章节编辑 |
| `/works/:id/outline` | OutlinePage | 大纲架构 |
| `/works/:id/characters` | CharactersPage | 角色档案 |
| `/works/:id/world` | WorldBiblePage | 世界观圣经 |
| `/settings` | SettingsApiConfigsPage | 系统设置 |
| `/settings/general` | SettingsGeneral | 系统设置 |
| `/settings/api-configs` | SettingsApiConfigsPage | 系统设置 |
| `/settings/writing` | SettingsWriting | 系统设置 |
| `/settings/appearance` | SettingsAppearance | 系统设置 |
| `/settings/backup` | SettingsBackup | 系统设置 |
| `/settings/about` | SettingsAbout | 系统设置 |
| `/help` | HelpPage | 使用文档 |

---

## 5. 页面清单

### 状态图例

| 符号 | 含义 |
|------|------|
| ✅ | Figma 已完成（v0.2 HTML 高保真） |
| 📐 | 已 spec，待 Figma 实施 |
| ❌ | 待 spec + Figma + 前端 |
| **v0.2** | 已基于 stitch v0.2 高保真设计 |

---

### P0-1. HomePage（启动 / 欢迎页）

| 项 | 值 |
|----|----|
| 尺寸 | **1920 × 1080** |
| 路由 | `/` |
| Figma 状态 | 📐（复用 NavRail + Header） |

#### 布局分区

| 区域 | 位置 (x, y) | 尺寸 (w, h) | 内容 |
|------|-------------|-------------|------|
| NavRail | 0, 0 | 240 × 1080 | 全局侧栏（无激活项） |
| Header | 240, 0 | 1680 × 64 | 全局顶栏（无面包屑） |
| Main | 240, 64 | 1680 × 1016 | 居中 Hero |

#### Hero 区（1680 × 1016）

| 子区 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| 渐变背景 | 240, 64 | 1680 × 1016 | `surface-container-low` → 中心 radial `primary-container/30` |
| Logo 大图标 | 居中, 280 | 96 × 96 | 主色渐变方块，radius 24，shadow lg |
| 产品名 | 居中, 410 | auto | 「织梦 · ZhiMeng」display 32 |
| 副标题 | 居中, 460 | auto | 「你的本地 AI 小说创作搭档」body-lg 16 |
| 主 CTA | 居中, 520 | 200 × 48 | 「进入作品库 →」primary lg |
| 次级 CTA | 居中, 580 | auto | 「查看文档」ghost |
| 配置提示横幅 | 居中, 660 | 480 × 60 | 「还未配置 API Key？前往设置 →」 + 链接 |
| 底部状态条 | 居中, 1000 | 1680 × 36 | 「v0.2 本地版 · SQLite + Chroma 离线就绪」caption |

#### 组件清单
- [Logo]
- [Button: primary lg] [Button: ghost]
- [EmptyState inline]

#### 状态
- 首次启动（无 API Key）：显示配置提示横幅
- 正常：直接显示 Logo + CTA
- 已加载：检查 `/api/v1/settings/` 切换 CTA 行为

#### API
- `GET /api/v1/settings/`

---

### P0-2. WorksListPage（作品库页） ✅ v0.2

| 项 | 值 |
|----|----|
| 画布 | 1920 × 1080 |
| 尺寸 | 完整 NavRail + Header + Content |
| 路由 | `/works` |
| Figma 状态 | ✅（基于 stitch workslistpage_v0.2） |

#### 布局分区

| 区域 | 位置 (x, y) | 尺寸 (w, h) | 内容 |
|------|-------------|-------------|------|
| NavRail | 0, 0 | 240 × 1080 | 全局侧栏（激活「作品库」） |
| Header | 240, 0 | 1680 × 64 | 全局顶栏（面包屑 「织梦工作台 / 工作区」） |
| Content | 240, 64 | 1680 × 1016 | 见下 |

#### Content 内分区

| 子区 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| 标题区 | 272, 88 | 1616 × 120 | 「我的作品库」headline-lg + 「SQLite Ready」chip + 副文「共 12 本作品 · 本地 SQLite 安全存储 · 离线 RAG 向量索引就绪」 |
| 总字数统计 + 新建按钮 | 1280, 88 | 320 × 120 | 「总字数统计 1,286,400 字」+ 柱状图（5 列紫渐变）+ 「+ 新建作品」primary lg |
| 筛选 Chips 行 | 272, 240 | 1616 × 32 | 全部 (12) / 草稿 (2) / 写作中 (8) / 已完结 (2) / 已归档 (0) + 搜索框 + 排序 |
| 题材 Chips 行 | 272, 296 | 1616 × 32 | 「题材：」+ 全题材 / 玄幻仙侠 / 都市异能 / 青春言情 / 历史架空 / 硬核科幻 |
| 作品卡片网格 | 272, 360 | 1616 × 600 | 4 列 × 1 行 = 4 张 WorkCard |

#### WorkCard（384 × 600）

| 子区 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| Hero 区 | 0, 0 | 384 × 200 | 渐变背景 + 题材 chip（白半透明） + 状态徽章（pill 主色 / 灰） |
| 标题区 | 20, 220 | 344 × 60 | 「《剑来·前传》」headline-md bold + ID `LM-2025-001` code-sm |
| 创作进度 | 20, 296 | 344 × 40 | 「创作进度」+ 「35.2万 / 100万字 (35.2%)」+ ProgressBar |
| 最新章节 | 20, 360 | 344 × 40 | 「第42章 「风起青萍」」label-md + 「2小时前」caption |
| 编目智能体 | 20, 420 | 344 × 40 | 「编目智能体」+ chip 列表 (Claude Opus 5 / DeepSeek-V3) |
| 操作按钮 | 20, 540 | 344 × 36 | 「进入写作」primary + 「…」IconButton |

#### 底部状态条（1616 × 36）

| 内容 |
|------|
| 🗄 SQLite DB: `/data/works/zhimeng.db` 24.8 MB  ·  ✨ Chroma 向量库: 18,920 节点正常  ·  · 🟢 本地自动增量快照 10 分钟前完成  · 完整存储拓扑 → |

#### 组件清单
- [NavRail] [GlobalHeader]
- [WorkCard]
- [FilterChips] [StatusBadge]
- [Input: search]
- [Button: primary lg / secondary / IconButton]
- [ProgressBar]
- [SystemHealthBar]

#### 状态
- 加载：4 张 WorkCard Skeleton
- 空：「还没有作品」EmptyState + 「+ 新建」CTA
- 有数据：4 张完整 WorkCard
- 搜索无结果：「未找到匹配作品」EmptyState

#### API
- `GET /api/v1/works/?page=1&page_size=20&status=`

---

### P0-3. NewWorkWizardModal（新建作品引导） ✅ v0.2

| 项 | 值 |
|----|----|
| 画布 | 1920 × 1080（dimmed 背景） |
| 模态尺寸 | **1012 × 888** |
| 模态位置 | (454, 96)（1920/2 - 1012/2 = 454；1080/2 - 888/2 = 96） |
| 路由 | `/works/new`（浮层在 WorksListPage 之上） |
| Figma 状态 | ✅（基于 stitch newworkwizardmodal_v0.2） |

#### 模态布局

| 区域 | 位置 (x, y) | 尺寸 (w, h) | 内容 |
|------|-------------|-------------|------|
| Backdrop | 0, 0 | 1920 × 1080 | `rgba(31,35,48,0.35)` scrim |
| Modal 外框 | 454, 96 | 1012 × 888 | radius 12，shadow L3 |
| Modal Header | 0, 0 | 1012 × 100 | 「创建新作品」headline-lg + 「New Work Wizard」+ 「Step 2 of 4」chip + ✕ 关闭 |
| Modal 副文 | 32, 76 | 948 × 24 | 「只需 4 步，ZhiMeng 协作 Agent 将为你构建完整的世界观底层、高维角色与第一卷纲。」body-sm |
| Stepper | 32, 110 | 948 × 32 | 4 节点：✅1 基本信息 / 2 风格与受众 (active) / 3 目标设定 / 4 确认创建 |
| Modal Body | 32, 160 | 948 × 580 | 滚动区 |
| Modal Footer | 0, 740 | 1012 × 148 | 底部操作行 |

#### 4 步骤内容（默认显示 Step 2）

##### Step 1：基本信息

| 字段 | 类型 | 必填 |
|------|------|------|
| 作品名 | Input text | ✅ |
| 题材定位 | 6 个 GenreCard（详见 Step 2 风格，但仅显示题材组） | ✅ |
| 一句话简介 | Textarea 3 行 | ❌ |

##### Step 2：风格与受众（当前激活）

| 子区 | 内容 |
|------|------|
| **题材类型定位** | 标题「题材类型定位 *（赋能本地微调权重 & RAG 圣经语料库）」+ 「单选 · 已选 玄幻仙侠」 |
| 6 个 GenreCard（3 × 2 网格） | 玄幻仙侠 / 都市异能 / 青春言情 / 历史架空 / 硬核科幻 / 悬疑惊悚 |
| **目标受众心智与叙事节奏模式** | 「单选 · 决定情节对抗曲线」 |
| 3 个 AudiencePaceCard | 男频热血爽文（98/100 强驱动）/ 女频细腻情感（76/100 情感流）/ 严肃群像正剧（64/100 沉浸式） |
| **核心风格与母题标签** | 「已选 4/8 项」+ 「✨ 让 AI 智能推荐词云」 |
| 14 个 StyleKeywordChip | 热血狂飙 ✓ / 杀伐果断 ✓ / 严谨设定 ✓ / 反转不断 ✓ / 轻松幽默 / 克系克制 / 智商在线 / 单女主纯爱 / 志怪民俗 / 时间循环 / 无敌流 / 慢热种田 / 群像推演 / 末世危机 |
| **灵感速记与一句话立意** (Premise & Pitch) | Textarea 138/1000 字 |

##### Step 3：目标设定

| 字段 | 类型 |
|------|------|
| 目标字数 | Input number（默认 1,000,000） |
| 写作节奏 | Select（每周 3000 / 周末 / 自定义） |
| 模型分配 | 6 个 Agent × 多选 API Config |
| 起始章节名 | Input text |
| 启用世界书 | Toggle |
| 启用角色档案 | Toggle |

##### Step 4：确认创建（Review）

| 内容 |
|------|
| Step 1 / 2 / 3 信息汇总（只读 + 修改链接） |
| 「开始创作」primary lg 居中 |

#### 模态底部 Footer（1012 × 148）

| 左侧 | 右侧 |
|------|------|
| 🟢 本地自动暂存 SQLite · 随时可继续 | 「上一步」secondary + 「下一步：目标设定与大纲初稿 →」primary |

#### 组件清单
- [Modal scrim]
- [WizardStepper]
- [Input / Textarea / Select / Toggle]
- [Chip 可选中]
- [GenreCard]
- [AudiencePaceCard]
- [StyleKeywordChip]
- [Button: primary / secondary]

#### 状态
- 每步：校验中 / 有效
- 最后一步：点「开始创作」POST，loading → 成功后跳 `/works/:newId`

#### API
- `POST /api/v1/works/` + `POST /api/v1/outline-nodes/`（自动）

---

### P0-4. ChapterEditorPage（章节编辑页） ✅ v0.2

| 项 | 值 |
|----|----|
| 画布 | 1920 × 1080 |
| 主区尺寸 | 240 + 1640 = 1880（右侧 40px 内边距） |
| 三栏宽度 | **300 (Outline) + 880 (Editor) + 460 (ContextPanel) = 1640** |
| 路由 | `/works/:id/chapters/:chapterId` |
| Figma 状态 | ✅（基于 stitch chaptereditorpage_v0.2） |

#### 布局分区

| 区域 | 位置 (x, y) | 尺寸 (w, h) | 内容 |
|------|-------------|-------------|------|
| NavRail | 0, 0 | 240 × 1080 | 全局侧栏（激活「章节编辑」） |
| Header | 240, 0 | 1680 × 64 | 全局顶栏 |
| Content | 240, 64 | 1680 × 1016 | 3 栏 |
| **三栏** | | | |
| Outline 栏 | 240, 64 | 300 × 1016 | 大纲树 |
| Editor 栏 | 540, 64 | 880 × 1016 | 编辑器 |
| Context 栏 | 1420, 64 | 460 × 1016 | 上下文与 Agent 协同 |
| 右空白 | 1880, 64 | 40 × 1016 | 内边距 |

#### Outline 栏（300 × 1016）

| 子区 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| 栏头 | 12, 16 | 276 × 72 | 🔱 + 「章节大纲」headline-sm + 「12/36章」pill chip + 检索输入框 |
| 卷纲行 | 16, 96 | 268 × 32 | ▾ + 「第一卷 · 初入江湖」label-md + 「已定稿 12章」chip |
| 章节组（嵌套） | 32, 132 | 252 × var | Ch40 / Ch41 / Ch42(active) / Ch43 / Ch44 |
| 章节激活态 | — | — | bg `primary/10`，左侧 3×16 primary 强调条，标题主色 + 字数主色 + 状态「编辑中」pill |
| 章节默认态 | — | — | bg `surface-container-lowest/70`，hover `surface-container` |
| 章节锁定态 | — | — | opacity 85，icon `lock_clock` + 「待动笔」 |
| 规划中态 | — | — | opacity 60，icon `pending` + 「大纲规划中」 |
| 底部 CTA | 16, 960 | 268 × 60 | 「+ 新建章节 / AI 拆解节拍」primary full width + 「全书共 352,800 字 · 自动同步」caption |

#### Editor 栏（880 × 1016）

| 子区 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| Toolbar | 0, 0 | 880 × 48 | bg `surface-container-lowest/95 backdrop-blur-md`，底边 1px outline-variant |
| 工具按钮组 | 16, 8 | var | B / I / S 分隔 H1 H2 ❝ ☰ 分隔 对白排版 / Diff 比对 |
| 版本选择 | 右 200 | auto | 🕘 + 「v3 (最新版)」+ ▼ |
| 字数计数 | 右 32 | auto | 🟢 + 「3,420 / 目标 5,000 字」code-sm |
| 编辑区 | 0, 48 | 880 × 968 | 滚动 |
| └ 章节元信息 | 80, 32 | 720 × 32 | `CHAPTER 42` chip + 「节拍进度: 114% 超额达标」+ 右「2分钟前自动落盘」 |
| └ 章节标题 | 80, 80 | 720 × 48 | 「第四十二章 风起青萍」display 32 bold |
| └ 分隔 | 80, 156 | 720 × 1 | 底边 |
| └ 段落 × N | 80, 180 | 720 × var | body-lg 16，行高 1.9，indent-8（首行缩进 2em） |
| └ AI 建议内联卡 | 80, var | 720 × var | radius 12，bg `surface-container-low`，含 原句/建议对比、置信度、理由、操作按钮 |
| └ 续写提示条 | 80, var | 720 × var | bg `surface-container-high/60`，🟢 animated + 「Writer Agent 准备续写...」+ 「Tab 采纳续写建议」 |

#### Context 栏（460 × 1016）

| 子区 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| 栏头 | 16, 16 | 428 × 32 | 🛰 + 「上下文与 Agent 协同」headline-sm + 「4 Agents 实时监听」pill |
| **Section: 当前主线节拍** | 16, 56 | 428 × 120 | Story Beat 卡：节拍名 + 描述 + 标签（开场铺垫 / 高潮反转 / 伏笔埋设）+ 进度 chip |
| **Section: 本章登场角色** | 16, 192 | 428 × var | 角色卡列表 × 3：林墨（墨/primary）/ 云浩（浩/tertiary）/ 苏婉（婉/outline，含状态与语气拟合度） |
| **Section: 世界观校验** | 16, var | 428 × var | Bible Check 卡：法则条目 + 「无冲突」chip |
| **Section: 伏笔追踪** | 16, var | 428 × var | Foreshadowing 卡：🔮 + 伏笔标题 + 描述 + 计划回收章节 |
| **Section: Critic 测评** | 16, var | 428 × var | 综合评分 8.8/10 + 2×2 画像分布（爽文读者 9.0 / 考据严谨党 8.5）+ 改进建议 |

#### 组件清单
- [NavRail] [GlobalHeader]
- [EditorToolbar]
- [TipTap Editor]
- [EditorAIAgentSuggestionCard]
- [BeatCard]
- [CharacterVoiceCard]
- [WorldBibleCheckCard]
- [ForeshadowingCard]
- [CriticScoreCard]
- [StatusBadge / Pill / Chip]

#### 状态
- 草稿：StatusBadge「草稿」
- 生成中：工具栏 disabled，编辑器追加流式内容
- 已审：StatusBadge「已审」
- WS 断线：Toast「连接已断开」+ 重试按钮

#### API
- `GET /api/v1/chapters/:id`
- `PATCH /api/v1/chapters/:id`（autosave 30s）
- `WS /ws/generation/:taskId`

---

### P0-5. SettingsApiConfigsPage（LLM API 配置） ✅ v0.2

| 项 | 值 |
|----|----|
| 画布 | 1920 × 1080 |
| 路由 | `/settings` 或 `/settings/api-configs` |
| Figma 状态 | ✅（基于 stitch llm_settingsapiconfigspage_v0.2） |

#### 布局分区

| 区域 | 位置 (x, y) | 尺寸 (w, h) | 内容 |
|------|-------------|-------------|------|
| NavRail | 0, 0 | 240 × 1080 | 全局侧栏（激活「系统设置」） |
| 二级 Settings Nav | 240, 64 | 240 × 952 | 6 项设置 tab |
| Header | 480, 0 | 1440 × 64 | 「系统设置」+ 「v0.2」badge |
| Content | 480, 64 | 1440 × 1016 | 配置卡列表 |

#### 二级 Settings Nav（240 × 952）

| 行 | 标签 | 徽章 | 激活 |
|----|------|------|------|
| 1 | ⚙ 常规设置 | — | — |
| 2 | 🔗 LLM API 配置 | 🟢 | ✅ |
| 3 | ✏ 写作偏好 | — | — |
| 4 | 🎨 外观主题 | — | — |
| 5 | 💾 数据与备份 | SQLite | — |
| 6 | ⓘ 关于织梦 | — | — |

#### Content 内分区

| 子区 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| 页头 | 40, 88 | 1360 × 96 | 「LLM API 配置与模型网关」headline-lg + 「企业级混合调度」chip + 副文 + 「测试全部连通性 (Ping All)」secondary + 「+ 添加 API 配置」primary lg |
| 工具行 | 40, 200 | 1360 × 56 | 搜索框 + 「全部 (4)」/「活跃启用 (3)」/「已禁用 (1)」+ 「排序依据：优先级最高 ▼」 |
| ApiConfigCard × 3 | 40, 280 | 1360 × var | 见下 |

#### ApiConfigCard（1360 × 320）

| 子区 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| 头部 | 20, 16 | 1320 × 48 | Provider 图标 40×40 + 名称 headline-md + 副文 + 「活跃在线 198ms」pill + 「主力直连」chip + 「就绪运作中」caption + Toggle |
| 字段网格 3 × 2 | 20, 88 | 1320 × 132 | API 凭据（含 👁 显示）/ Base URL 端点 / 上下文容量 / 输入成本 / 输出成本 / 并发限流策略 |
| Agent 分配 | 20, 244 | var × 32 | 「受指派 Agent:」+ chip 列表（正文写作主力 Agent / 智能审校 Agent / 大纲策划 Agent / 模拟读者评审 Agent） |
| 操作 | 右 16 | auto | 「显示 Key」「编辑参数」「测试连通性」「删除」(红) |

#### 本地网关状态卡（最底部）

| 内容 |
|------|
| 🟢 本地网关状态: 就绪  · RTX 4090 VRAM: 8.2 / 24 GB  · Ollama port: :11434 |

#### 组件清单
- [NavRail] [GlobalHeader]
- [Settings SubNav]
- [Input: search]
- [FilterChips]
- [ApiConfigCard]
- [StatusBadge]
- [Button: primary lg / secondary / danger]
- [Toggle]
- [ProgressBar]（显存使用率）

#### 状态
- 加载：3 张卡 Skeleton
- 空：「还没有 LLM Key」+ 「添加」CTA
- 有数据：3 张完整 ApiConfigCard
- Ping 全部中：卡片加载 skeleton 覆盖

#### API
- `GET /api/v1/settings/api-configs`
- `POST /api/v1/settings/api-configs`
- `PATCH /api/v1/settings/api-configs/:id`
- `DELETE /api/v1/settings/api-configs/:id`
- `POST /api/v1/settings/api-configs/:id/reveal`
- `POST /api/v1/settings/api-configs/ping-all`

---

### P1-1. SettingsGeneral（设置 → 常规） 📐

| 项 | 值 |
|----|----|
| 尺寸 | 1920 × 1080 |
| 路由 | `/settings/general` |
| Figma 状态 | 📐 |

#### Content（1440 × 1016）

| 分组 | 字段 |
|------|------|
| **界面偏好** | 默认语言 / 默认字体大小（Slider 12–18）/ 编辑器宽度（Radio 中/宽/超宽） |
| **写作默认** | 默认目标字数 / 自动保存间隔（Select 10/30/60/120s）/ 起始章节名 |
| **智能默认** | 默认模型（下拉列出已配置 API）/ 默认预设 / 默认风格关键词 |
| **高级** | 启用调试日志（Toggle）/ 启用遥测（Toggle + 「默认关闭」说明） |

---

### P1-2. SettingsWriting（设置 → 写作偏好） 📐

| 项 | 值 |
|----|----|
| 尺寸 | 1920 × 1080 |
| 路由 | `/settings/writing` |

#### Content（1440 × 1016）

| 分组 | 字段 |
|------|------|
| **默认文风** | 默认风格关键词（14 项 Chip 多选）/ 默认受众（3 选 1） |
| **叙事偏好** | 默认视角（Radio 第一人称/第三人称/全知）/ 默认段落长度（Radio 短/中/长）/ 对话占比（Slider 0–100%） |
| **生成行为** | 生成前自动检索记忆（Toggle）/ 单章最大尝试次数（Input 1–5）/ 失败时回退模型 |

---

### P1-3. WorkDetailPage（作品详情 / 总览） 📐

| 项 | 值 |
|----|----|
| 尺寸 | 1920 × 1080 |
| 路由 | `/works/:workId` |

#### 布局分区

| 区域 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| NavRail | 0, 0 | 240 × 1080 | 全局（激活「作品库」） |
| Header | 240, 0 | 1680 × 64 | 全局 |
| Hero 区 | 240, 64 | 1680 × 320 | 大封面渐变 + 标题 + 副标 + Chip 组 + 进度条 + 「续写」primary lg |
| Tabs 行 | 240, 384 | 1680 × 56 | 章节 / 大纲 / 角色 / 世界观 / 统计 |
| Tab 内容区 | 240, 440 | 1680 × 640 | 当前 Tab 内容 |

#### Hero 区（1680 × 320）

| 子区 | 内容 |
|------|------|
| 封面背景 | 渐变 + 噪声纹理 |
| 标题 | 「凌天传说」display 32 bold + 「一个废柴少年逆袭的故事」body-lg |
| 标签 | Chip：玄幻 / 写作中 / 35.2万字 |
| 进度条 | 主色填充 + 「3.5%」caption |
| 操作 | 「续写」primary lg + 「…」IconButton |

#### Tab = 章节（默认）

| 内容 |
|------|
| 12 行表格：# / 标题 / 状态 / 字数 / 最后编辑 / 操作 |

#### Tab = 大纲 / 角色 / 世界观 / 统计

各 Tab 摘要视图，详见独立页面。

---

### P1-4. OutlinePage（作品大纲页） 📐

| 项 | 值 |
|----|----|
| 尺寸 | 1920 × 1080 |
| 路由 | `/works/:workId/outline` |

#### 布局分区

| 区域 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| NavRail | 0, 0 | 240 × 1080 | 全局（激活「大纲架构」） |
| Header | 240, 0 | 1680 × 64 | 全局 + 「AI 生成大纲」primary |
| Content | 240, 64 | 1680 × 1016 | 卷纲树 |

#### 树区（1680 × 1016）

| 子区 | 内容 |
|------|------|
| 顶部操作 | 「+ 新建卷」+ 「展开全部」+ 「折叠全部」 |
| 卷卡 × N | 每卷一卡：标题 + 描述 + 进度条 + 节拍列表（拖拽手柄 + 标题 + 出场角色 Chip + 操作） |
| 节拍行 | 拖拽手柄 + 标题 + 出场角色 + 「关联章节」「删除」 |

---

### P1-5. CharactersPage（角色档案页） 📐

| 项 | 值 |
|----|----|
| 尺寸 | 1920 × 1080 |
| 路由 | `/works/:workId/characters` |

#### 布局分区

| 区域 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| NavRail | 0, 0 | 240 × 1080 | 全局（激活「角色档案」） |
| Header | 240, 0 | 1680 × 64 | 全局 + 「+ 新建角色」+ 「查看人物关系图」 |
| 角色网格 | 272, 88 | 1616 × var | 4 列 × N 行 |

#### 角色卡（384 × 240）

| 子区 | 内容 |
|------|------|
| 头像 | 64×64 圆头像 + 名字首字（primary 背景） |
| 姓名 | headline-sm |
| 角色 | Chip「主角 / INTJ」 |
| 简介 | 2 行省略 |
| 操作 | 悬浮「编辑」「删除」 |

---

### P1-6. WorldBiblePage（世界观设定页） 📐

| 项 | 值 |
|----|----|
| 尺寸 | 1920 × 1080 |
| 路由 | `/works/:workId/world` |

#### 布局分区

| 区域 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| NavRail | 0, 0 | 240 × 1080 | 全局（激活「世界观圣经」） |
| Header | 240, 0 | 1680 × 64 | 全局 + 「AI 辅助生成」 |
| Tabs | 240, 120 | 1680 × 48 | 地理 / 势力 / 修炼体系 / 时间线 / 关键物件 |
| Tab 内容 | 240, 168 | 1680 × 912 | 见下 |

#### Tab = 地理（默认）

| 内容 |
|------|
| 地区卡网格：名称 + 简介 + 关键地点数 + 「展开」按钮 |

#### Tab = 势力

类似角色页：势力卡片网格。

#### Tab = 修炼体系

树形结构：境界从低到高，每境界有名称 + 描述 + 关键能力。

#### Tab = 时间线

垂直时间轴：年份 + 事件描述。

#### Tab = 关键物件

类似角色页：物品卡网格。

---

### P2-1. SettingsAppearance（设置 → 外观主题） 📐

| 项 | 值 |
|----|----|
| 路由 | `/settings/appearance` |

#### Content（1440 × 1016）

| 分组 | 内容 |
|------|------|
| 主题 | Radio：浅色 / 深色 / 跟随系统 |
| 主色 | 色板网格（6 色），单选 |
| 字体大小 | Slider 12–18 |
| 编辑器宽度 | Radio：中等 880 / 宽 1040 / 超宽 1200 |
| 预览 | 右侧 600×600 实时预览面板（迷你编辑器） |

---

### P2-2. SettingsBackup（设置 → 数据与备份） 📐

| 项 | 值 |
|----|----|
| 路由 | `/settings/backup` |

#### Content（1440 × 1016）

| 分组 | 内容 |
|------|------|
| 手动备份 | 「立即备份」Primary + 上次备份时间 |
| 自动备份 | Toggle + Select：每天 / 每周 / 每月 + 时间选择 |
| 保留策略 | Input：保留 N 份，超出自动清理 |
| 备份目录 | 显示当前路径 + 「更改…」Secondary |
| 历史备份 | 列表：时间 + 大小 + 「恢复」「删除」 |
| 危险区 | 「清理全部数据」Danger 按钮 + 二次确认 Modal |

---

### P2-3. HelpPage（帮助中心） 📐

| 项 | 值 |
|----|----|
| 路由 | `/help` |

#### 布局

| 子区 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| NavRail | 0, 0 | 240 × 1080 | 全局（激活「使用文档」） |
| Header | 240, 0 | 1680 × 64 | 全局 |
| 顶部 Banner | 272, 88 | 1616 × 200 | 大标题 + 搜索框 |
| 双栏 | 272, 320 | 1616 × var | 左 800「快速入门」+ 右 800「常见问题」 |
| 快捷键表 | 272, 760 | 1616 × 220 | 表格：操作 / Mac / Win |
| 底部链接 | 272, 1000 | 1616 × auto | 文档站 / GitHub / Email |

---

### P3-1. SettingsAbout（设置 → 关于） 📐

- 版本号、MIT 许可证、致谢、第三方依赖列表（含许可证）
- 路由：`/settings/about`

### P3-2. OnboardingTour（首次启动引导蒙层） 📐

- 4 步 Coach Mark：欢迎 → 作品库 → 编辑器 → 设置
- 半透明黑色遮罩 + 镂空高亮区 + 浮动说明卡 + 「下一步」「跳过」

### P3-3. NotFoundPage 404 📐

| 区域 | 位置 | 尺寸 | 内容 |
|------|------|------|------|
| 居中 | 760, 380 | 400 × 320 | 404 display 96 + 「页面走丢了」headline-md + 「返回首页」Primary |

---

## 6. 状态矩阵

| 页面 | 加载态 | 空态 | 错误态 | 部分错误态 |
|------|--------|------|--------|------------|
| HomePage | 全屏 Skeleton | 首次启动引导 | Toast | — |
| WorksListPage | 4 卡 Skeleton | 「还没有作品」+「+ 新建」 | Toast + 重试 | 部分加载 |
| NewWorkWizardModal | — | — | 每步校验错误 | — |
| ChapterEditorPage | 工具栏禁用 | 「暂无章节」 | WS 断线 Toast | 段落保存失败 |
| SettingsApiConfigs | 卡片 Skeleton | 「还没有 LLM Key」+「添加」 | Toast | 删除失败回滚 |
| OutlinePage | 树 Skeleton | 「暂无大纲」+「AI 生成」 | Toast | 节点展开失败 |
| CharactersPage | 卡 Skeleton | 「暂无角色」+「+ 新建」 | Toast | — |
| WorldBiblePage | Tab Skeleton | 「暂无设定」+「AI 辅助」 | Toast | — |

---

## 7. Figma 文件结构

```
ZhiMeng UI Mockups (fileKey: 3KeVqfxy14BQja5JBx5UgM)
├── Page 1: 全局
│   ├── Design Tokens (ColorCollection "ZhiMeng Colors" — 19 vars)
│   └── Components (待沉淀：Button / Card / Tag / Input ...)
├── Frame: 作品库页 - Works List          (D2 ✅ 基于 v0.2 设计)
├── Frame: 章节编辑页 - Chapter Editor    (D3 ✅ 基于 v0.2 设计)
├── Frame: 新建作品引导 - New Work Wizard (D4 ✅ 基于 v0.2 设计)
├── Frame: LLM API 配置 - Settings        (D5 ✅ 基于 v0.2 设计)
├── Frame: 首页 - Home                    (P0 📐)
├── Frame: 作品详情 - Work Detail         (P1 📐)
├── Frame: 大纲页 - Outline                (P1 📐)
├── Frame: 角色页 - Characters            (P1 📐)
├── Frame: 世界观页 - World Bible         (P1 📐)
├── Frame: 设置-常规 - Settings General   (P1 📐)
├── Frame: 设置-写作偏好 - Writing        (P1 📐)
├── Frame: 设置-外观 - Appearance         (P2 📐)
├── Frame: 设置-备份 - Backup             (P2 📐)
├── Frame: 帮助页 - Help                  (P2 📐)
├── Frame: 设置-关于 - About              (P3 📐)
└── Frame: 404                            (P3 📐)
```

### 节点 ID 速查

| 节点 | ID |
|------|-----|
| File Key | `3KeVqfxy14BQja5JBx5UgM` |
| D2 作品列表页 | `1:2` |
| D3 章节编辑页 | `2:170` |
| D4 新建作品引导 | `7:2` |
| D5 设置页 | （待更新至 v0.2 设计） |
| ColorCollection "ZhiMeng Colors" | `VariableCollectionId:1:1` |
| primary 变量 | `VariableID:1:3` |

---

## 8. 未决问题

| # | 问题 | 候选方案 | 待定 |
|---|------|----------|------|
| 1 | 深色模式范围 | 仅主界面 / 整个 app 包括编辑器 | 待评审 |
| 2 | TipTap 编辑器是否支持 Markdown 快捷输入 | 支持 / 不支持 | 待评审 |
| 3 | 流式生成的撤销粒度 | 字符级 / 段落级 | 待评审 |
| 4 | 移动端是否支持 | 不支持（仅 Web） | PRD 已声明 out-of-scope |
| 5 | 作品封面自定义上传 | 自动渐变 / 允许上传 | 已实现渐变 |
| 6 | AI 建议的采纳方式 | 原地替换 / 弹 Diff Modal | 当前 v0.2 为内联卡 + 3 按钮 |
| 7 | 离线模式 | 禁用 AI / 提示离线 | v0.2 默认显示本地离线 chip |
| 8 | Settings 默认 Tab | 通用 / LLM API | v0.2 默认 LLM API |
| 9 | 大纲页是否需要单独的「分卷」管理 | 是 / 否 | v0.2 Outline 页采用卷卡 + 节拍嵌套 |
| 10 | Editor 三栏 vs 两栏 | v0.2 已确认 3 栏（300+880+460） | ✅ |
| 11 | 全局 NavRail 是否常驻 | v0.2 采用常驻（无收起） | ✅ |
| 12 | 全局 Header 是否常驻 | v0.2 采用常驻 fixed blur | ✅ |

---

## 附录 A：页面优先级一览

| 优先级 | 页面数 | 已 spec | 待 spec | 备注 |
|--------|--------|---------|---------|------|
| **P0** | 5 | 5 | 0 | MVP 必需 |
| **P1** | 6 | 6 | 0 | 次核心 |
| **P2** | 3 | 3 | 0 | 增强 |
| **P3** | 3 | 3 | 0 | 边缘 |
| **合计** | **17** | **17** | **0** | — |

## 附录 B：参考文档

- [PRD.md](PRD.md) — 产品需求
- [ARCHITECTURE.md](ARCHITECTURE.md) — 系统架构
- [API.md](API.md) — REST + WS 协议
- [GETTING_STARTED.md](GETTING_STARTED.md) — 启动文档
- [CONTRIBUTING.md](CONTRIBUTING.md) — 贡献指南
- [FRONTEND_REQUIREMENTS.md](FRONTEND_REQUIREMENTS.md) — 前端需求
- [stitch_zhimeng_novel_studio/](../stitch_zhimeng_novel_studio/) — v0.2 设计参考（4 个高保真 HTML）
- [stitch_zhimeng_novel_studio/precision_workspace/DESIGN.md](../stitch_zhimeng_novel_studio/precision_workspace/DESIGN.md) — 设计系统规范

## 附录 C：变更日志

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.1 | 2026-09-11 | 初稿，登记 17 个页面，1440×900 画布 |
| 0.2 | 2026-09-11 | 统一画布至 1920×1080，补充每个页面的布局分区表与组件清单 |
| **0.3** | **2026-09-12** | **基于 stitch_zhimeng_novel_studio v0.2 设计参考全面重构：M3 色板、Material Design 字体体系、NavRail + GlobalHeader 全局布局壳、P0-4 三栏（300+880+460）、P0-5 ApiConfigCard 完整规格、P1-P3 全部 spec 补齐** |

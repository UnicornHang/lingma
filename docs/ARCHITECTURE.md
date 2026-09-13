# ZhiMeng 架构设计

> 版本 0.1.0 · 2026-09-10

本文档描述织梦小说工坊（ZhiMeng Novel Studio）的整体架构、模块边界、数据流与关键技术决策。开发人员应先读此文档，再读具体模块的需求文档。

---

## 目录

1. [顶层架构](#1-顶层架构)
2. [模块划分](#2-模块划分)
3. [数据模型](#3-数据模型)
4. [Agent 编排](#4-agent-编排)
5. [数据流](#5-数据流)
6. [关键技术决策](#6-关键技术决策)
7. [部署架构](#7-部署架构)
8. [安全模型](#8-安全模型)
9. [性能与扩展](#9-性能与扩展)
10. [演进路线](#10-演进路线)

---

## 1. 顶层架构

ZhiMeng 采用经典的 **前后端分离 + 本地一体化部署** 结构：

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (React SPA)                       │
│  React 18 + Antd 5 + TipTap + Tailwind + Zustand + RQ      │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP REST + WebSocket
┌──────────────────────▼───────────────────────────────────────┐
│                     Nginx (反向代理)                          │
│      /api/*  /ws/*  →  backend:8000                           │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│             FastAPI Backend (Python 3.11+)                    │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐   │
│  │  REST API   │ │  WebSocket   │ │   Agent Orchestrator │   │
│  └──────┬──────┘ └──────┬───────┘ └──────────┬───────────┘   │
│         │               │                    │               │
│  ┌──────▼───────────────▼────────────────────▼───────────┐   │
│  │            Service Layer (业务服务)                     │   │
│  │  WorkService / ChapterService / SettingService        │   │
│  │  CryptoService / LLMService                            │   │
│  └──────┬──────────────────┬──────────────────┬──────────┘   │
│         │                  │                  │              │
│  ┌──────▼─────┐    ┌───────▼────────┐   ┌─────▼─────────┐   │
│  │  SQLite    │    │  Chroma Vector │   │  LLM Provider │   │
│  │  (SQLAlchemy)│   │     Store     │   │  (LiteLLM)    │   │
│  └────────────┘    └────────────────┘   └───────────────┘   │
└──────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                  LLM API / 本地模型                          │
│      OpenAI / Anthropic / DeepSeek / Ollama / 自定义          │
└──────────────────────────────────────────────────────────────┘
```

**核心设计原则**

- **本地优先**：所有作品数据、API Key、向量库均存储在用户本地磁盘，零云端上传
- **协议统一**：前端只与后端 HTTP/WS 通信，LLM 调用由后端代理
- **模块解耦**：Agent 层通过统一接口（`BaseAgent`）接入，方便替换实现
- **可观测**：所有生成任务产生 Task 记录，支持查询、重试、取消

---

## 2. 模块划分

### 2.1 后端模块（backend/app/）

```
app/
├── main.py                # FastAPI 应用入口、lifespan、CORS、异常处理
├── config.py              # Pydantic Settings 配置
├── deps.py                # FastAPI 依赖注入（DB Session）
├── api/                   # HTTP/WS 路由
│   ├── v1/
│   │   ├── works.py       # 作品 CRUD
│   │   ├── chapters.py    # 章节 CRUD
│   │   └── settings.py    # 设置 + API 配置
│   └── ws/
│       └── generation.py  # 流式生成 WS
├── agents/                # AI Agent 实现
│   ├── base.py            # BaseAgent 抽象类
│   ├── plot_agent.py      # 剧情
│   ├── world_agent.py     # 世界观
│   ├── character_agent.py # 角色
│   ├── writer_agent.py    # 写作
│   ├── editor_agent.py    # 润色
│   └── critic_agent.py    # 审稿
├── orchestrator/
│   └── orchestrator.py    # 流水线编排（当前线性，后续 LangGraph）
├── services/              # 业务服务层
│   ├── work_service.py
│   ├── chapter_service.py
│   ├── setting_service.py
│   ├── crypto_service.py  # API Key 加密
│   └── llm_service.py     # LLM 适配（基于 LiteLLM 接口）
├── models/                # SQLAlchemy ORM 模型
├── schemas/               # Pydantic Schema（API DTO）
├── db/session.py          # 异步 DB Session
└── utils/                 # 工具
```

### 2.2 前端模块（frontend/src/）

```
src/
├── main.tsx              # 入口（Provider 装配）
├── App.tsx               # 根组件
├── router.tsx            # 路由表（懒加载）
├── api/                  # HTTP/WS 客户端
│   ├── client.ts         # Axios 实例 + 拦截器
│   └── works.ts          # 业务 API 封装
├── stores/               # Zustand 全局状态
│   └── useUIStore.ts     # 主题/侧边栏/Loading
├── components/           # 通用组件
│   └── Layout/AppLayout.tsx
├── pages/                # 路由页面
│   ├── HomePage.tsx
│   ├── WorksListPage.tsx
│   ├── SettingsPage.tsx
│   └── NotFoundPage.tsx
├── types/                # TypeScript 类型
└── styles/globals.css    # 全局样式 + Tailwind 入口
```

---

## 3. 数据模型

### 3.1 ER 概览

```
            ┌──────────┐
            │  Setting │ (单例 key-value)
            └──────────┘

            ┌──────────────┐
            │  APIConfig   │ (LLM 配置，Key 加密)
            └──────────────┘

            ┌──────────────┐
            │     Work     │ ◀─────────┐
            │──────────────│           │
            │ id           │           │
            │ title        │           │
            │ genre        │           │
            │ status       │           │
            │ target_words │           │
            └──────┬───────┘           │
                   │                   │
       ┌───────────┼───────────┬───────┴────────┐
       ▼           ▼           ▼                ▼
  ┌─────────┐ ┌─────────┐ ┌────────┐   ┌──────────────┐
  │ Chapter │ │Character│ │Outline │   │ WorldBible   │
  │─────────│ │─────────│ │  Node  │   │──────────────│
  │ id      │ │ id      │ │ id     │   │ id           │
  │ work_id │ │ work_id │ │work_id │   │ work_id(uniq)│
  │ title   │ │ name    │ │ parent │   │ geography    │
  │ content │ │ role    │ │ type   │   │ power_system │
  │ status  │ │basic... │ │ title  │   │ raw_text     │
  │ words   │ │person...│ │beats...│   └──────────────┘
  │ version │ └─────────┘ └────────┘
  └────┬────┘
       │
       ▼
  ┌──────────────┐
  │ChapterVersion│ (历史快照)
  └──────────────┘

  ┌──────────────────┐
  │ GenerationTask   │ (异步任务追踪)
  │──────────────────│
  │ work_id          │
  │ task_type        │
  │ status           │
  │ progress         │
  │ result           │
  └──────────────────┘
```

### 3.2 关键设计

- **Work** 是顶层聚合根，删除作品时级联清理所有子表
- **ChapterVersion** 保留每次保存/生成的快照，支持 diff 与回滚
- **GenerationTask** 跟踪所有 Agent 异步调用，便于前端轮询或 WS 订阅
- **WorldBible** 一对一关联作品（`uselist=False`），包含结构化字段 + 自然语言描述
- 所有时间戳（`created_at` / `updated_at`）由 `TimestampMixin` 自动管理
- 所有主键使用 UUID（`UUIDMixin`），避免 ID 可枚举

---

## 4. Agent 编排

### 4.1 Agent 角色

| Agent | 类型 | 职责 | 输入 | 输出 |
|------|------|------|------|------|
| **Plot** | 规划 | 总纲/卷纲/节拍设计 | logline / 一句话简介 | 分卷结构 + 节拍列表 |
| **World** | 规划 | 世界观圣经 | 题材 + 灵感关键词 | 地理/势力/修炼体系 |
| **Character** | 规划 | 角色档案 | 大纲 + 主题 | 角色卡（多张） |
| **Writer** | 生成 | 章节正文 | 大纲节点 + 上下文 + 前章 | TipTap JSON + plain text |
| **Editor** | 编辑 | 风格润色 | 章节草稿 | 润色版本 + 修改建议 |
| **Critic** | 评估 | 质量评估 | 章节正文 + 上下文 | 评分 + 问题清单 |

### 4.2 编排流水线

默认 6 步流水线（`Orchestrator.DEFAULT_PIPELINE`）：

```
plot ──► world ──► character ──► writer ──► editor ──► critic
```

每个 Agent 接收：
- 初始 `context`（work_id, logline 等）
- 前序 Agent 的输出（`previous_results`）

并产出结构化 JSON 结果。

### 4.3 演进路线

| 阶段 | 实现 | 状态 |
|------|------|------|
| MVP | 串行调用，固定流水线 | ✅ 已实现 |
| V1 | LangGraph 状态机，支持分支 / 回滚 | 📋 待开发 |
| V2 | 多 Writer 并行 + Critic 仲裁 | 📋 待开发 |
| V3 | 自适应编排（基于任务类型选择 Agent 子集） | 📋 待开发 |

---

## 5. 数据流

### 5.1 创建作品

```
Browser                       Backend                       DB
   │ POST /api/v1/works/        │                          │
   │ ─────────────────────────► │ validate (Pydantic)      │
   │                            │ ─────────────────────►   │
   │                            │   INSERT works           │
   │                            │ ◄─────────────────────   │
   │ ◄─────── 201 + Work ────── │                          │
```

### 5.2 生成章节（流式）

```
Browser                 Backend                    LLM
   │ POST chapter          │                          │
   │ ───────────────────►  │ create Task              │
   │ WS /ws/generation/{}  │                          │
   │ ───────────────────►  │                          │
   │                       │ LLM.stream()             │
   │                       │ ──────────────────────►  │
   │ ◄── {delta} ───────── │ ◄── chunk ────────────── │
   │ ◄── {delta} ───────── │ ◄── chunk ────────────── │
   │ ◄── {done} ────────── │ ◄── final ─────────────── │
   │ save to DB            │                          │
```

### 5.3 编辑保存（增量）

```
Browser TipTap ──autosave──► /api/v1/chapters/{id} ──► SQL UPDATE
                          ◄─── 200 + new version ────
```

---

## 6. 关键技术决策

### 6.1 为什么选 FastAPI

- **异步原生**：与 SQLAlchemy 2.0 async / 异步 LLM SDK 契合
- **类型驱动**：Pydantic 自动校验 + OpenAPI 文档
- **WS 一等公民**：流式生成无需额外库
- **生态成熟**：LangChain / LangGraph / LiteLLM 均有 Python SDK

### 6.2 为什么选 SQLAlchemy 2.0 异步

- **类型安全**：`Mapped[]` + `mapped_column()` 比 1.x 简洁
- **async session**：与 FastAPI 异步路由天然匹配
- **Alembic 兼容**：迁移工具稳定

### 6.3 为什么用 LiteLLM 接口

- **统一抽象**：一个 `LLMService` 适配 OpenAI / Anthropic / DeepSeek / Ollama / 自定义
- **未来无痛切换**：真实集成时只需替换 `llm_service.py` 内部实现

### 6.4 为什么用 TipTap

- **结构化存储**：输出 JSON 而非 HTML，便于 diff / RAG / 版本控制
- **扩展性**：自定义节点（人物引用、伏笔标记）通过扩展实现
- **协作潜力**：与 Yjs 协同可实现多人共创

### 6.5 为什么用 Zustand 而不是 Redux

- **更轻量**：API 极简（`create` + hook）
- **够用**：本项目全局状态简单（主题、侧边栏），无需 Redux 模板代码
- **持久化**：内置 `persist` 中间件即可写 localStorage

### 6.6 为什么 AES-256 + PBKDF2

- **Fernet（AES-128-CBC + HMAC）** 对单机本地存储已足够
- **PBKDF2 派生**：APP_SECRET 不直接当 Key，额外加盐 + 48 万次迭代抵御离线爆破
- **可演进**：接口 `encrypt() / decrypt()` 抽象，未来可换 AES-256-GCM

---

## 7. 部署架构

### 7.1 单机一体化（推荐）

```
Docker Compose:
┌─────────────────────────────────┐
│  zhimeng-frontend (nginx:80)    │ ── 静态文件 + 反向代理
│  zhimeng-backend (python:8000)   │ ── FastAPI
│  zhimeng-data (volume)           │ ── SQLite + Chroma + 上传
└─────────────────────────────────┘
```

启动：
```bash
./scripts/start.sh    # 一键启动
# → http://localhost:7860
```

### 7.2 配置文件

根目录 `.env`：
```env
APP_ENV=production
APP_SECRET=<随机 32+ 字符串>
DATABASE_URL=sqlite+aiosqlite:////app/data/works/zhimeng.db
VECTOR_STORE_PATH=/app/data/vector_store
CORS_ORIGINS=["http://localhost:7860"]
```

### 7.3 数据目录

```
data/
├── works/
│   └── zhimeng.db           # SQLite 主库
├── vector_store/           # Chroma 持久化
│   └── <work_id>/
│       └── chroma.sqlite3
├── uploads/                # 用户上传（图片、参考文档）
└── logs/
    └── backend.log
```

### 7.4 备份策略

`scripts/backup.sh` 每日打包 `data/` 到 `backups/`，保留 7 天。

---

## 8. 安全模型

### 8.1 敏感数据

| 数据 | 存储方式 | 加密 |
|------|----------|------|
| 用户作品正文 | SQLite JSON 字段 | 否（本地可信环境） |
| API Key | SQLite Text | ✅ AES + PBKDF2 |
| APP_SECRET | 环境变量 / `.env` | 否（用户保管） |
| 上传文件 | 本地 `data/uploads/` | 否 |

### 8.2 API Key 生命周期

```
用户输入明文 ──encrypt()──► 密文存 DB ──reveal 接口──► 一次性明文返回
                                              ↓
                                       后端 LLMService
                                       调用时解密使用
```

明文 Key **不进入任何日志**；`reveal` 端点要求用户明确触发。

### 8.3 网络暴露面

默认仅监听 `127.0.0.1`，如需局域网共享需：
- 设置 `CORS_ORIGINS` 包含客户端 IP
- 部署时建议挂载 Nginx + Basic Auth

---

## 9. 性能与扩展

### 9.1 当前性能基线（单机）

| 操作 | 目标耗时 |
|------|----------|
| 列表查询（100 作品） | < 50ms |
| 章节保存 | < 100ms |
| RAG 检索 Top-5 | < 200ms |
| 章节生成（3000 字） | 30-90s（取决于 LLM） |

### 9.2 扩展点

- **水平扩展**：FastAPI workers + Redis 队列（`arq` 已在 `pyproject.toml`）
- **向量库**：Chroma → Qdrant / Milvus（百万级文档）
- **缓存层**：常用作品 / 大纲读 Redis
- **CDN**：上传图片挂 CDN（可选）

### 9.3 LLM 成本控制

- **Token 预算**：每次生成前预估，超限拒绝
- **上下文压缩**：旧章节摘要替代原文
- **模型分层**：大纲用小模型，正文用大模型

---

## 10. 演进路线

```
v0.1 (当前 MVP)
 ├─ ✅ 基础 CRUD（作品 / 章节 / 设置 / API 配置）
 ├─ ✅ 加密存储
 ├─ ✅ 6 个 Agent 占位实现
 ├─ ✅ WebSocket 流式生成（Mock LLM）
 └─ ✅ 单元测试 25 个全通过

v0.5 (1-2 月)
 ├─ ⏳ 接入真实 LLM（LiteLLM 完整集成）
 ├─ ⏳ Plot / Character Agent 完整实现
 ├─ ⏳ 章节编辑器 + TipTap 双向绑定
 └─ ⏳ 简单 RAG（基于 Chroma）

v1.0 (3-4 月)
 ├─ ⏳ 全 6 Agent 端到端流水线
 ├─ ⏳ 向量记忆系统（角色 / 世界 / 伏笔）
 ├─ ⏳ LangGraph 编排器
 └─ ⏳ 多用户、多设备（同步协议）

v2.0 (6+ 月)
 ├─ ⏳ 多人协作（CRDT）
 ├─ ⏳ 智能 Prompt 优化器
 ├─ ⏳ 多语言支持
 └─ ⏳ 移动端 PWA
```

---

## 附录 A：术语表

| 术语 | 含义 |
|------|------|
| **Agent** | 单一职责的 AI 单元（如 PlotAgent），实现 `BaseAgent` 接口 |
| **Orchestrator** | 协调多个 Agent 执行的引擎 |
| **RAG** | Retrieval-Augmented Generation，向量检索增强生成 |
| **TipTap** | 基于 ProseMirror 的富文本编辑器框架 |
| **Fernet** | cryptography 库的加密方案（AES + HMAC + 时间戳） |
| **Pipeline** | Agent 链式调用序列 |

## 附录 B：参考文档

- [PRD.md](PRD.md) - 产品需求文档
- [BACKEND_REQUIREMENTS.md](BACKEND_REQUIREMENTS.md) - 后端开发需求
- [FRONTEND_REQUIREMENTS.md](FRONTEND_REQUIREMENTS.md) - 前端开发需求
- [GETTING_STARTED.md](GETTING_STARTED.md) - 快速启动
- [API.md](API.md) - API 参考
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
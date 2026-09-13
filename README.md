# 织梦 (ZhiMeng) Novel Studio

> 一款零门槛、本地化、隐私安全的 AI 辅助小说创作平台

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![React](https://img.shields.io/badge/react-18-blue.svg)](https://react.dev)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com)

ZhiMeng 是为小说作者、写作爱好者、技术创作者打造的 AI 写作协作平台。通过 6 个专业 Agent 的协作，提供从大纲、世界观、角色设计到章节生成、编辑润色、读者评审的完整创作工作流。

**核心特点**：

- 🔒 **完全本地化** — 所有数据存本地，零云端上传
- 🤖 **多 Agent 协作** — Plot / World / Character / Writer / Editor / Critic
- 💡 **长期一致性** — 基于向量库的 RAG 记忆系统
- 🎨 **专业富文本** — 基于 TipTap 的所见即所得编辑器
- 🚀 **一键部署** — `docker compose up -d` 即可启动

---

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose v2+
- 至少 8GB 可用内存
- 至少 10GB 可用磁盘空间

### 启动

```bash
# 1. 克隆项目
git clone https://github.com/UnicornHang/zhimeng.git
cd zhimeng

# 2. 复制环境变量模板
cp .env.example .env

# 3. 编辑 .env，配置你的 LLM API Key（至少一个）
vim .env

# 4. 一键启动
./scripts/start.sh
```

启动完成后访问：**http://localhost:7860**

### 停止

```bash
./scripts/stop.sh
```

### 备份数据

```bash
./scripts/backup.sh
# 输出在 ./backups/ 目录
```

---

## 项目结构

```
zhimeng/
├── backend/                      # Python 后端 (FastAPI)
│   ├── app/
│   │   ├── api/                  # REST + WebSocket
│   │   ├── agents/               # 6 个 AI Agent
│   │   ├── core/                 # LLM Gateway / RAG
│   │   ├── models/               # SQLAlchemy 数据模型
│   │   ├── schemas/              # Pydantic Schema
│   │   ├── orchestrator/         # Agent 编排
│   │   └── services/             # 业务逻辑
│   ├── alembic/                  # DB 迁移
│   ├── tests/
│   └── Dockerfile
│
├── frontend/                     # React 前端 (Vite + TypeScript)
│   ├── src/
│   │   ├── components/           # 通用组件
│   │   ├── pages/                # 页面
│   │   ├── stores/               # Zustand 状态
│   │   ├── api/                  # API 客户端
│   │   └── hooks/                # 自定义 Hooks
│   └── Dockerfile
│
├── docs/                         # 项目文档
│   ├── PRD.md                    # 产品需求文档
│   ├── BACKEND_REQUIREMENTS.md   # 后端开发文档
│   ├── FRONTEND_REQUIREMENTS.md  # 前端开发文档
│   ├── ARCHITECTURE.md           # 系统架构
│   ├── GETTING_STARTED.md        # 开发环境搭建
│   ├── API.md                    # API 速查
│   └── CONTRIBUTING.md           # 贡献指南
│
├── data/                         # 运行时数据（挂载卷）
│   ├── works/                    # SQLite DB
│   ├── vector_store/             # Chroma 向量库
│   └── logs/                     # 日志
│
├── scripts/                      # 运维脚本
├── docker-compose.yml            # 容器编排
├── .env.example                  # 环境变量模板
└── README.md                     # 本文件
```

---

## 技术栈

**后端**：Python 3.11+ / FastAPI / SQLAlchemy 2.0 / LangGraph / Chroma / LiteLLM

**前端**：React 18 / Vite / TypeScript / TipTap / Ant Design 5 / Tailwind CSS / Zustand

**基础设施**：Docker Compose / SQLite / ChromaDB / Nginx

---

## 支持的 LLM

| 服务商 | 用途 | 配置项 |
|--------|------|--------|
| OpenAI (GPT-5) | 写作主力 | `OPENAI_API_KEY` |
| Anthropic (Claude Opus 5) | 写作/编辑首选 | `ANTHROPIC_API_KEY` |
| DeepSeek | 性价比之王 | `DEEPSEEK_API_KEY` |
| Qwen/通义 | 中文优化 | `QWEN_API_KEY` |
| Ollama | 完全本地 | `OLLAMA_BASE_URL` |

详细配置见 [.env.example](.env.example) 和 [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)。

---

## 路线图

| 版本 | 时间 | 主要特性 |
|------|------|----------|
| v0.1 MVP | 2026-Q4 | 核心创作闭环、单 Agent、流式输出 |
| v0.5 Beta | 2027-Q1 | 6 Agent 完整、RAG 记忆、版本管理 |
| v1.0 GA | 2027-Q2 | 角色对话、模板市场、性能优化 |

详见 [docs/PRD.md 第13 章](docs/PRD.md#13-开发计划与里程碑)。

---

## 文档索引

- 📘 [PRD.md](docs/PRD.md) — 产品需求总览
- 🔧 [BACKEND_REQUIREMENTS.md](docs/BACKEND_REQUIREMENTS.md) — 后端实现规范
- 🎨 [FRONTEND_REQUIREMENTS.md](docs/FRONTEND_REQUIREMENTS.md) — 前端实现规范
- 🏗️ [ARCHITECTURE.md](docs/ARCHITECTURE.md) — 系统架构与数据流
- 🚀 [GETTING_STARTED.md](docs/GETTING_STARTED.md) — 开发环境搭建
- 📡 [API.md](docs/API.md) — API 速查表
- 🤝 [CONTRIBUTING.md](docs/CONTRIBUTING.md) — 贡献指南

---

## 许可证

[MIT License](LICENSE)

---

## 贡献

欢迎贡献代码、报告问题或提出建议！详见 [CONTRIBUTING.md](docs/CONTRIBUTING.md)。

---

**ZhiMeng Team** · 让 AI 成为你的写作搭档，而不是替代者。
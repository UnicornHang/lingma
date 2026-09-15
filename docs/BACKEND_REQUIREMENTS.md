# 织梦 (ZhiMeng) — 后端开发需求文档

> 项目代号：**ZhiMeng Novel Studio**
> 文档版本：v1.1
> 文档日期：2026-09-15
> 适用模块：**后端服务（Backend）**
> 技术栈：Python 3.11+ / FastAPI / SQLAlchemy 2.0 / LangGraph / Chroma / LiteLLM
> 配套文档：[PRD.md](PRD.md) · [FRONTEND_REQUIREMENTS.md](FRONTEND_REQUIREMENTS.md)

---

## 目录

1. [概述](#1-概述)
2. [技术栈与依赖](#2-技术栈与依赖)
3. [系统架构](#3-系统架构)
4. [目录结构](#4-目录结构)
5. [数据模型](#5-数据模型)
6. [API 设计规范](#6-api-设计规范)
7. [核心模块设计](#7-核心模块设计)
8. [Agent 实现规范](#8-agent-实现规范)
9. [LLM 网关](#9-llm-网关)
10. [向量记忆系统](#10-向量记忆系统)
11. [任务与流式输出](#11-任务与流式输出)
12. [安全与隐私](#12-安全与隐私)
13. [配置与环境变量](#13-配置与环境变量)
14. [测试规范](#14-测试规范)
15. [部署方案](#15-部署方案)
16. [开发里程碑](#16-开发里程碑)
17. [附录](#附录)

---

## 1. 概述

### 1.1 后端定位

ZhiMeng 后端是整个系统的"大脑"，承担以下职责：
- **数据持久化**：作品、大纲、章节、人物、世界观等结构化数据存储
- **业务编排**：6 个 AI Agent 的调度、上下文组装、状态管理
- **LLM 路由**：对接多模型服务（OpenAI、Anthropic、DeepSeek、Qwen、Ollama 等）
- **记忆系统**：连续性账本（权威短状态）+ 向量库 RAG（语义召回）
- **实时通信**：WebSocket 流式输出章节生成内容
- **文件服务**：导入导出 DOCX/EPUB/TXT

### 1.2 后端设计原则

| 原则 | 说明 |
|------|------|
| **异步优先** | 全栈使用 async/await，支持高并发 Agent 调用 |
| **可观测** | 每个请求、Agent 调用、LLM 请求都有结构化日志 |
| **可恢复** | 长任务持久化到 DB，支持断点续传 |
| **插件化** | Agent 可插拔，方便后续扩展 |
| **零外部依赖** | 仅依赖 LLM API，所有其他资源本地化 |
| **类型安全** | 全量使用 Pydantic Schema + Type Hints |

### 1.3 与前端的边界

```
┌──────────────────────────────────────────────┐
│                  Frontend                      │
│  - UI 渲染、表单、交互、富文本编辑 │
│  - 通过 REST/WebSocket 调用后端 │
│  - 不直接接触 LLM、不直连数据库 │
└──────────────────┬───────────────────────────┘
                   │ HTTP / WS
┌──────────────────▼───────────────────────────┐
│                  Backend                       │
│  - 业务逻辑、Agent 编排、数据持久化 │
│  - LLM 调用、流式输出、向量检索 │
│  - 文件处理、导入导出 │
└──────────────────┬───────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
  SQLite         Chroma        Local FS
```

---

## 2. 技术栈与依赖

### 2.1 核心技术栈

| 类别 | 选型 | 版本 | 理由 |
|------|------|------|------|
| 语言 | Python | 3.11+ | async 语法增强、生态成熟 |
| Web 框架 | FastAPI | 0.110+ | 高性能、自动文档、原生 async |
| ASGI 服务器 | Uvicorn | 0.27+ | 配合 FastAPI |
| ORM | SQLAlchemy | 2.0+ | async 友好、迁移工具完善 |
| 数据库 | SQLite | 3.45+ | 零部署、单文件 |
| 数据迁移 | Alembic | 1.13+ | SQLAlchemy 官方工具 |
| Agent 框架 | LangGraph | 0.0.30+ | 状态机、可观测 |
| LLM 客户端 | LiteLLM | 1.40+ | 统一多模型接口 |
| 向量库 | Chroma | 0.4.20+ | 嵌入式、零部署 |
| Embedding | sentence-transformers | 2.6+ | 本地向量生成 |
| 文档解析 | python-docx / ebooklib | latest | 导入导出 |
| WebSocket | FastAPI 原生 | — | 无需额外库 |
| 任务队列 | Arq | 0.25+ | 轻量 async 队列 |
| 日志 | structlog | 24.1+ | 结构化日志 |
| 配置管理 | pydantic-settings | 2.2+ | 类型安全 |
| 测试 | pytest + pytest-asyncio | latest | async 测试 |
| 依赖管理 | Poetry | 1.7+ | 锁文件、虚拟环境 |

### 2.2 pyproject.toml（关键依赖）

```toml
[tool.poetry]
name = "zhimeng-backend"
version = "0.1.0"
description = "ZhiMeng Novel Studio Backend"
authors = ["ZhiMeng Team"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
sqlalchemy = "^2.0.27"
alembic = "^1.13.1"
aiosqlite = "^0.20.0"
pydantic = "^2.6.0"
pydantic-settings = "^2.2.0"
langgraph = "^0.0.30"
langchain = "^0.1.10"
langchain-openai = "^0.1.0"
langchain-anthropic = "^0.1.0"
litellm = "^1.40.0"
chromadb = "^0.4.20"
sentence-transformers = "^2.6.0"
python-docx = "^1.1.0"
ebooklib = "^0.18"
arq = "^0.25.0"
structlog = "^24.1.0"
cryptography = "^42.0.0"
python-jose = "^3.3.0"
httpx = "^0.27.0"
websockets = "^12.0"

[tool.poetry.dev-dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"
mypy = "^1.8.0"
ruff = "^0.3.0"
black = "^24.1.0"
```

---

## 3. 系统架构

### 3.1 分层架构

```
┌──────────────────────────────────────────────────────┐
│  Layer 1 - API Layer (FastAPI Routes)                │
│  - REST endpoints + WebSocket handlers               │
│  - 请求校验、鉴权、限流                              │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│  Layer 2 - Service Layer (业务逻辑)                  │
│  - WorkService / ChapterService / CharacterService │
│  - 调用 Orchestrator 执行 Agent 任务                 │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│  Layer 3 - Orchestrator (编排层)                     │
│  - LangGraph State Machine                            │
│  - 上下文组装、Agent 调用顺序、错误重试              │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│  Layer 4 - Agent Layer (智能体)                      │
│  - PlotAgent / WorldAgent / CharacterAgent           │
│  - WriterAgent / EditorAgent / CriticAgent           │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│  Layer 5 - Core (基础设施)                           │
│  - LLMGateway / MemoryService / RAGService           │
│  - PromptBuilder / TokenTracker                      │
└──────────────────┬───────────────────────────────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
   ┌────────┐ ┌────────┐ ┌─────────┐
   │ SQLite │ │ Chroma │ │ LocalFS │
   └────────┘ └────────┘ └─────────┘
```

### 3.2 请求生命周期

```
[HTTP Request]
    │
    ▼
[Middleware: 日志/异常捕获/CORS]
    │
    ▼
[Router] → [Dependency Injection]
    │         - DB Session
    │         - Current User
    │         - LLM Gateway
    │
    ▼
[Schema Validation] (Pydantic)
    │
    ▼
[Service Layer]
    │
    ├─ 同步操作 → 直接返回
    │
    └─ 异步任务 → 创建 GenerationTask → 入队 → 立即返回 task_id
                                          │
                                          ▼
                            [Worker: 后台执行 Agent 流程]
                                          │
                                          ├─ 通过 WebSocket 推送进度
                                          │
                                          └─ 更新 GenerationTask 状态
```

### 3.3 模块依赖图

```
api/v1/works.py ──→ services/work_service.py ──→ models/work.py
                                       │
                                       ↓
                              services/chapter_service.py
                                       │
                                       ↓
                              orchestrator/chapter_orchestrator.py
                                       │
                                       ├──→ agents/writer_agent.py
                                       ├──→ agents/editor_agent.py
                                       ├──→ core/llm_gateway.py
                                       ├──→ core/memory_service.py
                                       └──→ core/rag_service.py
```

---

## 4. 目录结构

```
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/                       # 数据库迁移
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── config.py                  # 全局配置（pydantic-settings）
│   ├── deps.py                    # 公共依赖注入
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # 汇总所有路由
│   │   │   ├── works.py           # 作品 API
│   │   │   ├── volumes.py         # 卷 API
│   │   │   ├── chapters.py        # 章节 API
│   │   │   ├── outline.py         # 大纲 API
│   │   │   ├── characters.py      # 角色 API
│   │   │   ├── world.py           # 世界观 API
│   │   │   ├── agents.py          # Agent API
│   │   │   ├── tasks.py           # 任务查询 API
│   │   │   ├── settings.py        # 设置 API
│   │   │   ├── api_configs.py     # API 配置
│   │   │   └── import_export.py   # 导入导出
│   │   └── ws/
│   │       └── generation.py      # WebSocket 生成路由
│   │
│   ├── schemas/                   # Pydantic Schema
│   │   ├── __init__.py
│   │   ├── work.py
│   │   ├── chapter.py
│   │   ├── character.py
│   │   ├── world.py
│   │   ├── outline.py
│   │   ├── agent.py
│   │   └── common.py
│   │
│   ├── models/                    # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── base.py                # 公共基类
│   │   ├── work.py
│   │   ├── chapter.py
│   │   ├── character.py
│   │   ├── world.py
│   │   ├── outline.py
│   │   ├── task.py
│   │   ├── setting.py
│   │   └── api_config.py
│   │
│   ├── services/                  # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── work_service.py
│   │   ├── chapter_service.py
│   │   ├── character_service.py
│   │   ├── world_service.py
│   │   ├── outline_service.py
│   │   ├── task_service.py
│   │   ├── settings_service.py
│   │   ├── import_export_service.py
│   │   └── crypto_service.py
│   │
│   ├── agents/                    # Agent 实现
│   │   ├── __init__.py
│   │   ├── base.py                # BaseAgent 抽象类
│   │   ├── registry.py            # Agent 注册表
│   │   ├── plot_agent.py
│   │   ├── world_agent.py
│   │   ├── character_agent.py
│   │   ├── writer_agent.py
│   │   ├── editor_agent.py
│   │   └── critic_agent.py
│   │
│   ├── orchestrator/              # 编排引擎
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── chapter_orchestrator.py
│   │   ├── outline_orchestrator.py
│   │   └── state.py               # 状态定义
│   │
│   ├── core/                      # 核心基础设施
│   │   ├── __init__.py
│   │   ├── llm_gateway.py         # LLM 统一入口
│   │   ├── memory_service.py      # 记忆管理
│   │   ├── rag_service.py         # 向量检索
│   │   ├── prompt_builder.py      # Prompt 构造器
│   │   ├── token_tracker.py       # Token 用量统计
│   │   ├── cache_service.py       # 缓存
│   │   └── ws_manager.py          # WebSocket 连接管理
│   │
│   ├── prompts/                   # Prompt 模板
│   │   ├── __init__.py
│   │   ├── plot.j2
│   │   ├── world.j2
│   │   ├── character.j2
│   │   ├── writer.j2
│   │   ├── editor.j2
│   │   └── critic.j2
│   │
│   ├── db/                        # 数据库
│   │   ├── __init__.py
│   │   ├── session.py             # Session 工厂
│   │   └── init.py                # 初始化
│   │
│   ├── utils/                     # 工具
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── exceptions.py
│   │   ├── file_utils.py
│   │   ├── docx_parser.py
│   │   └── epub_parser.py
│   │
│   └── workers/                   # 异步任务
│       ├── __init__.py
│       ├── arq_settings.py
│       └── generation_worker.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_agents/
│   │   ├── test_services/
│   │   └── test_core/
│   ├── integration/
│   │   ├── test_works_api.py
│   │   ├── test_chapters_api.py
│   │   └── test_websocket.py
│   └── e2e/
│       └── test_full_flow.py
│
├── data/                          # 运行时数据（挂载卷）
│   ├── works/
│   ├── vector_store/
│   └── logs/
│
├── scripts/
│   ├── init_db.py
│   └── seed_data.py
│
├── .env.example
├── Dockerfile
└── README.md
```

---

## 5. 数据模型

### 5.1 实体关系图

```
┌─────────┐       ┌──────────────┐       ┌──────────┐
│  Work   │1─────*│   Volume     │1─────*│ Chapter  │
└─────────┘       └──────────────┘       └──────────┘
     │1                                      │1
     │                                       │
     *                                       *
 WorldBible                          ChapterVersion
     │
     │1
     │
     *
 Character
     │
     │
     *──── OutlineNode (独立挂在 Work 下)
     │
     *──── TrackingState (1:1 权威 JSON)
     │
     *
 SettingRule

Work 1───* GenerationTask
Work 1───* APIConfig (全局共享)
Work 1───* StyleProfile
```

### 5.2 SQLAlchemy 模型定义

#### 5.2.1 Base 模型

```python
# app/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
from uuid import UUID, uuid4
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class UUIDMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
```

#### 5.2.2 Work 模型

```python
# app/models/work.py
from sqlalchemy import String, Integer, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin
import enum

class WorkStatus(str, enum.Enum):
    DRAFT = "draft"
    WRITING = "writing"
    FINISHED = "finished"
    ARCHIVED = "archived"

class Genre(str, enum.Enum):
    FANTASY = "fantasy"           # 玄幻
    URBAN = "urban"               # 都市
    ROMANCE = "romance"           # 言情
    HISTORICAL = "historical"     # 历史
    SCI_FI = "sci_fi"             # 科幻
    MYSTERY = "mystery"           # 悬疑
    OTHER = "other"

class Work(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "works"

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    genre: Mapped[Genre] = mapped_column(SAEnum(Genre), nullable=False)
    target_word_count: Mapped[int] = mapped_column(Integer, default=1000000)
    logline: Mapped[str] = mapped_column(String(500), default="")
    style_keywords: Mapped[list] = mapped_column(JSON, default=list)
    target_audience: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[WorkStatus] = mapped_column(
        SAEnum(WorkStatus), default=WorkStatus.DRAFT
    )
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    # 关系
    volumes: Mapped[list["Volume"]] = relationship(
        back_populates="work", cascade="all, delete-orphan", lazy="selectin"
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="work", cascade="all, delete-orphan", lazy="selectin"
    )
    characters: Mapped[list["Character"]] = relationship(
        back_populates="work", cascade="all, delete-orphan", lazy="selectin"
    )
    outline_nodes: Mapped[list["OutlineNode"]] = relationship(
        back_populates="work", cascade="all, delete-orphan", lazy="selectin"
    )
    world_bible: Mapped["WorldBible"] = relationship(
        back_populates="work", cascade="all, delete-orphan",
        uselist=False, lazy="selectin"
    )
    style_profile: Mapped["StyleProfile"] = relationship(
        back_populates="work", cascade="all, delete-orphan",
        uselist=False, lazy="selectin"
    )
```

#### 5.2.2b TrackingState 模型

每部作品一条权威 JSON。Writer 写前只读派生「上下文卡」；写后走 `tracking_service.commit_tracking`，禁止把摘要 Markdown 反向解析回权威状态。

```python
# app/models/tracking.py
class TrackingState(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tracking_states"
    work_id: Mapped[UUID] = mapped_column(ForeignKey("works.id"), unique=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1)
```

payload 键：`foreshadows` / `characters`（运行时状态） / `author_timeline` / `reader_timeline` / `chapter_records` / `chapter_constraints`。

Writer 装配顺序：约束锁 → 细纲 → 人设卡 → 角色当前状态 → 伏笔与知情范围 → RAG 补充（不得覆盖账本）。

#### 5.2.3 Chapter 模型

```python
# app/models/chapter.py
class ChapterStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    FINALIZED = "finalized"

class Chapter(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chapters"

    work_id: Mapped[UUID] = mapped_column(ForeignKey("works.id"), nullable=False)
    volume_id: Mapped[UUID | None] = mapped_column(ForeignKey("volumes.id"))
    outline_node_id: Mapped[UUID | None] = mapped_column(ForeignKey("outline_nodes.id"))

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, default=dict)  # TipTap JSON
    plain_content: Mapped[str] = mapped_column(Text, default="")  # 纯文本（用于检索）
    summary: Mapped[str] = mapped_column(Text, default="")
    key_events: Mapped[list] = mapped_column(JSON, default=list)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ChapterStatus] = mapped_column(
        SAEnum(ChapterStatus), default=ChapterStatus.DRAFT
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    current_version_id: Mapped[UUID | None] = mapped_column()

    # 关系
    work: Mapped["Work"] = relationship(back_populates="chapters")
    versions: Mapped[list["ChapterVersion"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan",
        order_by="ChapterVersion.version_no.desc()"
    )

class ChapterVersion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chapter_versions"

    chapter_id: Mapped[UUID] = mapped_column(ForeignKey("chapters.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON)  # TipTap JSON
    plain_content: Mapped[str] = mapped_column(Text, default="")
    generated_by: Mapped[str] = mapped_column(String(20))  # user/ai/ai_revised
    prompt_used: Mapped[str] = mapped_column(Text, default="")
    model_used: Mapped[str] = mapped_column(String(100), default="")
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict)
    note: Mapped[str] = mapped_column(String(200), default="")  # 版本标签

    chapter: Mapped["Chapter"] = relationship(back_populates="versions")
```

#### 5.2.4 Character 模型

```python
# app/models/character.py
class Character(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "characters"

    work_id: Mapped[UUID] = mapped_column(ForeignKey("works.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="supporting")  # main/supporting/antagonist

    # 结构化字段
    basic_info: Mapped[dict] = mapped_column(JSON, default=dict)
    personality: Mapped[dict] = mapped_column(JSON, default=dict)
    backstory: Mapped[dict] = mapped_column(JSON, default=dict)
    relationships: Mapped[list] = mapped_column(JSON, default=list)
    arc: Mapped[dict] = mapped_column(JSON, default=dict)
    voice_samples: Mapped[list] = mapped_column(JSON, default=list)

    # 统计字段
    appearance_count: Mapped[int] = mapped_column(Integer, default=0)
    first_appearance_chapter_id: Mapped[UUID | None] = mapped_column()

    # 向量化状态
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_text: Mapped[str] = mapped_column(Text, default="")  # 用于向量化的纯文本

    work: Mapped["Work"] = relationship(back_populates="characters")
```

#### 5.2.5 WorldBible 模型

```python
# app/models/world.py
class WorldBible(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "world_bibles"

    work_id: Mapped[UUID] = mapped_column(
        ForeignKey("works.id"), unique=True, nullable=False
    )

    # 结构化字段
    geography: Mapped[dict] = mapped_column(JSON, default=dict)
    factions: Mapped[list] = mapped_column(JSON, default=list)
    power_system: Mapped[dict] = mapped_column(JSON, default=dict)
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    rules: Mapped[list] = mapped_column(JSON, default=list)
    culture: Mapped[dict] = mapped_column(JSON, default=dict)

    # 自然语言全文（供 Prompt 注入）
    raw_text: Mapped[str] = mapped_column(Text, default="")

    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)

    work: Mapped["Work"] = relationship(back_populates="world_bible")
```

#### 5.2.6 OutlineNode 模型

```python
# app/models/outline.py
class OutlineNodeType(str, enum.Enum):
    VOLUME = "volume"
    CHAPTER = "chapter"
    BEAT = "beat"

class OutlineNode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "outline_nodes"

    work_id: Mapped[UUID] = mapped_column(ForeignKey("works.id"), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("outline_nodes.id"))

    type: Mapped[OutlineNodeType] = mapped_column(SAEnum(OutlineNodeType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    beats: Mapped[list] = mapped_column(JSON, default=list)
    characters_involved: Mapped[list] = mapped_column(JSON, default=list)  # [character_id]
    world_refs: Mapped[list] = mapped_column(JSON, default=list)  # [world_setting_id]
    target_word_count: Mapped[int] = mapped_column(Integer, default=3000)
    order: Mapped[int] = mapped_column(Integer, default=0)

    # 父子关系
    work: Mapped["Work"] = relationship(back_populates="outline_nodes")
    children: Mapped[list["OutlineNode"]] = relationship(
        "OutlineNode", backref=backref("parent", remote_side="OutlineNode.id"),
        order_by="OutlineNode.order"
    )
```

#### 5.2.7 GenerationTask 模型

```python
# app/models/task.py
class TaskType(str, enum.Enum):
    OUTLINE_GENERATE = "outline_generate"
    OUTLINE_EXPAND = "outline_expand"
    CHAPTER_GENERATE = "chapter_generate"
    CHAPTER_CONTINUE = "chapter_continue"
    CHAPTER_REWRITE = "chapter_rewrite"
    CHAPTER_EXPAND = "chapter_expand"
    CHAPTER_SHORTEN = "chapter_shorten"
    CHAPTER_POLISH = "chapter_polish"
    CHAPTER_REVIEW = "chapter_review"
    WORLD_BUILD = "world_build"
    CHARACTER_DESIGN = "character_design"
    CRITIC_EVALUATE = "critic_evaluate"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class GenerationTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "generation_tasks"

    work_id: Mapped[UUID] = mapped_column(ForeignKey("works.id"), nullable=False)
    chapter_id: Mapped[UUID | None] = mapped_column(ForeignKey("chapters.id"))
    outline_node_id: Mapped[UUID | None] = mapped_column(ForeignKey("outline_nodes.id"))

    task_type: Mapped[TaskType] = mapped_column(SAEnum(TaskType), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), default=TaskStatus.PENDING
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict)
```

#### 5.2.8 APIConfig 模型

```python
# app/models/api_config.py
class Provider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    VLLM = "vllm"
    CUSTOM = "custom"

class APIConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "api_configs"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[Provider] = mapped_column(SAEnum(Provider), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)  # AES-256 加密
    base_url: Mapped[str] = mapped_column(String(500), default="")
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # 模型分配：哪些 Agent 使用该配置
    agent_assignments: Mapped[list] = mapped_column(JSON, default=list)

    # 元数据
    max_context_tokens: Mapped[int] = mapped_column(Integer, default=32000)
    cost_per_1k_input: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_1k_output: Mapped[float] = mapped_column(Float, default=0.0)
```

### 5.3 数据库迁移

使用 Alembic 管理 schema 变更：

```bash
# 初始化
alembic init alembic

# 生成迁移
alembic revision --autogenerate -m "init schema"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

`alembic/env.py` 配置：

```python
from app.models import Base
from app.config import settings

target_metadata = Base.metadata

def run_migrations_online():
    config.set_main_option("sqlalchemy.url", settings.database_url)
    # ... 异步配置
```

### 5.4 向量库 Schema

```python
# app/core/rag_service.py
from chromadb import PersistentClient

class RAGService:
    def __init__(self, persist_dir: str):
        self.client = PersistentClient(path=persist_dir)
        # 默认 embedding 函数：本地 sentence-transformers
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-small-zh-v1.5"
        )

    def get_or_create_collection(self, work_id: UUID):
        """每个作品独立 collection"""
        return self.client.get_or_create_collection(
            name=f"work_{work_id}",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    async def add_documents(self, work_id: UUID, docs: list[dict]):
        """
        docs 结构：
        {
            "id": "uuid",
            "text": "向量化文本",
            "type": "character|world|chapter|event",
            "metadata": {...}
        }
        """
        collection = self.get_or_create_collection(work_id)
        collection.add(
            ids=[d["id"] for d in docs],
            documents=[d["text"] for d in docs],
            metadatas=[d["metadata"] for d in docs]
        )

    async def query(self, work_id: UUID, query_text: str, n_results: int = 5,
                    filter: dict | None = None) -> list[dict]:
        collection = self.get_or_create_collection(work_id)
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filter
        )
        return self._format_results(results)
```

**文档类型约定**：

| type | 来源 | 元数据 |
|------|------|--------|
| `character` | Character.raw_text | `character_id`, `name` |
| `world` | WorldBible.raw_text | `section: geography/factions/rules/...` |
| `chapter_summary` | Chapter.summary | `chapter_id`, `chapter_title`, `order` |
| `chapter_content` | Chapter.plain_content 切片 | `chapter_id`, `chunk_index` |
| `event` | Chapter.key_events | `chapter_id`, `event_type` |

---

## 6. API 设计规范

### 6.1 通用规范

- **Base URL**：`http://localhost:8000/api/v1`
- **认证**：本地部署默认无认证；如启用需加 `Authorization: Bearer <token>` 头
- **数据格式**：`application/json; charset=utf-8`
- **时间格式**：`ISO 8601`，UTC 时区
- **分页**：使用 `?page=1&page_size=20`，返回 `total`、`page`、`page_size`、`items`
- **错误响应**：统一格式

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "章节字数超出范围",
    "details": {
      "field": "target_words",
      "constraint": "1000-10000"
    }
  }
}
```

**错误码规范**：

| HTTP | code | 含义 |
|------|------|------|
| 400 | INVALID_INPUT | 参数校验失败 |
| 401 | UNAUTHORIZED | 未认证 |
| 403 | FORBIDDEN | 无权限 |
| 404 | NOT_FOUND | 资源不存在 |
| 409 | CONFLICT | 资源冲突 |
| 422 | VALIDATION_ERROR | Pydantic 校验失败 |
| 500 | INTERNAL_ERROR | 服务器异常 |
| 503 | LLM_UNAVAILABLE | LLM 服务不可用 |

### 6.2 REST API 详细定义

#### 6.2.1 作品相关 `/works`

```python
# GET /works - 作品列表
query_params:
  - page: int = 1
  - page_size: int = 20
  - genre: str | None
  - status: str | None
  - search: str | None
  - sort: str = "-updated_at"  # 排序字段

response:
{
  "total": 12,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "uuid",
      "title": "剑来·前传",
      "genre": "fantasy",
      "status": "writing",
      "word_count": 352000,
      "target_word_count": 1000000,
      "created_at": "2026-08-01T...",
      "updated_at": "2026-09-10T...",
      "cover_url": "/api/v1/works/{id}/cover"
    }
  ]
}

# POST /works - 创建作品
request:
{
  "title": "剑来·前传",
  "genre": "fantasy",
  "target_word_count": 1000000,
  "logline": "一个孤儿成长为宗师的历程",
  "style_keywords": ["热血", "升级", "东方玄幻"],
  "target_audience": ["男频"],
  "template_id": "uuid | null"  # 可选，从模板创建
}
response: 201 Created + Work 对象

# GET /works/{id} - 作品详情
response: Work 完整对象（含 world_bible、characters、outline 概览）

# PATCH /works/{id} - 更新作品
request: 任意 Work 字段

# DELETE /works/{id} - 删除作品（级联删除所有关联数据）
response: 204 No Content

# GET /works/{id}/statistics - 统计信息
response:
{
  "total_chapters": 100,
  "total_words": 352000,
  "average_chapter_words": 3520,
  "completion_ratio": 0.352,
  "daily_words": [{"date": "2026-09-09", "words": 5000}, ...],
  "agent_usage": [
    {"agent": "writer", "calls": 100, "tokens": 1500000}
  ],
  "total_cost": 45.6
}

# POST /works/{id}/export - 导出
query: format=txt|docx|epub|json
response: 文件下载

# POST /works/import - 导入
request: multipart/form-data
  - file: 文件
  - format: txt|docx|epub|json
  - work_info: {title, genre, ...}
response: Work 对象
```

#### 6.2.2 章节相关 `/chapters`

```python
# GET /works/{work_id}/chapters - 章节列表
query:
  - volume_id: uuid | None
  - status: str | None
  - page: int = 1
  - page_size: int = 50

response: {total, items: [Chapter概要]}

# GET /chapters/{id} - 章节详情
response: Chapter 完整对象（含 versions 摘要）

# PATCH /chapters/{id} - 更新（手动保存）
request:
{
  "title": "...",
  "content": {...},  # TipTap JSON
  "plain_content": "..."
}
response: 更新后的 Chapter

# DELETE /chapters/{id}
response: 204

# GET /chapters/{id}/versions - 版本列表
response: [{version_no, generated_by, created_at, note}, ...]

# POST /chapters/{id}/switch-version - 切换当前版本
request: {"version_no": 3}
response: 更新后的 Chapter

# POST /chapters/generate - 生成章节（异步）
request:
{
  "outline_node_id": "uuid",
  "target_words": 3000,
  "style_reference": "few_shot | description | none",
  "few_shot_examples": ["...", "..."],  # 可选
  "user_instructions": "本章节重点推进支线",
  "character_ids": ["uuid", ...],
  "model_config_id": "uuid | null"  # null 则用默认
}
response: 202 Accepted
{
  "task_id": "uuid",
  "ws_url": "ws://localhost:8000/ws/generation/{task_id}",
  "status": "pending"
}
# 无章纲 / 卷纲 / 细纲为空 → 409。默认只做痕迹检测；auto_rewrite 才润色。写完自动 tracking/commit。

# POST /chapters/{id}/ai-continue - 续写（异步）
request:
{
  "position": "cursor | end",
  "length": 500,
  "user_instructions": "..."
}
response: 同 generate

# POST /chapters/{id}/ai-rewrite - 改写
request:
{
  "range": {"from": 100, "to": 300},  # 字符范围
  "style": "more_vivid | more_concise | more_colloquial | custom",
  "custom_instruction": "..."
}
response: 同 generate

# POST /chapters/{id}/ai-expand - 扩写
request:
{
  "range": {...},
  "expansion_ratio": 1.5
}

# POST /chapters/{id}/ai-shorten - 缩写
request:
{
  "range": {...},
  "compression_ratio": 0.5
}

# POST /chapters/{id}/ai-polish - 润色
request:
{
  "range": {...},
  "focus": ["grammar | style | dialogue"]  # 关注点
}

# POST /chapters/{id}/ai-review - AI 审校
request:
{
  "dimensions": ["basic", "logic", "consistency", "rhythm", "style"]
}
response:
{
  "suggestions": [
    {
      "id": "uuid",
      "type": "spelling | logic | consistency | rhythm | style",
      "severity": "info | warning | error",
      "range": {"from": 100, "to": 120},
      "original": "原文",
      "suggestion": "建议改为...",
      "reason": "理由"
    }
  ],
  "scores": {
    "rhythm": 8.5,
    "style": 7.0,
    "overall": 7.8
  }
}
```

#### 6.2.3 大纲相关 `/outline`

```python
# GET /works/{id}/outline - 获取大纲树
response:
{
  "nodes": [
    {
      "id": "uuid",
      "type": "volume",
      "title": "第一卷",
      "summary": "...",
      "children": [
        {
          "id": "uuid",
          "type": "chapter",
          "title": "第一章",
          "summary": "...",
          "beats": [...],
          "target_words": 3000,
          "children": []
        }
      ]
    }
  ]
}

# POST /works/{id}/outline/nodes - 创建节点
request:
{
  "parent_id": "uuid | null",
  "type": "chapter",
  "title": "...",
  "summary": "...",
  "target_word_count": 3000
}

# PATCH /outline/nodes/{id} - 更新
# DELETE /outline/nodes/{id} - 删除（级联删除子节点）

# POST /works/{id}/outline/ai-generate - AI 生成大纲
request:
{
  "logline": "一句话简介",
  "genre": "fantasy",
  "target_words": 1000000,
  "structure": "three_act | hero_journey | chinese_classical",
  "total_chapters": 100
}
response: 202 + task_id

# POST /outline/nodes/{id}/ai-expand - 扩展节点
request:
{
  "granularity": "chapter | beat",
  "count": 5
}
response: 202 + task_id
```

#### 6.2.4 角色相关 `/characters`

```python
# GET /works/{id}/characters
# POST /works/{id}/characters
request:
{
  "name": "林墨",
  "role": "main",
  "basic_info": {...},
  "personality": {...},
  "backstory": {...},
  ...
}

# GET /characters/{id}
# PATCH /characters/{id}
# DELETE /characters/{id}

# POST /characters/{id}/ai-design - AI 设计角色
request:
{
  "name": "林墨",
  "requirements": "一个沉默寡言的剑修，...",
  "context": {work_genre, existing_characters, ...}
}
response: 202 + task_id

# POST /characters/{id}/chat - 角色对话
request:
{
  "messages": [
    {"role": "user", "content": "你是谁？"}
  ],
  "max_turns": 10
}
response:
{
  "reply": "我是林墨，...",
  "session_id": "uuid"
}

# GET /characters/{id}/appearances - 出场记录
response:
{
  "appearances": [
    {
      "chapter_id": "uuid",
      "chapter_title": "第一章·风起青萍",
      "snippet": "林墨踏入了...",
      "word_count": 250
    }
  ],
  "total_appearances": 25,
  "total_words": 15000
}
```

#### 6.2.5 世界观相关 `/world`

```python
# GET /works/{id}/world
# PUT /works/{id}/world - 整体更新
# PATCH /works/{id}/world/{section} - 部分更新
#   section: geography | factions | power_system | timeline | rules | culture

# POST /works/{id}/world/ai-build - AI 构建
request:
{
  "genre": "fantasy",
  "themes": ["修仙", "宗门"],
  "requirements": "...",
  "sections": ["geography", "factions", "power_system"]  # 要构建的部分
}
response: 202 + task_id

# POST /works/{id}/world/check-consistency - 一致性检查
request:
{
  "text": "要检查的文本",
  "context": "chapter_id | null"
}
response:
{
  "issues": [
    {
      "type": "power_system_violation",
      "severity": "error",
      "text": "筑基期修士飞行千里",
      "rule_violated": "凡人无法踏空",
      "suggestion": "建议改为金丹期"
    }
  ]
}
```

#### 6.2.6 任务与 Agent

```python
# POST /agents/plot/generate
# POST /agents/world/generate
# POST /agents/character/generate
# POST /agents/editor/review
# POST /agents/critic/evaluate
# 通用模式：创建异步任务

# GET /tasks/{id} - 任务详情
response:
{
  "id": "uuid",
  "task_type": "chapter_generate",
  "status": "running",
  "progress": 45,
  "params": {...},
  "result": null,
  "error": null,
  "started_at": "...",
  "completed_at": null,
  "token_usage": {"input": 5000, "output": 1500}
}

# GET /tasks - 任务列表
query:
  - work_id: uuid
  - status: pending | running | completed | failed
  - task_type: str
  - page, page_size

# POST /tasks/{id}/cancel - 取消任务
response: 204
```

#### 6.2.7 设置与 API 配置

```python
# GET /settings - 获取所有设置
response:
{
  "ui": {"theme": "light", "language": "zh-CN", "font_size": 14},
  "editor": {"auto_save_interval": 10, "spell_check": true},
  "creation": {"default_target_words": 3000, "default_style": []},
  "security": {"encrypt_data": true, "auto_backup": true},
  "advanced": {"max_context_tokens": 32000, "log_level": "INFO"}
}

# PUT /settings/{key} - 更新设置
#   key: dot.notation, e.g. "ui.theme"

# GET /api-configs - API 配置列表
# POST /api-configs - 新增
request:
{
  "name": "我的 Claude",
  "provider": "anthropic",
  "api_key": "sk-ant-xxx",  # 仅创建时明文，存储后加密
  "base_url": "https://api.anthropic.com",
  "model_name": "claude-opus-5-20251101",
  "agent_assignments": ["writer", "editor"]
}
# PATCH /api-configs/{id} - 更新
# DELETE /api-configs/{id}

# POST /api-configs/{id}/test - 测试连接
request: {"test_prompt": "Hello"}
response: {"success": true, "latency_ms": 1234, "model_response": "..."}

# GET /api-configs/defaults - 获取推荐的默认配置模板
response:
{
  "writer": {
    "provider": "anthropic",
    "model_name": "claude-opus-5-20251101",
    "alternatives": [{"provider": "openai", "model_name": "gpt-5"}]
  },
  ...
}
```

### 6.3 WebSocket 协议

#### 6.3.1 连接

```
ws://localhost:8000/ws/generation/{task_id}
```

#### 6.3.2 消息协议

```typescript
// 客户端发送（可选，主要用于控制）
type ClientMessage =
  | { type: 'subscribe', task_id: string }
  | { type: 'pause', task_id: string }
  | { type: 'resume', task_id: string }
  | { type: 'cancel', task_id: string }
  | { type: 'update_params', task_id: string, params: any };

// 服务端推送
type ServerMessage =
  | {
      type: 'connected';
      task_id: string;
      task_type: string;
    }
  | {
      type: 'started';
      task_id: string;
      started_at: string;
      total_steps: number;
    }
  | {
      type: 'progress';
      task_id: string;
      progress: number;       // 0-100
      step: string;            // "context_retrieving" | "writing" | "reviewing"
      message?: string;         // 人类可读状态
    }
  | {
      type: 'chunk';            // 流式内容片段（章节正文）
      task_id: string;
      content: string;
      accumulated_length: number;
    }
  | {
      type: 'log';              // 调试日志
      task_id: string;
      level: 'debug' | 'info' | 'warning' | 'error';
      message: string;
    }
  | {
      type: 'review';           // 编辑批注
      task_id: string;
      suggestions: ReviewSuggestion[];
    }
  | {
      type: 'score';            // 评审评分
      task_id: string;
      scores: Record<string, number>;
      overall: number;
      grade: 'A' | 'B' | 'C' | 'D';
    }
  | {
      type: 'completed';
      task_id: string;
      result: any;
      token_usage: { input: number; output: number; total: number };
      duration_ms: number;
    }
  | {
      type: 'failed';
      task_id: string;
      error: string;
      error_code?: string;
    };
```

#### 6.3.3 服务端实现（FastAPI）

```python
# app/api/ws/generation.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.ws_manager import WSManager

router = APIRouter()
ws_manager = WSManager()

@router.websocket("/ws/generation/{task_id}")
async def generation_ws(websocket: WebSocket, task_id: str):
    await ws_manager.connect(websocket, task_id)
    try:
        # 推送连接成功
        await ws_manager.send(task_id, {
            "type": "connected",
            "task_id": task_id
        })
        # 保持连接，接收客户端控制消息
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_control(task_id, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(task_id)
```

#### 6.3.4 客户端调用示例（前端）

```typescript
const ws = new WebSocket(`ws://localhost:8000/ws/generation/${taskId}`);
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  switch (msg.type) {
    case 'chunk':
      appendToEditor(msg.content);
      break;
    case 'progress':
      updateProgressBar(msg.progress);
      break;
    case 'review':
      showReviewSuggestions(msg.suggestions);
      break;
    case 'completed':
      finalizeChapter(msg.result);
      break;
  }
};
```

---

## 7. 核心模块设计

### 7.1 LLM Gateway（`app/core/llm_gateway.py`）

```python
from typing import AsyncIterator
from litellm import acompletion
from app.models.api_config import APIConfig
from app.core.cache_service import CacheService
from app.core.token_tracker import TokenTracker

class LLMGateway:
    """统一 LLM 调用入口"""

    def __init__(self, configs: list[APIConfig], cache: CacheService, tracker: TokenTracker):
        self.configs = {c.id: c for c in configs if c.enabled}
        self.cache = cache
        self.tracker = tracker

    def select_config(self, agent_type: str) -> APIConfig:
        """根据 Agent 类型选择模型"""
        # 1. 优先查找该 Agent 指定配置
        for cfg in self.configs.values():
            if agent_type in (cfg.agent_assignments or []):
                return cfg
        # 2. 使用第一个可用配置
        return next(iter(self.configs.values()))

    def decrypt_key(self, encrypted: str) -> str:
        """解密 API Key"""
        from app.services.crypto_service import decrypt
        return decrypt(encrypted)

    async def generate(
        self,
        agent_type: str,
        messages: list[dict],
        stream: bool = False,
        temperature: float = 0.8,
        max_tokens: int | None = None,
        **kwargs
    ) -> AsyncIterator[str] | str:
        config = self.select_config(agent_type)

        # 缓存检查（非流式）
        cache_key = self._make_cache_key(config, messages)
        if not stream:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        # 解密 API Key
        api_key = self.decrypt_key(config.api_key_encrypted) if config.api_key_encrypted else "EMPTY"

        # 调用 LLM
        try:
            response = await acompletion(
                model=f"{config.provider.value}/{config.model_name}",
                messages=messages,
                api_key=api_key,
                api_base=config.base_url or None,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            if stream:
                async def gen():
                    full = ""
                    async for chunk in response:
                        delta = chunk.choices[0].delta.content or ""
                        full += delta
                        yield delta
                    # 流结束后记录 usage
                    await self.tracker.record(config, len(full), is_stream=True)
                return gen()
            else:
                content = response.choices[0].message.content
                await self.tracker.record(
                    config,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
                await self.cache.set(cache_key, content)
                return content

        except Exception as e:
            # 重试 + 降级
            fallback = self._get_fallback(agent_type)
            if fallback and fallback.id != config.id:
                return await self.generate_with_config(fallback, messages, stream, **kwargs)
            raise

    def _get_fallback(self, agent_type: str) -> APIConfig | None:
        """获取备选配置"""
        # 简单实现：返回第二个 enabled 配置
        enabled = [c for c in self.configs.values() if c.enabled]
        return enabled[1] if len(enabled) > 1 else None

    def _make_cache_key(self, config: APIConfig, messages: list[dict]) -> str:
        import hashlib, json
        content = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        return f"{config.id}:{hashlib.md5(content.encode()).hexdigest()}"
```

### 7.2 Memory Service（`app/core/memory_service.py`）

```python
class MemoryService:
    """记忆管理：摘要、滑动窗口、向量检索"""

    def __init__(self, rag: RAGService, llm: LLMGateway):
        self.rag = rag
        self.llm = llm

    async def get_chapter_context(self, work_id: UUID, chapter_id: UUID) -> dict:
        """组装章节生成所需的完整上下文"""
        return {
            "world_bible_excerpt": await self._get_world_context(work_id),
            "characters_involved": await self._get_characters(work_id, chapter_id),
            "recent_chapters": await self._get_recent_chapters(work_id, chapter_id, n=3),
            "current_outline": await self._get_outline(work_id, chapter_id),
            "related_passages": await self._search_related(work_id, chapter_id, k=5),
        }

    async def _get_recent_chapters(self, work_id: UUID, current_id: UUID, n: int):
        """获取最近 N 章摘要"""
        # 从 DB 查最近 N 章
        async with self.session() as s:
            stmt = (
                select(Chapter)
                .where(Chapter.work_id == work_id, Chapter.id != current_id)
                .order_by(Chapter.created_at.desc())
                .limit(n)
            )
            chapters = (await s.execute(stmt)).scalars().all()
        return [
            {"id": str(c.id), "title": c.title, "summary": c.summary}
            for c in reversed(chapters)
        ]

    async def _search_related(self, work_id: UUID, chapter_id: UUID, k: int):
        """向量检索相关段落"""
        chapter = await self._get_chapter(chapter_id)
        results = await self.rag.query(
            work_id=work_id,
            query_text=chapter.summary,
            n_results=k,
            filter={"type": {"$in": ["chapter_content", "event"]}}
        )
        return results

    async def generate_summary(self, chapter_content: str) -> str:
        """生成章节摘要"""
        prompt = f"请为以下章节内容生成 300 字摘要：\n\n{chapter_content}"
        return await self.llm.generate(
            agent_type="summarizer",
            messages=[{"role": "user", "content": prompt}]
        )
```

### 7.3 Prompt Builder（`app/core/prompt_builder.py`）

```python
from jinja2 import Environment, FileSystemLoader

class PromptBuilder:
    """Prompt 构造器：基于 Jinja2 模板"""

    def __init__(self, template_dir: str = "app/prompts"):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build_writer_prompt(self, ctx: dict) -> list[dict]:
        """构造写作 Agent 的 messages"""
        system = self.env.get_template("writer.j2").render(**ctx)
        user = self.env.get_template("writer_user.j2").render(**ctx)
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

    def build_editor_prompt(self, content: str, dimensions: list) -> list[dict]:
        system = self.env.get_template("editor.j2").render(
            dimensions=dimensions
        )
        user = f"请审校以下章节内容：\n\n{content}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
```

`app/prompts/writer.j2` 示例：

```jinja2
你是一位专业的小说家，正在创作《{{ title }}》（{{ genre_label }}）。

## 风格要求
{{ style_keywords | join('、') }}

## 参考片段
{% for sample in few_shot_samples %}
{{ sample }}
---
{% endfor %}

## 当前章节任务
- **章节**：{{ chapter_title }}
- **摘要**：{{ chapter_summary }}
- **节拍**：{{ beats | join(' → ') }}
- **涉及人物**：{{ character_names | join('、') }}
- **重点要求**：{{ user_instructions }}

## 人物档案
{% for char in involved_characters %}
### {{ char.name }}（{{ char.role }}）
{{ char.raw_text }}
{% endfor %}

## 世界设定摘要
{{ world_bible_excerpt }}

## 前文衔接
{% for ch in recent_chapters %}
### {{ ch.title }}
{{ ch.summary }}
{% endfor %}

## 写作要求
- 目标字数：{{ target_words }} 字（±10%）
- 人物言行必须符合 Character Card
- 世界设定必须符合 World Bible
- 与前文衔接自然流畅
- 使用纯文本格式输出，每段 100-200 字
```

---

## 8. Agent 实现规范

### 8.1 BaseAgent 抽象类

```python
# app/agents/base.py
from abc import ABC, abstractmethod
from app.core.llm_gateway import LLMGateway
from app.core.prompt_builder import PromptBuilder

class BaseAgent(ABC):
    agent_type: str  # "writer" | "editor" | ...

    def __init__(self, llm: LLMGateway, prompts: PromptBuilder):
        self.llm = llm
        self.prompts = prompts

    @abstractmethod
    async def execute(self, ctx: dict) -> dict:
        """执行 Agent 任务"""
        pass

    @abstractmethod
    def build_prompt(self, ctx: dict) -> list[dict]:
        """构造 Prompt"""
        pass
```

### 8.2 Agent 注册表

```python
# app/agents/registry.py
from .writer_agent import WriterAgent
from .editor_agent import EditorAgent
from .critic_agent import CriticAgent
from .plot_agent import PlotAgent
from .world_agent import WorldAgent
from .character_agent import CharacterAgent

AGENT_REGISTRY = {
    "writer": WriterAgent,
    "editor": EditorAgent,
    "critic": CriticAgent,
    "plot": PlotAgent,
    "world": WorldAgent,
    "character": CharacterAgent,
}

def get_agent(agent_type: str, **deps):
    cls = AGENT_REGISTRY.get(agent_type)
    if not cls:
        raise ValueError(f"Unknown agent: {agent_type}")
    return cls(**deps)
```

### 8.3 Writer Agent

```python
# app/agents/writer_agent.py
from .base import BaseAgent
from app.core.memory_service import MemoryService
from typing import AsyncIterator

class WriterAgent(BaseAgent):
    agent_type = "writer"

    def __init__(self, llm, prompts, memory: MemoryService):
        super().__init__(llm, prompts)
        self.memory = memory

    async def execute_stream(
        self,
        work_id: UUID,
        chapter_id: UUID,
        params: dict
    ) -> AsyncIterator[dict]:
        """流式生成章节"""
        # 1. 上下文组装
        ctx = await self.memory.get_chapter_context(work_id, chapter_id)
        ctx.update(params)

        # 2. 构建 Prompt
        messages = self.prompts.build_writer_prompt(ctx)

        # 3. 流式调用
        full_content = ""
        async for chunk in self.llm.generate(
            agent_type="writer",
            messages=messages,
            stream=True,
            temperature=0.8
        ):
            full_content += chunk
            yield {"type": "chunk", "content": chunk}

        # 4. 后续：保存、审校、向量化
        yield {"type": "completed", "content": full_content}
```

### 8.4 Orchestrator（编排器）

```python
# app/orchestrator/chapter_orchestrator.py
from langgraph.graph import StateGraph, END
from typing import TypedDict

class ChapterGenState(TypedDict):
    work_id: UUID
    chapter_id: UUID
    outline_node_id: UUID
    params: dict
    context: dict
    draft: str
    review_suggestions: list
    final_content: str

class ChapterOrchestrator:
    """编排章节生成：上下文组装 → 写作 → 审校 → 保存"""

    def __init__(self, writer, editor, memory, chapter_service, ws_manager):
        self.writer = writer
        self.editor = editor
        self.memory = memory
        self.chapter_service = chapter_service
        self.ws = ws_manager

    def build_graph(self) -> StateGraph:
        g = StateGraph(ChapterGenState)

        g.add_node("assemble_context", self._assemble_context)
        g.add_node("write", self._write)
        g.add_node("review", self._review)
        g.add_node("save", self._save)

        g.set_entry_point("assemble_context")
        g.add_edge("assemble_context", "write")
        g.add_edge("write", "review")
        g.add_edge("review", "save")
        g.add_edge("save", END)

        return g.compile()

    async def _assemble_context(self, state):
        ctx = await self.memory.get_chapter_context(
            state["work_id"], state["chapter_id"]
        )
        await self.ws.send(state["chapter_id"], {
            "type": "progress", "progress": 20, "step": "context"
        })
        return {"context": ctx}

    async def _write(self, state):
        draft = ""
        async for event in self.writer.execute_stream(
            state["work_id"], state["chapter_id"],
            {**state["params"], **state["context"]}
        ):
            if event["type"] == "chunk":
                draft += event["content"]
                await self.ws.send(state["chapter_id"], event)
            elif event["type"] == "completed":
                draft = event["content"]

        await self.ws.send(state["chapter_id"], {
            "type": "progress", "progress": 70, "step": "writing_done"
        })
        return {"draft": draft}

    async def _review(self, state):
        review = await self.editor.execute(
            content=state["draft"],
            dimensions=["logic", "consistency"]
        )
        await self.ws.send(state["chapter_id"], {
            "type": "review",
            "suggestions": review["suggestions"]
        })
        return {"review_suggestions": review["suggestions"]}

    async def _save(self, state):
        await self.chapter_service.save_generated(
            chapter_id=state["chapter_id"],
            content=state["draft"],
            suggestions=state["review_suggestions"]
        )
        await self.ws.send(state["chapter_id"], {
            "type": "completed"
        })
```

---

## 9. LLM 网关

详见 [7.1 LLM Gateway](#71-llm-gatewayappcorellm_gatewaypy)。

补充：

### 9.1 模型路由策略

```python
# app/core/llm_gateway.py (补充)
class ModelRouter:
    """根据任务特征自动选模型"""

    @staticmethod
    def select_for_agent(agent_type: str, configs: list[APIConfig]) -> APIConfig:
        priority_map = {
            "writer": ["anthropic", "openai"],
            "editor": ["anthropic", "openai"],
            "critic": ["deepseek", "openai"],
            "plot": ["deepseek", "openai"],
            "world": ["deepseek", "anthropic"],
            "character": ["deepseek", "anthropic"],
            "summarizer": ["deepseek", "ollama"],
        }
        providers = priority_map.get(agent_type, ["openai"])
        for p in providers:
            for cfg in configs:
                if cfg.enabled and cfg.provider.value == p:
                    return cfg
        return configs[0]
```

### 9.2 限流与并发控制

```python
# app/core/rate_limiter.py
from asyncio import Semaphore

class RateLimiter:
    def __init__(self, max_concurrent: int = 3):
        self.semaphore = Semaphore(max_concurrent)

    async def acquire(self):
        await self.semaphore.acquire()

    def release(self):
        self.semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        self.release()
```

---

## 10. 向量记忆系统

### 10.1 RAGService

详见 [5.4](#54-向量库-schema)。

### 10.2 索引策略

| 触发时机 | 内容 | 行为 |
|----------|------|------|
| 章节生成完成 | Chapter.plain_content | 按段落切片入库 |
| 章节生成完成 | Chapter.summary | 入库 |
| 章节生成完成 | Chapter.key_events | 每个事件入库 |
| 角色创建/更新 | Character.raw_text | 整体入库 |
| 世界观创建/更新 | WorldBible.raw_text | 按 section 切片入库 |

### 10.3 检索策略

```python
async def retrieve_for_chapter(
    self, work_id: UUID, outline_node: OutlineNode
) -> dict:
    """为章节生成检索相关上下文"""

    # 1. 检索相关历史章节
    related_chapters = await self.rag.query(
        work_id=work_id,
        query_text=f"{outline_node.title} {outline_node.summary}",
        n_results=5,
        filter={"type": "chapter_content"}
    )

    # 2. 检索涉及的设定
    world_refs = []
    if outline_node.world_refs:
        world_refs = await self.rag.query(
            work_id=work_id,
            query_text=outline_node.summary,
            n_results=3,
            filter={"type": "world"}
        )

    # 3. 检索涉及的人物
    char_contexts = []
    for char_id in outline_node.characters_involved:
        char = await self.character_service.get(char_id)
        char_contexts.append(char)

    return {
        "related_chapters": related_chapters,
        "world_refs": world_refs,
        "characters": char_contexts,
    }
```

### 10.4 增量更新

- 章节删除时，同步删除对应向量
- 章节内容修改时，更新对应向量
- 提供 `/admin/reindex` 端点重建索引

---

## 11. 任务与流式输出

### 11.1 任务生命周期

```
[Client] POST /chapters/generate
    │
    ▼
[Service] 创建 GenerationTask (status=pending)
    │
    ▼
[Service] 推入 arq 队列
    │
    ▼
[Worker] 取出任务，更新 status=running
    │
    ▼
[Orchestrator] 执行编排
    │
    ├─ 通过 WSManager 推送 progress/chunk/review
    │
    └─ 完成时更新 status=completed + result
```

### 11.2 WSManager

```python
# app/core/ws_manager.py
from fastapi import WebSocket
from collections import defaultdict

class WSManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, ws: WebSocket, task_id: str):
        await ws.accept()
        self.connections[task_id].append(ws)

    def disconnect(self, task_id: str):
        self.connections.pop(task_id, None)

    async def send(self, task_id: str, message: dict):
        """广播消息到所有订阅此 task 的连接"""
        dead = []
        for ws in self.connections.get(task_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections[task_id].remove(ws)
```

### 11.3 Arq Worker

```python
# app/workers/generation_worker.py
from arq.connections import ArqRedis
from app.orchestrator.chapter_orchestrator import ChapterOrchestrator

async def execute_chapter_generation(ctx: dict, task_id: str):
    """arq worker 入口"""
    orchestrator: ChapterOrchestrator = ctx["orchestrator"]
    graph = orchestrator.build_graph()
    await graph.ainvoke({
        "work_id": UUID(ctx["work_id"]),
        "chapter_id": UUID(ctx["chapter_id"]),
        ...
    })

# app/workers/arq_settings.py
from arq import RedisSettings
class WorkerSettings:
    redis_settings = RedisSettings(host="redis", port=6379)
    functions = [execute_chapter_generation]
    max_jobs = 3
```

---

## 12. 安全与隐私

### 12.1 敏感数据加密

```python
# app/services/crypto_service.py
from cryptography.fernet import Fernet
from app.config import settings

_cipher = None
def get_cipher():
    global _cipher
    if _cipher is None:
        # APP_SECRET 作为基础密钥
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"zhimeng-salt",
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.app_secret.encode()))
        _cipher = Fernet(key)
    return _cipher

def encrypt(plaintext: str) -> str:
    return get_cipher().encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    return get_cipher().decrypt(ciphertext.encode()).decode()
```

### 12.2 日志脱敏

```python
# app/utils/logger.py
import structlog
import re

SENSITIVE_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "sk-****"),
    (re.compile(r"sk-ant-[a-zA-Z0-9-]{20,}"), "sk-ant-****"),
]

def mask_sensitive(_, __, event_dict):
    for key, value in event_dict.items():
        if isinstance(value, str):
            for pattern, replacement in SENSITIVE_PATTERNS:
                value = pattern.sub(replacement, value)
            event_dict[key] = value
    return event_dict

structlog.configure(
    processors=[
        mask_sensitive,
        structlog.processors.JSONRenderer()
    ]
)
```

### 12.3 输入校验

- 所有 Pydantic Schema 严格校验
- 章节字数上限 10000 字（防 Token 爆炸）
- 文件上传大小限制 50MB
- API Key 格式校验（正则）

### 12.4 速率限制

```python
# app/api/deps.py
from slowapi import Limiter

limiter = Limiter(key_func=lambda: "global")

@app.post("/chapters/generate")
@limiter.limit("10/minute")  # 每分钟最多 10 次生成请求
async def generate_chapter(...):
    ...
```

---

## 13. 配置与环境变量

### 13.1 `.env.example`

```bash
# ===== 基础配置 =====
APP_ENV=production
APP_SECRET=change-me-to-random-32-chars-string
LOG_LEVEL=INFO

# ===== 数据库 =====
DATABASE_URL=sqlite+aiosqlite:////app/data/works/zhimeng.db

# ===== 向量库 =====
VECTOR_STORE_PATH=/app/data/vector_store
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5

# ===== Redis (可选) =====
REDIS_URL=redis://redis:6379/0

# ===== LLM API Keys (用户在前端配置后存 DB) =====
# OPENAI_API_KEY=sk-xxx
# ANTHROPIC_API_KEY=sk-ant-xxx
# DEEPSEEK_API_KEY=sk-xxx

# ===== 服务端口 =====
BACKEND_PORT=8000
WORKERS=2

# ===== 限流 =====
RATE_LIMIT_PER_MINUTE=60
MAX_CONCURRENT_LLM=3
```

### 13.2 `app/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "production"
    app_secret: str
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:////app/data/works/zhimeng.db"
    vector_store_path: str = "/app/data/vector_store"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    redis_url: str | None = None

    backend_port: int = 8000
    workers: int = 2

    rate_limit_per_minute: int = 60
    max_concurrent_llm: int = 3

settings = Settings()
```

---

## 14. 测试规范

### 14.1 测试层级

| 层级 | 工具 | 覆盖范围 |
|------|------|----------|
| 单元测试 | pytest | Agent、Service、Core 模块 |
| 集成测试 | pytest + httpx | API 端到端 |
| WebSocket 测试 | pytest + websockets | 流式输出 |
| E2E 测试 | pytest + docker | 完整流程 |

### 14.2 测试用例示例

```python
# tests/unit/test_agents/test_writer_agent.py
import pytest
from app.agents.writer_agent import WriterAgent

@pytest.mark.asyncio
async def test_writer_agent_build_prompt(mock_llm, mock_memory):
    agent = WriterAgent(mock_llm, mock_memory)
    ctx = {"chapter_title": "测试章", "target_words": 1000}
    messages = agent.build_prompt(ctx)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "测试章" in messages[0]["content"]

# tests/integration/test_chapters_api.py
@pytest.mark.asyncio
async def test_generate_chapter_endpoint(client, auth_headers):
    response = await client.post(
        "/api/v1/chapters/generate",
        json={
            "outline_node_id": "uuid",
            "target_words": 2000
        },
        headers=auth_headers
    )
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"

# tests/integration/test_websocket.py
@pytest.mark.asyncio
async def test_generation_websocket_flow():
    uri = "ws://localhost:8000/ws/generation/test-task-id"
    async with websockets.connect(uri) as ws:
        msg = await ws.recv()
        data = json.loads(msg)
        assert data["type"] == "connected"
```

### 14.3 测试覆盖率要求

- MVP 阶段：核心模块 ≥ 60%
- Beta 阶段：≥ 70%
- GA 阶段：≥ 80%

---

## 15. 部署方案

### 15.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y \
    gcc g++ libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction

COPY . .

# 数据卷
RUN mkdir -p /app/data/works /app/data/vector_store /app/data/logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 15.2 docker-compose 服务

```yaml
backend:
  build: ./backend
  container_name: zhimeng-backend
  ports:
    - "8000:8000"
  volumes:
    - ./data/works:/app/data/works
    - ./data/vector_store:/app/data/vector_store
    - ./data/logs:/app/data/logs
    - ./backend/.env:/app/.env:ro
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/works/zhimeng.db
    - VECTOR_STORE_PATH=/app/data/vector_store
  depends_on:
    - redis
  restart: unless-stopped

worker:
  build: ./backend
  container_name: zhimeng-worker
  command: arq app.workers.arq_settings.WorkerSettings
  volumes:
    - ./data/works:/app/data/works
    - ./data/vector_store:/app/data/vector_store
    - ./backend/.env:/app/.env:ro
  depends_on:
    - backend
    - redis
  restart: unless-stopped

redis:
  image: redis:7-alpine
  container_name: zhimeng-redis
  volumes:
    - redis_data:/data
  restart: unless-stopped

volumes:
  redis_data:
```

### 15.3 健康检查

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "database": "ok",
        "vector_store": "ok",
        "llm_configs": len([c for c in api_configs if c.enabled])
    }
```

---

## 16. 开发里程碑

### 16.1 v0.1 MVP（4 周）

| 周 | 后端任务 | 工时 |
|----|----------|------|
| W1 | FastAPI 骨架 + 配置 + DB Migration | 3d |
| W1 | SQLAlchemy 模型 (Work/Chapter/Outline) | 2d |
| W2 | CRUD API (Works/Chapters/Outline) | 3d |
| W2 | LLM Gateway + LiteLLM 集成 | 3d |
| W3 | Writer Agent (基础版) + WebSocket | 4d |
| W3 | 任务队列 (arq) + Redis | 2d |
| W4 | 导入导出 (TXT/DOCX) | 2d |
| W4 | Docker + 部署 + 文档 | 2d |
| W4 | 测试 + Bug 修复 | 2d |

### 16.2 v0.5 Beta（+8 周）

| 周 | 后端任务 |
|----|----------|
| W5-W6 | World/Character/Plot/Editor/Critic Agent |
| W7-W8 | Chroma 向量库 + RAG Service + Memory Service |
| W9-W10 | 一致性校验 + 连续性账本（TrackingState）+ 摘要滚动 |
| W11-W12 | 高级设置 + Prompt 编辑 + 模板系统 |

### 16.3 v1.0 GA（+4 周）

| 周 | 后端任务 |
|----|----------|
| W13 | 角色对话 + 多模型路由 |
| W14 | 插件化 Agent + 安全审计 |
| W15-W16 | 性能优化 + 压测 + 文档完善 |

---

## 附录

### 附录 A：常见错误码

| 错误码 | 含义 | HTTP |
|--------|------|------|
| `WORK_NOT_FOUND` | 作品不存在 | 404 |
| `CHAPTER_NOT_FOUND` | 章节不存在 | 404 |
| `NO_API_CONFIG` | 未配置 LLM | 400 |
| `LLM_CALL_FAILED` | LLM 调用失败 | 503 |
| `INVALID_TARGET_WORDS` | 目标字数不合法 | 400 |
| `TASK_NOT_RUNNING` | 任务未在运行 | 400 |
| `VECTOR_INDEX_FAILED` | 向量索引失败 | 500 |
| `IMPORT_PARSE_FAILED` | 导入解析失败 | 400 |

### 附录 B：术语表

| 术语 | 释义 |
|------|------|
| Orchestrator | 编排器，使用 LangGraph 管理多 Agent 协作 |
| State Graph | 状态图，LangGraph 中的核心数据结构 |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| Embedding | 向量化，将文本转为数值向量 |
| Token | LLM 处理的最小单位（≈ 0.75 个英文单词 / 1-2 个中文字） |
| WebSocket | 全双工通信协议，用于流式推送 |

### 附录 C：参考链接

- FastAPI: https://fastapi.tiangolo.com/
- LangGraph: https://langchain-ai.github.io/langgraph/
- SQLAlchemy 2.0: https://docs.sqlalchemy.org/en/20/
- Chroma: https://docs.trychroma.com/
- LiteLLM: https://docs.litellm.ai/
- Arq: https://arq-docs.helpmanual.io/

---

## 文档结束

> **下一步**：
> 1. 评审本后端需求文档
> 2. 同步评审 [FRONTEND_REQUIREMENTS.md](FRONTEND_REQUIREMENTS.md)
> 3. 创建后端项目骨架（`backend/` 目录初始化）
> 4. 按里程碑实现
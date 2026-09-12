# LingMa Backend

> Python 后端服务 - FastAPI + SQLAlchemy + LangGraph

## 快速开始

### 本地开发

```bash
# 1. 安装 Poetry（如果未安装）
curl -sSL https://install.python-poetry.org | python3 -

# 2. 安装依赖
poetry install

# 3. 复制环境变量
cp ../.env.example .env

# 4. 启动开发服务器
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：
- API: http://localhost:8000
- 文档: http://localhost:8000/docs

### Docker 启动（推荐）

从项目根目录：

```bash
./scripts/start.sh
```

## 目录结构

```
backend/
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 配置
│   ├── deps.py            # 依赖注入
│   ├── api/               # REST + WebSocket
│   │   ├── v1/            # API v1
│   │   └── ws/            # WebSocket
│   ├── core/              # LLM Gateway / RAG
│   ├── models/            # SQLAlchemy 模型
│   ├── schemas/           # Pydantic
│   ├── services/          # 业务服务
│   ├── agents/            # 6 个 AI Agent
│   ├── orchestrator/      # LangGraph 编排
│   └── utils/             # 工具
├── alembic/               # DB 迁移
├── tests/                 # 测试
└── pyproject.toml
```

## 开发命令

```bash
# 代码格式化
poetry run black .
poetry run ruff check --fix .

# 类型检查
poetry run mypy app/

# 测试
poetry run pytest

# 数据库迁移
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head
```

详见 [../docs/BACKEND_REQUIREMENTS.md](../docs/BACKEND_REQUIREMENTS.md)。
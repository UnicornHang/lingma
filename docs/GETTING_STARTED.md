# LingMa 快速启动

> 5 分钟跑起来 LingMa 小说工坊

本指南将带你在 **5 分钟内** 完成 LingMa 的本地部署并跑通完整链路。如果遇到任何问题，请查阅 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 或提交 Issue。

---

## 📋 前置要求

| 工具 | 最低版本 | 检查命令 |
|------|---------|----------|
| **Python** | 3.11+ | `python --version` |
| **Node.js** | 18+ | `node --version` |
| **Docker Desktop** | 4.0+ (推荐) | `docker --version` |
| **Git** | 任意 | `git --version` |

> 💡 不使用 Docker 也能跑，只需 Python + Node。

---

## 🚀 方式 A：Docker 一键启动（推荐）

适合：**不想折腾环境的用户**

### 步骤 1：克隆并进入项目

```bash
git clone <repo-url> lingma
cd lingma
```

### 步骤 2：复制环境变量模板

```bash
cp .env.example .env
```

打开 `.env`，**至少修改一项**：

```env
APP_SECRET=请改为你的随机字符串至少32位
```

可以用 Python 生成：
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 步骤 3：一键启动

**Linux / macOS：**
```bash
chmod +x scripts/*.sh
./scripts/start.sh
```

**Windows (PowerShell)：**
```powershell
# 后续版本将提供 PowerShell 脚本
docker compose up -d
```

### 步骤 4：访问

打开浏览器：[http://localhost:7860](http://localhost:7860)

看到 🎉 LingMa 首页 → **启动成功**！

### 步骤 5：停止

```bash
./scripts/stop.sh
# 或
docker compose down
```

---

## 🛠 方式 B：本地开发模式

适合：**前后端开发者，需要热更新 / 调试**

### 步骤 1：启动后端

```bash
cd backend

# 推荐使用 Poetry
pip install poetry
poetry install
poetry shell

# 或者使用 venv + pip
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

# 复制环境变量
cp ../.env.example .env

# 初始化数据库
python -m app.init_db   # 首次运行会自动建表

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

后端启动成功：
```
INFO    | 🚀 LingMa Backend 启动中...
INFO    | ✅ 数据库初始化完成
INFO    | ✅ 服务就绪，监听端口: 8000
```

API 文档：[http://localhost:8000/docs](http://localhost:8000/docs)

### 步骤 2：启动前端（新终端）

```bash
cd frontend

# 安装依赖
npm install
# 或 pnpm install

# 启动开发服务器
npm run dev
```

前端启动成功：
```
  VITE v5.x  ready in 320 ms
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

打开浏览器：[http://localhost:5173](http://localhost:5173)

> 💡 前端 dev server 已配置代理，`/api` 和 `/ws` 自动转发到 `localhost:8000`

### 步骤 3：验证联通

1. 打开前端首页 → 应能看到"灵码 · LingMa"标题
2. 点击"进入作品库" → 当前会显示"还没有作品"（预期行为）
3. 打开浏览器 DevTools → Network → 应能看到 `/api/v1/settings/` 请求成功

---

## 🧪 第一次使用

### 配置 LLM Key

1. 进入 **设置** → **API 配置**
2. 点击 **+ 添加配置**
3. 选择服务商（OpenAI / Anthropic / DeepSeek / 自定义）
4. 填入 **API Key** 与 **模型名**
5. 保存 → Key 即加密存储

> 🔒 Key 仅在你的本地加密存储，不会上传任何云端

### 创建你的第一本作品

1. 进入 **作品库** → 点击 **+ 新建作品**
2. 填写：
   - 作品名（如《凌天传说》）
   - 题材（玄幻 / 都市 / 言情 / ...）
   - 一句话简介
   - 目标字数
3. 保存 → 进入作品详情
4. 在 **大纲** 标签页，点击 **+ 生成大纲** → Agent 自动规划分卷与节拍
5. 在 **章节** 标签页，点击 **+ 生成章节** → Writer Agent 流式产出正文

---

## 🔧 常用命令

### 后端

```bash
# 运行测试
pytest tests/ -v

# 代码格式化
ruff format .
ruff check --fix .

# 类型检查
mypy app/

# 数据库迁移
alembic revision --autogenerate -m "add xxx"
alembic upgrade head

# 查看数据库
sqlite3 data/works/lingma.db
```

### 前端

```bash
# 开发
npm run dev

# 生产构建
npm run build

# 类型检查
npm run type-check

# Lint
npm run lint

# 测试
npm run test          # 单元
npm run test:e2e      # E2E (Playwright)

# 预览构建产物
npm run preview
```

### Docker

```bash
# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 进入容器
docker compose exec backend bash

# 重建镜像
docker compose build --no-cache

# 清理
docker compose down -v  # 注意：会删除数据卷！
```

---

## 🐛 常见问题

### Q1: 启动时 `APP_SECRET must be at least 32 characters`

A: 修改 `.env` 中的 `APP_SECRET` 为 32+ 字符的随机串。

### Q2: 端口 7860 / 8000 被占用

A: 修改 `docker-compose.yml` 中的端口映射，例如 `"8888:80"`。

### Q3: 前端访问 `/api/...` 报 404

A:
- Docker 模式：检查 Nginx 代理配置（`frontend/nginx.conf`）
- 本地模式：确认后端在 8000 端口运行；检查 `vite.config.ts` 中的 proxy

### Q4: Docker 构建卡在 `pip install`

A: 国内网络可配置镜像：
```bash
# 在 backend/Dockerfile 中加：
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q5: 数据库表不存在

A: 删除旧库后重启：
```bash
rm data/works/lingma.db
docker compose restart backend
```

### Q6: WebSocket 连不上

A: 检查 Nginx 配置是否透传 Upgrade 头（参考 `frontend/nginx.conf` 中的 `/ws/` 块）。

### Q7: 如何重置所有数据

A:
```bash
docker compose down
rm -rf data/
docker compose up -d
```

---

## 📚 下一步

- 📖 阅读 [ARCHITECTURE.md](ARCHITECTURE.md) 理解整体架构
- 🛠 阅读 [BACKEND_REQUIREMENTS.md](BACKEND_REQUIREMENTS.md) 开始后端开发
- 🎨 阅读 [FRONTEND_REQUIREMENTS.md](FRONTEND_REQUIREMENTS.md) 开始前端开发
- 📡 阅读 [API.md](API.md) 查看完整 API 列表
- 🤝 阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献流程

---

## 💬 获取帮助

- GitHub Issues: <repo-url>/issues
- 文档站: [docs/](.)
- 邮件: team@lingma.io

---

> 🎉 祝你创作愉快！
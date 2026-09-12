# 贡献指南

> 欢迎来到 LingMa！本文档帮助你快速上手贡献流程。

我们欢迎任何形式的贡献：代码、文档、Issue、创意。LingMa 是一个本地优先的 AI 小说创作工具，我们的目标是让每个写作者都能拥有自己的 AI 创作搭档。

---

## 📜 行为准则

- 尊重他人，不进行人身攻击
- 接受建设性批评，以协作心态讨论问题
- 关注对社区最有利的事情
- 展示同理心

---

## 🤔 我可以贡献什么？

### 适合新手的任务（good first issue）

- 📝 修正文档错别字 / 翻译
- 🎨 完善组件样式细节
- ✅ 为已有代码补单元测试
- 🐛 复现并确认他人报告的 Bug

### 进阶任务

- ✨ 实现新的 Agent 类型（战斗描写、对话润色、文风模仿）
- 🔌 接入新的 LLM Provider
- 🗄 优化数据库查询 / 索引
- 🎯 提升 RAG 检索质量

### 大型任务（建议先讨论）

- 🧠 重构 Orchestrator 为 LangGraph
- 🌍 多语言界面
- 👥 多人协作（CRDT / Yjs）

---

## 🔧 开发环境搭建

参见 [GETTING_STARTED.md](GETTING_STARTED.md) 的"方式 B：本地开发模式"。

### 推荐工具

| 工具 | 用途 |
|------|------|
| **VSCode** | IDE（推荐） |
| **Ruff** | Python Linter + Formatter |
| **Black** | Python 格式化（可选） |
| **ESLint + Prettier** | 前端代码质量 |
| **SQLite Browser** | 数据库浏览 |

### VSCode 推荐扩展

- Python
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- ES7+ React/Redux/React-Native snippets
- Conventional Commits

---

## 📁 项目结构速览

```
lingma/
├── backend/              # Python 后端
│   ├── app/
│   │   ├── api/         # HTTP/WS 路由
│   │   ├── agents/      # AI Agent 实现
│   │   ├── services/    # 业务逻辑
│   │   ├── models/      # ORM 模型
│   │   ├── schemas/     # Pydantic DTO
│   │   ├── orchestrator/# Agent 编排
│   │   └── main.py      # 入口
│   ├── tests/           # pytest 测试
│   └── pyproject.toml
│
├── frontend/            # React 前端
│   ├── src/
│   │   ├── api/         # HTTP 客户端
│   │   ├── components/  # UI 组件
│   │   ├── pages/       # 路由页面
│   │   ├── stores/      # 状态管理
│   │   └── types/       # 类型定义
│   └── package.json
│
├── docs/                # 文档
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── ...
│
├── scripts/             # 运维脚本
├── docker-compose.yml
└── README.md
```

---

## 📐 代码规范

### Python（后端）

- **格式化**：`ruff format`（等价 black）
- **Lint**：`ruff check`
- **类型注解**：所有公开函数必须带类型注解
- **文档字符串**：模块 / 类 / 公开函数使用 Google 风格 docstring
- **命名**：`snake_case`（变量/函数）、`PascalCase`（类）、`UPPER_CASE`（常量）
- **导入顺序**：标准库 → 第三方 → 本地（用 ruff 自动管理）

**示例**：
```python
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import Work
from app.services import work_service


async def list_user_works(
    db: AsyncSession,
    user_id: UUID,
    *,
    page: int = 1,
    page_size: int = 20,
) -> Sequence[Work]:
    """获取用户的作品列表（分页）。

    Args:
        db: 异步数据库 Session。
        user_id: 用户 UUID。
        page: 页码，从 1 开始。
        page_size: 每页条数，1-100。

    Returns:
        作品列表，按 updated_at 倒序。
    """
    ...
```

### TypeScript（前端）

- **格式化**：Prettier（默认配置）
- **Lint**：ESLint（`eslint-plugin-react-hooks` 必须开启）
- **类型**：所有导出函数 / 组件 props 必须有显式类型
- **禁止**：`any`（除非第三方无类型）、`@ts-ignore`（优先 `@ts-expect-error` + 注释）
- **命名**：`camelCase`（变量/函数）、`PascalCase`（组件/类/类型）、`UPPER_CASE`（常量）

**示例**：
```typescript
interface WorkCardProps {
  work: Work;
  onClick?: (id: string) => void;
}

export function WorkCard({ work, onClick }: WorkCardProps) {
  const progress = useMemo(
    () => Math.round((work.wordCount / work.targetWordCount) * 100),
    [work.wordCount, work.targetWordCount]
  );

  return (
    <Card hoverable onClick={() => onClick?.(work.id)}>
      {/* ... */}
    </Card>
  );
}
```

### 提交信息（Conventional Commits）

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 列表**：

| Type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 仅文档 |
| `style` | 不影响逻辑的格式变更 |
| `refactor` | 重构（既非 feat 也非 fix） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖 |

**Scope 建议**：`api` / `agent` / `db` / `ui` / `editor` / `auth` / `docs` ...

**示例**：
```
feat(agent): 实现 PlotAgent 的真实大纲生成逻辑

接入 GPT-4 模型，基于一句话简介生成 3 卷大纲。
使用 Pydantic 解析 LLM 输出，确保结构稳定。

Closes #42
```

---

## 🔀 Git 工作流

### 分支模型

```
main                  ← 稳定发布分支
├── feat/xxx          ← 功能分支
├── fix/xxx           ← 修复分支
└── docs/xxx          ← 文档分支
```

### 提交流程

1. **Fork 仓库**（如外部贡献者）或创建分支
2. **编写代码 + 测试**
3. **本地验证**（lint + test + type check）
4. **提交**（遵循 Conventional Commits）
5. **推送到你的分支**
6. **创建 Pull Request** 到 `main`
7. **Code Review** 后合并

### 分支命名

- `feat/add-character-agent`
- `fix/chapter-save-409`
- `docs/update-api-spec`

---

## ✅ PR 检查清单

提交 PR 前请确认：

- [ ] 代码遵循项目规范（lint + format 通过）
- [ ] 所有现有测试通过
- [ ] 新增代码有对应测试（覆盖率 ≥ 80%）
- [ ] 类型检查通过（mypy / tsc）
- [ ] 公开 API 有 docstring / JSDoc
- [ ] 涉及数据库变更时已编写 Alembic 迁移
- [ ] 涉及前端变更时已在主流浏览器验证
- [ ] 文档已更新（如 API.md / ARCHITECTURE.md）
- [ ] Commit 信息遵循 Conventional Commits
- [ ] PR 描述清楚说明了 **改了什么** + **为什么改** + **如何验证**

---

## 🧪 测试规范

### 后端测试（pytest）

```
tests/
├── conftest.py                  # 共享 fixtures
├── test_health.py
├── test_works.py                # 每个 API 模块一个文件
├── test_chapters.py
├── test_settings.py
├── test_crypto.py               # 服务层单测
└── test_agents/
    ├── test_plot_agent.py
    └── ...
```

**运行**：
```bash
pytest tests/ -v
pytest tests/test_works.py -v --tb=long    # 单文件
pytest tests/ -k "test_create" -v          # 按名称筛选
pytest tests/ --cov=app --cov-report=html  # 覆盖率
```

### 前端测试（Vitest + React Testing Library）

```
src/
├── __tests__/
│   ├── api/
│   │   └── works.test.ts
│   └── components/
│       └── WorkCard.test.tsx
```

**运行**：
```bash
npm run test          # 单元
npm run test:ui       # UI 模式
npm run test:coverage # 覆盖率
npm run test:e2e      # E2E (Playwright)
```

---

## 🐛 报告 Bug

提交 Issue 时请包含：

### Bug 报告模板

```markdown
## 描述
清晰简洁地描述 Bug。

## 复现步骤
1. ...
2. ...
3. ...

## 预期行为
应该发生什么。

## 实际行为
实际发生了什么。

## 环境
- OS: [e.g. Windows 11]
- Docker: [e.g. 4.18]
- Python: [e.g. 3.11.5]
- Node: [e.g. 20.10.0]
- LingMa 版本: [e.g. v0.1.0]

## 日志 / 截图
（如有）
```

---

## 💡 提出新功能

提 Issue 时请说明：

1. **痛点**：你遇到了什么问题？
2. **方案**：建议怎么解决？是否有替代方案？
3. **影响范围**：影响哪些模块？
4. **替代方案**：是否考虑过其他实现？

大型功能建议先在 Discussions 中讨论，再写 Issue。

---

## 🔐 安全问题

**请勿** 在公开 Issue 中报告安全漏洞。

请发送邮件到 **security@lingma.io**，主题前缀 `[SECURITY]`。我们会在 48 小时内回复。

---

## 📜 许可证

LingMa 使用 **MIT License**。贡献的代码默认遵循同一许可证。

详见 [LICENSE](../LICENSE)。

---

## 🙏 致谢

感谢所有贡献者（按贡献时间排序）：

<!-- 此处由 CI 自动生成 -->

---

> 🌟 期待你的第一个 PR！
# ZhiMeng API 参考

> 完整的 REST + WebSocket API 文档
>
> - 基地址：`http://localhost:8000`
> - API 前缀：`/api/v1`
> - 完整路径：`http://localhost:8000/api/v1/...`
> - WebSocket：`ws://localhost:8000/ws/...`
> - OpenAPI 文档：`/docs`（仅 development 环境）

---

## 目录

1. [通用约定](#通用约定)
2. [认证](#认证)
3. [错误响应](#错误响应)
4. [REST 端点](#rest-端点)
   - [作品 Works](#作品-works)
   - [连续性追踪 Tracking](#连续性追踪-tracking)
   - [章节 Chapters](#章节-chapters)
   - [设置 Settings](#设置-settings)
5. [WebSocket 端点](#websocket-端点)
   - [流式生成](#流式生成)
6. [数据模型 Schema](#数据模型-schema)

---

## 通用约定

- 所有请求/响应均为 `application/json`
- UUID 字段在 URL 中不带引号（如 `/works/abc-uuid-123`）
- 时间戳统一为 ISO 8601 格式（`2026-09-10T12:00:00+08:00`）
- 字段命名使用 **snake_case**（与 Python 后端一致）

### 标准查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码，从 1 开始 |
| `page_size` | int | 20 | 每页条数（1-100） |

---

## 认证

**MVP 阶段**：本地部署默认无需认证（仅 127.0.0.1 可访问）。

**未来**：将引入 JWT Token，通过 `Authorization: Bearer <token>` 头传递。

---

## 错误响应

统一错误格式：

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "作品 abc-uuid 不存在",
    "details": null
  }
}
```

| HTTP | 含义 | code 示例 |
|------|------|-----------|
| 400 | 请求参数错误 | `INVALID_PAYLOAD` |
| 401 | 未认证 | `UNAUTHORIZED` |
| 403 | 无权限 | `FORBIDDEN` |
| 404 | 资源不存在 | `RESOURCE_NOT_FOUND` |
| 409 | 冲突 | `DUPLICATE_RESOURCE` |
| 422 | Pydantic 校验失败 | `VALIDATION_ERROR` |
| 429 | 限流 | `RATE_LIMITED` |
| 500 | 服务器内部错误 | `INTERNAL_ERROR` |

---

## REST 端点

### 根路径

#### `GET /`
获取 API 元信息。

**响应**：
```json
{
  "name": "ZhiMeng API",
  "version": "0.1.0",
  "docs": "/docs"
}
```

---

#### `GET /health`
健康检查。

**响应**：
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "database": "ok",
  "vector_store": "ok"
}
```

---

### 作品 Works

#### `GET /api/v1/works/`
分页获取作品列表。

**Query 参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码 |
| `page_size` | int | 每页大小（1-100） |
| `status` | string | 状态过滤：`draft` / `writing` / `finished` / `archived` |

**响应**：
```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "c923ca2c-cddb-4cc7-a630-79998cea4481",
      "title": "凌天传说",
      "genre": "fantasy",
      "logline": "一个废柴少年逆袭的故事",
      "target_word_count": 1000000,
      "style_keywords": ["热血", "升级流"],
      "target_audience": ["青少年"],
      "status": "writing",
      "word_count": 35000,
      "settings": {},
      "created_at": "2026-09-10T10:00:00+08:00",
      "updated_at": "2026-09-10T15:30:00+08:00"
    }
  ]
}
```

---

#### `POST /api/v1/works/`
创建新作品。

**请求体**：
```json
{
  "title": "凌天传说",
  "genre": "fantasy",
  "logline": "一个废柴少年逆袭的故事",
  "target_word_count": 1000000,
  "style_keywords": ["热血", "升级流"],
  "target_audience": ["青少年"]
}
```

**字段说明**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 1-100 字符 |
| `genre` | enum | ✅ | `fantasy` / `urban` / `romance` / `historical` / `sci_fi` / `mystery` / `other` |
| `logline` | string | ❌ | 0-500 字符 |
| `target_word_count` | int | ❌ | 默认 1,000,000，范围 10,000-10,000,000 |
| `style_keywords` | string[] | ❌ | 默认 `[]` |
| `target_audience` | string[] | ❌ | 默认 `[]` |

**响应**：`201 Created` + Work 对象。

---

#### `GET /api/v1/works/{work_id}`
获取作品详情。

**响应**：`200 OK` + Work 对象；`404 Not Found` 如果不存在。

---

#### `PATCH /api/v1/works/{work_id}`
部分更新作品。所有字段可选。

**请求体**（示例）：
```json
{
  "title": "新标题",
  "status": "writing",
  "target_word_count": 1500000
}
```

**响应**：`200 OK` + 更新后的 Work 对象。

---

#### `DELETE /api/v1/works/{work_id}`
删除作品（级联删除章节、角色、大纲、世界书）。

**响应**：`204 No Content`。

---

#### `GET /api/v1/works/{work_id}/chapters`
便捷聚合：获取作品信息 + 其下的章节列表。

**Query 参数**：`page`、`page_size`（默认 50）。

**响应**：
```json
{
  "work": { /* Work 对象 */ },
  "total_chapters": 12,
  "chapters": [
    {
      "id": "6f30edd9-...",
      "title": "第一章 觉醒",
      "status": "draft",
      "word_count": 3200,
      "updated_at": "2026-09-10T..."
    }
  ]
}
```

---

### 连续性追踪 Tracking

对话不负责记忆。权威状态在 `tracking_states.payload`，下列接口只读写账本或返回派生视图。

#### `GET /api/v1/works/{work_id}/tracking`
返回伏笔、角色运行时状态、作者真相/读者已知时间线。Query `outline_node_id` 可选，传入则附带该细纲的写前上下文卡。

#### `GET /api/v1/works/{work_id}/tracking/context`
Writer 写前短卡：约束锁、出场角色状态、待收伏笔、知情范围。

#### `POST /api/v1/works/{work_id}/tracking/commit`
提交一章增量（埋笔、兑现、角色状态、时间线、备注）。备注上限 3072 字。

#### `POST /api/v1/works/{work_id}/tracking/foreshadows`
登记或更新一条伏笔（`open` / `paid` / `broken`）。

#### `PUT /api/v1/works/{work_id}/tracking/constraints/{outline_node_id}`
缓存细纲约束锁。细纲字段 `write_constraints` 仍是产品主入口。

---

### 章节 Chapters

#### `GET /api/v1/chapters/`
按作品列出章节。

**Query 参数**：
| 参数 | 必填 | 说明 |
|------|------|------|
| `work_id` | ✅ | UUID，所属作品 |
| `page` | ❌ | 默认 1 |
| `page_size` | ❌ | 默认 50，上限 200 |

**响应**：`ChapterListResponse`（结构与 `WorkListResponse` 类似）。

---

#### `POST /api/v1/chapters/`
创建章节。

**请求体**：
```json
{
  "work_id": "c923ca2c-...",
  "title": "第一章 觉醒",
  "content": { "type": "doc", "content": [...] },  // TipTap JSON，可选
  "plain_content": "少年猛然睁眼...",  // 纯文本，会自动统计字数
  "summary": "主角穿越觉醒",
  "key_events": ["睁眼", "发现经脉尽通"],
  "outline_node_id": null
}
```

**响应**：`201 Created` + Chapter 对象（自动填充 `word_count`、`version=1`）。

---

#### `GET /api/v1/chapters/{chapter_id}`
获取章节详情。

---

#### `PATCH /api/v1/chapters/{chapter_id}`
更新章节。每次更新 `version` 自动 +1。

**请求体**（任何字段可选）：
```json
{
  "title": "第一章 觉醒（修订）",
  "plain_content": "修改后的内容",
  "status": "reviewed"
}
```

**响应**：`200 OK` + 更新后的 Chapter 对象（带新 `version`）。

---

#### `DELETE /api/v1/chapters/{chapter_id}`
删除章节。

**响应**：`204 No Content`。

---

### 设置 Settings

#### `GET /api/v1/settings/`
获取应用全局设置。

**响应**：
```json
{
  "theme": "light",
  "language": "zh-CN",
  "font_size": 14,
  "auto_save_interval": 30,
  "default_model": null,
  "active_preset": null
}
```

---

#### `PATCH /api/v1/settings/`
更新设置。所有字段可选。

**请求体**：
```json
{
  "theme": "dark",
  "font_size": 16,
  "auto_save_interval": 60
}
```

---

#### `GET /api/v1/settings/api-configs`
列出所有 LLM API 配置（**不回显明文 Key，仅脱敏**）。

**响应**：
```json
[
  {
    "id": "f47ac10b-...",
    "name": "我的 OpenAI",
    "provider": "openai",
    "masked_key": "sk-p...mnop",
    "base_url": "https://api.openai.com/v1",
    "model_name": "gpt-4o-mini",
    "enabled": true,
    "max_context_tokens": 128000,
    "cost_per_1k_input": 0.00015,
    "cost_per_1k_output": 0.0006,
    "agent_assignments": ["writer", "editor"],
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

#### `POST /api/v1/settings/api-configs`
新增 API 配置（Key 加密存储）。

**请求体**：
```json
{
  "name": "我的 OpenAI",
  "provider": "openai",  // openai/anthropic/deepseek/qwen/ollama/custom
  "api_key": "sk-xxxx",  // 明文，仅此次传输
  "base_url": null,        // 可选，自定义网关
  "model_name": "gpt-4o-mini",
  "enabled": true,
  "max_context_tokens": 128000,
  "cost_per_1k_input": 0,
  "cost_per_1k_output": 0,
  "agent_assignments": []
}
```

**响应**：`201 Created` + ApiConfigRead（已脱敏）。

---

#### `PATCH /api/v1/settings/api-configs/{config_id}`
更新 API 配置。如需轮换 Key，在 `api_key` 字段传新值。

**请求体**：所有字段可选。

---

#### `DELETE /api/v1/settings/api-configs/{config_id}`
删除 API 配置。

**响应**：`204 No Content`。

---

#### `POST /api/v1/settings/api-configs/{config_id}/reveal`
**⚠️ 一次性显示明文 API Key**（不会再次返回）。

**响应**：
```json
{
  "api_key": "sk-xxxx"
}
```

> 🔒 仅在用户明确触发时调用，明文 Key 不会写入日志或前端持久化存储。

---

## WebSocket 端点

### 流式生成

#### `WS /ws/generation/{task_id}`

用于接收 LLM 流式生成结果（章节正文、大纲等）。

##### 协议

**握手**：
```
WS /ws/generation/<task_id>
```

服务端立即发送：
```json
{
  "type": "connected",
  "task_id": "uuid-string",
  "message": "WebSocket 已连接，请发送 start 启动生成"
}
```

##### 客户端 → 服务端

**1. 心跳**
```json
{ "type": "ping" }
```

**2. 启动生成**
```json
{
  "type": "start",
  "messages": [
    { "role": "system", "content": "你是一位玄幻小说家..." },
    { "role": "user",   "content": "请生成第一章，主角名叫林逸..." }
  ],
  "model": "gpt-4o-mini",
  "temperature": 0.8,
  "max_tokens": 3000
}
```

**3. 取消**
```json
{ "type": "cancel" }
```

##### 服务端 → 客户端

**开始事件**
```json
{
  "type": "start",
  "task_id": "...",
  "stream_id": "uuid",
  "model": "gpt-4o-mini"
}
```

**流式片段**（多个）
```json
{
  "type": "delta",
  "task_id": "...",
  "stream_id": "uuid",
  "content": "少年猛然睁眼，"
}
```

**完成事件**
```json
{
  "type": "done",
  "task_id": "...",
  "stream_id": "uuid",
  "content": "少年猛然睁眼，..."  // 完整内容
}
```

**错误事件**
```json
{
  "type": "error",
  "task_id": "...",
  "error": "LLM 调用超时"
}
```

**取消事件**
```json
{ "type": "cancelled", "task_id": "..." }
```

**心跳响应**
```json
{ "type": "pong" }
```

##### 客户端示例（JavaScript）

```typescript
const ws = new WebSocket('ws://localhost:8000/ws/generation/task-001');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'start',
    messages: [
      { role: 'system', content: '你是玄幻小说家' },
      { role: 'user', content: '写一段开场' }
    ],
    model: 'gpt-4o-mini',
    max_tokens: 1000
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  switch (msg.type) {
    case 'start':
      console.log('生成开始', msg.stream_id);
      break;
    case 'delta':
      // 增量追加到 UI
      appendToEditor(msg.content);
      break;
    case 'done':
      console.log('完成:', msg.content);
      saveToBackend(msg.content);
      break;
    case 'error':
      console.error('错误:', msg.error);
      break;
  }
};

// 心跳
setInterval(() => ws.send(JSON.stringify({ type: 'ping' })), 30000);
```

---

## 数据模型 Schema

### Work

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `title` | string | 1-100 字符 |
| `genre` | enum | `fantasy` \| `urban` \| `romance` \| `historical` \| `sci_fi` \| `mystery` \| `other` |
| `logline` | string | 0-500 字符 |
| `target_word_count` | int | 10,000-10,000,000 |
| `style_keywords` | string[] | 风格关键词 |
| `target_audience` | string[] | 目标读者 |
| `status` | enum | `draft` \| `writing` \| `finished` \| `archived` |
| `word_count` | int | 当前累计字数 |
| `settings` | object | 自定义扩展字段 |
| `created_at` | datetime | ISO 8601 |
| `updated_at` | datetime | ISO 8601 |

### Chapter

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `work_id` | UUID | 所属作品 |
| `title` | string | 1-200 字符 |
| `content` | object | TipTap JSON 结构 |
| `plain_content` | text | 纯文本（用于字数统计 / RAG） |
| `summary` | text | 摘要 |
| `key_events` | string[] | 关键事件 |
| `outline_node_id` | UUID? | 关联大纲节点 |
| `word_count` | int | 自动计算 |
| `status` | string | `draft` / `generated` / `reviewed` / `finalized` |
| `version` | int | 版本号（每次更新 +1） |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### ApiConfig

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `name` | string | 备注名 |
| `provider` | enum | `openai` \| `anthropic` \| `deepseek` \| `qwen` \| `ollama` \| `custom` |
| `masked_key` | string | 脱敏后的 Key（如 `sk-p...mnop`） |
| `base_url` | string | 自定义 Base URL |
| `model_name` | string | 默认模型 |
| `enabled` | bool | 是否启用 |
| `max_context_tokens` | int | 上下文窗口 |
| `cost_per_1k_input` | float | 输入价格（美元） |
| `cost_per_1k_output` | float | 输出价格（美元） |
| `agent_assignments` | string[] | 分配给哪些 Agent |

### SettingsBundle

| 字段 | 类型 | 默认值 |
|------|------|--------|
| `theme` | string | `"light"` |
| `language` | string | `"zh-CN"` |
| `font_size` | int | 14 |
| `auto_save_interval` | int | 30 |
| `default_model` | string? | null |
| `active_preset` | string? | null |

---

## 限流策略

| 端点 | 限制 |
|------|------|
| `/api/v1/*` | 60 请求/分钟/IP |
| `/ws/generation/*` | 3 并发 LLM 调用/实例 |

超出限制返回 `429 Too Many Requests`。

---

## 版本兼容

- 当前版本：`v0.1.0`
- 路径前缀 `/api/v1` 在 v1 系列内保证向后兼容
- 破坏性变更将发布新版本（如 `/api/v2`）

---

## 附录：完整端点列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | API 元信息 |
| GET | `/health` | 健康检查 |
| GET | `/api/v1/works/` | 作品列表 |
| POST | `/api/v1/works/` | 创建作品 |
| GET | `/api/v1/works/{id}` | 作品详情 |
| PATCH | `/api/v1/works/{id}` | 更新作品 |
| DELETE | `/api/v1/works/{id}` | 删除作品 |
| GET | `/api/v1/works/{id}/chapters` | 作品 + 章节列表 |
| GET | `/api/v1/chapters/` | 章节列表 |
| POST | `/api/v1/chapters/` | 创建章节 |
| GET | `/api/v1/chapters/{id}` | 章节详情 |
| PATCH | `/api/v1/chapters/{id}` | 更新章节 |
| DELETE | `/api/v1/chapters/{id}` | 删除章节 |
| GET | `/api/v1/settings/` | 应用设置 |
| PATCH | `/api/v1/settings/` | 更新设置 |
| GET | `/api/v1/settings/api-configs` | LLM 配置列表 |
| POST | `/api/v1/settings/api-configs` | 新增 LLM 配置 |
| PATCH | `/api/v1/settings/api-configs/{id}` | 更新 LLM 配置 |
| DELETE | `/api/v1/settings/api-configs/{id}` | 删除 LLM 配置 |
| POST | `/api/v1/settings/api-configs/{id}/reveal` | 显示明文 Key |
| WS | `/ws/generation/{task_id}` | 流式生成 |

---

> 📝 发现文档错误？[提交 Issue](https://github.com/your-org/zhimeng/issues)
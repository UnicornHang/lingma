# 织梦 (ZhiMeng) 小说 AI Agent 平台 — 产品需求文档 (PRD)

> 项目代号：**ZhiMeng Novel Studio**
> 文档版本：v1.0
> 文档日期：2026-09-10
> 文档状态：待评审

---

## 目录

1. [项目概述](#1-项目概述)
2. [用户画像与场景](#2-用户画像与场景)
3. [产品定位与核心价值](#3-产品定位与核心价值)
4. [功能需求详述](#4-功能需求详述)
5. [非功能需求](#5-非功能需求)
6. [系统架构设计](#6-系统架构设计)
7. [数据模型](#7-数据模型)
8. [API 设计规范](#8-api-设计规范)
9. [UI/UX 设计规范](#9-uiux-设计规范)
10. [本地化部署方案](#10-本地化部署方案)
11. [LLM 集成与模型适配](#11-llm-集成与模型适配)
12. [安全、隐私与合规](#12-安全隐私与合规)
13. [开发计划与里程碑](#13-开发计划与里程碑)
14. [风险评估与应对](#14-风险评估与应对)
15. [验收标准](#15-验收标准)
16. [附录](#附录)

---

## 1. 项目概述

### 1.1 项目名称

**ZhiMeng Novel Studio**（织梦·小说工坊）

### 1.2 项目愿景

打造一款 **零门槛、本地化、隐私安全** 的 AI 辅助小说创作平台，让任何用户无需编程、无需云端账号、无需付费订阅，即可在自己的电脑上享受专业级 AI Agent 协作创作小说的完整体验。

### 1.3 项目背景

- 现有 AI 写作工具多为 SaaS 形态，存在数据隐私、订阅成本、网络依赖等问题
- 网文作者群体规模庞大（国内超 2000 万），但缺乏工业化 AI 工具
- 个人玩家、写作爱好者、技术爱好者希望本地拥有"AI 写作团队"
- LLM 本地化部署能力（Ollama、vLLM 等）日趋成熟，使本地化方案具备可行性

### 1.4 项目目标

| 维度 | 目标 |
|------|------|
| **部署门槛** | 一行命令启动，普通用户 10 分钟内完成本地部署 |
| **核心能力** | 提供 6+ 专业 Agent 协作，覆盖大纲→章节→润色全流程 |
| **一致性** | 100 万字作品人物/世界观不崩坏 |
| **隐私** | 所有作品数据、API Key 仅存本地，不上传任何云端 |
| **成本** | 用户可使用本地模型（Ollama）或自有 API Key，零平台抽成 |

### 1.5 项目范围

**包含 (In Scope)**：
- Web 端应用（React + TypeScript）
- 后端服务（Python FastAPI）
- Agent 编排引擎
- 向量记忆系统
- 富文本编辑器
- 作品库管理
- 一键 Docker 部署

**不包含 (Out of Scope)**：
- 多端同步、移动端 App（V2 再议）
- 在线发布/分发功能
- 付费/会员体系
- 多人协作（V2 再议）

---

## 2. 用户画像与场景

### 2.1 目标用户

| 用户类型 | 占比 | 核心诉求 | 技术能力 |
|----------|------|----------|----------|
| **网文作者** | 40% | 高产、追热点、风格统一 | 中等 |
| **写作爱好者** | 30% | 低门槛、好玩、能写完整作品 | 较低 |
| **学生/创作者** | 20% | 学习写作技巧、生成作业/同人 | 中等 |
| **技术开发者** | 10% | 自部署、可定制、可扩展 | 高 |

### 2.2 典型使用场景

#### 场景 A：王老师（网文作者）

> 王老师是某平台签约作者，日更 8000 字。他需要在 3 小时内完成一章存稿，要求"主角不动主线、只推进支线、配角有血有肉"。

**使用流程**：
1. 打开 ZhiMeng → 选择作品《剑来·前传》
2. 点击「续写」→ 输入「支线推进，配角云浩出场」→ 选择「玄幻仙侠」风格
3. Writer Agent 自动调用 Character Agent 检索"云浩"过往言行
4. 30 秒内生成 2000 字初稿，王老师在编辑器中精修
5. Editor Agent 自动标出 3 处可优化位置，王老师一键采纳
6. 定稿保存至本地作品库

#### 场景 B：小李（写作爱好者）

> 小李是一名大学生，从未写过小说，想尝试创作一本校园言情。

**使用流程**：
1. 第一次启动，进入「新手引导」→ 选题材"言情" → 选风格"清新温暖"
2. 系统自动生成推荐大纲模板，小李选择「双向暗恋·成长线」
3. World Builder Agent 自动构建"青樱高中"世界观
4. Character Designer 创建男女主角人设卡
5. 逐步引导小李完成第 1-3 章

#### 场景 C：张工（技术开发者）

> 张工想本地部署一套 AI 写作系统供团队使用。

**使用流程**：
1. `git clone` 项目 → `docker-compose up -d` → 浏览器打开 `localhost:7860`
2. 在设置中配置自有 DeepSeek API Key 或本地 Ollama 模型
3. 配置多个 Agent 的 prompt 模板（高级设置）
4. 团队成员通过局域网访问（可选）

---

## 3. 产品定位与核心价值

### 3.1 一句话定位

**你的本地 AI 写作团队，零成本、零隐私泄露、零云端依赖。**

### 3.2 价值主张 vs 竞品

| 维度 | 通用 ChatGPT | 在线 AI 写作 SaaS | **ZhiMeng** |
|------|--------------|------------------|------------|
| 数据隐私 | ❌ 上传云端 | ❌ 上传云端 | ✅ 完全本地 |
| 长期一致性 | ⚠️ 弱 | ⚠️ 中 | ✅ 强（向量库） |
| 风格定制 | ⚠️ 需每次输入 | ⚠️ 模板有限 | ✅ 风格向量 |
| 协作能力 | ❌ 单模型 | ⚠️ 弱 | ✅ 6 Agent 协作 |
| 部署难度 | — | — | ✅ 一行命令 |
| 订阅成本 | $20/月 | $30-100/月 | ✅ 0 |

### 3.3 北极星指标

**用户的「作品完结率」**（开始创作的作品中，最终完成超过 5 万字的比例）。

---

## 4. 功能需求详述

### 4.1 功能总览

```
┌─────────────────────────────────────────────────────┐
│  ZhiMeng 功能架构                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  L1 - 作品层                                        │
│  ├─ 4.2 作品管理                                    │
│  ├─ 4.3 大纲与章节结构                              │
│  └─ 4.4 富文本编辑器                                │
│                                                     │
│  L2 - 智能体层（核心）                              │
│  ├─ 4.5 大纲策划 Agent                              │
│  ├─ 4.6 世界观 Agent                                │
│  ├─ 4.7 角色 Agent                                  │
│  ├─ 4.8 写作 Agent                                  │
│  ├─ 4.9 编辑 Agent                                  │
│  └─ 4.10 评审 Agent                                 │
│                                                     │
│  L3 - 记忆与知识层                                  │
│  ├─ 4.11 长期记忆（RAG）                            │
│  ├─ 4.12 人物卡管理                                 │
│  └─ 4.13 设定圣经管理                               │
│                                                     │
│  L4 - 系统层                                        │
│  ├─ 4.14 模型与 API 管理                            │
│  ├─ 4.15 Prompt 模板管理                            │
│  ├─ 4.16 导入导出                                   │
│  └─ 4.17 系统设置                                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 4.2 作品管理

#### 4.2.1 作品创建

**功能描述**：用户创建新作品，输入基础信息。

**输入字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 作品名 | string | ✅ | 1-50 字 |
| 题材类型 | enum | ✅ | 玄幻/都市/言情/历史/科幻/悬疑/其他 |
| 目标字数 | number | ❌ | 默认 100 万字 |
| 核心立意 | textarea | ❌ | 一句话描述核心主题 |
| 目标读者 | multi-enum | ❌ | 男频爽文/女频甜文/严肃文学等 |
| 风格关键词 | string[] | ❌ | 如"热血、轻松、反转" |

**业务规则**：
- 作品创建后自动生成唯一 ID（UUID）
- 默认创建空的"世界观"、"人物"、"大纲"、"章节"四个分区
- 支持从模板创建（预置 5-10 个常见题材大纲模板）

#### 4.2.2 作品列表

**功能描述**：展示用户所有作品，支持搜索、排序、筛选。

**列表字段**：封面缩略图、作品名、题材、最新更新时间、字数、状态（创作中/已完结/草稿）

**交互**：
- 点击进入作品详情
- 右键菜单：复制、导出、删除、改名
- 顶部筛选：按题材、按状态、按更新时间

#### 4.2.3 作品统计

**功能描述**：仪表盘展示统计信息。

**展示内容**：
- 总字数、最近 7 天日更字数曲线图
- 各 Agent 调用次数与 Token 消耗
- 作品完成度（基于目标字数）
- 章节列表及字数分布

### 4.3 大纲与章节结构

#### 4.3.1 大纲编辑器

**功能描述**：树状/列表结构管理作品大纲。

**节点类型**：
- 卷（如：第一卷·初入江湖）
- 章（如：第一章·风起青萍）
- 节拍点（如：主角登场 / 第一次冲突 / 阶段高潮）

**操作**：
- 拖拽排序
- 节点展开/折叠
- 节点详情：摘要（200 字）、关键事件、参与人物、目标字数
- AI 生成子节点：选中父节点 → 点击「AI 拆分」→ 选择粒度 → 自动生成子节点

#### 4.3.2 章节生成流程

**核心流程**：

```
用户在大纲中选中节点
  ↓
点击「生成章节」
  ↓
弹出配置面板：
  - 目标字数（1000-10000）
  - 风格参考（前 N 章片段 / 风格描述）
  - 重点要求（用户输入）
  - 涉及人物（多选）
  ↓
Writer Agent 启动：
  Step 1: 调用 Character Agent → 获取人物卡
  Step 2: 调用 Plot Agent → 获取上下文摘要
  Step 3: 调用 World Agent → 检索相关设定
  Step 4: 流式生成正文
  ↓
实时显示在富文本编辑器
  ↓
完成后 Editor Agent 自动审校 → 显示批注
```

### 4.4 富文本编辑器

#### 4.4.1 基础能力

**功能描述**：基于 TipTap 的所见即所得编辑器。

**核心功能**：
- 富文本格式化：标题、段落、粗体、斜体、引用、列表
- 字数实时统计（中英文分开）
- 自动保存（每 10 秒 / 失焦时）
- 撤销/重做（保留 50 步历史）
- 查找替换（支持正则）

#### 4.4.2 AI 增强交互

**侧边栏 AI 助手**：
- **续写**：选中光标位置 → 续写 N 字
- **改写**：选中段落 → 选择改写风格（更华丽/更简洁/更口语）
- **扩写/缩写**：选中段落 → 调整长度
- **翻译**：将选中段落翻译为目标语言
- **润色**：调用 Editor Agent 出建议
- **剧情走向**：基于当前内容给出 3 个走向建议

**交互方式**：
- 工具栏 AI 按钮
- 右键菜单
- 快捷键（自定义）
- 斜杠命令（输入 `/ai` 唤起）

#### 4.4.3 版本管理

**功能描述**：每次 AI 生成产生新版本，支持版本切换。

**展示形式**：

```
┌─────────────────────────────┐
│ 当前版本：v3（2026-09-10 14:30）│
│ [查看历史版本] [对比差异]   │
└─────────────────────────────┘
```

**支持**：
- 版本列表（按时间倒序）
- 任意版本切换
- 双版本 diff 查看
- 版本标签（"满意"、"初稿"、"AI建议"）

### 4.5 大纲策划 Agent (Plot Architect)

#### 4.5.1 Agent 职责

基于用户输入生成结构化大纲，遵循经典叙事结构。

#### 4.5.2 输入

- 题材类型、目标字数、核心立意、风格关键词
- 可选：参考作品（用户上传片段或 URL）

#### 4.5.3 输出结构

```json
{
  "title": "作品标题",
  "logline": "一句话简介",
  "structure": "三幕结构 / 起承转合 / 英雄之旅",
  "volumes": [
    {
      "name": "第一卷·卷名",
      "summary": "卷摘要（100字）",
      "chapters": [
        {
          "title": "第一章·章名",
          "summary": "章摘要（50字）",
          "beats": ["节拍1", "节拍2", "节拍3"],
          "characters": ["主角A", "配角B"],
          "target_words": 3000,
          "key_events": ["事件1", "事件2"]
        }
      ]
    }
  ]
}
```

#### 4.5.4 交互流程

1. 用户输入基本信息
2. Plot Agent 调用 LLM 生成大纲草案（流式）
3. 用户可要求「重写某个卷」「增加支线」「调整结构」
4. 用户可手动修改后让 Agent "基于修改扩展"

### 4.6 世界观 Agent (World Builder)

#### 4.6.1 Agent 职责

构建并维护作品的设定体系，保证一致性。

#### 4.6.2 管理维度

| 维度 | 内容 | 示例 |
|------|------|------|
| 地理 | 大陆、国家、城市、地标 | "天玄大陆、东荒圣域、长安城" |
| 势力 | 门派、种族、组织 | "青云剑宗、魔族皇庭" |
| 力量体系 | 等级、修炼路径、限制 | "筑基→金丹→元婴，资源有限" |
| 历史 | 时间线、大事件 | "三千年前的仙魔之战" |
| 规则 | 物理/魔法规则 | "凡人无法踏空，筑基期可御剑" |
| 文化 | 习俗、宗教、语言 | "剑修以剑为魂" |

#### 4.6.3 一致性校验

当其他 Agent 引用设定时，自动检查是否冲突：
- 例：用户写作"筑基期修士飞行千里"，Agent 提醒"设定中筑基期无法飞行，建议改为金丹期"

#### 4.6.4 输出形态

- 结构化 JSON（机器读）
- 可视化图谱（势力关系图、时间线）
- 自然语言文档（供 Prompt 注入）

### 4.7 角色 Agent (Character Designer)

#### 4.7.1 人物卡结构

```yaml
basic_info:
  name: 林墨
  age: 18
  gender: 男
  appearance: 黑衣黑发，面容清冷
  identity: 青云剑宗外门弟子

personality:
  traits: [沉默, 重情, 偏执]
  mbti: INTJ
  speech_style: 惜字如金，不善言辞，关键时刻语出惊人
  habits: [左手持剑, 独处时凝视远方]
  strengths: [剑道天赋, 隐忍]
  weaknesses: [不善社交, 容易自责]

backstory:
  origin: 孤儿出身，被师父收留
  formative_events: ["十岁目睹师门被灭", "十五岁复仇失败"]
  current_goal: "查明真相，重振师门"
  secrets: ["真实身世：魔族后裔"]

relationships:
  - target: 女主·苏婉
    type: 暗恋
    development: 暗恋 → 误会 → 真相 → 生死与共

arc:
  initial_state: 孤独少年
  final_state: 宗门之主
  growth_points: ["接受友情", "直面身世", "承担责任"]

voice_samples:
  - "我……不愿。"
  - "若此剑指苍生，我便折之。"
```

#### 4.7.2 一致性检查

每次角色出现，自动校验：
- 性格：对话是否符合 MBTI 和性格标签
- 说话方式：是否与 speech_style 一致
- 关系：对其他角色的态度是否符合关系定义
- 成长弧线：当前行为是否与 arc 进度一致

#### 4.7.3 角色对话能力

点击人物卡 → 「角色对话」→ 进入与该角色的对话界面：
- 用户扮演另一个角色或对话者
- 角色基于其人物卡回复
- 对话可一键转换为小说片段

### 4.8 写作 Agent (Writer)

#### 4.8.1 核心能力

基于大纲、人物、世界观、风格生成章节正文。

#### 4.8.2 Prompt 模板骨架（伪代码）

```python
SYSTEM_PROMPT = f"""
你是一位专业的小说家，正在创作《{title}》({genre})。
风格要求：{style_keywords}
参考片段：{few_shot_examples}

## 当前章节任务
章节：{chapter_title}
摘要：{chapter_summary}
节拍：{beats}
涉及人物：{characters}
重点要求：{user_instructions}

## 必须遵守
- 人物言行必须符合 Character Card
- 世界设定必须符合 World Bible
- 与前文衔接：{prev_chapter_summary}
- 目标字数：{target_words}
"""

USER_PROMPT = """
请开始创作本章正文。
"""
```

#### 4.8.3 上下文组装

```
[设定圣经摘要]
    ↓
[相关人物卡（前5个相关人物）]
    ↓
[前 3 章摘要]
    ↓
[当前章节大纲]
    ↓
[System Prompt + User Prompt]
    ↓
LLM 流式输出
```

#### 4.8.4 流式输出

- WebSocket 推送（Server-Sent Events 也可）
- 前端打字机效果展示
- 用户可随时暂停、续写

#### 4.8.5 长章节分段生成

- 单次生成超过 4000 字时自动分段
- 每段生成后写入数据库，断电可恢复
- 段间衔接校验

### 4.9 编辑 Agent (Editor)

#### 4.9.1 审校维度

| 维度 | 检查项 | 输出 |
|------|--------|------|
| 基础 | 错别字、病句、标点 | 红色高亮 + 修改建议 |
| 逻辑 | 时间线、人物行为合理性 | 黄色批注 |
| 一致性 | 人物、设定前后矛盾 | 橙色警告 |
| 节奏 | 张弛有度、爽点密度 | 评分（1-10）+ 优化建议 |
| 文笔 | 用词、句式、对话自然度 | 评分（1-10） |
| 风格 | 与作者风格向量偏差 | 偏差百分比 |

#### 4.9.2 批注展示

```
┌──────────────────────────────┐
│ 林墨皱眉道："我……不愿。"    │
│           ▲                  │
│           │ 建议：可加强内心戏│
│           │ 修改：林墨握紧双拳│
│           │       皱眉道："我…│
│           │       …不愿。"    │
└──────────────────────────────┘
[采纳] [忽略] [全部采纳]
```

#### 4.9.3 自动审校时机

- 每章生成完成后自动触发
- 用户手动点击「审校」
- 定时全作品审校（低优先级）

### 4.10 评审 Agent (Critic)

#### 4.10.1 模拟读者视角

预设多种读者 Persona：
- 爽文党：追爽点、节奏快、金手指
- 文青党：文笔、情感、意境
- 考据党：设定、逻辑、细节
- 萌新读者：可读性、引导性
- 主编视角：商业价值、市场定位

#### 4.10.2 评分维度

- 代入感：1-10
- 节奏：1-10
- 爽点/泪点密度：1-10
- 情感冲击：1-10
- 总评：A/B/C/D 等级

#### 4.10.3 输出

- 整体评分
- 优点 Top 3
- 改进建议 Top 3
- 具体段落点评
- 与历史章节对比

### 4.11 长期记忆系统（RAG）

#### 4.11.1 存储策略

| 内容类型 | 存储方式 | 用途 |
|----------|----------|------|
| 人物卡 | 结构化存储 + 向量 | 检索人物行为一致性 |
| 设定圣经 | 结构化存储 + 向量 | 检索世界观一致性 |
| 章节摘要 | 向量 + 时序索引 | 上下文衔接 |
| 章节原文 | 全文索引 + 向量 | 细节检索 |
| 关键事件 | 时序数据库 | 时间线校验 |

#### 4.11.2 向量化策略

```python
# 章节嵌入粒度
- 段落级：每段 200-500 字
- 章节摘要级：每章 1-2 个摘要
- 事件级：每章提取 5-10 个关键事件

# 检索时机
- 续写前：检索前 3 章 + 相似章节
- 角色出场前：检索该角色所有历史行为
- 涉及设定时：检索设定圣经相关条款
```

#### 4.11.3 摘要滚动

- 每章生成 300 字摘要
- 每 10 章生成一份卷摘要（1000 字）
- 全文生成一份总摘要（2000 字）
- 摘要本身就是上下文压缩

### 4.12 Prompt 模板管理（高级功能）

#### 4.12.1 用户可定制

提供 Prompt 编辑器，高级用户可自定义每个 Agent 的 Prompt 模板。

#### 4.12.2 模板市场（V2）

- 内置 50+ 模板（按题材分类）
- 用户可导入/导出模板
- 社区共享（V2）

#### 4.12.3 模板结构

```yaml
template:
  name: 玄幻爽文·男频·热血
  description: 适合《斗破苍穹》类风格
  variables: [主角名, 金手指类型, 故事背景]
  system_prompt: |
    你是一位玄幻小说作者...
  few_shot:
    - role: user
      content: ...
    - role: assistant
      content: ...
```

### 4.13 导入导出

#### 4.13.1 导入格式

- **TXT**：纯文本，自动按段落/空行切分
- **DOCX**：保留基础格式
- **EPUB**：拆章导入
- **JSON**：项目级导入/导出

#### 4.13.2 导出格式

- **TXT**
- **DOCX**
- **EPUB**（含目录）
- **PDF**（可选）
- **JSON**（项目级备份）

#### 4.13.3 项目级导入导出

```json
{
  "format_version": "1.0",
  "work_info": {...},
  "world_bible": {...},
  "characters": [...],
  "outline": {...},
  "chapters": [...],
  "settings": {...}
}
```

### 4.14 模型与 API 管理

#### 4.14.1 支持的模型来源

| 来源 | 配置方式 | 适用 |
|------|----------|------|
| **OpenAI** | API Key + Base URL | GPT-5 系列 |
| **Anthropic** | API Key | Claude Opus 5 |
| **DeepSeek** | API Key | 性价比之王 |
| **Qwen/通义** | API Key | 中文场景 |
| **Ollama** | 本地服务地址 | 完全本地 |
| **LM Studio** | 本地服务地址 | 桌面 GPU 用户 |
| **vLLM** | 自托管 | 企业用户 |
| **自定义** | OpenAI 兼容接口 | 任意兼容服务 |

#### 4.14.2 模型分配策略

- 用户可为每个 Agent 配置不同模型
- 推荐默认：
  - 大纲/世界观：DeepSeek-V3（性价比）
  - 写作主力：Claude Opus 5 或 GPT-5（质量优先）
  - 编辑润色：Claude Opus 5（细颗粒）
  - 评审：DeepSeek-V3（量大）
  - 简单任务：本地 Ollama

#### 4.14.3 成本追踪

- 每个 Agent 单独统计 Token 用量
- 作品维度成本汇总
- 月度账单视图（不发起实际支付）
- 支持设置月度预算告警

### 4.15 系统设置

#### 4.15.1 基础设置

- 界面语言（中文/英文）
- 主题（浅色/深色/跟随系统）
- 字体大小
- 自动保存间隔

#### 4.15.2 创作设置

- 默认目标字数
- 默认章节模板
- 默认风格关键词

#### 4.15.3 安全设置

- 数据加密（AES-256 本地存储）
- 自动备份策略（每 24 小时备份到指定目录）
- 清除缓存

#### 4.15.4 高级设置

- Agent Prompt 编辑
- 上下文窗口大小配置
- 向量库重置
- 日志查看

---

## 5. 非功能需求

### 5.1 性能需求

| 指标 | 要求 |
|------|------|
| 页面加载时间 | < 2 秒（首屏） |
| 大纲生成（3000 字大纲） | < 30 秒 |
| 单章生成（3000 字） | < 60 秒（流式，首字< 5 秒） |
| 向量检索（10 万字作品） | < 500ms |
| 编辑器响应 | < 100ms（无卡顿） |
| 并发 Agent 调用 | 支持 3+ Agent 并行 |

### 5.2 可用性需求

- 系统可用性 99.5%（本地部署时仅指服务进程）
- 异常恢复：网络中断后自动重连，任务可恢复
- 数据零丢失：所有操作事务化

### 5.3 兼容性需求

**操作系统**：
- Windows 10/11
- macOS 12+
- Ubuntu 20.04+ / Debian 11+

**浏览器**：
- Chrome 100+
- Edge 100+
- Safari 15+
- Firefox 100+

**硬件最低配置**：
- CPU：4 核
- 内存：8 GB（仅使用云端 API）
- 内存：16 GB（本地小模型）
- 硬盘：10 GB（含 Docker 镜像）

### 5.4 可扩展性需求

- 支持插件化 Agent（开发者可新增 Agent 类型）
- 支持自定义存储后端（SQLite/PostgreSQL）
- 支持自定义向量库（Chroma/Milvus/Qdrant）

### 5.5 国际化

- 中英文双语界面
- 数字、日期本地化
- 货币不展示（无支付场景）

---

## 6. 系统架构设计

### 6.1 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│  Browser (React SPA)                                         │
│  - Vite + React 18 + TypeScript + Zustand                    │
│  - TipTap Editor · Ant Design · Tailwind                     │
└────────────────────────────┬─────────────────────────────────┘
                       HTTP + WebSocket
┌────────────────────────────▼─────────────────────────────────┐
│              Nginx (Reverse Proxy, Optional)                 │
└────────────────────────────┬─────────────────────────────────┘
┌────────────────────────────▼─────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   REST API  │  │  WebSocket  │  │  Auth/限流  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Agent Orchestrator (LangGraph)                       │   │
│  │  - 状态机 · DAG · 工具调度 · 上下文组装               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Plot Agt │ │ World Agt│ │ Char Agt │ │ Writer   │ ...   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ LLM Gateway                                           │   │
│  │  - 路由 · 重试 · 缓存 · 限流 · Token 计费             │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────┘
                       │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐    ┌──────────┐    ┌─────────┐
   │ SQLite  │    │ Chroma   │    │  Local  │
   │ 主库    │    │ 向量库   │    │  Files  │
   └─────────┘    └──────────┘    └─────────┘
```

### 6.2 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| 前端框架 | React 18 + Vite + TypeScript | 生态成熟、性能优秀 |
| UI 组件 | Ant Design 5.x | 企业级、组件丰富 |
| 样式 | Tailwind CSS | 高效、可定制 |
| 状态管理 | Zustand | 轻量、TS 友好 |
| 编辑器 | TipTap | 强大、可扩展、AI 友好 |
| 图表 | ECharts | 数据可视化 |
| 后端框架 | FastAPI | 高性能、原生异步 |
| Agent 框架 | LangGraph | 状态机清晰、可观测 |
| 数据库 | SQLite | 零部署、单文件 |
| ORM | SQLAlchemy 2.0 | 成熟、async 友好 |
| 向量库 | Chroma | 嵌入式、易用 |
| 缓存 | Redis (可选) | 高性能缓存 |
| 任务队列 | Celery / Arq | 异步任务 |
| LLM 客户端 | LiteLLM | 统一多模型接口 |
| 容器化 | Docker Compose | 一键部署 |
| 文档站点 | Docusaurus | 用户手册 |

### 6.3 目录结构

```
zhimeng/
├── docker-compose.yml
├── docker-compose.override.yml   # 可选：本地模型
├── .env.example
├── README.md
├── docs/                          # 用户文档
│   ├── PRD.md
│   ├── getting-started.md
│   ├── configuration.md
│   └── faq.md
├── frontend/                      # React 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/
│   │   ├── components/
│   │   ├── stores/
│   │   ├── api/
│   │   └── types/
│   └── Dockerfile
├── backend/                       # Python 后端
│   ├── pyproject.toml
│   ├── alembic/                   # DB 迁移
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── works.py
│   │   │       ├── chapters.py
│   │   │       ├── agents.py
│   │   │       └── settings.py
│   │   ├── agents/                # Agent 实现
│   │   │   ├── base.py
│   │   │   ├── plot.py
│   │   │   ├── world.py
│   │   │   ├── character.py
│   │   │   ├── writer.py
│   │   │   ├── editor.py
│   │   │   └── critic.py
│   │   ├── core/                  # 核心能力
│   │   │   ├── llm_gateway.py
│   │   │   ├── orchestrator.py
│   │   │   ├── memory.py
│   │   │   └── rag.py
│   │   ├── models/                # SQLAlchemy 模型
│   │   ├── schemas/               # Pydantic Schema
│   │   └── utils/
│   ├── tests/
│   └── Dockerfile
├── data/                          # 数据卷
│   ├── works/
│   ├── vector_store/
│   └── logs/
└── scripts/
    ├── init.sh
    ├── backup.sh
    └── restore.sh
```

### 6.4 关键流程

#### 6.4.1 章节生成流程

```
[用户操作] 选中大纲节点 → 点击"生成章节"
    │
    ▼
[前端] POST /api/v1/chapters/generate
    │   body: {outline_node_id, target_words, style, ...}
    │
    ▼
[后端] ChapterService.create_generation_task()
    │   ├─ 写入 generation_task 表
    │   └─ 推送任务到队列
    │
    ▼
[Worker] AgentOrchestrator.execute_chapter_generation()
    │   │
    │   ├─ Step 1: 上下文组装
    │   │   ├─ Memory.retrieve_related(outline_node)
    │   │   ├─ World.retrieve(outline_node.world_refs)
    │   │   ├─ Character.retrieve(outline_node.char_refs)
    │   │   └─ Plot.retrieve(outline_node.plot_refs)
    │   │
    │   ├─ Step 2: Prompt 构建
    │   │   └─ PromptBuilder.build_writer_prompt(ctx)
    │   │
    │   ├─ Step 3: LLM 调用（流式）
    │   │   └─ LLMGateway.stream_generate(prompt)
    │   │
    │   ├─ Step 4: 实时推送（WebSocket）
    │   │   └─ PushService.push_chunk(content)
    │   │
    │   ├─ Step 5: 完成后审校
    │   │   ├─ EditorAgent.review(content)
    │   │   └─ PushService.push_review(suggestions)
    │   │
    │   └─ Step 6: 持久化
    │       ├─ 写入 chapter 表
    │       └─ 向量化索引
    │
    ▼
[前端] 实时展示生成内容 + 审校批注
```

---

## 7. 数据模型

### 7.1 核心实体关系图

```
┌─────────┐       ┌──────────────┐       ┌──────────┐
│  Work   │1─────*│   Volume     │1─────*│ Chapter  │
└─────────┘       └──────────────┘       └──────────┘
     │                                          │
     │1                                        *
     │                                          │
     ├──* WorldBible                           *
     │                                          │
     │1                                        │
     │                                          │
     ├──* Character                  OutlineNode
     │
     ├──* SettingRule
     │
     └──* StyleProfile
```

### 7.2 主要表结构（SQLAlchemy）

```python
# works 表
class Work(Base):
    __tablename__ = "works"
    id: UUID (PK)
    title: str
    genre: str
    target_word_count: int
    logline: str                    # 一句话简介
    style_keywords: JSON
    status: enum                    # draft/writing/finished/archived
    created_at: datetime
    updated_at: datetime
    word_count: int                 # 冗余字段，加速统计
    settings: JSON                  # 作品级配置

# volumes 表（卷）
class Volume(Base):
    __tablename__ = "volumes"
    id: UUID (PK)
    work_id: UUID (FK)
    title: str
    summary: str
    order: int
    target_word_count: int

# chapters 表
class Chapter(Base):
    __tablename__ = "chapters"
    id: UUID (PK)
    work_id: UUID (FK)
    volume_id: UUID (FK, nullable)
    outline_node_id: UUID (FK, nullable)
    title: str
    content: TEXT                   # 富文本 JSON
    summary: str                    # 章节摘要
    key_events: JSON                # 关键事件列表
    word_count: int
    status: enum                    # draft/generated/reviewed/finalized
    version: int
    current_version_id: UUID
    created_at: datetime
    updated_at: datetime

# chapter_versions 表（版本历史）
class ChapterVersion(Base):
    __tablename__ = "chapter_versions"
    id: UUID (PK)
    chapter_id: UUID (FK)
    version_no: int
    content: TEXT
    generated_by: enum              # user/ai/ai_revised
    prompt_used: TEXT
    model_used: str
    token_usage: JSON
    created_at: datetime

# world_bible 表
class WorldBible(Base):
    __tablename__ = "world_bibles"
    id: UUID (PK)
    work_id: UUID (FK, unique)
    geography: JSON                 # 地理
    factions: JSON                  # 势力
    power_system: JSON              # 力量体系
    timeline: JSON                  # 时间线
    rules: JSON                     # 规则
    culture: JSON                   # 文化
    raw_text: TEXT                  # 自然语言版本

# characters 表
class Character(Base):
    __tablename__ = "characters"
    id: UUID (PK)
    work_id: UUID (FK)
    name: str
    basic_info: JSON
    personality: JSON
    backstory: JSON
    relationships: JSON
    arc: JSON
    voice_samples: JSON
    appearance_count: int
    first_appearance_chapter: UUID

# outline_nodes 表
class OutlineNode(Base):
    __tablename__ = "outline_nodes"
    id: UUID (PK)
    work_id: UUID (FK)
    parent_id: UUID (FK, nullable)
    type: enum                      # volume/chapter/beat
    title: str
    summary: str
    beats: JSON
    characters_involved: JSON       # [character_id]
    world_refs: JSON                # [world_setting_id]
    target_word_count: int
    order: int

# generation_tasks 表
class GenerationTask(Base):
    __tablename__ = "generation_tasks"
    id: UUID (PK)
    work_id: UUID (FK)
    chapter_id: UUID (FK, nullable)
    outline_node_id: UUID (FK, nullable)
    task_type: enum                 # outline/chapter/review/edit/...
    status: enum                    # pending/running/completed/failed
    progress: int                   # 0-100
    error: TEXT
    result: JSON
    started_at: datetime
    completed_at: datetime

# settings 表
class Setting(Base):
    __tablename__ = "settings"
    key: str (PK)
    value: JSON
    encrypted: bool                 # API Key 等敏感字段加密

# api_configs 表
class APIConfig(Base):
    __tablename__ = "api_configs"
    id: UUID (PK)
    provider: enum                  # openai/anthropic/deepseek/...
    api_key_encrypted: TEXT
    base_url: str
    model_name: str
    enabled: bool
    agent_assignments: JSON         # 哪个 Agent 用哪个模型
```

### 7.3 向量库 Schema

```python
# 每个作品独立的 collection
collection_name = f"work_{work_id}"

# 存储的文档类型
{
    "id": "uuid",
    "type": "character" | "world" | "chapter_summary" | "event",
    "work_id": "uuid",
    "chapter_id": "uuid",
    "text": "向量化的文本",
    "metadata": {
        "character_id": "uuid",
        "type": "character",
        "created_at": "timestamp"
    }
}
```

---

## 8. API 设计规范

### 8.1 通用规范

- Base URL：`http://localhost:8000/api/v1`
- 认证：本地部署无认证（如需可加 basic auth）
- 数据格式：JSON
- 时间格式：ISO 8601 (UTC)
- 错误响应：统一格式

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "章节字数超出范围",
    "details": {...}
  }
}
```

### 8.2 REST API 列表

#### 作品相关

```
GET    /works                         # 作品列表
POST   /works                         # 创建作品
GET    /works/{id}                    # 作品详情
PATCH  /works/{id}                    # 更新作品
DELETE /works/{id}                    # 删除作品
GET    /works/{id}/statistics         # 作品统计
POST   /works/{id}/export             # 导出作品
POST   /works/import                  # 导入作品
```

#### 大纲相关

```
GET    /works/{id}/outline            # 获取大纲树
POST   /works/{id}/outline/nodes      # 创建节点
PATCH  /outline/nodes/{id}            # 更新节点
DELETE /outline/nodes/{id}            # 删除节点
POST   /works/{id}/outline/ai-generate   # AI 生成大纲
POST   /outline/nodes/{id}/ai-expand  # AI 扩展节点
```

#### 章节相关

```
GET    /works/{id}/chapters           # 章节列表
GET    /chapters/{id}                  # 章节详情
PATCH  /chapters/{id}                 # 更新章节（手动编辑）
DELETE /chapters/{id}                 # 删除章节
GET    /chapters/{id}/versions        # 版本列表
POST   /chapters/{id}/switch-version  # 切换版本
POST   /chapters/generate             # 生成章节（异步）
POST   /chapters/{id}/ai-continue     # AI 续写
POST   /chapters/{id}/ai-rewrite      # AI 改写
POST   /chapters/{id}/ai-expand       # AI 扩写
POST   /chapters/{id}/ai-shorten      # AI 缩写
POST   /chapters/{id}/ai-polish       # AI 润色
POST   /chapters/{id}/ai-review       # AI 审校
```

#### 世界观相关

```
GET    /works/{id}/world              # 获取世界圣经
PUT    /works/{id}/world              # 整体更新
PATCH  /works/{id}/world/{section}    # 部分更新（如 factions）
POST   /works/{id}/world/ai-build     # AI 构建世界观
POST   /works/{id}/world/check-consistency   # 一致性检查
```

#### 角色相关

```
GET    /works/{id}/characters         # 角色列表
POST   /works/{id}/characters         # 创建角色
GET    /characters/{id}               # 角色详情
PATCH  /characters/{id}               # 更新角色
DELETE /characters/{id}               # 删除角色
POST   /characters/{id}/ai-design     # AI 设计角色
POST   /characters/{id}/chat          # 角色对话
GET    /characters/{id}/appearances   # 出场记录
```

#### Agent 与生成任务

```
POST   /agents/plot/generate          # 大纲生成
POST   /agents/world/generate
POST   /agents/character/generate
POST   /agents/editor/review
POST   /agents/critic/evaluate
GET    /tasks/{id}                    # 查询任务状态
GET    /tasks                         # 任务列表
```

#### 设置相关

```
GET    /settings                      # 获取所有设置
PUT    /settings/{key}                # 更新单个设置
GET    /api-configs                   # API 配置列表
POST   /api-configs                   # 新增 API 配置
PATCH  /api-configs/{id}              # 更新
DELETE /api-configs/{id}              # 删除
POST   /api-configs/{id}/test         # 测试连接
```

### 8.3 WebSocket API

#### 连接

```
ws://localhost:8000/ws/generation/{task_id}
```

#### 消息类型

```typescript
// 服务端推送
type WSMessage =
  | { type: 'start', task_id: string, total?: number }
  | { type: 'chunk', task_id: string, content: string }  // 流式输出
  | { type: 'progress', task_id: string, progress: number }
  | { type: 'log', task_id: string, message: string }
  | { type: 'review', task_id: string, suggestions: any[] }  // 编辑批注
  | { type: 'complete', task_id: string, result: any }
  | { type: 'error', task_id: string, error: string }

// 客户端发送
type WSCommand =
  | { type: 'pause', task_id: string }
  | { type: 'resume', task_id: string }
  | { type: 'cancel', task_id: string }
  | { type: 'change_params', params: any }
```

---

## 9. UI/UX 设计规范

### 9.1 设计原则

1. **专业而不失温度**：类 Notion 的清爽感 + 创作软件的工具感
2. **AI 隐于幕后**：AI 能力通过侧边栏、悬浮按钮呈现，不打断创作流
3. **键盘优先**：重度作者依赖快捷键
4. **信息密度合理**：左侧导航 + 主编辑区 + 右侧 AI 助手的三栏布局

### 9.2 设计系统

**主色板**：
- Primary：`#5B5FE9`（沉稳紫蓝，专属感）
- Secondary：`#1F2937`（深灰，专业感）
- Accent：`#F59E0B`（琥珀色，AI 高亮）

**字体**：
- 中文：思源宋体（正文）/ 思源黑体（UI）
- 英文：Inter
- 等宽：JetBrains Mono

**间距**：8px 网格

**圆角**：6px（卡片）/ 4px（按钮）

### 9.3 关键页面线框

#### 9.3.1 主页（作品列表）

```
┌─────────────────────────────────────────────────────────────┐
│  ZhiMeng        🔍搜索  ⚙️设置  👤用户  📚文档                │
├─────────────────────────────────────────────────────────────┤
│  我的作品 (12)                                              │
│  [全部] [玄幻] [都市] [言情] [历史] [科幻] [悬疑]            │
│  排序：最新更新 ▼   视图：网格 | 列表    [➕新建作品]        │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 📕剑来前传│ │ 📗重生2008│ │ 📘暖阳   │ │ 📙银河纪元│      │
│  │ 玄幻·创作中│ │ 都市·创作中│ │ 言情·草稿  │ │ 科幻·完结  │      │
│  │ 35.2万字 │ │ 12.8万字 │ │ 0.5万字  │ │ 80万字    │      │
│  │ 更新于2h前│ │ 更新于昨日│ │ —        │ │ 已完结    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

#### 9.3.2 作品详情页（编辑器）

```
┌────────────────────────────────────────────────────────────────────┐
│  ←返回剑来前传  [第一章·风起青萍]  📝v3  ⚙️   [▶续写] [📊评审] [📥导出]│
├────────┬────────────────────────────────────────────────┬──────────┤
│ 📚大纲 │  风起青萍                                       │ 🤖 AI    │
│        │                                                │          │
│ ▼第一卷│  林墨独行于山道，薄暮时分，夕阳将他的影子拉得极长。│ 上下文: │
│  ▶第1章│  他抬头望向远方，那里是青云剑宗的山门所在……      │  [大纲] │
│  ▶第2章│                                                │  [人物] │
│  ▶第3章│  忽然，一阵剑鸣从身后传来……                       │  [风格] │
│        │                                                │          │
│ ▼世界  │  ...                                           │ ────    │
│  势力  │                                                │ AI操作: │
│  修炼  │  字数: 2,847    状态: AI生成v3 · 已审校          │  [续写] │
│  规则  │                                                │  [改写] │
│        │                                                │  [扩写] │
│ ▼人物  │                                                │  [润色] │
│  林墨  │                                                │ ────    │
│  苏婉  │                                                │ 评审:   │
│  云浩  │                                                │  8.5/10 │
│        │                                                │  👍爽点足│
│ [📊统计]│                                                │  💡改进3│
└────────┴────────────────────────────────────────────────┴──────────┘
```

#### 9.3.3 新建作品引导

```
┌────────────────────────────────────────────────────────────┐
│  ✨ 开启你的创作之旅                                       │
│                                                            │
│  Step 1 / 4   ────●────○────○────○                         │
│                                                            │
│  你想写什么类型的故事？                                    │
│                                                            │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ ⚔️玄幻│ │ 🏙️都市│ │ 💕言情│ │ 📜历史│ │ 🚀科幻│ │ 🎭悬疑│   │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘   │
│                                                            │
│  或者告诉我你想写什么：[___________________________]      │
│                                                            │
│                          [上一步]              [下一步 →]  │
└────────────────────────────────────────────────────────────┘
```

---

## 10. 本地化部署方案

### 10.1 部署架构

#### 10.1.1 极简部署（仅 API 模式）

适用：用户有云端 API Key，没有本地 GPU。

```
┌─────────────────────────┐
│  Docker Compose         │
│  ├─ backend (FastAPI)   │
│  ├─ frontend (Nginx)    │
│  └─ redis (缓存，可选)  │
└─────────────────────────┘
       │
       ▼
  浏览器访问 localhost:7860
```

#### 10.1.2 完整本地化（无 API）

适用：用户希望完全本地化，无外部调用。

```
┌─────────────────────────────────────────────┐
│  Docker Compose                             │
│  ├─ backend (FastAPI)                       │
│  ├─ frontend (Nginx)                        │
│  ├─ redis (缓存)                            │
│  └─ ollama (本地 LLM，可选)                 │
└─────────────────────────────────────────────┘
       │
       ▼
  浏览器访问 localhost:7860
  Ollama 服务 localhost:11434
```

### 10.2 docker-compose.yml（极简版）

```yaml
version: '3.8'

services:
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
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: zhimeng-frontend
    ports:
      - "7860:80"
    depends_on:
      - backend
    restart: unless-stopped

  # 可选：本地 LLM（用户有 GPU 时启用）
  ollama:
    image: ollama/ollama:latest
    container_name: zhimeng-ollama
    profiles: ["local-llm"]
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

volumes:
  ollama_data:
```

### 10.3 一键启动脚本

`./scripts/start.sh`：

```bash
#!/bin/bash
set -e

echo "🚀 ZhiMeng 启动中..."

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 创建数据目录
mkdir -p ./data/works ./data/vector_store ./data/logs

# 复制环境变量模板
if [ ! -f ./backend/.env ]; then
    cp ./backend/.env.example ./backend/.env
    echo "⚠️  请编辑 backend/.env 配置 API Key 后重新启动"
fi

# 启动
docker compose up -d --build

echo "✅ ZhiMeng 已启动！"
echo "📖 访问: http://localhost:7860"
echo "📚 文档: docs/getting-started.md"
```

### 10.4 环境变量模板（.env.example）

```bash
# ===== 基础配置 =====
APP_ENV=production
APP_SECRET=change-me-to-random-string
LOG_LEVEL=INFO

# ===== 数据库 =====
DATABASE_URL=sqlite+aiosqlite:////app/data/works/zhimeng.db

# ===== 向量库 =====
VECTOR_STORE_PATH=/app/data/vector_store
EMBEDDING_MODEL=text-embedding-3-small   # 或本地 bge-small

# ===== LLM API Keys（至少配置一个）=====
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEEPSEEK_API_KEY=
QWEN_API_KEY=

OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_BASE_URL=https://api.anthropic.com
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# ===== 本地模型（Ollama 等）=====
OLLAMA_BASE_URL=http://ollama:11434

# ===== 服务端口 =====
BACKEND_PORT=8000
FRONTEND_PORT=7860
```

### 10.5 系统要求与资源占用

| 配置项 | 最低 | 推荐 |
|--------|------|------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB |
| 硬盘 | 10 GB | 50 GB（含本地模型） |
| 操作系统 | Win10 / macOS 12 / Ubuntu 20.04 | Win11 / macOS 14 / Ubuntu 22.04 |
| Docker | 20.10+ | 最新 |

### 10.6 升级与备份

**数据备份**：

```bash
./scripts/backup.sh
# 输出 ./backups/zhimeng_20260910_140000.tar.gz
```

**数据恢复**：

```bash
./scripts/restore.sh ./backups/zhimeng_xxx.tar.gz
```

**升级**：

```bash
git pull
docker compose down
docker compose up -d --build
```

---

## 11. LLM 集成与模型适配

### 11.1 LLM 网关设计

```python
class LLMGateway:
    """统一 LLM 调用入口，支持重试、缓存、降级"""

    def __init__(self, configs: List[APIConfig]):
        self.configs = configs
        self.cache = RedisCache()

    async def generate(
        self,
        messages: List[Message],
        agent_type: str,        # 用于路由模型
        stream: bool = False,
        **kwargs
    ) -> AsyncIterator[str] | str:
        # 1. 选择模型
        config = self._select_config(agent_type)

        # 2. 缓存命中检查
        cached = await self.cache.get(messages)
        if cached:
            yield cached
            return

        # 3. 调用 LLM（含重试、降级）
        for attempt in range(3):
            try:
                response = await self._call(config, messages, stream, **kwargs)
                await self.cache.set(messages, response)
                yield response
                return
            except Exception as e:
                if attempt == 2:
                    # 降级到次选模型
                    config = self._fallback_config(agent_type)
                    if not config:
                        raise

    def _select_config(self, agent_type: str) -> APIConfig:
        # 根据 Agent 类型路由到不同模型
        return self.configs[0]
```

### 11.2 默认模型推荐配置

| Agent | 推荐模型 | 备选 |
|-------|----------|------|
| Plot | DeepSeek-V3 | GPT-5 |
| World | Claude Opus 5 | DeepSeek-V3 |
| Character | Claude Opus 5 | DeepSeek-V3 |
| Writer | Claude Opus 5 | GPT-5 |
| Editor | Claude Opus 5 | GPT-5 |
| Critic | DeepSeek-V3 | GPT-5-mini |

### 11.3 上下文窗口管理

| 模型 | 上下文窗口 | 使用策略 |
|------|-----------|----------|
| Claude Opus 5 | 200K | 全量上下文 + 摘要备份 |
| GPT-5 | 128K | 摘要压缩 |
| DeepSeek-V3 | 64K | 必须做 RAG |
| 本地 7B | 8K-32K | 强 RAG + 严格摘要 |

### 11.4 Token 成本预估

以一个 100 万字作品为例：
- 输入 Token：~5M（含所有 Prompt + RAG 检索）
- 输出 Token：~1M（生成）
- 总计：~6M Tokens
- DeepSeek-V3 价格：约 ¥30-50
- Claude Opus 5 价格：约 ¥300-500

---

## 12. 安全、隐私与合规

### 12.1 数据安全

- **本地存储**：所有用户数据存储于本地 `data/` 目录
- **加密存储**：API Key 等敏感字段使用 AES-256 加密（密钥来自 APP_SECRET）
- **数据库加密**：可选启用 SQLCipher
- **传输加密**：本地 HTTP 可选启用 HTTPS（自签证书）

### 12.2 隐私保护

- **零云端上传**：作品内容、API Key、设置**绝不上传**到任何外部服务（除 LLM API 调用外）
- **日志脱敏**：日志中自动遮蔽 API Key、作品内容
- **网络隔离**：可配置为完全离线运行

### 12.3 内容安全

- **可选内容过滤**：调用 LLM 前可选启用敏感词过滤
- **免责声明**：用户自负创作内容责任
- **多语言合规**：默认遵循用户所在司法管辖区

### 12.4 API Key 安全

- 加密存储（AES-256）
- 仅在前端脱敏展示（`sk-****1234`）
- 不写入日志
- 不发送到任何非 LLM 服务

---

## 13. 开发计划与里程碑

### 13.1 整体路线图

```
v0.1 (MVP)        v0.5 (Beta)               v1.0 (GA)
2026-Q4          2027-Q1                  2027-Q2
   │                  │                          │
   ▼                  ▼                          ▼
┌────────┐      ┌──────────┐            ┌──────────┐
│ 核心闭环│      │ 完整 Agent│            │  商业化  │
│ 验证   │      │ +记忆系统 │            │  + 生态  │
└────────┘      └──────────┘            └──────────┘
```

### 13.2 MVP（v0.1）功能范围 — 4 周

**目标**：验证核心创作闭环

**必须功能**：
- ✅ 作品创建、列表、详情
- ✅ 大纲编辑器（手动）
- ✅ 富文本编辑器（基础）
- ✅ 单一写作 Agent（基于大模型生成章节）
- ✅ 章节保存
- ✅ 基础设置（API Key 配置）
- ✅ Docker 一键部署
- ✅ Web 流式输出

**不包含**：
- ❌ 多 Agent 协作
- ❌ RAG 记忆系统
- ❌ 编辑 Agent 审校
- ❌ 评审 Agent
- ❌ 角色卡系统
- ❌ 模板市场

### 13.3 Beta（v0.5）功能范围 — 8 周

**新增**：
- ✅ 6 个 Agent 全部上线
- ✅ 世界观 Agent、角色 Agent
- ✅ RAG 向量记忆（Chroma）
- ✅ 编辑 Agent + 批注
- ✅ 评审 Agent
- ✅ 长期一致性保证
- ✅ 版本管理
- ✅ 导入导出
- ✅ 高级设置（Prompt 编辑）

### 13.4 GA（v1.0）功能范围 — 12 周

**新增**：
- ✅ 角色对话（Interactive NPC）
- ✅ 多模型智能路由
- ✅ 模板市场（内置 50+ 模板）
- ✅ 插件系统（开发者扩展）
- ✅ 完善的统计与计费
- ✅ 文档站点
- ✅ 性能优化
- ✅ 安全审计

### 13.5 详细任务分解（v0.1 MVP）

| 模块 | 任务 | 工时 | 优先级 |
|------|------|------|--------|
| 后端 | FastAPI 项目骨架 | 0.5d | P0 |
| 后端 | 数据库设计与迁移 | 1d | P0 |
| 后端 | Work/Chapter CRUD API | 2d | P0 |
| 后端 | LLM 网关（LiteLLM 集成） | 2d | P0 |
| 后端 | 流式输出接口 | 1d | P0 |
| 后端 | WebSocket 服务 | 1d | P0 |
| 前端 | Vite + React + TS 骨架 | 0.5d | P0 |
| 前端 | 路由 + 状态管理 | 1d | P0 |
| 前端 | 作品列表页 | 2d | P0 |
| 前端 | 富文本编辑器集成 | 2d | P0 |
| 前端 | 章节生成交互 | 3d | P0 |
| 前端 | 设置页 | 1d | P0 |
| DevOps | Docker 配置 | 1d | P0 |
| DevOps | 启动脚本 + 文档 | 1d | P0 |
| 测试 | 单元测试 | 2d | P0 |
| 测试 | 集成测试 | 1d | P0 |

**总工时**：~22 人天

---

## 14. 风险评估与应对

| 风险 | 等级 | 影响 | 应对措施 |
|------|------|------|----------|
| **LLM 上下文窗口不足** | 高 | 长作品生成崩坏 | RAG + 摘要 + 分段生成 |
| **生成质量不稳定** | 高 | 用户体验差 | 多次采样择优 + Editor 审校 |
| **本地部署门槛高** | 中 | 用户放弃使用 | Docker Compose 一键启动 + 详细文档 |
| **API 成本不可控** | 中 | 用户流失 | 成本仪表盘 + 预算告警 + 本地模型选项 |
| **Agent 状态不一致** | 中 | 设定前后矛盾 | Character/World Bible 强校验 |
| **数据丢失** | 低 | 用户损失 | 自动备份 + 版本管理 |
| **LLM 服务商变动** | 低 | 服务中断 | 多模型路由 + 降级 |
| **Docker 镜像过大** | 低 | 用户下载慢 | 多阶段构建 + 镜像瘦身 |

---

## 15. 验收标准

### 15.1 MVP 验收标准

#### 功能验收

- [ ] 用户能创建、编辑、删除作品
- [ ] 用户能创建大纲节点
- [ ] 用户能基于大纲生成章节，流式展示
- [ ] 用户能在编辑器中手动编辑章节
- [ ] 用户能保存、查看历史版本
- [ ] 用户能配置至少一种 LLM API Key
- [ ] 系统支持 LLM 流式响应
- [ ] 数据持久化到本地 SQLite

#### 部署验收

- [ ] 提供 `docker-compose.yml`，一行命令启动
- [ ] 默认配置下，浏览器访问 `localhost:7860` 可用
- [ ] 提供 README 文档，含截图
- [ ] 提供故障排查指南

#### 性能验收

- [ ] 章节生成首字延迟 < 5 秒
- [ ] 3000 字章节完整生成 < 60 秒
- [ ] 页面首屏加载 < 3 秒

#### 安全验收

- [ ] API Key 加密存储
- [ ] 密码字段前端脱敏
- [ ] 日志中无明文敏感信息

### 15.2 Beta 验收标准（增量）

- [ ] 6 个 Agent 全部实现且可工作
- [ ] 100 万字作品人物一致性错误率 < 5%
- [ ] RAG 检索响应 < 1 秒
- [ ] 支持至少 4 个 LLM 服务商
- [ ] 支持至少 1 种本地模型

### 15.3 GA 验收标准（增量）

- [ ] 端到端测试覆盖率 > 70%
- [ ] 文档完整度 100%（API、用户、运维）
- [ ] 安全审计通过
- [ ] 性能压测通过（100 万字作品场景）

---

## 附录

### 附录 A：术语表

| 术语 | 释义 |
|------|------|
| Agent | 智能体，本系统中指专门执行某类任务的 LLM 应用 |
| Orchestrator | 编排器，调度多个 Agent 协作的引擎 |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| World Bible | 世界圣经，存储作品世界观设定的结构化文档 |
| Character Card | 人物卡，存储角色全部属性的结构化文档 |
| Few-shot | 少样本学习，在 Prompt 中提供示例 |
| Prompt Template | Prompt 模板，预定义的可复用 Prompt 结构 |

### 附录 B：参考资源

- LangGraph 文档：https://langchain-ai.github.io/langgraph/
- TipTap 文档：https://tiptap.dev/
- FastAPI 文档：https://fastapi.tiangolo.com/
- Chroma 向量库：https://www.trychroma.com/
- Ollama 本地模型：https://ollama.com/

### 附录 C：变更日志

| 版本 | 日期 | 变更 | 作者 |
|------|------|------|------|
| v1.0 | 2026-09-10 | 初版 | ZhiMeng Team |

---

## 文档结束

> **下一步行动**：
> 1. 评审本文档，确认 MVP 范围
> 2. 创建项目骨架（`git init` + 目录结构）
> 3. 实现 MVP（4 周）
> 4. 灰度发布到 GitHub
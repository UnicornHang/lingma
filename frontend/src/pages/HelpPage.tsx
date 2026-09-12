import { useState } from 'react';
import {
  Search,
  BookOpen,
  Rocket,
  Bot,
  Edit,
  MessagesSquare,
  Github,
  Sparkles,
  ChevronRight,
} from 'lucide-react';

const CATEGORIES = [
  { key: 'start',    label: '快速开始', icon: Rocket },
  { key: 'agent',    label: 'Agent 使用', icon: Bot },
  { key: 'editor',   label: '编辑器技巧', icon: Edit },
  { key: 'community', label: '社区与支持', icon: MessagesSquare },
];

const FAQS = [
  {
    q: '如何接入 LLM API？',
    a: '前往「系统设置 → LLM API 配置」添加 OpenAI / Anthropic / DeepSeek / Ollama 等 Provider。所有密钥使用 AES-256-GCM 加密存储于本机 data/secrets.json。',
  },
  {
    q: '数据是云端保存还是本地？',
    a: '灵码完全本地化：作品数据存于 SQLite + Chroma 向量库（data/ 目录），API Key 加密存储。不上传任何云端，断网也可使用。',
  },
  {
    q: '如何让 Writer 续写一个章节？',
    a: '在章节编辑器右侧 Co-pilot 面板的「提示词」按钮中输入续写需求，例如「从『他没有立刻回答』开始 · 节奏：慢热」。Agent 会参考已建好的角色档案、世界观圣经与最近 5 章上下文生成。',
  },
  {
    q: '如何避免百万字级别的人物崩坏？',
    a: '角色档案与世界圣经会自动注入 RAG 检索上下文。每次生成都会校验：角色声音一致性、设定一致性、伏笔簿。Co-pilot 面板会高亮显示冲突项。',
  },
  {
    q: '可以自定义 Agent 吗？',
    a: 'v0.3 将开放 SDK：基于 LangGraph 的自定义节点，支持私有 Prompt 与工具调用。详见开发文档。',
  },
];

export default function HelpPage() {
  const [activeCat, setActiveCat] = useState('start');
  const [openIdx, setOpenIdx] = useState<number | null>(0);

  return (
    <div className="w-full h-full overflow-y-auto bg-surface-container-low">
      <div className="max-w-[1080px] mx-auto px-8 py-8 flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="text-display font-bold text-on-surface">使用文档</h1>
            <p className="text-body-md text-on-surface-variant">
              从快速开始到高级技巧 · 与 5,000+ 创作者一同精进
            </p>
          </div>
        </div>

        {/* Search bar */}
        <div className="surface-card p-6 flex flex-col gap-3">
          <div className="flex items-center px-3 h-12 rounded-lg border border-outline-variant/50 bg-surface-container-lowest">
            <Search size={20} className="text-outline" />
            <input
              placeholder="搜索文档：比如「API 配置」「角色档案」「批量替换」..."
              className="flex-1 outline-none ml-3 bg-transparent text-body-md text-on-surface"
            />
            <span className="font-code-sm text-outline px-2 py-0.5 rounded bg-surface-container">⌘ K</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-label-sm text-on-surface-variant">热门：</span>
            {['配置 LLM', '新建作品', 'Writer 续写', '批量替换', '导出 Markdown', '备份与恢复'].map((t) => (
              <button key={t} className="px-3 py-1 rounded-full bg-surface-container-low text-on-surface-variant text-label-md hover:bg-primary-fixed hover:text-on-primary-container">
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Categories */}
        <section className="grid grid-cols-4 gap-4">
          {CATEGORIES.map((c) => {
            const active = c.key === activeCat;
            return (
              <button
                key={c.key}
                onClick={() => setActiveCat(c.key)}
                className={`p-6 rounded-xl flex flex-col items-start gap-3 text-left ${
                  active ? 'surface-card-active' : 'surface-card hover:border-primary-container'
                }`}
              >
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${active ? 'bg-primary text-white' : 'bg-primary-container text-primary'}`}>
                  <c.icon size={26} />
                </div>
                <div className="flex flex-col">
                  <h3 className="text-label-lg font-semibold text-on-surface">{c.label}</h3>
                  <span className="text-body-sm text-on-surface-variant">
                    {c.key === 'start'    && '10 分钟跑通你的第一部 AI 小说'}
                    {c.key === 'agent'    && '6 个协作 Agent 详细使用指南'}
                    {c.key === 'editor'   && 'TipTap 编辑器高效技巧'}
                    {c.key === 'community' && '5,000+ 用户社区 + GitHub + Discord'}
                  </span>
                </div>
              </button>
            );
          })}
        </section>

        {/* Quick start + FAQ */}
        <section className="grid grid-cols-3 gap-4">
          <div className="col-span-2 surface-card p-6 flex flex-col gap-4">
            <h2 className="text-headline-sm font-semibold text-on-surface pb-2 border-b border-outline-variant/40 flex items-center gap-2">
              <Rocket size={20} className="text-primary" />
              快速开始（5 步）
            </h2>
            {[
              { n: 1, title: '配置 LLM API', desc: '在「系统设置 → LLM API 配置」添加至少一个 Provider。推荐先用 DeepSeek 或 Ollama。' },
              { n: 2, title: '新建作品', desc: '从作品库点击「新建作品」，跟随向导填好体裁、受众、节奏、风格关键词。' },
              { n: 3, title: '打开章节编辑器', desc: '点击「打开编辑器」进入 3 列视图：左侧大纲 + 中间正文 + 右侧 Co-pilot。' },
              { n: 4, title: '调用 Writer 续写', desc: '选中一段文本，点击工具栏「提示词」按钮，输入续写需求并「接受」。' },
              { n: 5, title: '让 Critic 评分', desc: 'Co-pilot 面板自动给出节奏 / 对话 / 描写 / 钩子 4 个维度的 0-10 分。' },
            ].map((s) => (
              <div key={s.n} className="flex items-start gap-3">
                <span className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold text-label-md flex-shrink-0">
                  {s.n}
                </span>
                <div className="flex-1">
                  <h3 className="text-label-lg font-semibold text-on-surface">{s.title}</h3>
                  <p className="text-body-sm text-on-surface-variant mt-0.5">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="surface-card p-6 flex flex-col gap-3">
            <h2 className="text-headline-sm font-semibold text-on-surface pb-2 border-b border-outline-variant/40">
              常见问题
            </h2>
            {FAQS.map((f, i) => {
              const open = openIdx === i;
              return (
                <div key={i} className="border-b border-outline-variant/20 last:border-b-0">
                  <button
                    onClick={() => setOpenIdx(open ? null : i)}
                    className="w-full flex items-center justify-between py-3 text-left"
                  >
                    <span className="text-label-md text-on-surface font-semibold">{f.q}</span>
                    <ChevronRight
                      size={18}
                      className={`text-outline transition-transform ${open ? 'rotate-90' : ''}`}
                    />
                  </button>
                  {open && (
                    <p className="text-body-sm text-on-surface-variant pb-3">
                      {f.a}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Links */}
        <section className="grid grid-cols-3 gap-4">
          <a
            href="#"
            className="surface-card p-6 flex flex-col gap-2 hover:border-primary-container cursor-pointer"
          >
            <BookOpen size={28} className="text-primary" />
            <span className="text-label-lg font-semibold text-on-surface">开发文档</span>
            <span className="text-body-sm text-on-surface-variant">从 SDK 到自定义 Agent 的完整指南</span>
          </a>
          <a
            href="#"
            className="surface-card p-6 flex flex-col gap-2 hover:border-primary-container cursor-pointer"
          >
            <Github size={28} className="text-primary" />
            <span className="text-label-lg font-semibold text-on-surface">GitHub 仓库</span>
            <span className="text-body-sm text-on-surface-variant">查看源码、提交 Issue、参与开发</span>
          </a>
          <a
            href="#"
            className="surface-card p-6 flex flex-col gap-2 hover:border-primary-container cursor-pointer"
          >
            <Sparkles size={28} className="text-primary" />
            <span className="text-label-lg font-semibold text-on-surface">示例提示词</span>
            <span className="text-body-sm text-on-surface-variant">社区精选的 120+ 高质量 Prompt 模板</span>
          </a>
        </section>
      </div>
    </div>
  );
}
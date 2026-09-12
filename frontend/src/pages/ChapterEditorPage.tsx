import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Bot,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Bold,
  Italic,
  Underline,
  Heading,
  Quote,
  List,
  ListOrdered,
} from 'lucide-react';

// 示例大纲树
const OUTLINE = [
  {
    volume: '第一卷·少年游',
    chapters: 42,
    expanded: true,
    items: [
      { id: 'c1',  title: '第 1 章 洞天风云',  wordCount: '2.4k', active: false },
      { id: 'c11', title: '第 11 章 意外来客', wordCount: '3.2k', active: true },
      { id: 'c12', title: '第 12 章 山雨欲来', wordCount: '2.8k', active: false },
    ],
  },
  { volume: '第二卷·江湖路', chapters: 38, expanded: false, items: [] },
  { volume: '第三卷·风波起', chapters: 36, expanded: false, items: [] },
];

const TABS = ['分析', '批注', '角色', '一致性', '伏笔'];

export default function ChapterEditorPage() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <div className="flex w-full h-full bg-surface-container-low">
      {/* Outline tree (left, 300px) */}
      <aside className="w-[300px] flex-shrink-0 h-full bg-surface-container-lowest border-r border-outline-variant/30 overflow-y-auto flex flex-col">
        <div className="p-6 border-b border-outline-variant/30">
          <h3 className="text-headline-sm font-semibold text-on-surface flex items-center justify-between">
            <span>剑来·前传</span>
            <button className="text-outline"><Plus size={18} /></button>
          </h3>
          <p className="text-body-sm text-on-surface-variant mt-1">
            35.2 万字 · 142 章 · 玄幻
          </p>
        </div>
        <div className="p-4 flex flex-col gap-1">
          {OUTLINE.map((vol) => (
            <div key={vol.volume} className="flex flex-col gap-0.5">
              <button className="flex items-center justify-between px-2 py-1 rounded hover:bg-surface-container">
                {vol.expanded ? (
                  <ChevronDown size={16} className="text-outline" />
                ) : (
                  <ChevronRight size={16} className="text-outline" />
                )}
                <span className="text-label-md font-semibold text-on-surface flex-1 ml-1 text-left">
                  {vol.volume}
                </span>
                <span className="font-code-sm text-outline">{vol.chapters} 章</span>
              </button>
              {vol.expanded && (
                <div className="ml-4 flex flex-col gap-0.5">
                  {vol.items.map((c) => (
                    <a
                      key={c.id}
                      href="#"
                      className={`flex items-center gap-2 px-2 py-1.5 rounded text-body-sm ${
                        c.active
                          ? 'bg-primary-container text-on-primary-container font-semibold'
                          : 'text-on-surface-variant hover:bg-surface-container'
                      }`}
                    >
                      <FileText size={14} />
                      <span className="flex-1">{c.title}</span>
                      <span className="font-code-sm">{c.wordCount}</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* Editor (center) */}
      <section className="flex-1 h-full overflow-y-auto bg-surface-container-low">
        <div className="max-w-[880px] mx-auto px-8 py-8">
          {/* Breadcrumb + title */}
          <div className="flex items-center gap-2 text-on-surface-variant text-label-md mb-2">
            <span>第一卷·少年游</span>
            <span className="text-outline">/</span>
            <span>第 11 章</span>
          </div>
          <h1 className="text-display font-bold text-on-surface">意外来客</h1>
          <div className="flex items-center gap-2 mt-2">
            <span className="chip-tertiary">玄幻</span>
            <span className="chip-primary">高潮</span>
            <span className="chip-secondary">POV · 第一人称</span>
            <span className="font-code-sm text-on-surface-variant">3,247 / 3,500 字</span>
          </div>

          {/* Toolbar */}
          <div className="flex items-center gap-1 p-1 mt-4 bg-surface-container-lowest rounded-lg border border-outline-variant/40 shadow-L1-card">
            {[Bold, Italic, Underline].map((Icon, i) => (
              <button key={i} className="text-on-surface-variant hover:bg-surface-container rounded px-2 py-1">
                <Icon size={18} />
              </button>
            ))}
            <div className="w-px h-5 bg-outline-variant/40 mx-1" />
            {[Heading, Quote].map((Icon, i) => (
              <button key={i} className="text-on-surface-variant hover:bg-surface-container rounded px-2 py-1">
                <Icon size={18} />
              </button>
            ))}
            <div className="w-px h-5 bg-outline-variant/40 mx-1" />
            {[List, ListOrdered].map((Icon, i) => (
              <button key={i} className="text-on-surface-variant hover:bg-surface-container rounded px-2 py-1">
                <Icon size={18} />
              </button>
            ))}
            <div className="w-px h-5 bg-outline-variant/40 mx-1" />
            <button className="px-2 py-1 text-primary bg-primary-container rounded">
              <Bot size={18} />
            </button>
            <span className="px-2 py-1 text-label-sm text-primary font-semibold">提示词</span>
            <span className="ml-auto px-2 py-1 text-body-sm text-on-surface-variant">
              已自动保存 · 12 秒前
            </span>
          </div>

          {/* Body */}
          <div className="mt-6 flex flex-col gap-3 text-body-lg text-on-surface leading-[1.8]">
            <p>
              暮色从北岭深处涌下来，像墨汁渗入宣纸，把村口的石桥染成一道深沉的剪影。陈平安站在桥头，肩上的青布包比往日重了几分——他今天替刘羡阳挨了一记闷棍，右臂隐隐作痛。
            </p>
            <p>
              "你怕了？"他低声问自己。
              <span className="bg-primary-fixed px-1 rounded text-primary-container font-semibold cursor-pointer hover:bg-primary-fixed-dim">
                怎么会。
              </span>
            </p>
            <p>
              远处的灯火次第亮起来，
              <span className="bg-yellow-100/60 px-1 rounded cursor-pointer">
                像是有人在替他点亮回家的路
              </span>
              ，可他此刻心里清楚，这条路通向的，未必是他想去的方向。
            </p>
            <p className="text-headline-md font-semibold text-on-surface mt-3">一</p>
            <p>来客是个女子。</p>
            <p>
              她骑着一头通体雪白的驴子，自村北小路缓缓行来，身上披着一件不合季节的青灰色道袍，腰间悬着一柄无鞘短剑。她的目光在他身上停了片刻，似乎在确认什么，又似乎只是在打量。
            </p>
            <p>"你叫陈平安？"</p>
            <p>他没有立刻回答。手心微微出汗。</p>
          </div>

          {/* AI suggestion inline */}
          <div className="mt-4 p-4 rounded-lg bg-primary-fixed/40 border-l-4 border-primary flex items-start gap-3">
            <Sparkles size={18} className="text-primary" />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-label-md text-on-surface font-semibold">Writer Agent 建议续写</span>
                <span className="font-code-sm text-on-surface-variant">
                  从 <em>"他没有立刻回答"</em> 开始 · 节奏：慢热
                </span>
              </div>
              <p className="text-body-sm text-on-surface mt-1">
                女子见他不语，翻身下驴，从袖中取出一封泛黄的信笺：
              </p>
              <div className="mt-2 flex gap-2">
                <button className="px-3 py-1.5 rounded bg-primary text-white text-label-md">接受</button>
                <button className="px-3 py-1.5 rounded bg-surface-container-lowest text-on-surface text-label-md">改写</button>
                <button className="px-3 py-1.5 rounded text-on-surface-variant text-label-md hover:underline">拒绝</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Right Co-pilot panel (460px) */}
      <aside className="w-[460px] flex-shrink-0 h-full bg-surface-container-lowest border-l border-outline-variant/30 overflow-y-auto">
        <div className="px-6 py-3 border-b border-outline-variant/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot size={20} className="text-primary" />
            <span className="text-label-lg font-semibold text-on-surface">协作 Co-pilot</span>
          </div>
          <span className="chip-tertiary">READY</span>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 px-4 py-2 border-b border-outline-variant/30">
          {TABS.map((t, i) => (
            <button
              key={t}
              onClick={() => setActiveTab(i)}
              className={`px-3 py-1.5 rounded text-label-md ${
                activeTab === i
                  ? 'bg-primary-container text-on-primary-container font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Cards */}
        <div className="p-4 flex flex-col gap-4">
          {/* Beat */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-primary">节拍</span>
              <span className="font-code-sm text-outline">第 11 章 · 段 5</span>
            </div>
            <p className="text-body-md text-on-surface">
              本章核心节拍：<strong>陌生人出现 + 主角审视</strong>
            </p>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 h-1.5 rounded-full bg-surface-container-high">
                <div className="h-full w-3/4 rounded-full bg-primary" />
              </div>
              <span className="font-code-sm text-primary font-semibold">75%</span>
            </div>
          </div>

          {/* Character voice */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-tertiary">角色声音</span>
              <span className="font-code-sm text-outline">3 / 5</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-bold">
                陈
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-label-md text-on-surface">陈平安</span>
                  <span className="font-code-sm text-tertiary">92% 一致</span>
                </div>
                <div className="h-1 mt-1 rounded-full bg-surface-container-high">
                  <div className="h-full w-11/12 rounded-full bg-tertiary" />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-fixed-variant flex items-center justify-center font-bold">
                女
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-label-md text-on-surface">来客 (未命名)</span>
                  <span className="font-code-sm text-outline">尚未建立档案</span>
                </div>
                <button className="text-primary font-code-sm hover:underline">+ 创建档案</button>
              </div>
            </div>
          </div>

          {/* Critic score */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-secondary">质检</span>
              <span className="font-code-sm text-outline">总分 8.4 / 10</span>
            </div>
            <div className="grid grid-cols-4 gap-2 mt-1">
              {[
                { v: '9.1', l: '节奏' },
                { v: '8.6', l: '对话' },
                { v: '8.0', l: '描写' },
                { v: '7.9', l: '钩子' },
              ].map((m) => (
                <div key={m.l} className="flex flex-col items-center p-2 rounded bg-surface-container-lowest">
                  <span className="text-headline-sm font-bold text-primary">{m.v}</span>
                  <span className="font-code-sm text-outline">{m.l}</span>
                </div>
              ))}
            </div>
          </div>

          {/* World bible check */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-tertiary">一致性 ✓</span>
              <span className="font-code-sm text-outline">3 项检查</span>
            </div>
            <ul className="flex flex-col gap-1 mt-1">
              <li className="flex items-center gap-2 text-body-sm">
                <CheckCircle2 size={16} className="text-tertiary" />
                <span className="text-on-surface">"剑来" 招式名 → 功法卷轴存在</span>
              </li>
              <li className="flex items-center gap-2 text-body-sm">
                <CheckCircle2 size={16} className="text-tertiary" />
                <span className="text-on-surface">陈平安右臂旧伤 → 第 8 章已埋伏笔</span>
              </li>
              <li className="flex items-center gap-2 text-body-sm">
                <AlertTriangle size={16} className="text-error" />
                <span className="text-on-surface">来客道袍颜色与第 4 章描述不一致</span>
              </li>
            </ul>
          </div>

          {/* Foreshadowing */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-primary">伏笔</span>
              <span className="font-code-sm text-outline">2 项建议</span>
            </div>
            <div className="p-2 rounded bg-surface-container-lowest">
              <p className="text-body-sm text-on-surface">
                "白驴" → 暂无关联，可在后续卷中关联「骊珠洞天·灵兽」
              </p>
              <button className="text-primary font-code-sm hover:underline mt-1">+ 加入伏笔簿</button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
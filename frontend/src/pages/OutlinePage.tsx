import { useState } from 'react';
import {
  Plus,
  ChevronDown,
  ChevronRight,
  Edit,
  ArrowRight,
  Sparkles,
  Network,
  FileText,
  Flag,
} from 'lucide-react';

interface OutlineNode {
  id: string;
  type: 'volume' | 'chapter' | 'beat';
  title: string;
  meta?: string;
  status?: 'done' | 'writing' | 'draft';
  children?: OutlineNode[];
}

const TREE: OutlineNode[] = [
  {
    id: 'v1',
    type: 'volume',
    title: '第一卷 · 少年游',
    meta: '12 章 · 8.2 万字 · 完结',
    status: 'done',
    children: [
      {
        id: 'v1c1',
        type: 'chapter',
        title: '第 1 章 洞天风云',
        meta: '2,400 字 · 完结',
        status: 'done',
        children: [
          { id: 'v1c1b1', type: 'beat', title: '楔子 · 骊珠洞天', meta: '—' },
          { id: 'v1c1b2', type: 'beat', title: '陈平安出场',      meta: '—' },
        ],
      },
      {
        id: 'v1c11',
        type: 'chapter',
        title: '第 11 章 意外来客',
        meta: '3,247 字 · 创作中',
        status: 'writing',
      },
      {
        id: 'v1c12',
        type: 'chapter',
        title: '第 12 章 山雨欲来',
        meta: '2,800 字 · 待写',
        status: 'draft',
      },
    ],
  },
  {
    id: 'v2',
    type: 'volume',
    title: '第二卷 · 江湖路',
    meta: '38 章 · 12.4 万字 · 完结',
    status: 'done',
    children: [],
  },
  {
    id: 'v3',
    type: 'volume',
    title: '第三卷 · 风波起',
    meta: '36 章 · 写作中',
    status: 'writing',
    children: [],
  },
];

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  done:    { label: '完结',   cls: 'chip-tertiary' },
  writing: { label: '写作中', cls: 'chip-primary' },
  draft:   { label: '待写',   cls: 'chip-secondary' },
};

export default function OutlinePage() {
  const [selectedId, setSelectedId] = useState('v1c11');

  return (
    <div className="flex w-full h-full">
      {/* Tree (left) */}
      <aside className="w-[400px] flex-shrink-0 h-full bg-surface-container-lowest border-r border-outline-variant/30 overflow-y-auto flex flex-col">
        <div className="px-6 py-4 border-b border-outline-variant/30 flex items-center justify-between">
          <h3 className="text-headline-sm font-semibold text-on-surface">大纲架构</h3>
          <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary text-white text-label-md">
            <Plus size={16} /> 新建节点
          </button>
        </div>
        <div className="p-4 flex flex-col gap-1">
          {TREE.map((node) => (
            <TreeNode
              key={node.id}
              node={node}
              depth={0}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          ))}
        </div>
      </aside>

      {/* Detail (right) */}
      <section className="flex-1 h-full overflow-y-auto bg-surface-container-low">
        <div className="max-w-[960px] mx-auto px-8 py-8 flex flex-col gap-6">
          <div className="flex items-end justify-between">
            <div className="flex flex-col gap-1">
              <span className="text-label-md text-on-surface-variant">第一卷 · 少年游 / 第 11 章</span>
              <h1 className="text-display font-bold text-on-surface">意外来客</h1>
              <div className="flex items-center gap-2 mt-2">
                <span className="chip-primary">写作中</span>
                <span className="font-code-sm text-on-surface-variant">3,247 / 3,500 字</span>
                <span className="font-code-sm text-outline">v3 · 上次编辑 2 小时前</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="flex items-center gap-1 px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant/50 text-on-surface text-label-md hover:bg-surface-container-high">
                <Edit size={16} /> 编辑
              </button>
              <button className="flex items-center gap-1 px-3 py-2 rounded-lg bg-primary text-white text-label-md hover:bg-primary-hover">
                <Sparkles size={16} /> AI 续写
                <ArrowRight size={16} />
              </button>
            </div>
          </div>

          {/* Summary */}
          <div className="surface-card p-6 flex flex-col gap-3">
            <h2 className="text-headline-sm font-semibold text-on-surface pb-2 border-b border-outline-variant/40">
              本章摘要
            </h2>
            <p className="text-body-md text-on-surface">
              陈平安在村口石桥偶遇一位骑白驴的女子。对方以一封泛黄信笺试探他的身份。
              几番对话后，陈平安隐隐感觉自己与这封信背后的人物有着宿命的联系，但他尚不知来客的真实目的。
            </p>
            <div className="flex flex-wrap gap-1 mt-2">
              <span className="chip-tertiary">陌生人</span>
              <span className="chip-tertiary">试探</span>
              <span className="chip-tertiary">信笺</span>
              <span className="chip-secondary">埋伏笔</span>
            </div>
          </div>

          {/* Beats */}
          <div className="surface-card p-6 flex flex-col gap-3">
            <h2 className="text-headline-sm font-semibold text-on-surface pb-2 border-b border-outline-variant/40">
              节拍（4 / 5）
            </h2>
            {[
              { title: '桥头独白', done: true, pct: 100 },
              { title: '白驴出现', done: true, pct: 100 },
              { title: '道袍女子问名', done: true, pct: 100 },
              { title: '陈平安审视来客', done: true, pct: 100 },
              { title: '信笺悬念', done: false, pct: 30 },
            ].map((b, i) => (
              <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface-container-low">
                <span className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-body-sm ${b.done ? 'bg-tertiary text-white' : 'bg-outline text-white'}`}>
                  {i + 1}
                </span>
                <span className="flex-1 text-body-md text-on-surface">{b.title}</span>
                <div className="flex-1 h-1.5 rounded-full bg-surface-container-highest">
                  <div className={`h-full rounded-full ${b.done ? 'bg-tertiary' : 'bg-primary'}`} style={{ width: `${b.pct}%` }} />
                </div>
                <span className="font-code-sm text-on-surface-variant w-12 text-right">{b.pct}%</span>
              </div>
            ))}
          </div>

          {/* Linked entities */}
          <div className="grid grid-cols-2 gap-4">
            <div className="surface-card p-6 flex flex-col gap-2">
              <h2 className="text-headline-sm font-semibold text-on-surface pb-2 border-b border-outline-variant/40">
                涉及角色
              </h2>
              <Row label="陈平安" meta="主角 · 首次出现" />
              <Row label="来客 (未命名)" meta="新角色 · 待建档" />
            </div>
            <div className="surface-card p-6 flex flex-col gap-2">
              <h2 className="text-headline-sm font-semibold text-on-surface pb-2 border-b border-outline-variant/40">
                涉及地点
              </h2>
              <Row label="村口石桥" meta="首次出现 · 重要场景" />
              <Row label="骊珠洞天" meta="背景 · 暗示" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function Row({ label, meta }: { label: string; meta: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-body-md text-on-surface">{label}</span>
      <span className="font-code-sm text-on-surface-variant">{meta}</span>
    </div>
  );
}

function TreeNode({
  node, depth, selectedId, onSelect,
}: {
  node: OutlineNode;
  depth: number;
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const isSelected = node.id === selectedId;
  const status = node.status ? STATUS_BADGE[node.status] : undefined;
  const indent = depth * 24;

  return (
    <div>
      <button
        onClick={() => {
          setOpen(!open);
          onSelect(node.id);
        }}
        className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-body-sm ${
          isSelected
            ? 'bg-primary-container text-on-primary-container font-semibold'
            : 'text-on-surface hover:bg-surface-container'
        }`}
        style={{ paddingLeft: 8 + indent }}
      >
        {node.children && node.children.length > 0 ? (
          open ? (
            <ChevronDown size={16} className="text-outline" />
          ) : (
            <ChevronRight size={16} className="text-outline" />
          )
        ) : (
          <span className="w-4" />
        )}
        {node.type === 'volume' ? (
          <Network size={16} className="text-outline" />
        ) : node.type === 'chapter' ? (
          <FileText size={16} className="text-outline" />
        ) : (
          <Flag size={16} className="text-outline" />
        )}
        <span className="flex-1 text-left">{node.title}</span>
        {status ? (
          <span className={status.cls}>{status.label}</span>
        ) : (
          <span className="font-code-sm text-outline">{node.meta}</span>
        )}
      </button>
      {open && node.children && (
        <div className="flex flex-col gap-0.5">
          {node.children.map((c) => (
            <TreeNode
              key={c.id}
              node={c}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
import { useState } from 'react';
import {
  Plus,
  Search,
  ChevronDown,
  ChevronRight,
  Globe,
  Layers,
  Sword,
  Flame,
  School,
  CheckCircle2,
} from 'lucide-react';

const SECTIONS = [
  {
    key: 'geography',
    label: '地理',
    icon: Globe,
    items: [
      { id: 'g1', name: '骊珠洞天',   meta: '大陆 / 起点',     consistency: 96 },
      { id: 'g2', name: '落魄山',     meta: '山门 / 修炼地',   consistency: 92 },
      { id: 'g3', name: '剑气长城',   meta: '关隘 / 中期',     consistency: 88 },
    ],
  },
  {
    key: 'cultivation',
    label: '修炼体系',
    icon: Sword,
    items: [
      { id: 'c1', name: '练气',       meta: '入门 · 9 层',     consistency: 99 },
      { id: 'c2', name: '筑基',       meta: '关隘',            consistency: 97 },
      { id: 'c3', name: '金丹',       meta: '关隘',            consistency: 95 },
      { id: 'c4', name: '元婴',       meta: '关隘',            consistency: 90 },
      { id: 'c5', name: '飞升',       meta: '终境',            consistency: 82 },
    ],
  },
  {
    key: 'history',
    label: '历史大事',
    icon: Flame,
    items: [
      { id: 'h1', name: '万年之约',   meta: '约公元前 10000 年', consistency: 94 },
      { id: 'h2', name: '骊珠降世',   meta: '约公元前 8000 年',  consistency: 91 },
    ],
  },
  {
    key: 'factions',
    label: '门派势力',
    icon: School,
    items: [
      { id: 'f1', name: '落魄山',     meta: '主角所属',         consistency: 95 },
      { id: 'f2', name: '剑气长城',   meta: '盟友',             consistency: 89 },
      { id: 'f3', name: '蛮荒天下',   meta: '敌对',             consistency: 87 },
    ],
  },
];

const TOTAL = SECTIONS.reduce((s, sec) => s + sec.items.length, 0);

export default function WorldBiblePage() {
  const [open, setOpen] = useState<Record<string, boolean>>({
    geography: true,
    cultivation: true,
    history: false,
    factions: false,
  });

  return (
    <div className="w-full h-full overflow-y-auto bg-surface-container-low">
      <div className="p-8 flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="text-display font-bold text-on-surface">世界观圣经</h1>
            <p className="text-body-md text-on-surface-variant">
              {TOTAL} 条目 · 4 个一级分类 · 一致性平均 92% · 末次审计 2 天前
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center px-3 h-9 rounded-lg border border-outline-variant/50 bg-surface-container-lowest w-72">
              <Search size={18} className="text-outline" />
              <input placeholder="搜索地点 / 体系 / 势力..." className="flex-1 outline-none ml-2 bg-transparent text-body-md" />
            </div>
            <button className="flex items-center gap-1 px-3 py-2 rounded-lg bg-primary text-white text-label-md font-medium">
              <Plus size={16} /> 新建条目
            </button>
          </div>
        </div>

        {/* Summary tiles */}
        <section className="grid grid-cols-4 gap-4">
          <StatTile icon={Globe} label="地理" value="3" sub="6 大陆 11 秘境" />
          <StatTile icon={Sword} label="修炼体系" value="5" sub="练气 → 飞升" />
          <StatTile icon={Flame} label="历史大事" value="2" sub="万年纪年" />
          <StatTile icon={School} label="门派势力" value="3" sub="盟友 / 敌对" />
        </section>

        {/* Main panels */}
        <div className="grid grid-cols-2 gap-4">
          {SECTIONS.map((sec) => (
            <div key={sec.key} className="surface-card p-6 flex flex-col gap-3">
              <button
                onClick={() => setOpen({ ...open, [sec.key]: !open[sec.key] })}
                className="flex items-center justify-between pb-3 border-b border-outline-variant/40"
              >
                <div className="flex items-center gap-2">
                  <sec.icon size={20} className="text-primary" />
                  <h2 className="text-headline-sm font-semibold text-on-surface">
                    {sec.label}
                  </h2>
                  <span className="chip-primary">{sec.items.length}</span>
                </div>
                {open[sec.key] ? (
                  <ChevronDown size={18} className="text-outline" />
                ) : (
                  <ChevronRight size={18} className="text-outline" />
                )}
              </button>

              {open[sec.key] && (
                <div className="flex flex-col gap-2">
                  {sec.items.map((it) => (
                    <div key={it.id} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface-container-lowest cursor-pointer">
                      <div className="w-8 h-8 rounded-lg bg-primary-container flex items-center justify-center">
                        <sec.icon size={18} className="text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-label-md text-on-surface font-semibold">{it.name}</span>
                          {it.consistency >= 95 && (
                            <CheckCircle2 size={14} className="text-tertiary" />
                          )}
                        </div>
                        <span className="font-code-sm text-on-surface-variant">{it.meta}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-1.5 rounded-full bg-surface-container-high">
                          <div
                            className={`h-full rounded-full ${
                              it.consistency >= 95
                                ? 'bg-tertiary'
                                : it.consistency >= 90
                                  ? 'bg-primary'
                                  : 'bg-outline'
                            }`}
                            style={{ width: `${it.consistency}%` }}
                          />
                        </div>
                        <span className="font-code-sm text-on-surface-variant w-10 text-right">
                          {it.consistency}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Recent edits */}
        <div className="surface-card p-6 flex flex-col gap-3">
          <h2 className="text-headline-sm font-semibold text-on-surface pb-2 border-b border-outline-variant/40">
            最近编辑
          </h2>
          <div className="grid grid-cols-3 gap-4">
            {[
              { name: '骊珠洞天', type: '地理', ago: '2 小时前' },
              { name: '元婴',     type: '修炼体系', ago: '昨天' },
              { name: '落魄山',   type: '门派', ago: '3 天前' },
            ].map((it, i) => (
              <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface-container-low">
                <div className="w-8 h-8 rounded-lg bg-secondary-container flex items-center justify-center">
                  <Layers size={18} className="text-on-secondary-fixed-variant" />
                </div>
                <div className="flex-1">
                  <div className="text-label-md text-on-surface font-semibold">{it.name}</div>
                  <span className="font-code-sm text-on-surface-variant">{it.type} · {it.ago}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatTile({
  icon: Icon, label, value, sub,
}: {
  icon: typeof Globe;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="surface-card p-4 flex items-center gap-3">
      <div className="w-10 h-10 rounded-lg bg-primary-container flex items-center justify-center">
        <Icon size={22} className="text-primary" />
      </div>
      <div className="flex flex-col">
        <span className="text-label-sm text-outline uppercase">{label}</span>
        <span className="text-headline-sm font-bold text-on-surface">{value}</span>
        <span className="font-code-sm text-on-surface-variant">{sub}</span>
      </div>
    </div>
  );
}
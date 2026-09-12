import { useState } from 'react';
import {
  Plus,
  Search,
  MoreHorizontal,
  Edit,
  Sparkles,
  Star,
  StarOff,
  Users,
} from 'lucide-react';

interface Character {
  id: string;
  name: string;
  role: 'protagonist' | 'supporting' | 'antagonist';
  avatar?: string;
  personality: string[];
  status: string;
  appearances: number;
  starred?: boolean;
}

const CHARACTERS: Character[] = [
  {
    id: 'c1', name: '陈平安', role: 'protagonist',
    personality: ['坚韧', '隐忍', '重情'],
    status: '活跃', appearances: 142, starred: true,
  },
  {
    id: 'c2', name: '宁姚', role: 'supporting',
    personality: ['果断', '聪慧', '傲骨'],
    status: '活跃', appearances: 87,
  },
  {
    id: 'c3', name: '齐静春', role: 'supporting',
    personality: ['温和', '深邃', '悲悯'],
    status: '活跃', appearances: 54,
  },
  {
    id: 'c4', name: '阮邛', role: 'supporting',
    personality: ['豪爽', '执着', '孤傲'],
    status: '活跃', appearances: 41,
  },
  {
    id: 'c5', name: '顾粼', role: 'antagonist',
    personality: ['阴鸷', '多疑', '贪婪'],
    status: '潜伏', appearances: 18,
  },
];

const ROLE_BADGE: Record<Character['role'], { label: string; cls: string }> = {
  protagonist: { label: '主角', cls: 'chip-primary' },
  supporting:  { label: '配角', cls: 'chip-tertiary' },
  antagonist: { label: '反派', cls: 'chip-secondary' },
};

export default function CharactersPage() {
  const [filter, setFilter] = useState<'all' | Character['role']>('all');
  const filtered = CHARACTERS.filter((c) => filter === 'all' || c.role === filter);

  return (
    <div className="w-full h-full overflow-y-auto bg-surface-container-low">
      <div className="p-8 flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="text-display font-bold text-on-surface">角色档案</h1>
            <p className="text-body-md text-on-surface-variant">
              5 主角 · 33 配角 · 共 38 个角色 · 最近编辑 1 小时前
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center px-3 h-9 rounded-lg border border-outline-variant/50 bg-surface-container-lowest w-72">
              <Search size={18} className="text-outline" />
              <input
                placeholder="搜索角色..."
                className="flex-1 outline-none ml-2 bg-transparent text-body-md"
              />
            </div>
            <button className="flex items-center gap-1 px-3 py-2 rounded-lg bg-primary text-white text-label-md font-medium">
              <Plus size={16} /> 新建角色
            </button>
          </div>
        </div>

        {/* Filter chips */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-full text-label-md ${
              filter === 'all'
                ? 'bg-primary-container text-on-primary-container font-semibold'
                : 'bg-surface-container text-on-surface-variant border border-outline-variant/40'
            }`}
          >
            全部 <span className="font-code-sm ml-1">{CHARACTERS.length}</span>
          </button>
          <button
            onClick={() => setFilter('protagonist')}
            className={`px-3 py-1.5 rounded-full text-label-md ${
              filter === 'protagonist'
                ? 'bg-primary-container text-on-primary-container font-semibold'
                : 'bg-surface-container text-on-surface-variant border border-outline-variant/40'
            }`}
          >
            主角 <span className="font-code-sm ml-1">1</span>
          </button>
          <button
            onClick={() => setFilter('supporting')}
            className={`px-3 py-1.5 rounded-full text-label-md ${
              filter === 'supporting'
                ? 'bg-primary-container text-on-primary-container font-semibold'
                : 'bg-surface-container text-on-surface-variant border border-outline-variant/40'
            }`}
          >
            配角 <span className="font-code-sm ml-1">3</span>
          </button>
          <button
            onClick={() => setFilter('antagonist')}
            className={`px-3 py-1.5 rounded-full text-label-md ${
              filter === 'antagonist'
                ? 'bg-primary-container text-on-primary-container font-semibold'
                : 'bg-surface-container text-on-surface-variant border border-outline-variant/40'
            }`}
          >
            反派 <span className="font-code-sm ml-1">1</span>
          </button>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-3 gap-4">
          {filtered.map((c) => (
            <CharacterCard key={c.id} character={c} />
          ))}
        </div>
      </div>
    </div>
  );
}

function CharacterCard({ character: c }: { character: Character }) {
  const role = ROLE_BADGE[c.role];
  return (
    <div className="surface-card p-6 flex flex-col gap-3 hover:border-primary-container cursor-pointer transition-colors">
      <div className="flex items-start gap-3">
        <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary to-[#7A7DEF] flex items-center justify-center text-white text-headline-sm font-bold">
          {c.name[0]}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-headline-sm font-semibold text-on-surface">{c.name}</h3>
            {c.starred ? (
              <Star size={16} className="text-primary" fill="currentColor" />
            ) : (
              <StarOff size={16} className="text-outline" />
            )}
          </div>
          <div className="flex items-center gap-1 mt-1">
            <span className={role.cls}>{role.label}</span>
            <span className="font-code-sm text-on-surface-variant">{c.status}</span>
          </div>
        </div>
        <button className="text-outline hover:text-primary"><MoreHorizontal size={20} /></button>
      </div>

      {/* Personality */}
      <div className="flex flex-wrap gap-1">
        {c.personality.map((t) => (
          <span key={t} className="chip-tertiary">{t}</span>
        ))}
      </div>

      {/* Stats */}
      <div className="flex items-center justify-between pt-3 border-t border-outline-variant/30">
        <div className="flex items-center gap-1">
          <Users size={14} className="text-outline" />
          <span className="font-code-sm text-on-surface-variant">
            出现 {c.appearances} 章
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button className="text-outline hover:text-primary"><Edit size={18} /></button>
          <button className="text-outline hover:text-primary"><Sparkles size={18} /></button>
        </div>
      </div>
    </div>
  );
}
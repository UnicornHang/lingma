import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Empty, Spin, App, Button, Space } from 'antd';
import {
  Plus,
  LayoutGrid,
  List as ListIcon,
  Star,
  StarOff,
  Filter,
  ChevronDown,
  BookOpen,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { worksApi, type Work, type Paginated, type WorkStatus } from '@/api/works';
import { checkHealth } from '@/api/client';
import { useCurrentWorkStore } from '@/stores/useCurrentWorkStore';
import { formatRelativeTime, formatWordCount } from '@/utils/format';

const GENRE_LABEL: Record<string, { label: string; chipClass: string }> = {
  fantasy:    { label: '玄幻', chipClass: 'chip-tertiary' },
  urban:      { label: '都市', chipClass: 'chip-tertiary' },
  romance:    { label: '言情', chipClass: 'chip-tertiary' },
  historical: { label: '历史', chipClass: 'chip-tertiary' },
  sci_fi:     { label: '科幻', chipClass: 'chip-tertiary' },
  mystery:    { label: '悬疑', chipClass: 'chip-tertiary' },
  other:      { label: '其他', chipClass: 'chip-secondary' },
};

const STATUS_CHIP: Record<string, { label: string; cls: string }> = {
  draft:    { label: '草稿',   cls: 'chip-secondary' },
  writing:  { label: '连载中', cls: 'chip-tertiary' },
  finished: { label: '已完结', cls: 'chip-secondary' },
  archived: { label: '已归档', cls: 'chip-secondary' },
};

const STATUS_GRADIENT: Record<string, string> = {
  writing:  'from-[#047857] via-[#0d9488] to-[#14b8a6]',
  finished: 'from-[#f59e0b] via-[#fbbf24] to-[#fde68a]',
  draft:    'from-[#94a3b8] via-[#cbd5e1] to-[#e2e8f0]',
  archived: 'from-[#b91c1c] via-[#dc2626] to-[#f87171]',
};

function WorkCard({ work, isCurrent }: { work: Work; isCurrent: boolean }) {
  const genre = GENRE_LABEL[work.genre] || GENRE_LABEL.other;
  const status = STATUS_CHIP[work.status] || STATUS_CHIP.draft;
  const gradient = STATUS_GRADIENT[work.status] || STATUS_GRADIENT.draft;

  return (
    <Link
      to={`/works/${work.id}`}
      className={`surface-card overflow-hidden flex flex-col cursor-pointer transition-all ${
        isCurrent ? 'shadow-L2-popover' : ''
      }`}
    >
      <div className={`relative h-32 bg-gradient-to-br ${gradient}`}>
        <div className="absolute top-3 right-3">
          <span className="px-2 py-0.5 rounded-full bg-white/90 text-on-surface text-label-sm font-medium backdrop-blur-sm">
            {status.label}
          </span>
        </div>
        <div className="absolute top-3 left-3">
          <BookOpen size={28} className="text-white/90" />
        </div>
        {isCurrent && (
          <div className="absolute bottom-3 left-3">
            <span className="px-2 py-0.5 rounded bg-white text-primary text-label-sm font-semibold">
              当前
            </span>
          </div>
        )}
      </div>

      <div className="p-4 flex-1 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-headline-sm font-semibold text-on-surface flex-1 truncate">
            {work.title}
          </h3>
          {isCurrent ? (
            <Star size={18} className="text-primary" fill="currentColor" />
          ) : (
            <StarOff size={18} className="text-outline" />
          )}
        </div>
        <p className="text-body-sm text-on-surface-variant text-ellipsis-2">
          {work.logline || '（暂无简介）'}
        </p>
        <div className="flex items-center gap-1 mt-1">
          <span className={genre.chipClass}>{genre.label}</span>
        </div>
        <div className="mt-auto pt-3 border-t border-outline-variant/30 flex items-center justify-between font-code-sm text-on-surface-variant">
          <span>
            {formatWordCount(work.word_count)} / {formatWordCount(work.target_word_count)}
          </span>
          <span>{formatRelativeTime(work.updated_at)}</span>
        </div>
      </div>
    </Link>
  );
}

export default function WorksListPage() {
  const { message } = App.useApp();
  const currentWorkId = useCurrentWorkStore((s) => s.currentWorkId);
  const [statusFilter, setStatusFilter] = useState<WorkStatus | 'all'>('all');
  const { data, isLoading, error } = useQuery({
    queryKey: ['works'],
    queryFn: () => worksApi.list({ page: 1, page_size: 50 }),
  });

  useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      try {
        const result = await checkHealth() as unknown as { status: string; version: string; environment: string; database: string };
        message.success(`后端连接正常 (${result.environment})`);
        return result;
      } catch {
        message.error('后端连接失败');
        throw new Error('health check failed');
      }
    },
    enabled: false,
  });

  const works = (data as Paginated<Work> | undefined)?.items || [];
  const totalWords = useMemo(
    () => works.reduce((sum, w) => sum + (w.word_count || 0), 0),
    [works],
  );
  const counts = useMemo(() => ({
    all: works.length,
    writing: works.filter((w) => w.status === 'writing').length,
    finished: works.filter((w) => w.status === 'finished').length,
    draft: works.filter((w) => w.status === 'draft').length,
  }), [works]);
  const visible = statusFilter === 'all' ? works : works.filter((w) => w.status === statusFilter);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center text-error">
        加载失败：{(error as Error).message}
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full h-full">
      <div className="flex items-end justify-between px-8 pt-8 pb-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-display font-bold text-on-surface">作品库</h1>
          <p className="text-body-md text-on-surface-variant">
            {works.length} 部作品 · 总计 {formatWordCount(totalWords)}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Space.Compact>
            <Button type="default" icon={<LayoutGrid size={16} />}>网格</Button>
            <Button type="text" icon={<ListIcon size={16} />}>列表</Button>
          </Space.Compact>
          <Link to="/works/new">
            <Button type="primary" icon={<Plus size={16} />}>
              新建作品
            </Button>
          </Link>
        </div>
      </div>

      <div className="flex items-center justify-between px-8 pb-4">
        <div className="flex items-center gap-2">
          {([
            ['all', '全部', counts.all],
            ['writing', '连载中', counts.writing],
            ['finished', '已完结', counts.finished],
            ['draft', '草稿', counts.draft],
          ] as const).map(([key, label, count]) => (
            <Button
              key={key}
              type={statusFilter === key ? 'primary' : 'default'}
              shape="round"
              onClick={() => setStatusFilter(key)}
            >
              {label} <span className="font-code-sm ml-1">{count}</span>
            </Button>
          ))}
        </div>
        <Button type="text">
          <Filter size={18} />
          <span className="ml-2">排序：最近编辑</span>
          <ChevronDown size={18} className="ml-2" />
        </Button>
      </div>

      {works.length === 0 ? (
        <div className="flex-1 flex items-center justify-center px-8 pb-16">
          <Empty description="还没有作品，从向导创建第一部吧">
            <Link to="/works/new">
              <Button type="primary" icon={<Plus size={16} />}>新建作品</Button>
            </Link>
          </Empty>
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4 px-8 pb-8">
          {visible.map((w) => (
            <WorkCard key={w.id} work={w} isCurrent={w.id === currentWorkId} />
          ))}
          <Link
            to="/works/new"
            className="rounded-xl border-2 border-dashed border-outline-variant/60 hover:border-primary hover:bg-primary-fixed/30 flex flex-col items-center justify-center gap-3 min-h-[320px] cursor-pointer transition-colors"
          >
            <Plus size={48} className="text-outline" />
            <span className="text-label-lg text-on-surface">新建作品</span>
            <span className="text-body-sm text-on-surface-variant">打开新建向导</span>
          </Link>
        </div>
      )}
    </div>
  );
}

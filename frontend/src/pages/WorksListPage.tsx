import { useQuery } from '@tanstack/react-query';
import { Empty, Spin, App, Button } from 'antd';
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

import { worksApi, type Work, type Paginated } from '@/api/works';
import { checkHealth } from '@/api/client';

const GENRE_LABEL: Record<string, { label: string; chipClass: string }> = {
  fantasy:    { label: '玄幻', chipClass: 'chip-tertiary' },
  urban:      { label: '都市', chipClass: 'chip-tertiary' },
  romance:    { label: '言情', chipClass: 'chip-tertiary' },
  historical: { label: '历史', chipClass: 'chip-tertiary' },
  sci_fi:     { label: '科幻', chipClass: 'chip-tertiary' },
  mystery:    { label: '悬疑', chipClass: 'chip-tertiary' },
  other:      { label: '其他', chipClass: 'chip-secondary' },
};

const STATUS_CHIP: Record<string, { label: string; cls: string; icon?: React.ReactNode }> = {
  draft:    { label: '草稿',   cls: 'chip-secondary' },
  writing:  { label: '连载中', cls: 'chip-tertiary' },
  finished: { label: '已完结', cls: 'chip-secondary' },
  archived: { label: '已归档', cls: 'chip-secondary' },
};

const STATUS_GRADIENT: Record<string, string> = {
  writing:  'from-[#14b8a6] to-[#10b981]',     // Teal → Emerald (light)
  finished: 'from-[#34d399] to-[#059669]',     // Bright emerald → deep emerald
  draft:    'from-[#94a3b8] to-[#475569]',     // Slate gradient
  archived: 'from-[#38bdf8] to-[#0369a1]',     // Sky blue (archived = secondary status)
};

function WorkCard({ work }: { work: Work }) {
  const genre = GENRE_LABEL[work.genre] || GENRE_LABEL.other;
  const status = STATUS_CHIP[work.status] || STATUS_CHIP.draft;
  const isCurrent = work.title === '剑来·前传';
  const gradient = STATUS_GRADIENT[work.status] || STATUS_GRADIENT.draft;
  const wordWan = (work.word_count / 10000).toFixed(1);
  const targetWan = (work.target_word_count / 10000).toFixed(0);

  return (
    <Link
      to={`/works/${work.id}`}
      className={`overflow-hidden flex flex-col ${
        isCurrent ? 'surface-card-active' : 'surface-card'
      } hover:border-primary-container transition-colors cursor-pointer`}
    >
      {/* Banner */}
      <div
        className={`relative h-32 bg-gradient-to-br ${gradient}`}
      >
        <div className="absolute top-3 right-3">
          <span className={status.cls}>{status.label}</span>
        </div>
        <div className="absolute top-3 left-3">
          <BookOpen size={28} className="text-white" />
        </div>
        {isCurrent && (
          <div className="absolute bottom-3 left-3">
            <span className="px-2 py-0.5 rounded bg-primary text-white text-label-sm font-semibold">
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
          讲述陈平安从骊珠洞天走出后的一段尘缘。他要修的不只是大道，更是人心……
        </p>
        <div className="flex items-center gap-1 mt-1">
          <span className={genre.chipClass}>{genre.label}</span>
        </div>
        <div className="mt-auto pt-3 border-t border-outline-variant/30 flex items-center justify-between font-code-sm text-on-surface-variant">
          <span>
            {wordWan} 万字 / {targetWan} 万字
          </span>
          <span>2 小时前</span>
        </div>
      </div>
    </Link>
  );
}

export default function WorksListPage() {
  const { message } = App.useApp();
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

  const works = (data as Paginated<Work> | undefined)?.items || [];
  // Demo: inject fake works so the grid is populated visually
  const demoWorks: Work[] =
    works.length === 0
      ? [
          {
            id: '1',
            title: '剑来·前传',
            genre: 'fantasy',
            status: 'writing',
            word_count: 352000,
            target_word_count: 1000000,
            logline: '讲述陈平安从骊珠洞天走出后的一段尘缘。',
            style_keywords: ['热血狂飙', '杀伐果断'],
            target_audience: ['男频'],
            settings: {},
            created_at: '',
            updated_at: '',
          },
          {
            id: '2',
            title: '深海回声',
            genre: 'sci_fi',
            status: 'writing',
            word_count: 287000,
            target_word_count: 600000,
            logline: '一群海洋生物学家发现深海中传出的不明信号。',
            style_keywords: ['严谨设定', '反转不断'],
            target_audience: ['不限'],
            settings: {},
            created_at: '',
            updated_at: '',
          },
          {
            id: '3',
            title: '长安夜未央',
            genre: 'historical',
            status: 'finished',
            word_count: 421000,
            target_word_count: 400000,
            logline: '盛唐之下，街市间的暗流与灯火交织。',
            style_keywords: ['史诗气魄', '群像推演'],
            target_audience: ['不限'],
            settings: {},
            created_at: '',
            updated_at: '',
          },
          {
            id: '4',
            title: '荒岛游戏',
            genre: 'mystery',
            status: 'writing',
            word_count: 184000,
            target_word_count: 500000,
            logline: '荒岛求生之中，真相在每个人手中翻牌。',
            style_keywords: ['智商在线', '反转不断'],
            target_audience: ['男频'],
            settings: {},
            created_at: '',
            updated_at: '',
          },
        ]
      : works;

  return (
    <div className="flex flex-col w-full h-full">
      {/* Header */}
      <div className="flex items-end justify-between px-8 pt-8 pb-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-display font-bold text-on-surface">作品库</h1>
          <p className="text-body-md text-on-surface-variant">
            {demoWorks.length} 部作品 · 总计 1,284,532 字 · 最近更新 2 小时前
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1 p-1 bg-surface-container-low rounded-lg">
            <button className="px-3 py-1.5 rounded bg-surface-container-lowest text-on-surface text-label-md shadow-sm flex items-center gap-1">
              <LayoutGrid size={16} />网格
            </button>
            <button className="px-3 py-1.5 rounded text-on-surface-variant text-label-md hover:bg-surface-container-highest flex items-center gap-1">
              <ListIcon size={16} />列表
            </button>
          </div>
          <Link to="/works/new">
            <Button type="primary" icon={<Plus size={16} />}>
              新建作品
            </Button>
          </Link>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center justify-between px-8 pb-4">
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 rounded-full bg-primary-container text-on-primary-container text-label-md font-semibold flex items-center gap-1">
            全部 <span className="font-code-sm">{demoWorks.length}</span>
          </button>
          <button className="px-3 py-1.5 rounded-full bg-surface-container text-on-surface-variant text-label-md border border-outline-variant/40">
            连载中 <span className="font-code-sm">3</span>
          </button>
          <button className="px-3 py-1.5 rounded-full bg-surface-container text-on-surface-variant text-label-md border border-outline-variant/40">
            已完结 <span className="font-code-sm">1</span>
          </button>
          <button className="px-3 py-1.5 rounded-full bg-surface-container text-on-surface-variant text-label-md border border-outline-variant/40">
            草稿 <span className="font-code-sm">1</span>
          </button>
          <button className="px-3 py-1.5 rounded-full bg-surface-container text-on-surface-variant text-label-md border border-outline-variant/40">
            <Star size={14} className="inline mr-1" />收藏
          </button>
        </div>
        <div className="flex items-center px-3 h-9 rounded-lg border border-outline-variant/50 bg-surface-container-lowest">
          <Filter size={18} className="text-outline" />
          <span className="ml-2 text-body-md text-on-surface-variant">
            排序：最近编辑
          </span>
          <ChevronDown size={18} className="ml-2 text-outline" />
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-4 gap-4 px-8 pb-8">
        {demoWorks.map((w) => (
          <WorkCard key={w.id} work={w} />
        ))}
        <Link
          to="/works/new"
          className="rounded-xl border-2 border-dashed border-outline-variant/60 hover:border-primary hover:bg-primary-fixed/30 flex flex-col items-center justify-center gap-3 min-h-[320px] cursor-pointer transition-colors"
        >
          <Plus size={48} className="text-outline" />
          <span className="text-label-lg text-on-surface">新建作品</span>
          <span className="text-body-sm text-on-surface-variant">从模板 / 向导 / 空白页</span>
        </Link>
      </div>

      {works.length === 0 && (
        <div className="px-8 pb-4">
          <div className="text-label-sm text-on-surface-low">
            <Empty
              description={
                <span className="text-body-md text-on-surface-variant">
                  未从后端拉取到作品 · 已显示演示数据
                </span>
              }
            />
          </div>
        </div>
      )}
    </div>
  );
}
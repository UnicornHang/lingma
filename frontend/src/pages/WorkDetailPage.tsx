import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Empty, Spin, App as AntApp } from 'antd';
import {
  BookOpen,
  FileText,
  Network,
  Users,
  MoreHorizontal,
  Clock,
  ArrowLeft,
} from 'lucide-react';

import { worksApi, chaptersApi, checkHealth, type Work, type Chapter } from '@/api';

interface ChapterSummary {
  id: string;
  title: string;
  status: string;
  word_count: number;
  updated_at: string;
}

export default function WorkDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { message } = AntApp.useApp();

  const workQuery = useQuery({
    queryKey: ['work', id],
    queryFn: () => worksApi.get(id!),
    enabled: !!id,
  });

  const chaptersQuery = useQuery({
    queryKey: ['work-chapters', id],
    queryFn: () => chaptersApi.listByWork(id!, { page: 1, page_size: 50 }),
    enabled: !!id,
  });

  // 健康检查副作用（首次进入时显示一次连接状态）
  useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      try {
        const j = await checkHealth();
        if (j?.status === 'ok') message.success(`后端连接正常 (${j.environment})`);
        else message.warning(`后端状态异常: ${j?.status}`);
        return j;
      } catch {
        message.error('后端连接失败');
        throw new Error('health check failed');
      }
    },
    enabled: !!id && !workQuery.isLoading,
    retry: false,
  });

  if (!id) {
    return (
      <div className="flex items-center justify-center h-full">
        <Empty description="缺少作品 ID" />
      </div>
    );
  }

  if (workQuery.isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spin size="large" />
      </div>
    );
  }

  if (workQuery.error) {
    return (
      <div className="p-8 text-center text-error">
        加载失败：{(workQuery.error as Error).message}
      </div>
    );
  }

  const work = workQuery.data!;
  const chapters: ChapterSummary[] = (chaptersQuery.data?.items ?? []).map((c: Chapter) => ({
    id: c.id,
    title: c.title,
    status: c.status,
    word_count: c.word_count,
    updated_at: c.updated_at,
  }));
  const totalWords = chapters.reduce((acc, c) => acc + c.word_count, 0);
  const targetWords = work.target_word_count;
  const progressPct = targetWords > 0 ? Math.min(100, Math.round((totalWords / targetWords) * 100)) : 0;
  const firstChapterId = chapters[0]?.id;

  return (
    <div className="w-full h-full overflow-y-auto bg-surface-container-low">
      <div className="p-8 flex flex-col gap-6">
        <Link
          to="/works"
          className="inline-flex items-center gap-1 text-on-surface-variant hover:text-on-surface text-label-md self-start"
        >
          <ArrowLeft size={16} /> 返回作品库
        </Link>

        {/* Hero */}
        <section className="p-8 rounded-2xl bg-gradient-to-br from-[#047857] via-[#065f46] to-[#064e3b] text-white shadow-L2-popover flex items-center gap-6">
          <div className="h-32 w-32 rounded-2xl bg-white/10 backdrop-blur flex items-center justify-center">
            <BookOpen size={64} className="text-white" strokeWidth={1.5} />
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="chip-tertiary">{STATUS_LABEL[work.status]}</span>
              <span className="px-2 py-0.5 rounded-full bg-white/20 text-white font-code-sm">
                {GENRE_LABEL[work.genre] ?? work.genre} · {work.target_audience.join(' · ') || '不限'}
              </span>
            </div>
            <h1 className="text-display font-bold text-white">{work.title}</h1>
            <p className="text-body-lg text-white/80 max-w-2xl">
              {work.logline || '（暂无简介）'}
            </p>
            <div className="flex items-center gap-4 mt-2">
              <Link
                to={firstChapterId ? `/editor/${firstChapterId}` : '/editor'}
                className={`flex items-center gap-2 px-6 py-3 bg-white text-primary rounded-lg text-label-md font-semibold hover:opacity-90 ${!firstChapterId ? 'pointer-events-none opacity-60' : ''}`}
              >
                <FileText size={20} />
                <span>打开编辑器</span>
              </Link>
              <Link
                to={`/works/${id}/outline`}
                className="flex items-center gap-2 px-6 py-3 bg-white/10 backdrop-blur text-white border border-white/30 rounded-lg text-label-md font-medium"
              >
                <Network size={20} />
                <span>查看大纲</span>
              </Link>
              <Link
                to={`/works/${id}/characters`}
                className="flex items-center gap-2 px-6 py-3 bg-white/10 backdrop-blur text-white border border-white/30 rounded-lg text-label-md font-medium"
              >
                <Users size={20} />
                <span>角色</span>
              </Link>
              <button className="ml-auto">
                <MoreHorizontal size={28} className="text-white" />
              </button>
            </div>
          </div>
        </section>

        {/* Stats row */}
        <section className="grid grid-cols-4 gap-4">
          <Stat label="总字数" value={totalWords.toLocaleString()} sub={`/ ${targetWords.toLocaleString()}`} />
          <Stat label="章节" value={String(chapters.length)} sub="已落库" />
          <Stat label="风格关键词" value={String(work.style_keywords.length)} sub={work.style_keywords.slice(0, 3).join(' · ') || '（未设置）'} />
          <Stat label="已完成度" value={`${progressPct}%`} isProgress progress={progressPct} />
        </section>

        {/* Recent chapters */}
        <section className="surface-card p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30">
            <h2 className="text-headline-sm font-semibold text-on-surface">最近章节</h2>
            <Link to="/editor" className="text-primary text-label-md hover:underline">
              新建章节
            </Link>
          </div>
          {chaptersQuery.isLoading ? (
            <Spin />
          ) : chapters.length === 0 ? (
            <Empty description="该作品还没有章节" />
          ) : (
            <table className="w-full text-left">
              <thead>
                <tr className="text-on-surface-variant text-label-sm">
                  <th className="py-2 font-medium">章节</th>
                  <th className="py-2 font-medium">状态</th>
                  <th className="py-2 font-medium">字数</th>
                  <th className="py-2 font-medium">最近编辑</th>
                </tr>
              </thead>
              <tbody className="text-body-md text-on-surface">
                {chapters.slice(0, 20).map((c) => (
                  <tr key={c.id} className="border-t border-outline-variant/30 hover:bg-surface-container/40">
                    <td className="py-3">
                      <Link
                        to={`/editor/${c.id}`}
                        className="flex items-center gap-2 hover:text-primary"
                      >
                        <FileText size={18} className="text-outline" />
                        <span className="font-code-md text-primary">{c.id.slice(0, 4)}</span>
                        <span>{c.title}</span>
                      </Link>
                    </td>
                    <td className="py-3">
                      <span className="font-code-sm">{STATUS_CHAPTER_LABEL[c.status] ?? c.status}</span>
                    </td>
                    <td className="py-3 font-code-md">{c.word_count.toLocaleString()}</td>
                    <td className="py-3 font-code-sm text-on-surface-variant flex items-center gap-1">
                      <Clock size={12} /> {new Date(c.updated_at).toLocaleString('zh-CN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}

const GENRE_LABEL: Record<string, string> = {
  fantasy: '玄幻',
  urban: '都市',
  romance: '言情',
  historical: '历史',
  sci_fi: '科幻',
  mystery: '悬疑',
  other: '其他',
};

const STATUS_LABEL: Record<Work['status'], string> = {
  draft: '草稿',
  writing: '连载中',
  finished: '已完结',
  archived: '已归档',
};

const STATUS_CHAPTER_LABEL: Record<string, string> = {
  draft: '草稿',
  generated: '已生成',
  reviewed: '已审阅',
  finalized: '已定稿',
};

function Stat({
  label, value, sub, isProgress, progress,
}: {
  label: string;
  value: string;
  sub?: string;
  isProgress?: boolean;
  progress?: number;
}) {
  return (
    <div className="surface-card p-4 flex flex-col">
      <span className="text-label-sm text-outline uppercase">{label}</span>
      <span className="text-headline-md font-bold text-on-surface mt-1">{value}</span>
      {isProgress ? (
        <div className="h-1.5 mt-2 rounded-full bg-surface-container-high">
          <div className="h-full rounded-full bg-primary" style={{ width: `${progress}%` }} />
        </div>
      ) : sub ? (
        <span className="font-code-sm text-on-surface-variant">{sub}</span>
      ) : null}
    </div>
  );
}
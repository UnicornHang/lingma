import { Link } from 'react-router-dom';
import {
  BookOpen,
  FileText,
  Network,
  Users,
  MoreHorizontal,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Clock,
} from 'lucide-react';

const RECENT_CHAPTERS = [
  { ch: 142, title: '风雪剑来',   words: 3420, score: 9.1, ago: '2 小时前', active: true },
  { ch: 141, title: '山外有山',   words: 3180, score: 8.7, ago: '昨天',     active: false },
  { ch: 140, title: '临江宴',     words: 2940, score: 8.5, ago: '3 天前',  active: false },
  { ch: 139, title: '江湖再见',   words: 3520, score: 9.3, ago: '5 天前',  active: false },
];

const ACTIVITIES = [
  { Icon: Sparkles, bg: 'bg-primary-container', color: 'text-primary',
    title: 'Writer 续写了 第 142 章 第三段', when: '2 小时前' },
  { Icon: CheckCircle2, bg: 'bg-tertiary-container', color: 'text-tertiary',
    title: '一致性检查通过：第 142 章', when: '2 小时前' },
  { Icon: AlertTriangle, bg: 'bg-error-container', color: 'text-error',
    title: '世界观冲突：来客道袍颜色', when: '4 小时前' },
  { Icon: FileText, bg: 'bg-secondary-container', color: 'text-on-secondary-fixed-variant',
    title: '手动编辑 第 142 章 · 720 字', when: '昨天' },
];

export default function WorkDetailPage() {
  return (
    <div className="w-full h-full overflow-y-auto bg-surface-container-low">
      <div className="p-8 flex flex-col gap-6">
        {/* Hero */}
        <section className="p-8 rounded-2xl bg-gradient-to-br from-primary via-[#7A7DEF] to-[#5B5FE9] text-white shadow-L2-popover flex items-center gap-6">
          <div className="h-32 w-32 rounded-2xl bg-white/10 backdrop-blur flex items-center justify-center">
            <BookOpen size={64} className="text-white" strokeWidth={1.5} />
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="chip-tertiary">连载中</span>
              <span className="px-2 py-0.5 rounded-full bg-white/20 text-white font-code-sm">
                玄幻 · 修仙 · 男频
              </span>
            </div>
            <h1 className="text-display font-bold text-white">剑来·前传</h1>
            <p className="text-body-lg text-white/80 max-w-2xl">
              讲述陈平安从骊珠洞天走出后的一段尘缘。他要修的不只是大道，更是人心……
            </p>
            <div className="flex items-center gap-4 mt-2">
              <Link
                to="/editor"
                className="flex items-center gap-2 px-6 py-3 bg-white text-primary rounded-lg text-label-md font-semibold hover:opacity-90"
              >
                <FileText size={20} />
                <span>打开编辑器</span>
              </Link>
              <Link
                to="/outline"
                className="flex items-center gap-2 px-6 py-3 bg-white/10 backdrop-blur text-white border border-white/30 rounded-lg text-label-md font-medium"
              >
                <Network size={20} />
                <span>查看大纲</span>
              </Link>
              <Link
                to="/characters"
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
        <section className="grid grid-cols-6 gap-4">
          <Stat label="总字数" value="352,431" trend="↑ 8,200 本周" trendColor="text-tertiary" />
          <Stat label="章节"   value="142" sub="3 卷 12 节" />
          <Stat label="角色"   value="38"  sub="5 主角 · 33 配角" />
          <Stat label="地点"   value="17"  sub="6 大陆 11 秘境" />
          <Stat label="伏笔"   value="28"  sub="3 项待回收" subColor="text-error" />
          <Stat label="已完成度" value="35%" isProgress progress={35} />
        </section>

        {/* Recent chapters + activity */}
        <section className="grid grid-cols-3 gap-4">
          <div className="col-span-2 surface-card p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30">
              <h2 className="text-headline-sm font-semibold text-on-surface">最近章节</h2>
              <Link to="/editor" className="text-primary text-label-md hover:underline">
                查看全部
              </Link>
            </div>
            <table className="w-full text-left">
              <thead>
                <tr className="text-on-surface-variant text-label-sm">
                  <th className="py-2 font-medium">章节</th>
                  <th className="py-2 font-medium">字数</th>
                  <th className="py-2 font-medium">评分</th>
                  <th className="py-2 font-medium">最近编辑</th>
                </tr>
              </thead>
              <tbody className="text-body-md text-on-surface">
                {RECENT_CHAPTERS.map((c) => (
                  <tr key={c.ch} className="border-t border-outline-variant/30">
                    <td className="py-3 flex items-center gap-2">
                      <FileText size={18} className={c.active ? 'text-primary' : 'text-outline'} />
                      <span className="font-code-md text-primary">第 {c.ch} 章</span>
                      <span>{c.title}</span>
                    </td>
                    <td className="py-3 font-code-md">{c.words.toLocaleString()}</td>
                    <td className="py-3">
                      <span
                        className={`font-code-sm font-semibold ${
                          c.score >= 9 ? 'text-tertiary' : 'text-primary'
                        }`}
                      >
                        {c.score.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-3 font-code-sm text-on-surface-variant">{c.ago}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="surface-card p-6 flex flex-col gap-4">
            <h2 className="text-headline-sm font-semibold text-on-surface pb-3 border-b border-outline-variant/30">
              最近活动
            </h2>
            <div className="flex flex-col gap-4">
              {ACTIVITIES.map((a, i) => (
                <div key={i} className="flex items-start gap-2">
                  <div className={`w-8 h-8 rounded-full ${a.bg} flex items-center justify-center`}>
                    <a.Icon size={16} className={a.color} />
                  </div>
                  <div className="flex-1">
                    <p className="text-body-md text-on-surface">{a.title}</p>
                    <span className="font-code-sm text-outline flex items-center gap-1 mt-0.5">
                      <Clock size={12} /> {a.when}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function Stat({
  label, value, sub, trend, trendColor, subColor, isProgress, progress,
}: {
  label: string;
  value: string;
  sub?: string;
  trend?: string;
  trendColor?: string;
  subColor?: string;
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
      ) : trend ? (
        <span className={`font-code-sm ${trendColor ?? 'text-on-surface-variant'}`}>{trend}</span>
      ) : sub ? (
        <span className={`font-code-sm ${subColor ?? 'text-on-surface-variant'}`}>{sub}</span>
      ) : null}
    </div>
  );
}
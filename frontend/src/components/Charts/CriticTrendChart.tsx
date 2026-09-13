/**
 * [P3.2] Critic 评分趋势图 —— echarts-for-react
 *
 * 数据语义: 每个点是「评审当时的快照」,与当前 chapter.version 内容不一定匹配。
 * 顶部永久 disclaimer 提醒用户勿误读为「章节评分在下降」。
 *
 * 显示策略:
 * - 0 条 → 空态(Empty + 解释)
 * - 1 条 → 单点 caption「趋势待积累,继续生成章节或触发重评」
 * - ≥2 条 → 折线图(4 子分 + overall 虚线)
 *
 * 性能:
 * - echarts 包体 ~1MB gzipped,通过 lazy import 异步加载,
 *   减少首屏 CommonJS chunk 体积
 * - Suspense fallback 显示骨架屏
 */
import { useMemo, Suspense, lazy } from 'react';
import { Empty, Skeleton, Alert } from 'antd';
import { TrendingUp } from 'lucide-react';
import type { CriticEvaluationListItem } from '@/api/chapters';

// ReactECharts 包体较大(~150KB gzipped),lazy 加载避免污染 Modal 打开前的初始 bundle
const ReactECharts = lazy(() => import('echarts-for-react'));

interface Props {
  evaluations: CriticEvaluationListItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
}

const DIM_COLORS = {
  consistency: '#1677ff', // primary blue
  pacing: '#52c41a',      // green
  prose: '#faad14',       // amber
  engagement: '#f5222d',  // red
  overall: '#722ed1',     // purple
} as const;

const DIM_LABELS: Record<keyof typeof DIM_COLORS, string> = {
  consistency: '一致性',
  pacing: '节奏',
  prose: '文笔',
  engagement: '钩子',
  overall: '综合',
};

export function CriticTrendChart({ evaluations, isLoading, isError }: Props) {
  // ===== 0 / 1 点 → 极简文案(显式说明,不强行画空图) =====
  if (isLoading) {
    return <Skeleton active paragraph={{ rows: 3 }} />;
  }
  if (isError) {
    return (
      <Alert
        type="error"
        showIcon
        message="评分历史加载失败"
        description="请检查网络连接或稍后重试"
      />
    );
  }
  if (!evaluations || evaluations.length === 0) {
    return (
      <div data-testid="critic-trend-empty">
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div className="flex flex-col gap-1">
              <span className="text-on-surface">暂无 Critic 评审记录</span>
              <span className="text-body-xs text-on-surface-variant">
                启用自动评审(P2 默认开)后,每次生成章节都会落一条评分
              </span>
            </div>
          }
        />
      </div>
    );
  }
  if (evaluations.length === 1) {
    const only = evaluations[0];
    return (
      <div
        data-testid="critic-trend-single"
        className="surface-card p-4 flex items-start gap-3"
      >
        <TrendingUp size={18} className="text-primary mt-1 shrink-0" />
        <div className="flex flex-col gap-1">
          <span className="text-body-md text-on-surface font-medium">
            趋势待积累
          </span>
          <span className="text-body-sm text-on-surface-variant">
            当前共 1 条评审(v{only.version_no},overall {only.overall.toFixed(2)});
            继续生成或触发自动改写后再看曲线变化。
          </span>
        </div>
      </div>
    );
  }

  // ===== ≥2 点 → 折线图 =====
  return <Chart evaluations={evaluations} />;
}

function Chart({ evaluations }: { evaluations: CriticEvaluationListItem[] }) {
  // X 轴 = version_no(评审当时的快照)
  const xAxisData = useMemo(
    () => evaluations.map((e) => `v${e.version_no}`),
    [evaluations],
  );

  // 4 维度 + overall 共 5 条线
  const series = useMemo(
    () =>
      (Object.keys(DIM_COLORS) as Array<keyof typeof DIM_COLORS>).map((dim) => ({
        name: DIM_LABELS[dim],
        type: 'line' as const,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: DIM_COLORS[dim],
          width: dim === 'overall' ? 2 : 1.5,
          type: dim === 'overall' ? 'dashed' : 'solid',
        },
        itemStyle: { color: DIM_COLORS[dim] },
        data: evaluations.map((e) => e[dim]),
      })),
    [evaluations],
  );

  const option = {
    grid: { left: 40, right: 20, top: 40, bottom: 30 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      valueFormatter: (v: number) => v.toFixed(2),
    },
    legend: {
      data: series.map((s) => s.name),
      bottom: 0,
      icon: 'roundRect',
    },
    xAxis: {
      type: 'category',
      data: xAxisData,
      boundaryGap: false,
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      splitNumber: 5,
      axisLabel: {
        fontSize: 11,
        formatter: (v: number) => v.toFixed(1),
      },
    },
    series,
  };

  return (
    <div data-testid="critic-trend-chart" className="flex flex-col gap-2">
      <Alert
        type="info"
        showIcon
        banner
        message="评分是评审当时的快照,与当前章节内容不一定匹配——多用于观察历史变化趋势"
      />
      <Suspense fallback={<Skeleton active paragraph={{ rows: 3 }} />}>
        <ReactECharts option={option} style={{ height: 280 }} notMerge lazyUpdate />
      </Suspense>
    </div>
  );
}
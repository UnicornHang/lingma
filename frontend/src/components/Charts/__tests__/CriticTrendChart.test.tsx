/**
 * [P3.2] CriticTrendChart 组件单测
 *
 * 覆盖:
 * - 0 条 → 显示「空态」文案
 * - 1 条 → 显示「趋势待积累」caption
 * - ≥2 条 → 显示图表(disclaimer + 5 series)
 * - loading → skeleton
 * - error → 错误 Alert
 *
 * 不依赖 @testing-library/jest-dom: 用 document.querySelector + textContent
 * 直接断言 DOM 存在性,与项目既有 selection.test.tsx 风格一致。
 *
 * 注: echarts-for-react 在 happy-dom + Windows symlink 受限环境下无法解析
 * `tslib`/`echarts` 真实模块,所以 mock 掉。组件本身(disclaimer / 5-series legend
 * / chart container)的契约验证不受影响。
 */
import { describe, it, expect, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';

// mock echarts-for-react 的 lazy 导入(返回固定 div 占位,不渲染真图)
vi.mock('echarts-for-react', () => ({
  default: ({ option }: { option: { legend?: { data?: string[] } } }) => (
    <div
      data-testid="echarts-mock"
      data-legend={JSON.stringify(option.legend?.data ?? [])}
    />
  ),
}));

import { CriticTrendChart } from '../CriticTrendChart';
import type { CriticEvaluationListItem } from '@/api/chapters';

const makeEval = (
  version: number,
  overall: number,
  created = '2026-09-13T12:00:00Z',
): CriticEvaluationListItem => ({
  id: `eval-${version}`,
  version_no: version,
  overall,
  consistency: overall,
  pacing: overall,
  prose: overall,
  engagement: overall,
  created_at: created,
  model_used: 'mock',
});

describe('CriticTrendChart', () => {
  it('renders empty state when 0 evaluations', () => {
    const { container } = render(
      <CriticTrendChart evaluations={[]} isLoading={false} isError={false} />,
    );
    expect(container.querySelector('[data-testid="critic-trend-empty"]')).toBeTruthy();
    expect(container.textContent).toMatch(/暂无 Critic 评审记录/);
  });

  it('renders loading skeleton when isLoading=true', () => {
    const { container } = render(
      <CriticTrendChart evaluations={undefined} isLoading isError={false} />,
    );
    expect(container.querySelector('.ant-skeleton')).toBeTruthy();
  });

  it('renders error alert when isError=true', () => {
    const { container } = render(
      <CriticTrendChart evaluations={undefined} isLoading={false} isError />,
    );
    expect(container.textContent).toMatch(/评分历史加载失败/);
  });

  it('renders single-point caption when exactly 1 evaluation', () => {
    const { container } = render(
      <CriticTrendChart
        evaluations={[makeEval(1, 0.6)]}
        isLoading={false}
        isError={false}
      />,
    );
    expect(container.querySelector('[data-testid="critic-trend-single"]')).toBeTruthy();
    expect(container.textContent).toMatch(/趋势待积累/);
    expect(container.textContent).toMatch(/v1/);
    expect(container.textContent).toMatch(/0\.60/);
  });

  it('renders chart container with disclaimer when >=2 evaluations', async () => {
    const { container } = render(
      <CriticTrendChart
        evaluations={[
          makeEval(1, 0.5, '2026-09-13T12:00:00Z'),
          makeEval(2, 0.7, '2026-09-13T14:00:00Z'),
        ]}
        isLoading={false}
        isError={false}
      />,
    );

    // 图表容器 + 顶部 disclaimer(disclaimer 是 alert banner,不是 ECharts legend)
    expect(container.querySelector('[data-testid="critic-trend-chart"]')).toBeTruthy();
    expect(container.textContent).toMatch(/评分是评审当时的快照/);

    // echarts-for-react 通过 mock 异步加载,5 条 series 名进入 option.legend.data
    await waitFor(() => {
      const mock = container.querySelector('[data-testid="echarts-mock"]');
      expect(mock).toBeTruthy();
      const legendData = JSON.parse(mock?.getAttribute('data-legend') ?? '[]');
      expect(legendData).toEqual(
        expect.arrayContaining(['一致性', '节奏', '文笔', '钩子', '综合']),
      );
    });
  });
});
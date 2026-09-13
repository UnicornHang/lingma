/** [P3.4] ExportWorkModal 测试。 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App as AntApp } from 'antd';

import { ExportWorkModal } from '../ExportWorkModal';

// ---- exportApi mock ----
const mockExportWork = vi.fn();
const mockDownloadBlob = vi.fn();

vi.mock('@/api/export', () => ({
  exportWork: (...args: unknown[]) => mockExportWork(...args),
  downloadBlob: (...args: unknown[]) => mockDownloadBlob(...args),
}));

function renderModal(props: Partial<React.ComponentProps<typeof ExportWorkModal>> = {}) {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    workId: 'work-1',
    workTitle: '测试作品',
    ...props,
  };
  return {
    ...render(
      <AntApp>
        <ExportWorkModal {...defaultProps} />
      </AntApp>
    ),
    props: defaultProps,
  };
}

describe('ExportWorkModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // jsdom 不实现 URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();
  });
  afterEach(() => cleanup());

  it('渲染时显示作品标题与默认格式 DOCX', () => {
    renderModal();
    expect(screen.getByText('《测试作品》')).toBeTruthy();
    // 验证 DOCX 单选框存在(用 label 文本而非 hidden input)
    const docxLabel = screen.getByText('DOCX');
    expect(docxLabel).toBeTruthy();
  });

  it('点击「开始导出」调用 exportWork 并下载', async () => {
    const fakeBlob = new Blob(['PK\x03\x04mock'], { type: 'application/octet-stream' });
    mockExportWork.mockResolvedValueOnce({
      blob: fakeBlob,
      headers: {
        contentLength: 1024,
        filename: '测试作品.docx',
        chapterCount: 5,
        volumeCount: 2,
        mediaType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      },
    });
    renderModal();

    fireEvent.click(screen.getByTestId('export-submit'));

    await waitFor(() => {
      expect(mockExportWork).toHaveBeenCalledWith(
        'work-1',
        'docx',
        expect.objectContaining({ include_outline: true })
      );
    });
    expect(mockDownloadBlob).toHaveBeenCalledWith(fakeBlob, '测试作品.docx');
  });

  it('切换到 EPUB 格式 → 提交时传 epub', async () => {
    mockExportWork.mockResolvedValueOnce({
      blob: new Blob(['x'], { type: 'application/epub+zip' }),
      headers: {
        contentLength: 100,
        filename: 'x.epub',
        chapterCount: 1,
        volumeCount: 1,
        mediaType: 'application/epub+zip',
      },
    });
    renderModal();

    // 点击 EPUB 标签触发 Radio 切换
    fireEvent.click(screen.getByText('EPUB'));
    fireEvent.click(screen.getByTestId('export-submit'));

    await waitFor(() => {
      expect(mockExportWork).toHaveBeenCalledWith(
        'work-1',
        'epub',
        expect.any(Object)
      );
    });
  });

  it('取消勾选「按大纲分卷」时 include_outline=false', async () => {
    mockExportWork.mockResolvedValueOnce({
      blob: new Blob(['x']),
      headers: {
        contentLength: 1,
        filename: 'a.docx',
        chapterCount: 0,
        volumeCount: 0,
        mediaType: '',
      },
    });
    renderModal();

    // 点击 checkbox label 切换
    fireEvent.click(screen.getByText(/按大纲分卷/));
    fireEvent.click(screen.getByTestId('export-submit'));

    await waitFor(() => {
      expect(mockExportWork).toHaveBeenCalledWith(
        'work-1',
        'docx',
        expect.objectContaining({ include_outline: false })
      );
    });
  });

  it('导出失败时显示错误信息且不调用 downloadBlob', async () => {
    mockExportWork.mockRejectedValueOnce(new Error('章节数 600 超过导出上限 500'));
    renderModal();

    fireEvent.click(screen.getByTestId('export-submit'));

    await waitFor(() => {
      const errEl = screen.queryByTestId('export-error');
      expect(errEl?.textContent ?? '').toContain('超过导出上限');
    });
    expect(mockDownloadBlob).not.toHaveBeenCalled();
  });

  it('导出成功后显示文件大小 / 章节 / 卷信息', async () => {
    mockExportWork.mockResolvedValueOnce({
      blob: new Blob(['x']),
      headers: {
        contentLength: 2048,
        filename: '测试.docx',
        chapterCount: 12,
        volumeCount: 3,
        mediaType: '',
      },
    });
    renderModal();

    fireEvent.click(screen.getByTestId('export-submit'));

    await waitFor(() => {
      const succEl = screen.queryByTestId('export-success');
      expect(succEl?.textContent ?? '').toContain('12 章');
      expect(succEl?.textContent ?? '').toContain('3 卷');
    });
  });

  it('open=false 时不渲染 modal 内容', () => {
    renderModal({ open: false });
    expect(screen.queryByTestId('export-work-modal')).toBeNull();
  });
});

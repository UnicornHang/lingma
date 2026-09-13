/** [P3.4] 作品导出 API —— DOCX / EPUB 下载。 */

export type ExportFormat = 'docx' | 'epub';

export interface ExportOptions {
  /** 是否按 OutlineNode 分卷(默认 true) */
  include_outline?: boolean;
  /** 覆盖默认 CJK 字体名(默认留空 = 用后端 settings.export_cjk_font_name) */
  cjk_font_name?: string;
}

/** 后端响应头(StreamingResponse) */
export interface ExportResponseHeaders {
  /** 实际字节数 */
  contentLength: number;
  /** 文件名(从 Content-Disposition 提取) */
  filename: string;
  /** 章节数(从 X-Chapter-Count 提取) */
  chapterCount: number;
  /** 卷数(从 X-Volume-Count 提取) */
  volumeCount: number;
  /** Content-Type */
  mediaType: string;
}

/**
 * 触发导出并下载文件 —— 返回 Blob 与解析后的响应头。
 *
 * 为什么不直接给 `<a download>` 拼 URL?因为需要从响应头读取 X-Chapter-Count
 * 等元数据用于 UI 提示,直接 fetch + blob 才能拿到这些头。
 */
export async function exportWork(
  workId: string,
  format: ExportFormat,
  options: ExportOptions = {}
): Promise<{ blob: Blob; headers: ExportResponseHeaders }> {
  const API_BASE = (import.meta.env.VITE_API_BASE || '/api/v1') as string;
  const params = new URLSearchParams();
  if (options.include_outline !== undefined) {
    params.set('include_outline', String(options.include_outline));
  }
  if (options.cjk_font_name) {
    params.set('cjk_font_name', options.cjk_font_name);
  }
  const url = `${API_BASE}/works/${workId}/export/${format}?${params.toString()}`;

  const res = await fetch(url, {
    method: 'GET',
    credentials: 'include',
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore non-JSON
    }
    throw new Error(`导出失败: ${detail}`);
  }

  const blob = await res.blob();
  return {
    blob,
    headers: {
      contentLength: Number(res.headers.get('Content-Length') ?? blob.size),
      filename: extractFilename(res.headers.get('Content-Disposition')),
      chapterCount: Number(res.headers.get('X-Chapter-Count') ?? 0),
      volumeCount: Number(res.headers.get('X-Volume-Count') ?? 0),
      mediaType: res.headers.get('Content-Type') ?? '',
    },
  };
}

/** 从 Content-Disposition 头提取 filename(优先 RFC 5987 的 filename*) */
function extractFilename(header: string | null): string {
  if (!header) return 'export';
  // 优先 filename*=UTF-8''... (RFC 5987)
  const rfc5987 = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (rfc5987) {
    try {
      return decodeURIComponent(rfc5987[1]);
    } catch {
      /* fall through */
    }
  }
  // 退化到普通 filename="..."
  const plain = header.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1] : 'export';
}

/** 触发浏览器下载给定 Blob */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // 延迟 revoke,确保 click 事件在 Chrome 上能完成下载
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

import { http } from './client';
import type { Paginated } from './works';

export type ChapterStatus = 'draft' | 'generated' | 'reviewed' | 'finalized';

/**
 * TipTap JSON document — 简化版本，仅保留必要字段
 */
export interface TipTapDoc {
  type: 'doc';
  content?: TipTapNode[];
}

export interface TipTapNode {
  type: string;
  attrs?: Record<string, unknown>;
  content?: TipTapNode[];
  marks?: Array<{ type: string; attrs?: Record<string, unknown> }>;
  text?: string;
}

export interface Chapter {
  id: string;
  work_id: string;
  title: string;
  content: TipTapDoc | Record<string, unknown>;
  plain_content: string;
  summary: string;
  key_events: string[];
  outline_node_id: string | null;
  status: ChapterStatus;
  word_count: number;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ChapterCreate {
  work_id: string;
  title: string;
  content?: TipTapDoc | Record<string, unknown>;
  plain_content?: string;
  summary?: string;
  key_events?: string[];
  outline_node_id?: string | null;
}

export interface ChapterUpdate {
  title?: string;
  content?: TipTapDoc | Record<string, unknown>;
  plain_content?: string;
  summary?: string;
  key_events?: string[];
  status?: ChapterStatus;
}

/** 章节生成模式：continue=续写（默认），generate=全量重写 */
export type GenerateMode = 'continue' | 'generate';

export interface GenerateChapterRequest {
  chapter_id?: string;
  title?: string;
  outline_node_id?: string;
  target_word_count?: number;
  style_overrides?: Record<string, unknown>;
  /** 续写 vs 全量重写（默认 continue） */
  mode?: GenerateMode;
  /** 续写模式下取章节末尾最近 N 字作为 prompt 上下文（默认 1500） */
  continue_from_chars?: number;
  /** [提交 C] 生成完成后是否自动跑 AI 痕迹检测与去味（默认开） */
  auto_polish?: boolean;
  /** [提交 C] blocking finding 阈值,达到/超过即触发自动重写;默认 0 */
  max_blocking_for_rewrite?: number;
}

/** [提交 C] 自动去味报告 —— WS done 事件附带的元数据 */
export interface AutoPolishReport {
  blocking_count: number;
  advisory_count: number;
  rewrite_attempted: boolean;
  rewrite_succeeded: boolean;
  rewrite_error: string | null;
  final_blocking: number | null;
  pre_findings: Array<{
    category: string;
    severity: string;
    start: number;
    end: number;
    snippet: string;
    message: string;
    rule: string;
  }>;
  elapsed_ms: number;
}

export interface GenerateChapterResponse {
  task_id: string;
  ws_url: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  chapter_id: string;
}

/**
 * 统一通过 `http` 调用 —— 返回 Promise<T>（即后端响应体），无需再 .data。
 */
export const chaptersApi = {
  listByWork: (
    workId: string,
    params?: { page?: number; page_size?: number }
  ) => http.get<Paginated<Chapter>>('/chapters/', { params: { ...params, work_id: workId } }),

  get: (id: string) => http.get<Chapter>(`/chapters/${id}`),

  create: (data: ChapterCreate) => http.post<Chapter>('/chapters/', data),

  update: (id: string, data: ChapterUpdate) => http.patch<Chapter>(`/chapters/${id}`, data),

  delete: (id: string) => http.delete<void>(`/chapters/${id}`),

  generate: (chapterId: string, payload?: GenerateChapterRequest) =>
    http.post<GenerateChapterResponse>(`/chapters/${chapterId}/generate`, payload ?? {}),

  listVersions: (chapterId: string) =>
    http.get<{ total: number; items: ChapterVersion[] }>(`/chapters/${chapterId}/versions`),

  // ----- Editor Agent: AI 痕迹检测 / 去味 -----
  analyzeAIPatterns: (text: string) =>
    http.post<AnalyzeAIPatternsResponse>('/chapters/analyze-ai-patterns', { text }),

  /** 老版同步去味(易超时,不再推荐,保留向后兼容) */
  polish: (payload: PolishChapterRequest) =>
    http.post<PolishChapterResponse>('/chapters/polish', payload),

  /** 流式去味(SSE)—— 不受 axios 30s 超时限制,带实时进度回调。
   *
   * 事件序列:
   * - detected → findings 立即可见(毫秒级)
   * - llm_started → LLM 开始调用
   * - llm_delta(content) → LLM 流式片段(多次)
   * - done → polished_text + rewrites + summary + stats
   * - error → 失败,fallback 字段含原文 + findings
   *
   * 通过 callbacks.onProgress 提供阶段提示,callbacks.onLLMDelta 累积 LLM 原始输出。
   */
  polishStream: async (
    payload: PolishChapterRequest,
    callbacks: {
      onDetected?: (data: PolishStreamDetectedPayload) => void;
      onLLMStarted?: (data: { model: string }) => void;
      onLLMDelta?: (content: string) => void;
      onDone?: (data: PolishStreamDonePayload) => void;
      onError?: (data: PolishStreamErrorPayload) => void;
    } = {},
  ): Promise<PolishStreamDonePayload> => {
    const API_BASE = (import.meta.env.VITE_API_BASE || '/api/v1') as string;

    const res = await fetch(`${API_BASE}/chapters/polish/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok || !res.body) {
      throw new Error(`SSE 请求失败: HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let donePayload: PolishStreamDonePayload | null = null;

    // 解析 SSE 格式:event / data 行对,以空行结束
    const flushEvent = (raw: string): void => {
      // raw 形如 "event: detected\ndata: {...}\n\n"
      const eventLines: string[] = [];
      const dataLines: string[] = [];
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) eventLines.push(line.slice(6).trim());
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
      }
      if (eventLines.length === 0) return;
      const eventName = eventLines.join(' ');
      let parsed: any = {};
      const dataStr = dataLines.join('\n');
      if (dataStr) {
        try {
          parsed = JSON.parse(dataStr);
        } catch {
          parsed = { _raw: dataStr };
        }
      }
      switch (eventName) {
        case 'detected':
          callbacks.onDetected?.(parsed as PolishStreamDetectedPayload);
          break;
        case 'llm_started':
          callbacks.onLLMStarted?.(parsed);
          break;
        case 'llm_delta':
          callbacks.onLLMDelta?.(String(parsed.content ?? ''));
          break;
        case 'done':
          donePayload = parsed as PolishStreamDonePayload;
          callbacks.onDone?.(donePayload);
          break;
        case 'error':
          callbacks.onError?.(parsed as PolishStreamErrorPayload);
          break;
        default:
          // 忽略未知事件
          break;
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // 按双换行切事件;剩余不完整部分继续累积
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';
      for (const part of parts) {
        if (part.trim()) flushEvent(part);
      }
    }

    // 处理末尾残余
    if (buffer.trim()) flushEvent(buffer);

    if (!donePayload) {
      throw new Error('SSE 流未收到 done 事件');
    }
    return donePayload;
  },
};

// ==================== Editor Agent ====================

/** AI 痕迹单条命中 */
export interface PatternFinding {
  category: string;
  severity: 'blocking' | 'advisory';
  start: number;
  end: number;
  snippet: string;
  message: string;
  rule: string;
}

export interface AnalyzeAIPatternsResponse {
  findings: PatternFinding[];
  blocking_count: number;
  advisory_count: number;
  stats: {
    total: number;
    by_category: Record<string, number>;
    by_severity: Record<string, number>;
  };
}

export interface PolishRewrite {
  category: string;
  original: string;
  rewritten: string;
  reason: string;
}

export interface PolishChapterRequest {
  text: string;
  style_keywords?: string[];
  temperature?: number;
  max_tokens?: number;
}

export interface PolishChapterResponse {
  findings: PatternFinding[];
  rewrites: PolishRewrite[];
  polished_text: string;
  summary: string;
  stats: AnalyzeAIPatternsResponse['stats'];
}

// ============ SSE 流式去味事件 payload ============

export interface PolishStreamDetectedPayload {
  findings: PatternFinding[];
  blocking_count: number;
  advisory_count: number;
  stats: AnalyzeAIPatternsResponse['stats'];
}

export interface PolishStreamDonePayload {
  polished_text: string;
  rewrites: PolishRewrite[];
  summary: string;
  stats: AnalyzeAIPatternsResponse['stats'];
}

export interface PolishStreamErrorPayload {
  phase: 'detect' | 'llm';
  error: string;
  fallback?: PolishStreamDonePayload;
}

// ==================== Chapter Version ====================

export interface ChapterVersion {
  id: string;
  chapter_id: string;
  version_no: number;
  plain_content: string;
  generated_by: string; // 'user' | 'ai' | 'ai_revised'
  prompt_used: string;
  model_used: string;
  token_usage: Record<string, number>;
  note: string;
  created_at: string;
}
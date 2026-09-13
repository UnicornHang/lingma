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

  polish: (payload: PolishChapterRequest) =>
    http.post<PolishChapterResponse>('/chapters/polish', payload),
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
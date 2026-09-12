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

export interface GenerateChapterRequest {
  chapter_id?: string;
  title?: string;
  outline_node_id?: string;
  target_word_count?: number;
  style_overrides?: Record<string, unknown>;
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
};
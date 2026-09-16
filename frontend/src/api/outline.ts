import { http } from './client';
import type { WriteConstraints } from './tracking';

export type OutlineNodeType = 'volume' | 'chapter' | 'beat';

export interface OutlineNode {
  id: string;
  parent_id: string | null;
  type: OutlineNodeType;
  title: string;
  summary: string;
  beats: string[];
  characters_involved: string[];
  world_refs: string[];
  target_word_count: number;
  order: number;
  write_constraints?: WriteConstraints;
  work_id: string;
  created_at: string;
  updated_at: string;
}

export interface OutlineTreeNode extends OutlineNode {
  children: OutlineTreeNode[];
}

export interface OutlineTreeResponse {
  work_id: string;
  nodes: OutlineTreeNode[];
}

export interface OutlineNodeCreate {
  work_id: string;
  parent_id?: string | null;
  type: OutlineNodeType;
  title: string;
  summary?: string;
  beats?: string[];
  characters_involved?: string[];
  world_refs?: string[];
  target_word_count?: number;
  order?: number;
  write_constraints?: WriteConstraints;
}

export interface OutlineNodeUpdate {
  parent_id?: string | null;
  type?: OutlineNodeType;
  title?: string;
  summary?: string;
  beats?: string[];
  characters_involved?: string[];
  world_refs?: string[];
  target_word_count?: number;
  order?: number;
  write_constraints?: WriteConstraints;
}

// ==================== AI 推荐大纲（强 schema）====================

export interface PlotBeat {
  title: string;
  summary?: string;
}
export interface PlotChapter {
  title: string;
  summary?: string;
  target_word_count?: number;
  beats?: PlotBeat[];
  characters_involved?: string[];
  world_refs?: string[];
  key_events?: string[];
}
export interface PlotVolume {
  vol_no: number;
  vol_title: string;
  summary?: string;
  chapters: PlotChapter[];
}

export interface PlotOutlineRequest {
  total_volumes?: number;
  target_chapter_count?: number | null;
  extra_hint?: string;
}
export interface PlotOutlineResponse {
  volumes: PlotVolume[];
  model_used: string;
  raw_content?: string;
}

export interface BulkOutlineCreateRequest {
  volumes: PlotVolume[];
  extra_hint?: string;
}

/** 单章细纲扩写建议（不自动落库） */
export interface PlotChapterExpand {
  title: string;
  summary: string;
  beats: string[];
  characters_involved: string[];
  target_word_count: number;
  write_constraints: WriteConstraints;
}

export interface PlotChapterExpandRequest {
  extra_hint?: string;
}

export interface PlotChapterExpandResponse {
  suggestion: PlotChapterExpand;
  model_used: string;
  raw_content?: string;
}

export const outlineApi = {
  list: (workId: string) => http.get<{ total: number; items: OutlineNode[] }>(`/works/${workId}/outline`),

  tree: (workId: string) => http.get<OutlineTreeResponse>(`/works/${workId}/outline/tree`),

  get: (nodeId: string) => http.get<OutlineNode>(`/outline/${nodeId}`),

  create: (payload: OutlineNodeCreate) => http.post<OutlineNode>('/outline', payload),

  update: (nodeId: string, payload: OutlineNodeUpdate) => http.patch<OutlineNode>(`/outline/${nodeId}`, payload),

  delete: (nodeId: string) => http.delete<void>(`/outline/${nodeId}`),

  aiSuggest: (workId: string, payload: PlotOutlineRequest) =>
    http.post<PlotOutlineResponse>(`/works/${workId}/outline/ai-outline`, payload, {
      timeout: 180_000,
    }),

  aiPreview: (payload: {
    work_preview: {
      title: string;
      genre?: string;
      logline?: string;
      style_keywords?: string[];
      target_audience?: string[];
      notes?: string;
      target_word_count?: number;
    };
    total_volumes?: number;
    target_chapter_count?: number | null;
    extra_hint?: string;
  }) =>
    http.post<PlotOutlineResponse>('/outline/ai-preview', payload, {
      timeout: 180_000,
    }),

  /** PlotAgent 扩写本章细纲；返回建议，需再 update 落库 */
  aiExpand: (nodeId: string, payload?: PlotChapterExpandRequest) =>
    http.post<PlotChapterExpandResponse>(`/outline/${nodeId}/ai-expand`, payload ?? {}),

  bulkCreate: (workId: string, payload: BulkOutlineCreateRequest) =>
    http.post<OutlineTreeResponse>(`/works/${workId}/outline/bulk-create`, payload),
};

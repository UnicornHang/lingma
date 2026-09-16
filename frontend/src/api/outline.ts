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

export interface PlotOutlinePreviewPayload {
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

  aiPreview: (payload: PlotOutlinePreviewPayload) =>
    http.post<PlotOutlineResponse>('/outline/ai-preview', payload, {
      timeout: 180_000,
    }),

  /**
   * SSE 预览大纲。思考阶段靠服务端 keepalive 保活，不受 axios 超时限制。
   * 事件：started → (volume_started → llm_delta* → volume)* → done | error
   */
  aiPreviewStream: async (
    payload: PlotOutlinePreviewPayload,
    callbacks: {
      onStarted?: (data: { model: string; chapter_count: number; total_volumes?: number }) => void;
      onVolumeStarted?: (data: { vol_no: number; total: number; chapter_count: number }) => void;
      onVolumeRetry?: (data: {
        vol_no: number;
        attempt: number;
        total_attempts: number;
        total?: number;
      }) => void;
      onVolume?: (volume: PlotVolume) => void;
      onDelta?: (content: string) => void;
      onDone?: (data: PlotOutlineResponse) => void;
      onError?: (message: string) => void;
    } = {},
  ): Promise<PlotOutlineResponse> => {
    const API_BASE = (import.meta.env.VITE_API_BASE || '/api/v1') as string;
    const res = await fetch(`${API_BASE}/outline/ai-preview/stream`, {
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
    let donePayload: PlotOutlineResponse | null = null;
    let streamError: string | null = null;

    const flushEvent = (raw: string): void => {
      const eventLines: string[] = [];
      const dataLines: string[] = [];
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) eventLines.push(line.slice(6).trim());
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
      }
      if (eventLines.length === 0) return;
      const eventName = eventLines.join(' ');
      let parsed: Record<string, unknown> = {};
      const dataStr = dataLines.join('\n');
      if (dataStr) {
        try {
          parsed = JSON.parse(dataStr) as Record<string, unknown>;
        } catch {
          parsed = { _raw: dataStr };
        }
      }
      switch (eventName) {
        case 'started':
          callbacks.onStarted?.(parsed as { model: string; chapter_count: number; total_volumes?: number });
          break;
        case 'volume_started':
          callbacks.onVolumeStarted?.(parsed as { vol_no: number; total: number; chapter_count: number });
          break;
        case 'volume_retry':
          callbacks.onVolumeRetry?.(
            parsed as {
              vol_no: number;
              attempt: number;
              total_attempts: number;
              total?: number;
            },
          );
          break;
        case 'volume':
          if (parsed.volume && typeof parsed.volume === 'object') {
            callbacks.onVolume?.(parsed.volume as PlotVolume);
          }
          break;
        case 'llm_delta':
          callbacks.onDelta?.(String(parsed.content ?? ''));
          break;
        case 'done':
          donePayload = parsed as unknown as PlotOutlineResponse;
          callbacks.onDone?.(donePayload);
          break;
        case 'error':
          streamError = String(parsed.error ?? '大纲生成失败');
          callbacks.onError?.(streamError);
          break;
        default:
          break;
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';
      for (const part of parts) {
        if (part.trim()) flushEvent(part);
      }
    }
    if (buffer.trim()) flushEvent(buffer);

    if (streamError) {
      throw new Error(streamError);
    }
    if (!donePayload) {
      throw new Error('SSE 流未收到 done 事件');
    }
    return donePayload;
  },

  /** PlotAgent 扩写本章细纲；返回建议，需再 update 落库 */
  aiExpand: (nodeId: string, payload?: PlotChapterExpandRequest) =>
    http.post<PlotChapterExpandResponse>(`/outline/${nodeId}/ai-expand`, payload ?? {}),

  bulkCreate: (workId: string, payload: BulkOutlineCreateRequest) =>
    http.post<OutlineTreeResponse>(`/works/${workId}/outline/bulk-create`, payload),
};

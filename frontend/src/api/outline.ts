import { http } from './client';

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
}

export const outlineApi = {
  list: (workId: string) => http.get<{ total: number; items: OutlineNode[] }>(`/works/${workId}/outline`),

  tree: (workId: string) => http.get<OutlineTreeResponse>(`/works/${workId}/outline/tree`),

  get: (nodeId: string) => http.get<OutlineNode>(`/outline/${nodeId}`),

  create: (payload: OutlineNodeCreate) => http.post<OutlineNode>('/outline', payload),

  update: (nodeId: string, payload: OutlineNodeUpdate) => http.patch<OutlineNode>(`/outline/${nodeId}`, payload),

  delete: (nodeId: string) => http.delete<void>(`/outline/${nodeId}`),
};
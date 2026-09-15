import { http } from './client';

export interface WorldBible {
  id: string;
  work_id: string;
  geography: Record<string, unknown>;
  factions: unknown[];
  power_system: Record<string, unknown>;
  timeline: unknown[];
  rules: unknown[];
  culture: Record<string, unknown>;
  raw_text: string;
  is_indexed: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorldBibleCreate {
  work_id: string;
  geography?: Record<string, unknown>;
  factions?: unknown[];
  power_system?: Record<string, unknown>;
  timeline?: unknown[];
  rules?: unknown[];
  culture?: Record<string, unknown>;
  raw_text?: string;
}

export interface WorldBibleUpdate {
  geography?: Record<string, unknown>;
  factions?: unknown[];
  power_system?: Record<string, unknown>;
  timeline?: unknown[];
  rules?: unknown[];
  culture?: Record<string, unknown>;
  raw_text?: string;
}

export const worldApi = {
  getOrCreate: (workId: string) => http.get<WorldBible>(`/works/${workId}/world`),

  create: (data: WorldBibleCreate) => http.post<WorldBible>('/world', data),

  update: (workId: string, data: WorldBibleUpdate) =>
    http.patch<WorldBible>(`/works/${workId}/world`, data),

  checkConsistency: (workId: string, data: ConsistencyCheckRequest = {}) =>
    http.post<ConsistencyCheckResponse>(
      `/works/${workId}/world/check-consistency`,
      data,
    ),
};

export type ConsistencyIssueType =
  | 'geography_conflict'
  | 'faction_conflict'
  | 'power_system_violation'
  | 'timeline_conflict'
  | 'rule_violation'
  | 'culture_conflict'
  | 'other';

export type ConsistencySeverity = 'error' | 'warning' | 'info';

export interface ConsistencyIssue {
  type: ConsistencyIssueType;
  severity: ConsistencySeverity;
  text: string;
  rule_violated: string;
  suggestion: string;
  dimension: string;
  source: 'heuristic' | 'llm';
}

export interface ConsistencyCheckRequest {
  text?: string;
  chapter_id?: string;
}

export interface ConsistencyCheckResponse {
  passed: boolean;
  issue_count: number;
  issues: ConsistencyIssue[];
  summary: string;
  model_used: string;
  checked_chars: number;
  world_empty: boolean;
}
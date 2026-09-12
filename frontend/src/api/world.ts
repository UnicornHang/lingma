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

  update: (workId: string, data: WorldBibleUpdate) => http.patch<WorldBible>(`/works/${workId}/world`, data),
};
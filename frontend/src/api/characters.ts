import { http } from './client';

export type CharacterRole = 'protagonist' | 'antagonist' | 'supporting' | 'narrator';

export interface Character {
  id: string;
  work_id: string;
  name: string;
  role: string;
  basic_info: Record<string, unknown>;
  personality: Record<string, unknown>;
  backstory: Record<string, unknown>;
  relationships: unknown[];
  arc: Record<string, unknown>;
  voice_samples: unknown[];
  raw_text: string;
  appearance_count: number;
  is_indexed: boolean;
  created_at: string;
  updated_at: string;
}

export interface CharacterCreate {
  work_id: string;
  name: string;
  role?: string;
  basic_info?: Record<string, unknown>;
  personality?: Record<string, unknown>;
  backstory?: Record<string, unknown>;
  relationships?: unknown[];
  arc?: Record<string, unknown>;
  voice_samples?: unknown[];
  raw_text?: string;
}

export interface CharacterUpdate {
  name?: string;
  role?: string;
  basic_info?: Record<string, unknown>;
  personality?: Record<string, unknown>;
  backstory?: Record<string, unknown>;
  relationships?: unknown[];
  arc?: Record<string, unknown>;
  voice_samples?: unknown[];
  raw_text?: string;
}

export const charactersApi = {
  list: (workId: string) => http.get<{ total: number; items: Character[] }>(`/works/${workId}/characters`),

  get: (id: string) => http.get<Character>(`/characters/${id}`),

  create: (data: CharacterCreate) => http.post<Character>('/characters', data),

  update: (id: string, data: CharacterUpdate) => http.patch<Character>(`/characters/${id}`, data),

  delete: (id: string) => http.delete<void>(`/characters/${id}`),
};
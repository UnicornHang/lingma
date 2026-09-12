import { http } from './client';

export type CharacterRole = 'protagonist' | 'antagonist' | 'supporting' | 'narrator';

export interface Character {
  id: string;
  work_id: string;
  name: string;
  role: CharacterRole;
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

// ==================== AI 推荐（强 schema）====================

export interface CharacterBasicInfo {
  age?: string | null;
  occupation?: string | null;
  appearance?: string | null;
  background?: string | null;
}
export interface CharacterPersonality {
  traits: string[];
  mbti?: string | null;
  strengths: string[];
  flaws: string[];
}
export interface CharacterBackstory {
  origin?: string | null;
  key_events: string[];
  secrets: string[];
}
export interface CharacterRelationship {
  target_character: string;
  relation: string;
  dynamic: string;
}
export interface CharacterArc {
  start_state?: string | null;
  end_state?: string | null;
  key_transformations: string[];
}
export interface CharacterCard {
  name: string;
  role: CharacterRole;
  basic_info: CharacterBasicInfo;
  personality: CharacterPersonality;
  backstory: CharacterBackstory;
  relationships: CharacterRelationship[];
  arc: CharacterArc;
  voice_samples: string[];
  raw_text: string;
}

export type CharacterSuggestFocus = 'protagonist' | 'antagonist' | 'supporting' | 'all';
export interface CharacterSuggestRequest {
  work_id: string;
  count?: number;
  focus?: CharacterSuggestFocus;
  extra_hint?: string;
}
export interface CharacterSuggestResponse {
  cards: CharacterCard[];
  model_used: string;
  raw_content?: string;
}

export const charactersApi = {
  list: (workId: string) => http.get<{ total: number; items: Character[] }>(`/works/${workId}/characters`),

  get: (id: string) => http.get<Character>(`/characters/${id}`),

  create: (data: CharacterCreate) => http.post<Character>('/characters', data),

  update: (id: string, data: CharacterUpdate) => http.patch<Character>(`/characters/${id}`, data),

  delete: (id: string) => http.delete<void>(`/characters/${id}`),

  aiSuggest: (workId: string, payload: Omit<CharacterSuggestRequest, 'work_id'>) =>
    http.post<CharacterSuggestResponse>('/characters/ai-suggest', { work_id: workId, ...payload }),
};

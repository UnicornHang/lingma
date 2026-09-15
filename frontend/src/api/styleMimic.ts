import { http } from './client';

/** 去剧情化短技法片段 */
export interface StyleSnippet {
  tag: string;
  text: string;
}

/** 结构化风格画像 */
export interface StylePortrait {
  narrative_pov: string;
  avg_sentence_len: string;
  dialogue_density: string;
  rhetoric_habits: string[];
  pacing_tags: string[];
  emotional_style: string;
  lexicon_notes: string;
}

/** 作品级仿文风格记忆 */
export interface StyleProfile {
  id: string;
  work_id: string;
  source_label: string;
  source_char_count: number;
  portrait: StylePortrait;
  writing_directives: string;
  snippets: StyleSnippet[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface StyleMimicAnalyzeRequest {
  sample_text: string;
  source_label?: string;
  save?: boolean;
  enabled?: boolean;
}

export interface StyleMimicAnalyzeResponse {
  portrait: StylePortrait;
  writing_directives: string;
  snippets: StyleSnippet[];
  source_char_count: number;
  model_used: string;
  used_heuristic: boolean;
  profile: StyleProfile | null;
}

export interface StyleProfileUpdate {
  enabled?: boolean;
  source_label?: string;
}

/** 仿文风格画像 API */
export const styleMimicApi = {
  analyze: (workId: string, data: StyleMimicAnalyzeRequest) =>
    http.post<StyleMimicAnalyzeResponse>(`/works/${workId}/style-mimic/analyze`, data),

  get: (workId: string) =>
    http.get<StyleProfile | null>(`/works/${workId}/style-mimic`),

  update: (workId: string, data: StyleProfileUpdate) =>
    http.patch<StyleProfile>(`/works/${workId}/style-mimic`, data),

  remove: (workId: string) =>
    http.delete<void>(`/works/${workId}/style-mimic`),
};

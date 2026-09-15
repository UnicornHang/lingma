import { http } from './client';

/** 本章约束锁（项目事实，优先于技法） */
export interface WriteConstraints {
  word_count_min?: number | null;
  word_count_max?: number | null;
  must_happen: string[];
  must_not_happen: string[];
  time_anchor: string;
  stop_point: string;
  end_hook_debt: string;
}

export interface ForeshadowItem {
  id: string;
  title: string;
  description: string;
  status: 'open' | 'paid' | 'broken';
  planted_chapter_id?: string | null;
  payoff_chapter_id?: string | null;
  character_names: string[];
}

export interface CharacterRuntimeState {
  character_id: string;
  name: string;
  location: string;
  goal: string;
  known_facts: string[];
  unknown_facts: string[];
  open_threads: string[];
}

export interface TimelineEvent {
  text: string;
  chapter_id?: string | null;
}

export interface WriterContextCard {
  constraints: WriteConstraints;
  character_states: CharacterRuntimeState[];
  open_foreshadows: ForeshadowItem[];
  author_timeline: TimelineEvent[];
  reader_timeline: TimelineEvent[];
  last_chapter_id?: string | null;
}

export interface TrackingStateRead {
  work_id: string;
  revision: number;
  last_chapter_id?: string | null;
  foreshadows: ForeshadowItem[];
  character_states: CharacterRuntimeState[];
  author_timeline: TimelineEvent[];
  reader_timeline: TimelineEvent[];
  chapter_records: Array<{ chapter_id?: string | null; note: string }>;
  context_card?: WriterContextCard | null;
}

export interface TrackingCommitPayload {
  chapter_id?: string;
  foreshadows_planted?: Array<{ title: string; description?: string; character_names?: string[] }>;
  foreshadows_paid?: string[];
  character_updates?: Array<{
    character_id: string;
    name?: string;
    location?: string;
    goal?: string;
    known_facts_add?: string[];
    unknown_facts_add?: string[];
    known_facts?: string[];
    unknown_facts?: string[];
    open_threads?: string[];
  }>;
  author_events?: string[];
  reader_events?: string[];
  note?: string;
}

export interface ForeshadowUpsertPayload {
  id?: string;
  title: string;
  description?: string;
  status?: 'open' | 'paid' | 'broken';
  character_names?: string[];
}

/** 作品连续性账本 API */
export const trackingApi = {
  get: (workId: string, outlineNodeId?: string) =>
    http.get<TrackingStateRead>(`/works/${workId}/tracking`, {
      params: outlineNodeId ? { outline_node_id: outlineNodeId } : undefined,
    }),

  context: (workId: string, outlineNodeId?: string) =>
    http.get<WriterContextCard>(`/works/${workId}/tracking/context`, {
      params: outlineNodeId ? { outline_node_id: outlineNodeId } : undefined,
    }),

  commit: (workId: string, payload: TrackingCommitPayload) =>
    http.post<TrackingStateRead>(`/works/${workId}/tracking/commit`, payload),

  upsertForeshadow: (workId: string, payload: ForeshadowUpsertPayload) =>
    http.post<TrackingStateRead>(`/works/${workId}/tracking/foreshadows`, payload),
};

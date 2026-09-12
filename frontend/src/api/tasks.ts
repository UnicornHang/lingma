import { http } from './client';

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface GenerationTask {
  id: string;
  work_id: string;
  chapter_id: string | null;
  outline_node_id: string | null;
  task_type: string;
  status: TaskStatus;
  progress: number;
  params: Record<string, unknown>;
  result: Record<string, unknown>;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  token_usage: Record<string, number>;
  created_at: string;
  updated_at: string;
}

export const tasksApi = {
  /** 用于 WS 断线时轮询兜底 */
  get: (taskId: string) => http.get<GenerationTask>(`/tasks/${taskId}`),
};
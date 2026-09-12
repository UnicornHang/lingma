/**
 * 全局类型定义
 */

// API 错误
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// 作品
export type Genre =
  | 'fantasy'
  | 'urban'
  | 'romance'
  | 'historical'
  | 'sci_fi'
  | 'mystery'
  | 'other';

export type WorkStatus = 'draft' | 'writing' | 'finished' | 'archived';

export interface Work {
  id: string;
  title: string;
  genre: Genre;
  status: WorkStatus;
  word_count: number;
  target_word_count: number;
  logline?: string;
  style_keywords?: string[];
  created_at: string;
  updated_at: string;
}

// 章节
export type ChapterStatus = 'draft' | 'generated' | 'reviewed' | 'finalized';

export interface Chapter {
  id: string;
  work_id: string;
  title: string;
  content: Record<string, unknown>;
  plain_content: string;
  summary?: string;
  word_count: number;
  status: ChapterStatus;
  version: number;
}

// 大纲节点
export type OutlineNodeType = 'volume' | 'chapter' | 'beat';

export interface OutlineNode {
  id: string;
  work_id: string;
  parent_id?: string;
  type: OutlineNodeType;
  title: string;
  summary?: string;
  beats?: string[];
  target_word_count: number;
  order: number;
}

// 角色
export interface Character {
  id: string;
  work_id: string;
  name: string;
  role: string;
  basic_info: Record<string, unknown>;
  personality: Record<string, unknown>;
  backstory: Record<string, unknown>;
  raw_text: string;
}

// 任务状态
export type TaskStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface GenerationTask {
  id: string;
  work_id: string;
  task_type: string;
  status: TaskStatus;
  progress: number;
  error?: string;
  result?: Record<string, unknown>;
}
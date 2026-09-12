import { http } from './client';

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
  logline: string;
  style_keywords: string[];
  target_audience: string[];
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Paginated<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface WorkCreate {
  title: string;
  genre: Genre;
  logline?: string;
  target_word_count?: number;
  style_keywords?: string[];
  target_audience?: string[];
}

export type WorkUpdate = Partial<WorkCreate> & { status?: WorkStatus };

export interface WorkChaptersResponse {
  work: Work;
  total_chapters: number;
  chapters: Array<{
    id: string;
    title: string;
    status: string;
    word_count: number;
    updated_at: string;
  }>;
}

/**
 * 统一通过 `http` 调用：响应拦截器已在 client.ts 中解包成 response.data，
 * 类型层也是 Promise<T>（不是 AxiosResponse<T>），调用方不需要再 .data。
 */
export const worksApi = {
  list: (params?: { page?: number; page_size?: number; genre?: Genre; status?: WorkStatus; search?: string }) =>
    http.get<Paginated<Work>>('/works/', { params }),

  get: (id: string) =>
    http.get<Work>(`/works/${id}`),

  create: (data: WorkCreate) =>
    http.post<Work>('/works/', data),

  update: (id: string, data: WorkUpdate) =>
    http.patch<Work>(`/works/${id}`, data),

  delete: (id: string) =>
    http.delete<void>(`/works/${id}`),

  chapters: (id: string, params?: { page?: number; page_size?: number }) =>
    http.get<WorkChaptersResponse>(`/works/${id}/chapters`, { params }),
};
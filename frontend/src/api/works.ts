import { apiClient } from './client';

export interface Work {
  id: string;
  title: string;
  genre: string;
  status: string;
  word_count: number;
  target_word_count: number;
  created_at: string;
  updated_at: string;
}

export interface Paginated<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export const worksApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<Paginated<Work>>('/works/', { params }),

  get: (id: string) =>
    apiClient.get<Work>(`/works/${id}`),

  create: (data: Partial<Work>) =>
    apiClient.post<Work>('/works/', data),

  update: (id: string, data: Partial<Work>) =>
    apiClient.patch<Work>(`/works/${id}`, data),

  delete: (id: string) =>
    apiClient.delete<void>(`/works/${id}`),
};
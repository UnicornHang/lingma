import axios, { AxiosError } from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 预留：注入认证 token
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<{ error?: { code: string; message: string } }>) => {
    const message =
      error.response?.data?.error?.message || error.message || '请求失败';
    console.error('[API Error]', message);
    return Promise.reject(new Error(message));
  }
);

/**
 * 统一 API 错误
 */
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status?: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * 健康检查
 */
export async function checkHealth() {
  return apiClient.get<{
    status: string;
    version: string;
    environment: string;
    database: string;
  }>('/../');
}
import axios, { AxiosError, type AxiosRequestConfig } from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

const _client = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截器
_client.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// 响应拦截器：解包成 response.data
_client.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<{ error?: { code: string; message: string } }>) => {
    const message =
      error.response?.data?.error?.message || error.message || '请求失败';
    console.error('[API Error]', message);
    return Promise.reject(new Error(message));
  }
);

/**
 * 包装后的 HTTP 客户端 —— 运行时直接返回后端响应体（response.data 已被拦截器解包），
 * 由于 axios 的类型签名不带拦截器转换，这里用 `as unknown as Promise<T>` 强制告诉 TS：
 *  "我返回的是 T，不是 AxiosResponse<T>"。
 */
export const http = {
  get: <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    _client.get(url, config) as unknown as Promise<T>,

  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> =>
    _client.post(url, data, config) as unknown as Promise<T>,

  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> =>
    _client.patch(url, data, config) as unknown as Promise<T>,

  delete: <T = void>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    _client.delete(url, config) as unknown as Promise<T>,
};

/** 向后兼容 —— 旧 apiClient 调用方暂可继续使用 */
export const apiClient = _client;

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
 * 健康检查 —— 直接走 vite proxy 的 /health，绕开 baseURL=/api/v1
 * （使用裸 axios 实例，避免被 baseURL 拼成 /api/v1/health）
 */
export async function checkHealth() {
  const r = await axios.get<{
    status: string;
    version: string;
    environment: string;
    database: string;
    vector_store?: string;
  }>('/health');
  return r.data;
}
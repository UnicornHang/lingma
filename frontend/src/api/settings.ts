import { http } from './client';

/** Provider 列表（与后端 app.models.api_config.Provider 对齐） */
export const PROVIDERS = [
  { value: 'openai',    label: 'OpenAI',    color: '#10A37F', needsKey: true,  defaultBaseUrl: 'https://api.openai.com/v1' },
  { value: 'anthropic', label: 'Anthropic', color: '#CB785C', needsKey: true,  defaultBaseUrl: '' },
  { value: 'deepseek',  label: 'DeepSeek',  color: '#4D8AFF', needsKey: true,  defaultBaseUrl: 'https://api.deepseek.com/v1' },
  { value: 'qwen',      label: '通义千问',  color: '#FF6A00', needsKey: true,  defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { value: 'ollama',    label: 'Ollama (本地)', color: '#059669', needsKey: false, defaultBaseUrl: 'http://127.0.0.1:11434/v1' },
  { value: 'lmstudio',  label: 'LM Studio', color: '#7C3AED', needsKey: false, defaultBaseUrl: 'http://127.0.0.1:1234/v1' },
  { value: 'vllm',      label: 'vLLM',      color: '#9333EA', needsKey: false, defaultBaseUrl: 'http://127.0.0.1:8000/v1' },
  { value: 'custom',    label: '自定义',    color: '#6B7280', needsKey: false, defaultBaseUrl: '' },
] as const;

export type ProviderValue = (typeof PROVIDERS)[number]['value'];

/** Agent 列表（与后端 agents/ 一致） */
export const AGENT_TYPES = [
  { value: 'writer',    label: 'Writer（章节正文）' },
  { value: 'plot',      label: 'Plot（大纲）' },
  { value: 'world',     label: 'World（世界书）' },
  { value: 'character', label: 'Character（角色）' },
  { value: 'editor',    label: 'Editor（润色）' },
  { value: 'critic',    label: 'Critic（点评）' },
] as const;

export interface ApiConfig {
  id: string;
  name: string;
  provider: ProviderValue | string;
  masked_key: string;
  base_url: string;
  model_name: string;
  enabled: boolean;
  max_context_tokens: number;
  cost_per_1k_input: number;
  cost_per_1k_output: number;
  agent_assignments: string[];
  created_at: string;
  updated_at: string;
}

export interface ApiConfigCreate {
  name: string;
  provider: ProviderValue | string;
  api_key?: string;
  base_url?: string;
  model_name: string;
  enabled?: boolean;
  max_context_tokens?: number;
  cost_per_1k_input?: number;
  cost_per_1k_output?: number;
  agent_assignments?: string[];
}

export type ApiConfigUpdate = Partial<ApiConfigCreate>;

export const apiConfigsApi = {
  list: () => http.get<ApiConfig[]>('/settings/api-configs'),

  create: (data: ApiConfigCreate) =>
    http.post<ApiConfig>('/settings/api-configs', data),

  update: (id: string, data: ApiConfigUpdate) =>
    http.patch<ApiConfig>(`/settings/api-configs/${id}`, data),

  delete: (id: string) =>
    http.delete<void>(`/settings/api-configs/${id}`),

  /** 一次性查看明文 Key —— 后端不持久化 */
  reveal: (id: string) =>
    http.post<{ api_key: string }>(`/settings/api-configs/${id}/reveal`, {}),
};
/** [P4] Prompt 模板 API */
import { http } from './client';

export type PromptAgentType =
  | 'writer'
  | 'plot'
  | 'world'
  | 'character'
  | 'editor'
  | 'critic';

export interface PromptTemplate {
  agent_type: PromptAgentType;
  name: string;
  description: string;
  system_prompt: string;
  enabled: boolean;
  variables: string[];
  is_customized: boolean;
  updated_at: string | null;
}

export interface PromptTemplateUpdate {
  system_prompt?: string;
  enabled?: boolean;
  name?: string;
  description?: string;
}

export const promptsApi = {
  list: () =>
    http.get<{ items: PromptTemplate[] }>('/settings/prompts').then((r) => r.items),

  get: (agentType: PromptAgentType) =>
    http.get<PromptTemplate>(`/settings/prompts/${agentType}`),

  update: (agentType: PromptAgentType, data: PromptTemplateUpdate) =>
    http.patch<PromptTemplate>(`/settings/prompts/${agentType}`, data),

  reset: (agentType: PromptAgentType) =>
    http.post<PromptTemplate>(`/settings/prompts/${agentType}/reset`),
};

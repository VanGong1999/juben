/**
 * Atelier 多智能体编排 API
 */

import api, { API_BASE_URL, getAuthHeaderValue } from './api';
import { getLlmRequestOverrides } from '@/utils/llmRequest';

export type AtelierModule =
  | 'planning'
  | 'story'
  | 'plot'
  | 'character'
  | 'creation'
  | 'evaluation';

export interface AtelierConstraints {
  title?: string;
  genre?: string;
  total_episodes?: number;
  audience?: string;
  tone?: string;
  modules?: AtelierModule[] | string[];
  drama_id?: string | null;
  user_id?: string;
}

export interface AtelierStep {
  id: string;
  agent_id: string;
  title: string;
  rationale: string;
  kind?: string;
  agent_name?: string;
  category?: string;
  module?: string;
  enabled: boolean;
  status: 'pending' | 'running' | 'done' | 'skipped' | 'error' | string;
  artifact_id?: string | null;
  error?: string | null;
}

export interface AtelierPlan {
  query: string;
  constraints: AtelierConstraints;
  steps: AtelierStep[];
}

export interface AtelierRun extends AtelierPlan {
  run_id: string;
  drama_id: string;
  drama_title?: string;
  status: string;
  current_step_id?: string | null;
  created_at?: string;
  updated_at?: string;
  preflight?: boolean;
}

export const ATELIER_MODULES: Array<{
  id: AtelierModule;
  label: string;
  hint: string;
}> = [
  { id: 'planning', label: '策划', hint: '立项卖点' },
  { id: 'story', label: '故事', hint: '五元素' },
  { id: 'plot', label: '情节点', hint: '节奏转折' },
  { id: 'character', label: '人物', hint: '小传' },
  { id: 'creation', label: '样章', hint: '第1集' },
  { id: 'evaluation', label: '评估', hint: '多维打分' },
];

export async function proposeAtelierPlan(payload: {
  query: string;
  constraints?: AtelierConstraints;
}) {
  return api.post<{ success: boolean; plan: AtelierPlan }>('/juben/atelier/plan', payload);
}

export async function createAtelierRun(payload: {
  query: string;
  constraints?: AtelierConstraints;
  steps: Array<Partial<AtelierStep> & { agent_id: string; enabled: boolean }>;
}) {
  return api.post<{ success: boolean; run: AtelierRun }>('/juben/atelier/runs', payload);
}

export async function getAtelierRun(runId: string, dramaId?: string) {
  const params: Record<string, string> = {};
  if (dramaId) params.drama_id = dramaId;
  return api.get<{ success: boolean; run: AtelierRun }>(`/juben/atelier/runs/${runId}`, params);
}

export async function getAtelierRunByDrama(dramaId: string) {
  return api.get<{ success: boolean; run: AtelierRun }>(`/juben/atelier/dramas/${dramaId}/run`);
}

export async function startPreflight(dramaId: string, query?: string, force = false) {
  return api.post<{ success: boolean; run: AtelierRun }>(
    `/juben/atelier/dramas/${dramaId}/preflight`,
    { user_id: localStorage.getItem('userId') || 'default_user', query, force }
  );
}

export async function patchAtelierRun(
  runId: string,
  payload: {
    constraints?: Partial<AtelierConstraints>;
    steps?: Array<Partial<AtelierStep> & { agent_id: string; enabled?: boolean }>;
    drama_id?: string;
  }
) {
  const url = `${API_BASE_URL}/juben/atelier/runs/${runId}`;
  const auth = getAuthHeaderValue();
  const response = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(auth ? { Authorization: auth } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<{ success: boolean; run: AtelierRun }>;
}

export type AtelierStreamHandlers = {
  onEvent?: (event: string, data: any) => void;
  onChunk?: (text: string) => void;
  onComplete?: (payload: any) => void;
  onError?: (message: string) => void;
};

/**
 * 执行单步（POST SSE）
 */
export async function startAtelierStep(
  runId: string,
  stepId: string,
  payload: { drama_id?: string; user_id?: string; session_id?: string },
  handlers: AtelierStreamHandlers = {}
): Promise<void> {
  const url = `${API_BASE_URL}/juben/atelier/runs/${runId}/steps/${stepId}/start`;
  const auth = getAuthHeaderValue();
  const llm = getLlmRequestOverrides();
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(auth ? { Authorization: auth } : {}),
    },
    body: JSON.stringify({
      drama_id: payload.drama_id,
      user_id: payload.user_id || localStorage.getItem('userId') || 'default_user',
      session_id: payload.session_id,
      ...llm,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    handlers.onError?.(text || `HTTP ${response.status}`);
    throw new Error(text || `HTTP ${response.status}`);
  }
  if (!response.body) {
    handlers.onError?.('无响应流');
    throw new Error('无响应流');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';

    for (const part of parts) {
      const line = part
        .split('\n')
        .find((l) => l.startsWith('data: '));
      if (!line) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;
      try {
        const parsed = JSON.parse(raw);
        const event = parsed.event || parsed.event_type || 'message';
        const data = parsed.data;
        handlers.onEvent?.(event, data);

        if (event === 'error') {
          const msg =
            typeof data === 'string'
              ? data
              : data?.content || data?.message || '步骤失败';
          handlers.onError?.(String(msg));
        } else if (event === 'complete') {
          handlers.onComplete?.(data);
        } else if (event === 'llm_chunk' || event === 'message') {
          const text =
            typeof data === 'string'
              ? data
              : typeof data?.content === 'string'
                ? data.content
                : '';
          if (text) handlers.onChunk?.(text);
        } else if (event === 'system' || event === 'progress') {
          const text =
            typeof data === 'string'
              ? data
              : typeof data?.content === 'string'
                ? data.content
                : '';
          if (text) handlers.onEvent?.('system', text);
        }
      } catch {
        /* ignore malformed chunk */
      }
    }
  }
}

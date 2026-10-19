import { api } from './api';

export type AgentInfraCapabilities = Record<
  string,
  { status: string; [k: string]: unknown }
>;

export async function fetchCapabilities() {
  const res = await api.get<{ success: boolean; data: AgentInfraCapabilities }>(
    '/agent-infra/capabilities'
  );
  return res.data;
}

export async function fetchAgentMetrics() {
  const res = await api.get<{ success: boolean; data: Record<string, unknown> }>(
    '/agent-infra/metrics'
  );
  return res.data;
}

export async function fetchQueueStats() {
  const res = await api.get<{ success: boolean; data: Record<string, unknown> }>(
    '/agent-infra/queue/stats'
  );
  return res.data;
}

export async function fetchRedisQueueStats() {
  const res = await api.get<{ success: boolean; data: Record<string, unknown> }>(
    '/agent-infra/queue/redis/stats'
  );
  return res.data;
}

export async function fetchSecretsCheck() {
  const res = await api.get<{ success: boolean; data: Record<string, unknown> }>(
    '/agent-infra/secrets/check'
  );
  return res.data;
}

export async function runEvalSuite(datasetPath = 'evals/agent_smoke.jsonl') {
  const res = await api.post<{ success: boolean; data: Record<string, unknown> }>(
    '/agent-infra/eval/run',
    { dataset_path: datasetPath, suite_id: 'ui' }
  );
  return res.data;
}

export async function fetchDemoDag() {
  const res = await api.get<{ success: boolean; data: Record<string, unknown> }>(
    '/agent-infra/orchestration/demo-dag'
  );
  return res.data;
}

export interface ContextPreviewMessage {
  role: string;
  content?: string;
  tool_calls?: Array<{
    id?: string;
    type?: string;
    function?: { name?: string; arguments?: string };
  }>;
  tool_call_id?: string;
  name?: string;
  [k: string]: unknown;
}

export interface ContextPreviewCacheConfig {
  enabled?: boolean;
  cache_retention?: string;
  keep_recent_messages?: number;
  compact_threshold_chars?: number;
  auto_compact?: boolean;
  pruning_mode?: string;
  tool_result_max_chars?: number;
}

export interface ContextPreviewResult {
  agent_id: string;
  agent_name?: string;
  model?: string;
  model_provider?: string;
  drama_id?: string | null;
  session_id?: string;
  query?: string;
  stable_prefix?: string;
  dynamic_suffix?: string;
  messages?: ContextPreviewMessage[];
  tools?: Record<string, unknown>[];
  drama_context_block?: string;
  cache?: {
    prompt_cache_key?: string;
    prefix_fingerprint?: string;
    extra_body?: Record<string, unknown>;
    config?: ContextPreviewCacheConfig;
  };
  stats?: {
    stable_chars?: number;
    dynamic_chars?: number;
    total_chars?: number;
    message_count?: number;
    tool_count?: number;
  };
}

export interface ContextPreviewPayload {
  agent_id: string;
  drama_id?: string | null;
  session_id?: string;
  query?: string;
  user_id?: string;
  model?: string;
  tool_names?: string[];
}

export async function fetchContextPreview(payload: ContextPreviewPayload) {
  const res = await api.post<{ success: boolean; data: ContextPreviewResult }>(
    '/agent-infra/context/preview',
    payload
  );
  return res.data;
}

/**
 * 从本地设置组装发给后端的 LLM 覆盖字段
 */

import { useSettingsStore } from '@/store/settingsStore';

export type LlmRequestOverrides = {
  model_provider?: string;
  model?: string;
  api_key?: string;
  base_url?: string;
};

export function getLlmRequestOverrides(): LlmRequestOverrides {
  const { modelProvider, model, apiKey, baseUrl } = useSettingsStore.getState();
  const out: LlmRequestOverrides = {
    model_provider: modelProvider,
    model: model || undefined,
  };
  const key = (apiKey || '').trim();
  const url = (baseUrl || '').trim();
  if (key) out.api_key = key;
  if (url) out.base_url = url;
  return out;
}

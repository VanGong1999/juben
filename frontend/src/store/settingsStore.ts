/**
 * 设置状态管理 Store - 增强版
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { Language } from '@/i18n/types';

type Theme = 'light' | 'dark';
type FontSize = 'sm' | 'md' | 'lg';

/** 根据浏览器语言自动判断默认语言：中文环境 → zh，其余 → en。 */
function detectBrowserLanguage(): Language {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return 'zh';
  const lang = (navigator.language || (navigator as any).userLanguage || 'zh').toLowerCase();
  return lang.startsWith('zh') ? 'zh' : 'en';
}
export type ModelProvider = 'deepseek' | 'zhipu' | 'openrouter' | 'openai' | 'local' | 'ollama' | 'dashscope';

export const PROVIDER_DEFAULTS: Record<
  ModelProvider,
  { baseUrl: string; model: string; label: string }
> = {
  deepseek: {
    label: 'DeepSeek',
    baseUrl: 'https://api.deepseek.com',
    model: 'deepseek-flash',
  },
  zhipu: {
    label: '智谱 AI',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    model: 'glm-4.7-flash',
  },
  openai: {
    label: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4o-mini',
  },
  openrouter: {
    label: 'OpenRouter',
    baseUrl: 'https://openrouter.ai/api/v1',
    model: 'openai/gpt-4o-mini',
  },
  dashscope: {
    label: '通义千问',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'qwen-turbo',
  },
  local: {
    label: '本地兼容',
    baseUrl: 'http://localhost:8000/v1',
    model: 'qwen2.5:7b',
  },
  ollama: {
    label: 'Ollama',
    baseUrl: 'http://localhost:11434',
    model: 'qwen2.5:7b',
  },
};

interface SettingsState {
  theme: Theme;
  model: string;
  modelProvider: ModelProvider;
  /** 用户自备 API Key（仅存本机） */
  apiKey: string;
  /** OpenAI 兼容 Base URL */
  baseUrl: string;
  streamEnabled: boolean;
  showThoughtChain: boolean;
  fontSize: FontSize;
  autoScroll: boolean;
  showTimestamp: boolean;
  enableWebSearch: boolean;
  enableKnowledgeBase: boolean;
  enableRetryOnError: boolean;
  maxRetries: number;
  memoryUserEnabled: boolean;
  memoryProjectEnabled: boolean;
  language: Language;

  // Actions
  setTheme: (theme: Theme) => void;
  setModel: (model: string) => void;
  setModelProvider: (provider: ModelProvider) => void;
  setApiKey: (key: string) => void;
  setBaseUrl: (url: string) => void;
  applyProviderDefaults: (provider: ModelProvider) => void;
  setStreamEnabled: (enabled: boolean) => void;
  setShowThoughtChain: (show: boolean) => void;
  setFontSize: (size: FontSize) => void;
  setAutoScroll: (enabled: boolean) => void;
  setShowTimestamp: (show: boolean) => void;
  setEnableWebSearch: (enabled: boolean) => void;
  setEnableKnowledgeBase: (enabled: boolean) => void;
  setEnableRetryOnError: (enabled: boolean) => void;
  setMaxRetries: (count: number) => void;
  setMemoryUserEnabled: (enabled: boolean) => void;
  setMemoryProjectEnabled: (enabled: boolean) => void;
  setLanguage: (language: Language) => void;

  // Reset
  resetSettings: () => void;
}

const defaultSettings: Omit<
  SettingsState,
  | 'setTheme'
  | 'setModel'
  | 'setModelProvider'
  | 'setApiKey'
  | 'setBaseUrl'
  | 'applyProviderDefaults'
  | 'setStreamEnabled'
  | 'setShowThoughtChain'
  | 'setFontSize'
  | 'setAutoScroll'
  | 'setShowTimestamp'
  | 'setEnableWebSearch'
  | 'setEnableKnowledgeBase'
  | 'setEnableRetryOnError'
  | 'setMaxRetries'
  | 'setMemoryUserEnabled'
  | 'setMemoryProjectEnabled'
  | 'setLanguage'
  | 'resetSettings'
> = {
  theme: 'light',
  model: 'deepseek-flash',
  modelProvider: 'deepseek',
  apiKey: '',
  baseUrl: PROVIDER_DEFAULTS.deepseek.baseUrl,
  streamEnabled: true,
  showThoughtChain: true,
  fontSize: 'md',
  autoScroll: true,
  showTimestamp: true,
  enableWebSearch: true,
  enableKnowledgeBase: true,
  enableRetryOnError: true,
  maxRetries: 3,
  memoryUserEnabled: true,
  memoryProjectEnabled: true,
  language: detectBrowserLanguage(),
};

export const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set) => ({
        ...defaultSettings,

        // Actions
        setTheme: (theme) => set({ theme }),
        setModel: (model) => set({ model }),
        setModelProvider: (provider) => set({ modelProvider: provider }),
        setApiKey: (apiKey) => set({ apiKey }),
        setBaseUrl: (baseUrl) => set({ baseUrl }),
        applyProviderDefaults: (provider) => {
          const d = PROVIDER_DEFAULTS[provider];
          set({
            modelProvider: provider,
            baseUrl: d.baseUrl,
            model: d.model,
          });
        },
        setStreamEnabled: (enabled) => set({ streamEnabled: enabled }),
        setShowThoughtChain: (show) => set({ showThoughtChain: show }),
        setFontSize: (size) => set({ fontSize: size }),
        setAutoScroll: (enabled) => set({ autoScroll: enabled }),
        setShowTimestamp: (show) => set({ showTimestamp: show }),
        setEnableWebSearch: (enabled) => set({ enableWebSearch: enabled }),
        setEnableKnowledgeBase: (enabled) => set({ enableKnowledgeBase: enabled }),
        setEnableRetryOnError: (enabled) => set({ enableRetryOnError: enabled }),
        setMaxRetries: (count) => set({ maxRetries: count }),
        setMemoryUserEnabled: (enabled) => set({ memoryUserEnabled: enabled }),
        setMemoryProjectEnabled: (enabled) => set({ memoryProjectEnabled: enabled }),
        setLanguage: (language) => set({ language }),

        // Reset
        resetSettings: () => set(defaultSettings),
      }),
      {
        name: 'juben-settings',
        version: 4,
        migrate: (persisted: any, version) => {
          if (!persisted || typeof persisted !== 'object') return persisted;
          const next: any = { ...persisted };
          if (version < 2) {
            next.apiKey = persisted.apiKey || '';
            next.baseUrl =
              persisted.baseUrl ||
              PROVIDER_DEFAULTS[(persisted.modelProvider as ModelProvider) || 'deepseek']
                ?.baseUrl ||
              PROVIDER_DEFAULTS.deepseek.baseUrl;
          }
          if (version < 4) {
            // 自动检测浏览器语言（用户手动切换后版本为 4，不再触发）
            next.language = detectBrowserLanguage();
          }
          return next;
        },
      }
    ),
    { name: 'SettingsStore' }
  )
);

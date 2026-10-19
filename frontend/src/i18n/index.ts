/**
 * 轻量自研 i18n — 无第三方依赖。
 * 语言状态存 settingsStore（持久化），zustand 响应式驱动切换。
 */

import { useMemo } from 'react';
import { useSettingsStore } from '@/store/settingsStore';
import type { Language } from './types';
import { zh } from './zh';
import { en } from './en';

export type { Language } from './types';

export const LANGUAGES: { value: Language; label: string }[] = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
];

type Dict = typeof zh;
const dictionaries: Record<Language, Dict> = { zh, en };

export type TFunction = (key: string, vars?: Record<string, string | number>) => string;

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (raw, name: string) => {
    const value = vars[name];
    return value === undefined ? raw : String(value);
  });
}

function lookup(dict: Dict, key: string): string | undefined {
  const parts = key.split('.');
  let node: unknown = dict;
  for (const part of parts) {
    if (node === null || typeof node !== 'object') return undefined;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === 'string' ? node : undefined;
}

/**
 * 非 hook 翻译函数。lang 缺省时读 settingsStore 当前语言。
 * 缺 key 回退中文，再回退 key 本身 —— 未迁移字符串仍为硬编码中文，天然不破坏。
 */
export function translate(
  key: string,
  lang?: Language,
  vars?: Record<string, string | number>
): string {
  const language = lang ?? useSettingsStore.getState().language;
  const dict = dictionaries[language] ?? dictionaries.zh;
  const raw = lookup(dict, key) ?? lookup(dictionaries.zh, key) ?? key;
  return interpolate(raw, vars);
}

/** 响应式翻译 hook：切语言自动重渲。 */
export function useI18n() {
  const language = useSettingsStore((s) => s.language);
  const t = useMemo<TFunction>(
    () => (key: string, vars?: Record<string, string | number>) => translate(key, language, vars),
    [language]
  );
  return { language, t };
}

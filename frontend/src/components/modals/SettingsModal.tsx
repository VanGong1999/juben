/**
 * 设置弹窗组件 - 增强版
 * 包含更多设置选项
 */

import { useUIStore } from '@/store/uiStore';
import { useSettingsStore, PROVIDER_DEFAULTS, type ModelProvider } from '@/store/settingsStore';
import { useAgents } from '@/hooks/useAgents';
import { X, Monitor, Type, Zap, Eye, RotateCcw, Globe, Database, RefreshCw, Hash, KeyRound, Link2, Languages } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getMemorySettings, updateMemorySettings } from '@/services/memoryService';
import { useI18n, LANGUAGES } from '@/i18n';

const MODELS = [
  { value: 'deepseek-flash', label: 'DeepSeek Flash', desc: '最便宜主力 (推荐)' },
  { value: 'deepseek-v4-pro', label: 'DeepSeek V4 Pro', desc: '更强推理·贵一些' },
  { value: 'deepseek-chat', label: 'DeepSeek Chat', desc: '兼容旧名' },
  { value: 'glm-4.7-flash', label: 'GLM-4.7 Flash', desc: '智谱备用' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini', desc: 'OpenAI 经济款' },
  { value: 'qwen-turbo', label: 'Qwen Turbo', desc: '通义快速' },
  { value: 'qwen2.5:7b', label: 'Qwen2.5 7B', desc: '本地常用默认' },
];

const MODEL_PROVIDERS = (Object.keys(PROVIDER_DEFAULTS) as ModelProvider[]).map((value) => ({
  value,
  label: PROVIDER_DEFAULTS[value].label,
}));

export default function SettingsModal() {
  const { settingsModalOpen, setSettingsModalOpen } = useUIStore();
  const {
    theme,
    model,
    modelProvider,
    apiKey,
    baseUrl,
    streamEnabled,
    showThoughtChain,
    fontSize,
    autoScroll,
    showTimestamp,
    enableWebSearch,
    enableKnowledgeBase,
    enableRetryOnError,
    maxRetries,
    memoryUserEnabled,
    memoryProjectEnabled,
    setTheme,
    setModel,
    setApiKey,
    setBaseUrl,
    applyProviderDefaults,
    setStreamEnabled,
    setShowThoughtChain,
    setFontSize,
    setAutoScroll,
    setShowTimestamp,
    setEnableWebSearch,
    setEnableKnowledgeBase,
    setEnableRetryOnError,
    setMaxRetries,
    setMemoryUserEnabled,
    setMemoryProjectEnabled,
    language,
    setLanguage,
    resetSettings,
  } = useSettingsStore();

  const { t } = useI18n();

  const { activeAgentData } = useAgents();
  const [localModelInput, setLocalModelInput] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [memoryEffectiveEnabled, setMemoryEffectiveEnabled] = useState(true);
  const userId = localStorage.getItem('userId') || 'default-user';
  const projectId = localStorage.getItem('projectId') || undefined;

  useEffect(() => {
    const load = async () => {
      try {
        const res = await getMemorySettings({ user_id: userId, project_id: projectId });
        if (res?.data) {
          setMemoryUserEnabled(res.data.user_enabled);
          setMemoryProjectEnabled(res.data.project_enabled);
          setMemoryEffectiveEnabled(res.data.effective_enabled);
        }
      } catch {
        setMemoryEffectiveEnabled(memoryUserEnabled && memoryProjectEnabled);
      }
    };
    load();
  }, [userId, projectId]);

  const handleToggleUserMemory = async () => {
    const next = !memoryUserEnabled;
    setMemoryUserEnabled(next);
    try {
      const res = await updateMemorySettings({ user_id: userId, project_id: projectId, user_enabled: next });
      if (res?.data) {
        setMemoryProjectEnabled(res.data.project_enabled);
        setMemoryEffectiveEnabled(res.data.effective_enabled);
      } else {
        setMemoryEffectiveEnabled(next && memoryProjectEnabled);
      }
    } catch {
      setMemoryEffectiveEnabled(next && memoryProjectEnabled);
    }
  };

  const handleToggleProjectMemory = async () => {
    const next = !memoryProjectEnabled;
    setMemoryProjectEnabled(next);
    try {
      const res = await updateMemorySettings({ user_id: userId, project_id: projectId, project_enabled: next });
      if (res?.data) {
        setMemoryUserEnabled(res.data.user_enabled);
        setMemoryEffectiveEnabled(res.data.effective_enabled);
      } else {
        setMemoryEffectiveEnabled(memoryUserEnabled && next);
      }
    } catch {
      setMemoryEffectiveEnabled(memoryUserEnabled && next);
    }
  };

  useEffect(() => {
    if (modelProvider === 'local' || modelProvider === 'ollama') {
      setLocalModelInput(model);
    }
  }, [modelProvider, model]);

  if (!settingsModalOpen) return null;

  return (
    <>
      {/* 遮罩 */}
      <div
        className="fixed inset-0 bg-black/50 z-50 animate-fade-in"
        onClick={() => setSettingsModalOpen(false)}
      />

      {/* 弹窗 */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg animate-scale-in max-h-[90vh] overflow-y-auto">
          {/* 头部 */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white z-10">
            <h2 className="text-lg font-semibold">{t('settings.title')}</h2>
            <button
              onClick={() => setSettingsModalOpen(false)}
              className="p-2 rounded-lg hover:bg-gray-100 hover-scale icon-rotate transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 当前Agent信息 */}
          {activeAgentData && (
            <div className="mx-6 mt-4 p-4 bg-gray-50 rounded-lg">
              <div className="flex items-start gap-3">
                <span className="text-3xl">{activeAgentData.icon}</span>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">{activeAgentData.displayName}</h3>
                  <p className="text-sm text-gray-500 mt-1">{activeAgentData.description}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs px-2 py-0.5 bg-white text-gray-600 rounded">
                      {activeAgentData.category}
                    </span>
                    <span className="text-xs text-gray-400">{t('settings.model')}: {activeAgentData.model}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 内容 */}
          <div className="p-6 space-y-6">
            {/* 语言 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Languages className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">{t('settings.language')}</label>
              </div>
              <div className="flex gap-2">
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang.value}
                    type="button"
                    onClick={() => setLanguage(lang.value)}
                    className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all hover-scale ${
                      language === lang.value
                        ? 'border-gray-900 bg-gray-50 shadow-sm'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 模型提供商 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Hash className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">{t('settings.modelProvider')}</label>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {MODEL_PROVIDERS.map((provider) => (
                  <button
                    key={provider.value}
                    type="button"
                    onClick={() => applyProviderDefaults(provider.value)}
                    className={`px-3 py-2 text-sm rounded-lg border-2 transition-all hover-scale ${
                      modelProvider === provider.value
                        ? 'border-gray-900 bg-gray-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {provider.label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500">
                {t('settings.modelProviderHint')}
              </p>
            </div>

            {/* API Key + Base URL */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">{t('settings.apiKey')}</label>
              </div>
              <div className="flex gap-2">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={t('settings.apiKeyPlaceholder')}
                  className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-black font-mono"
                  autoComplete="off"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey((v) => !v)}
                  className="px-3 py-2 text-xs rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
                >
                  {showApiKey ? t('settings.hide') : t('settings.show')}
                </button>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <Link2 className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">{t('settings.baseUrl')}</label>
              </div>
              <input
                type="url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1"
                className="w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-black font-mono"
              />
              <p className="text-xs text-gray-500">
                {t('settings.keyHint')}
              </p>
            </div>

            {/* 模型选择 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">{t('settings.model')}</label>
              </div>
              <select
                value={MODELS.some((m) => m.value === model) ? model : '__custom__'}
                onChange={(e) => {
                  if (e.target.value !== '__custom__') setModel(e.target.value);
                }}
                className="w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-black input-focus-effect transition-all"
              >
                {MODELS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label} - {m.desc}
                  </option>
                ))}
                <option value="__custom__">{t('settings.customModel')}</option>
              </select>
              <input
                value={localModelInput || model}
                onChange={(e) => {
                  setLocalModelInput(e.target.value);
                  setModel(e.target.value);
                }}
                placeholder="模型 ID，如 glm-4.7-flash / gpt-4o-mini / qwen2.5:7b"
                className="w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-black font-mono"
              />
            </div>

            {/* 主题 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Monitor className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">{t('settings.theme')}</label>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setTheme('light')}
                  className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all hover-scale ${
                    theme === 'light'
                      ? 'border-gray-900 bg-gray-50 shadow-sm'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {t('settings.light')}
                </button>
                <button
                  onClick={() => setTheme('dark')}
                  className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all hover-scale ${
                    theme === 'dark'
                      ? 'border-gray-900 bg-gray-50 shadow-sm'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {t('settings.dark')}
                </button>
              </div>
            </div>

            {/* 字体大小 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Type className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">{t('settings.fontSize')}</label>
              </div>
              <div className="flex gap-2">
                {(['sm', 'md', 'lg'] as const).map((size) => (
                  <button
                    key={size}
                    onClick={() => setFontSize(size)}
                    className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all hover-scale ${
                      fontSize === size
                        ? 'border-gray-900 bg-gray-50 shadow-sm'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {size === 'sm' ? t('settings.fontSmall') : size === 'md' ? t('settings.fontMedium') : t('settings.fontLarge')}
                  </button>
                ))}
              </div>
            </div>

            {/* 开关选项 - 第一组 */}
            <div className="space-y-4">
              {/* 流式响应 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Zap className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">{t('settings.streaming')}</div>
                    <div className="text-sm text-gray-500">{t('settings.streamingDesc')}</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={streamEnabled}
                    onChange={(e) => setStreamEnabled(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setStreamEnabled(!streamEnabled)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      streamEnabled ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        streamEnabled ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 网络搜索 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Globe className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">{t('settings.webSearch')}</div>
                    <div className="text-sm text-gray-500">{t('settings.webSearchDesc')}</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={enableWebSearch}
                    onChange={(e) => setEnableWebSearch(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setEnableWebSearch(!enableWebSearch)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      enableWebSearch ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        enableWebSearch ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 知识库 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">{t('settings.knowledgeBase')}</div>
                    <div className="text-sm text-gray-500">{t('settings.knowledgeBaseDesc')}</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={enableKnowledgeBase}
                    onChange={(e) => setEnableKnowledgeBase(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setEnableKnowledgeBase(!enableKnowledgeBase)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      enableKnowledgeBase ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        enableKnowledgeBase ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 错误重试 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <RefreshCw className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">{t('settings.autoRetry')}</div>
                    <div className="text-sm text-gray-500">{t('settings.autoRetryDesc', { count: maxRetries })}</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={enableRetryOnError}
                    onChange={(e) => setEnableRetryOnError(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setEnableRetryOnError(!enableRetryOnError)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      enableRetryOnError ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        enableRetryOnError ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 显示思考链 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Eye className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">{t('settings.thoughtChain')}</div>
                    <div className="text-sm text-gray-500">{t('settings.thoughtChainDesc')}</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showThoughtChain}
                    onChange={(e) => setShowThoughtChain(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setShowThoughtChain(!showThoughtChain)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      showThoughtChain ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        showThoughtChain ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 自动滚动 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-xs">↓</span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{t('settings.autoScroll')}</div>
                    <div className="text-sm text-gray-500">{t('settings.autoScrollDesc')}</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={autoScroll}
                    onChange={(e) => setAutoScroll(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setAutoScroll(!autoScroll)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      autoScroll ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        autoScroll ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 显示时间戳 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-xs">⏱</span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{t('settings.timestamp')}</div>
                    <div className="text-sm text-gray-500">{t('settings.timestampDesc')}</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showTimestamp}
                    onChange={(e) => setShowTimestamp(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setShowTimestamp(!showTimestamp)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      showTimestamp ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        showTimestamp ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>
            </div>

            {/* 记忆开关 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">{t('settings.memory')}</label>
                <span className="text-xs text-gray-400">{t('settings.effective')}: {memoryEffectiveEnabled ? t('settings.on') : t('settings.off')}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>{t('settings.userMemory')}</span>
                <button
                  onClick={handleToggleUserMemory}
                  className={`px-3 py-1 rounded-full text-xs border ${
                    memoryUserEnabled ? 'bg-black text-white border-black' : 'bg-white text-gray-600 border-gray-200'
                  }`}
                >
                  {memoryUserEnabled ? t('settings.enabled') : t('settings.disabled')}
                </button>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>{t('settings.projectMemory')}</span>
                <button
                  onClick={handleToggleProjectMemory}
                  className={`px-3 py-1 rounded-full text-xs border ${
                    memoryProjectEnabled ? 'bg-black text-white border-black' : 'bg-white text-gray-600 border-gray-200'
                  }`}
                >
                  {memoryProjectEnabled ? t('settings.enabled') : t('settings.disabled')}
                </button>
              </div>
              {!projectId && (
                <div className="text-xs text-gray-400">{t('settings.noProjectMemory')}</div>
              )}
            </div>

            {/* 重试次数 */}
            {enableRetryOnError && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-gray-600" />
                  <label className="font-medium text-gray-900">{t('settings.maxRetries')}</label>
                </div>
                <div className="flex gap-2">
                  {[1, 2, 3, 5].map((count) => (
                    <button
                      key={count}
                      onClick={() => setMaxRetries(count)}
                      className={`flex-1 px-4 py-2 text-sm rounded-lg border-2 transition-all hover-scale ${
                        maxRetries === count
                          ? 'border-gray-900 bg-gray-50 shadow-sm'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      {count}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 底部 */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 sticky bottom-0 bg-white">
            <button
              onClick={resetSettings}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-all hover-scale icon-rotate"
            >
              <RotateCcw className="w-4 h-4" />
              {t('settings.resetSettings')}
            </button>
            <button
              onClick={() => setSettingsModalOpen(false)}
              className="px-6 py-2 text-sm text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-all hover-scale shadow-md hover:shadow-lg"
            >
              {t('common.done')}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

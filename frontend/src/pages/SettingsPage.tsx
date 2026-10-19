/**
 * 设置枢纽 — 模型凭证 · 记忆 · Skills · 工具 · 账户
 */

import { Link } from 'react-router-dom';
import {
  Brain,
  Sparkles,
  Wrench,
  Shield,
  ArrowRight,
  Cpu,
  KeyRound,
  Link2,
  Eye,
  EyeOff,
} from 'lucide-react';
import { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import { useAuthStore } from '@/store/authStore';
import {
  PROVIDER_DEFAULTS,
  useSettingsStore,
  type ModelProvider,
} from '@/store/settingsStore';
import { useI18n } from '@/i18n';
import clsx from 'clsx';

const LINKS = [
  {
    to: '/memory',
    titleKey: 'settingsPage.link.memory.title',
    descKey: 'settingsPage.link.memory.desc',
    icon: Brain,
  },
  {
    to: '/skills',
    titleKey: 'settingsPage.link.skills.title',
    descKey: 'settingsPage.link.skills.desc',
    icon: Sparkles,
  },
  {
    to: '/toolbox',
    titleKey: 'settingsPage.link.toolbox.title',
    descKey: 'settingsPage.link.toolbox.desc',
    icon: Wrench,
  },
  {
    to: '/toolbox/tokens',
    titleKey: 'settingsPage.link.tokens.title',
    descKey: 'settingsPage.link.tokens.desc',
    icon: Cpu,
  },
];

export default function SettingsPage() {
  const { user, isAdmin } = useAuthStore();
  const {
    modelProvider,
    model,
    apiKey,
    baseUrl,
    setModel,
    setApiKey,
    setBaseUrl,
    applyProviderDefaults,
  } = useSettingsStore();
  const { t } = useI18n();
  const [showKey, setShowKey] = useState(false);
  const [savedHint, setSavedHint] = useState('');

  const providers = Object.keys(PROVIDER_DEFAULTS) as ModelProvider[];

  const flashSaved = () => {
    setSavedHint(t('settingsPage.saved'));
    window.setTimeout(() => setSavedHint(''), 1600);
  };

  return (
    <AppShell title={t('settings.title')} subtitle={t('settingsPage.subtitle')}>
      <div className="px-4 sm:px-10 py-8 sm:py-12 max-w-3xl mx-auto space-y-12">
        <section className="border-b border-pearl-line pb-10">
          <div className="flex items-baseline justify-between gap-3 mb-2">
            <p className="text-[11px] tracking-[0.18em] uppercase text-ink-faint">Model</p>
            {savedHint && (
              <span className="text-[11px] text-atelier-teal animate-fade-in">{savedHint}</span>
            )}
          </div>
          <h2 className="font-display text-3xl font-semibold text-ink">{t('settingsPage.connectModel')}</h2>
          <p className="mt-3 text-sm text-ink-muted leading-relaxed">
            {t('settingsPage.connectModelDesc')}
          </p>

          <div className="mt-6 flex flex-wrap gap-2">
            {providers.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => {
                  applyProviderDefaults(p);
                  flashSaved();
                }}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs border transition-colors',
                  modelProvider === p
                    ? 'border-atelier-teal/40 bg-atelier-teal-soft text-atelier-teal font-semibold'
                    : 'border-pearl-line text-ink-muted hover:bg-pearl-soft'
                )}
              >
                {PROVIDER_DEFAULTS[p].label}
              </button>
            ))}
          </div>

          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-ink-faint">
                <KeyRound className="w-3.5 h-3.5" />
                API Key
              </span>
              <div className="mt-1.5 flex gap-2">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value);
                    flashSaved();
                  }}
                  placeholder={t('settingsPage.apiKeyPlaceholder')}
                  className="flex-1 rounded-xl border border-pearl-line bg-white px-3 py-2.5 text-sm font-mono text-ink outline-none focus:border-atelier-teal"
                  autoComplete="off"
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setShowKey((v) => !v)}
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </label>

            <label className="block">
              <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-ink-faint">
                <Link2 className="w-3.5 h-3.5" />
                Base URL
              </span>
              <input
                type="url"
                value={baseUrl}
                onChange={(e) => {
                  setBaseUrl(e.target.value);
                  flashSaved();
                }}
                placeholder="https://open.bigmodel.cn/api/paas/v4"
                className="mt-1.5 w-full rounded-xl border border-pearl-line bg-white px-3 py-2.5 text-sm font-mono text-ink outline-none focus:border-atelier-teal"
              />
            </label>

            <label className="block">
              <span className="text-[11px] uppercase tracking-wider text-ink-faint">{t('settingsPage.modelId')}</span>
              <input
                value={model}
                onChange={(e) => {
                  setModel(e.target.value);
                  flashSaved();
                }}
                placeholder="glm-4.7-flash"
                className="mt-1.5 w-full rounded-xl border border-pearl-line bg-white px-3 py-2.5 text-sm font-mono text-ink outline-none focus:border-atelier-teal"
              />
            </label>
          </div>

          <div className="mt-5 rounded-xl border border-pearl-line/80 bg-pearl-soft/50 px-4 py-3 text-xs text-ink-muted leading-relaxed">
            {t('settingsPage.current')}
            <span className="font-mono text-atelier-teal mx-1">{modelProvider}</span>·
            <span className="font-mono text-atelier-teal mx-1">{model}</span>
            {apiKey ? ` · ${t('settingsPage.keyConfigured')}` : ` · ${t('settingsPage.serverKey')}`}
          </div>
        </section>

        <section>
          <h3 className="font-display text-2xl font-semibold text-ink mb-4">{t('settingsPage.capabilities')}</h3>
          <ul className="border-t border-pearl-line">
            {LINKS.map((item) => (
              <li key={item.to} className="border-b border-pearl-line">
                <Link
                  to={item.to}
                  className="flex items-start gap-4 py-4 hover:bg-pearl-soft/50 -mx-1 px-1 transition-colors group"
                >
                  <div className="w-9 h-9 rounded-md bg-pearl-soft text-atelier-teal flex items-center justify-center shrink-0">
                    <item.icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-ink">{t(item.titleKey)}</div>
                    <p className="text-sm text-ink-muted mt-0.5">{t(item.descKey)}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-ink-faint mt-2 group-hover:text-atelier-teal" />
                </Link>
              </li>
            ))}
            {isAdmin() && (
              <li className="border-b border-pearl-line">
                <Link
                  to="/admin"
                  className="flex items-start gap-4 py-4 hover:bg-pearl-soft/50 -mx-1 px-1 transition-colors group"
                >
                  <div className="w-9 h-9 rounded-md bg-pearl-soft text-atelier-teal flex items-center justify-center shrink-0">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-ink">{t('nav.admin')}</div>
                    <p className="text-sm text-ink-muted mt-0.5">{t('settingsPage.adminDesc')}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-ink-faint mt-2 group-hover:text-atelier-teal" />
                </Link>
              </li>
            )}
          </ul>
        </section>

        <section className="border-t border-pearl-line pt-8">
          <h3 className="font-display text-2xl font-semibold text-ink mb-2">{t('settingsPage.account')}</h3>
          <p className="text-sm text-ink-muted">
            {t('settingsPage.currentUser')}<span className="text-ink font-medium">{user?.username || t('nav.creator')}</span>
          </p>
          <p className="text-xs text-ink-faint mt-2">
            {t('settingsPage.accountHint')}
          </p>
        </section>
      </div>
    </AppShell>
  );
}

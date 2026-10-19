/**
 * 上下文预览 — 离线查看「真正发给 LLM 的完整上下文」
 * Prompt 组装 · 缓存元数据 · 作品上下文（不调 LLM、不产生费用）
 */

import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Eye, Play, ChevronDown, ChevronRight, KeyRound } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import Skeleton from '@/components/common/Skeleton';
import { ErrorCard } from '@/components/common/ErrorHandling';
import { EmptyState } from '@/components/common/EmptyState';
import { getAgents } from '@/services/agentService';
import { listDramas, type DramaMeta } from '@/services/dramaService';
import {
  fetchContextPreview,
  type ContextPreviewResult,
  type ContextPreviewMessage,
} from '@/services/agentInfraService';
import { AGENTS_CONFIG } from '@/config/agents';
import { useI18n } from '@/i18n';
import clsx from 'clsx';

type AgentOption = { id: string; displayName: string };

const ROLE_UI: Record<
  string,
  { label: string; badge: string; border: string; accent: string }
> = {
  system: { label: 'system', badge: 'bg-sky-100 text-sky-700', border: 'border-sky-200', accent: 'text-sky-700' },
  user: { label: 'user', badge: 'bg-ink text-white', border: 'border-stone-300', accent: 'text-ink' },
  assistant: { label: 'assistant', badge: 'bg-pearl-soft text-ink-muted', border: 'border-pearl-line', accent: 'text-ink-muted' },
  tool: { label: 'tool', badge: 'bg-slate-100 text-slate-700', border: 'border-slate-200', accent: 'text-slate-700' },
  unknown: { label: 'unknown', badge: 'bg-stone-100 text-stone-600', border: 'border-stone-200', accent: 'text-stone-600' },
};

function MessageRow({ m, index }: { m: ContextPreviewMessage; index: number }) {
  const [open, setOpen] = useState(false);
  const role = m.role || 'unknown';
  const ui = ROLE_UI[role] || ROLE_UI.unknown;
  const content = m.content != null ? String(m.content) : '';
  const toolCalls = Array.isArray(m.tool_calls) ? m.tool_calls : [];

  return (
    <div className={clsx('rounded-lg border bg-white/60', ui.border)}>
      <div className="flex items-start gap-2 px-3 py-2">
        <span className="mt-0.5 shrink-0 font-mono text-[10px] text-ink-faint">#{index + 1}</span>
        <span className={clsx('shrink-0 rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase', ui.badge)}>
          {ui.label}
        </span>
        {m.name && <code className="text-[10px] font-mono text-ink-faint">{m.name}</code>}
        {m.tool_call_id && (
          <code className="truncate text-[10px] font-mono text-ink-faint" title={m.tool_call_id}>
            {m.tool_call_id}
          </code>
        )}
        {toolCalls.length > 0 && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="ml-auto inline-flex shrink-0 items-center gap-1 text-[10px] font-medium text-amber-700 hover:text-amber-900"
          >
            {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            tool_calls ({toolCalls.length})
          </button>
        )}
      </div>
      {content && (
        <pre className="whitespace-pre-wrap px-3 pb-2.5 font-mono text-[11px] leading-relaxed text-ink-muted">
          {content}
        </pre>
      )}
      {open &&
        toolCalls.map((tc, i) => {
          const fn = tc.function || {};
          const name = fn.name || '?';
          const args = fn.arguments || '';
          let pretty = args;
          try {
            pretty = JSON.stringify(JSON.parse(args), null, 2);
          } catch {
            pretty = args;
          }
          return (
            <div key={i} className="mx-3 mb-2 rounded-md border border-amber-200 bg-amber-50/40 px-2 py-1.5">
              <code className="text-[10px] font-mono font-semibold text-amber-800">{name}</code>
              <pre className="mt-1 overflow-auto whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-amber-900/80">
                {pretty}
              </pre>
            </div>
          );
        })}
    </div>
  );
}

export default function ContextPreviewPage() {
  const { t } = useI18n();
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [dramas, setDramas] = useState<DramaMeta[]>([]);
  const [agentId, setAgentId] = useState('auto');
  const [dramaId, setDramaId] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<ContextPreviewResult | null>(null);

  useEffect(() => {
    getAgents()
      .then((list) =>
        setAgents(
          (list || []).map((a) => ({
            id: a.id,
            displayName: a.displayName || a.name || a.id,
          }))
        )
      )
      .catch(() =>
        setAgents(
          AGENTS_CONFIG.map((a) => ({ id: a.id, displayName: a.displayName || a.name || a.id }))
        )
      );
    listDramas()
      .then((r) => setDramas(Array.isArray(r.dramas) ? r.dramas : []))
      .catch(() => setDramas([]));
  }, []);

  const run = async () => {
    if (!agentId) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await fetchContextPreview({
        agent_id: agentId,
        drama_id: dramaId || null,
        session_id: sessionId || undefined,
        query,
      });
      setResult(data);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const threshold = result?.cache?.config?.compact_threshold_chars ?? 24000;
  const stats = result?.stats;
  const cache = result?.cache;

  const statCards = useMemo(() => {
    const key = cache?.prompt_cache_key || '';
    return [
      { label: t('toolbox.contextPreview.stat.stableChars'), value: stats?.stable_chars ?? 0, mono: true },
      { label: t('toolbox.contextPreview.stat.dynamicChars'), value: stats?.dynamic_chars ?? 0, mono: true },
      { label: t('toolbox.contextPreview.stat.totalChars'), value: stats?.total_chars ?? 0, mono: true, budget: threshold },
      { label: t('toolbox.contextPreview.stat.messageCount'), value: stats?.message_count ?? 0, mono: true },
      { label: t('toolbox.contextPreview.stat.toolCount'), value: stats?.tool_count ?? 0, mono: true },
      { label: t('toolbox.contextPreview.stat.cacheKey'), value: key ? key.slice(0, 8) : '—', mono: true, hint: key },
    ];
  }, [stats, cache, threshold, t]);

  const charBudget = (n: number, max: number) => (
    <span className={clsx('text-[10px]', n > max * 0.9 ? 'text-amber-700' : 'text-ink-faint')}>
      {n.toLocaleString()}/{max.toLocaleString()}
    </span>
  );

  const cacheConfig = cache?.config;
  const cacheRows: Array<[string, unknown]> = [
    ['enabled', cacheConfig?.enabled],
    ['cache_retention', cacheConfig?.cache_retention],
    ['keep_recent_messages', cacheConfig?.keep_recent_messages],
    ['compact_threshold_chars', cacheConfig?.compact_threshold_chars],
    ['auto_compact', cacheConfig?.auto_compact],
    ['pruning_mode', cacheConfig?.pruning_mode],
    ['tool_result_max_chars', cacheConfig?.tool_result_max_chars],
  ];

  return (
    <AppShell
      title={t('toolbox.contextPreview.title')}
      subtitle={t('toolbox.contextPreview.subtitle')}
      actions={
        <Link to="/toolbox" className="btn btn-ghost btn-sm inline-flex items-center gap-1">
          <ArrowLeft className="h-3.5 w-3.5" />
          {t('toolbox.back')}
        </Link>
      }
    >
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-6">
        {/* 输入区 */}
        <section className="glass-panel p-5">
          <div className="mb-3 flex items-center gap-2">
            <Eye className="h-4 w-4 text-studio-teal" />
            <h2 className="font-display text-base font-semibold text-ink">{t('toolbox.contextPreview.offline')}</h2>
            <span className="text-xs text-ink-faint">{t('toolbox.contextPreview.offlineHint')}</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="text-xs text-ink-muted">
              Agent
              <select
                className="input mt-1 w-full"
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
              >
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.displayName} ({a.id})
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-ink-muted">
              {t('toolbox.contextPreview.workOptional')}
              <select
                className="input mt-1 w-full"
                value={dramaId}
                onChange={(e) => setDramaId(e.target.value)}
              >
                <option value="">{t('toolbox.contextPreview.noContext')}</option>
                {dramas.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title || d.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-ink-muted">
              {t('toolbox.contextPreview.sessionOptional')}
              <input
                className="input mt-1 w-full font-mono text-xs"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                placeholder={`preview-${agentId || 'auto'}`}
              />
            </label>
            <div className="flex items-end">
              <button
                type="button"
                className="btn btn-primary btn-sm inline-flex w-full items-center justify-center gap-1.5"
                disabled={loading || !agentId}
                onClick={run}
              >
                <Play className="h-3.5 w-3.5" />
                {loading ? t('toolbox.contextPreview.assembling') : t('toolbox.contextPreview.preview')}
              </button>
            </div>
          </div>
          <label className="mt-3 block text-xs text-ink-muted">
            query
            <textarea
              className="input mt-1 min-h-[64px] w-full"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('toolbox.contextPreview.queryExample')}
            />
          </label>
        </section>

        {error && <ErrorCard error={error} />}

        {loading && (
          <div className="space-y-4">
            <Skeleton type="text" lines={4} />
            <div className="grid gap-4 lg:grid-cols-2">
              <Skeleton type="card" />
              <Skeleton type="card" />
            </div>
          </div>
        )}

        {!loading && !error && !result && (
          <EmptyState
            icon={Eye}
            title={t('toolbox.contextPreview.emptyTitle')}
            description={t('toolbox.contextPreview.emptyDesc')}
            size="sm"
          />
        )}

        {!loading && !error && result && (
          <div className="space-y-6">
            {/* 统计卡片 */}
            <section className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {statCards.map((c) => (
                <div key={c.label} className="surface-panel p-3">
                  <div className="text-[10px] uppercase tracking-wider text-ink-faint">{c.label}</div>
                  <div
                    className={clsx('mt-1 truncate font-display text-xl font-semibold text-ink', c.mono && 'font-mono text-base')}
                    title={c.hint}
                  >
                    {typeof c.value === 'number' ? c.value.toLocaleString() : c.value}
                  </div>
                  {c.budget && (
                    <div className="mt-1">{charBudget(c.value as number, c.budget)}</div>
                  )}
                </div>
              ))}
            </section>

            {/* 主区两栏 */}
            <div className="grid gap-6 lg:grid-cols-2">
              {/* 左栏：Prompt 组装 */}
              <div className="space-y-4">
                <section className="surface-panel p-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 rounded border border-emerald-200 bg-emerald-50/60 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                      Stable Prefix
                    </span>
                    {charBudget(stats?.stable_chars ?? 0, threshold)}
                  </div>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-stone-950 p-3 text-[11px] leading-relaxed text-stone-100">
                    {result.stable_prefix || t('toolbox.contextPreview.empty')}
                  </pre>
                </section>

                <section className="surface-panel p-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 rounded border border-amber-200 bg-amber-50/60 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                      Dynamic Suffix
                    </span>
                    {charBudget(stats?.dynamic_chars ?? 0, threshold)}
                  </div>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-stone-950 p-3 text-[11px] leading-relaxed text-stone-100">
                    {result.dynamic_suffix || t('toolbox.contextPreview.empty')}
                  </pre>
                </section>

                <section className="surface-panel p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="font-display text-sm font-semibold text-ink">{t('toolbox.contextPreview.messages')}</h3>
                    <span className="text-[10px] text-ink-faint">{stats?.message_count ?? 0} {t('toolbox.contextPreview.countUnit')}</span>
                  </div>
                  <div className="space-y-2">
                    {(result.messages || []).map((m, i) => (
                      <MessageRow key={i} m={m} index={i} />
                    ))}
                  </div>
                </section>
              </div>

              {/* 右栏：元数据 */}
              <div className="space-y-4">
                <section className="surface-panel p-4">
                  <h3 className="mb-3 font-display text-sm font-semibold text-ink">{t('toolbox.contextPreview.cacheMeta')}</h3>
                  <div className="space-y-2">
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-ink-faint">prompt_cache_key</div>
                      <code className="break-all font-mono text-[11px] text-ink">
                        {cache?.prompt_cache_key || '—'}
                      </code>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-ink-faint">prefix_fingerprint</div>
                      <code className="break-all font-mono text-[11px] text-ink">
                        {cache?.prefix_fingerprint || '—'}
                      </code>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-ink-faint">extra_body</div>
                      <pre className="mt-1 overflow-auto rounded-md bg-stone-950 p-3 font-mono text-[11px] leading-relaxed text-stone-100">
                        {JSON.stringify(cache?.extra_body ?? {}, null, 2)}
                      </pre>
                    </div>
                  </div>
                </section>

                <section className="surface-panel p-4">
                  <h3 className="mb-3 font-display text-sm font-semibold text-ink">{t('toolbox.contextPreview.cacheConfig')}</h3>
                  <dl className="space-y-1.5 text-sm">
                    {cacheRows.map(([k, v]) => (
                      <div key={k} className="flex items-center justify-between gap-3 border-b border-pearl-line py-1">
                        <dt className="font-mono text-[11px] text-ink-faint">{k}</dt>
                        <dd className="font-mono text-[11px] text-ink">{String(v ?? '—')}</dd>
                      </div>
                    ))}
                  </dl>
                </section>

                <section className="surface-panel p-4">
                  <h3 className="mb-2 flex items-center gap-1.5 font-display text-sm font-semibold text-ink">
                    <KeyRound className="h-3.5 w-3.5 text-studio-amber" />
                    {t('toolbox.contextPreview.workContextBlock')}
                  </h3>
                  <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md bg-stone-950 p-3 text-[11px] leading-relaxed text-stone-100">
                    {result.drama_context_block || t('toolbox.contextPreview.noWorkContext')}
                  </pre>
                </section>

                <ToolsSchema tools={result.tools || []} />
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function ToolsSchema({ tools }: { tools: Record<string, unknown>[] }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const { t } = useI18n();
  return (
    <section className="surface-panel p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold text-ink">{t('toolbox.contextPreview.toolsSchema')}</h3>
        <span className="text-[10px] text-ink-faint">{tools.length} {t('toolbox.contextPreview.toolUnit')}</span>
      </div>
      {tools.length === 0 ? (
        <p className="text-xs text-ink-muted">{t('toolbox.contextPreview.noTools')}</p>
      ) : (
        <ul className="space-y-1">
          {tools.map((t, i) => {
            const fn = (t.function as Record<string, unknown>) || {};
            const name = String(fn.name || t.name || `tool_${i}`);
            const isOpen = open[name] ?? false;
            return (
              <li key={name} className="rounded-md border border-pearl-line">
                <button
                  type="button"
                  onClick={() => setOpen((m) => ({ ...m, [name]: !isOpen }))}
                  className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left hover:bg-paper-cool/50"
                >
                  {isOpen ? (
                    <ChevronDown className="h-3 w-3 shrink-0 text-ink-faint" />
                  ) : (
                    <ChevronRight className="h-3 w-3 shrink-0 text-ink-faint" />
                  )}
                  <code className="truncate font-mono text-[11px] text-ink">{name}</code>
                </button>
                {isOpen && (
                  <pre className="mx-2 mb-2 overflow-auto rounded bg-ink/[0.03] p-2 font-mono text-[10px] leading-relaxed text-ink-muted">
                    {JSON.stringify(t, null, 2)}
                  </pre>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

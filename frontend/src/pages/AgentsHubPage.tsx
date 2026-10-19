/**
 * 专家目录 — 杂志式按流水线阶段分组
 * 工具类能力改为 Agent Tools，不再冒充专家
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, ArrowRight, ChevronDown, Wrench } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { useAgentStore } from '@/store/agentStore';
import {
  AGENTS_CONFIG,
  groupAgentsByPipelineStage,
  resolveNavTier,
  type PipelineStage,
} from '@/config/agents';
import { EXTERNAL_TOOLS, PREBUILT_TOOLS, type ToolDefinitionUI } from '@/config/tools';
import clsx from 'clsx';
import { useI18n } from '@/i18n';

export default function AgentsHubPage() {
  const { t } = useI18n();
  const { agents: loaded, setActiveAgent } = useAgentStore();
  const agents = useMemo(() => {
    const src = loaded.length > 0 ? loaded : AGENTS_CONFIG;
    return src.filter((a) => resolveNavTier(a) !== 'utility');
  }, [loaded]);
  const [q, setQ] = useState('');
  const [showTools, setShowTools] = useState(false);

  const filtered = useMemo(() => {
    if (!q.trim()) return agents;
    const lower = q.toLowerCase();
    return agents.filter(
      (a) =>
        a.displayName.toLowerCase().includes(lower) ||
        a.description.toLowerCase().includes(lower) ||
        (a.features || []).some((f) => f.toLowerCase().includes(lower))
    );
  }, [agents, q]);

  const primaryGroups = useMemo(
    () => groupAgentsByPipelineStage(filtered, { includeUtility: false }),
    [filtered]
  );

  const toolQuery = q.trim().toLowerCase();
  const filteredTools = useMemo(() => {
    const all = [...EXTERNAL_TOOLS, ...PREBUILT_TOOLS];
    if (!toolQuery) return all;
    return all.filter(
      (t) =>
        t.label.toLowerCase().includes(toolQuery) ||
        t.name.toLowerCase().includes(toolQuery) ||
        t.description.toLowerCase().includes(toolQuery)
    );
  }, [toolQuery]);

  const openStudio = (id: string) => {
    setActiveAgent(id);
  };

  const renderGroup = (stage: PipelineStage, list: typeof agents) => (
    <section key={stage} className="border-t border-pearl-line pt-8 first:border-t-0 first:pt-0">
      <h3 className="font-display text-2xl font-semibold text-ink mb-1">{stage}</h3>
      <p className="text-[11px] text-ink-faint mb-5 uppercase tracking-wider">{t('admin.experts.expertCount', { count: list.length })}</p>
      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {list.map((agent) => {
          const isCore = resolveNavTier(agent) === 'core';
          return (
            <Link
              key={agent.id}
              to={`/studio?agent=${agent.id}`}
              onClick={() => openStudio(agent.id)}
              className="group flex flex-col rounded-2xl border border-pearl-line bg-white/60 p-4 hover:border-atelier-teal/40 hover:bg-white hover:shadow-atelier transition-all duration-200"
            >
              <div className="flex items-start gap-3">
                <div className="text-2xl w-9 h-9 shrink-0 flex items-center justify-center rounded-lg bg-pearl-soft">
                  {agent.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-ink truncate">{agent.displayName}</span>
                    {isCore && (
                      <span className="shrink-0 text-[9px] px-1.5 py-0.5 rounded-full bg-atelier-teal-soft text-atelier-teal">
                        {t('admin.experts.core')}
                      </span>
                    )}
                  </div>
                  <code className="text-[10px] text-ink-faint font-mono">{agent.id}</code>
                </div>
              </div>

              <p className="mt-3 text-xs text-ink-muted leading-relaxed line-clamp-3">
                {agent.description}
              </p>

              {(agent.features?.length ?? 0) > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {agent.features.slice(0, 4).map((f) => (
                    <span
                      key={f}
                      className="text-[9px] px-1.5 py-0.5 rounded bg-pearl-soft text-ink-muted"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              )}

              {(agent.capabilities?.length ?? 0) > 0 && (
                <ul className="mt-3 space-y-1">
                  {agent.capabilities.slice(0, 3).map((c) => (
                    <li key={c} className="flex items-start gap-1.5 text-[11px] text-ink-muted">
                      <span className="mt-[5px] w-1 h-1 rounded-full bg-atelier-teal/50 shrink-0" />
                      <span className="line-clamp-1">{c}</span>
                    </li>
                  ))}
                </ul>
              )}

              <div className="mt-auto pt-4 flex items-center justify-between">
                <span className="text-[10px] text-ink-faint font-mono">{agent.model}</span>
                <span className="inline-flex items-center gap-1 text-xs font-medium text-atelier-teal group-hover:underline">
                  {t('admin.experts.enterStudio')}
                  <ArrowRight className="w-3 h-3" />
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );

  const renderToolCard = (tool: ToolDefinitionUI) => {
    const requiredParams = tool.parameters?.required || [];
    return (
      <div
        key={tool.name}
        className="flex flex-col rounded-2xl border border-pearl-line bg-white/60 p-4 hover:border-atelier-teal/40 hover:bg-white transition-all duration-200"
      >
        <div className="flex items-start gap-3">
          <div className="text-xl w-8 h-8 shrink-0 flex items-center justify-center rounded-lg bg-pearl-soft">
            {tool.icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-semibold text-ink truncate">{tool.label}</span>
              {tool.category === 'prebuilt' && (
                <span className="text-[9px] uppercase tracking-wider text-ink-faint">prebuilt</span>
              )}
              {tool.dangerous && (
                <span className="text-[9px] text-studio-amber">{t('admin.experts.restricted')}</span>
              )}
            </div>
            <code className="text-[10px] text-ink-faint font-mono">{tool.name}</code>
          </div>
        </div>

        <p className="mt-3 text-xs text-ink-muted leading-relaxed line-clamp-2">
          {tool.description}
        </p>

        {requiredParams.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {requiredParams.map((r) => (
              <span
                key={r}
                className="text-[9px] px-1.5 py-0.5 rounded bg-pearl-soft text-ink-muted font-mono"
              >
                {r}
              </span>
            ))}
          </div>
        )}

        <div className="mt-auto pt-4">
          <Link
            to={`/toolbox/agent-tools?tool=${tool.name}`}
            className="inline-flex items-center gap-1 text-xs font-medium text-atelier-teal hover:underline"
          >
            {t('admin.experts.view')}
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    );
  };

  return (
    <AppShell
      title={t('nav.experts')}
      subtitle={t('admin.experts.subtitle')}
      actions={
        <Link to="/studio" className="btn btn-primary btn-sm">
          {t('dashboard.openStudio')}
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      }
    >
      <div className="px-4 sm:px-8 lg:px-10 py-8 sm:py-12 max-w-6xl mx-auto space-y-10">
        <header className="border-b border-pearl-line pb-8">
          <p className="text-[11px] tracking-[0.18em] uppercase text-ink-faint mb-2">Directory</p>
          <h2 className="font-display text-3xl sm:text-4xl font-semibold text-ink leading-tight">
            {t('admin.experts.directoryTitle')}
          </h2>
          <p className="mt-3 text-sm text-ink-muted max-w-lg">
            {t('admin.experts.directoryDesc')}
          </p>
          <div className="relative mt-6 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-faint" />
            <input
              className="input pl-10"
              placeholder={t('admin.experts.searchPlaceholder')}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
        </header>

        <div className="space-y-10">
          {primaryGroups.map(({ stage, agents: list }) => renderGroup(stage, list))}
        </div>

        <section className="border-t border-pearl-line pt-6">
          <button
            type="button"
            onClick={() => setShowTools((v) => !v)}
            className="flex items-center gap-2 text-sm font-medium text-ink-muted hover:text-ink"
          >
            <ChevronDown className={clsx('w-4 h-4 transition-transform', showTools && 'rotate-180')} />
            <Wrench className="w-3.5 h-3.5" />
            {t('admin.experts.toolSection', { count: filteredTools.length })}
          </button>
          <p className="mt-2 text-xs text-ink-faint max-w-md">
            {t('admin.experts.toolSectionDesc')}
          </p>
          {showTools && (
            <div className="mt-4 grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredTools.map(renderToolCard)}
            </div>
          )}
          <div className="mt-3">
            <Link
              to="/toolbox/agent-tools"
              className="text-xs text-atelier-teal hover:underline inline-flex items-center gap-1"
            >
              {t('admin.experts.openTools')}
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

/**
 * 左侧创作蓝图 — 默认只露核心专家，可展开更多
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Sparkles, Clapperboard, ChevronDown } from 'lucide-react';
import clsx from 'clsx';
import { useAgentStore } from '@/store/agentStore';
import {
  AGENTS_CONFIG,
  getCoreAgents,
  resolveNavTier,
  resolvePipelineStage,
  resolveProductLine,
  type AgentConfig,
  type PipelineStage,
  type ProductLine,
} from '@/config/agents';
import { useI18n } from '@/i18n';

const STAGE_FILTERS: { id: PipelineStage | 'all'; label: string }[] = [
  { id: 'all', label: 'common.all' },
  { id: '策划', label: 'workspace.category.planning' },
  { id: '故事', label: 'workspace.category.story' },
  { id: '情节点', label: 'workspace.category.analysis' },
  { id: '人物', label: 'workspace.category.character' },
  { id: '创作', label: 'workspace.category.creation' },
  { id: '评估', label: 'workspace.category.evaluation' },
];

function AgentRow({
  agent,
  active,
  onSelect,
}: {
  agent: AgentConfig;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={clsx(
        'w-full text-left rounded-md px-2 py-1.5 border transition-colors',
        active
          ? 'border-atelier-teal/40 bg-atelier-teal-soft'
          : 'border-transparent hover:bg-pearl-soft'
      )}
    >
      <div className="flex items-start gap-2">
        <span className="text-xs leading-none mt-0.5 w-6 h-6 rounded bg-pearl-card border border-pearl-line flex items-center justify-center shrink-0">
          {agent.icon || '✦'}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[12px] font-semibold text-ink truncate leading-tight">{agent.displayName}</div>
          <p className="text-[10px] text-ink-muted line-clamp-1 mt-0.5 leading-snug">{agent.description}</p>
        </div>
      </div>
    </button>
  );
}

export default function AgentBlueprintRail({
  productLines,
}: {
  productLines?: ProductLine[];
}) {
  const { t } = useI18n();
  const { agents: loaded, activeAgent, setActiveAgent } = useAgentStore();
  const agents = loaded.length > 0 ? loaded : AGENTS_CONFIG;
  const [stageId, setStageId] = useState<PipelineStage | 'all'>('all');
  const [q, setQ] = useState('');
  /** 默认展开扩展专家，避免剧本评估 / IP 评估等被藏在「更多」里用不了 */
  const [showMore, setShowMore] = useState(true);

  const visibleAgents = useMemo(() => {
    if (!productLines || productLines.length === 0) return agents;
    return agents.filter((a) => productLines.includes(resolveProductLine(a)));
  }, [agents, productLines]);

  const coreAgents = useMemo(() => getCoreAgents(visibleAgents), [visibleAgents]);

  const extendedAgents = useMemo(() => {
    const coreIds = new Set(coreAgents.map((a) => a.id));
    return visibleAgents.filter(
      (a) => resolveNavTier(a) !== 'utility' && !coreIds.has(a.id)
    );
  }, [visibleAgents, coreAgents]);

  const allExperts = useMemo(
    () => [...coreAgents, ...extendedAgents],
    [coreAgents, extendedAgents]
  );

  const filtered = useMemo(() => {
    // 搜索 / 按阶段筛选时看全部专家；否则按「核心 / 核心+扩展」切换
    const pool = q.trim() || stageId !== 'all' || showMore ? allExperts : coreAgents;
    let list = pool;
    if (q.trim()) {
      const lower = q.toLowerCase();
      list = allExperts.filter(
        (a) =>
          a.displayName.toLowerCase().includes(lower) ||
          a.description.toLowerCase().includes(lower) ||
          (a.features || []).some((f) => f.toLowerCase().includes(lower))
      );
    } else if (stageId !== 'all') {
      list = list.filter((a) => resolvePipelineStage(a) === stageId);
    }
    return list;
  }, [allExperts, coreAgents, showMore, q, stageId]);

  return (
    <aside className="h-full flex flex-col bg-transparent">
      <div className="px-3 pt-2.5 pb-2 border-b border-pearl-line">
        <div className="flex items-center gap-1.5">
          <div className="w-5 h-5 rounded bg-atelier-teal-soft text-atelier-teal flex items-center justify-center">
            <Sparkles className="w-3 h-3" />
          </div>
          <h2 className="font-display text-[13px] font-semibold text-ink leading-none">{t('studio.blueprint.title')}</h2>
          <span className="text-[10px] text-ink-faint ml-auto">{t('studio.blueprint.sixSteps')}</span>
        </div>
      </div>

      <div className="px-2.5 py-1.5 border-b border-pearl-line">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-ink-faint" />
          <input
            className="w-full pl-7 pr-2 py-1.5 text-[11px] rounded-md border border-pearl-line bg-pearl-soft/80 focus:outline-none focus:border-atelier-teal"
            placeholder={t('studio.blueprint.searchPlaceholder')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
      </div>

      {!q && (
        <div className="px-2 py-1.5 flex flex-wrap gap-0.5 border-b border-pearl-line">
          {STAGE_FILTERS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setStageId(s.id)}
              className={clsx(
                'px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors',
                stageId === s.id
                  ? 'bg-atelier-teal text-white'
                  : 'bg-pearl-soft text-ink-muted hover:text-atelier-teal'
              )}
            >
              {t(s.label)}
            </button>
          ))}
        </div>
      )}

      <div className="px-2.5 py-1">
        <div className="text-[9px] uppercase tracking-[0.1em] text-ink-faint">
          {q ? t('studio.blueprint.searchCount', { count: filtered.length }) : showMore ? t('studio.blueprint.coreExtCount', { count: filtered.length }) : t('studio.blueprint.coreCount', { count: filtered.length })}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-1">
        {filtered.length === 0 ? (
          <p className="text-xs text-ink-faint px-2 py-8 text-center">{t('studio.blueprint.noMatch')}</p>
        ) : (
          filtered.map((agent) => (
            <AgentRow
              key={agent.id}
              agent={agent}
              active={activeAgent === agent.id}
              onSelect={() => setActiveAgent(agent.id)}
            />
          ))
        )}
      </div>

      <div className="p-2 border-t border-pearl-line space-y-1">
        <button
          type="button"
          onClick={() => setShowMore((v) => !v)}
          className="flex items-center justify-center gap-1 w-full py-1.5 rounded-md text-[11px] font-medium text-ink-muted hover:bg-pearl-soft"
        >
          <ChevronDown className={clsx('w-3 h-3 transition-transform', showMore && 'rotate-180')} />
          {showMore ? t('studio.blueprint.showCoreOnly') : t('studio.blueprint.browseAll')}
        </button>
        <Link
          to="/dramas"
          className="flex items-center justify-center gap-1.5 w-full py-1.5 rounded-md text-[11px] font-semibold bg-atelier-teal text-white hover:bg-atelier-teal-mid"
        >
          <Clapperboard className="w-3 h-3" />
          {t('studio.blueprint.openWork')}
        </Link>
      </div>
    </aside>
  );
}

/**
 * 左栏故事蓝图 — 制片阶段 + 分集过滤 + 专家/设定
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Sparkles, Layers, Check, Pencil, X, Trash2 } from 'lucide-react';
import clsx from 'clsx';
import StreamingText from '@/components/chat/StreamingText';
import { useAgentStore } from '@/store/agentStore';
import { useI18n } from '@/i18n';
import { getCoreAgents, AGENTS_CONFIG } from '@/config/agents';
import type { DramaDetail, EpisodeStatus } from '@/services/dramaService';
import type { AtelierRun } from '@/services/atelierService';
import StudioPipelineRail, {
  type PipelineStageId,
  type StudioStage,
} from '@/components/workspace/StudioPipelineRail';
import StudioScriptsPanel from '@/components/workspace/StudioScriptsPanel';
import { setDramaRefDragData } from '@/utils/dramaRefs';

const statusLabel: Record<EpisodeStatus, string> = {
  draft: 'studio.status.draft',
  writing: 'studio.status.writing',
  done: 'studio.status.done',
  error: 'studio.status.error',
};

type EpFilter = 'all' | 'draft' | 'done' | 'writing';

type Props = {
  drama: DramaDetail;
  selectedEp: number;
  onSelectEpisode: (n: number) => void;
  onGenerateOutline: () => void;
  busy?: boolean;
  artifactCount?: number;
  artifactKinds?: string[];
  atelierRun?: AtelierRun | null;
  onOpenMap?: () => void;
  onSelectStage?: (stage: StudioStage) => void;
  onStartStage?: (stage: StudioStage) => void;
  activeStageId?: PipelineStageId | null;
  onUpdateDrama?: (payload: { title?: string; description?: string; genre?: string; total_episodes?: number }) => Promise<void> | void;
  onSaveBible?: (payload: { world?: string; characters?: string }) => Promise<void> | void;
  onDeleteEpisode?: (n: number) => Promise<void> | void;
};

export default function StudioDramaRail({
  drama,
  selectedEp,
  onSelectEpisode,
  onGenerateOutline,
  busy,
  artifactCount = 0,
  artifactKinds = [],
  atelierRun,
  onOpenMap,
  onSelectStage,
  onStartStage,
  activeStageId,
  onUpdateDrama,
  onSaveBible,
  onDeleteEpisode,
}: Props) {
  const { t } = useI18n();
  const { agents: loaded, activeAgent, setActiveAgent } = useAgentStore();
  const agents = loaded.length > 0 ? loaded : AGENTS_CONFIG;
  const core = useMemo(() => getCoreAgents(agents), [agents]);
  const [tab, setTab] = useState<'pipeline' | 'episodes' | 'scripts' | 'agents' | 'bible'>(
    'pipeline'
  );
  const [epFilter, setEpFilter] = useState<EpFilter>('all');
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState(drama.title);
  const [editingWorld, setEditingWorld] = useState(false);
  const [worldDraft, setWorldDraft] = useState(drama.bible?.world || '');
  const [editingChars, setEditingChars] = useState(false);
  const [charsDraft, setCharsDraft] = useState(drama.bible?.characters || '');
  const [editingTotal, setEditingTotal] = useState(false);
  const [totalDraft, setTotalDraft] = useState(drama.total_episodes || 80);

  const saveTitle = async () => {
    await onUpdateDrama?.({ title: titleDraft });
    setEditingTitle(false);
  };
  const saveWorld = async () => {
    await onSaveBible?.({ world: worldDraft });
    setEditingWorld(false);
  };
  const saveChars = async () => {
    await onSaveBible?.({ characters: charsDraft });
    setEditingChars(false);
  };
  const saveTotal = async () => {
    await onUpdateDrama?.({ total_episodes: Math.max(1, totalDraft) });
    setEditingTotal(false);
  };

  const done =
    drama.completed_episodes || drama.episodes?.filter((e) => e.status === 'done').length || 0;
  const total = drama.total_episodes || 1;
  const pct = Math.min(100, Math.round((done / Math.max(total, 1)) * 100));
  const writing = drama.episodes?.filter((e) => e.status === 'writing').length || 0;
  const draft = drama.episodes?.filter((e) => e.status === 'draft' || e.status === 'error').length || 0;

  const castPreview = (drama.bible?.characters || '')
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean)
    .slice(0, 8);

  const filteredEps = useMemo(() => {
    const list = drama.episodes || [];
    if (epFilter === 'all') return list;
    if (epFilter === 'done') return list.filter((e) => e.status === 'done');
    if (epFilter === 'writing') return list.filter((e) => e.status === 'writing');
    return list.filter((e) => e.status === 'draft' || e.status === 'error');
  }, [drama.episodes, epFilter]);

  return (
    <aside className="h-full flex flex-col">
      <div className="px-3.5 pt-3.5 pb-3 border-b border-pearl-line/80">
        <div className="flex items-center justify-between gap-2">
          <div className="text-[10px] uppercase tracking-[0.14em] text-ink-faint">{t('studio.rail.storyBlueprint')}</div>
          <Link to="/dramas" className="text-[10px] text-atelier-teal hover:underline shrink-0">
            {t('studio.rail.worksLibrary')}
          </Link>
        </div>
        {editingTitle ? (
          <div className="mt-1 flex items-center gap-1">
            <input
              autoFocus
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && saveTitle()}
              className="w-full bg-transparent font-display text-lg font-semibold text-ink leading-tight outline-none border-b border-atelier-teal/40"
            />
            <button onClick={saveTitle} className="p-1 text-atelier-teal shrink-0" title={t('common.save')}>
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => {
                setEditingTitle(false);
                setTitleDraft(drama.title);
              }}
              className="p-1 text-ink-faint shrink-0"
              title={t('common.cancel')}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1 group/ttl">
            <h2 className="font-display text-lg font-semibold text-ink truncate leading-tight mt-1">
              {drama.title}
            </h2>
            {onUpdateDrama && (
              <button
                onClick={() => {
                  setTitleDraft(drama.title);
                  setEditingTitle(true);
                }}
                className="mt-1 p-1 text-ink-faint hover:text-atelier-teal opacity-0 group-hover/ttl:opacity-100 transition-opacity shrink-0"
                title={t('studio.rail.editTitle')}
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-atelier-teal-soft text-atelier-teal">
            {drama.genre || t('common.shortDrama')}
          </span>
          {editingTotal ? (
            <span className="flex items-center gap-1 text-[10px] tabular-nums">
              <input
                type="number"
                min={1}
                autoFocus
                value={totalDraft}
                onChange={(e) => setTotalDraft(Math.max(1, Number(e.target.value) || 1))}
                onKeyDown={(e) => e.key === 'Enter' && saveTotal()}
                className="w-14 px-1 py-0.5 text-[10px] rounded border border-atelier-teal/40 bg-white outline-none tabular-nums"
              />
              <button onClick={saveTotal} className="text-atelier-teal" title={t('common.save')}>
                <Check className="w-3 h-3" />
              </button>
              <button onClick={() => setEditingTotal(false)} className="text-ink-faint" title={t('common.cancel')}>
                <X className="w-3 h-3" />
              </button>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] text-ink-faint tabular-nums group/total">
              {done}/{total} {t('dramas.episodeUnit')} · {pct}%
              {onUpdateDrama && (
                <button
                  onClick={() => {
                    setTotalDraft(drama.total_episodes || 80);
                    setEditingTotal(true);
                  }}
                  className="p-0.5 text-ink-faint hover:text-atelier-teal opacity-0 group-hover/total:opacity-100 transition-opacity"
                  title={t('studio.rail.editTotal')}
                >
                  <Pencil className="w-3 h-3" />
                </button>
              )}
            </span>
          )}
          {atelierRun && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-atelier-gold-soft text-atelier-gold">
              {t('studio.rail.orchestrating')}
            </span>
          )}
        </div>
        <p className="text-[11px] text-ink-muted mt-2 line-clamp-2 leading-snug">
          {drama.description || t('studio.rail.noDesc')}
        </p>
        {onOpenMap && (
          <button
            type="button"
            onClick={onOpenMap}
            className="mt-2.5 w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg border border-atelier-teal/25 bg-atelier-teal-soft/50 text-left hover:bg-atelier-teal-soft transition-colors"
          >
            <span className="inline-flex items-center gap-1.5 text-[12px] font-semibold text-atelier-teal">
              <Layers className="w-3.5 h-3.5" />
              {t('studio.rail.creationMap')}
            </span>
            <span className="text-[10px] tabular-nums text-atelier-teal/80">
              {artifactCount > 0 ? t('studio.rail.assets', { count: artifactCount }) : t('studio.rail.overview')}
            </span>
          </button>
        )}
        <div className="mt-2 h-1 rounded-full bg-pearl-soft overflow-hidden">
          <div
            className="h-full bg-atelier-teal transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="flex border-b border-pearl-line/80 text-[11px]">
        {(
          [
            { id: 'pipeline' as const, label: t('studio.tab.stages') },
            { id: 'episodes' as const, label: t('studio.tab.episodes') },
            { id: 'scripts' as const, label: t('studio.tab.scripts') },
            { id: 'agents' as const, label: t('studio.tab.agents') },
            { id: 'bible' as const, label: t('studio.tab.bible') },
          ] as const
        ).map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={clsx(
              'flex-1 py-2.5 font-medium transition-colors',
              tab === id
                ? 'text-atelier-teal border-b-2 border-atelier-teal'
                : 'text-ink-muted hover:text-ink'
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {tab === 'pipeline' && (
          <StudioPipelineRail
            drama={drama}
            artifactKinds={artifactKinds}
            atelierRun={atelierRun}
            activeStageId={activeStageId}
            onSelectStage={(stage) => {
              onSelectStage?.(stage);
              if (stage.midMode === 'episode') setTab('episodes');
            }}
            onStartStage={onStartStage}
          />
        )}

        {tab === 'episodes' && (
          <div className="p-2 space-y-1.5">
            <div className="flex items-center justify-between px-1.5 py-1 gap-2">
              <div className="flex flex-wrap gap-1">
                {(
                  [
                    { id: 'all' as const, label: t('studio.filter.all', { count: total }) },
                    { id: 'draft' as const, label: t('studio.filter.draft', { count: draft }) },
                    { id: 'writing' as const, label: t('studio.filter.writing', { count: writing }) },
                    { id: 'done' as const, label: t('studio.filter.done', { count: done }) },
                  ] as const
                ).map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setEpFilter(f.id)}
                    className={clsx(
                      'text-[10px] px-1.5 py-0.5 rounded-md border transition-colors',
                      epFilter === f.id
                        ? 'border-atelier-teal/40 bg-atelier-teal-soft text-atelier-teal'
                        : 'border-transparent text-ink-faint hover:bg-white/60'
                    )}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={onGenerateOutline}
                className="inline-flex items-center gap-1 text-[11px] text-atelier-teal hover:underline shrink-0"
              >
                <BookOpen className="w-3 h-3" />
                {t('studio.bible.outline')}
              </button>
            </div>
            {filteredEps.length === 0 ? (
              <p className="px-2 py-6 text-center text-[11px] text-ink-faint">{t('studio.rail.noEpFilter')}</p>
            ) : (
              filteredEps.map((ep) => {
                const active = selectedEp === ep.number;
                return (
                  <div
                    key={ep.number}
                    draggable={ep.status === 'done'}
                    title={
                      ep.status === 'done'
                        ? t('workspace.dragToChat')
                        : undefined
                    }
                    onDragStart={(e) => {
                      if (ep.status !== 'done') {
                        e.preventDefault();
                        return;
                      }
                      setDramaRefDragData(e, {
                        kind: 'episode',
                        dramaId: drama.id,
                        episodeNumber: ep.number,
                        label: t('studio.ep', { n: ep.number }),
                      });
                    }}
                    className={clsx(
                      'group relative rounded-xl border transition-all duration-200',
                      active
                        ? 'border-atelier-teal/45 bg-atelier-teal-soft/90 shadow-sm'
                        : 'border-pearl-line/50 bg-white/40 hover:bg-white/70',
                      ep.status === 'done' && 'cursor-grab active:cursor-grabbing'
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onSelectEpisode(ep.number)}
                      className="w-full text-left px-3 py-2.5"
                    >
                      {active && (
                        <Check className="absolute right-7 top-2.5 w-3.5 h-3.5 text-atelier-teal" />
                      )}
                      <div className="flex items-center gap-2 pr-5">
                        <span className="text-[12px] font-semibold text-ink">{t('studio.ep', { n: ep.number })}</span>
                        <span
                          className={clsx(
                            'text-[9px] px-1.5 py-0.5 rounded',
                            ep.status === 'done'
                              ? 'bg-atelier-teal text-white'
                              : ep.status === 'writing'
                                ? 'bg-atelier-gold-soft text-atelier-gold'
                                : 'bg-pearl-soft text-ink-faint'
                          )}
                        >
                          {t(statusLabel[ep.status])}
                        </span>
                      </div>
                      <p className="text-[12px] text-ink mt-0.5 truncate font-medium">
                        {ep.title || t('studio.unnamed')}
                      </p>
                      <p className="text-[10px] text-ink-muted mt-0.5 line-clamp-2 leading-snug">
                        {ep.summary || (ep.status === 'done' ? t('studio.rail.doneSaved') : t('studio.rail.editOrWrite'))}
                      </p>
                      <div className="mt-1 text-[10px] text-ink-faint tabular-nums">
                        {ep.word_count ? t('studio.charCount', { count: ep.word_count }) : t('studio.charCount', { count: 0 })}
                      </div>
                    </button>
                    {onDeleteEpisode && (
                      <button
                        type="button"
                        onClick={async () => {
                          if (window.confirm(t('studio.rail.deleteEpConfirm', { n: ep.number }))) {
                            await onDeleteEpisode(ep.number);
                          }
                        }}
                        className="absolute right-1.5 top-1.5 p-1 text-ink-faint hover:text-rose-600 opacity-0 group-hover:opacity-100 transition-opacity"
                        title={t('studio.rail.deleteEp')}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        {tab === 'scripts' && (
          <StudioScriptsPanel dramaId={drama.id} dramaTitle={drama.title} />
        )}

        {tab === 'agents' && (
          <div className="p-2 space-y-1">
            <p className="px-1.5 py-1 text-[10px] uppercase tracking-wider text-ink-faint">{t('studio.rail.coreExperts')}</p>
            {core.map((agent) => (
              <button
                key={agent.id}
                type="button"
                onClick={() => setActiveAgent(agent.id)}
                className={clsx(
                  'w-full text-left rounded-lg px-2.5 py-2 border transition-colors',
                  activeAgent === agent.id
                    ? 'border-atelier-teal/40 bg-atelier-teal-soft'
                    : 'border-transparent hover:bg-white/60'
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm w-6 text-center">{agent.icon}</span>
                  <div className="min-w-0">
                    <div className="text-[12px] font-semibold text-ink truncate">
                      {agent.displayName}
                    </div>
                    <div className="text-[10px] text-ink-faint truncate">{agent.features?.[0]}</div>
                  </div>
                </div>
              </button>
            ))}
            <Link to="/experts" className="block text-center text-xs text-atelier-teal py-2 hover:underline">
              {t('studio.rail.allExperts')}
            </Link>
          </div>
        )}

        {tab === 'bible' && (
          <div className="p-2.5 space-y-2">
            {drama.outline?.trim() && (
              <div
                className="rounded-lg border border-pearl-line/70 bg-white/50 p-2.5 cursor-grab active:cursor-grabbing"
                draggable
                title={t('workspace.dragToChat')}
                onDragStart={(e) =>
                  setDramaRefDragData(e, {
                    kind: 'outline',
                    dramaId: drama.id,
                    label: t('studio.bible.seriesOutline'),
                  })
                }
              >
                <div className="text-[10px] text-ink-faint font-medium mb-1">{t('studio.bible.seriesOutline')}</div>
                <div className="max-h-56 overflow-y-auto markdown text-[11px] text-ink-muted leading-snug">
                  <StreamingText content={drama.outline} compact />
                </div>
              </div>
            )}

            <div
              className="rounded-lg border border-pearl-line/70 bg-white/50 p-2.5 cursor-grab active:cursor-grabbing"
              draggable={!editingWorld}
              title={t('workspace.dragToChat')}
              onDragStart={(e) => {
                if (editingWorld) {
                  e.preventDefault();
                  return;
                }
                setDramaRefDragData(e, {
                  kind: 'world',
                  dramaId: drama.id,
                  label: t('studio.bible.world'),
                });
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="text-[10px] text-atelier-teal font-medium">{t('studio.bible.world')}</div>
                {onSaveBible && (
                  editingWorld ? (
                    <div className="flex gap-0.5">
                      <button onClick={saveWorld} className="p-1 text-atelier-teal" title={t('common.save')}>
                        <Check className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => setEditingWorld(false)}
                        className="p-1 text-ink-faint"
                        title={t('common.cancel')}
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        setWorldDraft(drama.bible?.world || '');
                        setEditingWorld(true);
                      }}
                      className="p-1 text-ink-faint hover:text-atelier-teal"
                      title={t('studio.rail.editWorld')}
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                  )
                )}
              </div>
              {editingWorld ? (
                <textarea
                  autoFocus
                  value={worldDraft}
                  onChange={(e) => setWorldDraft(e.target.value)}
                  className="w-full min-h-[110px] text-[11px] leading-snug rounded-md border border-atelier-teal/30 bg-white/80 p-2 outline-none focus:border-atelier-teal"
                />
              ) : (
                <p className="text-[11px] text-ink-muted leading-snug line-clamp-5 whitespace-pre-wrap">
                  {drama.bible?.world || t('studio.bible.worldEmpty')}
                </p>
              )}
            </div>

            <div
              className="rounded-lg border border-pearl-line/70 bg-white/50 p-2.5 cursor-grab active:cursor-grabbing"
              draggable={!editingChars}
              title={t('workspace.dragToChat')}
              onDragStart={(e) => {
                if (editingChars) {
                  e.preventDefault();
                  return;
                }
                setDramaRefDragData(e, {
                  kind: 'characters',
                  dramaId: drama.id,
                  label: t('studio.bible.characters'),
                });
              }}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="text-[10px] text-ink-faint font-medium">{t('studio.bible.characters')}</div>
                {onSaveBible && (
                  editingChars ? (
                    <div className="flex gap-0.5">
                      <button onClick={saveChars} className="p-1 text-atelier-teal" title={t('common.save')}>
                        <Check className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => setEditingChars(false)}
                        className="p-1 text-ink-faint"
                        title={t('common.cancel')}
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        setCharsDraft(drama.bible?.characters || '');
                        setEditingChars(true);
                      }}
                      className="p-1 text-ink-faint hover:text-atelier-teal"
                      title={t('studio.rail.editChars')}
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                  )
                )}
              </div>
              {editingChars ? (
                <textarea
                  autoFocus
                  value={charsDraft}
                  onChange={(e) => setCharsDraft(e.target.value)}
                  className="w-full min-h-[140px] text-[11px] leading-snug rounded-md border border-atelier-teal/30 bg-white/80 p-2 outline-none focus:border-atelier-teal"
                />
              ) : castPreview.length > 0 ? (
                <ul className="space-y-1">
                  {castPreview.map((line) => (
                    <li
                      key={line}
                      className="text-[11px] text-ink-muted truncate border-b border-pearl-line/50 pb-1"
                    >
                      {line.replace(/^[-*•#\s]+/, '')}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[11px] text-ink-faint">{t('studio.bible.charsEmpty')}</p>
              )}
            </div>

            <div className="rounded-lg border border-pearl-line/70 bg-white/50 p-2.5">
              <div className="text-[10px] text-atelier-gold font-medium mb-1 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                Skills
              </div>
              <p className="text-[11px] text-ink-muted leading-snug">
                {t('studio.bible.skillsHint')}
              </p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

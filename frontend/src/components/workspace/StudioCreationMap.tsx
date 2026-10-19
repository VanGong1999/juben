/**
 * 创作图 — 高密度资产墙：本集焦点 · 人物 · 设定 · 情节点 · 策划/评估
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Sparkles,
  Users,
  BookOpen,
  BarChart3,
  PenLine,
  Lightbulb,
  ArrowRight,
  Eye,
  Wand2,
  Layers,
  Clock,
  FileText,
  X,
  Zap,
} from 'lucide-react';
import clsx from 'clsx';
import StreamingText from '@/components/chat/StreamingText';
import {
  getDramaArtifact,
  listDramaArtifacts,
  type DramaArtifact,
  type DramaArtifactMeta,
  type DramaDetail,
} from '@/services/dramaService';
import { useAgentStore } from '@/store/agentStore';
import { useI18n } from '@/i18n';

type SectionId = 'focus' | 'character' | 'knowledge' | 'plot' | 'planning' | 'evaluation' | 'creation';

const SECTIONS: {
  id: SectionId;
  kinds: string[];
  title: string;
  hint: string;
  icon: typeof Users;
  agentId?: string;
  emptyCta: string;
}[] = [
  {
    id: 'character',
    kinds: ['character'],
    title: 'studio.map.sec.biosTitle',
    hint: 'studio.map.sec.biosHint',
    icon: Users,
    agentId: 'character_profile_generator',
    emptyCta: 'studio.map.generateBios',
  },
  {
    id: 'knowledge',
    kinds: ['story', 'planning'],
    title: 'studio.map.sec.knowledgeTitle',
    hint: 'studio.map.sec.knowledgeHint',
    icon: Lightbulb,
    agentId: 'story_five_elements',
    emptyCta: 'studio.map.analyzeFive',
  },
  {
    id: 'plot',
    kinds: ['plot'],
    title: 'studio.map.sec.plotTitle',
    hint: 'studio.map.sec.plotHint',
    icon: Zap,
    agentId: 'major_plot_points',
    emptyCta: 'studio.map.sec.plotEmpty',
  },
  {
    id: 'planning',
    kinds: ['planning'],
    title: 'studio.map.sec.planningTitle',
    hint: 'studio.map.sec.planningHint',
    icon: Sparkles,
    agentId: 'short_drama_planner',
    emptyCta: 'studio.map.sec.planningEmpty',
  },
  {
    id: 'evaluation',
    kinds: ['evaluation'],
    title: 'studio.map.sec.evaluationTitle',
    hint: 'studio.map.sec.evaluationHint',
    icon: BarChart3,
    agentId: 'short_drama_evaluation',
    emptyCta: 'studio.map.sec.evaluationEmpty',
  },
  {
    id: 'creation',
    kinds: ['creation'],
    title: 'studio.map.sec.creationTitle',
    hint: 'studio.map.sec.creationHint',
    icon: PenLine,
    agentId: 'short_drama_creator',
    emptyCta: 'studio.map.sec.creationEmpty',
  },
];

function formatWhen(iso?: string) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function parseCharacterCards(text: string): { name: string; role: string; blurb: string; full: string }[] {
  if (!text?.trim()) return [];
  const blocks = text.split(/\n(?=#{1,3}\s|【|[【\[]|[「]|^\*\*)/m).filter((b) => b.trim().length > 8);
  const cards: { name: string; role: string; blurb: string; full: string }[] = [];
  for (const block of blocks.slice(0, 8)) {
    const lines = block
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);
    if (!lines.length) continue;
    const head = lines[0].replace(/^#+\s*/, '').replace(/[*【】\[\]]/g, '').trim();
    const name = head.split(/[·|:：\-\s]/)[0]?.slice(0, 12) || '角色';
    const roleMatch = block.match(/(主角|女主|男主|配角|反派|核心)/);
    const blurb = lines.slice(1).join(' ').replace(/\s+/g, ' ').slice(0, 72);
    cards.push({ name, role: roleMatch?.[1] || '人物', blurb: blurb || head.slice(0, 72), full: block });
  }
  if (cards.length === 0 && text.trim()) {
    cards.push({ name: '人物设定', role: '汇总', blurb: text.replace(/\s+/g, ' ').slice(0, 90), full: text });
  }
  return cards;
}

type Props = {
  drama: DramaDetail;
  selectedEp: number;
  episodeTitle: string;
  episodeContent: string;
  onSelectEpisode: (n: number) => void;
  onWriteEpisode: () => void;
  onOpenEpisodeEditor: () => void;
  busy?: boolean;
  /** 真正发送任务给专家（用于思维导图等「点击即生成」的场景） */
  onAsk?: (prompt: string, agentId: string) => void;
};

export default function StudioCreationMap({
  drama,
  selectedEp,
  episodeTitle,
  episodeContent,
  onSelectEpisode,
  onWriteEpisode,
  onOpenEpisodeEditor,
  busy,
  onAsk,
}: Props) {
  const { t } = useI18n();
  const { setActiveAgent } = useAgentStore();
  const [items, setItems] = useState<DramaArtifactMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState<DramaArtifact | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listDramaArtifacts(drama.id, { limit: 150 });
      setItems(res.artifacts || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [drama.id]);

  useEffect(() => {
    reload();
    const onUpdate = (e: Event) => {
      const detail = (e as CustomEvent).detail as { dramaId?: string } | undefined;
      if (!detail?.dramaId || detail.dramaId === drama.id) reload();
    };
    window.addEventListener('drama-artifacts-updated', onUpdate);
    return () => window.removeEventListener('drama-artifacts-updated', onUpdate);
  }, [drama.id, reload]);

  const byKind = useMemo(() => {
    const map: Record<string, DramaArtifactMeta[]> = {};
    for (const it of items) {
      const k = it.kind || 'other';
      if (!map[k]) map[k] = [];
      map[k].push(it);
    }
    return map;
  }, [items]);

  const done =
    drama.completed_episodes || drama.episodes?.filter((e) => e.status === 'done').length || 0;
  const total = drama.total_episodes || 1;
  const pct = Math.min(100, Math.round((done / total) * 100));
  const currentEp = drama.episodes?.find((e) => e.number === selectedEp);

  const characterCards = useMemo(() => {
    const fromBible = parseCharacterCards(drama.bible?.characters || '');
    const fromArts = (byKind.character || [])
      .slice(0, 4)
      .flatMap((a) => parseCharacterCards(a.preview || a.title));
    const merged = [...fromArts, ...fromBible];
    const seen = new Set<string>();
    return merged.filter((c) => {
      if (seen.has(c.name)) return false;
      seen.add(c.name);
      return true;
    }).slice(0, 6);
  }, [drama.bible?.characters, byKind.character]);

  const knowledgeCards = useMemo(() => {
    const cards: { title: string; tag: string; blurb: string; id?: string; content?: string }[] = [];
    if (drama.bible?.world?.trim()) {
      cards.push({
        title: t('studio.map.worldTag'),
        tag: t('studio.map.settingTag'),
        blurb: drama.bible.world.replace(/\s+/g, ' ').slice(0, 80),
        content: drama.bible.world,
      });
    }
    if (drama.outline?.trim()) {
      cards.push({
        title: t('studio.bible.seriesOutline'),
        tag: t('studio.map.storyTag'),
        blurb: drama.outline.replace(/\s+/g, ' ').slice(0, 80),
        content: drama.outline,
      });
    }
    if (drama.description?.trim()) {
      cards.push({
        title: t('studio.map.pitchTitle'),
        tag: t('studio.map.planTag'),
        blurb: drama.description.slice(0, 80),
        content: drama.description,
      });
    }
    for (const a of [...(byKind.story || []), ...(byKind.planning || [])].slice(0, 5)) {
      cards.push({
        title: a.title,
        tag: a.kind_label || t('studio.map.knowledgeTag'),
        blurb: (a.preview || '').slice(0, 80),
        id: a.id,
      });
    }
    return cards.slice(0, 8);
  }, [drama, byKind]);

  const openKnowledge = (k: { title: string; tag: string; blurb: string; content?: string }) => {
    setActive({
      id: `knowledge-${k.title}`,
      drama_id: drama.id,
      kind: 'story',
      kind_label: k.tag,
      title: k.title,
      content: k.content || k.blurb,
      preview: k.blurb,
      agent_name: '',
    } as DramaArtifact);
  };

  const openArtifact = async (id: string) => {
    setLoadingDetail(true);
    try {
      const res = await getDramaArtifact(drama.id, id);
      if (res.artifact) setActive(res.artifact);
    } finally {
      setLoadingDetail(false);
    }
  };

  const askAgent = (agentId: string) => {
    setActiveAgent(agentId);
  };

  const stats = [
    { label: t('studio.map.progress'), value: `${done}/${total}`, sub: `${pct}%` },
    { label: t('studio.map.artifacts'), value: String(items.length), sub: t('studio.map.unit') },
    { label: t('studio.map.characters'), value: String(characterCards.length || byKind.character?.length || 0), sub: t('studio.map.card') },
    { label: t('studio.map.evaluation'), value: String(byKind.evaluation?.length || 0), sub: t('studio.map.unit') },
  ];

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Dense header strip */}
      <div className="px-4 sm:px-5 pt-3 pb-3 border-b border-pearl-line/70 flex flex-wrap items-center gap-3 justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-atelier-teal" />
            <h2 className="font-display text-xl font-semibold text-ink leading-none">{t('studio.map.title')}</h2>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-atelier-teal-soft text-atelier-teal">
              {drama.genre || t('common.shortDrama')}
            </span>
          </div>
          <p className="text-[11px] text-ink-muted mt-1 truncate max-w-xl">
            {drama.description || t('studio.map.noDesc')}
          </p>
        </div>
        <div className="flex gap-1.5">
          {stats.map((s) => (
            <div
              key={s.label}
              className="px-2.5 py-1.5 rounded-lg bg-white/55 border border-white/70 backdrop-blur-sm min-w-[58px]"
            >
              <div className="text-[9px] uppercase tracking-wider text-ink-faint">{s.label}</div>
              <div className="font-mono text-sm text-ink tabular-nums leading-tight">
                {s.value}
                <span className="text-[10px] text-ink-faint ml-0.5">{s.sub}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 space-y-3">
        {/* Focus: current episode + versions-like strip */}
        <section className="grid lg:grid-cols-[1.35fr_1fr] gap-3">
          <div className="rounded-xl border border-white/60 bg-white/60 backdrop-blur-md p-4 shadow-atelier">
            <div className="flex items-start justify-between gap-2 mb-2">
              <div>
                <div className="text-[10px] text-ink-faint uppercase tracking-wider">{t('studio.map.focus')}</div>
                <h3 className="font-display text-2xl font-semibold text-ink mt-0.5">
                  {t('studio.ep', { n: selectedEp })}
                  <span className="text-base text-ink-muted font-sans font-medium ml-2">
                    {episodeTitle || currentEp?.title || t('studio.unnamed')}
                  </span>
                </h3>
              </div>
              <span
                className={clsx(
                  'text-[10px] px-2 py-0.5 rounded-full shrink-0',
                  currentEp?.status === 'done'
                    ? 'bg-atelier-teal text-white'
                    : 'bg-pearl-soft text-ink-muted'
                )}
              >
                {currentEp?.status === 'done' ? t('studio.map.done') : t('studio.map.pending')}
              </span>
            </div>
            <p className="text-sm text-ink-muted leading-relaxed line-clamp-4 min-h-[4.5rem] whitespace-pre-wrap">
              {episodeContent?.trim() ||
                currentEp?.summary ||
                t('studio.map.noBody')}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-[11px] text-ink-faint tabular-nums">
                {t('studio.charCount', { count: (episodeContent || '').length || currentEp?.word_count || 0 })}
              </span>
              <div className="flex-1" />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onOpenEpisodeEditor}
              >
                <Eye className="w-3.5 h-3.5" />
                {t('studio.map.enterEdit')}
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={busy}
                onClick={onWriteEpisode}
              >
                <Wand2 className="w-3.5 h-3.5" />
                {t('studio.episode.aiWrite')}
              </button>
            </div>
            <div className="mt-3 h-1 rounded-full bg-pearl-soft overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-atelier-teal to-atelier-teal-mid transition-all duration-700"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          {/* Episode rail dense + creation snippets as "versions" */}
          <div className="rounded-xl border border-white/60 bg-white/55 backdrop-blur-md p-3 shadow-atelier flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-2 px-1">
              <div className="text-[12px] font-semibold text-ink">{t('studio.map.episodeOverview')}</div>
              <span className="text-[10px] text-ink-faint">{t('studio.map.doneCount', { done, total })}</span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-1.5 max-h-[220px]">
              {(drama.episodes || []).slice(0, 12).map((ep) => (
                <button
                  key={ep.number}
                  type="button"
                  onClick={() => onSelectEpisode(ep.number)}
                  className={clsx(
                    'w-full text-left rounded-lg px-2.5 py-2 border transition-all duration-200',
                    selectedEp === ep.number
                      ? 'border-atelier-teal/50 bg-atelier-teal-soft/80 shadow-sm'
                      : 'border-transparent hover:bg-white/70'
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[13px] font-medium text-ink">
                      {t('studio.ep', { n: ep.number })} · {ep.title || t('studio.unnamed')}
                    </span>
                    <span className="text-[10px] text-ink-faint tabular-nums shrink-0">
                      {ep.word_count ? t('studio.charCount', { count: ep.word_count }) : '—'}
                    </span>
                  </div>
                  <p className="text-[11px] text-ink-muted line-clamp-1 mt-0.5">
                    {ep.summary || (ep.status === 'done' ? t('studio.map.saved') : t('studio.map.pendingCreate'))}
                  </p>
                </button>
              ))}
            </div>
            {(byKind.creation || []).length > 0 && (
              <div className="mt-2 pt-2 border-t border-pearl-line/80">
                <div className="text-[10px] text-ink-faint mb-1.5 px-1">{t('studio.map.recentSnippets')}</div>
                <div className="space-y-1">
                  {(byKind.creation || []).slice(0, 2).map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => openArtifact(a.id)}
                      className="w-full text-left rounded-lg px-2.5 py-2 bg-white/50 border border-pearl-line/60 hover:border-atelier-teal/30 transition-colors"
                    >
                      <div className="text-[12px] font-medium text-ink truncate">{a.title}</div>
                      <p className="text-[10px] text-ink-muted line-clamp-1 mt-0.5">{a.preview}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Character + Knowledge dense row */}
        <section className="grid md:grid-cols-2 gap-3">
          <AssetSection
            title={t('studio.map.bios')}
            hint={t('studio.map.items', { count: characterCards.length || byKind.character?.length || 0 })}
            icon={Users}
            loading={loading}
            empty={!characterCards.length && !(byKind.character || []).length}
            emptyText={t('studio.map.biosEmpty')}
            onEmpty={() => askAgent('character_profile_generator')}
            emptyCta={t('studio.map.generateBios')}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {characterCards.map((c) => (
                <button
                  key={c.name + c.blurb.slice(0, 12)}
                  type="button"
                  onClick={() =>
                    setActive({
                      id: `char-${c.name}`,
                      drama_id: drama.id,
                      kind: 'character',
                      kind_label: t('studio.map.bios'),
                      title: c.name,
                      content: c.full,
                      preview: c.blurb,
                      agent_name: '',
                    } as DramaArtifact)
                  }
                  className="text-left rounded-lg border border-pearl-line/70 bg-white/70 p-2.5 hover:border-atelier-teal/40 hover:shadow-sm transition-all group"
                >
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-atelier-teal to-atelier-teal-mid text-white text-xs font-semibold flex items-center justify-center shrink-0">
                      {c.name[0]}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] font-semibold text-ink truncate group-hover:text-atelier-teal">{c.name}</div>
                      <div className="text-[10px] text-atelier-teal">{c.role}</div>
                    </div>
                    <Eye className="w-3 h-3 text-ink-faint opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                  </div>
                  <p className="text-[11px] text-ink-muted mt-1.5 line-clamp-2 leading-snug">{c.blurb}</p>
                </button>
              ))}
              {(byKind.character || []).slice(0, 3).map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => openArtifact(a.id)}
                  className="text-left rounded-lg border border-dashed border-pearl-line/80 bg-white/40 p-2.5 hover:bg-white/80 transition-colors"
                >
                  <div className="text-[11px] text-ink-faint">{t('studio.map.expertOutput')}</div>
                  <div className="text-[12px] font-medium text-ink truncate mt-0.5">{a.title}</div>
                  <p className="text-[10px] text-ink-muted line-clamp-2 mt-1">{a.preview}</p>
                </button>
              ))}
            </div>
          </AssetSection>

          <AssetSection
            title={t('studio.map.knowledge')}
            hint={t('studio.map.items', { count: knowledgeCards.length })}
            icon={Lightbulb}
            loading={loading}
            empty={knowledgeCards.length === 0}
            emptyText={t('studio.map.knowledgeEmpty')}
            onEmpty={() => askAgent('story_five_elements')}
            emptyCta={t('studio.map.analyzeFive')}
          >
            <div className="space-y-1.5">
              {knowledgeCards.map((k, i) => (
                <button
                  key={k.id || k.title + i}
                  type="button"
                  onClick={() => (k.id ? openArtifact(k.id) : openKnowledge(k))}
                  className="w-full text-left flex gap-2.5 rounded-lg border border-pearl-line/70 bg-white/70 p-2.5 hover:border-atelier-teal/30 transition-colors"
                >
                  <div className="w-7 h-7 rounded-md bg-atelier-gold-soft text-atelier-gold flex items-center justify-center shrink-0">
                    <BookOpen className="w-3.5 h-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[13px] font-semibold text-ink truncate">{k.title}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-pearl-soft text-ink-faint shrink-0">
                        {k.tag}
                      </span>
                    </div>
                    <p className="text-[11px] text-ink-muted line-clamp-2 mt-0.5">{k.blurb}</p>
                  </div>
                </button>
              ))}
            </div>
          </AssetSection>
        </section>

        {/* Plot / Planning / Evaluation / Creation grids */}
        <section className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {SECTIONS.filter((s) => ['plot', 'planning', 'evaluation', 'creation'].includes(s.id)).map(
            (sec) => {
              const list = sec.kinds.flatMap((k) => byKind[k] || []);
              const unique = Array.from(new Map(list.map((x) => [x.id, x])).values()).slice(0, 4);
              const Icon = sec.icon;
              return (
                <AssetSection
                  key={sec.id}
                  title={t(sec.title)}
                  hint={t(sec.hint)}
                  icon={Icon}
                  loading={loading}
                  empty={unique.length === 0}
                  emptyText={t('studio.map.emptyTitle', { title: t(sec.title) })}
                  onEmpty={() => sec.agentId && askAgent(sec.agentId)}
                  emptyCta={t(sec.emptyCta)}
                  compact
                >
                  <div className="space-y-1.5">
                    {unique.map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        onClick={() => openArtifact(a.id)}
                        className="w-full text-left rounded-lg border border-pearl-line/70 bg-white/70 p-2.5 hover:border-atelier-teal/35 hover:shadow-sm transition-all group"
                      >
                        <div className="flex items-center gap-1.5 mb-1">
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-atelier-teal-soft text-atelier-teal">
                            {a.kind_label || t(sec.title)}
                          </span>
                          {a.created_at && (
                            <span className="text-[9px] text-ink-faint inline-flex items-center gap-0.5">
                              <Clock className="w-2.5 h-2.5" />
                              {formatWhen(a.created_at)}
                            </span>
                          )}
                        </div>
                        <div className="text-[12px] font-semibold text-ink line-clamp-1 group-hover:text-atelier-teal">
                          {a.title}
                        </div>
                        <p className="text-[10px] text-ink-muted line-clamp-3 mt-1 leading-snug">
                          {a.preview || t('studio.map.clickToView')}
                        </p>
                        <div className="mt-1.5 text-[10px] text-ink-faint tabular-nums">
                          {t('studio.charCount', { count: a.word_count || 0 })} · {a.agent_name || t('studio.expert')}
                        </div>
                      </button>
                    ))}
                  </div>
                </AssetSection>
              );
            }
          )}
        </section>

        {/* Quick expert actions */}
        <section className="rounded-xl border border-white/60 bg-white/45 backdrop-blur-sm p-3">
          <div className="text-[11px] font-semibold text-ink mb-2 px-1">{t('studio.map.nextStep')}</div>
          <div className="flex flex-wrap gap-1.5">
            {[
              { id: 'short_drama_planner', label: t('studio.map.quickPlanning') },
              { id: 'character_profile_generator', label: t('studio.map.quickCast') },
              { id: 'character_relationship_analyzer', label: t('studio.map.quickRelations') },
              { id: 'major_plot_points', label: t('studio.map.quickPlot') },
              { id: 'short_drama_creator', label: t('studio.map.quickDialogue') },
              { id: 'short_drama_evaluation', label: t('studio.map.quickEval') },
              { id: 'mind_map', label: t('studio.map.quickMindmap') },
            ].map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => {
                  if (a.id === 'mind_map' && onAsk) {
                    onAsk('请为这部剧生成结构思维导图', 'mind_map');
                  } else {
                    askAgent(a.id);
                  }
                }}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-[11px] font-medium border border-pearl-line/80 bg-white/70 text-ink-muted hover:text-atelier-teal hover:border-atelier-teal/40 hover:bg-atelier-teal-soft transition-all"
              >
                {a.label}
                <ArrowRight className="w-3 h-3 opacity-50" />
              </button>
            ))}
          </div>
        </section>
      </div>

      {/* Detail drawer */}
      {(active || loadingDetail) && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-ink/25 backdrop-blur-[2px]" onClick={() => setActive(null)} />
          <aside className="relative w-full max-w-lg h-full bg-white/92 backdrop-blur-xl border-l border-white/60 shadow-atelier-lg flex flex-col animate-slide-up">
            <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-pearl-line">
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-wider text-ink-faint">
                  {active?.kind_label || t('studio.map.artifact')}
                </div>
                <h3 className="font-display text-xl font-semibold text-ink truncate mt-0.5">
                  {loadingDetail ? t('studio.loading') : active?.title}
                </h3>
                <p className="text-[11px] text-ink-muted mt-1">
                  {active?.agent_name}
                  {active?.created_at ? ` · ${formatWhen(active.created_at)}` : ''}
                  {active?.word_count ? ` · ${t('studio.charCount', { count: active.word_count })}` : ''}
                </p>
              </div>
              <button
                type="button"
                className="p-2 rounded-lg hover:bg-pearl-soft text-ink-muted"
                onClick={() => setActive(null)}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              {loadingDetail ? (
                <div className="space-y-2">
                  <div className="h-4 bg-pearl-soft animate-pulse rounded w-3/4" />
                  <div className="h-4 bg-pearl-soft animate-pulse rounded w-full" />
                </div>
              ) : (
                <StreamingText content={active?.content || t('studio.empty')} />
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function AssetSection({
  title,
  hint,
  icon: Icon,
  children,
  loading,
  empty,
  emptyText,
  emptyCta,
  onEmpty,
  compact,
}: {
  title: string;
  hint: string;
  icon: typeof FileText;
  children: ReactNode;
  loading?: boolean;
  empty?: boolean;
  emptyText?: string;
  emptyCta?: string;
  onEmpty?: () => void;
  compact?: boolean;
}) {
  return (
    <div
      className={clsx(
        'rounded-xl border border-white/60 bg-white/55 backdrop-blur-md shadow-atelier flex flex-col min-h-0',
        compact ? 'p-2.5' : 'p-3'
      )}
    >
      <div className="flex items-center justify-between gap-2 mb-2 px-0.5">
        <div className="flex items-center gap-1.5 min-w-0">
          <Icon className="w-3.5 h-3.5 text-atelier-teal shrink-0" />
          <span className="text-[13px] font-semibold text-ink truncate">{title}</span>
        </div>
        <span className="text-[10px] text-ink-faint shrink-0">{hint}</span>
      </div>
      {loading ? (
        <div className="space-y-1.5">
          <div className="h-14 bg-pearl-soft/80 animate-pulse rounded-lg" />
          <div className="h-14 bg-pearl-soft/80 animate-pulse rounded-lg" />
        </div>
      ) : empty ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-6 px-3">
          <p className="text-[11px] text-ink-muted leading-relaxed">{emptyText}</p>
          {onEmpty && emptyCta && (
            <button
              type="button"
              onClick={onEmpty}
              className="mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-atelier-teal hover:underline"
            >
              {emptyCta}
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
      ) : (
        children
      )}
    </div>
  );
}

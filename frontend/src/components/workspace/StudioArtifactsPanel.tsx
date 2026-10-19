/**
 * 作品 Artifacts — 策划 / 人物 / 情节点 / 评估等专家产物画廊
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Layers,
  Sparkles,
  Users,
  ListTree,
  BookOpen,
  BarChart3,
  PenLine,
  Search,
  Trash2,
  X,
  FileText,
  History,
} from 'lucide-react';
import clsx from 'clsx';
import {
  deleteDramaArtifact,
  getDramaArtifact,
  listDramaArtifacts,
  type DramaArtifact,
  type DramaArtifactMeta,
} from '@/services/dramaService';
import { useNotificationStore } from '@/store/notificationStore';
import DramaVersionPanel from './DramaVersionPanel';
import { useI18n } from '@/i18n';

const KIND_META: Record<
  string,
  { label: string; icon: typeof Sparkles; tone: string }
> = {
  planning: { label: 'studio.artifactKind.planning', icon: Sparkles, tone: 'text-atelier-teal bg-atelier-teal-soft' },
  story: { label: 'studio.artifactKind.story', icon: BookOpen, tone: 'text-atelier-teal bg-atelier-teal-soft' },
  plot: { label: 'studio.artifactKind.plot', icon: ListTree, tone: 'text-atelier-gold bg-atelier-gold-soft' },
  character: { label: 'studio.artifactKind.character', icon: Users, tone: 'text-atelier-teal bg-atelier-teal-soft' },
  evaluation: { label: 'studio.artifactKind.evaluation', icon: BarChart3, tone: 'text-atelier-gold bg-atelier-gold-soft' },
  creation: { label: 'studio.artifactKind.creation', icon: PenLine, tone: 'text-ink-muted bg-pearl-soft' },
  analysis: { label: 'studio.artifactKind.analysis', icon: Search, tone: 'text-ink-muted bg-pearl-soft' },
  other: { label: 'studio.artifactKind.other', icon: Layers, tone: 'text-ink-faint bg-pearl-soft' },
};

function formatWhen(iso?: string) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

type Props = {
  dramaId: string;
  className?: string;
};

export default function StudioArtifactsPanel({ dramaId, className }: Props) {
  const { t } = useI18n();
  const { success, error } = useNotificationStore();
  const [items, setItems] = useState<DramaArtifactMeta[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [kind, setKind] = useState<string>('all');
  const [q, setQ] = useState('');
  const [active, setActive] = useState<DramaArtifact | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [view, setView] = useState<'artifacts' | 'versions'>('artifacts');

  const reload = useCallback(async () => {
    if (!dramaId) return;
    setLoading(true);
    try {
      const res = await listDramaArtifacts(dramaId, { limit: 120 });
      setItems(res.artifacts || []);
      setCounts(res.counts || {});
    } catch {
      setItems([]);
      setCounts({});
    } finally {
      setLoading(false);
    }
  }, [dramaId]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    const onUpdate = (e: Event) => {
      const detail = (e as CustomEvent).detail as { dramaId?: string } | undefined;
      if (!detail?.dramaId || detail.dramaId === dramaId) reload();
    };
    window.addEventListener('drama-artifacts-updated', onUpdate);
    return () => window.removeEventListener('drama-artifacts-updated', onUpdate);
  }, [dramaId, reload]);

  const filtered = useMemo(() => {
    return items.filter((it) => {
      if (kind !== 'all' && it.kind !== kind) return false;
      if (!q.trim()) return true;
      const hay = `${it.title} ${it.agent_name || ''} ${it.preview || ''}`.toLowerCase();
      return hay.includes(q.toLowerCase());
    });
  }, [items, kind, q]);

  const kindTabs = useMemo(() => {
    const base = [{ id: 'all', label: 'common.all', count: items.length }];
    return base.concat(
      Object.entries(KIND_META).map(([id, meta]) => ({
        id,
        label: meta.label,
        count: counts[id] || 0,
      })).filter((t) => t.id === 'all' || t.count > 0 || kind === t.id)
    );
  }, [counts, items.length, kind]);

  const openArtifact = async (id: string) => {
    setLoadingDetail(true);
    try {
      const res = await getDramaArtifact(dramaId, id);
      if (res.artifact) setActive(res.artifact);
    } catch {
      error(t('studio.toast.loadFailed'), t('studio.toast.openArtifactFailed'));
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDelete = async (id: string, virtual?: boolean) => {
    if (virtual) return;
    try {
      await deleteDramaArtifact(dramaId, id);
      if (active?.id === id) setActive(null);
      success(t('dramas.toast.deleted'), '');
      reload();
    } catch {
      error(t('dramas.toast.deleteFailed'), '');
    }
  };

  if (view === 'versions') {
    return <DramaVersionPanel dramaId={dramaId} onBack={() => setView('artifacts')} />;
  }

  return (
    <div className={clsx('h-full flex flex-col min-h-0', className)}>
      <div className="px-4 sm:px-6 pt-4 pb-3 border-b border-pearl-line/70">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl font-semibold text-ink leading-none">{t('studio.artifacts.title')}</h2>
            <p className="text-[11px] text-ink-muted mt-1.5">
              {t('studio.artifacts.subtitle')}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0 pt-1">
            <button
              type="button"
              onClick={() => setView('versions')}
              className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-white/50 border border-pearl-line/70 text-ink-muted hover:bg-white hover:text-atelier-teal flex items-center gap-1"
            >
              <History className="w-3 h-3" /> {t('studio.artifacts.versionHistory')}
            </button>
            <span className="text-[11px] tabular-nums text-ink-faint">
              {t('studio.artifacts.count', { count: items.length })}
            </span>
          </div>
        </div>

        <div className="mt-3 relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-faint" />
          <input
            className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-pearl-line/80 bg-white/50 backdrop-blur-sm focus:outline-none focus:border-atelier-teal"
            placeholder={t('studio.artifacts.searchPlaceholder')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>

        <div className="mt-3 flex flex-wrap gap-1">
          {kindTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setKind(tab.id)}
              className={clsx(
                'px-2.5 py-1 rounded-full text-[11px] font-medium transition-all duration-200',
                kind === tab.id
                  ? 'bg-atelier-teal text-white shadow-sm'
                  : 'bg-white/50 text-ink-muted hover:bg-atelier-teal-soft hover:text-atelier-teal'
              )}
            >
              {t(tab.label)}
              {tab.count > 0 && <span className="ml-1 opacity-70 tabular-nums">{tab.count}</span>}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5">
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="h-20 rounded-xl bg-pearl-soft/70 animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="h-full min-h-[240px] flex flex-col items-center justify-center text-center px-6">
            <div className="w-14 h-14 rounded-2xl bg-atelier-teal-soft text-atelier-teal flex items-center justify-center mb-3">
              <FileText className="w-6 h-6" />
            </div>
            <p className="font-display text-lg font-semibold text-ink">{t('studio.artifacts.empty')}</p>
            <p className="text-xs text-ink-muted mt-2 max-w-xs leading-relaxed">
              {t('studio.artifacts.emptyHint')}
            </p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-2.5 stagger-children">
            {filtered.map((it) => {
              const km = KIND_META[it.kind] || KIND_META.other;
              const Icon = km.icon;
              return (
                <button
                  key={it.id}
                  type="button"
                  onClick={() => openArtifact(it.id)}
                  className={clsx(
                    'text-left rounded-xl border border-white/60 bg-white/50 backdrop-blur-sm p-3.5',
                    'hover:bg-white/85 hover:border-atelier-teal/30 hover:shadow-atelier transition-all duration-200 group'
                  )}
                >
                  <div className="flex items-start gap-2.5">
                    <div
                      className={clsx(
                        'w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
                        km.tone
                      )}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-medium text-ink-faint">{t(km.label)}</span>
                        {it.virtual && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-pearl-soft text-ink-faint">
                            {t('studio.artifacts.system')}
                          </span>
                        )}
                      </div>
                      <div className="text-sm font-semibold text-ink truncate mt-0.5 group-hover:text-atelier-teal">
                        {it.title}
                      </div>
                      <p className="text-[11px] text-ink-muted line-clamp-2 mt-1 leading-snug">
                        {it.preview || t('studio.artifacts.noPreview')}
                      </p>
                      <div className="mt-2 flex items-center gap-2 text-[10px] text-ink-faint">
                        <span className="truncate">{it.agent_name || it.agent_id || t('studio.expert')}</span>
                        <span>·</span>
                        <span className="tabular-nums">{t('studio.charCount', { count: it.word_count || 0 })}</span>
                        {it.created_at && (
                          <>
                            <span>·</span>
                            <span>{formatWhen(it.created_at)}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Detail drawer */}
      {(active || loadingDetail) && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-ink/25 backdrop-blur-[2px]" onClick={() => setActive(null)} />
          <aside className="relative w-full max-w-lg h-full bg-white/90 backdrop-blur-xl border-l border-white/60 shadow-atelier-lg flex flex-col animate-slide-up">
            <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-pearl-line">
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-wider text-ink-faint">
                  {active?.kind_label || t(KIND_META[active?.kind || '']?.label || 'studio.artifacts.artifact')}
                </div>
                <h3 className="font-display text-xl font-semibold text-ink truncate mt-0.5">
                  {loadingDetail ? t('studio.loading') : active?.title}
                </h3>
                <p className="text-[11px] text-ink-muted mt-1">
                  {active?.agent_name || active?.agent_id}
                  {active?.created_at ? ` · ${formatWhen(active.created_at)}` : ''}
                  {active?.word_count ? ` · ${t('studio.charCount', { count: active.word_count })}` : ''}
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {active && !active.virtual && (
                  <button
                    type="button"
                    className="p-2 rounded-lg text-ink-faint hover:text-red-600 hover:bg-red-50"
                    title={t('common.delete')}
                    onClick={() => handleDelete(active.id, active.virtual)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
                <button
                  type="button"
                  className="p-2 rounded-lg hover:bg-pearl-soft text-ink-muted"
                  onClick={() => setActive(null)}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              {loadingDetail ? (
                <div className="space-y-2">
                  <div className="h-4 bg-pearl-soft animate-pulse rounded w-3/4" />
                  <div className="h-4 bg-pearl-soft animate-pulse rounded w-full" />
                  <div className="h-4 bg-pearl-soft animate-pulse rounded w-5/6" />
                </div>
              ) : (
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
                  {active?.content || t('studio.empty')}
                </pre>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

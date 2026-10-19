/**
 * 剧本片段版本历史 — 展示 小传/大纲/世界观/剧本 的改前/改后 diff 与版本链
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { History, GitCommit, ChevronLeft, Clock, User, RotateCcw, ArrowLeftRight, X } from 'lucide-react';
import clsx from 'clsx';
import {
  listDramaVersions,
  getDramaVersion,
  rollbackDramaVersion,
  readDramaPart,
  type DramaVersion,
  type DramaPartTarget,
} from '@/services/dramaService';
import SideBySideDiff from './SideBySideDiff';
import { useI18n } from '@/i18n';

const TARGET_LABEL: Record<string, string> = {
  world: 'studio.version.target.world',
  characters: 'studio.version.target.characters',
  outline: 'studio.version.target.outline',
  episode: 'studio.version.target.episode',
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

/** 把 unified diff 文本渲染成带红/绿着色的行 */
function DiffLines({ diff }: { diff?: string }) {
  const { t } = useI18n();
  const lines = useMemo(() => (diff || '').split('\n'), [diff]);
  if (!diff) {
    return <p className="text-xs text-ink-faint">{t('studio.diff.none')}</p>;
  }
  return (
    <pre className="text-[11px] leading-relaxed font-mono overflow-x-auto p-3 rounded-lg bg-pearl-soft/60 whitespace-pre-wrap">
      {lines.map((line, i) => {
        let cls = 'text-ink-muted';
        if (line.startsWith('+++') || line.startsWith('---')) cls = 'text-ink-faint font-semibold';
        else if (line.startsWith('@@')) cls = 'text-atelier-teal font-semibold';
        else if (line.startsWith('+')) cls = 'text-emerald-600 bg-emerald-50';
        else if (line.startsWith('-')) cls = 'text-rose-600 bg-rose-50';
        return (
          <div key={i} className={cls}>
            {line || ' '}
          </div>
        );
      })}
    </pre>
  );
}

type Props = {
  dramaId: string;
  onBack?: () => void;
};

export default function DramaVersionPanel({ dramaId, onBack }: Props) {
  const { t } = useI18n();
  const [versions, setVersions] = useState<DramaVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [target, setTarget] = useState<string>('all');
  const [active, setActive] = useState<DramaVersion | null>(null);
  const [tab, setTab] = useState<'diff' | 'side' | 'before' | 'after'>('diff');
  const [restoring, setRestoring] = useState(false);
  const [compareBase, setCompareBase] = useState<DramaVersion | null>(null);
  const [compareResult, setCompareResult] = useState<{ base: DramaVersion; other: DramaVersion } | null>(null);
  const [rollbackConfirm, setRollbackConfirm] = useState<{ target: DramaVersion; current: string } | null>(null);

  const reload = useCallback(async () => {
    if (!dramaId) return;
    setLoading(true);
    try {
      const res = await listDramaVersions(dramaId);
      setVersions(res.versions || []);
    } catch {
      setVersions([]);
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

  const openVersion = async (versionId: string) => {
    try {
      const res = await getDramaVersion(dramaId, versionId);
      if (res.version) {
        setActive(res.version);
        setTab('diff');
      }
    } catch {
      /* ignore */
    }
  };

  const handleCompareClick = async (v: DramaVersion) => {
    try {
      const res = await getDramaVersion(dramaId, v.version_id);
      const full = res.version;
      if (!full) return;
      if (!compareBase || compareBase.version_id === full.version_id) {
        setCompareBase(full);
        setCompareResult(null);
      } else {
        setCompareResult({ base: compareBase, other: full });
        setCompareBase(null);
      }
    } catch {
      /* ignore */
    }
  };

  const handleRestoreClick = async () => {
    if (!active) return;
    let current = '';
    try {
      const res = await readDramaPart(
        dramaId,
        active.target as DramaPartTarget,
        active.episode_number ?? undefined
      );
      current = res.part?.content || '';
    } catch {
      /* 读不到当前内容就降级为无 diff 的确认 */
    }
    setRollbackConfirm({ target: active, current });
  };

  const doRollback = async () => {
    if (!rollbackConfirm) return;
    const { target } = rollbackConfirm;
    setRestoring(true);
    try {
      await rollbackDramaVersion(dramaId, target.version_id, { agent_name: 'user' });
      window.dispatchEvent(new CustomEvent('drama-artifacts-updated', { detail: { dramaId } }));
      await reload();
      setRollbackConfirm(null);
      setActive(null);
    } catch {
      /* ignore */
    } finally {
      setRestoring(false);
    }
  };

  const filtered = useMemo(() => {
    if (target === 'all') return versions;
    return versions.filter((v) => v.target === target);
  }, [versions, target]);

  const targets = useMemo(() => {
    const seen = new Map<string, number>();
    versions.forEach((v) => seen.set(v.target, (seen.get(v.target) || 0) + 1));
    return Array.from(seen.entries()).map(([id, count]) => ({ id, label: TARGET_LABEL[id] || id, count }));
  }, [versions]);

  return (
    <div className="h-full flex flex-col min-h-0">
      <div className="px-4 sm:px-6 pt-4 pb-3 border-b border-pearl-line/70">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl font-semibold text-ink leading-none">{t('studio.version.title')}</h2>
            <p className="text-[11px] text-ink-muted mt-1.5">
              {t('studio.version.subtitle')}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0 pt-1">
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-white/50 border border-pearl-line/70 text-ink-muted hover:bg-white"
              >
                {t('studio.version.back')}
              </button>
            )}
            <span className="text-[11px] tabular-nums text-ink-faint">{t('studio.version.count', { count: versions.length })}</span>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setTarget('all')}
            className={clsx(
              'px-2.5 py-1 rounded-full text-[11px] font-medium transition-all',
              target === 'all' ? 'bg-atelier-teal text-white' : 'bg-white/50 text-ink-muted'
            )}
          >
            {t('studio.version.all', { count: versions.length })}
          </button>
          {targets.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setTarget(tab.id)}
              className={clsx(
                'px-2.5 py-1 rounded-full text-[11px] font-medium transition-all',
                target === tab.id ? 'bg-atelier-teal text-white' : 'bg-white/50 text-ink-muted'
              )}
            >
              {t(tab.label)} {tab.count}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5">
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-16 rounded-xl bg-pearl-soft/70 animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="h-full min-h-[240px] flex flex-col items-center justify-center text-center px-6">
            <History className="w-8 h-8 text-ink-faint mb-3" />
            <p className="text-sm text-ink-muted">{t('studio.version.empty')}</p>
            <p className="text-xs text-ink-faint mt-1">{t('studio.version.emptyHint')}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((v) => (
              <div
                key={v.version_id}
                role="button"
                tabIndex={0}
                onClick={() => openVersion(v.version_id)}
                className={clsx(
                  'w-full text-left rounded-xl border border-white/60 bg-white/50 p-3.5 cursor-pointer',
                  'hover:bg-white/85 hover:border-atelier-teal/30 transition-all group',
                  compareBase?.version_id === v.version_id && 'ring-2 ring-atelier-teal border-atelier-teal'
                )}
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-atelier-teal-soft text-atelier-teal flex items-center justify-center shrink-0">
                    <GitCommit className="w-3.5 h-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-atelier-teal-soft text-atelier-teal">
                        {v.target_label || t(TARGET_LABEL[v.target] || v.target)}
                      </span>
                      <span className="text-xs font-semibold text-ink truncate">
                        {v.title || (v.episode_number ? t('studio.ep', { n: v.episode_number }) : t('studio.version.contentEdit'))}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[10px] text-ink-faint">
                      <span className="truncate flex items-center gap-1">
                        <User className="w-3 h-3" /> {v.agent_name || v.agent_id || t('studio.expert')}
                      </span>
                      <span>·</span>
                      <span className="tabular-nums">{t('studio.charCount', { count: v.word_count || 0 })}</span>
                      <span>·</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {formatWhen(v.created_at)}
                      </span>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-ink-faint shrink-0">{v.version_id}</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCompareClick(v);
                    }}
                    className={clsx(
                      'shrink-0 px-2 py-1 rounded-md text-[10px] font-medium flex items-center gap-1 border transition-all',
                      compareBase?.version_id === v.version_id
                        ? 'bg-atelier-teal text-white border-atelier-teal'
                        : 'text-ink-muted border-pearl-line/70 hover:bg-atelier-teal-soft hover:text-atelier-teal'
                    )}
                  >
                    <ArrowLeftRight className="w-3 h-3" /> {t('studio.version.compare')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 版本详情抽屉 */}
      {active && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-ink/25 backdrop-blur-[2px]" onClick={() => setActive(null)} />
          <aside className="relative w-full max-w-2xl h-full bg-white/90 backdrop-blur-xl border-l border-white/60 shadow-atelier-lg flex flex-col animate-slide-up">
            <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-pearl-line">
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-wider text-ink-faint flex items-center gap-1">
                  <History className="w-3 h-3" /> {active.target_label || t(TARGET_LABEL[active.target] || active.target)}
                </div>
                <h3 className="font-display text-lg font-semibold text-ink truncate mt-0.5">
                  {active.title || (active.episode_number ? t('studio.ep', { n: active.episode_number }) : t('studio.version.contentEdit'))}
                </h3>
                <p className="text-[11px] text-ink-muted mt-1">
                  {active.agent_name || active.agent_id} · {formatWhen(active.created_at)} ·{' '}
                  <span className="font-mono">{active.version_id}</span>
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  disabled={restoring}
                  onClick={handleRestoreClick}
                  className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-atelier-teal text-white hover:bg-atelier-teal/90 disabled:opacity-50 flex items-center gap-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> {restoring ? t('studio.version.restoring') : t('studio.version.restore')}
                </button>
                <button
                  type="button"
                  className="p-2 rounded-lg hover:bg-pearl-soft text-ink-muted flex items-center gap-1 text-xs"
                  onClick={() => setActive(null)}
                >
                  <ChevronLeft className="w-4 h-4" /> {t('studio.back')}
                </button>
              </div>
            </div>

            <div className="flex gap-1 px-5 pt-3 border-b border-pearl-line/60 pb-2">
              {(['diff', 'side', 'before', 'after'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setTab(mode)}
                  className={clsx(
                    'px-3 py-1.5 rounded-t-lg text-xs font-medium transition-all',
                    tab === mode ? 'bg-atelier-teal text-white' : 'text-ink-muted hover:bg-pearl-soft'
                  )}
                >
                  {mode === 'diff'
                    ? t('studio.version.tab.diff')
                    : mode === 'side'
                      ? t('studio.version.tab.side')
                      : mode === 'before'
                        ? t('studio.version.tab.before')
                        : t('studio.version.tab.after')}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4">
              {tab === 'diff' ? (
                <DiffLines diff={active.diff} />
              ) : tab === 'side' ? (
                <SideBySideDiff before={active.before} after={active.after} />
              ) : (
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink bg-pearl-soft/40 rounded-lg p-4">
                  {tab === 'before' ? active.before || t('studio.empty') : active.after || t('studio.empty')}
                </pre>
              )}
            </div>
          </aside>
        </div>
      )}

      {/* 两两对比：基准提示 */}
      {compareBase && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-4 py-2 rounded-full bg-ink text-white shadow-atelier-lg text-xs">
          <span className="font-mono">{compareBase.version_id}</span>
          <span>{t('studio.version.compareHint')}</span>
          <button type="button" className="text-white/70 hover:text-white underline" onClick={() => setCompareBase(null)}>
            {t('common.cancel')}
          </button>
        </div>
      )}

      {/* 两两对比结果抽屉 */}
      {compareResult && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-ink/25 backdrop-blur-[2px]" onClick={() => setCompareResult(null)} />
          <aside className="relative w-full max-w-3xl h-full bg-white/90 backdrop-blur-xl border-l border-white/60 shadow-atelier-lg flex flex-col animate-slide-up">
            <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-pearl-line">
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-wider text-ink-faint">{t('studio.version.compareTitle')}</div>
                <h3 className="font-display text-lg font-semibold text-ink mt-0.5 flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-sm">{compareResult.base.version_id}</span>
                  <ArrowLeftRight className="w-4 h-4 text-ink-faint" />
                  <span className="font-mono text-sm">{compareResult.other.version_id}</span>
                </h3>
              </div>
              <button type="button" className="p-2 rounded-lg hover:bg-pearl-soft text-ink-muted" onClick={() => setCompareResult(null)}>
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              <SideBySideDiff before={compareResult.base.after} after={compareResult.other.after} />
            </div>
          </aside>
        </div>
      )}

      {/* 回滚二次确认（带 diff 预览） */}
      {rollbackConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-ink/25 backdrop-blur-[2px]" onClick={() => setRollbackConfirm(null)} />
          <div className="relative w-full max-w-2xl max-h-[85vh] bg-white/95 backdrop-blur-xl rounded-2xl shadow-atelier-lg flex flex-col animate-slide-up">
            <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-pearl-line">
              <div className="min-w-0">
                <h3 className="font-display text-lg font-semibold text-ink">{t('studio.version.confirmRestore')}</h3>
                <p className="text-[11px] text-ink-muted mt-0.5">
                  {t('studio.version.confirmHint', {
                    target: rollbackConfirm.target.target_label || t(TARGET_LABEL[rollbackConfirm.target.target] || rollbackConfirm.target.target),
                    id: rollbackConfirm.target.version_id,
                  })}
                </p>
              </div>
              <button type="button" className="p-2 rounded-lg hover:bg-pearl-soft text-ink-muted" onClick={() => setRollbackConfirm(null)}>
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              <SideBySideDiff before={rollbackConfirm.current} after={rollbackConfirm.target.after} />
            </div>
            <div className="flex justify-end gap-2 px-5 py-4 border-t border-pearl-line">
              <button type="button" className="px-4 py-2 rounded-lg text-sm text-ink-muted hover:bg-pearl-soft" onClick={() => setRollbackConfirm(null)}>
                {t('common.cancel')}
              </button>
              <button
                type="button"
                disabled={restoring}
                onClick={doRollback}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-atelier-teal text-white hover:bg-atelier-teal/90 disabled:opacity-50 flex items-center gap-1"
              >
                <RotateCcw className="w-4 h-4" /> {restoring ? t('studio.version.restoring') : t('studio.version.confirmRestore')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

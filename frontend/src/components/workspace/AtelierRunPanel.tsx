/**
 * Studio 内 Atelier 编排面板：步骤进度 / 执行下一步 / 跳过 / 改约束
 */

import { useEffect, useState } from 'react';
import {
  Check,
  ChevronDown,
  ChevronUp,
  Loader2,
  Play,
  SkipForward,
  Sparkles,
} from 'lucide-react';
import clsx from 'clsx';
import {
  getAtelierRun,
  patchAtelierRun,
  startAtelierStep,
  type AtelierRun,
  type AtelierStep,
} from '@/services/atelierService';
import { useNotificationStore } from '@/store/notificationStore';
import { useAgentStore } from '@/store/agentStore';
import { useI18n } from '@/i18n';

interface Props {
  runId: string;
  dramaId: string;
  onRunUpdated?: (run: AtelierRun) => void;
  onArtifactsMaybeChanged?: () => void;
}

export default function AtelierRunPanel({
  runId,
  dramaId,
  onRunUpdated,
  onArtifactsMaybeChanged,
}: Props) {
  const { t } = useI18n();
  const { success, error } = useNotificationStore();
  const { setActiveAgent } = useAgentStore();
  const [run, setRun] = useState<AtelierRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [streamLog, setStreamLog] = useState('');
  const [showConstraints, setShowConstraints] = useState(false);
  const [episodes, setEpisodes] = useState(80);
  const [genre, setGenre] = useState('都市情感');

  const reload = async () => {
    const res = await getAtelierRun(runId, dramaId);
    if (res.success && res.run) {
      setRun(res.run);
      setEpisodes(res.run.constraints?.total_episodes || 80);
      setGenre(res.run.constraints?.genre || '都市情感');
      onRunUpdated?.(res.run);
      return res.run;
    }
    return null;
  };

  useEffect(() => {
    setLoading(true);
    reload()
      .catch(() => error(t('studio.toast.loadFailed'), t('studio.atelier.loadFailed')))
      .finally(() => setLoading(false));
  }, [runId, dramaId]);

  const nextStep = run?.steps.find(
    (s) => s.enabled && (s.status === 'pending' || s.status === 'error')
  );

  const handleStart = async (step: AtelierStep) => {
    if (!run || busy) return;
    setBusy(true);
    setStreamLog('');
    setActiveAgent(step.agent_id);
    try {
      await startAtelierStep(
        run.run_id,
        step.id,
        { drama_id: dramaId },
        {
          onChunk: (t) => setStreamLog((prev) => (prev + t).slice(-4000)),
          onEvent: (ev, data) => {
            if (ev === 'system') {
              const text = typeof data === 'string' ? data : '';
              if (text) setStreamLog((prev) => `${prev}\n[${text}]\n`.slice(-4000));
            }
          },
          onComplete: async () => {
            const updated = await reload();
            onArtifactsMaybeChanged?.();
            window.dispatchEvent(
              new CustomEvent('drama-artifacts-updated', { detail: { dramaId } })
            );
            success(t('studio.toast.stepDone'), step.title);
            if (updated?.status === 'completed') {
              success(t('studio.toast.runDone'), t('studio.toast.runDoneHint'));
            }
          },
          onError: (msg) => error(t('studio.toast.stepFailed'), msg),
        }
      );
      await reload();
      onArtifactsMaybeChanged?.();
    } catch (e) {
      error(t('studio.toast.runFailed'), e instanceof Error ? e.message : '');
      await reload();
    } finally {
      setBusy(false);
    }
  };

  const handleSkip = async (step: AtelierStep) => {
    if (!run || busy) return;
    setBusy(true);
    try {
      const steps = run.steps.map((s) =>
        s.id === step.id ? { ...s, enabled: false, status: 'skipped' } : s
      );
      const res = await patchAtelierRun(run.run_id, { steps, drama_id: dramaId });
      if (res.run) {
        setRun(res.run);
        onRunUpdated?.(res.run);
        success(t('studio.toast.skipped'), step.title);
      }
    } catch (e) {
      error(t('studio.toast.skipFailed'), e instanceof Error ? e.message : '');
    } finally {
      setBusy(false);
    }
  };

  const handleSaveConstraints = async () => {
    if (!run || busy) return;
    setBusy(true);
    try {
      const res = await patchAtelierRun(run.run_id, {
        drama_id: dramaId,
        constraints: { total_episodes: episodes, genre },
      });
      if (res.run) {
        setRun(res.run);
        onRunUpdated?.(res.run);
        success(t('studio.atelier.constraintsUpdated'), t('studio.atelier.episodesHint', { count: episodes, genre }));
      }
    } catch (e) {
      error(t('studio.toast.updateFailed'), e instanceof Error ? e.message : '');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="p-4 text-sm text-ink-muted flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin" />
        {t('studio.atelier.loading')}
      </div>
    );
  }

  if (!run) {
    return <div className="p-4 text-sm text-ink-muted">{t('studio.atelier.notFound')}</div>;
  }

  const doneCount = run.steps.filter((s) => s.status === 'done').length;
  const totalEnabled = run.steps.filter((s) => s.enabled || s.status === 'done').length;

  return (
    <div className="flex flex-col h-full min-h-0 border-b border-pearl-line bg-white/70">
      <div className="px-3 py-2.5 flex items-center justify-between gap-2 shrink-0">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-atelier-teal">
            <Sparkles className="w-3.5 h-3.5" />
            {t('studio.atelier.title')}
          </div>
          <p className="text-xs text-ink-muted truncate mt-0.5">
            {doneCount}/{totalEnabled || run.steps.length} · {run.status}
          </p>
        </div>
        <button
          type="button"
          className="btn btn-ghost btn-sm px-2"
          onClick={() => setShowConstraints((v) => !v)}
        >
          {showConstraints ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {showConstraints && (
        <div className="px-3 pb-3 space-y-2 border-b border-pearl-line/60">
          <label className="block text-[11px] text-ink-faint">
            {t('studio.atelier.genre')}
            <input
              className="mt-1 w-full rounded-lg border border-pearl-line bg-white px-2 py-1.5 text-sm"
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
            />
          </label>
          <label className="block text-[11px] text-ink-faint">
            {t('studio.atelier.episodes')}
            <input
              type="number"
              min={1}
              max={200}
              className="mt-1 w-full rounded-lg border border-pearl-line bg-white px-2 py-1.5 text-sm"
              value={episodes}
              onChange={(e) => setEpisodes(Number(e.target.value) || 80)}
            />
          </label>
          <button
            type="button"
            className="btn btn-secondary btn-sm w-full"
            disabled={busy}
            onClick={() => void handleSaveConstraints()}
          >
            {t('studio.atelier.saveConstraints')}
          </button>
        </div>
      )}

      <ol className="px-3 py-2 space-y-1.5 overflow-y-auto max-h-48 shrink-0">
        {run.steps.map((step, idx) => {
          const isNext = nextStep?.id === step.id;
          return (
            <li
              key={step.id}
              className={clsx(
                'rounded-lg px-2.5 py-2 text-xs border transition-colors',
                step.status === 'done' && 'border-atelier-teal/30 bg-atelier-teal-soft/40',
                step.status === 'running' && 'border-atelier-gold/40 bg-atelier-gold-soft/50',
                step.status === 'skipped' && 'border-pearl-line/50 opacity-50',
                step.status === 'error' && 'border-red-300 bg-red-50',
                isNext && step.status === 'pending' && 'border-atelier-teal bg-white'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-medium text-ink truncate">
                    {idx + 1}. {step.title}
                  </div>
                  <div className="text-[10px] text-ink-faint mt-0.5 truncate">
                    {step.status === 'skipped' ? t('studio.atelier.skipped') : step.rationale}
                  </div>
                </div>
                {step.status === 'done' && <Check className="w-3.5 h-3.5 text-atelier-teal shrink-0" />}
                {step.status === 'running' && (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-atelier-gold shrink-0" />
                )}
              </div>
            </li>
          );
        })}
      </ol>

      <div className="px-3 pb-3 flex flex-wrap gap-2 shrink-0">
        {nextStep ? (
          <>
            <button
              type="button"
              className="btn btn-primary btn-sm flex-1"
              disabled={busy}
              onClick={() => void handleStart(nextStep)}
            >
              {busy ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}
              {t('studio.atelier.run', { title: nextStep.title })}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={busy}
              onClick={() => void handleSkip(nextStep)}
              title={t('studio.atelier.skipStep')}
            >
              <SkipForward className="w-3.5 h-3.5" />
            </button>
          </>
        ) : (
          <p className="text-xs text-ink-muted py-1">
            {run.status === 'completed' ? t('studio.atelier.allDone') : t('studio.atelier.noPending')}
          </p>
        )}
      </div>

      {(busy || streamLog) && (
        <div className="px-3 pb-3 min-h-0 flex-1 overflow-hidden">
          <pre className="text-[10px] leading-relaxed text-ink-muted bg-pearl-soft/80 rounded-lg p-2 max-h-32 overflow-y-auto whitespace-pre-wrap break-words">
            {streamLog || t('studio.generating')}
          </pre>
        </div>
      )}
    </div>
  );
}

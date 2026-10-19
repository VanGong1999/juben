import { useEffect, useState } from 'react';
import { X, RotateCcw } from 'lucide-react';
import clsx from 'clsx';
import { useI18n } from '@/i18n';
import { getMemoryVersion } from '@/services/memoryService';

export default function VersionDiffDrawer({
  dramaId,
  versions,
  onClose,
  onRollback,
}: {
  dramaId: string;
  versions: any[];
  onClose: () => void;
  onRollback?: (versionId: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(versions[0]?.version_id || null);
  const [detail, setDetail] = useState<any>(null);
  const [view, setView] = useState<'diff' | 'before' | 'after'>('diff');
  const { t } = useI18n();

  useEffect(() => {
    if (!selected) return;
    getMemoryVersion(dramaId, selected)
      .then((res) => setDetail(res.data || null))
      .catch(() => setDetail(null));
  }, [dramaId, selected]);

  const targetLabel = (target: string) =>
    ({ rules: t('dataViews.versionDiff.rules'), memory: t('dataViews.versionDiff.memory'), user: t('dataViews.versionDiff.user'), org: t('dataViews.versionDiff.org') } as Record<string, string>)[target] || target;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-ink/20" onClick={onClose} />
      <div className="relative w-full max-w-2xl h-full bg-paper-white shadow-xl flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-studio-line">
          <div>
            <h3 className="font-display font-semibold text-ink">{t('dataViews.versionDiff.title')}</h3>
            <p className="text-xs text-ink-muted">{t('dataViews.versionDiff.hint')}</p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4 grid grid-cols-[240px_1fr] gap-4">
          <div className="space-y-1 overflow-auto">
            {versions.map((v) => (
              <button
                key={v.version_id}
                type="button"
                onClick={() => setSelected(v.version_id)}
                className={clsx(
                  'w-full text-left px-3 py-2 rounded-lg text-xs border',
                  selected === v.version_id ? 'border-studio-teal bg-studio-teal/5' : 'border-transparent hover:bg-ink/[0.03]'
                )}
              >
                <div className="font-medium text-ink">{targetLabel(v.target)} · {v.version_id}</div>
                <div className="text-ink-faint">{String(v.created_at || '').slice(0, 19)}</div>
                {v.agent_id && <div className="text-ink-faint font-mono">{v.agent_id}</div>}
              </button>
            ))}
          </div>

          <div className="space-y-2 min-w-0">
            {detail && (
              <div className="flex items-center gap-1 mb-1">
                {(['diff', 'before', 'after'] as const).map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setView(v)}
                    className={clsx(
                      'px-2 py-1 text-xs rounded-lg border',
                      view === v ? 'bg-studio-teal text-white border-studio-teal' : 'border-studio-line text-ink-muted'
                    )}
                  >
                    {v === 'diff' ? 'Diff' : v === 'before' ? t('dataViews.versionDiff.before') : t('dataViews.versionDiff.after')}
                  </button>
                ))}
                {onRollback && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm ml-auto"
                    onClick={() => onRollback(selected!)}
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    {t('dataViews.versionDiff.rollback')}
                  </button>
                )}
              </div>
            )}
            <pre className="text-xs whitespace-pre-wrap font-mono surface-panel p-3 overflow-auto min-h-[300px] text-ink-muted">
              {detail
                ? view === 'diff'
                  ? detail.diff || t('dataViews.versionDiff.noDiff')
                  : view === 'before'
                  ? detail.before
                  : detail.after
                : t('dataViews.versionDiff.loading')}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}

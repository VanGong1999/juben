import { Pin, Trash2, Brain } from 'lucide-react';
import clsx from 'clsx';
import { useI18n } from '@/i18n';
import MemoryDataTable, { type Column } from './MemoryDataTable';

const outcomeStyle: Record<string, string> = {
  success: 'bg-emerald-50 text-emerald-800',
  failure: 'bg-rose-50 text-rose-800',
  partial: 'bg-amber-50 text-amber-800',
  cancelled: 'bg-slate-100 text-slate-600',
};

export default function EpisodesTable({
  rows,
  onPin,
  onReflect,
  onDelete,
}: {
  rows: any[];
  onPin?: (ep: any) => void;
  onReflect?: (ep: any) => void;
  onDelete?: (ep: any) => void;
}) {
  const { t } = useI18n();
  const columns: Column<any>[] = [
    {
      key: 'outcome',
      label: t('dataViews.episodes.result'),
      filter: true,
      render: (e) => (
        <span className={clsx('text-[10px] uppercase px-1.5 py-0.5 rounded', outcomeStyle[e.outcome] || 'bg-ink/[0.06] text-ink-muted')}>
          {e.outcome}
        </span>
      ),
    },
    {
      key: 'pinned',
      label: t('dataViews.table.pin'),
      render: (e) => (e.pinned ? <Pin className="w-3.5 h-3.5 text-studio-teal" /> : null),
    },
    { key: 'task_description', label: t('dataViews.episodes.task'), render: (e) => <span className="text-ink">{String(e.task_description || '').slice(0, 90)}</span> },
    { key: 'agent_id', label: 'Agent', filter: true, sortable: true, className: 'font-mono text-xs' },
    { key: 'session_id', label: t('dataViews.episodes.session'), className: 'font-mono text-xs text-ink-faint' },
    {
      key: 'tags',
      label: t('dataViews.episodes.tag'),
      render: (e) => (
        <span className="text-xs text-ink-faint">{(e.tags || []).join(', ')}</span>
      ),
    },
    {
      key: 'tokens_used',
      label: 'Tokens',
      sortable: true,
      render: (e) => <span className="text-xs font-mono text-ink-faint">{e.tokens_used ?? 0}</span>,
    },
    {
      key: 'duration_seconds',
      label: t('dataViews.episodes.duration'),
      sortable: true,
      render: (e) => <span className="text-xs font-mono text-ink-faint">{Number(e.duration_seconds ?? 0).toFixed(1)}</span>,
    },
    {
      key: 'created_at',
      label: t('dataViews.table.time'),
      sortable: true,
      render: (e) => <span className="text-xs text-ink-faint">{String(e.created_at || '').slice(0, 16)}</span>,
    },
    {
      key: '_actions',
      label: '',
      render: (e) => (
        <span className="flex gap-1">
          {onPin && (
            <button type="button" className="btn btn-ghost btn-sm !px-1.5" title={t('dataViews.table.pinAction')} onClick={() => onPin(e)}>
              <Pin className="w-3.5 h-3.5" />
            </button>
          )}
          {onReflect && (
            <button type="button" className="btn btn-ghost btn-sm !px-1.5" title={t('dataViews.episodes.reflect')} onClick={() => onReflect(e)}>
              <Brain className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button type="button" className="btn btn-ghost btn-sm !px-1.5 text-rose-700" title={t('common.delete')} onClick={() => onDelete(e)}>
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </span>
      ),
    },
  ];

  return (
    <MemoryDataTable
      rows={rows}
      columns={columns}
      rowKey={(e) => e.episode_id}
      searchKeys={['task_description', 'approach', 'resolution', 'agent_id']}
      searchPlaceholder={t('dataViews.episodes.search')}
      emptyText={t('dataViews.episodes.empty')}
      expand={(e) => (
        <div className="space-y-2 text-xs">
          <div><span className="text-ink-faint">approach：</span>{e.approach || '—'}</div>
          <div><span className="text-ink-faint">resolution：</span>{e.resolution || '—'}</div>
          {e.key_decisions?.length > 0 && <div><span className="text-ink-faint">key_decisions：</span>{(e.key_decisions || []).join('；')}</div>}
          {e.errors?.length > 0 && <div className="text-rose-700"><span className="text-ink-faint">errors：</span>{(e.errors || []).join('；')}</div>}
        </div>
      )}
    />
  );
}

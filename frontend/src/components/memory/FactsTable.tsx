import { useState } from 'react';
import { Pin, Trash2 } from 'lucide-react';
import clsx from 'clsx';
import { useI18n } from '@/i18n';
import MemoryDataTable, { type Column } from './MemoryDataTable';

const statusStyle: Record<string, string> = {
  active: 'bg-emerald-50 text-emerald-800',
  superseded: 'bg-slate-100 text-slate-600',
  archived: 'bg-ink/[0.06] text-ink-muted',
  flagged: 'bg-amber-50 text-amber-800',
};

function confidenceStyle(c: string): string {
  if (c === 'fact') return 'bg-sky-50 text-sky-800';
  if (c === 'inference') return 'bg-violet-50 text-violet-800';
  if (c === 'preference') return 'bg-rose-50 text-rose-800';
  return 'bg-slate-100 text-slate-600';
}

function Truncated({ text, max = 80 }: { text: string; max?: number }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const s = String(text ?? '');
  if (s.length <= max) return <span className="text-ink-muted">{s}</span>;
  return (
    <span className="text-ink-muted">
      {open ? s : `${s.slice(0, max)}…`}
      <button type="button" className="ml-1 text-studio-teal text-xs" onClick={() => setOpen(!open)}>
        {open ? t('dataViews.common.collapse') : t('dataViews.common.expand')}
      </button>
    </span>
  );
}

export default function FactsTable({
  rows,
  onPin,
  onDelete,
}: {
  rows: any[];
  onPin?: (fact: any) => void;
  onDelete?: (fact: any) => void;
}) {
  const { t } = useI18n();
  const columns: Column<any>[] = [
    {
      key: 'status',
      label: t('dataViews.table.status'),
      filter: true,
      render: (f) => (
        <span className={clsx('text-[10px] uppercase px-1.5 py-0.5 rounded', statusStyle[f.status] || 'bg-ink/[0.06] text-ink-muted')}>
          {f.status}
        </span>
      ),
    },
    { key: 'entity_type', label: t('dataViews.facts.entityType'), filter: true, sortable: true },
    { key: 'entity_id', label: t('dataViews.facts.entityId'), sortable: true, className: 'font-mono text-xs' },
    { key: 'predicate', label: t('dataViews.facts.predicate'), filter: true, sortable: true, className: 'font-mono text-xs' },
    { key: 'value', label: t('dataViews.facts.value'), render: (f) => <Truncated text={String(f.value)} /> },
    {
      key: 'confidence',
      label: t('dataViews.facts.confidence'),
      filter: true,
      render: (f) => (
        <span className={clsx('text-[10px] uppercase px-1.5 py-0.5 rounded', confidenceStyle(f.confidence))}>{f.confidence}</span>
      ),
    },
    { key: 'scope', label: t('dataViews.facts.scope'), filter: true, render: (f) => <span className="text-xs text-ink-faint">{f.scope}</span> },
    {
      key: 'pinned',
      label: t('dataViews.table.pin'),
      render: (f) => (f.pinned ? <Pin className="w-3.5 h-3.5 text-studio-teal" /> : null),
    },
    {
      key: 'strength',
      label: t('dataViews.facts.strength'),
      sortable: true,
      render: (f) => <span className="text-xs font-mono">{Number(f.strength ?? 1).toFixed(2)}</span>,
    },
    {
      key: 'access_count',
      label: t('dataViews.facts.access'),
      sortable: true,
      render: (f) => <span className="text-xs font-mono text-ink-faint">{f.access_count ?? 0}</span>,
    },
    {
      key: 'expires_at',
      label: t('dataViews.facts.expires'),
      sortable: true,
      render: (f) => <span className="text-xs text-ink-faint">{f.expires_at ? String(f.expires_at).slice(0, 10) : '—'}</span>,
    },
    {
      key: 'provenance',
      label: t('dataViews.facts.provenance'),
      render: (f) => <span className="text-xs text-ink-faint">{f.provenance?.source || '—'}</span>,
    },
    {
      key: 'updated_at',
      label: t('dataViews.facts.updated'),
      sortable: true,
      render: (f) => <span className="text-xs text-ink-faint">{String(f.updated_at || '').slice(0, 16)}</span>,
    },
    {
      key: '_actions',
      label: '',
      render: (f) => (
        <span className="flex gap-1">
          {onPin && (
            <button type="button" className="btn btn-ghost btn-sm !px-1.5" title={t('dataViews.table.pinAction')} onClick={() => onPin(f)}>
              <Pin className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button type="button" className="btn btn-ghost btn-sm !px-1.5 text-rose-700" title={t('common.delete')} onClick={() => onDelete(f)}>
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
      rowKey={(f) => f.fact_id}
      searchKeys={['entity_type', 'entity_id', 'predicate', 'value']}
      searchPlaceholder={t('dataViews.facts.search')}
      emptyText={t('dataViews.facts.empty')}
      expand={(f) => (
        <div className="space-y-1 font-mono text-xs">
          <div>fact_id: {f.fact_id}</div>
          <div>valid_from: {f.valid_from} · valid_until: {f.valid_until || '—'}</div>
          <div>superseded_by: {f.superseded_by || '—'}</div>
          <div className="whitespace-pre-wrap break-all">value: {String(f.value)}</div>
          {f.provenance && <div>provenance: {JSON.stringify(f.provenance)}</div>}
        </div>
      )}
    />
  );
}

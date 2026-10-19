import clsx from 'clsx';
import { useI18n } from '@/i18n';
import MemoryDataTable, { type Column } from './MemoryDataTable';

const kindStyle: Record<string, string> = {
  success: 'bg-emerald-50 text-emerald-800',
  failure: 'bg-rose-50 text-rose-800',
  partial: 'bg-amber-50 text-amber-800',
};

export default function ReflectionsTable({ rows }: { rows: any[] }) {
  const { t } = useI18n();
  const columns: Column<any>[] = [
    {
      key: 'kind',
      label: t('dataViews.reflections.type'),
      filter: true,
      render: (r) => (
        <span className={clsx('text-[10px] uppercase px-1.5 py-0.5 rounded', kindStyle[r.kind] || 'bg-ink/[0.06] text-ink-muted')}>
          {r.kind}
        </span>
      ),
    },
    { key: 'summary', label: t('dataViews.reflections.summary'), render: (r) => <span className="text-ink">{String(r.summary || '').slice(0, 120)}</span> },
    { key: 'episode_id', label: t('dataViews.reflections.relatedEpisode'), className: 'font-mono text-xs text-ink-faint' },
    { key: 'created_at', label: t('dataViews.table.time'), sortable: true, render: (r) => <span className="text-xs text-ink-faint">{String(r.created_at || '').slice(0, 16)}</span> },
  ];

  return (
    <MemoryDataTable
      rows={rows}
      columns={columns}
      rowKey={(r) => r.reflection_id}
      searchKeys={['summary', 'why', 'next_action']}
      searchPlaceholder={t('dataViews.reflections.search')}
      emptyText={t('dataViews.reflections.empty')}
      expand={(r) => (
        <div className="space-y-2 text-xs">
          {r.why?.length > 0 && <div><span className="text-ink-faint">why：</span>{(r.why || []).join('；')}</div>}
          {r.next_action && <div><span className="text-ink-faint">next_action：</span>{r.next_action}</div>}
        </div>
      )}
    />
  );
}

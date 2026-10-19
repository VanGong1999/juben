import { useI18n } from '@/i18n';
import MemoryDataTable, { type Column } from './MemoryDataTable';

export default function AuditTable({ rows }: { rows: any[] }) {
  const { t } = useI18n();
  const columns: Column<any>[] = [
    { key: 'created_at', label: t('dataViews.table.time'), sortable: true, render: (a) => <span className="text-xs text-ink-faint">{String(a.created_at || '').slice(0, 19)}</span> },
    { key: 'action', label: t('dataViews.audit.action'), filter: true, sortable: true, render: (a) => <span className="text-ink font-medium">{a.action}</span> },
    { key: 'layer', label: t('dataViews.audit.layer'), filter: true, render: (a) => <span className="text-xs text-ink-faint">{a.layer}</span> },
    { key: 'target_id', label: t('dataViews.audit.target'), className: 'font-mono text-xs' },
    { key: 'agent_id', label: 'Agent', filter: true, className: 'font-mono text-xs text-ink-faint' },
  ];

  return (
    <MemoryDataTable
      rows={rows}
      columns={columns}
      rowKey={(a) => a.audit_id || `${a.created_at}_${a.action}_${a.target_id}`}
      searchKeys={['action', 'layer', 'target_id', 'agent_id']}
      searchPlaceholder={t('dataViews.audit.search')}
      emptyText={t('dataViews.audit.empty')}
      expand={(a) => (
        <div className="space-y-2 text-xs font-mono">
          {a.before_snippet && <div><span className="text-ink-faint">before：</span>{a.before_snippet}</div>}
          {a.after_snippet && <div><span className="text-ink-faint">after：</span>{a.after_snippet}</div>}
          {a.detail && Object.keys(a.detail).length > 0 && (
            <div><span className="text-ink-faint">detail：</span>{JSON.stringify(a.detail)}</div>
          )}
        </div>
      )}
    />
  );
}

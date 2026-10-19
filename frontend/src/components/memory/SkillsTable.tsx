import { Trash2 } from 'lucide-react';
import clsx from 'clsx';
import { useI18n } from '@/i18n';
import MemoryDataTable, { type Column } from './MemoryDataTable';

export default function SkillsTable({
  rows,
  onToggle,
  onDelete,
}: {
  rows: any[];
  onToggle?: (skill: any) => void;
  onDelete?: (skill: any) => void;
}) {
  const { t } = useI18n();
  const columns: Column<any>[] = [
    { key: 'name', label: t('dataViews.table.name'), sortable: true, render: (s) => <span className="text-ink font-medium">{s.name}</span> },
    { key: 'trigger', label: t('dataViews.skills.trigger'), sortable: true, render: (s) => <span className="font-mono text-xs">{s.trigger}</span> },
    {
      key: 'version',
      label: t('dataViews.skills.version'),
      sortable: true,
      render: (s) => <span className="text-xs font-mono text-ink-faint">v{s.version}</span>,
    },
    {
      key: 'success_rate',
      label: t('dataViews.skills.successRate'),
      sortable: true,
      render: (s) => <span className="text-xs font-mono">{Number(s.success_rate ?? 0).toFixed(2)}</span>,
    },
    {
      key: 'last_used',
      label: t('dataViews.skills.lastUsed'),
      sortable: true,
      render: (s) => <span className="text-xs text-ink-faint">{s.last_used ? String(s.last_used).slice(0, 16) : '—'}</span>,
    },
    {
      key: 'enabled',
      label: t('dataViews.table.status'),
      filter: true,
      render: (s) =>
        s.enabled ? (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800">{t('dataViews.skills.enabled')}</span>
        ) : (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-800">{t('dataViews.skills.disabled')}</span>
        ),
    },
    {
      key: '_actions',
      label: '',
      render: (s) => (
        <span className="flex gap-1">
          {onToggle && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => onToggle(s)}>
              {s.enabled ? t('dataViews.skills.disabled') : t('dataViews.skills.enabled')}
            </button>
          )}
          {onDelete && (
            <button type="button" className="btn btn-ghost btn-sm text-rose-700" onClick={() => onDelete(s)}>
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
      rowKey={(s) => s.skill_id}
      searchKeys={['name', 'trigger']}
      searchPlaceholder={t('dataViews.skills.search')}
      emptyText={t('dataViews.skills.empty')}
      expand={(s) => (
        <div className="space-y-2 text-xs">
          <div><span className="text-ink-faint">steps：</span></div>
          <ol className="list-decimal pl-5 space-y-1">
            {(s.steps || []).map((st: string, i: number) => (
              <li key={i}>{st}</li>
            ))}
          </ol>
          {s.failure_modes?.length > 0 && (
            <div className="text-rose-700"><span className="text-ink-faint">failure_modes：</span>{(s.failure_modes || []).join('；')}</div>
          )}
        </div>
      )}
    />
  );
}

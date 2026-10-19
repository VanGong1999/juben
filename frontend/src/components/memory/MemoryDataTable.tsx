import { useMemo, useState, type ReactNode } from 'react';
import clsx from 'clsx';
import { ArrowUpDown, ChevronDown, ChevronRight, Search } from 'lucide-react';
import { useI18n } from '@/i18n';

export interface Column<T = any> {
  key: string;
  label: string;
  sortable?: boolean;
  filter?: boolean;
  render?: (row: T) => ReactNode;
  className?: string;
}

interface MemoryDataTableProps<T = any> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  searchKeys?: string[];
  searchPlaceholder?: string;
  emptyText?: string;
  expand?: (row: T) => ReactNode;
}

function primitive(v: unknown): string {
  if (v === null || v === undefined) return '';
  if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return String(v);
  return '';
}

export default function MemoryDataTable<T = any>({
  rows,
  columns,
  rowKey,
  searchKeys,
  searchPlaceholder,
  emptyText,
  expand,
}: MemoryDataTableProps<T>) {
  const { t } = useI18n();
  const resolvedSearchPlaceholder = searchPlaceholder ?? t('dataViews.table.search');
  const resolvedEmptyText = emptyText ?? t('dataViews.table.noData');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const filterOptions = useMemo(() => {
    const opts: Record<string, string[]> = {};
    for (const col of columns) {
      if (!col.filter) continue;
      const set = new Set<string>();
      for (const r of rows) {
        const v = primitive((r as any)[col.key]);
        if (v) set.add(v);
      }
      opts[col.key] = Array.from(set).sort();
    }
    return opts;
  }, [columns, rows]);

  const filtered = useMemo(() => {
    let out = rows;
    const q = search.trim().toLowerCase();
    if (q) {
      const keys = searchKeys && searchKeys.length ? searchKeys : columns.map((c) => c.key);
      out = out.filter((r) =>
        keys.some((k) => primitive((r as any)[k]).toLowerCase().includes(q))
      );
    }
    for (const [key, val] of Object.entries(filters)) {
      if (!val) continue;
      out = out.filter((r) => primitive((r as any)[key]) === val);
    }
    if (sortKey) {
      const dir = sortDir === 'asc' ? 1 : -1;
      out = [...out].sort((a, b) => {
        const av = (a as any)[sortKey];
        const bv = (b as any)[sortKey];
        if (av === bv) return 0;
        if (av === undefined || av === null) return 1;
        if (bv === undefined || bv === null) return -1;
        return av > bv ? dir : -dir;
      });
    }
    return out;
  }, [rows, search, searchKeys, columns, filters, sortKey, sortDir]);

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const toggleExpand = (key: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-studio-line rounded-lg bg-paper-white"
            placeholder={resolvedSearchPlaceholder}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="surface-panel p-8 text-center text-sm text-ink-muted">{resolvedEmptyText}</div>
      ) : (
        <div className="surface-panel overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-studio-line text-left text-xs text-ink-muted">
                {expand && <th className="w-8 px-2 py-2" />}
                {columns.map((col) => (
                  <th key={col.key} className={clsx('px-3 py-2 font-medium whitespace-nowrap', col.className)}>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        className={clsx('inline-flex items-center gap-0.5', col.sortable && 'hover:text-ink')}
                        onClick={() => col.sortable && toggleSort(col.key)}
                        disabled={!col.sortable}
                      >
                        {col.label}
                        {col.sortable && (
                          <ArrowUpDown className={clsx('w-3 h-3', sortKey === col.key ? 'text-studio-teal' : 'text-ink-faint')} />
                        )}
                      </button>
                      {col.filter && (
                        <select
                          className="ml-1 text-[11px] border border-studio-line rounded px-1 py-0.5 bg-paper-white"
                          value={filters[col.key] || ''}
                          onChange={(e) => setFilters((f) => ({ ...f, [col.key]: e.target.value }))}
                        >
                          <option value="">{t('common.all')}</option>
                          {(filterOptions[col.key] || []).map((o) => (
                            <option key={o} value={o}>
                              {o}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => {
                const key = rowKey(row);
                const isOpen = expanded.has(key);
                return (
                  <ExpandableRow
                    key={key}
                    row={row}
                    columns={columns}
                    isOpen={isOpen}
                    hasExpand={!!expand}
                    onToggle={() => toggleExpand(key)}
                  >
                    {expand ? expand(row) : null}
                  </ExpandableRow>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ExpandableRow<T>({
  row,
  columns,
  isOpen,
  hasExpand,
  onToggle,
  children,
}: {
  row: T;
  columns: Column<T>[];
  isOpen: boolean;
  hasExpand: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <>
      <tr className="border-b border-pearl-line hover:bg-ink/[0.02]">
        {hasExpand && (
          <td className="px-2 py-2 align-top">
            <button type="button" className="text-ink-faint" onClick={onToggle}>
              {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>
          </td>
        )}
        {columns.map((col) => (
          <td key={col.key} className={clsx('px-3 py-2 align-top', col.className)}>
            {col.render ? col.render(row) : <span className="text-ink">{primitive((row as any)[col.key])}</span>}
          </td>
        ))}
      </tr>
      {hasExpand && isOpen && (
        <tr className="border-b border-pearl-line bg-ink/[0.02]">
          <td colSpan={columns.length + 1} className="px-4 py-3 text-sm text-ink-muted">
            {children}
          </td>
        </tr>
      )}
    </>
  );
}

/**
 * 并排（side-by-side）diff 视图 — 左「改前」右「改后」，基于 LCS 行对齐高亮增删。
 */

import { useMemo } from 'react';
import clsx from 'clsx';
import { useI18n } from '@/i18n';

type RowType = 'same' | 'del' | 'add';
interface DiffRow {
  type: RowType;
  before: string;
  after: string;
}

function computeDiff(beforeText: string, afterText: string): DiffRow[] {
  const a = (beforeText || '').split('\n');
  const b = (afterText || '').split('\n');
  const m = a.length;
  const n = b.length;

  // LCS 表
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      dp[i][j] =
        a[i] === b[j]
          ? dp[i + 1][j + 1] + 1
          : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const rows: DiffRow[] = [];
  let i = 0;
  let j = 0;
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      rows.push({ type: 'same', before: a[i], after: b[j] });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      rows.push({ type: 'del', before: a[i], after: '' });
      i++;
    } else {
      rows.push({ type: 'add', before: '', after: b[j] });
      j++;
    }
  }
  while (i < m) {
    rows.push({ type: 'del', before: a[i], after: '' });
    i++;
  }
  while (j < n) {
    rows.push({ type: 'add', before: '', after: b[j] });
    j++;
  }
  return rows;
}

type Props = {
  before?: string;
  after?: string;
};

export default function SideBySideDiff({ before = '', after = '' }: Props) {
  const { t } = useI18n();
  const rows = useMemo(() => computeDiff(before, after), [before, after]);

  if (!before && !after) {
    return <p className="text-xs text-ink-faint">{t('studio.diff.none')}</p>;
  }

  const stats = useMemo(() => {
    let del = 0;
    let add = 0;
    for (const r of rows) {
      if (r.type === 'del') del++;
      else if (r.type === 'add') add++;
    }
    return { del, add };
  }, [rows]);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-[10px] tabular-nums">
        <span className="px-2 py-0.5 rounded bg-rose-50 text-rose-600">-{stats.del}</span>
        <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-600">+{stats.add}</span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-pearl-line/60">
        <div className="min-w-[640px] grid grid-cols-2 text-[11px] leading-relaxed font-mono">
          {/* 表头 */}
          <div className="px-3 py-1.5 bg-pearl-soft/60 text-ink-faint font-sans font-medium border-b border-pearl-line/60 border-r sticky top-0">
            {t('studio.diff.before')}
          </div>
          <div className="px-3 py-1.5 bg-pearl-soft/60 text-ink-faint font-sans font-medium border-b border-pearl-line/60">
            {t('studio.diff.after')}
          </div>

          {rows.map((r, idx) => {
            const isDel = r.type === 'del';
            const isAdd = r.type === 'add';
            return (
              <div key={idx} className="contents">
                <div
                  className={clsx(
                    'px-3 py-0.5 border-r border-pearl-line/30 whitespace-pre-wrap break-all',
                    isDel ? 'bg-rose-50 text-rose-700' : 'text-ink-muted'
                  )}
                >
                  {isDel ? `- ${r.before || ' '}` : r.before || ' '}
                </div>
                <div
                  className={clsx(
                    'px-3 py-0.5 whitespace-pre-wrap break-all',
                    isAdd ? 'bg-emerald-50 text-emerald-700' : 'text-ink-muted'
                  )}
                >
                  {isAdd ? `+ ${r.after || ' '}` : r.after || ' '}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

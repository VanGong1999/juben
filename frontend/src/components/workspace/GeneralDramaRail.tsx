/**
 * 通用剧本左栏 — 项目选择器 + 创作/分析子流程 + 专家（general + shared）
 */

import { useMemo } from 'react';
import { Clapperboard, Plus } from 'lucide-react';
import clsx from 'clsx';
import AgentBlueprintRail from './AgentBlueprintRail';
import type { DramaMeta } from '@/services/dramaService';
import { useI18n } from '@/i18n';

type SubTab = 'create' | 'analyze';

type Props = {
  subTab: SubTab;
  onSubTabChange: (t: SubTab) => void;
  projects: DramaMeta[];
  selectedId?: string | null;
  onSelectProject: (id: string) => void;
  onNewProject: (type: 'long_drama' | 'script_analysis') => void;
  creating?: boolean;
};

export default function GeneralDramaRail({
  subTab,
  onSubTabChange,
  projects,
  selectedId,
  onSelectProject,
  onNewProject,
  creating,
}: Props) {
  const { t } = useI18n();
  const list = useMemo(
    () => projects.filter((p) => p.type === (subTab === 'create' ? 'long_drama' : 'script_analysis')),
    [projects, subTab]
  );

  return (
    <aside className="h-full flex flex-col bg-transparent">
      <div className="shrink-0 px-3 pt-2.5 pb-2.5 border-b border-pearl-line space-y-2.5">
        <div className="flex items-center gap-1.5">
          <div className="w-5 h-5 rounded bg-atelier-gold-soft text-atelier-gold flex items-center justify-center">
            <Clapperboard className="w-3 h-3" />
          </div>
          <h2 className="font-display text-[13px] font-semibold text-ink leading-none">{t('studio.mode.general')}</h2>
          <span className="text-[10px] text-ink-faint ml-auto">{t('studio.general.subtitle')}</span>
        </div>

        <div className="flex gap-1 p-0.5 rounded-lg bg-pearl-soft border border-pearl-line">
          {(
            [
              { id: 'create' as const, label: t('studio.general.createLong') },
              { id: 'analyze' as const, label: t('studio.general.analyzeScript') },
            ]
          ).map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => onSubTabChange(t.id)}
              className={clsx(
                'flex-1 py-1.5 rounded-md text-[11px] font-medium transition-colors',
                subTab === t.id ? 'bg-white text-ink shadow-sm' : 'text-ink-muted hover:text-ink'
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          <select
            value={selectedId || ''}
            onChange={(e) => onSelectProject(e.target.value)}
            className="flex-1 min-w-0 rounded-lg border border-pearl-line bg-white/70 px-2 py-1.5 text-[11px] outline-none focus:border-atelier-teal"
          >
            <option value="">
              {subTab === 'create' ? t('studio.general.selectLong') : t('studio.general.selectAnalysis')}
            </option>
            {list.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={creating}
            onClick={() => onNewProject(subTab === 'create' ? 'long_drama' : 'script_analysis')}
            className="shrink-0 inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-[11px] font-medium bg-atelier-teal text-white hover:bg-atelier-teal-mid disabled:opacity-50"
            title={subTab === 'create' ? t('studio.general.newLongTitle') : t('studio.general.newAnalysisTitle')}
          >
            <Plus className="w-3.5 h-3.5" />
            {subTab === 'create' ? t('studio.general.newLong') : t('studio.general.newAnalysis')}
          </button>
        </div>

        <p className="text-[10px] text-ink-faint leading-snug">
          {selectedId
            ? subTab === 'create'
              ? t('studio.general.hintSelectedCreate')
              : t('studio.general.hintSelectedAnalyze')
            : subTab === 'create'
              ? t('studio.general.hintCreate')
              : t('studio.general.hintAnalyze')}
        </p>
      </div>

      <div className="flex-1 min-h-0">
        <AgentBlueprintRail productLines={['general', 'shared']} />
      </div>
    </aside>
  );
}

/**
 * 短剧制片阶段轨 — 立项→故事→情节点→人物→连载→评估
 * 借鉴「工作流进度」信息架构，内容与交互按竖屏短剧定制。
 */

import clsx from 'clsx';
import { Check, Circle, Loader2, Play } from 'lucide-react';
import type { DramaDetail } from '@/services/dramaService';
import type { AtelierRun } from '@/services/atelierService';
import { useI18n, translate } from '@/i18n';

export type PipelineStageId =
  | 'planning'
  | 'story'
  | 'plot'
  | 'character'
  | 'serialize'
  | 'evaluation';

export type StageStatus = 'done' | 'active' | 'todo';

export type StudioStage = {
  id: PipelineStageId;
  label: string;
  hint: string;
  status: StageStatus;
  agentId?: string;
  midMode?: 'map' | 'episode';
};

type Props = {
  drama: DramaDetail;
  artifactKinds?: string[];
  atelierRun?: AtelierRun | null;
  activeStageId?: PipelineStageId | null;
  onSelectStage?: (stage: StudioStage) => void;
  onStartStage?: (stage: StudioStage) => void;
  compact?: boolean;
};

function hasKind(kinds: string[] | undefined, kind: string) {
  return (kinds || []).includes(kind);
}

export function deriveStudioStages(
  drama: DramaDetail,
  artifactKinds: string[] = [],
  atelierRun?: AtelierRun | null
): StudioStage[] {
  const chars = (drama.bible?.characters || '').trim();
  const world = (drama.bible?.world || '').trim();
  const outline = (drama.outline || '').trim();
  const doneEps =
    drama.completed_episodes ||
    drama.episodes?.filter((e) => e.status === 'done').length ||
    0;

  const runDone = (module: string) =>
    Boolean(
      atelierRun?.steps?.some(
        (s) => s.module === module && (s.status === 'done' || s.artifact_id)
      )
    );
  const runActive = (module: string) =>
    Boolean(
      atelierRun?.steps?.some(
        (s) =>
          s.module === module &&
          (s.status === 'running' ||
            (s.enabled &&
              s.status === 'pending' &&
              s.id === atelierRun.current_step_id))
      )
    );

  const flags = {
    planning: runDone('planning') || hasKind(artifactKinds, 'planning'),
    story:
      runDone('story') ||
      hasKind(artifactKinds, 'story') ||
      world.length > 40 ||
      outline.length > 40,
    plot: runDone('plot') || hasKind(artifactKinds, 'plot') || outline.length > 80,
    character:
      runDone('character') ||
      hasKind(artifactKinds, 'character') ||
      chars.length > 60,
    serialize: doneEps > 0 || runDone('creation'),
    evaluation: runDone('evaluation') || hasKind(artifactKinds, 'evaluation'),
  };

  const defs: Array<Omit<StudioStage, 'status'> & { done: boolean; activeHint: boolean }> = [
    {
      id: 'planning',
      label: translate('studio.pipeline.planning'),
      hint: translate('studio.pipeline.planningHint'),
      agentId: 'short_drama_planner',
      midMode: 'map',
      done: flags.planning,
      activeHint: runActive('planning'),
    },
    {
      id: 'story',
      label: translate('studio.pipeline.story'),
      hint: translate('studio.pipeline.storyHint'),
      agentId: 'story_five_elements',
      midMode: 'map',
      done: flags.story,
      activeHint: runActive('story'),
    },
    {
      id: 'plot',
      label: translate('studio.pipeline.plot'),
      hint: translate('studio.pipeline.plotHint'),
      agentId: 'major_plot_points',
      midMode: 'map',
      done: flags.plot,
      activeHint: runActive('plot'),
    },
    {
      id: 'character',
      label: translate('studio.pipeline.character'),
      hint: translate('studio.pipeline.characterHint'),
      agentId: 'character_profile_generator',
      midMode: 'map',
      done: flags.character,
      activeHint: runActive('character'),
    },
    {
      id: 'serialize',
      label: translate('studio.pipeline.serialize'),
      hint: translate('studio.pipeline.serializeHint', undefined, { done: doneEps, total: drama.total_episodes || 0 }),
      agentId: 'short_drama_creator',
      midMode: 'episode',
      done: doneEps >= Math.max(1, Math.min(3, drama.total_episodes || 1)) && doneEps > 0,
      activeHint: runActive('creation') || (flags.character && doneEps === 0),
    },
    {
      id: 'evaluation',
      label: translate('studio.pipeline.evaluation'),
      hint: translate('studio.pipeline.evaluationHint'),
      agentId: 'short_drama_evaluation',
      midMode: 'map',
      done: flags.evaluation,
      activeHint: runActive('evaluation'),
    },
  ];

  let firstTodoLocked = false;
  return defs.map((d) => {
    let status: StageStatus = 'todo';
    if (d.done) status = 'done';
    else if (d.activeHint && !firstTodoLocked) {
      status = 'active';
      firstTodoLocked = true;
    } else if (!d.done && !firstTodoLocked) {
      status = 'active';
      firstTodoLocked = true;
    }
    return {
      id: d.id,
      label: d.label,
      hint: d.hint,
      agentId: d.agentId,
      midMode: d.midMode,
      status,
    };
  });
}

export default function StudioPipelineRail({
  drama,
  artifactKinds = [],
  atelierRun,
  activeStageId,
  onSelectStage,
  onStartStage,
  compact,
}: Props) {
  const { t } = useI18n();
  const stages = deriveStudioStages(drama, artifactKinds, atelierRun);
  const doneCount = stages.filter((s) => s.status === 'done').length;

  return (
    <div className={clsx('border-b border-pearl-line/70', compact ? 'px-3 py-2.5' : 'px-3.5 py-3')}>
      <div className="flex items-center justify-between mb-2.5">
        <div className="text-[10px] uppercase tracking-[0.14em] text-ink-faint">{t('studio.pipeline.stages')}</div>
        <div className="text-[10px] tabular-nums text-ink-muted">
          {doneCount}/{stages.length}
        </div>
      </div>
      <ol className="space-y-0">
        {stages.map((stage, idx) => {
          const isActive = activeStageId === stage.id || stage.status === 'active';
          return (
            <li key={stage.id} className="relative">
              {idx < stages.length - 1 && (
                <span
                  className={clsx(
                    'absolute left-[9px] top-6 w-px h-[calc(100%-8px)]',
                    stage.status === 'done' ? 'bg-atelier-teal/50' : 'bg-pearl-line'
                  )}
                />
              )}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => onSelectStage?.(stage)}
                  className={clsx(
                    'flex-1 min-w-0 flex items-start gap-2.5 rounded-xl px-1.5 py-1.5 text-left transition-all duration-200',
                    isActive
                      ? 'bg-atelier-teal-soft/70'
                      : 'hover:bg-white/55'
                  )}
                >
                  <span
                    className={clsx(
                      'mt-0.5 w-[18px] h-[18px] rounded-full flex items-center justify-center shrink-0 border',
                      stage.status === 'done' &&
                        'bg-atelier-teal border-atelier-teal text-white',
                      stage.status === 'active' &&
                        'bg-white border-atelier-teal text-atelier-teal shadow-sm',
                      stage.status === 'todo' &&
                        'bg-white/70 border-pearl-line text-ink-faint'
                    )}
                  >
                    {stage.status === 'done' ? (
                      <Check className="w-3 h-3" />
                    ) : stage.status === 'active' ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Circle className="w-2.5 h-2.5" />
                    )}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span
                      className={clsx(
                        'block text-[12px] font-semibold leading-tight',
                        isActive ? 'text-atelier-teal' : 'text-ink'
                      )}
                    >
                      {idx + 1}. {stage.label}
                    </span>
                    <span className="block text-[10px] text-ink-faint mt-0.5 truncate">
                      {stage.hint}
                    </span>
                  </span>
                </button>
                {onStartStage && (
                  <button
                    type="button"
                    onClick={() => onStartStage(stage)}
                    className="shrink-0 inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium border border-atelier-teal/30 text-atelier-teal hover:bg-atelier-teal-soft transition-colors"
                    title={t('studio.pipeline.startStage', { label: stage.label })}
                  >
                    <Play className="w-3 h-3" />
                    {t('studio.pipeline.start')}
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/**
 * 右侧专家动作坞 — 当前集焦点 + 一键专家动作（短剧向）
 */

import { useState } from 'react';
import clsx from 'clsx';
import {
  BarChart3,
  BookOpen,
  ListTree,
  PenLine,
  Sparkles,
  Users,
  Wand2,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { useAgentStore } from '@/store/agentStore';
import type { DramaDetail } from '@/services/dramaService';
import { useI18n } from '@/i18n';

type Action = {
  id: string;
  label: string;
  hint: string;
  agentId: string;
  icon: typeof Sparkles;
  prompt: string;
  accent?: 'teal' | 'gold' | 'ink';
};

type Props = {
  drama: DramaDetail;
  selectedEp: number;
  episodeTitle?: string;
  onAsk: (prompt: string, agentId: string) => void;
  onWriteEpisode?: () => void;
  busy?: boolean;
};

export default function StudioAgentDock({
  drama,
  selectedEp,
  episodeTitle,
  onAsk,
  onWriteEpisode,
  busy,
}: Props) {
  const { t } = useI18n();
  const { activeAgent, setActiveAgent } = useAgentStore();
  const [open, setOpen] = useState(true);

  const actions: Action[] = [
    {
      id: 'plan',
      label: t('studio.dock.plan'),
      hint: t('studio.dock.planHint'),
      agentId: 'short_drama_planner',
      icon: Sparkles,
      prompt: `围绕《${drama.title}》完善短剧立项策划：题材卖点、受众、商业化卡点。\n简介：${drama.description || '（无）'}`,
    },
    {
      id: 'story',
      label: t('studio.dock.story'),
      hint: t('studio.dock.storyHint'),
      agentId: 'story_five_elements',
      icon: BookOpen,
      prompt: `分析《${drama.title}》的故事五元素，并给出可写入圣经的设定要点。\n请依据已有设定：@drama[characters] @drama[world] @drama[outline]`,
    },
    {
      id: 'plot',
      label: t('studio.dock.plot'),
      hint: t('studio.dock.plotHint'),
      agentId: 'major_plot_points',
      icon: ListTree,
      prompt: `为《${drama.title}》拆解大情节点与竖屏节奏，重点服务第 ${selectedEp} 集前后。\n请沿用已有人物与大纲，勿杜撰新人：@drama[characters] @drama[outline]`,
    },
    {
      id: 'cast',
      label: t('studio.dock.cast'),
      hint: t('studio.dock.castHint'),
      agentId: 'character_profile_generator',
      icon: Users,
      prompt: `为《${drama.title}》生成/补全主要人物小传（300–500 字/人），突出关系张力。\n先对照已有设定再补全：@drama[characters] @drama[outline] @drama[world]`,
      accent: 'gold',
    },
    {
      id: 'write',
      label: t('studio.dock.write'),
      hint: t('studio.ep', { n: selectedEp }),
      agentId: 'short_drama_creator',
      icon: PenLine,
      prompt: `请撰写《${drama.title}》第 ${selectedEp} 集${episodeTitle ? `「${episodeTitle}」` : ''}正文，强调前 3 秒钩子与集末卡点。\n必须依据：@drama[characters] @drama[outline]；若有前集请参考相邻集。`,
      accent: 'teal',
    },
    {
      id: 'eval',
      label: t('studio.dock.eval'),
      hint: t('studio.dock.evalHint'),
      agentId: 'short_drama_evaluation',
      icon: BarChart3,
      prompt: `评估《${drama.title}》第 ${selectedEp} 集的可播性：钩子、人设、节奏、付费点，给出可改清单。\n请以该集完整正文为准（不是大纲）：@drama[episode:${selectedEp}]\n可对照人设：@drama[characters]`,
    },
  ];

  return (
    <div className="flex-shrink-0 border-b border-pearl-line/80 px-3.5 py-3 bg-white/35">
      <div className="flex items-start justify-between gap-2 mb-2.5">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.14em] text-ink-faint">{t('studio.episode.focus')}</div>
          <div className="font-display text-base font-semibold text-ink truncate leading-tight mt-0.5">
            {t('studio.ep', { n: selectedEp })}
            {episodeTitle ? ` · ${episodeTitle}` : ''}
          </div>
          <p className="text-[11px] text-ink-muted mt-0.5 truncate">
            {t('studio.dock.hint', { genre: drama.genre || t('common.shortDrama') })}
          </p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {onWriteEpisode && (
            <button
              type="button"
              disabled={busy}
              onClick={onWriteEpisode}
              className="btn btn-primary btn-sm"
            >
              <Wand2 className="w-3.5 h-3.5" />
              {t('studio.episode.aiWrite')}
            </button>
          )}
          <button
            type="button"
            onClick={() => setOpen(!open)}
            className="p-1 rounded-md text-ink-faint hover:text-ink hover:bg-pearl-soft transition-colors"
          >
            {open ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {open && (
      <div className="grid grid-cols-3 gap-1.5">
        {actions.map((a) => {
          const Icon = a.icon;
          const on = activeAgent === a.agentId;
          return (
            <button
              key={a.id}
              type="button"
              disabled={busy}
              onClick={() => {
                setActiveAgent(a.agentId);
                onAsk(a.prompt, a.agentId);
              }}
              className={clsx(
                'rounded-xl border px-2 py-2 text-left transition-all duration-200',
                on
                  ? 'border-atelier-teal/45 bg-atelier-teal-soft shadow-sm'
                  : 'border-pearl-line/70 bg-white/55 hover:border-atelier-teal/30 hover:bg-white/90'
              )}
            >
              <Icon
                className={clsx(
                  'w-3.5 h-3.5 mb-1',
                  a.accent === 'gold'
                    ? 'text-atelier-gold'
                    : a.accent === 'teal' || on
                      ? 'text-atelier-teal'
                      : 'text-ink-muted'
                )}
              />
              <div className="text-[11px] font-semibold text-ink leading-none">{a.label}</div>
              <div className="text-[9px] text-ink-faint mt-0.5 truncate">{a.hint}</div>
            </button>
          );
        })}
      </div>
      )}
    </div>
  );
}

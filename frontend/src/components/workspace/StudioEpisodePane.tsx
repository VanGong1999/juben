/**
 * 工作室中栏 — 创作图 / 分集正文 / 文档画布
 * 分集模式：统计条 + 本集焦点 + 正文编辑
 */

import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  Wand2,
  Maximize2,
  Sparkles,
  Layers,
  FileText,
  Target,
  AlertCircle,
  Clock,
  Eye,
  Pencil,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import clsx from 'clsx';
import StreamingText from '@/components/chat/StreamingText';
import type { DramaDetail, EpisodeStatus } from '@/services/dramaService';
import { useI18n } from '@/i18n';

const statusLabel: Record<EpisodeStatus, string> = {
  draft: 'studio.status.draft',
  writing: 'studio.status.writing',
  done: 'studio.status.done',
  error: 'studio.status.error',
};

export type StudioMidMode = 'map' | 'episode' | 'canvas';

type Props = {
  drama: DramaDetail;
  selectedEp: number;
  title: string;
  content: string;
  skills?: Array<{ id: string; name: string; enabled?: boolean }>;
  busy?: boolean;
  artifactCount?: number;
  onTitleChange: (v: string) => void;
  onContentChange: (v: string) => void;
  onWrite: () => void;
  targetWords: number;
  onTargetWordsChange: (v: number) => void;
  midMode: StudioMidMode;
  onMidModeChange: (m: StudioMidMode) => void;
  canvas: ReactNode;
  creationMap: ReactNode;
};

function extractEpisodeFocus(outline: string | undefined, ep: number): string {
  if (!outline?.trim()) return '';
  const lines = outline.split(/\n+/).map((l) => l.trim()).filter(Boolean);
  const hit = lines.find((l) =>
    new RegExp(`(第\\s*${ep}\\s*集|EP\\s*0*${ep}\\b|集\\s*${ep}\\b)`, 'i').test(l)
  );
  if (hit) return hit;
  // fallback: nearby chunk
  const chunk = lines.slice(0, 4).join(' · ');
  return chunk.slice(0, 160);
}

export default function StudioEpisodePane({
  drama,
  selectedEp,
  title,
  content,
  skills,
  busy,
  onTitleChange,
  onContentChange,
  onWrite,
  targetWords,
  onTargetWordsChange,
  midMode,
  onMidModeChange,
  canvas,
  creationMap,
  artifactCount = 0,
}: Props) {
  const { t } = useI18n();
  const meta = drama.episodes?.find((e) => e.number === selectedEp);
  const enabledSkills = (skills || []).filter((s) => s.enabled !== false).slice(0, 4);
  const wordCount = content.replace(/\s/g, '').length || content.length;
  const target = targetWords;
  const progress = Math.min(100, Math.round((wordCount / target) * 100));
  const focus = extractEpisodeFocus(drama.outline, selectedEp);
  const updatedAt = meta?.updated_at
    ? new Date(meta.updated_at).toLocaleString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—';
  const issues =
    meta?.status === 'error' ? 1 : wordCount > 0 && wordCount < target * 0.4 ? 1 : 0;
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>('preview');
  const [statsOpen, setStatsOpen] = useState(true);
  const [focusOpen, setFocusOpen] = useState(true);

  return (
    <div className="h-full flex flex-col min-h-0">
      <div className="flex items-center justify-between gap-3 px-3 sm:px-4 pt-3 pb-0">
        <div className="flex gap-0.5 p-0.5 rounded-lg bg-white/55 border border-pearl-line/80 backdrop-blur-sm">
          <button
            type="button"
            onClick={() => onMidModeChange('map')}
            className={clsx(
              'inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              midMode === 'map' ? 'bg-white text-ink shadow-sm' : 'text-ink-muted'
            )}
          >
            <Layers className="w-3 h-3" />
            {t('studio.episode.creationMap')}
            {artifactCount > 0 && (
              <span className="tabular-nums text-[10px] text-atelier-teal">{artifactCount}</span>
            )}
          </button>
          <button
            type="button"
            onClick={() => onMidModeChange('episode')}
            className={clsx(
              'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              midMode === 'episode' ? 'bg-white text-ink shadow-sm' : 'text-ink-muted'
            )}
          >
            {t('studio.episode.scriptBody')}
          </button>
          <button
            type="button"
            onClick={() => onMidModeChange('canvas')}
            className={clsx(
              'inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              midMode === 'canvas' ? 'bg-white text-ink shadow-sm' : 'text-ink-muted'
            )}
          >
            <FileText className="w-3 h-3" />
            {t('studio.episode.canvas')}
          </button>
        </div>
      </div>

      {midMode === 'map' ? (
        <div className="flex-1 min-h-0 overflow-hidden">{creationMap}</div>
      ) : midMode === 'canvas' ? (
        <div className="flex-1 min-h-0 overflow-hidden">{canvas}</div>
      ) : (
        <>
          <div className="px-4 sm:px-5 pt-3">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase tracking-wider text-ink-faint">{t('studio.episode.stats')}</span>
              <button
                type="button"
                onClick={() => setStatsOpen(!statsOpen)}
                className="inline-flex items-center gap-1 text-[10px] text-ink-faint hover:text-ink transition-colors"
              >
                {statsOpen ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
            {statsOpen && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  {
                    id: 'wordCount',
                    label: t('studio.episode.wordCount'),
                    value: wordCount,
                    icon: FileText,
                    tone: 'text-ink',
                  },
                  {
                    id: 'target',
                    label: t('studio.episode.targetWords'),
                    value: target,
                    icon: Target,
                    tone: 'text-atelier-teal',
                  },
                  {
                    id: 'issues',
                    label: t('studio.episode.issues'),
                    value: issues,
                    icon: AlertCircle,
                    tone: issues > 0 ? 'text-atelier-gold' : 'text-ink-muted',
                  },
                  {
                    id: 'updatedAt',
                    label: t('studio.episode.updatedAt'),
                    value: updatedAt,
                    icon: Clock,
                    tone: 'text-ink-muted',
                    small: true,
                  },
                ].map((kpi) => (
                  <div
                    key={kpi.id}
                    className="rounded-xl border border-pearl-line/70 bg-white/55 px-3 py-2 backdrop-blur-sm"
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-[10px] text-ink-faint uppercase tracking-wider">
                        {kpi.label}
                      </span>
                      <kpi.icon className="w-3 h-3 text-ink-faint" />
                    </div>
                    {kpi.id === 'target' ? (
                      <input
                        type="number"
                        min={100}
                        step={100}
                        value={targetWords}
                        onChange={(e) =>
                          onTargetWordsChange(Math.max(100, Number(e.target.value) || 1200))
                        }
                        className="mt-1 w-full bg-transparent font-display font-semibold text-xl text-atelier-teal tabular-nums leading-none outline-none border-b border-transparent focus:border-atelier-teal/40"
                        title={t('studio.episode.setTargetTitle')}
                      />
                    ) : (
                      <div
                        className={clsx(
                          'mt-1 font-display font-semibold tabular-nums leading-none',
                          kpi.small ? 'text-sm' : 'text-xl',
                          kpi.tone
                        )}
                      >
                        {kpi.value}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-start justify-between gap-3 px-4 sm:px-5 pt-3 pb-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="font-display text-2xl font-semibold text-ink leading-none">
                  {t('studio.ep', { n: selectedEp })}
                </h2>
                <span
                  className={clsx(
                    'text-[10px] px-2 py-0.5 rounded',
                    meta?.status === 'done'
                      ? 'bg-atelier-teal-soft text-atelier-teal'
                      : meta?.status === 'writing'
                        ? 'bg-atelier-gold-soft text-atelier-gold'
                        : 'bg-pearl-soft text-ink-muted'
                  )}
                >
                  {t(statusLabel[meta?.status || 'draft'])}
                </span>
              </div>
              <input
                className="mt-2 w-full bg-transparent text-sm text-ink-muted outline-none border-b border-transparent focus:border-pearl-line"
                value={title}
                onChange={(e) => onTitleChange(e.target.value)}
                placeholder={t('studio.episode.titlePlaceholder')}
              />
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={onWrite}>
                <Wand2 className="w-3.5 h-3.5" />
                {t('studio.episode.aiWrite')}
              </button>
              <Link
                to={`/dramas/${drama.id}/episodes/${selectedEp}`}
                className="btn btn-secondary btn-sm"
              >
                <Maximize2 className="w-3.5 h-3.5" />
                {t('studio.episode.fullscreen')}
              </Link>
            </div>
          </div>

          {(focus || drama.description) && (
            <div className="mx-4 sm:mx-5 mb-2 rounded-xl border border-atelier-teal/20 bg-atelier-teal-soft/35 px-3.5 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] uppercase tracking-wider text-atelier-teal">{t('studio.episode.focus')}</span>
                <button
                  type="button"
                  onClick={() => setFocusOpen(!focusOpen)}
                  className="inline-flex items-center gap-1 text-[10px] text-atelier-teal/70 hover:text-atelier-teal transition-colors"
                >
                  {focusOpen ? (
                    <ChevronUp className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
              {focusOpen && (
                <>
                  <p className="text-[12px] text-ink-muted leading-relaxed mt-1">
                    {focus || t('studio.episode.focusHint', { n: selectedEp })}
                    {!focus && drama.description ? ` ${drama.description.slice(0, 80)}` : ''}
                  </p>
                  <div className="mt-2 h-1 rounded-full bg-white/70 overflow-hidden">
                    <div
                      className="h-full bg-atelier-teal/80 transition-all duration-500"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </>
              )}
            </div>
          )}

          {/* {enabledSkills.length > 0 && (
            <div className="px-4 sm:px-5 py-2 border-y border-pearl-line/70 flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1 text-[10px] text-ink-faint uppercase tracking-wider">
                <Sparkles className="w-3 h-3 text-atelier-gold" />
                生效 Skills
              </span>
              {enabledSkills.map((s) => (
                <span
                  key={s.id}
                  className="text-[10px] px-2 py-0.5 rounded bg-atelier-gold-soft/70 text-atelier-gold"
                >
                  {s.name}
                </span>
              ))}
            </div>
          )} */}

          <div className="flex-1 overflow-hidden p-4 sm:p-5 pt-3">
            {viewMode === 'edit' ? (
              <textarea
                className="w-full h-full min-h-[280px] resize-none rounded-xl border border-pearl-line/80 bg-white/80 px-4 py-3 text-sm leading-relaxed text-ink outline-none focus:border-atelier-teal backdrop-blur-sm shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]"
                value={content}
                onChange={(e) => onContentChange(e.target.value)}
                placeholder={t('studio.episode.writePlaceholder')}
              />
            ) : (
              <div className="w-full h-full min-h-[280px] overflow-y-auto rounded-xl border border-pearl-line/80 bg-white/80 px-5 py-4 backdrop-blur-sm shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
                {content.trim() ? (
                  <StreamingText content={content} />
                ) : (
                  <p className="text-sm text-ink-faint">{t('studio.episode.emptyBody')}</p>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between px-4 sm:px-5 py-2.5 border-t border-pearl-line/70 text-xs text-ink-faint">
            <span className="tabular-nums">
              {t('studio.episode.wordGoal', { words: wordCount, target, pct: progress })}
            </span>
            <div className="flex items-center gap-0.5 p-0.5 rounded-md bg-white/60 border border-pearl-line/70">
              <button
                type="button"
                onClick={() => setViewMode('edit')}
                className={clsx(
                  'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium transition-colors',
                  viewMode === 'edit' ? 'bg-white text-ink shadow-sm' : 'text-ink-muted hover:text-ink'
                )}
              >
                <Pencil className="w-3 h-3" />
                {t('studio.episode.edit')}
              </button>
              <button
                type="button"
                onClick={() => setViewMode('preview')}
                className={clsx(
                  'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium transition-colors',
                  viewMode === 'preview' ? 'bg-white text-ink shadow-sm' : 'text-ink-muted hover:text-ink'
                )}
              >
                <Eye className="w-3 h-3" />
                {t('studio.episode.preview')}
              </button>
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-1 hover:text-atelier-teal"
              disabled={busy}
              onClick={onWrite}
            >
              <Sparkles className="w-3.5 h-3.5" />
              {t('studio.episode.aiContinue')}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/**
 * 短剧工作台 — 参考「故事蓝图 | 编辑器 | 设定资料」三栏
 */

import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  BookOpen,
  Play,
  Sparkles,
  Plus,
  Users,
  Library,
  ListTree,
  Wand2,
  Save,
} from 'lucide-react';
import {
  generateOutline,
  getDrama,
  startAutoWrite,
  getAutoWriteStatus,
  writeEpisode,
  type DramaDetail,
  type EpisodeStatus,
} from '@/services/dramaService';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';
import clsx from 'clsx';

export default function DramaWorkspacePage() {
  const { dramaId } = useParams<{ dramaId: string }>();
  const { t } = useI18n();
  const statusLabel: Record<EpisodeStatus, string> = {
    draft: t('studio.status.draft'),
    writing: t('studio.status.writing'),
    done: t('studio.status.done'),
    error: t('studio.status.error'),
  };
  const [drama, setDrama] = useState<DramaDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState('');
  const [selectedEp, setSelectedEp] = useState(1);
  const [editorContent, setEditorContent] = useState('');
  const [editorTitle, setEditorTitle] = useState('');
  const [rightTab, setRightTab] = useState<'bible' | 'cast' | 'plot'>('bible');
  const { success, error } = useNotificationStore();
  const navigate = useNavigate();

  const reload = async () => {
    if (!dramaId) return;
    const res = await getDrama(dramaId);
    if (res.success && res.drama) {
      setDrama(res.drama);
      localStorage.setItem('dramaId', dramaId);
    }
  };

  const loadEpisodeBody = async (n: number) => {
    if (!dramaId) return;
    const { getEpisode } = await import('@/services/dramaService');
    const ep = await getEpisode(dramaId, n);
    if (ep.episode) {
      setEditorTitle(ep.episode.title || t('studio.ep', { n }));
      setEditorContent((ep.episode as any).content || '');
    }
  };

  useEffect(() => {
    if (!dramaId) return;
    setLoading(true);
    reload()
      .then(() => loadEpisodeBody(1))
      .catch(() => error(t('studio.toast.loadFailed'), t('project.dramaLoadFailed')))
      .finally(() => setLoading(false));
  }, [dramaId]);

  useEffect(() => {
    if (!jobId || !dramaId) return;
    const timer = setInterval(async () => {
      try {
        const res = await getAutoWriteStatus(dramaId, jobId);
        const job = res.job;
        if (!job) return;
        setJobProgress(`${job.current}/${job.total} · ${job.message || job.status}`);
        if (job.status === 'done' || job.status === 'error' || job.status === 'failed') {
          clearInterval(timer);
          setJobId(null);
          setBusy(false);
          await reload();
          await loadEpisodeBody(selectedEp);
          if (job.status === 'done') success(t('studio.toast.serialDone'), job.message || '');
          else error(t('studio.toast.serialInterrupted'), job.message || '');
        }
      } catch {
        /* ignore */
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [jobId, dramaId]);

  const selectEpisode = async (n: number) => {
    setSelectedEp(n);
    await loadEpisodeBody(n);
  };

  const handleOutline = async () => {
    if (!dramaId) return;
    setBusy(true);
    try {
      await generateOutline(dramaId, drama?.description);
      await reload();
      success(t('studio.toast.outlineGenerated'), '');
      setRightTab('plot');
    } catch (e) {
      error(t('studio.toast.generateFailed'), e instanceof Error ? e.message : '');
    } finally {
      setBusy(false);
    }
  };

  const handleWriteOne = async () => {
    if (!dramaId) return;
    setBusy(true);
    try {
      const res = await writeEpisode(dramaId, selectedEp);
      if (res.content) setEditorContent(res.content);
      if (res.episode?.title) setEditorTitle(res.episode.title);
      await reload();
      success(t('studio.toast.episodeGenerated', { n: selectedEp }), '');
    } catch (e) {
      error(t('studio.toast.writeFailed'), e instanceof Error ? e.message : '');
    } finally {
      setBusy(false);
    }
  };

  const handleAutoWrite = async () => {
    if (!dramaId || !drama) return;
    setBusy(true);
    try {
      const from = Math.max(1, (drama.completed_episodes || 0) + 1);
      const to = Math.min(drama.total_episodes, from + 4);
      const res = await startAutoWrite(dramaId, { from_episode: from, to_episode: to });
      if (res.job_id) {
        setJobId(res.job_id);
        setJobProgress(t('studio.toast.starting'));
        success(t('studio.toast.autoWriteStarted'), t('studio.episodeRange', { from, to }));
      }
    } catch (e) {
      setBusy(false);
      error(t('studio.toast.startFailed'), e instanceof Error ? e.message : '');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-studio-mesh flex items-center justify-center">
        <div className="w-48 h-8 rounded-xl bg-paper-cool animate-pulse" />
      </div>
    );
  }

  if (!drama) {
    return (
      <div className="min-h-screen bg-studio-mesh flex flex-col items-center justify-center gap-4">
        <p className="text-ink-muted">{t('project.dramaNotFound')}</p>
        <Link to="/dramas" className="btn btn-secondary">
          {t('project.backToDramas')}
        </Link>
      </div>
    );
  }

  const done = drama.completed_episodes || drama.episodes?.filter((e) => e.status === 'done').length || 0;
  const total = drama.total_episodes || 1;
  const pct = Math.min(100, Math.round((done / total) * 100));
  const currentEpMeta = drama.episodes?.find((e) => e.number === selectedEp);

  return (
    <div className="h-screen flex flex-col bg-studio-mesh">
      {/* 顶栏精简 */}
      <header className="flex-shrink-0 flex items-center justify-between gap-3 px-4 py-2.5 bg-paper-white/90 backdrop-blur border-b border-studio-line">
        <div className="flex items-center gap-3 min-w-0">
          <Link to="/dramas" className="p-2 rounded-lg hover:bg-paper-cool text-ink-muted">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="min-w-0">
            <h1 className="font-display font-semibold text-ink truncate">{drama.title}</h1>
            <p className="text-[11px] text-ink-faint truncate">
              {drama.genre || t('dramas.type.short_drama')} · {done}/{total} {t('dramas.episodeUnit')} · {pct}%
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link to={`/workspace?drama_id=${drama.id}`} className="btn btn-ghost btn-sm hidden sm:inline-flex">
            {t('project.expertWorkbench')}
          </Link>
          <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={handleOutline}>
            <BookOpen className="w-3.5 h-3.5" />
            {t('studio.header.generateOutline')}
          </button>
          <button type="button" className="btn btn-amber btn-sm" disabled={busy} onClick={handleAutoWrite}>
            <Play className="w-3.5 h-3.5" />
            {t('studio.header.autoSerialize')}
          </button>
        </div>
      </header>

      {jobId && (
        <div className="px-4 py-1.5 text-xs text-studio-amber bg-studio-amber-soft border-b border-studio-line flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 animate-progress-pulse" />
          {t('studio.header.autoWrite', { progress: jobProgress })}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* 左：故事蓝图 + 分集 */}
        <aside className="hidden md:flex w-[280px] xl:w-[300px] flex-col border-r border-studio-line bg-paper-white">
          <div className="px-4 pt-4 pb-3 border-b border-studio-line">
            <h2 className="font-display font-semibold text-sm text-ink">{t('studio.rail.storyBlueprint')}</h2>
            <p className="text-[11px] text-ink-muted mt-1 line-clamp-3">
              {drama.description || t('project.noDescHint')}
            </p>
          </div>
          <div className="px-4 py-3 border-b border-studio-line">
            <div className="text-[10px] uppercase tracking-wider text-ink-faint mb-1">{t('project.storySummary')}</div>
            <p className="text-xs text-ink-muted line-clamp-4 whitespace-pre-wrap">
              {(drama.outline || '').slice(0, 280) || t('project.outlineHint')}
            </p>
          </div>
          <div className="px-3 py-2 flex items-center justify-between">
            <span className="text-xs font-medium text-ink">{t('project.episodeList')}</span>
            <span className="text-[10px] text-ink-faint">{done}/{total}</span>
          </div>
          <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-1.5">
            {(drama.episodes || []).map((ep) => (
              <button
                key={ep.number}
                type="button"
                onClick={() => selectEpisode(ep.number)}
                className={clsx(
                  'w-full text-left rounded-xl px-3 py-2.5 border transition-all',
                  selectedEp === ep.number
                    ? 'border-studio-teal/40 bg-studio-teal-soft'
                    : 'border-transparent hover:bg-paper-cool'
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-ink">{t('studio.ep', { n: ep.number })}</span>
                  <span
                    className={clsx(
                      'text-[10px] px-1.5 py-0.5 rounded-full',
                      ep.status === 'done'
                        ? 'bg-studio-teal text-white'
                        : ep.status === 'writing'
                          ? 'bg-studio-amber-soft text-studio-amber'
                          : 'bg-paper-cool text-ink-faint'
                    )}
                  >
                    {statusLabel[ep.status]}
                  </span>
                </div>
                <p className="text-[11px] text-ink-muted mt-0.5 truncate">{ep.title}</p>
                {ep.word_count ? (
                  <p className="text-[10px] text-ink-faint mt-0.5">{t('studio.charCount', { count: ep.word_count })}</p>
                ) : null}
              </button>
            ))}
            <button
              type="button"
              className="w-full flex items-center justify-center gap-1 py-2.5 rounded-xl border border-dashed border-studio-line text-xs text-ink-muted hover:border-studio-teal hover:text-studio-teal"
              onClick={() => navigate(`/dramas/${drama.id}/episodes/${Math.min(total, done + 1 || 1)}`)}
            >
              <Plus className="w-3.5 h-3.5" />
              {t('project.openNextEpisode')}
            </button>
          </div>
        </aside>

        {/* 中：编辑器 */}
        <main className="flex-1 flex flex-col min-w-0 bg-paper-white/70">
          <div className="flex items-start justify-between gap-3 px-4 sm:px-6 pt-4 pb-3 border-b border-studio-line">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="font-display text-xl font-semibold text-ink">{t('studio.ep', { n: selectedEp })}</h2>
                <span
                  className={clsx(
                    'text-[10px] px-2 py-0.5 rounded-full',
                    currentEpMeta?.status === 'done'
                      ? 'bg-studio-teal-soft text-studio-teal'
                      : 'bg-paper-cool text-ink-muted'
                  )}
                >
                  {statusLabel[currentEpMeta?.status || 'draft']}
                </span>
              </div>
              <input
                className="mt-1 w-full bg-transparent text-sm text-ink-muted outline-none border-b border-transparent focus:border-studio-line"
                value={editorTitle}
                onChange={(e) => setEditorTitle(e.target.value)}
                placeholder={t('studio.episode.titlePlaceholder')}
              />
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={handleWriteOne}>
                <Wand2 className="w-3.5 h-3.5" />
                {t('studio.episode.aiWrite')}
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => navigate(`/dramas/${drama.id}/episodes/${selectedEp}`)}
              >
                <Save className="w-3.5 h-3.5" />
                {t('project.fullscreenEdit')}
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-hidden p-4 sm:p-6">
            <textarea
              className="w-full h-full min-h-[320px] resize-none rounded-2xl border border-studio-line bg-paper-white px-4 py-3 text-sm leading-relaxed text-ink outline-none focus:border-studio-teal focus:ring-2 focus:ring-studio-teal/15"
              value={editorContent}
              onChange={(e) => setEditorContent(e.target.value)}
              placeholder={t('project.editorPlaceholder')}
            />
          </div>

          <div className="flex items-center justify-between px-4 sm:px-6 py-2.5 border-t border-studio-line text-xs text-ink-faint">
            <span>{t('studio.charCount', { count: editorContent.length })}</span>
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="inline-flex items-center gap-1 hover:text-studio-teal"
                disabled={busy}
                onClick={handleWriteOne}
              >
                <Sparkles className="w-3.5 h-3.5" />
                {t('studio.episode.aiContinue')}
              </button>
              <Link
                to={`/workspace?agent=short_drama_evaluation&drama_id=${drama.id}`}
                className="inline-flex items-center gap-1 hover:text-studio-teal"
              >
                {t('project.aiReview')}
              </Link>
            </div>
          </div>

          {/* 移动端分集条 */}
          <div className="md:hidden flex gap-1 overflow-x-auto px-3 py-2 border-t border-studio-line">
            {(drama.episodes || []).slice(0, 24).map((ep) => (
              <button
                key={ep.number}
                type="button"
                onClick={() => selectEpisode(ep.number)}
                className={clsx(
                  'shrink-0 w-9 h-9 rounded-lg text-xs font-medium',
                  selectedEp === ep.number ? 'bg-studio-teal text-white' : 'bg-paper-cool text-ink-muted'
                )}
              >
                {ep.number}
              </button>
            ))}
          </div>
        </main>

        {/* 右：设定资料 */}
        <aside className="hidden lg:flex w-[300px] xl:w-[320px] flex-col border-l border-studio-line bg-paper-white">
          <div className="flex border-b border-studio-line">
            {(
              [
                { id: 'bible' as const, label: t('studio.map.knowledge'), icon: Library },
                { id: 'cast' as const, label: t('studio.map.characters'), icon: Users },
                { id: 'plot' as const, label: t('studio.dock.plot'), icon: ListTree },
              ] as const
            ).map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setRightTab(id)}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-1 py-2.5 text-[11px] font-medium',
                  rightTab === id
                    ? 'text-studio-teal border-b-2 border-studio-teal'
                    : 'text-ink-muted hover:text-ink'
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {rightTab === 'bible' && (
              <>
                <div className="rounded-xl border border-studio-line p-3">
                  <div className="text-[10px] text-studio-teal font-medium mb-1">{t('studio.bible.world')}</div>
                  <pre className="text-xs text-ink-muted whitespace-pre-wrap font-sans leading-relaxed">
                    {drama.bible?.world || t('project.worldEmptyHint')}
                  </pre>
                </div>
                <div className="rounded-xl border border-studio-line p-3">
                  <div className="text-[10px] text-studio-amber font-medium mb-1">{t('project.constraintsSkills')}</div>
                  <p className="text-xs text-ink-muted">{t('studio.bible.skillsHint')}</p>
                </div>
                <Link
                  to="/skills"
                  className="block text-center text-xs text-studio-teal py-2 rounded-xl border border-dashed border-studio-line hover:bg-studio-teal-soft"
                >
                  + {t('project.manageSkills')}
                </Link>
              </>
            )}
            {rightTab === 'cast' && (
              <>
                <div className="rounded-xl border border-studio-line p-3">
                  <div className="text-[10px] text-ink-faint mb-1">{t('studio.bible.characters')}</div>
                  <pre className="text-xs text-ink-muted whitespace-pre-wrap font-sans leading-relaxed">
                    {drama.bible?.characters || t('project.castEmptyHint')}
                  </pre>
                </div>
                <Link
                  to={`/workspace?agent=character_profile_generator&drama_id=${drama.id}`}
                  className="block text-center text-xs text-studio-teal py-2 rounded-xl border border-dashed border-studio-line hover:bg-studio-teal-soft"
                >
                  + {t('project.addCharacter')}
                </Link>
              </>
            )}
            {rightTab === 'plot' && (
              <>
                <div className="rounded-xl border border-studio-line p-3">
                  <div className="text-[10px] text-ink-faint mb-1">{t('project.outlineBeats')}</div>
                  <pre className="text-xs text-ink-muted whitespace-pre-wrap font-sans leading-relaxed max-h-[60vh] overflow-y-auto">
                    {drama.outline || t('project.noOutline')}
                  </pre>
                </div>
                <Link
                  to={`/workspace?agent=major_plot_points&drama_id=${drama.id}`}
                  className="block text-center text-xs text-studio-teal py-2 rounded-xl border border-dashed border-studio-line hover:bg-studio-teal-soft"
                >
                  + {t('project.majorPlotAnalysis')}
                </Link>
              </>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

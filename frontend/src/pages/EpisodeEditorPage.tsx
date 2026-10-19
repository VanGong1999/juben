/**
 * 单集编辑器 + AI 写作
 */

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Sparkles, Save } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { getDrama, getEpisode, writeEpisode } from '@/services/dramaService';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';

export default function EpisodeEditorPage() {
  const { dramaId, episodeNumber } = useParams<{ dramaId: string; episodeNumber: string }>();
  const n = Number(episodeNumber) || 1;
  const { t } = useI18n();
  const [title, setTitle] = useState(t('studio.ep', { n }));
  const [content, setContent] = useState('');
  const [dramaTitle, setDramaTitle] = useState('');
  const [instruction, setInstruction] = useState('');
  const [targetWords, setTargetWords] = useState(1200);
  const [loading, setLoading] = useState(true);
  const [writing, setWriting] = useState(false);
  const { success, error } = useNotificationStore();

  useEffect(() => {
    if (!dramaId) return;
    setLoading(true);
    Promise.all([getDrama(dramaId), getEpisode(dramaId, n)])
      .then(([d, ep]) => {
        if (d.drama) setDramaTitle(d.drama.title);
        if (ep.episode) {
          setTitle(ep.episode.title || t('studio.ep', { n }));
          setContent((ep.episode as any).content || '');
        }
      })
      .catch(() => error(t('studio.toast.loadFailed'), ''))
      .finally(() => setLoading(false));
  }, [dramaId, n]);

  const handleWrite = async () => {
    if (!dramaId) return;
    setWriting(true);
    try {
      const res = await writeEpisode(dramaId, n, instruction || undefined, targetWords);
      if (res.content) setContent(res.content);
      if (res.episode?.title) setTitle(res.episode.title);
      success(t('project.episodeGenerated'), t('project.contentWritten'));
    } catch (e) {
      error(t('studio.toast.generateFailed'), e instanceof Error ? e.message : '');
    } finally {
      setWriting(false);
    }
  };

  return (
    <AppShell
      title={title}
      subtitle={dramaTitle ? `${dramaTitle} · ${t('studio.ep', { n })}` : t('studio.ep', { n })}
      actions={
        <div className="flex gap-2">
          <Link to={`/studio/${dramaId}`} className="btn btn-ghost btn-sm">
            <ArrowLeft className="w-4 h-4" />
            {t('nav.studio')}
          </Link>
          <button type="button" className="btn btn-primary btn-sm" disabled={writing} onClick={handleWrite}>
            <Sparkles className="w-4 h-4" />
            {writing ? t('project.writing') : t('studio.episode.aiWrite')}
          </button>
        </div>
      }
    >
      <div className="p-4 sm:p-6 max-w-5xl mx-auto grid lg:grid-cols-[1fr_280px] gap-4">
        <div className="surface-panel p-4 sm:p-5 min-h-[70vh] flex flex-col">
          {loading ? (
            <div className="flex-1 bg-paper-cool animate-pulse rounded-xl" />
          ) : (
            <>
              <input
                className="input mb-3 font-display text-lg font-semibold border-0 bg-transparent px-0 focus:ring-0"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <textarea
                className="flex-1 w-full resize-none bg-transparent text-sm leading-relaxed text-ink outline-none min-h-[55vh]"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={t('project.episodePlaceholder')}
              />
              <div className="pt-3 border-t border-studio-line flex items-center justify-between text-xs text-ink-faint">
                <span>{t('studio.charCount', { count: content.length })}</span>
                <span className="inline-flex items-center gap-1">
                  <Save className="w-3 h-3" />
                  {t('project.savedTo')} episodes/ep_{String(n).padStart(3, '0')}.md
                </span>
              </div>
            </>
          )}
        </div>

        <aside className="surface-panel p-4 h-fit space-y-3">
          <h3 className="font-display font-semibold text-ink">{t('chat.assistant')}</h3>
          <p className="text-xs text-ink-muted">{t('project.aiReadsContext')}</p>
          <label className="block">
            <span className="text-xs text-ink-muted">{t('project.targetWords')}</span>
            <input
              type="number"
              min={100}
              step={100}
              value={targetWords}
              onChange={(e) => setTargetWords(Math.max(100, Number(e.target.value) || 1200))}
              className="input text-sm mt-1"
            />
          </label>
          <textarea
            className="input text-sm min-h-[100px]"
            placeholder={t('project.instructionPlaceholder')}
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
          />
          <button type="button" className="btn btn-primary w-full" disabled={writing} onClick={handleWrite}>
            <Sparkles className="w-4 h-4" />
            {writing ? t('studio.generating') : t('project.generateRewrite')}
          </button>
          <div className="flex gap-2 text-xs">
            {n > 1 && (
              <Link to={`/dramas/${dramaId}/episodes/${n - 1}`} className="text-studio-teal hover:underline">
                {t('project.prevEpisode')}
              </Link>
            )}
            <Link to={`/dramas/${dramaId}/episodes/${n + 1}`} className="text-studio-teal hover:underline ml-auto">
              {t('project.nextEpisode')}
            </Link>
          </div>
        </aside>
      </div>
    </AppShell>
  );
}

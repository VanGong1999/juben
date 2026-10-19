/**
 * 作品剧本库面板 — 上传 · grep/向量检索 · 送评估
 */

import { useEffect, useRef, useState } from 'react';
import {
  FileUp,
  Loader2,
  Search,
  Trash2,
  BarChart3,
  FileText,
  RefreshCw,
} from 'lucide-react';
import clsx from 'clsx';
import {
  deleteScript,
  listScripts,
  searchScripts,
  uploadScript,
  getScript,
  type ScriptMeta,
  type ScriptSearchHit,
  type ScriptSearchMode,
} from '@/services/scriptService';
import { useNotificationStore } from '@/store/notificationStore';
import { useAgentStore } from '@/store/agentStore';
import { useChatStore } from '@/store/chatStore';
import { useI18n } from '@/i18n';

type Props = {
  dramaId: string;
  dramaTitle?: string;
  /** 送评估/分析时目标 agent（默认短剧评估，通用剧本模式传入分析类专家） */
  evaluateAgentId?: string;
};

export default function StudioScriptsPanel({ dramaId, dramaTitle, evaluateAgentId = 'short_drama_evaluation' }: Props) {
  const { t } = useI18n();
  const { success, error } = useNotificationStore();
  const { setActiveAgent } = useAgentStore();
  const { sendMessage } = useChatStore();
  const fileRef = useRef<HTMLInputElement>(null);

  const [scripts, setScripts] = useState<ScriptMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<ScriptSearchMode>('hybrid');
  const [searching, setSearching] = useState(false);
  const [hits, setHits] = useState<ScriptSearchHit[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);

  const reload = async () => {
    setLoading(true);
    try {
      const res = await listScripts(dramaId);
      setScripts(res.scripts || []);
    } catch (e) {
      error(t('studio.toast.loadFailed'), e instanceof Error ? e.message : '');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
  }, [dramaId]);

  const handleUpload = async (files: FileList | null) => {
    if (!files?.length) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const res = await uploadScript(dramaId, file, {
          title: file.name.replace(/\.[^.]+$/, ''),
          tags: 'script,upload',
        });
        if (res.success) {
          success(t('studio.toast.uploaded'), res.message || res.script?.title || file.name);
        }
      }
      await reload();
    } catch (e) {
      error(t('workspace.uploadFailed'), e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await searchScripts(dramaId, {
        query: query.trim(),
        mode,
        top_k: 12,
      });
      setHits(res.hits || []);
      if (!(res.hits || []).length) {
        success(t('studio.toast.noMatch'), t('studio.toast.noMatchHint', { mode }));
      }
    } catch (e) {
      error(t('studio.toast.searchFailed'), e instanceof Error ? e.message : '');
    } finally {
      setSearching(false);
    }
  };

  const handleDelete = async (docId: string) => {
    setBusyId(docId);
    try {
      await deleteScript(dramaId, docId);
      setScripts((prev) => prev.filter((s) => s.id !== docId));
      setHits((prev) => prev.filter((h) => h.doc_id !== docId));
      success(t('dramas.toast.deleted'), '');
    } catch (e) {
      error(t('dramas.toast.deleteFailed'), e instanceof Error ? e.message : '');
    } finally {
      setBusyId(null);
    }
  };

  const sendToEvaluate = async (docId: string, excerpt?: string) => {
    setBusyId(docId);
    try {
      let body = excerpt || '';
      let title = scripts.find((s) => s.id === docId)?.title || '剧本';
      if (!body || body.length < 80) {
        const res = await getScript(dramaId, docId, true);
        body = res.script?.content || body;
        title = res.script?.title || title;
      }
      const clip = body.slice(0, 12000);
      const prompt =
        `请分析以下剧本《${title}》（作品：${dramaTitle || dramaId}）。` +
        `从结构、人物、情节、亮点与可改进之处给出专业结论。\n\n---\n${clip}`;
      setActiveAgent(evaluateAgentId);
      await sendMessage(prompt, evaluateAgentId);
      success(t('studio.toast.sentForAnalysis'), title);
    } catch (e) {
      error(t('studio.toast.evaluateFailed'), e instanceof Error ? e.message : '');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="px-3 pt-3 pb-2 border-b border-pearl-line/70 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-ink-faint">{t('studio.scripts.title')}</div>
            <p className="text-[11px] text-ink-muted mt-0.5">{t('studio.scripts.subtitle')}</p>
          </div>
          <button
            type="button"
            className="p-1.5 rounded-lg text-ink-muted hover:bg-white/70"
            onClick={() => void reload()}
            title={t('studio.refresh')}
          >
            <RefreshCw className={clsx('w-3.5 h-3.5', loading && 'animate-spin')} />
          </button>
        </div>

        <input
          ref={fileRef}
          type="file"
          accept=".txt,.md,.markdown,.json,.csv,.srt,.fountain,text/plain"
          multiple
          className="hidden"
          onChange={(e) => void handleUpload(e.target.files)}
        />
        <button
          type="button"
          disabled={uploading}
          onClick={() => fileRef.current?.click()}
          className="w-full btn btn-primary btn-sm"
        >
          {uploading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <FileUp className="w-3.5 h-3.5" />
          )}
          {t('studio.scripts.upload')}
        </button>
        <p className="text-[10px] text-ink-faint">{t('studio.scripts.uploadHint')}</p>
      </div>

      <div className="px-3 py-2 border-b border-pearl-line/70 space-y-2">
        <div className="flex gap-1">
          {(['hybrid', 'grep', 'vector'] as ScriptSearchMode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={clsx(
                'flex-1 text-[10px] py-1 rounded-md border transition-colors',
                mode === m
                  ? 'border-atelier-teal/40 bg-atelier-teal-soft text-atelier-teal'
                  : 'border-transparent text-ink-faint hover:bg-white/60'
              )}
            >
              {m === 'hybrid' ? t('studio.scripts.mode.hybrid') : m === 'grep' ? t('studio.scripts.mode.grep') : t('studio.scripts.mode.vector')}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void handleSearch();
            }}
            placeholder={mode === 'grep' ? t('studio.scripts.grepPlaceholder') : t('studio.scripts.vectorPlaceholder')}
            className="flex-1 rounded-lg border border-pearl-line bg-white/70 px-2 py-1.5 text-xs outline-none focus:border-atelier-teal"
          />
          <button
            type="button"
            className="btn btn-secondary btn-sm px-2"
            disabled={searching || !query.trim()}
            onClick={() => void handleSearch()}
          >
            {searching ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Search className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {hits.length > 0 && (
          <div className="p-2 space-y-1.5 border-b border-pearl-line/60">
            <div className="px-1 text-[10px] uppercase tracking-wider text-ink-faint">
              {t('studio.scripts.results', { count: hits.length })}
            </div>
            {hits.map((h, i) => (
              <div
                key={`${h.doc_id}-${h.line || h.chunk_id || i}`}
                className="rounded-lg border border-pearl-line/60 bg-white/55 px-2.5 py-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-semibold text-ink truncate">
                    {h.title || h.doc_id.slice(0, 8)}
                  </span>
                  <span className="text-[9px] text-ink-faint shrink-0">
                    {h.mode}
                    {typeof h.score === 'number' ? ` · ${h.score}` : ''}
                    {h.line ? ` · L${h.line}` : ''}
                  </span>
                </div>
                <p className="text-[11px] text-ink-muted mt-1 line-clamp-3 leading-snug">{h.text}</p>
                <button
                  type="button"
                  className="mt-1.5 text-[10px] text-atelier-teal hover:underline"
                  disabled={busyId === h.doc_id}
                  onClick={() => void sendToEvaluate(h.doc_id, h.text)}
                >
                  {t('studio.scripts.evaluateSnippet')}
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="p-2 space-y-1.5">
          <div className="px-1 text-[10px] uppercase tracking-wider text-ink-faint">
            {t('studio.scripts.indexed', { count: scripts.length })}
          </div>
          {loading ? (
            <div className="py-8 flex justify-center text-ink-faint">
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>
          ) : scripts.length === 0 ? (
            <div className="py-8 text-center text-[11px] text-ink-faint px-4">
              {t('studio.scripts.empty')}
            </div>
          ) : (
            scripts.map((s) => (
              <div
                key={s.id}
                className="rounded-xl border border-pearl-line/60 bg-white/50 px-2.5 py-2.5"
              >
                <div className="flex items-start gap-2">
                  <FileText className="w-3.5 h-3.5 text-atelier-teal mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-[12px] font-semibold text-ink truncate">{s.title}</div>
                    <div className="text-[10px] text-ink-faint mt-0.5 tabular-nums">
                      {t('studio.charCount', { count: s.char_count || 0 })} · {t('studio.scripts.chunks', { count: s.chunk_count || 0 })}
                      {s.embed_backend ? ` · ${s.embed_backend}` : ''}
                    </div>
                    {s.preview && (
                      <p className="text-[10px] text-ink-muted mt-1 line-clamp-2">{s.preview}</p>
                    )}
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md bg-atelier-teal-soft text-atelier-teal"
                        disabled={busyId === s.id}
                        onClick={() => void sendToEvaluate(s.id)}
                      >
                        <BarChart3 className="w-3 h-3" />
                        {t('studio.scripts.sendEvaluate')}
                      </button>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md text-ink-faint hover:bg-pearl-soft"
                        disabled={busyId === s.id}
                        onClick={() => void handleDelete(s.id)}
                      >
                        <Trash2 className="w-3 h-3" />
                        {t('common.delete')}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

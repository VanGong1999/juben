/**
 * 作品库 — 状态 / 进度 / 模板空状态 / 列表密度
 */

import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Clapperboard, Search, LayoutGrid, List, X, Pencil, Trash2 } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { createDrama, listDramas, updateDrama, deleteDrama, type DramaMeta, type DramaType } from '@/services/dramaService';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n, type TFunction, type Language } from '@/i18n';
import clsx from 'clsx';

const TEMPLATES = [
  {
    title: '都市甜宠',
    genre: '都市情感',
    description: '先婚后爱，职场与家庭的双向奔赴，每集兑现甜虐情绪点。',
    total_episodes: 80,
  },
  {
    title: '复仇爽剧',
    genre: '复仇爽文',
    description: '落魄归来、打脸升级，三秒钩子开场，集末强卡点。',
    total_episodes: 100,
  },
  {
    title: '悬疑反转',
    genre: '悬疑',
    description: '层层揭秘与身份反转，人物关系网驱动真相。',
    total_episodes: 60,
  },
];

type StatusKey = 'planning' | 'serializing' | 'completed';
type StatusFilter = 'all' | StatusKey;
type TypeFilter = 'all' | DramaType;

const TYPE_TONE: Record<DramaType, string> = {
  short_drama: 'bg-atelier-teal-soft text-atelier-teal',
  long_drama: 'bg-atelier-gold-soft text-atelier-gold',
  script_analysis: 'bg-violet-50 text-violet-600',
};

function resolveStatus(d: DramaMeta): StatusKey {
  const done = d.completed_episodes || 0;
  const total = d.total_episodes || 1;
  if (done <= 0) return 'planning';
  if (done >= total) return 'completed';
  return 'serializing';
}

function statusLabel(s: StatusKey, t: TFunction): string {
  return t(`dramas.status.${s}`);
}

function resolveType(d: DramaMeta): DramaType {
  return d.type === 'long_drama' || d.type === 'script_analysis' ? d.type : 'short_drama';
}

function formatDate(iso?: string, language?: Language) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(language === 'en' ? 'en-US' : 'zh-CN', { month: 'short', day: 'numeric' });
}

export default function DramasPage() {
  const [dramas, setDramas] = useState<DramaMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [view, setView] = useState<'list' | 'grid'>('list');
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: '',
    description: '',
    genre: '都市情感',
    total_episodes: 80,
  });
  const [renameTarget, setRenameTarget] = useState<DramaMeta | null>(null);
  const [renameForm, setRenameForm] = useState({ title: '', description: '', genre: '' });
  const { success, error } = useNotificationStore();
  const { t, language } = useI18n();
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const res = await listDramas();
      setDramas(res.dramas || []);
    } catch {
      setDramas([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    return dramas.filter((d) => {
      const matchQ =
        !q ||
        d.title?.toLowerCase().includes(q.toLowerCase()) ||
        d.genre?.toLowerCase().includes(q.toLowerCase());
      const st = resolveStatus(d);
      const matchStatus = statusFilter === 'all' || st === statusFilter;
      const matchType = typeFilter === 'all' || resolveType(d) === typeFilter;
      return matchQ && matchStatus && matchType;
    });
  }, [dramas, q, statusFilter, typeFilter]);

  const createAndOpen = async (payload: {
    title: string;
    description?: string;
    genre?: string;
    total_episodes?: number;
  }) => {
    setCreating(true);
    try {
      const res = await createDrama({
        title: payload.title.trim(),
        description: payload.description,
        genre: payload.genre,
        total_episodes: Number(payload.total_episodes) || 80,
      });
      if (res.success && res.drama?.id) {
        success(t('dramas.toast.created'), t('dramas.toast.entered'));
        navigate(`/studio/${res.drama.id}`);
      } else {
        error(t('dramas.toast.createFailed'), t('dramas.toast.retryLater'));
      }
    } catch (e) {
      error(t('dramas.toast.createFailed'), e instanceof Error ? e.message : t('dramas.toast.networkError'));
    } finally {
      setCreating(false);
    }
  };

  const handleCreate = async () => {
    if (!form.title.trim()) {
      error(t('dramas.toast.fillName'), '');
      return;
    }
    await createAndOpen(form);
  };

  const handleTemplate = async (t: (typeof TEMPLATES)[0]) => {
    await createAndOpen({
      title: t.title,
      description: t.description,
      genre: t.genre,
      total_episodes: t.total_episodes,
    });
  };

  const openRename = (d: DramaMeta) => {
    setRenameTarget(d);
    setRenameForm({
      title: d.title || '',
      description: d.description || '',
      genre: d.genre || '',
    });
  };

  const saveRename = async () => {
    if (!renameTarget) return;
    try {
      await updateDrama(renameTarget.id, {
        title: renameForm.title.trim(),
        description: renameForm.description,
        genre: renameForm.genre,
      });
      success(t('dramas.toast.renamed'), renameForm.title.trim());
      setRenameTarget(null);
      await load();
    } catch (e) {
      error(t('dramas.toast.renameFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleDelete = async (d: DramaMeta) => {
    if (!window.confirm(t('dramas.deleteConfirm', { title: d.title }))) {
      return;
    }
    try {
      await deleteDrama(d.id);
      success(t('dramas.toast.deleted'), d.title);
      await load();
    } catch (e) {
      error(t('dramas.toast.deleteFailed'), e instanceof Error ? e.message : '');
    }
  };

  return (
    <AppShell
      title={t('nav.works')}
      subtitle={t('dramas.subtitle')}
      actions={
        <button type="button" className="btn btn-primary btn-sm" onClick={() => setShowForm(true)}>
          <Plus className="w-4 h-4" />
          {t('common.newWork')}
        </button>
      }
    >
      <div className="px-4 sm:px-10 py-8 max-w-5xl mx-auto space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-faint" />
            <input
              className="input pl-10"
              placeholder={t('dramas.searchPlaceholder')}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <div className="flex gap-1 p-0.5 rounded-lg bg-pearl-soft border border-pearl-line">
              {(['all', 'planning', 'serializing', 'completed'] as StatusFilter[]).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setStatusFilter(s)}
                  className={clsx(
                    'px-2.5 py-1.5 rounded-md text-[11px] font-medium',
                    statusFilter === s ? 'bg-white text-ink shadow-sm' : 'text-ink-muted'
                  )}
                >
                  {s === 'all' ? t('dramas.status.all') : statusLabel(s, t)}
                </button>
              ))}
            </div>
            <div className="flex gap-1 p-0.5 rounded-lg bg-pearl-soft border border-pearl-line">
              {(
                [
                  { id: 'all' as TypeFilter, labelKey: 'dramas.type.all' },
                  { id: 'short_drama' as TypeFilter, labelKey: 'dramas.type.short_drama' },
                  { id: 'long_drama' as TypeFilter, labelKey: 'dramas.type.long_drama' },
                  { id: 'script_analysis' as TypeFilter, labelKey: 'dramas.type.script_analysis' },
                ]
              ).map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setTypeFilter(opt.id)}
                  className={clsx(
                    'px-2.5 py-1.5 rounded-md text-[11px] font-medium',
                    typeFilter === opt.id ? 'bg-white text-ink shadow-sm' : 'text-ink-muted'
                  )}
                >
                  {t(opt.labelKey)}
                </button>
              ))}
            </div>
            <div className="flex gap-0.5 p-0.5 rounded-lg border border-pearl-line">
              <button
                type="button"
                onClick={() => setView('list')}
                className={clsx('p-1.5 rounded-md', view === 'list' ? 'bg-pearl-soft text-ink' : 'text-ink-faint')}
              >
                <List className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setView('grid')}
                className={clsx('p-1.5 rounded-md', view === 'grid' ? 'bg-pearl-soft text-ink' : 'text-ink-faint')}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {showForm && (
          <div className="fixed inset-0 z-40 flex justify-end">
            <div className="absolute inset-0 bg-ink/25" onClick={() => setShowForm(false)} />
            <div className="relative w-full max-w-md h-full bg-white border-l border-pearl-line shadow-atelier-lg p-6 overflow-y-auto animate-slide-up">
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-display text-2xl font-semibold text-ink">{t('dramas.createTitle')}</h2>
                <button type="button" className="p-2 rounded-lg hover:bg-pearl-soft" onClick={() => setShowForm(false)}>
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-3">
                <input
                  className="input"
                  placeholder={t('dramas.dramaName')}
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
                <textarea
                  className="input min-h-[88px]"
                  placeholder={t('dramas.sellPoint')}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
                <div className="grid grid-cols-2 gap-3">
                  <input
                    className="input"
                    placeholder={t('dramas.genre')}
                    value={form.genre}
                    onChange={(e) => setForm({ ...form, genre: e.target.value })}
                  />
                  <input
                    className="input"
                    type="number"
                    min={1}
                    max={200}
                    placeholder={t('dramas.totalEpisodes')}
                    value={form.total_episodes}
                    onChange={(e) => setForm({ ...form, total_episodes: Number(e.target.value) })}
                  />
                </div>
                <button type="button" className="btn btn-primary w-full" disabled={creating} onClick={handleCreate}>
                  {creating ? t('dramas.creating') : t('dramas.createAndEnter')}
                </button>
              </div>
            </div>
          </div>
        )}

        {renameTarget && (
          <div className="fixed inset-0 z-40 flex justify-end">
            <div className="absolute inset-0 bg-ink/25" onClick={() => setRenameTarget(null)} />
            <div className="relative w-full max-w-md h-full bg-white border-l border-pearl-line shadow-atelier-lg p-6 overflow-y-auto animate-slide-up">
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-display text-2xl font-semibold text-ink">{t('dramas.editTitle')}</h2>
                <button type="button" className="p-2 rounded-lg hover:bg-pearl-soft" onClick={() => setRenameTarget(null)}>
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-3">
                <input
                  className="input"
                  placeholder={t('dramas.dramaName')}
                  value={renameForm.title}
                  onChange={(e) => setRenameForm({ ...renameForm, title: e.target.value })}
                />
                <textarea
                  className="input min-h-[88px]"
                  placeholder={t('dramas.sellPoint')}
                  value={renameForm.description}
                  onChange={(e) => setRenameForm({ ...renameForm, description: e.target.value })}
                />
                <input
                  className="input"
                  placeholder={t('dramas.genre')}
                  value={renameForm.genre}
                  onChange={(e) => setRenameForm({ ...renameForm, genre: e.target.value })}
                />
                <button type="button" className="btn btn-primary w-full" onClick={saveRename}>
                  {t('common.save')}
                </button>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="h-14 bg-pearl-soft animate-pulse rounded" />
            ))}
          </div>
        ) : dramas.length === 0 ? (
          <div className="border-t border-pearl-line pt-10">
            <div className="text-center mb-10">
              <Clapperboard className="w-8 h-8 text-atelier-teal mx-auto mb-3 opacity-70" />
              <h3 className="font-display text-2xl font-semibold text-ink">{t('dramas.startFromTemplate')}</h3>
              <p className="text-sm text-ink-muted mt-2">{t('dramas.customBlank')}</p>
            </div>
            <div className="grid sm:grid-cols-3 gap-4">
              {TEMPLATES.map((tmpl) => (
                <button
                  key={tmpl.title}
                  type="button"
                  disabled={creating}
                  onClick={() => handleTemplate(tmpl)}
                  className="text-left border border-pearl-line rounded-lg p-5 hover:border-atelier-teal/40 hover:bg-pearl-soft/40 transition-colors"
                >
                  <div className="text-[10px] uppercase tracking-wider text-ink-faint">{tmpl.genre}</div>
                  <div className="font-display text-xl font-semibold text-ink mt-1">{tmpl.title}</div>
                  <p className="text-xs text-ink-muted mt-2 leading-relaxed line-clamp-3">{tmpl.description}</p>
                  <div className="mt-3 text-[11px] text-atelier-teal">{tmpl.total_episodes} {t('dramas.episodeUnit')} · {t('dramas.oneClick')}</div>
                </button>
              ))}
            </div>
            <div className="mt-8 text-center">
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(true)}>
                <Plus className="w-4 h-4" />
                {t('dramas.blankWork')}
              </button>
            </div>
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-ink-muted py-12 text-center border-t border-pearl-line">{t('dramas.noMatch')}</p>
        ) : view === 'list' ? (
          <ul className="border-t border-pearl-line">
            {filtered.map((d) => {
              const done = d.completed_episodes || 0;
              const total = d.total_episodes || 1;
              const pct = Math.min(100, Math.round((done / total) * 100));
              const st = resolveStatus(d);
              const ty = resolveType(d);
              return (
                <li key={d.id} className="border-b border-pearl-line flex items-center gap-2 group">
                  <Link
                    to={`/dramas/${d.id}`}
                    className="flex flex-wrap sm:flex-nowrap items-baseline gap-x-6 gap-y-2 py-4 flex-1 min-w-0 hover:bg-pearl-soft/50 -mx-1 px-1 transition-colors"
                  >
                    <span className="font-display text-lg font-semibold text-ink flex-1 min-w-[140px] truncate">
                      {d.title}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${TYPE_TONE[ty]} w-fit`}>
                      {t(`dramas.type.${ty}`)}
                    </span>
                    <span className="text-[11px] text-ink-faint w-16">{d.genre || t('common.shortDrama')}</span>
                    <span className="text-[11px] text-atelier-teal w-10">{statusLabel(st, t)}</span>
                    <span className="font-mono text-xs text-ink-muted tabular-nums w-16">
                      {done}/{total}
                    </span>
                    <span className="hidden sm:block w-24 h-0.5 bg-pearl-soft overflow-hidden self-center">
                      <span className="block h-full bg-atelier-teal" style={{ width: `${pct}%` }} />
                    </span>
                    <span className="text-[11px] text-ink-faint w-14 text-right">
                      {formatDate(d.updated_at || d.created_at, language)}
                    </span>
                  </Link>
                  <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      type="button"
                      onClick={() => openRename(d)}
                      className="p-1.5 rounded-lg text-ink-faint hover:bg-pearl-soft hover:text-atelier-teal"
                      title={t('dramas.renameEdit')}
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(d)}
                      className="p-1.5 rounded-lg text-ink-faint hover:bg-rose-50 hover:text-rose-600"
                      title={t('dramas.deleteWork')}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">
            {filtered.map((d) => {
              const done = d.completed_episodes || 0;
              const total = d.total_episodes || 1;
              const pct = Math.min(100, Math.round((done / total) * 100));
              const st = resolveStatus(d);
              const ty = resolveType(d);
              return (
                <Link
                  key={d.id}
                  to={`/dramas/${d.id}`}
                  className="block border border-pearl-line rounded-lg p-5 hover:border-atelier-teal/35 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-display text-xl font-semibold text-ink line-clamp-2">{d.title}</h3>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${TYPE_TONE[ty]} shrink-0`}>
                      {t(`dramas.type.${ty}`)}
                    </span>
                    <span className="text-[10px] text-atelier-teal shrink-0">{statusLabel(st, t)}</span>
                  </div>
                  <p className="mt-2 text-xs text-ink-muted line-clamp-2">{d.description || t('dramas.noDesc')}</p>
                  <div className="mt-4 flex justify-between text-[11px] text-ink-faint mb-1">
                    <span>
                      {d.genre || t('common.shortDrama')} · {done}/{total} {t('dramas.episodeUnit')}
                    </span>
                    <span>{formatDate(d.updated_at || d.created_at, language)}</span>
                  </div>
                  <div className="h-0.5 bg-pearl-soft overflow-hidden">
                    <div className="h-full bg-atelier-teal" style={{ width: `${pct}%` }} />
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}

/**
 * 作品详情页 — 查看 / 修改历史成果、设定与版本，入口进入工作室
 */

import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  Clapperboard,
  History,
  Layers,
  Pencil,
  Trash2,
  X,
} from 'lucide-react';
import clsx from 'clsx';
import AppShell from '@/components/layout/AppShell';
import StudioArtifactsPanel from '@/components/workspace/StudioArtifactsPanel';
import DramaVersionPanel from '@/components/workspace/DramaVersionPanel';
import StreamingText from '@/components/chat/StreamingText';
import {
  deleteDrama,
  getDrama,
  updateDrama,
  type DramaDetail,
  type DramaType,
} from '@/services/dramaService';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';

const TYPE_TONE: Record<DramaType, string> = {
  short_drama: 'bg-atelier-teal-soft text-atelier-teal',
  long_drama: 'bg-atelier-gold-soft text-atelier-gold',
  script_analysis: 'bg-violet-50 text-violet-600',
};

function resolveType(d?: DramaDetail | null): DramaType {
  return d?.type === 'long_drama' || d?.type === 'script_analysis' ? d.type : 'short_drama';
}

function formatDate(iso?: string, lang?: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString(lang === 'zh' ? 'zh-CN' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function DramaDetailPage() {
  const { dramaId } = useParams<{ dramaId: string }>();
  const navigate = useNavigate();
  const { t, language } = useI18n();
  const { success, error } = useNotificationStore();
  const [drama, setDrama] = useState<DramaDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'bible' | 'artifacts'>('bible');
  const [showVersions, setShowVersions] = useState(false);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', genre: '', type: 'short_drama' as DramaType });

  const typeLabel: Record<DramaType, string> = {
    short_drama: t('dramas.type.short_drama'),
    long_drama: t('dramas.type.long_drama'),
    script_analysis: t('dramas.type.script_analysis'),
  };

  const load = async () => {
    if (!dramaId) return;
    setLoading(true);
    try {
      const res = await getDrama(dramaId);
      if (res.success && res.drama) setDrama(res.drama);
      else setDrama(null);
    } catch {
      setDrama(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const onUpdate = (e: Event) => {
      const detail = (e as CustomEvent).detail as { dramaId?: string } | undefined;
      if (!detail?.dramaId || detail.dramaId === dramaId) void load();
    };
    window.addEventListener('drama-artifacts-updated', onUpdate);
    return () => window.removeEventListener('drama-artifacts-updated', onUpdate);
  }, [dramaId]);

  const openEdit = () => {
    if (!drama) return;
    setForm({
      title: drama.title || '',
      description: drama.description || '',
      genre: drama.genre || '',
      type: resolveType(drama),
    });
    setEditing(true);
  };

  const saveEdit = async () => {
    if (!dramaId) return;
    try {
      await updateDrama(dramaId, {
        title: form.title.trim(),
        description: form.description,
        genre: form.genre,
        type: form.type,
      });
      success(t('studio.toast.saved'), form.title.trim());
      setEditing(false);
      await load();
    } catch (e) {
      error(t('studio.toast.saveFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleDelete = async () => {
    if (!drama) return;
    if (!window.confirm(t('project.deleteWorkConfirm', { title: drama.title }))) return;
    try {
      await deleteDrama(drama.id);
      success(t('dramas.toast.deleted'), drama.title);
      navigate('/dramas');
    } catch (e) {
      error(t('dramas.toast.deleteFailed'), e instanceof Error ? e.message : '');
    }
  };

  const enterStudio = () => {
    if (!drama) return;
    const ty = resolveType(drama);
    if (ty === 'short_drama') navigate(`/studio/${drama.id}`);
    else navigate(`/studio?mode=general&drama_id=${drama.id}`);
  };

  if (loading) {
    return (
      <AppShell title={t('project.workDetail')} subtitle={t('studio.loading')}>
        <div className="px-4 sm:px-10 py-8 max-w-5xl mx-auto space-y-3">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-16 bg-pearl-soft animate-pulse rounded-xl" />
          ))}
        </div>
      </AppShell>
    );
  }

  if (!drama) {
    return (
      <AppShell title={t('project.workDetail')}>
        <div className="px-4 sm:px-10 py-20 max-w-5xl mx-auto text-center">
          <Clapperboard className="w-8 h-8 text-ink-faint mx-auto mb-3" />
          <p className="text-ink-muted">{t('studio.workNotFound')}</p>
          <Link to="/dramas" className="btn btn-secondary mt-4">
            {t('studio.backToWorks')}
          </Link>
        </div>
      </AppShell>
    );
  }

  const ty = resolveType(drama);

  return (
    <AppShell title={drama.title} subtitle={t('project.workDetail')}>
      <div className="px-4 sm:px-10 py-8 max-w-5xl mx-auto space-y-6">
        {/* Meta header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-[11px] px-2 py-0.5 rounded ${TYPE_TONE[ty]}`}>{typeLabel[ty]}</span>
              <span className="text-[11px] text-ink-faint">{drama.genre || t('project.uncategorized')}</span>
              <span className="text-[11px] text-ink-faint">
                {drama.completed_episodes || 0}/{drama.total_episodes || 0} {t('dramas.episodeUnit')}
              </span>
            </div>
            <h1 className="font-display text-3xl font-semibold text-ink mt-2">{drama.title}</h1>
            <p className="text-sm text-ink-muted mt-2 max-w-2xl leading-relaxed">
              {drama.description || t('dramas.noDesc')}
            </p>
            <p className="text-[11px] text-ink-faint mt-2">
              {t('project.createdAt')} {formatDate(drama.created_at, language)} · {t('project.updatedAt')} {formatDate(drama.updated_at, language)}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button type="button" className="btn btn-primary" onClick={enterStudio}>
              {t('project.enterStudio')}
              <ArrowRight className="w-4 h-4" />
            </button>
            <button type="button" className="btn btn-secondary" onClick={openEdit}>
              <Pencil className="w-4 h-4" />
              {t('project.editInfo')}
            </button>
            <button
              type="button"
              className="p-2 rounded-lg text-ink-faint hover:bg-rose-50 hover:text-rose-600"
              onClick={handleDelete}
              title={t('dramas.deleteWork')}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-pearl-line text-sm">
          {(
            [
              { id: 'bible' as const, label: t('project.bibleTab'), icon: BookOpen },
              { id: 'artifacts' as const, label: t('project.artifactsTab'), icon: Layers },
            ]
          ).map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-2.5 font-medium transition-colors border-b-2 -mb-px',
                  tab === t.id
                    ? 'border-atelier-teal text-atelier-teal'
                    : 'border-transparent text-ink-muted hover:text-ink'
                )}
              >
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            );
          })}
        </div>

        {tab === 'bible' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold text-ink">{t('project.bibleContent')}</h2>
              <button
                type="button"
                className="px-3 py-1.5 rounded-lg text-xs font-medium border border-pearl-line text-ink-muted hover:bg-pearl-soft flex items-center gap-1"
                onClick={() => setShowVersions((v) => !v)}
              >
                <History className="w-3.5 h-3.5" />
                {showVersions ? t('project.backToContent') : t('studio.artifacts.versionHistory')}
              </button>
            </div>

            {showVersions ? (
              <div className="rounded-2xl border border-pearl-line bg-white/60 overflow-hidden h-[60vh]">
                <DramaVersionPanel dramaId={drama.id} />
              </div>
            ) : (
              <div className="grid gap-4">
                {drama.outline?.trim() && (
                  <Section title={t('studio.bible.outline')}>
                    <StreamingText content={drama.outline} />
                  </Section>
                )}
                <Section title={t('studio.bible.world')}>
                  <StreamingText content={drama.bible?.world || t('studio.empty')} />
                </Section>
                <Section title={t('studio.bible.characters')}>
                  <StreamingText content={drama.bible?.characters || t('studio.empty')} />
                </Section>
              </div>
            )}
          </div>
        )}

        {tab === 'artifacts' && (
          <div className="rounded-2xl border border-pearl-line bg-white/60 overflow-hidden h-[68vh]">
            <StudioArtifactsPanel dramaId={drama.id} />
          </div>
        )}
      </div>

      {/* Edit modal */}
      {editing && (
        <div className="fixed inset-0 z-40 flex justify-end">
          <div className="absolute inset-0 bg-ink/25" onClick={() => setEditing(false)} />
          <div className="relative w-full max-w-md h-full bg-white border-l border-pearl-line shadow-atelier-lg p-6 overflow-y-auto animate-slide-up">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-2xl font-semibold text-ink">{t('dramas.editTitle')}</h2>
              <button type="button" className="p-2 rounded-lg hover:bg-pearl-soft" onClick={() => setEditing(false)}>
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
                placeholder={t('project.synopsis')}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
              <input
                className="input"
                placeholder={t('project.genrePlaceholder')}
                value={form.genre}
                onChange={(e) => setForm({ ...form, genre: e.target.value })}
              />
              <select
                className="input"
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value as DramaType })}
              >
                <option value="short_drama">{t('dramas.type.short_drama')}</option>
                <option value="long_drama">{t('dramas.type.long_drama')}</option>
                <option value="script_analysis">{t('project.scriptAnalysis')}</option>
              </select>
              <button type="button" className="btn btn-primary w-full" onClick={saveEdit}>
                {t('common.save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-pearl-line bg-white/60 p-5">
      <div className="text-[10px] uppercase tracking-wider text-ink-faint mb-2">{title}</div>
      {children}
    </div>
  );
}

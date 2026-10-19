/**
 * 首页 — 高密度杂志编辑风 + 毛玻璃
 */

import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus,
  ArrowRight,
  Sparkles,
  Users,
  BookOpen,
  ListTree,
  PenLine,
  BarChart3,
  Clock,
  Brain,
  Clapperboard,
  Film,
  Layers,
  Loader2,
  Check,
  ChevronDown,
} from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import {
  listDramas,
  createDrama,
  updateDrama,
  startAutoWrite,
  getAutoWriteStatus,
  type DramaMeta,
} from '@/services/dramaService';
import { getMemorySettings } from '@/services/memoryService';
import { AGENTS_CONFIG, getCoreAgents } from '@/config/agents';
import { startPreflight, getAtelierRunByDrama } from '@/services/atelierService';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n, type TFunction, type Language } from '@/i18n';
import clsx from 'clsx';

const PIPELINE = [
  {
    titleKey: 'dashboard.pipeline.plan.title',
    descKey: 'dashboard.pipeline.plan.desc',
    icon: Sparkles,
    to: '/studio?agent=short_drama_planner',
    agents: '短剧策划助手',
  },
  {
    titleKey: 'dashboard.pipeline.story.title',
    descKey: 'dashboard.pipeline.story.desc',
    icon: BookOpen,
    to: '/studio?agent=story_five_elements',
    agents: '故事五元素分析',
  },
  {
    titleKey: 'dashboard.pipeline.plot.title',
    descKey: 'dashboard.pipeline.plot.desc',
    icon: ListTree,
    to: '/studio?agent=major_plot_points',
    agents: '大情节点分析',
  },
  {
    titleKey: 'dashboard.pipeline.cast.title',
    descKey: 'dashboard.pipeline.cast.desc',
    icon: Users,
    to: '/studio?agent=character_profile_generator',
    agents: '人物小传生成',
  },
  {
    titleKey: 'dashboard.pipeline.write.title',
    descKey: 'dashboard.pipeline.write.desc',
    icon: PenLine,
    to: '/studio?agent=short_drama_creator',
    agents: '短剧创作助手',
  },
  {
    titleKey: 'dashboard.pipeline.eval.title',
    descKey: 'dashboard.pipeline.eval.desc',
    icon: BarChart3,
    to: '/studio?agent=short_drama_evaluation',
    agents: '短剧评估助手',
  },
];

const QUICK_LINKS = [
  { to: '/studio?agent=character_profile_generator', labelKey: 'dashboard.quickLinksItems.bios.label', hintKey: 'dashboard.quickLinksItems.bios.hint' },
  { to: '/studio?agent=story_summary_generator', labelKey: 'dashboard.quickLinksItems.summary.label', hintKey: 'dashboard.quickLinksItems.summary.hint' },
  { to: '/studio?agent=script_evaluation', labelKey: 'dashboard.quickLinksItems.scriptEval.label', hintKey: 'dashboard.quickLinksItems.scriptEval.hint' },
  { to: '/studio?agent=character_relationship_analyzer', labelKey: 'dashboard.quickLinksItems.relations.label', hintKey: 'dashboard.quickLinksItems.relations.hint' },
  { to: '/skills', labelKey: 'dashboard.quickLinksItems.skills.label', hintKey: 'dashboard.quickLinksItems.skills.hint' },
  { to: '/memory', labelKey: 'dashboard.quickLinksItems.memory.label', hintKey: 'dashboard.quickLinksItems.memory.hint' },
];

type DramaStatus = 'completed' | 'serializing' | 'outline' | 'planning';

function dramaStatus(d: DramaMeta): DramaStatus {
  const done = d.completed_episodes || 0;
  const total = d.total_episodes || 1;
  if (d.status === 'completed' || done >= total) return 'completed';
  if (done > 0) return 'serializing';
  if (d.status === 'outline' || d.status === 'writing') return 'outline';
  return 'planning';
}

function statusLabel(status: DramaStatus, t: TFunction): string {
  return t(`dashboard.status.${status}`);
}

function formatRelative(iso: string | undefined, t: TFunction, language: Language): string {
  if (!iso) return t('dashboard.time.recent');
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return t('dashboard.time.recent');
  const diff = Date.now() - time;
  const h = Math.floor(diff / 3600000);
  if (h < 1) return t('dashboard.time.justNow');
  if (h < 24) return t('dashboard.time.hoursAgo', { h });
  const d = Math.floor(h / 24);
  if (d < 7) return t('dashboard.time.daysAgo', { d });
  return new Date(iso).toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US');
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { success, error } = useNotificationStore();
  const { t, language } = useI18n();
  const [dramas, setDramas] = useState<DramaMeta[]>([]);
  const [memoryOn, setMemoryOn] = useState(true);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState('');
  const [title, setTitle] = useState('');
  const [genre, setGenre] = useState('都市情感');
  const [episodes, setEpisodes] = useState(80);
  const [audience, setAudience] = useState('');
  const [tone, setTone] = useState('');
  const [bindDramaId, setBindDramaId] = useState<string>('');
  const [doPreflight, setDoPreflight] = useState(true);
  const [doSerialize, setDoSerialize] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState('');
  const [composerOpen, setComposerOpen] = useState(false);

  const waitForPreflight = async (dramaId: string): Promise<boolean> => {
    const timeoutMs = 15 * 60 * 1000;
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      await new Promise((r) => setTimeout(r, 2500));
      try {
        const res = await getAtelierRunByDrama(dramaId);
        const status = res.run?.status;
        if (status === 'completed') return true;
        if (status === 'error' || status === 'failed') return false;
      } catch {
        /* ignore transient errors */
      }
    }
    return false;
  };

  const handleOneShotGenerate = async () => {
    const hasQuery = query.trim().length > 0;
    const willGenerate = doPreflight || doSerialize;

    // 未勾选任何生成项：直接进入创作台（有创意则先建作品）
    if (!willGenerate) {
      if (!bindDramaId && !hasQuery && !title.trim()) {
        navigate('/studio');
        return;
      }
      setGenerating(true);
      try {
        let dramaId = bindDramaId;
        if (!dramaId) {
          const res = await createDrama({
            title: title.trim() || query.trim().slice(0, 24) || '未命名短剧',
            description: query.trim(),
            genre,
            total_episodes: episodes,
          });
          dramaId = res.drama.id;
        }
        navigate(`/studio/${dramaId}`);
      } catch (e) {
        error('创建失败', e instanceof Error ? e.message : '');
      } finally {
        setGenerating(false);
      }
      return;
    }

    if (!hasQuery) {
      error('请先填写创意', '描述题材、人物或想写的故事');
      return;
    }
    setGenerating(true);
    setProgress('');
    try {
      // 1. 确定作品：绑定已有或新建
      let dramaId = bindDramaId;
      if (!dramaId) {
        const res = await createDrama({
          title: title.trim() || query.trim().slice(0, 24) || '未命名短剧',
          description: query.trim(),
          genre,
          total_episodes: episodes,
        });
        dramaId = res.drama.id;
      } else if (title.trim() || genre || episodes) {
        await updateDrama(dramaId, {
          title: title.trim() || undefined,
          genre,
          total_episodes: episodes,
        });
      }

      const prompt = [
        query.trim(),
        audience.trim() ? `受众：${audience.trim()}` : '',
        tone.trim() ? `调性：${tone.trim()}` : '',
      ].filter(Boolean).join('；');

      // 2. 前置计划（后台执行 + 轮询到完成）
      if (doPreflight) {
        setProgress(t('dashboard.preflightRunning'));
        await startPreflight(dramaId, prompt);
        const ok = await waitForPreflight(dramaId);
        if (!ok) {
          error('前置计划未完成，可能失败', '可进入工作室查看详情');
          navigate(`/studio/${dramaId}`);
          return;
        }
        setProgress(t('dashboard.preflightDone'));
      }

      // 3. 分集全部生成（后台任务 + 轮询到完成）
      if (doSerialize) {
        setProgress(t('dashboard.serializing', { current: 0, total: episodes }));
        const jobRes = await startAutoWrite(dramaId, { from_episode: 1, to_episode: episodes });
        const jobId = jobRes.job_id;
        const jobTimeoutMs = 60 * 60 * 1000;
        const jobStarted = Date.now();
        let lastStatus = '';
        while (Date.now() - jobStarted < jobTimeoutMs) {
          await new Promise((r) => setTimeout(r, 2000));
          try {
            const s = await getAutoWriteStatus(dramaId, jobId);
            const job = s.job;
            if (!job) continue;
            lastStatus = job.status;
            setProgress(t('dashboard.serializing', { current: job.current, total: job.total }));
            if (job.status === 'done' || job.status === 'error' || job.status === 'failed') break;
          } catch {
            /* ignore */
          }
        }
        if (lastStatus === 'error' || lastStatus === 'failed') {
          error('分集生成中断', '可进入工作室继续');
        }
      }

      success(
        doPreflight && doSerialize ? '完整剧本已生成' : '已开始生成',
        '进入工作室查看'
      );
      navigate(`/studio/${dramaId}`);
    } catch (e) {
      error('生成失败', e instanceof Error ? e.message : '');
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [dramaRes, memRes] = await Promise.all([
          listDramas().catch(() => ({ success: false, dramas: [], total: 0 })),
          getMemorySettings({
            user_id: localStorage.getItem('userId') || 'default-user',
          }).catch(() => ({ success: false, data: null })),
        ]);
        setDramas(dramaRes.dramas || []);
        setMemoryOn(memRes.data?.user_enabled !== false);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const sorted = useMemo(() => {
    return [...dramas].sort((a, b) => {
      const ta = new Date(a.updated_at || a.created_at || 0).getTime();
      const tb = new Date(b.updated_at || b.created_at || 0).getTime();
      return tb - ta;
    });
  }, [dramas]);

  const continueDrama = sorted[0] || null;
  const recentWorks = sorted.slice(0, 8);

  const stats = useMemo(() => {
    const completedEps = dramas.reduce((s, d) => s + (d.completed_episodes || 0), 0);
    const totalEps = dramas.reduce((s, d) => s + (d.total_episodes || 0), 0);
    const serializing = dramas.filter((d) => dramaStatus(d) === 'serializing').length;
    const planning = dramas.filter((d) => dramaStatus(d) === 'planning' || dramaStatus(d) === 'outline').length;
    const done = dramas.filter((d) => dramaStatus(d) === 'completed').length;
    return {
      works: dramas.length,
      completedEps,
      totalEps,
      serializing,
      planning,
      done,
      agents: AGENTS_CONFIG.filter((a) => a.status === 'active').length,
      core: getCoreAgents().length,
    };
  }, [dramas]);

  const timeline = useMemo(() => {
    return sorted.slice(0, 8).map((d) => {
      const done = d.completed_episodes || 0;
      const status = dramaStatus(d);
      let action = t('dashboard.action.update');
      if (status === 'planning') action = t('dashboard.action.create');
      else if (status === 'outline') action = t('dashboard.action.outline');
      else if (status === 'serializing') action = t('dashboard.action.serializing', { done });
      else if (status === 'completed') action = t('dashboard.action.completed');
      return {
        id: d.id,
        title: d.title,
        action,
        when: formatRelative(d.updated_at || d.created_at, t, language),
        status,
        genre: d.genre || t('common.shortDrama'),
        done,
        total: d.total_episodes || 1,
      };
    });
  }, [sorted, t, language]);

  return (
    <AppShell
      title={t('dashboard.title')}
      subtitle={t('dashboard.subtitle')}
      actions={
        <div className="flex gap-2">
          <Link to="/studio" className="btn btn-secondary btn-sm hidden sm:inline-flex">
            {t('dashboard.openStudio')}
          </Link>
          <Link to="/dramas" className="btn btn-primary btn-sm">
            <Plus className="w-4 h-4" />
            {t('common.newWork')}
          </Link>
        </div>
      }
    >
      <div className="px-4 sm:px-8 lg:px-10 py-6 sm:py-8 max-w-6xl mx-auto space-y-6 sm:space-y-8">
        <div className="grid lg:grid-cols-5 gap-4 sm:gap-5">
          {/* Hero glass — left, wider */}
          <div className="lg:col-span-3 flex flex-col">
            <section className="atelier-hero p-5 sm:p-6 animate-fade-in flex-1">
              <div className="flex flex-col gap-6">
            <div className="min-w-0">
              <p className="text-[11px] tracking-[0.2em] uppercase text-ink-faint mb-3">
                AI影视 · Editorial Atelier
              </p>
              <h2 className="font-display text-3xl sm:text-4xl font-semibold text-ink leading-[1.12]">
                {t('dashboard.heroTitle')}
              </h2>
              <p className="mt-3 text-sm text-ink-muted max-w-lg leading-relaxed">
                {t('dashboard.heroDesc')}{' '}
                {t(memoryOn ? 'dashboard.memoryOn' : 'dashboard.memoryOff')} · {t('dashboard.expertsReady', { count: stats.core })}
              </p>
              <div className="mt-6 flex flex-wrap gap-2.5">
                {continueDrama ? (
                  <Link to={`/studio/${continueDrama.id}`} className="btn btn-primary">
                    {t('dashboard.continueWork', { title: continueDrama.title })}
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                ) : (
                  <Link to="/dramas" className="btn btn-primary">
                    {t('dashboard.createFirst')}
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                )}
                <Link to="/experts" className="btn btn-secondary">
                  {t('dashboard.expertDir')}
                </Link>
                <Link to="/studio" className="btn btn-ghost btn-sm hidden sm:inline-flex">
                  {t('dashboard.blankStudio')}
                </Link>
              </div>
            </div>

            {/* Compact KPI strip on glass */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full">
              {[
                { labelKey: 'dashboard.kpi.works', value: loading ? '—' : stats.works, icon: Clapperboard },
                { labelKey: 'dashboard.kpi.episodes', value: loading ? '—' : stats.completedEps, icon: Film },
                { labelKey: 'dashboard.kpi.serializing', value: loading ? '—' : stats.serializing, icon: Layers },
                { labelKey: 'dashboard.kpi.experts', value: stats.agents, icon: Users },
              ].map((kpi, i) => (
                <div
                  key={kpi.labelKey}
                  className="glass-dense px-3 py-2.5 animate-stagger-in"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-ink-faint">{t(kpi.labelKey)}</span>
                    <kpi.icon className="w-3 h-3 text-atelier-teal/70" />
                  </div>
                  <div className="font-display text-2xl font-semibold text-ink tabular-nums leading-none mt-1">
                    {kpi.value}
                  </div>
                </div>
              ))}
            </div>
              </div>
            </section>
          </div>

          {/* Atelier composer — right */}
          <div className="lg:col-span-2 flex flex-col">
            <section className="glass-panel p-5 sm:p-6 animate-slide-up flex-1 flex flex-col">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div>
              <h3 className="font-display text-xl font-semibold text-ink">{t('dashboard.composerTitle')}</h3>
              <p className="text-xs text-ink-muted mt-0.5">
                {t('dashboard.composerDesc')}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setComposerOpen((v) => !v)}
              className="shrink-0 p-2 rounded-lg text-ink-muted hover:bg-pearl-soft hover:text-ink transition-colors"
              aria-label={composerOpen ? t('dashboard.collapse') : t('dashboard.expand')}
            >
              <ChevronDown className={clsx('w-4 h-4 transition-transform', composerOpen && 'rotate-180')} />
            </button>
          </div>

          <textarea
            className="w-full min-h-[110px] rounded-xl border border-pearl-line bg-white/70 px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-atelier-teal/30 resize-y"
            placeholder={t('dashboard.composerPlaceholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setDoPreflight((v) => !v)}
              className={clsx(
                'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors',
                doPreflight
                  ? 'border-atelier-teal/40 bg-atelier-teal-soft text-atelier-teal'
                  : 'border-pearl-line bg-white/50 text-ink-muted hover:border-pearl-line'
              )}
            >
              {doPreflight && <Check className="w-3 h-3" />}
              {t('dashboard.togglePreflight')}
            </button>
            <button
              type="button"
              onClick={() => setDoSerialize((v) => !v)}
              className={clsx(
                'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors',
                doSerialize
                  ? 'border-atelier-teal/40 bg-atelier-teal-soft text-atelier-teal'
                  : 'border-pearl-line bg-white/50 text-ink-muted hover:border-pearl-line'
              )}
            >
              {doSerialize && <Check className="w-3 h-3" />}
              {t('dashboard.toggleSerialize')}
            </button>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn btn-primary"
              disabled={generating}
              onClick={() => void handleOneShotGenerate()}
            >
              {generating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {doPreflight && doSerialize
                ? t('dashboard.generateFull')
                : doPreflight
                  ? t('dashboard.generatePreflight')
                  : doSerialize
                    ? t('dashboard.generateSerialize')
                    : t('dashboard.enterStudio')}
            </button>
            {generating && progress && (
              <span className="inline-flex items-center gap-1.5 text-xs text-ink-muted">
                <Loader2 className="w-3 h-3 animate-spin text-atelier-teal" />
                {progress}
              </span>
            )}
          </div>

          {composerOpen && (
            <>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <label className="block text-[11px] text-ink-faint">
              {t('dashboard.titleOptional')}
              <input
                className="mt-1 w-full rounded-lg border border-pearl-line bg-white px-3 py-2 text-sm text-ink"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={t('dashboard.titlePlaceholder')}
              />
            </label>
            <label className="block text-[11px] text-ink-faint">
              {t('dashboard.genre')}
              <input
                className="mt-1 w-full rounded-lg border border-pearl-line bg-white px-3 py-2 text-sm text-ink"
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
              />
            </label>
            <label className="block text-[11px] text-ink-faint">
              {t('dashboard.episodes')}
              <input
                type="number"
                min={1}
                max={200}
                className="mt-1 w-full rounded-lg border border-pearl-line bg-white px-3 py-2 text-sm text-ink"
                value={episodes}
                onChange={(e) => setEpisodes(Number(e.target.value) || 80)}
              />
            </label>
            <label className="block text-[11px] text-ink-faint">
              {t('dashboard.bindDrama')}
              <select
                className="mt-1 w-full rounded-lg border border-pearl-line bg-white px-3 py-2 text-sm text-ink"
                value={bindDramaId}
                onChange={(e) => setBindDramaId(e.target.value)}
              >
                <option value="">{t('dashboard.newWorkOption')}</option>
                {sorted.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="block text-[11px] text-ink-faint">
              {t('dashboard.audience')}
              <input
                className="mt-1 w-full rounded-lg border border-pearl-line bg-white px-3 py-2 text-sm text-ink"
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                placeholder={t('dashboard.audiencePlaceholder')}
              />
            </label>
            <label className="block text-[11px] text-ink-faint">
              {t('dashboard.tone')}
              <input
                className="mt-1 w-full rounded-lg border border-pearl-line bg-white px-3 py-2 text-sm text-ink"
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                placeholder={t('dashboard.tonePlaceholder')}
              />
            </label>
          </div>

            </>
          )}
            </section>
          </div>
        </div>

        {/* Continue + status chips */}
        {continueDrama && (
          <section className="glass-panel p-5 sm:p-6 animate-slide-up">
            <div className="flex items-baseline justify-between mb-3">
              <h3 className="font-display text-xl font-semibold text-ink">{t('dashboard.continueFocus')}</h3>
              <Link to="/dramas" className="text-xs text-atelier-teal hover:underline">
                {t('dashboard.allWorks')}
              </Link>
            </div>
            <Link
              to={`/studio/${continueDrama.id}`}
              className="block rounded-xl border border-pearl-line/70 bg-white/50 px-4 py-4 hover:bg-white/80 hover:border-atelier-teal/30 transition-all duration-300 group"
            >
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-atelier-teal-soft text-atelier-teal">
                      {continueDrama.genre || t('common.shortDrama')}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-pearl-soft text-ink-muted">
                      {statusLabel(dramaStatus(continueDrama), t)}
                    </span>
                    <span className="text-[10px] text-ink-faint">
                      {formatRelative(continueDrama.updated_at || continueDrama.created_at, t, language)}
                    </span>
                  </div>
                  <div className="font-display text-2xl font-semibold text-ink truncate group-hover:text-atelier-teal transition-colors">
                    {continueDrama.title}
                  </div>
                  <p className="mt-1.5 text-sm text-ink-muted line-clamp-2 max-w-xl">
                    {continueDrama.description || t('dashboard.noDesc')}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-mono text-lg text-ink tabular-nums">
                    {continueDrama.completed_episodes || 0}
                    <span className="text-ink-faint text-sm">/{continueDrama.total_episodes || 1}</span>
                  </div>
                  <div className="text-[11px] text-ink-faint mt-0.5">{t('dashboard.completedEps')}</div>
                </div>
              </div>
              <div className="mt-3 h-1 rounded-full bg-pearl-soft overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-atelier-teal to-atelier-teal-mid transition-all duration-700"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.round(
                        ((continueDrama.completed_episodes || 0) / (continueDrama.total_episodes || 1)) *
                          100
                      )
                    )}%`,
                  }}
                />
              </div>
            </Link>

            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-ink-muted">
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-pearl-soft/80">
                <Brain className="w-3 h-3 text-atelier-teal" />
                {t(memoryOn ? 'dashboard.memoryOn' : 'dashboard.memoryOff')}
              </span>
              <span className="px-2 py-1 rounded-full bg-pearl-soft/80">{t('dashboard.status.planning')} {stats.planning}</span>
              <span className="px-2 py-1 rounded-full bg-pearl-soft/80">{t('dashboard.status.serializing')} {stats.serializing}</span>
              <span className="px-2 py-1 rounded-full bg-pearl-soft/80">{t('dashboard.status.completed')} {stats.done}</span>
              <span className="px-2 py-1 rounded-full bg-pearl-soft/80">
                {t('dashboard.totalProgress')} {stats.completedEps}/{stats.totalEps || '—'}
              </span>
            </div>
          </section>
        )}

        {/* Two-column: works + activity */}
        <section className="grid lg:grid-cols-5 gap-4 sm:gap-5">
          <div className="lg:col-span-3 glass-panel p-5 sm:p-6">
            <div className="flex items-baseline justify-between mb-3">
              <h3 className="font-display text-xl font-semibold text-ink">{t('dashboard.worksOverview')}</h3>
              <Link to="/dramas" className="text-xs text-atelier-teal hover:underline">
                {t('common.manage')}
              </Link>
            </div>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} className="h-11 bg-pearl-soft/80 animate-pulse rounded-lg" />
                ))}
              </div>
            ) : recentWorks.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-sm text-ink-muted mb-3">{t('dashboard.noWorksYet')}</p>
                <Link to="/dramas" className="btn btn-primary btn-sm">
                  <Plus className="w-4 h-4" />
                  {t('dashboard.createFromTemplate')}
                </Link>
              </div>
            ) : (
              <ul className="divide-y divide-pearl-line/80">
                {recentWorks.map((d, i) => {
                  const done = d.completed_episodes || 0;
                  const total = d.total_episodes || 1;
                  const pct = Math.min(100, Math.round((done / total) * 100));
                  const st = dramaStatus(d);
                  return (
                    <li key={d.id} className="animate-stagger-in" style={{ animationDelay: `${i * 35}ms` }}>
                      <Link
                        to={`/studio/${d.id}`}
                        className="flex items-center gap-3 py-2.5 hover:bg-white/50 -mx-2 px-2 rounded-lg transition-colors group"
                      >
                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-atelier-teal to-atelier-teal-mid text-white flex items-center justify-center font-display text-sm font-semibold shrink-0 shadow-sm">
                          {(d.title || '剧')[0]}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-ink truncate group-hover:text-atelier-teal">
                              {d.title}
                            </span>
                            <span className="text-[10px] text-ink-faint shrink-0">{statusLabel(st, t)}</span>
                          </div>
                          <div className="mt-1.5 flex items-center gap-2">
                            <div className="flex-1 h-0.5 rounded-full bg-pearl-soft overflow-hidden max-w-[140px]">
                              <div className="h-full bg-atelier-teal rounded-full" style={{ width: `${pct}%` }} />
                            </div>
                            <span className="text-[10px] text-ink-faint tabular-nums">
                              {done}/{total}
                            </span>
                            <span className="text-[10px] text-ink-faint hidden sm:inline">
                              {d.genre || t('common.shortDrama')}
                            </span>
                          </div>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 text-ink-faint opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="lg:col-span-2 glass-panel p-5 sm:p-6">
            <div className="flex items-baseline justify-between mb-3">
              <h3 className="font-display text-xl font-semibold text-ink">{t('dashboard.activity')}</h3>
              <span className="text-[10px] text-ink-faint inline-flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {t('dashboard.feed')}
              </span>
            </div>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-10 bg-pearl-soft/80 animate-pulse rounded-lg" />
                ))}
              </div>
            ) : timeline.length === 0 ? (
              <p className="text-sm text-ink-muted py-6">{t('dashboard.activityEmpty')}</p>
            ) : (
              <ul className="space-y-0.5">
                {timeline.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={`/studio/${item.id}`}
                      className="flex gap-3 py-2 px-2 -mx-2 rounded-lg hover:bg-white/55 transition-colors"
                    >
                      <span className="text-[10px] text-ink-faint w-14 shrink-0 tabular-nums pt-0.5">
                        {item.when}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="text-sm font-medium text-ink block truncate">{item.title}</span>
                        <span className="text-[11px] text-ink-muted">
                          {item.action} · {item.done}/{item.total}
                        </span>
                      </span>
                      <span className="text-[10px] text-atelier-teal shrink-0 pt-0.5">{statusLabel(item.status, t)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        {/* Quick links dense row */}
        <section className="glass-panel p-4 sm:p-5">
          <div className="flex items-baseline justify-between mb-3 px-1">
            <h3 className="font-display text-lg font-semibold text-ink">{t('dashboard.quickLinks')}</h3>
            <span className="text-[10px] text-ink-faint">{t('dashboard.quickLinksHint')}</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 stagger-children">
            {QUICK_LINKS.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="rounded-xl border border-pearl-line/70 bg-white/45 px-3 py-3 hover:bg-atelier-teal-soft/60 hover:border-atelier-teal/30 transition-all duration-200 group"
              >
                <div className="text-sm font-medium text-ink group-hover:text-atelier-teal truncate">
                  {t(item.labelKey)}
                </div>
                <div className="text-[10px] text-ink-faint mt-0.5">{t(item.hintKey)}</div>
              </Link>
            ))}
          </div>
        </section>

        {/* Pipeline dense editorial */}
        <section className="glass-panel p-5 sm:p-6">
          <div className="flex items-baseline justify-between mb-4">
            <div>
              <h3 className="font-display text-xl font-semibold text-ink">{t('dashboard.guide')}</h3>
              <p className="text-xs text-ink-muted mt-0.5">{t('dashboard.guideDesc')}</p>
            </div>
            <Link
              to="/experts"
              className="text-xs text-atelier-teal hover:underline inline-flex items-center gap-1"
            >
              {t('dashboard.allExperts')} <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <ol className="grid sm:grid-cols-2 gap-2">
            {PIPELINE.map((step, i) => (
              <li key={step.titleKey}>
                <Link
                  to={step.to}
                  className={clsx(
                    'group flex items-start gap-3 rounded-xl border border-pearl-line/70 bg-white/40 px-3.5 py-3',
                    'hover:bg-white/80 hover:border-atelier-teal/30 hover:shadow-atelier transition-all duration-250'
                  )}
                  style={{ animationDelay: `${i * 40}ms` }}
                >
                  <span className="font-mono text-[10px] text-ink-faint w-5 pt-1 tabular-nums">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <div className="w-8 h-8 rounded-lg bg-atelier-teal-soft text-atelier-teal flex items-center justify-center shrink-0 group-hover:bg-atelier-teal group-hover:text-white transition-colors duration-200">
                    <step.icon className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-ink">{t(step.titleKey)}</div>
                    <p className="text-[11px] text-ink-muted mt-0.5 truncate">{t(step.descKey)}</p>
                    <span className="inline-block mt-1 text-[10px] text-ink-faint">{step.agents}</span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-ink-faint mt-1 group-hover:text-atelier-teal shrink-0 transition-colors" />
                </Link>
              </li>
            ))}
          </ol>
        </section>

        <footer className="pt-2 pb-4 text-[11px] text-ink-faint flex flex-wrap justify-between gap-2 px-1">
          <span>{t('dashboard.footerTagline')}</span>
          <span className="font-mono">glm-4.7-flash · glass atelier</span>
        </footer>
      </div>
    </AppShell>
  );
}

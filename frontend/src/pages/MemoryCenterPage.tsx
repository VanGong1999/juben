/**
 * 记忆中心 — 生产级五层 Agent Memory 表格化控制台
 * 总览 / 语义事实 / 情节 / 技能 / 反思 / 版本与审计 / 导出与脱敏 / 画像与设置
 */

import { useEffect, useMemo, useState } from 'react';
import {
  Brain,
  Camera,
  User,
  RefreshCw,
  Layers,
  ScrollText,
  History,
  Sparkles,
  Moon,
  Save,
  Download,
  ShieldAlert,
  GitBranch,
  FileJson,
  Users,
  Table2,
  Wrench,
  NotebookPen,
} from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import {
  getMemorySettings,
  updateMemorySettings,
  listMemorySnapshots,
  createMemorySnapshot,
  restoreMemorySnapshot,
  getAgentMemoryOverview,
  getAgentMemoryResident,
  listAgentMemoryFacts,
  listAgentMemoryEpisodes,
  runAgentMemoryForget,
  runAgentMemoryDream,
  getAgentMemoryRules,
  putAgentMemoryRules,
  putUserResident,
  putDramaResident,
  patchAgentMemoryFact,
  deleteAgentMemoryFact,
  deleteAgentMemoryEpisode,
  pinAgentMemoryEpisode,
  reflectAgentMemoryEpisode,
  listAgentMemorySkills,
  promoteAgentMemorySkill,
  toggleAgentMemorySkill,
  deleteAgentMemorySkill,
  listAgentMemoryReflections,
  listAgentMemoryAudit,
  listMemoryVersions,
  rollbackMemoryVersion,
  exportMemory,
  redactMemory,
  getOrgMemory,
  setOrgResident,
  runOrgDream,
} from '@/services/memoryService';
import { listDramas, type DramaMeta } from '@/services/dramaService';
import api from '@/services/api';
import { useAuthStore } from '@/store/authStore';
import { useNotificationStore } from '@/store/notificationStore';
import clsx from 'clsx';
import { useI18n } from '@/i18n';
import FactsTable from '@/components/memory/FactsTable';
import EpisodesTable from '@/components/memory/EpisodesTable';
import SkillsTable from '@/components/memory/SkillsTable';
import ReflectionsTable from '@/components/memory/ReflectionsTable';
import AuditTable from '@/components/memory/AuditTable';
import VersionDiffDrawer from '@/components/memory/VersionDiffDrawer';

type Tab = 'overview' | 'facts' | 'episodes' | 'skills' | 'reflections' | 'versions' | 'export' | 'profile';

export default function MemoryCenterPage() {
  const { user } = useAuthStore();
  const { t } = useI18n();
  const userId = user?.id || localStorage.getItem('userId') || 'default-user';
  const sessionId = localStorage.getItem('sessionId') || 'default-session';
  const { success, error } = useNotificationStore();

  const [tab, setTab] = useState<Tab>('overview');
  const [dramas, setDramas] = useState<DramaMeta[]>([]);
  const [dramaId, setDramaId] = useState(
    () => localStorage.getItem('dramaId') || localStorage.getItem('projectId') || ''
  );

  const [settings, setSettings] = useState<any>(null);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [overview, setOverview] = useState<any>(null);
  const [rules, setRules] = useState('');
  const [userMd, setUserMd] = useState('');
  const [memoryMd, setMemoryMd] = useState('');
  const [facts, setFacts] = useState<any[]>([]);
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [skills, setSkills] = useState<any[]>([]);
  const [reflections, setReflections] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [versions, setVersions] = useState<any[]>([]);
  const [org, setOrg] = useState<{ resident: string; facts: any[]; versions: any[] } | null>(null);
  const [orgMd, setOrgMd] = useState('');
  const [redactResult, setRedactResult] = useState<any>(null);
  const [promoteName, setPromoteName] = useState('');
  const [promoteTrigger, setPromoteTrigger] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [versionsOpen, setVersionsOpen] = useState(false);

  const selectDrama = (id: string) => {
    setDramaId(id);
    if (id) {
      localStorage.setItem('dramaId', id);
      localStorage.setItem('projectId', id);
    }
  };

  const load = async () => {
    setLoading(true);
    try {
      const [s, snap, p, dramaList] = await Promise.all([
        getMemorySettings({ user_id: userId }),
        listMemorySnapshots({ user_id: userId, session_id: sessionId }).catch(() => ({ data: [] })),
        api.get(`/juben/user/profile/${userId}`).catch(() => null),
        listDramas().catch(() => ({ dramas: [] as DramaMeta[] })),
      ]);
      setSettings(s.data || null);
      setSnapshots(Array.isArray(snap.data) ? snap.data : []);
      setProfile((p as any)?.data || (p as any) || null);
      setDramas(Array.isArray(dramaList.dramas) ? dramaList.dramas : []);

      const ov = await getAgentMemoryOverview({
        user_id: userId,
        drama_id: dramaId || undefined,
      });
      setOverview(ov.data || null);

      const res = await getAgentMemoryResident({
        user_id: userId,
        drama_id: dramaId || undefined,
      });
      setUserMd(res.data?.user_md || '');
      setMemoryMd(res.data?.memory_md || '');

      if (dramaId) {
        const [r, f, e, sk, rf, au, v] = await Promise.all([
          getAgentMemoryRules(dramaId),
          listAgentMemoryFacts(dramaId, { active_only: false }),
          listAgentMemoryEpisodes(dramaId, { limit: 40 }),
          listAgentMemorySkills(dramaId, false),
          listAgentMemoryReflections(dramaId),
          listAgentMemoryAudit(dramaId, 40),
          listMemoryVersions(dramaId).catch(() => ({ data: [] })),
        ]);
        setRules(r.data?.content || '');
        setFacts(Array.isArray(f.data) ? f.data : []);
        setEpisodes(Array.isArray(e.data) ? e.data : []);
        setSkills(Array.isArray(sk.data) ? sk.data : []);
        setReflections(Array.isArray(rf.data) ? rf.data : []);
        setAudit(Array.isArray(au.data) ? au.data : []);
        setVersions(Array.isArray(v.data) ? v.data : []);
      } else {
        setRules('');
        setFacts([]);
        setEpisodes([]);
        setSkills([]);
        setReflections([]);
        setAudit([]);
        setVersions([]);
      }

      const o = await getOrgMemory().catch(() => null);
      if (o?.data) {
        setOrg(o.data);
        setOrgMd(o.data.resident || '');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, dramaId]);

  const toggle = async (key: 'user_enabled' | 'project_enabled') => {
    const next = !settings?.[key];
    const res = await updateMemorySettings({ user_id: userId, [key]: next });
    if (res.success) {
      setSettings(res.data);
      success(t('admin.memory.toast.updated'), key === 'user_enabled' ? t('admin.memory.toast.userToggle') : t('admin.memory.toast.projectToggle'));
    }
  };

  const saveResident = async () => {
    setSaving(true);
    try {
      await putUserResident(userId, userMd);
      if (dramaId) {
        await putDramaResident(dramaId, memoryMd);
        await putAgentMemoryRules(dramaId, rules);
      }
      success(t('admin.memory.toast.saved'), t('admin.memory.toast.residentSaved'));
      load();
    } catch (e) {
      error(t('admin.memory.toast.saveFailed'), e instanceof Error ? e.message : '');
    } finally {
      setSaving(false);
    }
  };

  const saveOrg = async () => {
    setSaving(true);
    try {
      await setOrgResident(orgMd);
      success(t('admin.memory.toast.saved'), t('admin.memory.toast.orgSaved'));
      load();
    } catch (e) {
      error(t('admin.memory.toast.saveFailed'), e instanceof Error ? e.message : '');
    } finally {
      setSaving(false);
    }
  };

  const handleForget = async () => {
    if (!dramaId) return error(t('admin.memory.toast.selectFirst'), '');
    try {
      const res = await runAgentMemoryForget(dramaId);
      success(
        t('admin.memory.toast.forgetDone'),
        t('admin.memory.toast.forgetDoneDesc', {
          archived: res.data?.archived_episodes ?? 0,
          expired: res.data?.expired_facts ?? 0,
          decayed: res.data?.decayed_facts ?? 0,
        })
      );
      load();
    } catch (e) {
      error(t('admin.memory.toast.forgetFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleDream = async () => {
    if (!dramaId) return error(t('admin.memory.toast.selectFirst'), '');
    try {
      const res = await runAgentMemoryDream(dramaId, { user_id: userId });
      success(
        t('admin.memory.toast.dreamDone'),
        t('admin.memory.toast.dreamDoneDesc', {
          lessons: res.data?.lessons_written ?? 0,
          reflections: res.data?.reflections ?? 0,
          promoted: (res.data?.skills_promoted || []).length,
        })
      );
      load();
    } catch (e) {
      error(t('admin.memory.toast.dreamFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handlePromote = async () => {
    if (!dramaId || !promoteName || !promoteTrigger) return;
    try {
      const res = await promoteAgentMemorySkill(dramaId, {
        name: promoteName,
        trigger: promoteTrigger,
        min_success: 2,
      });
      if (!res.success) {
        error(t('admin.memory.toast.notPromoted'), res.error || '');
        return;
      }
      success(t('admin.memory.toast.promoted'), promoteName);
      setPromoteName('');
      setPromoteTrigger('');
      load();
    } catch (e) {
      error(t('admin.memory.toast.promoteFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleExport = async () => {
    if (!dramaId) return error(t('admin.memory.toast.selectFirst'), '');
    try {
      const res = await exportMemory(dramaId);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memory-${dramaId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      success(t('admin.memory.toast.exported'), t('admin.memory.toast.exportedDesc'));
    } catch (e) {
      error(t('admin.memory.toast.exportFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleRedact = async (preview: boolean) => {
    if (!dramaId) return error(t('admin.memory.toast.selectFirst'), '');
    try {
      const res = await redactMemory(dramaId, preview);
      setRedactResult(res.data);
      success(preview ? t('admin.memory.toast.redactPreview') : t('admin.memory.toast.redactWritten'), t('admin.memory.toast.redactHits', { count: res.data?.count ?? 0 }));
    } catch (e) {
      error(t('admin.memory.toast.redactFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleRollback = async (versionId: string) => {
    if (!dramaId) return;
    try {
      await rollbackMemoryVersion(dramaId, versionId);
      success(t('admin.memory.toast.rolledBack'), t('admin.memory.toast.rolledTo', { version: versionId }));
      setVersionsOpen(false);
      load();
    } catch (e) {
      error(t('admin.memory.toast.rollbackFailed'), e instanceof Error ? e.message : '');
    }
  };

  const tabs: { id: Tab; label: string; icon: typeof Brain }[] = [
    { id: 'overview', label: t('admin.memory.tab.overview'), icon: Layers },
    { id: 'facts', label: t('admin.memory.tab.facts'), icon: Table2 },
    { id: 'episodes', label: t('admin.memory.tab.episodes'), icon: History },
    { id: 'skills', label: t('admin.memory.tab.skills'), icon: Wrench },
    { id: 'reflections', label: t('admin.memory.tab.reflections'), icon: NotebookPen },
    { id: 'versions', label: t('admin.memory.tab.versions'), icon: GitBranch },
    { id: 'export', label: t('admin.memory.tab.export'), icon: FileJson },
    { id: 'profile', label: t('admin.memory.tab.profile'), icon: User },
  ];

  const dramaStats = overview?.drama;
  const predicateDist = useMemo(() => {
    const m: Record<string, number> = {};
    for (const f of facts) m[f.predicate] = (m[f.predicate] || 0) + 1;
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  }, [facts]);
  const outcomeDist = useMemo(() => {
    const m: Record<string, number> = {};
    for (const e of episodes) m[e.outcome] = (m[e.outcome] || 0) + 1;
    return Object.entries(m);
  }, [episodes]);

  const charBudget = (n: number, max: number) => (
    <span className={clsx('text-[10px]', n > max * 0.9 ? 'text-amber-700' : 'text-ink-faint')}>
      {n}/{max}
    </span>
  );

  return (
    <AppShell
      title={t('admin.memory.title')}
      subtitle={t('admin.memory.subtitle')}
      actions={
        <div className="flex items-center gap-2">
          <select
            className="text-sm border border-studio-line rounded-lg px-2 py-1.5 bg-paper-white max-w-[200px]"
            value={dramaId}
            onChange={(e) => selectDrama(e.target.value)}
          >
            <option value="">{t('admin.memory.selectDrama')}</option>
            {dramas.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title || d.id.slice(0, 8)}
              </option>
            ))}
          </select>
          <button type="button" className="btn btn-ghost btn-sm" onClick={load}>
            <RefreshCw className="w-4 h-4" />
            {t('admin.refresh')}
          </button>
        </div>
      }
    >
      <div className="p-4 sm:p-8 max-w-6xl mx-auto space-y-6">
        <div className="flex gap-1 p-1 bg-paper-cool/80 rounded-xl w-fit flex-wrap">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                tab === id ? 'bg-paper-white text-studio-teal shadow-sm' : 'text-ink-muted'
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="h-48 rounded-2xl bg-paper-cool animate-pulse" />
        ) : tab === 'overview' ? (
          <div className="space-y-5">
            {!dramaId && (
              <p className="text-sm text-ink-muted surface-panel p-4">
                {t('admin.memory.selectHint')}
              </p>
            )}

            <div className="grid sm:grid-cols-4 gap-3">
              {[
                { label: t('admin.memory.stat.episodes'), value: dramaStats?.episodes ?? '—', icon: History },
                { label: t('admin.memory.stat.activeFacts'), value: dramaStats?.facts_active ?? '—', icon: Sparkles },
                { label: t('admin.memory.stat.reflections'), value: dramaStats?.reflections ?? '—', icon: Brain },
                { label: t('admin.memory.stat.promotedSkills'), value: dramaStats?.promoted_skills ?? '—', icon: ScrollText },
              ].map((c) => (
                <div key={c.label} className="surface-panel p-4">
                  <div className="flex items-center gap-2 text-ink-faint text-xs mb-1">
                    <c.icon className="w-3.5 h-3.5" />
                    {c.label}
                  </div>
                  <div className="font-display text-2xl font-semibold text-ink">{c.value}</div>
                </div>
              ))}
            </div>

            {dramaStats && (
              <div className="grid sm:grid-cols-2 gap-3">
                <div className="surface-panel p-4">
                  <h3 className="text-xs font-semibold text-ink-faint mb-2">{t('admin.memory.predicateDist')}</h3>
                  {predicateDist.length === 0 ? (
                    <p className="text-xs text-ink-muted">{t('admin.none')}</p>
                  ) : (
                    <ul className="space-y-1 text-xs">
                      {predicateDist.slice(0, 10).map(([k, v]) => (
                        <li key={k} className="flex justify-between">
                          <span className="font-mono text-ink">{k}</span>
                          <span className="text-ink-faint">{v}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div className="surface-panel p-4">
                  <h3 className="text-xs font-semibold text-ink-faint mb-2">{t('admin.memory.outcomeDist')}</h3>
                  {outcomeDist.length === 0 ? (
                    <p className="text-xs text-ink-muted">{t('admin.none')}</p>
                  ) : (
                    <ul className="space-y-1 text-xs">
                      {outcomeDist.map(([k, v]) => (
                        <li key={k} className="flex justify-between">
                          <span className="text-ink">{k}</span>
                          <span className="text-ink-faint">{v}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}

            <section className="surface-panel p-5 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <h3 className="font-display font-semibold text-ink">{t('admin.memory.residentTitle')}</h3>
                  <p className="text-xs text-ink-muted">{t('admin.memory.residentHint')}</p>
                </div>
                <button type="button" className="btn btn-primary btn-sm" onClick={saveResident} disabled={saving}>
                  <Save className="w-3.5 h-3.5" />
                  {t('common.save')}
                </button>
              </div>
              {dramaId && (
                <div>
                  <div className="flex justify-between text-xs text-ink-muted mb-1">
                    <span>RULES.md</span>
                    {charBudget(rules.length, 8000)}
                  </div>
                  <textarea
                    className="w-full text-xs font-mono min-h-[100px] p-3 rounded-lg border border-studio-line bg-ink/[0.02]"
                    value={rules}
                    onChange={(e) => setRules(e.target.value)}
                  />
                </div>
              )}
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-xs text-ink-muted mb-1">
                    <span>USER.md</span>
                    {charBudget(userMd.length, 4000)}
                  </div>
                  <textarea
                    className="w-full text-xs font-mono min-h-[140px] p-3 rounded-lg border border-studio-line bg-ink/[0.02]"
                    value={userMd}
                    onChange={(e) => setUserMd(e.target.value)}
                  />
                </div>
                <div>
                  <div className="flex justify-between text-xs text-ink-muted mb-1">
                    <span>MEMORY.md</span>
                    {charBudget(memoryMd.length, 6000)}
                  </div>
                  <textarea
                    className="w-full text-xs font-mono min-h-[140px] p-3 rounded-lg border border-studio-line bg-ink/[0.02]"
                    value={memoryMd}
                    onChange={(e) => setMemoryMd(e.target.value)}
                    disabled={!dramaId}
                  />
                </div>
              </div>
            </section>

            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleForget} disabled={!dramaId}>
                {t('admin.memory.runForget')}
              </button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleDream} disabled={!dramaId}>
                <Moon className="w-3.5 h-3.5" />
                {t('admin.memory.runDream')}
              </button>
            </div>
          </div>
        ) : tab === 'facts' ? (
          <FactsTable
            rows={facts}
            onPin={async (f) => {
              await patchAgentMemoryFact(dramaId, f.fact_id, { pinned: !f.pinned, user_id: userId });
              load();
            }}
            onDelete={async (f) => {
              await deleteAgentMemoryFact(dramaId, f.fact_id, { user_id: userId });
              load();
            }}
          />
        ) : tab === 'episodes' ? (
          <EpisodesTable
            rows={episodes}
            onPin={async (e) => {
              await pinAgentMemoryEpisode(dramaId, e.episode_id, !e.pinned);
              load();
            }}
            onReflect={async (e) => {
              await reflectAgentMemoryEpisode(dramaId, e.episode_id, userId);
              success(t('admin.memory.toast.reflectionWritten'), '');
              load();
            }}
            onDelete={async (e) => {
              await deleteAgentMemoryEpisode(dramaId, e.episode_id, userId);
              load();
            }}
          />
        ) : tab === 'skills' ? (
          <div className="space-y-4">
            <section className="surface-panel p-4 space-y-3">
              <h3 className="font-display font-semibold text-ink">{t('admin.memory.promoteTitle')}</h3>
              <div className="flex flex-wrap gap-2 items-end">
                <label className="text-xs text-ink-muted">
                  {t('admin.memory.name')}
                  <input
                    className="block mt-1 border border-studio-line rounded-lg px-2 py-1 text-sm"
                    value={promoteName}
                    onChange={(e) => setPromoteName(e.target.value)}
                    placeholder="卡点写法"
                  />
                </label>
                <label className="text-xs text-ink-muted">
                  Trigger
                  <input
                    className="block mt-1 border border-studio-line rounded-lg px-2 py-1 text-sm"
                    value={promoteTrigger}
                    onChange={(e) => setPromoteTrigger(e.target.value)}
                    placeholder="cliffhanger"
                  />
                </label>
                <button type="button" className="btn btn-secondary btn-sm" onClick={handlePromote} disabled={!dramaId}>
                  {t('admin.memory.promote')}
                </button>
              </div>
            </section>
            <SkillsTable
              rows={skills}
              onToggle={async (s) => {
                await toggleAgentMemorySkill(dramaId, s.skill_id, !s.enabled, userId);
                load();
              }}
              onDelete={async (s) => {
                await deleteAgentMemorySkill(dramaId, s.skill_id, userId);
                load();
              }}
            />
          </div>
        ) : tab === 'reflections' ? (
          <ReflectionsTable rows={reflections} />
        ) : tab === 'versions' ? (
          <div className="space-y-4">
            <section className="surface-panel p-4 flex items-center justify-between gap-2">
              <div>
                <h3 className="font-display font-semibold text-ink">{t('admin.memory.versionHistory')}</h3>
                <p className="text-xs text-ink-muted">{t('admin.memory.versionHint')}</p>
              </div>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setVersionsOpen(true)} disabled={!dramaId}>
                <GitBranch className="w-4 h-4" />
                {t('admin.memory.viewVersions')}
              </button>
            </section>
            <AuditTable rows={audit} />
          </div>
        ) : tab === 'export' ? (
          <div className="space-y-4">
            <section className="surface-panel p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Download className="w-4 h-4 text-studio-teal" />
                <h3 className="font-display font-semibold text-ink">{t('admin.memory.exportTitle')}</h3>
              </div>
              <p className="text-xs text-ink-muted">{t('admin.memory.exportHint')}</p>
              <button type="button" className="btn btn-primary btn-sm" onClick={handleExport} disabled={!dramaId}>
                <Download className="w-3.5 h-3.5" />
                {t('admin.memory.downloadJson')}
              </button>
            </section>
            <section className="surface-panel p-5 space-y-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                <h3 className="font-display font-semibold text-ink">{t('admin.memory.redactTitle')}</h3>
              </div>
              <p className="text-xs text-ink-muted">{t('admin.memory.redactHint')}</p>
              <div className="flex gap-2">
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleRedact(true)} disabled={!dramaId}>
                  {t('admin.memory.previewHits')}
                </button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleRedact(false)} disabled={!dramaId}>
                  {t('admin.memory.writeRedacted')}
                </button>
              </div>
              {redactResult && (
                <div className="space-y-2">
                  <div className="text-sm">{t('admin.memory.hitsCount', { count: redactResult.count })}</div>
                  {redactResult.hits?.length > 0 && (
                    <ul className="text-xs font-mono space-y-1 max-h-40 overflow-auto">
                      {redactResult.hits.slice(0, 20).map((h: any, i: number) => (
                        <li key={i}>
                          <span className="text-amber-700">{h.type}</span> · {h.match}
                        </li>
                      ))}
                    </ul>
                  )}
                  {redactResult.written_to && <div className="text-xs text-ink-muted">{t('admin.memory.writtenTo', { name: redactResult.written_to })}</div>}
                </div>
              )}
            </section>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="surface-panel p-6 space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl bg-studio-teal flex items-center justify-center">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="font-display font-semibold text-ink">{t('admin.memory.contextTitle')}</h2>
                  <p className="text-xs text-ink-muted">{t('admin.memory.contextHint')}</p>
                </div>
              </div>
              {[
                { key: 'user_enabled' as const, label: t('admin.memory.userMemory'), desc: t('admin.memory.userMemoryDesc') },
                { key: 'project_enabled' as const, label: t('admin.memory.projectMemory'), desc: t('admin.memory.projectMemoryDesc') },
              ].map((row) => (
                <div key={row.key} className="flex items-center justify-between py-3 border-t border-studio-line">
                  <div>
                    <div className="text-sm font-medium text-ink">{row.label}</div>
                    <div className="text-xs text-ink-muted">{row.desc}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => toggle(row.key)}
                    className={clsx(
                      'px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
                      settings?.[row.key]
                        ? 'bg-studio-teal text-white border-studio-teal'
                        : 'bg-paper-white text-ink-muted border-studio-line'
                    )}
                  >
                    {settings?.[row.key] ? t('admin.memory.enabled') : t('admin.memory.disabled')}
                  </button>
                </div>
              ))}
            </div>

            <div className="surface-panel p-6 space-y-4">
              <h2 className="font-display font-semibold">{t('admin.memory.profileTitle')}</h2>
              {profile ? (
                <dl className="grid sm:grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-ink-faint text-xs">{t('admin.memory.userId')}</dt>
                    <dd className="font-mono text-ink">{profile.user_id || userId}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-faint text-xs">{t('admin.memory.favGenres')}</dt>
                    <dd>{(profile.fav_genres || []).join('、') || t('admin.memory.notSet')}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-faint text-xs">{t('admin.memory.languageStyle')}</dt>
                    <dd>{(profile.language_style || []).join('、') || t('admin.memory.notSet')}</dd>
                  </div>
                </dl>
              ) : (
                <p className="text-sm text-ink-muted">{t('admin.memory.noProfile')}</p>
              )}
            </div>

            <div className="surface-panel p-6 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-studio-teal" />
                  <h2 className="font-display font-semibold">{t('admin.memory.orgTitle')}</h2>
                </div>
                <div className="flex gap-2">
                  <button type="button" className="btn btn-secondary btn-sm" onClick={saveOrg} disabled={saving}>
                    <Save className="w-3.5 h-3.5" />
                    {t('common.save')}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={async () => {
                      const res = await runOrgDream();
                      success('Org Dreaming', t('admin.memory.toast.orgDreamDone', { count: res.data?.shared_lessons_written ?? 0 }));
                      load();
                    }}
                  >
                    <Moon className="w-3.5 h-3.5" />
                    Org Dreaming
                  </button>
                </div>
              </div>
              <textarea
                className="w-full text-xs font-mono min-h-[140px] p-3 rounded-lg border border-studio-line bg-ink/[0.02]"
                value={orgMd}
                onChange={(e) => setOrgMd(e.target.value)}
              />
              {(org?.facts || []).length > 0 && (
                <ul className="text-xs space-y-1 max-h-40 overflow-auto">
                  {(org?.facts || []).map((f) => (
                    <li key={f.fact_id} className="font-mono">
                      [{f.status}] {f.entity_type}:{f.entity_id} {f.predicate}=<span className="text-ink-muted">{String(f.value).slice(0, 80)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                <h2 className="font-display font-semibold flex items-center gap-2">
                  <Camera className="w-4 h-4 text-studio-teal" />
                  {t('admin.memory.snapshots')}
                </h2>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={async () => {
                    try {
                      await createMemorySnapshot({ user_id: userId, session_id: sessionId, label: '手动快照' });
                      success(t('admin.memory.toast.snapshotCreated'), '');
                      const snap = await listMemorySnapshots({ user_id: userId, session_id: sessionId });
                      setSnapshots(Array.isArray(snap.data) ? snap.data : []);
                    } catch (e) {
                      error(t('admin.memory.toast.snapshotFailed'), e instanceof Error ? e.message : '');
                    }
                  }}
                >
                  <Camera className="w-4 h-4" />
                  {t('admin.memory.createSnapshot')}
                </button>
              </div>
              {snapshots.length === 0 ? (
                <div className="surface-panel p-8 text-center text-sm text-ink-muted">{t('admin.memory.noSnapshots')}</div>
              ) : (
                <ul className="space-y-2">
                  {snapshots.map((s) => (
                    <li key={s.snapshot_id || s.id} className="surface-panel p-4 flex items-center justify-between gap-3">
                      <div>
                        <div className="text-sm font-medium text-ink">
                          {s.description || s.label || s.snapshot_id}
                        </div>
                        <div className="text-xs text-ink-faint">{s.created_at}</div>
                      </div>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={async () => {
                          try {
                            await restoreMemorySnapshot(s.snapshot_id || s.id, {
                              user_id: userId,
                              session_id: sessionId,
                            });
                            success(t('admin.memory.toast.snapshotRestored'), '');
                          } catch (e) {
                            error(t('admin.memory.toast.restoreFailed'), e instanceof Error ? e.message : '');
                          }
                        }}
                      >
                        {t('admin.memory.restore')}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>

      {versionsOpen && dramaId && (
        <VersionDiffDrawer
          dramaId={dramaId}
          versions={versions}
          onClose={() => setVersionsOpen(false)}
          onRollback={handleRollback}
        />
      )}
    </AppShell>
  );
}

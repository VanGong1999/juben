/**
 * 统一工作室 — /studio 与 /studio/:dramaId
 * 左：制片阶段 / 分集 / 设定 · 中：创作图 / 分集 / 画布 · 右：专家坞 + 对话 / Atelier
 */

import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import StudioThreeColumnLayout from '@/components/layout/StudioThreeColumnLayout';
import StudioCreationHeader from '@/components/workspace/StudioCreationHeader';
import AgentBlueprintRail from '@/components/workspace/AgentBlueprintRail';
import StudioDramaRail from '@/components/workspace/StudioDramaRail';
import StudioEpisodePane, { type StudioMidMode } from '@/components/workspace/StudioEpisodePane';
import StudioCreationMap from '@/components/workspace/StudioCreationMap';
import WorkspacePanel from '@/components/workspace/WorkspacePanel';
import ChatPanel from '@/components/workspace/ChatPanel';
import AtelierRunPanel from '@/components/workspace/AtelierRunPanel';
import StudioAgentDock from '@/components/workspace/StudioAgentDock';
import StudioScriptsPanel from '@/components/workspace/StudioScriptsPanel';
import StudioArtifactsPanel from '@/components/workspace/StudioArtifactsPanel';
import GeneralDramaRail from '@/components/workspace/GeneralDramaRail';
import SettingsModal from '@/components/modals/SettingsModal';
import HelpModal from '@/components/modals/HelpModal';
import { useAgentStore } from '@/store/agentStore';
import { useChatStore } from '@/store/chatStore';
import { useNotificationStore } from '@/store/notificationStore';
import { LINKS } from '@/config/links';
import {
  generateOutline,
  getDrama,
  getEpisode,
  listSkills,
  listDramaArtifacts,
  startAutoWrite,
  getAutoWriteStatus,
  startBatchWriteStream,
  writeEpisode,
  updateDrama,
  saveBible,
  deleteEpisode,
  createDrama,
  listDramas,
  type DramaDetail,
  type DramaMeta,
  type DramaType,
} from '@/services/dramaService';
import { startPreflight, getAtelierRunByDrama, type AtelierRun } from '@/services/atelierService';
import type { PipelineStageId, StudioStage } from '@/components/workspace/StudioPipelineRail';
import { Play, Sparkles, FileText, Users, BookOpen, Layers } from 'lucide-react';
import clsx from 'clsx';
import { useI18n } from '@/i18n';

export default function StudioPage() {
  const { t } = useI18n();
  const { dramaId } = useParams<{ dramaId?: string }>();
  const [searchParams] = useSearchParams();
  const { setActiveAgent, agents, activeAgent } = useAgentStore();
  const { sendMessage } = useChatStore();
  const { success, error } = useNotificationStore();
  const navigate = useNavigate();

  const [helpOpen, setHelpOpen] = useState(false);
  const [drama, setDrama] = useState<DramaDetail | null>(null);
  const [loadingDrama, setLoadingDrama] = useState(Boolean(dramaId));
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState('');
  const [selectedEp, setSelectedEp] = useState(1);
  const [editorContent, setEditorContent] = useState('');
  const [editorTitle, setEditorTitle] = useState('');
  const [targetWords, setTargetWords] = useState(1200);
  const [midMode, setMidMode] = useState<StudioMidMode>('map');
  const [skills, setSkills] = useState<Array<{ id: string; name: string; enabled?: boolean }>>([]);
  const [artifactCount, setArtifactCount] = useState(0);
  const [artifactKinds, setArtifactKinds] = useState<string[]>([]);
  const [atelierRun, setAtelierRun] = useState<AtelierRun | null>(null);
  const [activeStageId, setActiveStageId] = useState<PipelineStageId | null>(null);
  const [preflightBusy, setPreflightBusy] = useState(false);
  const [preflightPoll, setPreflightPoll] = useState(false);

  // ---- 工作室模式：短剧创作 / 通用剧本 ----
  const [mode, setMode] = useState<'short_drama' | 'general'>(() => {
    const m = searchParams.get('mode');
    if (m === 'general' || m === 'short_drama') return m;
    return (localStorage.getItem('studioMode') as 'short_drama' | 'general') || 'short_drama';
  });
  const [generalSubTab, setGeneralSubTab] = useState<'create' | 'analyze'>('create');
  const [generalProjects, setGeneralProjects] = useState<DramaMeta[]>([]);
  const [generalDramaId, setGeneralDramaId] = useState<string | null>(null);
  const [generalDrama, setGeneralDrama] = useState<DramaDetail | null>(null);
  const [generalTab, setGeneralTab] = useState<'scripts' | 'agents' | 'artifacts' | 'bible'>('agents');
  const [creatingGeneral, setCreatingGeneral] = useState(false);
  const [generalWorldDraft, setGeneralWorldDraft] = useState('');
  const [generalCharsDraft, setGeneralCharsDraft] = useState('');

  // 前置创作是否完成（以世界观 + 人物设定已落盘为信号）
  const preflightDone = !!(drama?.bible?.world?.trim() && drama?.bible?.characters?.trim());

  const confirmPreflight = (): boolean => {
    if (preflightDone) return true;
    return window.confirm(t('studio.preflightConfirm'));
  };

  const runId = searchParams.get('run') || '';

  useEffect(() => {
    const agentId = searchParams.get('agent');
    if (agentId && agents.some((agent) => agent.id === agentId)) {
      setActiveAgent(agentId);
    }
  }, [searchParams, agents, setActiveAgent]);

  useEffect(() => {
    const projectId = searchParams.get('project_id') || searchParams.get('projectId');
    if (projectId) localStorage.setItem('projectId', projectId);
    if (mode === 'general') {
      const qDrama = searchParams.get('drama_id') || searchParams.get('dramaId') || projectId;
      if (qDrama && qDrama !== generalDramaId) setGeneralDramaId(qDrama);
      return;
    }
    const qDrama = searchParams.get('drama_id') || searchParams.get('dramaId');
    if (qDrama && !dramaId) {
      navigate(`/studio/${qDrama}${searchParams.get('agent') ? `?agent=${searchParams.get('agent')}` : ''}`, {
        replace: true,
      });
    }
  }, [searchParams, dramaId, navigate, mode, generalDramaId]);

  useEffect(() => {
    listSkills()
      .then((res) => {
        if (res.skills) setSkills(res.skills);
      })
      .catch(() => undefined);
  }, []);

  // ---- 通用剧本：项目列表 + 选中项目详情 ----
  const loadGeneralProjects = async () => {
    try {
      const res = await listDramas({ page_size: 200 });
      setGeneralProjects(
        (res.dramas || []).filter(
          (d) => d.type === 'long_drama' || d.type === 'script_analysis'
        )
      );
    } catch {
      setGeneralProjects([]);
    }
  };

  useEffect(() => {
    void loadGeneralProjects();
  }, []);

  useEffect(() => {
    localStorage.setItem('studioMode', mode);
  }, [mode]);

  useEffect(() => {
    if (mode !== 'general') return;
    if (!generalDramaId) {
      setGeneralDrama(null);
      return;
    }
    localStorage.setItem('dramaId', generalDramaId);
    getDrama(generalDramaId)
      .then((res) => {
        const d = res.success && res.drama ? res.drama : null;
        setGeneralDrama(d);
        if (d) {
          setGeneralWorldDraft(d.bible?.world || '');
          setGeneralCharsDraft(d.bible?.characters || '');
        }
      })
      .catch(() => setGeneralDrama(null));
  }, [generalDramaId, mode]);

  const handleNewGeneralProject = async (type: 'long_drama' | 'script_analysis') => {
    const label = type === 'long_drama' ? t('studio.general.longDrama') : t('studio.general.analysisProject');
    const title = window.prompt(t('studio.general.newProjectPrompt', { label }), '')?.trim();
    if (!title) return;
    setCreatingGeneral(true);
    try {
      const res = await createDrama({
        title,
        type: type as DramaType,
        description: '',
        genre: type === 'long_drama' ? '长剧' : '剧本分析',
      });
      if (res.success && res.drama?.id) {
        await loadGeneralProjects();
        setGeneralSubTab(type === 'long_drama' ? 'create' : 'analyze');
        setGeneralDramaId(res.drama.id);
        success(t('studio.general.created', { label }), title);
      } else {
        error(t('dramas.toast.createFailed'), t('dramas.toast.retryLater'));
      }
    } catch (e) {
      error(t('dramas.toast.createFailed'), e instanceof Error ? e.message : t('dramas.toast.networkError'));
    } finally {
      setCreatingGeneral(false);
    }
  };

  const handleGeneralSaveBible = async (payload: { world?: string; characters?: string }) => {
    if (!generalDramaId) return;
    try {
      await saveBible(generalDramaId, payload);
      const res = await getDrama(generalDramaId);
      if (res.success && res.drama) setGeneralDrama(res.drama);
      success(t('studio.toast.bibleSaved'), '');
    } catch (e) {
      error(t('studio.toast.saveFailed'), e instanceof Error ? e.message : '');
    }
  };

  const refreshArtifacts = async (id?: string) => {
    const did = id || dramaId;
    if (!did) {
      setArtifactCount(0);
      setArtifactKinds([]);
      return;
    }
    try {
      const res = await listDramaArtifacts(did, { limit: 200 });
      const items = res.artifacts || [];
      setArtifactCount(res.total || items.length || 0);
      const fromCounts = res.counts
        ? Object.entries(res.counts)
            .filter(([, n]) => Number(n) > 0)
            .map(([k]) => k)
        : [];
      setArtifactKinds(
        fromCounts.length > 0
          ? fromCounts
          : [...new Set(items.map((a) => String(a.kind || '')).filter(Boolean))]
      );
    } catch {
      setArtifactCount(0);
      setArtifactKinds([]);
    }
  };

  useEffect(() => {
    void refreshArtifacts();
    const onUpdate = (e: Event) => {
      const detail = (e as CustomEvent).detail as { dramaId?: string } | undefined;
      if (!detail?.dramaId || detail.dramaId === dramaId) {
        void refreshArtifacts();
        void reload();
      }
    };
    window.addEventListener('drama-artifacts-updated', onUpdate);
    return () => window.removeEventListener('drama-artifacts-updated', onUpdate);
  }, [dramaId]);

  const reload = async () => {
    if (!dramaId) return;
    const res = await getDrama(dramaId);
    if (res.success && res.drama) {
      setDrama(res.drama);
      localStorage.setItem('dramaId', dramaId);
    } else {
      setDrama(null);
    }
  };

  const loadEpisodeBody = async (n: number) => {
    if (!dramaId) return;
    const ep = await getEpisode(dramaId, n);
    if (ep.episode) {
      setEditorTitle(ep.episode.title || t('studio.ep', { n }));
      setEditorContent((ep.episode as { content?: string }).content || '');
    }
  };

  useEffect(() => {
    if (!dramaId) {
      setDrama(null);
      setLoadingDrama(false);
      return;
    }
    setLoadingDrama(true);
    reload()
      .then(() => loadEpisodeBody(1))
      .catch(() => error(t('studio.toast.loadFailed'), t('studio.toast.loadDetailFailed')))
      .finally(() => setLoadingDrama(false));
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

  // 进入工作室时拉取已有编排（前置创作）状态，便于展示进度 / 续跑
  useEffect(() => {
    if (!dramaId) return;
    getAtelierRunByDrama(dramaId)
      .then((res) => {
        if (!res.run) return;
        setAtelierRun(res.run);
        if (res.run.preflight && res.run.status === 'running') {
          setPreflightPoll(true);
        }
      })
      .catch(() => undefined);
  }, [dramaId]);

  // 前置创作进度轮询
  useEffect(() => {
    if (!preflightPoll || !dramaId) return;
    const timer = setInterval(async () => {
      try {
        const res = await getAtelierRunByDrama(dramaId);
        const run = res.run;
        if (run) setAtelierRun(run);
        if (run && (run.status === 'completed' || run.status === 'error')) {
          clearInterval(timer);
          setPreflightPoll(false);
          setPreflightBusy(false);
          await reload();
          await refreshArtifacts();
          if (run.status === 'completed') success(t('studio.toast.preflightDone'), t('studio.toast.preflightDoneHint'));
          else error(t('studio.toast.preflightInterrupted'), t('studio.toast.preflightInterruptedHint'));
        }
      } catch {
        /* ignore */
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [preflightPoll, dramaId]);

  const selectEpisode = async (n: number) => {
    setSelectedEp(n);
    setMidMode('episode');
    setActiveStageId('serialize');
    await loadEpisodeBody(n);
  };

  const handleOutline = async () => {
    if (!dramaId) return;
    setBusy(true);
    try {
      await generateOutline(dramaId, drama?.description);
      await reload();
      await refreshArtifacts();
      success(t('studio.toast.outlineGenerated'), t('studio.toast.updatedToMap'));
      setMidMode('map');
      setActiveStageId('plot');
    } catch (e) {
      error(t('studio.toast.generateFailed'), e instanceof Error ? e.message : '');
    } finally {
      setBusy(false);
    }
  };

  const handleWriteOne = async () => {
    if (!dramaId) return;
    if (!confirmPreflight()) return;
    setBusy(true);
    setActiveAgent('short_drama_creator');
    try {
      const res = await writeEpisode(dramaId, selectedEp, undefined, targetWords);
      if (res.content) setEditorContent(res.content);
      if (res.episode?.title) setEditorTitle(res.episode.title);
      await reload();
      setMidMode('episode');
      success(t('studio.toast.episodeGenerated', { n: selectedEp }), '');
    } catch (e) {
      error(t('studio.toast.writeFailed'), e instanceof Error ? e.message : '');
    } finally {
      setBusy(false);
    }
  };

  const handleUpdateDrama = async (payload: { title?: string; description?: string; genre?: string; total_episodes?: number }) => {
    if (!dramaId) return;
    try {
      await updateDrama(dramaId, payload);
      await reload();
      success(t('studio.toast.saved'), '');
    } catch (e) {
      error(t('studio.toast.saveFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleSaveBible = async (payload: { world?: string; characters?: string }) => {
    if (!dramaId) return;
    try {
      await saveBible(dramaId, payload);
      await reload();
      success(t('studio.toast.bibleSaved'), '');
    } catch (e) {
      error(t('studio.toast.saveFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleDeleteEpisode = async (n: number) => {
    if (!dramaId) return;
    try {
      await deleteEpisode(dramaId, n);
      await reload();
      if (selectedEp === n) {
        setEditorContent('');
        setEditorTitle(t('studio.ep', { n }));
      }
      success(t('studio.toast.episodeDeleted', { n }), '');
    } catch (e) {
      error(t('dramas.toast.deleteFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleAutoWrite = async () => {
    if (!dramaId || !drama) return;
    if (!confirmPreflight()) return;
    setBusy(true);
    setActiveStageId('serialize');
    const from = Math.max(1, (drama.completed_episodes || 0) + 1);
    const to = Math.min(drama.total_episodes, from + 4);
    setJobProgress(t('studio.toast.starting'));
    try {
      // 优先 SSE：连贯性草稿 + 并行单集 subagents（Cursor 风格过程可见）
      await startBatchWriteStream(
        dramaId,
        {
          from_episode: from,
          to_episode: to,
          instruction: `请并行撰写第${from}–${to}集，确保前后连贯、不重复桥段`,
        },
        (ev) => {
          const d = ev.data || {};
          const meta = d.metadata || {};
          if (ev.event === 'subagent_start') {
            const ep = d.episode_number ?? meta.episode_number;
            setJobProgress(`子专家写第 ${ep} 集…`);
          } else if (ev.event === 'subagent_end') {
            const ep = d.episode_number ?? meta.episode_number;
            setJobProgress(`第 ${ep} 集 ${d.success === false ? '失败' : '完成'}`);
          } else if (ev.event === 'system') {
            const msg = typeof d === 'string' ? d : d.content || d.message;
            if (msg) setJobProgress(String(msg).slice(0, 80));
          } else if (ev.event === 'composition') {
            setJobProgress(String(d.message || '并行派出单集编剧…').slice(0, 80));
          }
        }
      );
      await reload();
      setJobProgress('');
      setBusy(false);
      success(t('studio.toast.autoWriteStarted'), t('studio.episodeRange', { from, to }));
    } catch (e) {
      // 回退到后台 job
      try {
        const res = await startAutoWrite(dramaId, { from_episode: from, to_episode: to });
        if (res.job_id) {
          setJobId(res.job_id);
          setJobProgress(t('studio.toast.starting'));
        } else {
          setBusy(false);
          error(t('studio.toast.startFailed'), e instanceof Error ? e.message : '');
        }
      } catch (e2) {
        setBusy(false);
        error(t('studio.toast.startFailed'), e2 instanceof Error ? e2.message : '');
      }
    }
  };

  const handlePreflight = async () => {
    if (!dramaId || preflightBusy) return;
    setPreflightBusy(true);
    try {
      const res = await startPreflight(dramaId, drama?.description, preflightDone);
      if (res.success && res.run) {
        setAtelierRun(res.run);
        setPreflightPoll(true);
        success(t('studio.toast.preflightStarted'), t('studio.toast.preflightDesc'));
      } else {
        setPreflightBusy(false);
      }
    } catch (e) {
      setPreflightBusy(false);
      error(t('studio.toast.startFailed'), e instanceof Error ? e.message : '');
    }
  };

  const handleStageSelect = (stage: StudioStage) => {
    setActiveStageId(stage.id);
    if (stage.agentId) setActiveAgent(stage.agentId);
    if (stage.midMode) setMidMode(stage.midMode);
  };

  const handleAgentAsk = async (prompt: string, agentId: string) => {
    setActiveAgent(agentId);
    try {
      await sendMessage(prompt, agentId);
    } catch (e) {
      error(t('studio.toast.sendFailed'), e instanceof Error ? e.message : '');
    }
  };

  const stagePrompts: Record<string, string> = {
    planning: '围绕这部短剧完善立项策划：题材卖点、目标受众、商业化卡点。\n参考：@drama[characters] @drama[outline]',
    story: '分析这部短剧的故事五元素，并给出可写入设定的世界观要点。\n依据已有设定：@drama[characters] @drama[world] @drama[outline]',
    plot: '为这部短剧拆解大情节点与竖屏节奏，重点服务开篇。\n沿用已有人物，勿杜撰：@drama[characters] @drama[outline]',
    character: '为这部短剧生成或补全主要人物小传，突出关系张力。\n先对照：@drama[characters] @drama[outline] @drama[world]',
    evaluation: `评估第 ${selectedEp} 集完整正文的质量，给出可改进清单。\n以该集正文为准：@drama[episode:${selectedEp}]\n对照人设：@drama[characters]`,
  };

  const handleStartStage = async (stage: StudioStage) => {
    if (!drama) return;
    setActiveStageId(stage.id);
    if (stage.id === 'serialize') {
      setMidMode('episode');
      await handleWriteOne();
      return;
    }
    if (stage.agentId) {
      setActiveAgent(stage.agentId);
      const prompt = stagePrompts[stage.id] || `请开始「${stage.label}」阶段`;
      await handleAgentAsk(prompt, stage.agentId);
    }
  };

  const handleHelpClick = () => {
    if (LINKS.help) {
      window.open(LINKS.help, '_blank');
      return;
    }
    setHelpOpen(true);
  };

  const stageFromRun = useMemo<PipelineStageId | null>(() => {
    if (!atelierRun?.current_step_id) {
      return atelierRun?.status === 'completed' ? 'evaluation' : null;
    }
    const step = atelierRun.steps.find((s) => s.id === atelierRun.current_step_id);
    const mod = step?.module as string | undefined;
    if (mod === 'creation') return 'serialize';
    if (mod === 'planning' || mod === 'story' || mod === 'plot' || mod === 'character' || mod === 'evaluation') {
      return mod;
    }
    return null;
  }, [atelierRun]);

  const resolvedStageId = activeStageId || stageFromRun;

  const modeToggle = (
    <div className="flex gap-0.5 p-0.5 rounded-lg bg-pearl-soft border border-pearl-line">
      {(
        [
          { id: 'short_drama' as const, label: t('studio.mode.shortDrama') },
          { id: 'general' as const, label: t('studio.mode.general') },
        ]
      ).map((m) => (
        <button
          key={m.id}
          type="button"
          onClick={() => setMode(m.id)}
          className={clsx(
            'px-2.5 py-1.5 rounded-md text-[11px] font-medium whitespace-nowrap transition-colors',
            mode === m.id ? 'bg-white text-ink shadow-sm' : 'text-ink-muted hover:text-ink'
          )}
        >
          {m.label}
        </button>
      ))}
    </div>
  );

  if (mode === 'general') {
    const generalHasProject = Boolean(generalDramaId);
    const evaluateAgentId = (() => {
      const a = agents.find((x) => x.id === activeAgent);
      if (a && a.productLine && a.productLine !== 'short_drama') return a.id;
      return 'drama_analysis';
    })();
    const workspaceTabs = [
      { id: 'agents' as const, label: t('studio.tab.agents'), icon: Users },
      { id: 'scripts' as const, label: t('studio.tab.scripts'), icon: FileText },
      { id: 'artifacts' as const, label: t('studio.tab.artifacts'), icon: Layers },
      { id: 'bible' as const, label: t('studio.tab.bible'), icon: BookOpen },
    ];
    return (
      <>
        <StudioThreeColumnLayout
          header={
            <StudioCreationHeader
              onHelpClick={handleHelpClick}
              dramaTitle={generalDrama?.title}
              dramaId={generalDrama?.id}
              extraActions={<>{modeToggle}</>}
            />
          }
          blueprint={
            <GeneralDramaRail
              subTab={generalSubTab}
              onSubTabChange={setGeneralSubTab}
              projects={generalProjects}
              selectedId={generalDramaId}
              onSelectProject={setGeneralDramaId}
              onNewProject={handleNewGeneralProject}
              creating={creatingGeneral}
            />
          }
          workspace={
            <div className="h-full flex flex-col min-h-0">
              <div className="flex shrink-0 border-b border-pearl-line/80 text-[11px]">
                {workspaceTabs.map((t) => {
                  const Icon = t.icon;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setGeneralTab(t.id)}
                      className={clsx(
                        'flex-1 flex items-center justify-center gap-1 py-2.5 font-medium transition-colors',
                        generalTab === t.id
                          ? 'text-atelier-teal border-b-2 border-atelier-teal'
                          : 'text-ink-muted hover:text-ink'
                      )}
                    >
                      <Icon className="w-3 h-3" />
                      {t.label}
                    </button>
                  );
                })}
              </div>
              <div className="flex-1 min-h-0 overflow-hidden">
                {generalTab === 'agents' && (
                  <AgentBlueprintRail productLines={['general', 'shared']} />
                )}
                {generalTab === 'scripts' &&
                  (generalHasProject && generalDramaId ? (
                    <StudioScriptsPanel
                      dramaId={generalDramaId}
                      dramaTitle={generalDrama?.title}
                      evaluateAgentId={evaluateAgentId}
                    />
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center px-6 text-ink-muted">
                      <FileText className="w-8 h-8 text-ink-faint mb-3" />
                      <p className="text-sm">{t('studio.general.selectFirst')}</p>
                    </div>
                  ))}
                {generalTab === 'artifacts' &&
                  (generalHasProject && generalDramaId ? (
                    <StudioArtifactsPanel dramaId={generalDramaId} />
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center px-6 text-ink-muted">
                      <Layers className="w-8 h-8 text-ink-faint mb-3" />
                      <p className="text-sm">{t('studio.general.selectFirst')}</p>
                    </div>
                  ))}
                {generalTab === 'bible' &&
                  (generalHasProject && generalDramaId ? (
                    <div className="h-full overflow-y-auto p-4 sm:p-5 space-y-4">
                      {generalDrama?.outline?.trim() ? (
                        <div className="rounded-xl border border-pearl-line bg-white/60 p-4">
                          <div className="text-[10px] uppercase tracking-wider text-ink-faint mb-1">{t('studio.bible.outline')}</div>
                          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
                            {generalDrama.outline}
                          </pre>
                        </div>
                      ) : null}
                      <div className="rounded-xl border border-pearl-line bg-white/60 p-4">
                        <div className="text-[10px] uppercase tracking-wider text-atelier-teal mb-1">{t('studio.bible.world')}</div>
                        <textarea
                          value={generalWorldDraft}
                          onChange={(e) => setGeneralWorldDraft(e.target.value)}
                          className="w-full min-h-[120px] text-sm leading-relaxed rounded-md border border-pearl-line bg-white/80 p-2 outline-none focus:border-atelier-teal"
                        />
                      </div>
                      <div className="rounded-xl border border-pearl-line bg-white/60 p-4">
                        <div className="text-[10px] uppercase tracking-wider text-ink-faint mb-1">{t('studio.bible.characters')}</div>
                        <textarea
                          value={generalCharsDraft}
                          onChange={(e) => setGeneralCharsDraft(e.target.value)}
                          className="w-full min-h-[160px] text-sm leading-relaxed rounded-md border border-pearl-line bg-white/80 p-2 outline-none focus:border-atelier-teal"
                        />
                      </div>
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() =>
                          handleGeneralSaveBible({ world: generalWorldDraft, characters: generalCharsDraft })
                        }
                      >
                        {t('studio.bible.save')}
                      </button>
                    </div>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center px-6 text-ink-muted">
                      <BookOpen className="w-8 h-8 text-ink-faint mb-3" />
                      <p className="text-sm">{t('studio.general.selectFirst')}</p>
                    </div>
                  ))}
              </div>
            </div>
          }
          chat={<ChatPanel />}
        />
        <SettingsModal />
        <HelpModal isOpen={helpOpen} onClose={() => setHelpOpen(false)} />
      </>
    );
  }

  if (dramaId && loadingDrama) {
    return (
      <div className="min-h-screen bg-pearl flex items-center justify-center">
        <div className="w-48 h-8 rounded-lg bg-pearl-soft animate-pulse" />
      </div>
    );
  }

  if (dramaId && !drama) {
    return (
      <div className="min-h-screen bg-pearl flex flex-col items-center justify-center gap-4">
        <p className="text-ink-muted">{t('studio.workNotFound')}</p>
        <Link to="/dramas" className="btn btn-secondary">
          {t('studio.backToWorks')}
        </Link>
      </div>
    );
  }

  const bound = Boolean(dramaId && drama);

  return (
    <>
      <StudioThreeColumnLayout
        header={
          <div>
            <StudioCreationHeader
              onHelpClick={handleHelpClick}
              dramaTitle={drama?.title}
              dramaId={drama?.id}
              extraActions={
                <>
                  {modeToggle}
                  {bound ? (
                    <>
                      <button
                        type="button"
                        className={preflightDone ? 'btn btn-secondary btn-sm' : 'btn btn-primary btn-sm'}
                        disabled={busy || preflightBusy}
                        onClick={() => void handlePreflight()}
                        title={preflightDone ? t('studio.header.preflightRegenTitle') : t('studio.header.preflightBtn')}
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        {preflightBusy || atelierRun?.status === 'running'
                          ? t('studio.header.preflightGenerating')
                          : preflightDone
                            ? t('studio.header.preflightBtnRegen')
                            : t('studio.header.preflightBtn')}
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm hidden sm:inline-flex"
                        disabled={busy}
                        onClick={handleOutline}
                      >
                        {t('studio.header.generateOutline')}
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm hidden md:inline-flex bg-atelier-gold-soft text-atelier-gold border border-atelier-gold/20"
                        disabled={busy}
                        onClick={handleAutoWrite}
                      >
                        <Play className="w-3.5 h-3.5" />
                        {t('studio.header.autoSerialize')}
                      </button>
                    </>
                  ) : undefined}
                </>
              }
            />
            {jobId && (
              <div className="px-4 py-1.5 text-xs text-atelier-gold bg-atelier-gold-soft border-b border-pearl-line flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 animate-progress-pulse" />
                {t('studio.header.autoWrite', { progress: jobProgress })}
              </div>
            )}
            {atelierRun && (
              <div className="px-4 py-1.5 text-xs text-atelier-teal bg-atelier-teal-soft/60 border-b border-pearl-line flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5" />
                {atelierRun.preflight ? t('studio.header.preflightRunning') : t('studio.header.runRunning')} ·{' '}
                {atelierRun.steps.find((s) => s.id === atelierRun.current_step_id)?.title ||
                  (atelierRun.status === 'completed' ? t('studio.header.allDone') : atelierRun.status)}
              </div>
            )}
          </div>
        }
        blueprint={
          bound && drama ? (
            <StudioDramaRail
              drama={drama}
              selectedEp={selectedEp}
              onSelectEpisode={(n) => {
                void selectEpisode(n);
              }}
              onGenerateOutline={handleOutline}
              busy={busy}
              artifactCount={artifactCount}
              artifactKinds={artifactKinds}
              atelierRun={atelierRun}
              activeStageId={resolvedStageId}
              onOpenMap={() => {
                setMidMode('map');
                setActiveStageId(null);
              }}
              onSelectStage={handleStageSelect}
              onStartStage={handleStartStage}
              onUpdateDrama={handleUpdateDrama}
              onSaveBible={handleSaveBible}
              onDeleteEpisode={handleDeleteEpisode}
            />
          ) : (
            <AgentBlueprintRail />
          )
        }
        workspace={
          bound && drama ? (
            <StudioEpisodePane
              drama={drama}
              selectedEp={selectedEp}
              title={editorTitle}
              content={editorContent}
              skills={skills}
              busy={busy}
              artifactCount={artifactCount}
              onTitleChange={setEditorTitle}
              onContentChange={setEditorContent}
              onWrite={handleWriteOne}
              targetWords={targetWords}
              onTargetWordsChange={setTargetWords}
              midMode={midMode}
              onMidModeChange={setMidMode}
              canvas={<WorkspacePanel />}
              creationMap={
                <StudioCreationMap
                  drama={drama}
                  selectedEp={selectedEp}
                  episodeTitle={editorTitle}
                  episodeContent={editorContent}
                  onSelectEpisode={(n) => {
                    void selectEpisode(n);
                  }}
                  onWriteEpisode={handleWriteOne}
                  onOpenEpisodeEditor={() => setMidMode('episode')}
                  onAsk={(prompt, agentId) => {
                    void handleAgentAsk(prompt, agentId);
                  }}
                  busy={busy}
                />
              }
            />
          ) : (
            <WorkspacePanel />
          )
        }
        chat={
          bound && drama ? (
            <div className="flex flex-col h-full min-h-0">
              {runId && dramaId ? (
                <AtelierRunPanel
                  runId={runId}
                  dramaId={dramaId}
                  onRunUpdated={setAtelierRun}
                  onArtifactsMaybeChanged={() => {
                    void refreshArtifacts();
                    void reload();
                  }}
                />
              ) : (
                <StudioAgentDock
                  drama={drama}
                  selectedEp={selectedEp}
                  episodeTitle={editorTitle}
                  busy={busy}
                  onWriteEpisode={handleWriteOne}
                  onAsk={(prompt, agentId) => {
                    void handleAgentAsk(prompt, agentId);
                  }}
                />
              )}
              <div className="flex-1 min-h-0 overflow-hidden">
                <ChatPanel />
              </div>
            </div>
          ) : (
            <ChatPanel />
          )
        }
      />
      <SettingsModal />
      <HelpModal isOpen={helpOpen} onClose={() => setHelpOpen(false)} />
    </>
  );
}

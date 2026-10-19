/**
 * 图谱审核中心 — AppShell 紧凑布局
 * 处理抽取队列中的低置信度节点 / 情节 / 关系
 */

import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AppShell from '@/components/layout/AppShell';
import { useGraphStore } from '@/store/graphStore';
import {
  ClipboardCheck,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  Network,
  RefreshCw,
} from 'lucide-react';
import { graphService } from '@/services/graphService';
import clsx from 'clsx';
import { useI18n } from '@/i18n';

const PAGE_SIZE = 20;

type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'all';

type ReviewSelection = {
  nodes: number[];
  plot_nodes: number[];
  relationships: number[];
};

export default function GraphReviewCenterPage() {
  const navigate = useNavigate();
  const { t } = useI18n();
  const {
    currentStoryId,
    setCurrentStoryId,
    loadStories,
    stories,
    listReviewQueueEntries,
    getReviewQueueEntry,
    submitGraphReview,
    updateReviewQueueStatus,
  } = useGraphStore();

  const [statusFilter, setStatusFilter] = useState<ReviewStatus>('pending');
  const [queueItems, setQueueItems] = useState<any[]>([]);
  const [queueTotal, setQueueTotal] = useState(0);
  const [queueOffset, setQueueOffset] = useState(0);
  const [queueLoading, setQueueLoading] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [selectedReview, setSelectedReview] = useState<any | null>(null);
  const [selection, setSelection] = useState<ReviewSelection>({
    nodes: [],
    plot_nodes: [],
    relationships: [],
  });
  const [dependencyNotice, setDependencyNotice] = useState('');
  const [graphValidateResult, setGraphValidateResult] = useState<any | null>(null);
  const [characterConsistencyResult, setCharacterConsistencyResult] = useState<any | null>(null);
  const [projectId, setProjectId] = useState(localStorage.getItem('projectId') || '');
  const [enableLlmCheck, setEnableLlmCheck] = useState(false);
  const [validationLoading, setValidationLoading] = useState(false);
  const [backend, setBackend] = useState<string>('');

  useEffect(() => {
    loadStories();
    graphService
      .listStories()
      .then(() =>
        fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/graph/backend`)
          .then((r) => r.json())
          .then((j) => setBackend(j?.data?.backend || ''))
          .catch(() => setBackend(''))
      )
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!currentStoryId && stories.length > 0) {
      setCurrentStoryId(stories[0].story_id);
    }
  }, [stories, currentStoryId, setCurrentStoryId]);

  useEffect(() => {
    const loadQueue = async () => {
      if (!currentStoryId) return;
      setQueueLoading(true);
      try {
        const response = await listReviewQueueEntries({
          story_id: currentStoryId,
          status: statusFilter === 'all' ? undefined : statusFilter,
          limit: PAGE_SIZE,
          offset: queueOffset,
        });
        setQueueItems(response?.items || []);
        setQueueTotal(response?.total || 0);
      } finally {
        setQueueLoading(false);
      }
    };
    loadQueue();
  }, [currentStoryId, statusFilter, queueOffset, refreshTick, listReviewQueueEntries]);

  const toggleSelection = (key: keyof ReviewSelection, index: number) => {
    setSelection((prev) => {
      const set = new Set(prev[key]);
      if (set.has(index)) set.delete(index);
      else set.add(index);
      return { ...prev, [key]: Array.from(set) };
    });
  };

  const normalizeRelationshipPayload = (rel: any) => ({
    ...rel,
    source: rel.source_name || rel.source,
    target: rel.target_name || rel.target,
    source_id: rel.source_id || (rel.source_name ? rel.source : undefined),
    target_id: rel.target_id || (rel.target_name ? rel.target : undefined),
  });

  const ensureRelationshipDependencies = (selectedNodes: any[], relsPayload: any[], allNodes: any[]) => {
    const nodeByName = new Map<string, any>();
    allNodes.forEach((node) => {
      const key = (node.name || '').trim().toLowerCase();
      if (key) nodeByName.set(key, node);
    });
    const selectedNames = new Set(
      selectedNodes.map((node) => (node.name || '').trim().toLowerCase()).filter(Boolean)
    );
    const added: any[] = [];
    relsPayload.forEach((rel) => {
      if (rel.source_id && rel.target_id) return;
      const srcName = (rel.source_name || rel.source || '').trim().toLowerCase();
      const tgtName = (rel.target_name || rel.target || '').trim().toLowerCase();
      if (srcName && !selectedNames.has(srcName) && nodeByName.has(srcName)) {
        added.push(nodeByName.get(srcName));
        selectedNames.add(srcName);
      }
      if (tgtName && !selectedNames.has(tgtName) && nodeByName.has(tgtName)) {
        added.push(nodeByName.get(tgtName));
        selectedNames.add(tgtName);
      }
    });
    return added;
  };

  const openReview = async (item: any) => {
    let detail = item;
    if (!item?.payload) {
      detail = await getReviewQueueEntry(item.review_id);
    }
    setSelectedReview(detail);
    const payload = detail?.payload || {};
    setSelection({
      nodes: (payload.nodes || []).map((_: any, idx: number) => idx),
      plot_nodes: (payload.plot_nodes || []).map((_: any, idx: number) => idx),
      relationships: (payload.relationships || []).map((_: any, idx: number) => idx),
    });
    setDependencyNotice('');
  };

  const handleApprove = async () => {
    if (!currentStoryId || !selectedReview?.payload) return;
    const payload = selectedReview.payload || {};
    const selectedNodes = selection.nodes.map((idx) => payload.nodes?.[idx]).filter(Boolean) || [];
    const selectedPlots = selection.plot_nodes.map((idx) => payload.plot_nodes?.[idx]).filter(Boolean) || [];
    const selectedRels = selection.relationships
      .map((idx) => payload.relationships?.[idx])
      .filter(Boolean)
      .map(normalizeRelationshipPayload);

    const missingDeps = ensureRelationshipDependencies(selectedNodes, selectedRels, payload.nodes || []);
    if (missingDeps.length > 0) {
      setDependencyNotice(t('toolbox.graph.toast.autoFill', { count: missingDeps.length }));
      missingDeps.forEach((node) => selectedNodes.push(node));
    }

    await submitGraphReview({
      story_id: currentStoryId,
      nodes: selectedNodes,
      plot_nodes: selectedPlots,
      relationships: selectedRels,
      review_id: selectedReview.review_id,
    });
    setSelectedReview(null);
    setQueueOffset(0);
    setRefreshTick((prev) => prev + 1);
  };

  const handleReject = async () => {
    if (!selectedReview?.review_id) return;
    await updateReviewQueueStatus({ review_id: selectedReview.review_id, status: 'rejected' });
    setSelectedReview(null);
    setQueueOffset(0);
    setRefreshTick((prev) => prev + 1);
  };

  const totalPages = Math.max(1, Math.ceil(queueTotal / PAGE_SIZE));
  const currentPage = Math.floor(queueOffset / PAGE_SIZE) + 1;

  const handleGraphValidate = async () => {
    if (!currentStoryId) return;
    setValidationLoading(true);
    try {
      const res = await graphService.validateGraph(currentStoryId);
      setGraphValidateResult(res.data || null);
    } finally {
      setValidationLoading(false);
    }
  };

  const handleCharacterConsistency = async () => {
    if (!projectId) return;
    localStorage.setItem('projectId', projectId);
    setValidationLoading(true);
    try {
      const res = await graphService.checkCharacterConsistency({
        project_id: projectId,
        llm_check: enableLlmCheck,
      } as any);
      setCharacterConsistencyResult(res.data || null);
    } finally {
      setValidationLoading(false);
    }
  };

  return (
    <AppShell
      title={t('toolbox.graphReview.title')}
      subtitle={t('toolbox.graphReview.subtitle')}
      actions={
        <div className="flex items-center gap-2">
          {backend && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-pearl-soft text-ink-faint font-mono">
              {backend}
            </span>
          )}
          <Link
            to="/toolbox/graph"
            className="inline-flex items-center gap-1 text-[11px] text-atelier-teal hover:underline"
          >
            <Network className="w-3.5 h-3.5" />
            {t('toolbox.graphReview.openGraph')}
          </Link>
        </div>
      }
    >
      <div className="h-[calc(100vh-3.5rem)] flex flex-col min-h-0">
        {/* 工具条 */}
        <div className="flex-shrink-0 border-b border-pearl-line px-3 py-2 bg-white/70">
          <div className="flex flex-wrap items-center gap-2">
            <ClipboardCheck className="w-4 h-4 text-atelier-teal shrink-0" />
            <select
              className="rounded-md border border-pearl-line bg-pearl-soft/80 px-2 py-1 text-[11px] max-w-[180px]"
              value={currentStoryId || ''}
              onChange={(e) => {
                setCurrentStoryId(e.target.value);
                setQueueOffset(0);
                setSelectedReview(null);
              }}
            >
              <option value="" disabled>
                {t('toolbox.graphReview.selectStory')}
              </option>
              {stories.map((story: any) => (
                <option key={story.story_id} value={story.story_id}>
                  {story.name}
                </option>
              ))}
            </select>

            <div className="flex items-center gap-0.5">
              {(['pending', 'approved', 'rejected', 'all'] as ReviewStatus[]).map((status) => (
                <button
                  key={status}
                  type="button"
                  className={clsx(
                    'px-2 py-0.5 text-[10px] rounded font-medium transition-colors',
                    statusFilter === status
                      ? 'bg-atelier-teal text-white'
                      : 'bg-pearl-soft text-ink-muted hover:text-atelier-teal'
                  )}
                  onClick={() => {
                    setStatusFilter(status);
                    setQueueOffset(0);
                    setSelectedReview(null);
                  }}
                >
                  {status === 'pending'
                    ? t('toolbox.graphReview.status.pending')
                    : status === 'approved'
                      ? t('toolbox.graphReview.status.approved')
                      : status === 'rejected'
                        ? t('toolbox.graphReview.status.rejected')
                        : t('toolbox.graphReview.status.all')}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setRefreshTick((t) => t + 1)}
              className="p-1 rounded border border-pearl-line text-ink-faint hover:text-atelier-teal"
              title={t('toolbox.refresh')}
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>

            <div className="ml-auto flex items-center gap-1.5 text-[10px] text-ink-faint">
              <span>
                {t('toolbox.graphReview.queueCount', { count: queueTotal, page: currentPage, total: totalPages })}
              </span>
              <button
                type="button"
                className="p-0.5 border border-pearl-line rounded disabled:opacity-40"
                onClick={() => setQueueOffset(Math.max(0, queueOffset - PAGE_SIZE))}
                disabled={queueOffset === 0}
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                className="p-0.5 border border-pearl-line rounded disabled:opacity-40"
                onClick={() =>
                  setQueueOffset(Math.min(queueOffset + PAGE_SIZE, (totalPages - 1) * PAGE_SIZE))
                }
                disabled={queueOffset + PAGE_SIZE >= queueTotal}
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleGraphValidate}
              disabled={!currentStoryId || validationLoading}
              className="px-2 py-1 text-[10px] rounded-md border border-pearl-line hover:border-atelier-teal disabled:opacity-50"
            >
              {t('toolbox.graphReview.graphValidate')}
            </button>
            <input
              type="text"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder={t('toolbox.graphReview.projectIdPh')}
              className="w-40 px-2 py-1 text-[10px] rounded-md border border-pearl-line bg-pearl-soft/60"
            />
            <label className="flex items-center gap-1 text-[10px] text-ink-muted">
              <input
                type="checkbox"
                checked={enableLlmCheck}
                onChange={(e) => setEnableLlmCheck(e.target.checked)}
                className="rounded"
              />
              {t('toolbox.graphReview.aiMotivation')}
            </label>
            <button
              type="button"
              onClick={handleCharacterConsistency}
              disabled={!projectId || validationLoading}
              className="px-2 py-1 text-[10px] rounded-md bg-ink text-white disabled:opacity-50"
            >
              {t('toolbox.graphReview.characterConsistency')}
            </button>
            {validationLoading && <span className="text-[10px] text-ink-faint">{t('toolbox.graphReview.detecting')}</span>}
          </div>
        </div>

        {/* 三栏：队列 | 详情 | 校验结果 */}
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[220px_1fr_240px]">
          {/* 队列 */}
          <aside className="border-r border-pearl-line overflow-y-auto bg-white/40">
            {queueLoading && <p className="p-3 text-[11px] text-ink-faint">{t('toolbox.graphReview.loading')}</p>}
            {!queueLoading && !currentStoryId && (
              <p className="p-3 text-[11px] text-ink-faint">{t('toolbox.graphReview.selectStoryFirst')}</p>
            )}
            {!queueLoading && currentStoryId && queueItems.length === 0 && (
              <p className="p-3 text-[11px] text-ink-faint">{t('toolbox.graphReview.noQueue')}</p>
            )}
            <ul className="divide-y divide-pearl-line/80">
              {queueItems.map((item) => (
                <li key={item.review_id}>
                  <button
                    type="button"
                    onClick={() => openReview(item)}
                    className={clsx(
                      'w-full text-left px-2.5 py-2 hover:bg-pearl-soft/80 transition-colors',
                      selectedReview?.review_id === item.review_id && 'bg-atelier-teal-soft/50'
                    )}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <code className="text-[10px] font-mono text-ink truncate">
                        {item.review_id?.slice(0, 10)}
                      </code>
                      <span className="text-[9px] text-ink-faint shrink-0">{item.status}</span>
                    </div>
                    <p className="text-[10px] text-ink-muted mt-0.5">
                      {t('toolbox.graphReview.nodeLine', { nodes: item.nodes_count || 0, plots: item.plot_nodes_count || 0, relations: item.relationships_count || 0 })}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          {/* 详情 */}
          <main className="overflow-y-auto min-w-0 bg-white/30">
            {!selectedReview ? (
              <div className="h-full flex items-center justify-center px-4 text-center">
                <div>
                  <ClipboardCheck className="w-8 h-8 text-ink-faint mx-auto mb-2 opacity-50" />
                  <p className="text-[12px] text-ink-muted">{t('toolbox.graphReview.selectLeft')}</p>
                  <p className="text-[10px] text-ink-faint mt-1">
                    {t('toolbox.graphReview.sampleHint')}
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-3 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-[13px] font-semibold text-ink">{t('toolbox.graphReview.detail')}</h3>
                    <p className="text-[10px] text-ink-faint font-mono mt-0.5">
                      {selectedReview.review_id}
                    </p>
                  </div>
                  <div className="flex gap-1.5 shrink-0">
                    <button
                      type="button"
                      className="px-2.5 py-1 text-[11px] rounded-md border border-pearl-line text-ink-muted"
                      onClick={handleReject}
                    >
                      {t('toolbox.graphReview.reject')}
                    </button>
                    <button
                      type="button"
                      className="px-2.5 py-1 text-[11px] rounded-md bg-atelier-teal text-white"
                      onClick={handleApprove}
                    >
                      {t('toolbox.graphReview.confirmCommit')}
                    </button>
                  </div>
                </div>

                {dependencyNotice && (
                  <p className="text-[10px] text-amber-700 bg-amber-50 px-2 py-1 rounded">
                    {dependencyNotice}
                  </p>
                )}

                <div className="grid sm:grid-cols-3 gap-2">
                  {(
                    [
                      ['nodes', t('toolbox.graphReview.nodes'), 'name', 'type'],
                      ['plot_nodes', t('toolbox.graphReview.plot'), 'title', ''],
                      ['relationships', t('toolbox.graphReview.relations'), 'source', 'target'],
                    ] as const
                  ).map(([key, label, a, b]) => (
                    <div
                      key={key}
                      className="rounded-lg border border-pearl-line bg-white/80 p-2 min-h-[120px]"
                    >
                      <div className="text-[9px] uppercase tracking-wider text-ink-faint mb-1.5">
                        {label}
                      </div>
                      <div className="space-y-1.5 max-h-56 overflow-y-auto">
                        {(selectedReview.payload?.[key] || []).map((item: any, idx: number) => (
                          <label
                            key={`${key}-${idx}`}
                            className="flex items-start gap-1.5 text-[11px] text-ink"
                          >
                            <input
                              type="checkbox"
                              className="mt-0.5"
                              checked={(selection as any)[key].includes(idx)}
                              onChange={() => toggleSelection(key as keyof ReviewSelection, idx)}
                            />
                            <span className="leading-snug">
                              {key === 'relationships' ? (
                                <>
                                  <span className="font-medium">
                                    {item.source} → {item.target}
                                  </span>{' '}
                                  <span className="text-ink-faint">({item.type})</span>
                                </>
                              ) : (
                                <>
                                  <span className="font-medium">{item[a]}</span>
                                  {b && item[b] ? (
                                    <span className="text-ink-faint"> ({item[b]})</span>
                                  ) : null}
                                </>
                              )}
                              {item.confidence !== undefined && (
                                <span className="text-ink-faint"> · {item.confidence}</span>
                              )}
                            </span>
                          </label>
                        ))}
                        {(selectedReview.payload?.[key] || []).length === 0 && (
                          <p className="text-[10px] text-ink-faint">{t('toolbox.graphReview.none')}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {(selectedReview.payload?.validation_issues || []).length > 0 && (
                  <div className="text-[10px] text-amber-800 bg-amber-50/80 border border-amber-100 rounded-md px-2 py-1.5">
                    {(selectedReview.payload.validation_issues as string[]).join('；')}
                  </div>
                )}
              </div>
            )}
          </main>

          {/* 校验侧栏 */}
          <aside className="border-l border-pearl-line overflow-y-auto bg-pearl-soft/30 p-2.5 space-y-2.5 hidden lg:block">
            <section className="rounded-lg border border-pearl-line bg-white/90 p-2.5">
              <div className="flex items-center gap-1.5 mb-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                <span className="text-[11px] font-semibold text-ink">{t('toolbox.graphReview.graphConflict')}</span>
              </div>
              {!graphValidateResult ? (
                <p className="text-[10px] text-ink-faint">{t('toolbox.graphReview.runValidate')}</p>
              ) : (graphValidateResult.issues || []).length === 0 ? (
                <p className="text-[10px] text-emerald-700 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> {t('toolbox.graphReview.noConflict')}
                </p>
              ) : (
                <ul className="space-y-1">
                  {(graphValidateResult.issues || []).map((issue: any, idx: number) => (
                    <li key={idx}>
                      <button
                        type="button"
                        className="text-left text-[10px] text-ink-muted hover:text-atelier-teal w-full"
                        onClick={() => {
                          const focus =
                            issue.source_id || issue.target_id || (issue.nodes && issue.nodes[0]);
                          if (currentStoryId) {
                            navigate(
                              `/toolbox/graph?story_id=${currentStoryId}${
                                focus ? `&focus_node=${focus}` : ''
                              }`
                            );
                          }
                        }}
                      >
                        {issue.message || String(issue)}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-lg border border-pearl-line bg-white/90 p-2.5">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Sparkles className="w-3.5 h-3.5 text-atelier-teal" />
                <span className="text-[11px] font-semibold text-ink">{t('toolbox.graphReview.characterConsistency')}</span>
              </div>
              {!characterConsistencyResult ? (
                <p className="text-[10px] text-ink-faint">{t('toolbox.graphReview.enterProjectId')}</p>
              ) : (characterConsistencyResult.issues || []).length === 0 ? (
                <p className="text-[10px] text-emerald-700 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> {t('toolbox.graphReview.noIssue')}
                </p>
              ) : (
                <ul className="space-y-1">
                  {(characterConsistencyResult.issues || []).map((issue: string, idx: number) => (
                    <li key={idx} className="text-[10px] text-ink-muted">
                      {issue}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </aside>
        </div>
      </div>
    </AppShell>
  );
}

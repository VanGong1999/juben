/**
 * 图数据库可视化页面
 * Graph Database Visualization Page
 *
 * 提供交互式剧本图谱可视化功能，包括：
 * - 角色、情节、世界观规则的关系网络
 * - 角色网络分析
 * - 图谱统计信息
 * - 节点和关系的搜索与过滤
 */

import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useGraphStore } from '@/store/graphStore';
import AppShell from '@/components/layout/AppShell';
import { GraphVisualization } from '@/components/graph';
import { BookOpen, Plus, Search, ChevronDown, ChevronUp, Link2, ClipboardCheck, AlertTriangle, CheckCircle2, Sparkles } from 'lucide-react';
import { graphService } from '@/services/graphService';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';

export default function GraphVisualizationPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const notify = useNotificationStore();
  const { t } = useI18n();
  const {
    currentStoryId,
    setCurrentStoryId,
    loadStoryElements,
    loadStatistics,
    setFilter,
    createCharacter,
    createPlotNode,
    createWorldRule,
    createStory,
    createGenericNode,
    createRelationship,
    extractGraphFromText,
    extractGraphFromFile,
    submitGraphReview,
    createReviewQueueEntry,
    loadStories,
    loadRelationTypes,
    stories,
    nodes,
    relationTypeOptions,
    setSelectedNodeId,
  } = useGraphStore();

  const [showStorySelector, setShowStorySelector] = useState(true);
  const [showToolbar, setShowToolbar] = useState(true);
  const [selectedStoryName, setSelectedStoryName] = useState('');
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const [quickAddType, setQuickAddType] = useState<
    'Character' | 'PlotNode' | 'WorldRule' | 'Location' | 'Item' | 'Conflict' | 'Theme' | 'Motivation'
  >('Character');
  const [quickAddForm, setQuickAddForm] = useState({
    name: '',
    description: '',
    ruleType: 'general',
    status: 'alive',
    location: '',
    sequenceNumber: 1,
    tensionScore: 50,
    importance: 50,
    constraints: '',
    examples: '',
    category: '',
  });
  const [storyModalOpen, setStoryModalOpen] = useState(false);
  const [storyForm, setStoryForm] = useState({
    name: '',
    description: '',
    genre: '',
    tags: '',
    status: 'active',
  });
  const [relationshipModalOpen, setRelationshipModalOpen] = useState(false);
  const [relationshipForm, setRelationshipForm] = useState({
    sourceId: '',
    targetId: '',
    relationType: 'INFLUENCES',
    description: '',
  });
  const [extractModalOpen, setExtractModalOpen] = useState(false);
  const [extractForm, setExtractForm] = useState({
    content: '',
    chunkSize: 4000,
    overlap: 200,
  });
  const [extractFile, setExtractFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewPayload, setPreviewPayload] = useState({
    high: {
      nodes: [] as any[],
      plot_nodes: [] as any[],
      relationships: [] as any[],
    },
    low: {
      nodes: [] as any[],
      plot_nodes: [] as any[],
      relationships: [] as any[],
    },
    validation_issues: [] as any[],
  });
  const [previewSelection, setPreviewSelection] = useState({
    high: {
      nodes: [] as number[],
      plot_nodes: [] as number[],
      relationships: [] as number[],
    },
    low: {
      nodes: [] as number[],
      plot_nodes: [] as number[],
      relationships: [] as number[],
    },
  });
  const [dependencyNotice, setDependencyNotice] = useState('');
  const [validationLoading, setValidationLoading] = useState(false);
  const [graphValidateResult, setGraphValidateResult] = useState<any | null>(null);
  const [characterConsistencyResult, setCharacterConsistencyResult] = useState<any | null>(null);
  const [projectId, setProjectId] = useState(localStorage.getItem('projectId') || '');
  const [enableLlmCheck, setEnableLlmCheck] = useState(true);

  // 初始化：选择第一个故事
  useEffect(() => {
    loadStories();
    loadRelationTypes();
  }, []);

  useEffect(() => {
    if (!currentStoryId && stories.length > 0) {
      const firstStory = stories[0] as any;
      setCurrentStoryId(firstStory.story_id);
      setSelectedStoryName(firstStory.name);
      loadStoryElements(firstStory.story_id);
      loadStatistics(firstStory.story_id);
    }
  }, [stories]);

  useEffect(() => {
    const storyId = searchParams.get('story_id');
    const focusNode = searchParams.get('focus_node');
    if (storyId) {
      const story = stories.find((s: any) => s.story_id === storyId);
      if (story) {
        setCurrentStoryId(story.story_id);
        setSelectedStoryName(story.name);
        loadStoryElements(story.story_id);
        loadStatistics(story.story_id);
      }
    }
    if (focusNode) {
      setSelectedNodeId(focusNode);
    }
  }, [searchParams, stories]);

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

  const handleStoryChange = (storyId: string, storyName: string) => {
    setCurrentStoryId(storyId);
    setSelectedStoryName(storyName);
    loadStoryElements(storyId);
    loadStatistics(storyId);
    setShowStorySelector(false);
  };

  const resetQuickAddForm = () => {
    setQuickAddForm({
      name: '',
      description: '',
      ruleType: 'general',
      status: 'alive',
      location: '',
      sequenceNumber: 1,
      tensionScore: 50,
      importance: 50,
      constraints: '',
      examples: '',
      category: '',
    });
  };

  const handleQuickAddSubmit = async () => {
    if (!currentStoryId || !quickAddForm.name.trim()) return;

    if (quickAddType === 'Character') {
      await createCharacter({
        story_id: currentStoryId,
        name: quickAddForm.name.trim(),
        status: quickAddForm.status as any,
        location: quickAddForm.location || null,
        persona: [],
        arc: 0,
        backstory: null,
        motivations: [],
        flaws: [],
        strengths: [],
      });
    } else if (quickAddType === 'PlotNode') {
      await createPlotNode({
        story_id: currentStoryId,
        title: quickAddForm.name.trim(),
        description: quickAddForm.description.trim(),
        sequence_number: Number(quickAddForm.sequenceNumber) || 1,
        tension_score: Number(quickAddForm.tensionScore) || 50,
        chapter: null,
        characters_involved: [],
        locations: [],
        conflicts: [],
        themes: [],
        importance: Number(quickAddForm.importance) || 50,
        timestamp: null,
      });
    } else if (quickAddType === 'WorldRule') {
      await createWorldRule({
        story_id: currentStoryId,
        name: quickAddForm.name.trim(),
        description: quickAddForm.description.trim(),
        rule_type: quickAddForm.ruleType.trim() || 'general',
        constraints: quickAddForm.constraints
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        examples: quickAddForm.examples
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
      });
    } else {
      await createGenericNode(quickAddType, {
        name: quickAddForm.name.trim(),
        description: quickAddForm.description.trim(),
        category: quickAddForm.category.trim(),
      });
    }

    await loadStoryElements(currentStoryId);
    await loadStatistics(currentStoryId);
    resetQuickAddForm();
    setQuickAddOpen(false);
  };

  const resetStoryForm = () => {
    setStoryForm({
      name: '',
      description: '',
      genre: '',
      tags: '',
      status: 'active',
    });
  };

  const handleCreateStory = async () => {
    if (!storyForm.name.trim()) return;
    const created = await createStory({
      name: storyForm.name.trim(),
      description: storyForm.description.trim(),
      genre: storyForm.genre.trim() || null,
      tags: storyForm.tags
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      status: storyForm.status,
    });
    await loadStories();
    if (created?.story_id) {
      setCurrentStoryId(created.story_id);
      setSelectedStoryName(created.name || storyForm.name.trim());
      await loadStoryElements(created.story_id);
      await loadStatistics(created.story_id);
    }
    resetStoryForm();
    setStoryModalOpen(false);
  };

  const resetRelationshipForm = () => {
    setRelationshipForm({
      sourceId: '',
      targetId: '',
      relationType: 'INFLUENCES',
      description: '',
    });
  };

  const handleCreateRelationship = async () => {
    if (!currentStoryId || !relationshipForm.sourceId || !relationshipForm.targetId) return;
    if (relationshipForm.sourceId === relationshipForm.targetId) return;
    await createRelationship({
      source_id: relationshipForm.sourceId,
      target_id: relationshipForm.targetId,
      relation_type: relationshipForm.relationType as any,
      properties: relationshipForm.description
        ? { description: relationshipForm.description.trim() }
        : {},
    });
    resetRelationshipForm();
    setRelationshipModalOpen(false);
  };

  const resetExtractForm = () => {
    setExtractForm({
      content: '',
      chunkSize: 4000,
      overlap: 200,
    });
    setExtractFile(null);
    setFileInputKey((prev) => prev + 1);
  };

  const handleExtractPreview = async () => {
    if (!currentStoryId) {
      notify.warning(t('toolbox.graph.toast.noStory'), t('toolbox.graph.toast.noStoryDesc'));
      return;
    }
    if (!extractFile && !extractForm.content.trim()) {
      notify.warning(t('toolbox.graph.toast.emptyContent'), t('toolbox.graph.toast.emptyContentDesc'));
      return;
    }
    let result: any = null;
    try {
      if (extractFile) {
        result = await extractGraphFromFile({
          story_id: currentStoryId,
          file: extractFile,
          chunk_size: extractForm.chunkSize,
          overlap: extractForm.overlap,
          dry_run: true,
        });
      } else {
        result = await extractGraphFromText({
          story_id: currentStoryId,
          content: extractForm.content.trim(),
          chunk_size: extractForm.chunkSize,
          overlap: extractForm.overlap,
          dry_run: true,
        });
      }
    } catch (err: any) {
      notify.error(t('toolbox.graph.toast.extractFailed'), err?.message || t('toolbox.graph.toast.extractFailedDesc'));
      return;
    }
    const pending = result?.pending_review || {};
    const created = {
      nodes: result?.nodes || [],
      plot_nodes: result?.plot_nodes || [],
      relationships: result?.relationships || [],
    };
    const low = {
      nodes: pending.nodes || [],
      plot_nodes: pending.plot_nodes || [],
      relationships: pending.relationships || [],
    };
    setPreviewPayload({
      high: created,
      low,
      validation_issues: result?.validation_issues || [],
    });
    setPreviewSelection({
      high: {
        nodes: created.nodes.map((_: any, idx: number) => idx),
        plot_nodes: created.plot_nodes.map((_: any, idx: number) => idx),
        relationships: created.relationships.map((_: any, idx: number) => idx),
      },
      low: {
        nodes: low.nodes.map((_: any, idx: number) => idx),
        plot_nodes: low.plot_nodes.map((_: any, idx: number) => idx),
        relationships: low.relationships.map((_: any, idx: number) => idx),
      },
    });
    setDependencyNotice('');
    setPreviewModalOpen(true);
    resetExtractForm();
    setExtractModalOpen(false);
  };

  const togglePreviewSelection = (
    bucket: 'high' | 'low',
    key: 'nodes' | 'plot_nodes' | 'relationships',
    index: number
  ) => {
    setPreviewSelection((prev) => {
      const set = new Set(prev[bucket][key]);
      if (set.has(index)) {
        set.delete(index);
      } else {
        set.add(index);
      }
      return { ...prev, [bucket]: { ...prev[bucket], [key]: Array.from(set) } };
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
        const node = nodeByName.get(srcName);
        added.push(node);
        selectedNames.add(srcName);
      }
      if (tgtName && !selectedNames.has(tgtName) && nodeByName.has(tgtName)) {
        const node = nodeByName.get(tgtName);
        added.push(node);
        selectedNames.add(tgtName);
      }
    });
    return added;
  };

  const handleSubmitPreview = async () => {
    if (!currentStoryId) return;
    const selectedHighNodes = previewSelection.high.nodes
      .map((idx) => previewPayload.high.nodes[idx])
      .filter(Boolean);
    const selectedHighPlots = previewSelection.high.plot_nodes
      .map((idx) => previewPayload.high.plot_nodes[idx])
      .filter(Boolean);
    const selectedHighRels = previewSelection.high.relationships
      .map((idx) => previewPayload.high.relationships[idx])
      .filter(Boolean)
      .map(normalizeRelationshipPayload);

    const selectedLowNodes = previewSelection.low.nodes
      .map((idx) => previewPayload.low.nodes[idx])
      .filter(Boolean);
    const selectedLowPlots = previewSelection.low.plot_nodes
      .map((idx) => previewPayload.low.plot_nodes[idx])
      .filter(Boolean);
    const selectedLowRels = previewSelection.low.relationships
      .map((idx) => previewPayload.low.relationships[idx])
      .filter(Boolean)
      .map(normalizeRelationshipPayload);

    const selectedNodes = [...selectedHighNodes, ...selectedLowNodes];
    const selectedPlots = [...selectedHighPlots, ...selectedLowPlots];
    const selectedRels = [...selectedHighRels, ...selectedLowRels];

    const allCandidateNodes = [...previewPayload.high.nodes, ...previewPayload.low.nodes];
    const missingDeps = ensureRelationshipDependencies(selectedNodes, selectedRels, allCandidateNodes);
    if (missingDeps.length > 0) {
      setDependencyNotice(t('toolbox.graph.toast.autoFill', { count: missingDeps.length }));
      missingDeps.forEach((node) => selectedNodes.push(node));
    }

    await submitGraphReview({
      story_id: currentStoryId,
      nodes: selectedNodes,
      plot_nodes: selectedPlots,
      relationships: selectedRels,
    });
    setPreviewModalOpen(false);
  };

  const handleSaveToReviewQueue = async () => {
    if (!currentStoryId) return;
    const selectedLowNodes = previewSelection.low.nodes
      .map((idx) => previewPayload.low.nodes[idx])
      .filter(Boolean);
    const selectedLowPlots = previewSelection.low.plot_nodes
      .map((idx) => previewPayload.low.plot_nodes[idx])
      .filter(Boolean);
    const selectedLowRels = previewSelection.low.relationships
      .map((idx) => previewPayload.low.relationships[idx])
      .filter(Boolean);
    if (
      selectedLowNodes.length === 0 &&
      selectedLowPlots.length === 0 &&
      selectedLowRels.length === 0
    ) {
      return;
    }

    await createReviewQueueEntry({
      story_id: currentStoryId,
      payload: {
        nodes: selectedLowNodes,
        plot_nodes: selectedLowPlots,
        relationships: selectedLowRels,
        validation_issues: previewPayload.validation_issues || [],
      },
      source: 'extract:preview',
    });
    setPreviewModalOpen(false);
  };

  return (
    <AppShell
      title={t('toolbox.graph.title')}
      subtitle={t('toolbox.graph.subtitle')}
      actions={
        <Link
          to="/toolbox/graph-review"
          className="inline-flex items-center gap-1 text-[11px] text-atelier-teal hover:underline"
        >
          <ClipboardCheck className="w-3.5 h-3.5" />
          {t('toolbox.graph.reviewQueue')}
        </Link>
      }
    >
      <div className="px-4 sm:px-8 lg:px-10 py-6 sm:py-8 max-w-6xl mx-auto space-y-6 sm:space-y-8">
        {/* 工具栏 */}
        <div className="glass-panel p-5 sm:p-6 space-y-5">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider text-ink-faint">{t('toolbox.graph.toolbar')}</span>
            <button
              type="button"
              onClick={() => setShowToolbar(!showToolbar)}
              className="inline-flex items-center gap-1 text-xs text-ink-faint hover:text-ink transition-colors"
            >
              {showToolbar ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
          {showToolbar && (
            <>
          {/* 操作按钮 */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setStoryModalOpen(true)}
              className="btn btn-primary btn-sm"
              title={t('toolbox.graph.createStory')}
            >
              <Plus className="w-4 h-4" />
              {t('toolbox.graph.newStory')}
            </button>
            <button
              onClick={() => setQuickAddOpen(true)}
              className="btn btn-secondary btn-sm"
              title={t('toolbox.graph.quickAddNode')}
            >
              <Plus className="w-4 h-4" />
              {t('toolbox.graph.add')}
            </button>
            <button
              onClick={() => setRelationshipModalOpen(true)}
              className="btn btn-secondary btn-sm"
              title={t('toolbox.graph.createRelation')}
            >
              <Link2 className="w-4 h-4" />
              {t('toolbox.graph.relation')}
            </button>
            <button
              onClick={() => setExtractModalOpen(true)}
              className="btn btn-secondary btn-sm"
              title={t('toolbox.graph.autoExtractTitle')}
            >
              {t('toolbox.graph.autoExtract')}
            </button>
            <button
              onClick={() => navigate('/toolbox/graph-review')}
              className="btn btn-secondary btn-sm"
              title={t('toolbox.graph.review')}
            >
              <ClipboardCheck className="w-4 h-4" />
              {t('toolbox.graph.review')}
            </button>
            <button
              onClick={handleGraphValidate}
              className="btn btn-secondary btn-sm"
              title={t('toolbox.graph.graphValidate')}
              disabled={!currentStoryId || validationLoading}
            >
              {t('toolbox.graph.graphValidate')}
            </button>
            <button
              onClick={handleCharacterConsistency}
              className="btn btn-primary btn-sm"
              title={t('toolbox.graph.characterConsistency')}
              disabled={!projectId || validationLoading}
            >
              {t('toolbox.graph.characterConsistency')}
            </button>
          </div>

          {/* 工具栏 */}
          <div className="flex flex-wrap items-center gap-3">
            {/* 故事选择器 */}
            <div className="relative">
              <button
                onClick={() => setShowStorySelector(!showStorySelector)}
                className="flex items-center gap-2 px-4 py-2 bg-pearl-soft hover:bg-pearl-line rounded-lg transition-colors"
              >
                <BookOpen className="w-4 h-4 text-ink-muted" />
                <span className="text-sm font-medium text-ink">
                  {selectedStoryName || t('toolbox.graph.selectStory')}
                </span>
                <ChevronDown
                  className={`w-4 h-4 text-ink-muted transition-transform ${
                    showStorySelector ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {showStorySelector && (
                <div className="absolute top-full left-0 mt-2 w-64 glass-dense shadow-lg z-10">
                  <div className="p-2">
                    {stories.length === 0 && (
                      <div className="px-3 py-2 text-sm text-ink-muted">{t('toolbox.graph.noStory')}</div>
                    )}
                    {stories.map((story: any) => (
                      <button
                        key={story.story_id}
                        onClick={() => handleStoryChange(story.story_id, story.name)}
                        className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                          currentStoryId === story.story_id
                            ? 'bg-atelier-teal-soft text-atelier-teal'
                            : 'hover:bg-pearl-soft text-ink'
                        }`}
                      >
                        <div className="font-medium text-sm">{story.name}</div>
                        <div className="text-xs text-ink-muted">{story.description}</div>
                      </button>
                    ))}
                    <button
                      onClick={() => {
                        setShowStorySelector(false);
                        setStoryModalOpen(true);
                      }}
                      className="w-full text-left px-3 py-2 rounded-lg transition-colors hover:bg-pearl-soft text-ink"
                    >
                      <div className="font-medium text-sm">+ {t('toolbox.graph.newStory')}</div>
                      <div className="text-xs text-ink-muted">{t('toolbox.graph.createStoryHint')}</div>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* 搜索框 */}
            <div className="relative flex-1 min-w-[200px] max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-faint" />
              <input
                type="text"
                placeholder={t('toolbox.graph.searchNodes')}
                className="w-full pl-10 pr-4 py-2 border border-pearl-line rounded-lg focus:outline-none focus:border-atelier-teal text-sm"
                onChange={(e) => setFilter({ searchQuery: e.target.value })}
              />
            </div>
            <input
              type="text"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder={t('toolbox.graph.projectIdPh')}
              className="px-3 py-2 border border-pearl-line rounded-lg text-sm"
            />
            <label className="flex items-center gap-2 text-xs text-ink-muted">
              <input
                type="checkbox"
                checked={enableLlmCheck}
                onChange={(e) => setEnableLlmCheck(e.target.checked)}
              />
              {t('toolbox.graph.motivationAi')}
            </label>
          </div>

          {(graphValidateResult || characterConsistencyResult) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="glass-dense p-3">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  <span className="text-sm font-semibold text-ink">{t('toolbox.graph.graphConflict')}</span>
                </div>
                {!graphValidateResult ? (
                  <div className="text-xs text-ink-muted">{t('toolbox.graph.noValidateResult')}</div>
                ) : (graphValidateResult.issues || []).length === 0 ? (
                  <div className="text-xs text-emerald-600 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" /> {t('toolbox.graph.noConflict')}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {graphValidateResult.issues.map((issue: any, idx: number) => (
                      <button
                        key={`${issue.message || issue}-${idx}`}
                        className="text-left text-xs text-ink border border-pearl-line rounded-lg p-2 hover:bg-pearl-soft"
                        onClick={() => {
                          const focus = issue.source_id || issue.target_id || (issue.nodes && issue.nodes[0]);
                          if (focus) {
                            setSelectedNodeId(focus);
                          }
                        }}
                      >
                        {issue.message || issue}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div className="glass-dense p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-atelier-teal" />
                  <span className="text-sm font-semibold text-ink">{t('toolbox.graph.characterConsistency')}</span>
                </div>
                {!characterConsistencyResult ? (
                  <div className="text-xs text-ink-muted">{t('toolbox.graph.noDetectResult')}</div>
                ) : (characterConsistencyResult.issues || []).length === 0 ? (
                  <div className="text-xs text-emerald-600 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" /> {t('toolbox.graph.noIssue')}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {characterConsistencyResult.issues.map((issue: string, idx: number) => (
                      <div key={`${issue}-${idx}`} className="text-xs text-ink border border-pearl-line rounded-lg p-2">
                        {issue}
                      </div>
                    ))}
                  </div>
                )}
                {characterConsistencyResult?.llm_motivation && (
                  <div className="mt-2 text-xs text-ink-muted">
                    {t('toolbox.graph.motivationScore')}: {characterConsistencyResult.llm_motivation.score ?? '-'}
                  </div>
                )}
              </div>
            </div>
          )}
            </>
          )}
        </div>

        {/* 图谱可视化区域 */}
        <div className="glass-panel overflow-hidden relative">
          <div className="relative h-[70vh] min-h-[480px]">
            <GraphVisualization className="w-full h-full" height="100%" />
            {!currentStoryId && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-sm text-ink-muted">
                <span>{t('toolbox.graph.createStoryFirst')}</span>
                <button
                  type="button"
                  onClick={() => setStoryModalOpen(true)}
                  className="btn btn-primary btn-sm"
                >
                  <Plus className="w-4 h-4" />
                  {t('toolbox.graph.newStory')}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 快速添加菜单（当用户点击"添加"按钮时显示） */}
      {quickAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-ink">{t('toolbox.graph.quickAddNode')}</h3>
              <button
                onClick={() => setQuickAddOpen(false)}
                className="text-ink-muted hover:text-ink"
              >
                {t('toolbox.close')}
              </button>
            </div>

            <div className="flex gap-2 mb-4">
              {(
                [
                  'Character',
                  'PlotNode',
                  'WorldRule',
                  'Location',
                  'Item',
                  'Conflict',
                  'Theme',
                  'Motivation',
                ] as const
              ).map((type) => (
                <button
                  key={type}
                  onClick={() => setQuickAddType(type)}
                  className={`px-3 py-2 text-sm rounded-lg border ${
                    quickAddType === type
                      ? 'bg-atelier-teal-soft text-atelier-teal border-atelier-teal/20'
                      : 'bg-white text-ink-muted border-pearl-line'
                  }`}
                >
                  {type === 'Character'
                    ? t('toolbox.graph.nodeType.character')
                    : type === 'PlotNode'
                    ? t('toolbox.graph.nodeType.plot')
                    : type === 'WorldRule'
                    ? t('toolbox.graph.nodeType.rule')
                    : type === 'Location'
                    ? t('toolbox.graph.nodeType.location')
                    : type === 'Item'
                    ? t('toolbox.graph.nodeType.item')
                    : type === 'Conflict'
                    ? t('toolbox.graph.nodeType.conflict')
                    : type === 'Theme'
                    ? t('toolbox.graph.nodeType.theme')
                    : t('toolbox.graph.nodeType.motivation')}
                </button>
              ))}
            </div>

            <div className="space-y-3">
              <input
                className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                placeholder={quickAddType === 'PlotNode' ? t('toolbox.graph.plotTitle') : t('toolbox.graph.name')}
                value={quickAddForm.name}
                onChange={(e) => setQuickAddForm({ ...quickAddForm, name: e.target.value })}
              />

              {quickAddType !== 'Character' && quickAddType !== 'Location' && quickAddType !== 'Item' && quickAddType !== 'Conflict' && quickAddType !== 'Theme' && quickAddType !== 'Motivation' && (
                <textarea
                  className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                  placeholder={t('toolbox.graph.description')}
                  rows={3}
                  value={quickAddForm.description}
                  onChange={(e) => setQuickAddForm({ ...quickAddForm, description: e.target.value })}
                />
              )}

              {['Location', 'Item', 'Conflict', 'Theme', 'Motivation'].includes(quickAddType) && (
                <>
                  <textarea
                    className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                    placeholder={t('toolbox.graph.description')}
                    rows={3}
                    value={quickAddForm.description}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, description: e.target.value })
                    }
                  />
                  <input
                    className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                    placeholder={t('toolbox.graph.categoryOptional')}
                    value={quickAddForm.category}
                    onChange={(e) => setQuickAddForm({ ...quickAddForm, category: e.target.value })}
                  />
                </>
              )}

              {quickAddType === 'Character' && (
                <>
                  <div className="flex gap-2">
                    <select
                      className="flex-1 rounded-lg border border-pearl-line px-3 py-2 text-sm"
                      value={quickAddForm.status}
                      onChange={(e) => setQuickAddForm({ ...quickAddForm, status: e.target.value })}
                    >
                      <option value="alive">{t('toolbox.graph.status.alive')}</option>
                      <option value="deceased">{t('toolbox.graph.status.deceased')}</option>
                      <option value="unknown">{t('toolbox.graph.status.unknown')}</option>
                    </select>
                    <input
                      className="flex-1 rounded-lg border border-pearl-line px-3 py-2 text-sm"
                      placeholder={t('toolbox.graph.locationOptional')}
                      value={quickAddForm.location}
                      onChange={(e) => setQuickAddForm({ ...quickAddForm, location: e.target.value })}
                    />
                  </div>
                </>
              )}

              {quickAddType === 'PlotNode' && (
                <div className="grid grid-cols-3 gap-2">
                  <input
                    type="number"
                    className="rounded-lg border border-pearl-line px-3 py-2 text-sm"
                    placeholder={t('toolbox.graph.sequence')}
                    value={quickAddForm.sequenceNumber}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, sequenceNumber: Number(e.target.value) })
                    }
                  />
                  <input
                    type="number"
                    className="rounded-lg border border-pearl-line px-3 py-2 text-sm"
                    placeholder={t('toolbox.graph.tension')}
                    value={quickAddForm.tensionScore}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, tensionScore: Number(e.target.value) })
                    }
                  />
                  <input
                    type="number"
                    className="rounded-lg border border-pearl-line px-3 py-2 text-sm"
                    placeholder={t('toolbox.graph.importance')}
                    value={quickAddForm.importance}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, importance: Number(e.target.value) })
                    }
                  />
                </div>
              )}

              {quickAddType === 'WorldRule' && (
                <>
                  <input
                    className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                    placeholder={t('toolbox.graph.ruleType')}
                    value={quickAddForm.ruleType}
                    onChange={(e) => setQuickAddForm({ ...quickAddForm, ruleType: e.target.value })}
                  />
                  <input
                    className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                    placeholder={t('toolbox.graph.constraints')}
                    value={quickAddForm.constraints}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, constraints: e.target.value })
                    }
                  />
                  <input
                    className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                    placeholder={t('toolbox.graph.examples')}
                    value={quickAddForm.examples}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, examples: e.target.value })
                    }
                  />
                </>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-pearl-line text-ink-muted"
                onClick={() => setQuickAddOpen(false)}
              >
                {t('common.cancel')}
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-atelier-teal text-white"
                onClick={handleQuickAddSubmit}
              >
                {t('toolbox.graph.create')}
              </button>
            </div>
          </div>
        </div>
      )}

      {storyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-ink">{t('toolbox.graph.newStory')}</h3>
              <button
                onClick={() => setStoryModalOpen(false)}
                className="text-ink-muted hover:text-ink"
              >
                {t('toolbox.close')}
              </button>
            </div>

            <div className="space-y-3">
              <input
                className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                placeholder={t('toolbox.graph.storyName')}
                value={storyForm.name}
                onChange={(e) => setStoryForm({ ...storyForm, name: e.target.value })}
              />
              <textarea
                className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                placeholder={t('toolbox.graph.storyDesc')}
                rows={3}
                value={storyForm.description}
                onChange={(e) => setStoryForm({ ...storyForm, description: e.target.value })}
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  className="rounded-lg border border-pearl-line px-3 py-2 text-sm"
                  placeholder={t('toolbox.graph.genreOptional')}
                  value={storyForm.genre}
                  onChange={(e) => setStoryForm({ ...storyForm, genre: e.target.value })}
                />
                <select
                  className="rounded-lg border border-pearl-line px-3 py-2 text-sm"
                  value={storyForm.status}
                  onChange={(e) => setStoryForm({ ...storyForm, status: e.target.value })}
                >
                  <option value="active">{t('toolbox.graph.storyStatus.active')}</option>
                  <option value="paused">{t('toolbox.graph.storyStatus.paused')}</option>
                  <option value="archived">{t('toolbox.graph.storyStatus.archived')}</option>
                </select>
              </div>
              <input
                className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                placeholder={t('toolbox.graph.tagsPh')}
                value={storyForm.tags}
                onChange={(e) => setStoryForm({ ...storyForm, tags: e.target.value })}
              />
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-pearl-line text-ink-muted"
                onClick={() => setStoryModalOpen(false)}
              >
                {t('common.cancel')}
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-atelier-teal text-white"
                onClick={handleCreateStory}
              >
                {t('toolbox.graph.create')}
              </button>
            </div>
          </div>
        </div>
      )}

      {relationshipModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-ink">{t('toolbox.graph.createRelation')}</h3>
              <button
                onClick={() => setRelationshipModalOpen(false)}
                className="text-ink-muted hover:text-ink"
              >
                {t('toolbox.close')}
              </button>
            </div>

            <div className="space-y-3">
              <select
                className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                value={relationshipForm.sourceId}
                onChange={(e) => setRelationshipForm({ ...relationshipForm, sourceId: e.target.value })}
              >
                <option value="">{t('toolbox.graph.selectSource')}</option>
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.properties?.name || node.properties?.title || node.id} ({node.type})
                  </option>
                ))}
              </select>

              <select
                className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                value={relationshipForm.targetId}
                onChange={(e) => setRelationshipForm({ ...relationshipForm, targetId: e.target.value })}
              >
                <option value="">{t('toolbox.graph.selectTarget')}</option>
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.properties?.name || node.properties?.title || node.id} ({node.type})
                  </option>
                ))}
              </select>

              <select
                className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                value={relationshipForm.relationType}
                onChange={(e) => setRelationshipForm({ ...relationshipForm, relationType: e.target.value })}
              >
                {(relationTypeOptions.length > 0 ? relationTypeOptions : [
                  { value: 'SOCIAL_BOND', label: 'SOCIAL_BOND' },
                  { value: 'INFLUENCES', label: 'INFLUENCES' },
                ] as any).map((item: any) => (
                  <option key={item.value} value={item.value}>
                    {item.label || item.value}
                  </option>
                ))}
              </select>

              <textarea
                className="w-full rounded-lg border border-pearl-line px-3 py-2 text-sm"
                placeholder={t('toolbox.graph.relationDesc')}
                rows={2}
                value={relationshipForm.description}
                onChange={(e) => setRelationshipForm({ ...relationshipForm, description: e.target.value })}
              />
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-pearl-line text-ink-muted"
                onClick={() => setRelationshipModalOpen(false)}
              >
                {t('common.cancel')}
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-atelier-teal text-white"
                onClick={handleCreateRelationship}
              >
                {t('toolbox.graph.create')}
              </button>
            </div>
          </div>
        </div>
      )}

      {extractModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-ink">{t('toolbox.graph.autoExtractTitle')}</h3>
              <button
                onClick={() => setExtractModalOpen(false)}
                className="text-ink-muted hover:text-ink"
              >
                {t('toolbox.close')}
              </button>
            </div>

            <div className="space-y-3">
              <textarea
                className={`w-full rounded-lg border border-pearl-line px-3 py-2 text-sm ${
                  extractFile ? 'bg-pearl-soft text-ink-faint' : ''
                }`}
                placeholder={t('toolbox.graph.pasteScript')}
                rows={10}
                value={extractForm.content}
                disabled={!!extractFile}
                onChange={(e) => setExtractForm({ ...extractForm, content: e.target.value })}
              />
              {extractFile && (
                <div className="text-xs text-amber-600">
                  {t('toolbox.graph.fileSelected')}
                </div>
              )}
              <div className="flex items-center gap-3">
                <input
                  key={fileInputKey}
                  type="file"
                  accept=".txt,.md,.json"
                  onChange={(e) => {
                    const file = e.target.files ? e.target.files[0] : null;
                    setExtractFile(file);
                    if (file) {
                      setExtractForm({ ...extractForm, content: '' });
                    }
                  }}
                  className="text-sm"
                />
                {extractFile && (
                  <div className="flex items-center gap-2 text-xs text-ink-muted">
                    <span>{t('toolbox.graph.fileSelectedName')}{extractFile.name}</span>
                    <button
                      className="text-xs text-ink-muted underline"
                      onClick={() => {
                        setExtractFile(null);
                        setFileInputKey((prev) => prev + 1);
                      }}
                    >
                      {t('toolbox.graph.clearFile')}
                    </button>
                  </div>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  className="rounded-lg border border-pearl-line px-3 py-2 text-sm"
                  placeholder={t('toolbox.graph.chunkSize')}
                  value={extractForm.chunkSize}
                  onChange={(e) =>
                    setExtractForm({ ...extractForm, chunkSize: Number(e.target.value) || 4000 })
                  }
                />
                <input
                  type="number"
                  className="rounded-lg border border-pearl-line px-3 py-2 text-sm"
                  placeholder={t('toolbox.graph.overlap')}
                  value={extractForm.overlap}
                  onChange={(e) =>
                    setExtractForm({ ...extractForm, overlap: Number(e.target.value) || 200 })
                  }
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-pearl-line text-ink-muted"
                onClick={() => setExtractModalOpen(false)}
              >
                {t('common.cancel')}
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-atelier-teal text-white"
                onClick={handleExtractPreview}
              >
                {t('toolbox.graph.previewExtract')}
              </button>
            </div>
          </div>
        </div>
      )}

      {previewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-4xl rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-ink">{t('toolbox.graph.extractPreview')}</h3>
                <p className="text-xs text-ink-muted mt-1">
                  {t('toolbox.graph.previewHint')}
                </p>
              </div>
              <button
                onClick={() => setPreviewModalOpen(false)}
                className="text-ink-muted hover:text-ink"
              >
                {t('toolbox.close')}
              </button>
            </div>

            {dependencyNotice && (
              <div className="mb-3 text-xs text-amber-600">{dependencyNotice}</div>
            )}

            <div className="grid grid-cols-2 gap-4 max-h-[60vh] overflow-y-auto">
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-ink mb-2">{t('toolbox.graph.highConfidence')}</h4>
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs font-medium text-ink-muted mb-1">{t('toolbox.graph.nodes')}</div>
                      <div className="space-y-2">
                        {previewPayload.high.nodes.map((item, idx) => (
                          <label key={`high-node-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.high.nodes.includes(idx)}
                              onChange={() => togglePreviewSelection('high', 'nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.name}</span> ({item.type})
                              {item.confidence !== undefined ? ` · ${t('toolbox.graph.confidence')} ${item.confidence}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.high.nodes.length === 0 && (
                          <div className="text-xs text-ink-muted">{t('toolbox.graph.noCandidateNodes')}</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-ink-muted mb-1">{t('toolbox.graph.plotNodes')}</div>
                      <div className="space-y-2">
                        {previewPayload.high.plot_nodes.map((item, idx) => (
                          <label key={`high-plot-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.high.plot_nodes.includes(idx)}
                              onChange={() => togglePreviewSelection('high', 'plot_nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.title}</span>
                              {item.confidence !== undefined ? ` · ${t('toolbox.graph.confidence')} ${item.confidence}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.high.plot_nodes.length === 0 && (
                          <div className="text-xs text-ink-muted">{t('toolbox.graph.noCandidatePlot')}</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-ink-muted mb-1">{t('toolbox.graph.relations')}</div>
                      <div className="space-y-2">
                        {previewPayload.high.relationships.map((item, idx) => (
                          <label key={`high-rel-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.high.relationships.includes(idx)}
                              onChange={() => togglePreviewSelection('high', 'relationships', idx)}
                            />
                            <span>
                              <span className="font-medium">
                                {item.source_name || item.source} → {item.target_name || item.target}
                              </span>{' '}
                              ({item.type})
                              {item.confidence !== undefined ? ` · ${t('toolbox.graph.confidence')} ${item.confidence}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.high.relationships.length === 0 && (
                          <div className="text-xs text-ink-muted">{t('toolbox.graph.noCandidateRelations')}</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-ink mb-2">{t('toolbox.graph.lowConfidence')}</h4>
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs font-medium text-ink-muted mb-1">{t('toolbox.graph.nodes')}</div>
                      <div className="space-y-2">
                        {previewPayload.low.nodes.map((item, idx) => (
                          <label key={`low-node-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.low.nodes.includes(idx)}
                              onChange={() => togglePreviewSelection('low', 'nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.name}</span> ({item.type}) - {t('toolbox.graph.confidence')} {item.confidence}
                              {item.reason ? ` · ${item.reason}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.low.nodes.length === 0 && (
                          <div className="text-xs text-ink-muted">{t('toolbox.graph.noPendingNodes')}</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-ink-muted mb-1">{t('toolbox.graph.plotNodes')}</div>
                      <div className="space-y-2">
                        {previewPayload.low.plot_nodes.map((item, idx) => (
                          <label key={`low-plot-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.low.plot_nodes.includes(idx)}
                              onChange={() => togglePreviewSelection('low', 'plot_nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.title}</span> - {t('toolbox.graph.confidence')} {item.confidence}
                              {item.reason ? ` · ${item.reason}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.low.plot_nodes.length === 0 && (
                          <div className="text-xs text-ink-muted">{t('toolbox.graph.noPendingPlot')}</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-ink-muted mb-1">{t('toolbox.graph.relations')}</div>
                      <div className="space-y-2">
                        {previewPayload.low.relationships.map((item, idx) => (
                          <label key={`low-rel-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.low.relationships.includes(idx)}
                              onChange={() => togglePreviewSelection('low', 'relationships', idx)}
                            />
                            <span>
                              <span className="font-medium">
                                {item.source} → {item.target}
                              </span>{' '}
                              ({item.type}) - {t('toolbox.graph.confidence')} {item.confidence}
                              {item.reason ? ` · ${item.reason}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.low.relationships.length === 0 && (
                          <div className="text-xs text-ink-muted">{t('toolbox.graph.noPendingRelations')}</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {previewPayload.validation_issues.length > 0 && (
              <div className="mt-4 text-xs text-amber-600">
                {t('toolbox.graph.validationHint')}{previewPayload.validation_issues.join('；')}
              </div>
            )}

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-pearl-line text-ink-muted"
                onClick={() => setPreviewModalOpen(false)}
              >
                {t('common.cancel')}
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg border border-pearl-line text-ink"
                onClick={handleSaveToReviewQueue}
                disabled={previewPayload.low.nodes.length + previewPayload.low.plot_nodes.length + previewPayload.low.relationships.length === 0}
              >
                {t('toolbox.graph.addToReview')}
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-atelier-teal text-white"
                onClick={handleSubmitPreview}
              >
                {t('toolbox.graph.confirmCommit')}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

/**
 * 工作区面板组件
显示 AI 生成的最终成果（剧本、大纲、思维导图、JSON 报告等）
 */

import { useWorkspaceStore, WorkspaceViewType, Note } from '@/store/workspaceStore';
import { useChatStore } from '@/store/chatStore';
import { useAgentStore } from '@/store/agentStore';
import {
  FileText,
  Network,
  Code,
  BookOpen,
  FileJson,
  Save,
  Copy,
  Download,
  Undo,
  Redo,
  Maximize2,
  Minimize2,
  CheckSquare,
  Square,
  Layers,
  ChevronDown,
  ChevronUp,
  Link2,
  Search,
  Download as DownloadIcon
} from 'lucide-react';
import { useState, useEffect, useMemo } from 'react';
import { clsx } from 'clsx';
import { useI18n, translate } from '@/i18n';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';

// 视图类型配置
const VIEW_TYPE_CONFIG: Record<
  WorkspaceViewType,
  { icon: any; label: string; color: string }
> = {
  document: { icon: FileText, label: 'studio.viewType.document', color: 'blue' },
  mindmap: { icon: Network, label: 'studio.viewType.mindmap', color: 'green' },
  json: { icon: FileJson, label: 'studio.viewType.json', color: 'purple' },
  outline: { icon: BookOpen, label: 'studio.viewType.outline', color: 'orange' },
  script: { icon: FileText, label: 'studio.viewType.script', color: 'red' },
  evaluation: { icon: Code, label: 'studio.viewType.evaluation', color: 'cyan' },
  notes: { icon: Layers, label: 'studio.viewType.notes', color: 'indigo' },
};

export default function WorkspacePanel() {
  const { t } = useI18n();
  const {
    currentContent,
    viewMode,
    isDirty,
    canUndo,
    canRedo,
    notes,
    notesGroupedByAction,
    isLoadingNotes,
    toggleNoteSelection,
    exportNotes,
    exportSelectedNotes,
    createNoteFromContent,
    updateNotesSelectionBulk
  } = useWorkspaceStore();
  const { messages } = useChatStore();
  const { activeAgent, agents } = useAgentStore();

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedActionFilter, setSelectedActionFilter] = useState<string | null>(null);
  const [activeTocId, setActiveTocId] = useState<string | null>(null);
  const [tocCollapsed, setTocCollapsed] = useState(false);
  const [noteSaveHint, setNoteSaveHint] = useState<string | null>(null);

  // 加载Notes
  useEffect(() => {
    const userId = localStorage.getItem('userId') || 'default_user';
    const sessionId = localStorage.getItem('sessionId') || 'default_session';
    useWorkspaceStore.getState().loadNotes(userId, sessionId);
  }, []);

  // 获取最新的 AI 输出内容
  const activeAgentInfo = agents.find((agent) => agent.id === activeAgent);

  useEffect(() => {
    if (messages.length === 0) return;
    // 查找最新完成的 AI 消息作为工作区内容
    const latestAIMessage = [...messages]
      .reverse()
      .find((m) => m.role === 'assistant' && m.status === 'complete' && !!m.content);

    if (!latestAIMessage) return;

    const nextId = `msg_${latestAIMessage.id}`;
    if (currentContent?.id === nextId && currentContent.content === latestAIMessage.content) {
      return;
    }

    useWorkspaceStore.getState().setContent({
      id: nextId,
      type: 'document',
      title: `${activeAgentInfo?.displayName || activeAgent} ${t('studio.generatedResult')}`,
      content: latestAIMessage.content,
      metadata: {
        agentId: activeAgent,
        agentName: activeAgentInfo?.displayName,
        timestamp: latestAIMessage.timestamp || new Date().toISOString(),
      },
    });
  }, [messages, currentContent, activeAgent, activeAgentInfo]);


  const handleSave = async () => {
    await useWorkspaceStore.getState().saveContent();
  };

  const handleCopy = async () => {
    await useWorkspaceStore.getState().copyContent();
  };

  const handleExport = async () => {
    await useWorkspaceStore.getState().exportContent('md');
  };

  const handleSaveAsNote = async () => {
    if (!currentContent) return;
    const noteId = await createNoteFromContent(currentContent);
    if (noteId) {
      const created = useWorkspaceStore.getState().notes.find((n) => n.id === noteId);
      if (created) {
        await useWorkspaceStore.getState().updateNoteSelection(created, true);
      }
      setNoteSaveHint(t('studio.savedAsNote'));
      setTimeout(() => setNoteSaveHint(null), 2000);
    }
  };

  const handleUndo = () => {
    useWorkspaceStore.getState().undo();
  };

  const handleRedo = () => {
    useWorkspaceStore.getState().redo();
  };

  const handleViewChange = (newView: WorkspaceViewType) => {
    useWorkspaceStore.getState().setViewMode(newView);
  };

  const contentStats = currentContent
    ? {
        chars: currentContent.content.length,
        sections: Math.max(1, Math.ceil(currentContent.content.length / 500)),
      }
    : null;
  const contentToc = currentContent ? generateToc(currentContent.content) : [];

  useEffect(() => {
    if (!currentContent || contentToc.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => (a.boundingClientRect.top > b.boundingClientRect.top ? 1 : -1));
        if (visible.length > 0) {
          setActiveTocId(visible[0].target.id);
        }
      },
      { root: null, rootMargin: '0px 0px -70% 0px', threshold: 0.1 }
    );

    contentToc.forEach((item) => {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [currentContent, contentToc]);

  return (
    <div
      className={clsx(
        'flex h-full min-w-0 flex-col bg-transparent',
        isFullscreen && 'fixed inset-0 z-50 w-full bg-pearl-soft'
      )}
    >
      {/* 顶部工具栏 — 压缩高度 */}
      <div className="flex items-center justify-between gap-2 px-3 py-1.5 border-b border-pearl-line/80 bg-pearl-card/70 backdrop-blur-xl">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center gap-0.5 bg-pearl-soft/90 rounded-lg border border-pearl-line p-0.5">
            {(['document', 'notes'] as WorkspaceViewType[]).map((mode) => {
              const modeConfig = VIEW_TYPE_CONFIG[mode];
              const ModeIcon = modeConfig.icon;
              const isActive = viewMode === mode;
              return (
                <button
                  key={mode}
                  onClick={() => handleViewChange(mode)}
                  className={clsx(
                    'flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-all',
                    isActive
                      ? 'bg-atelier-teal text-white shadow-atelier'
                      : 'text-ink-muted hover:bg-pearl-card hover:text-atelier-teal'
                  )}
                >
                  <ModeIcon className="w-3 h-3" />
                  <span>{t(modeConfig.label)}</span>
                </button>
              );
            })}
          </div>

          {currentContent && (
            <h2 className="text-[11px] font-semibold text-ink truncate max-w-[200px] hidden md:block">
              {currentContent.title}
              {isDirty && <span className="text-atelier-gold ml-1">•</span>}
            </h2>
          )}
        </div>

        <div className="flex items-center gap-0.5">
          <button
            onClick={handleUndo}
            disabled={!canUndo}
            className={clsx(
              'p-1.5 rounded-lg transition-colors',
              canUndo ? 'hover:bg-atelier-teal-soft text-ink-muted' : 'text-ink-faint/40 cursor-not-allowed'
            )}
            title={t('studio.undo')}
          >
            <Undo className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleRedo}
            disabled={!canRedo}
            className={clsx(
              'p-1.5 rounded-lg transition-colors',
              canRedo ? 'hover:bg-atelier-teal-soft text-ink-muted' : 'text-ink-faint/40 cursor-not-allowed'
            )}
            title={t('studio.redo')}
          >
            <Redo className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleSave}
            className={clsx(
              'flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-semibold transition-all',
              isDirty
                ? 'bg-atelier-teal text-white shadow-atelier hover:bg-atelier-teal-deep'
                : 'bg-pearl-soft text-ink-muted hover:bg-atelier-teal-soft hover:text-atelier-teal border border-pearl-line'
            )}
            title={t('common.save')}
          >
            <Save className="w-3 h-3" />
            <span className="hidden sm:inline">{t('common.save')}</span>
          </button>

          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg hover:bg-atelier-teal-soft text-ink-muted transition-colors"
            title={t('studio.copy')}
          >
            <Copy className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleExport}
            className="p-1.5 rounded-lg hover:bg-atelier-teal-soft text-ink-muted transition-colors"
            title={t('studio.export')}
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-lg hover:bg-atelier-teal-soft text-ink-muted transition-colors"
            title={isFullscreen ? t('studio.exitFullscreen') : t('studio.fullscreen')}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-auto scrollbar p-3 sm:p-5">
        {viewMode === 'notes' ? (
          <NotesView
            notes={notes}
            notesGroupedByAction={notesGroupedByAction}
            isLoadingNotes={isLoadingNotes}
            onToggleSelection={toggleNoteSelection}
            onExport={exportNotes}
            onExportSelected={exportSelectedNotes}
            onBulkSelect={updateNotesSelectionBulk}
            selectedActionFilter={selectedActionFilter}
            onActionFilterChange={setSelectedActionFilter}
          />
        ) : !currentContent ? (
          <div className="h-full min-h-[280px] flex flex-col items-center justify-center px-4">
            <div className="relative w-full max-w-md text-center animate-fade-in py-8">
              <div className="mx-auto w-12 h-12 rounded-2xl bg-gradient-to-br from-atelier-teal to-atelier-teal-mid text-white flex items-center justify-center shadow-atelier mb-3">
                <FileText className="w-5 h-5" />
              </div>
              <p className="font-display text-lg font-semibold text-ink">{t('studio.awaitingResult')}</p>
              <p className="text-[12px] mt-2 text-ink-muted leading-relaxed max-w-xs mx-auto">
                {t('studio.awaitingResultHint')}
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-1.5">
                {[t('studio.awaitingTags.bios'), t('studio.awaitingTags.outline'), t('studio.awaitingTags.plot'), t('studio.awaitingTags.eval')].map((tag) => (
                  <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full border border-pearl-line text-ink-muted">
                    {tag}
                  </span>
                ))}
              </div>
              {notes.length > 0 && (
                <button
                  onClick={() => handleViewChange('notes')}
                  className="btn btn-secondary btn-sm mt-4"
                >
                  {t('studio.viewNotes', { count: notes.length })}
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto">
            <div className="mb-3 rounded-xl border border-pearl-line bg-pearl-card/90 px-3 py-2.5 shadow-atelier backdrop-blur">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-[10px] uppercase tracking-wide text-ink-faint mb-0.5">{t('studio.resultMarkdown')}</div>
                  <h2 className="font-display text-base font-semibold text-ink truncate">
                    {currentContent.title}
                  </h2>
                  <div className="text-[10px] text-ink-faint mt-0.5">
                    {currentContent.metadata?.agentName || activeAgentInfo?.displayName || activeAgent}
                    {currentContent.metadata?.timestamp && (
                      <>
                        <span className="mx-1.5">·</span>
                        <span>
                          {new Date(currentContent.metadata.timestamp).toLocaleString('zh-CN')}
                        </span>
                      </>
                    )}
                    {contentStats && (
                      <>
                        <span className="mx-1.5">·</span>
                        <span>{t('studio.charCount', { count: contentStats.chars })}</span>
                      </>
                    )}
                    {noteSaveHint && (
                      <>
                        <span className="mx-1.5">·</span>
                        <span className="text-emerald-600">{noteSaveHint}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={handleSaveAsNote}
                    className="px-2 py-1 text-[11px] rounded-md border border-pearl-line text-ink-muted hover:bg-pearl-soft"
                  >
                    Note
                  </button>
                  <button
                    onClick={handleCopy}
                    className="px-2 py-1 text-[11px] rounded-md border border-pearl-line text-ink-muted hover:bg-pearl-soft"
                  >
                    {t('studio.copy')}
                  </button>
                  <button
                    onClick={handleExport}
                    className="px-2 py-1 text-[11px] rounded-md bg-ink text-white hover:bg-ink/90"
                  >
                    {t('studio.export')}
                  </button>
                </div>
              </div>
            </div>
            {contentToc.length > 0 && (
              <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-medium text-gray-700">{t('studio.toc')}</div>
                  <button
                    onClick={() => setTocCollapsed((prev) => !prev)}
                    className="text-xs text-gray-500 hover:text-gray-700"
                  >
                    {tocCollapsed ? t('dashboard.expand') : t('studio.collapse')}
                  </button>
                </div>
                {!tocCollapsed && (
                  <div className="flex flex-wrap gap-2">
                    {contentToc.slice(0, 20).map((item) => (
                      <button
                        key={item.id}
                        onClick={() => {
                          const element = document.getElementById(item.id);
                          element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }}
                        className={clsx(
                          'px-3 py-1.5 text-xs rounded-full border transition-colors',
                          activeTocId === item.id
                            ? 'border-gray-900 text-gray-900 bg-gray-100'
                            : item.level === 1
                            ? 'border-gray-300 text-gray-700'
                            : item.level === 2
                            ? 'border-blue-200 text-blue-600'
                            : 'border-indigo-200 text-indigo-600'
                        )}
                      >
                        {item.text}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="bg-white rounded-xl border border-pearl-line p-4 sm:p-5 shadow-sm">
              <div
                className={clsx(
                  'markdown prose prose-sm prose-neutral max-w-none text-ink',
                  '[&_p]:my-2 [&_ul]:my-2 [&_ol]:my-2 [&_li]:my-0.5',
                  '[&_h1]:text-xl [&_h2]:text-lg [&_h3]:text-base',
                  '[&_pre]:text-[12px] [&_code]:text-[12.5px] leading-relaxed text-[13px]'
                )}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                  {currentContent.content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 底部状态栏 */}
      {currentContent && (
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span>{currentContent.metadata?.agentName}</span>
            <span>•</span>
            <span>
              {currentContent.metadata?.timestamp
                ? new Date(
                    currentContent.metadata.timestamp
                  ).toLocaleString('zh-CN')
                : ''}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span>{t('studio.charTotal', { count: currentContent.content.length })}</span>
            <span>•</span>
            <span>{t('studio.sections', { count: Math.ceil(currentContent.content.length / 500) })}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// 简单的 Markdown 渲染函数
// 实际使用时建议安装 react-markdown 等库
function renderMarkdown(content: string): string {
  // 简单的 Markdown 转换
  let html = content
    // 转义 HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // 标题（带锚点）
    .replace(/^### (.*$)/gim, (_, text) => `<h3 id="${slugify(text)}">${text}</h3>`)
    .replace(/^## (.*$)/gim, (_, text) => `<h2 id="${slugify(text)}">${text}</h2>`)
    .replace(/^# (.*$)/gim, (_, text) => `<h1 id="${slugify(text)}">${text}</h1>`)
    // 粗体
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // 斜体
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // 代码块
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 rounded">$1</code>')
    // 链接
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline">$1</a>')
    // 无序列表
    .replace(/^\* (.*$)/gim, '<li>$1</li>')
    // 有序列表
    .replace(/^\d+\. (.*$)/gim, '<li>$1</li>')
    // 换行
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br />');

  return `<p>${html}</p>`;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\u4e00-\u9fa5\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

interface TocItem {
  id: string;
  text: string;
  level: 1 | 2 | 3;
}

function generateToc(content: string): TocItem[] {
  const items: TocItem[] = [];
  content.split('\n').forEach((line) => {
    const match = /^(#{1,3})\s+(.*)$/.exec(line.trim());
    if (!match) return;
    const level = match[1].length as 1 | 2 | 3;
    const text = match[2].trim();
    if (!text) return;
    items.push({ id: slugify(text), text, level });
  });
  return items;
}

// Notes视图组件
interface NotesViewProps {
  notes: Note[];
  notesGroupedByAction: Record<string, Note[]>;
  isLoadingNotes: boolean;
  onToggleSelection: (note: Note) => Promise<void>;
  onExport: (format: string) => Promise<void>;
  onExportSelected: () => Promise<void>;
  onBulkSelect: (notes: Note[], selected: boolean) => Promise<void>;
  selectedActionFilter: string | null;
  onActionFilterChange: (action: string | null) => void;
}

function NotesView({
  notes,
  notesGroupedByAction,
  isLoadingNotes,
  onToggleSelection,
  onExport,
  onExportSelected,
  onBulkSelect,
  selectedActionFilter,
  onActionFilterChange,
}: NotesViewProps) {
  const { t } = useI18n();
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [showSelectedOnly, setShowSelectedOnly] = useState(false);
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest');
  const [bulkComment, setBulkComment] = useState('');
  const [phaseFilter, setPhaseFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showRagOnly, setShowRagOnly] = useState(false);
  const [ragSourceFilter, setRagSourceFilter] = useState('');
  const [showRagGraph, setShowRagGraph] = useState(false);
  const [filterNameInput, setFilterNameInput] = useState('');
  const [savedFilters, setSavedFilters] = useState<
    { name: string; filters: { search: string; phase: string; category: string; selectedOnly: boolean; ragOnly: boolean; ragSource?: string } }[]
  >([]);

  const toggleGroup = (action: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(action)) {
        next.delete(action);
      } else {
        next.add(action);
      }
      return next;
    });
  };

  const displayedNotes = selectedActionFilter
    ? notes.filter((n) => n.action === selectedActionFilter)
    : notes;

  const getPhase = (note: Note): string => {
    const metaPhase = note.metadata?.phase;
    if (metaPhase) return metaPhase;
    const outputTag = note.metadata?.output_tag;
    const mapping: Record<string, string> = {
      drama_planning: 'planning',
      drama_creation: 'creation',
      drama_evaluation: 'evaluation',
      novel_screening: 'evaluation',
      story_analysis: 'analysis',
      character_development: 'character',
      plot_development: 'story',
      series_analysis: 'analysis',
    };
    if (outputTag && mapping[outputTag]) return mapping[outputTag];
    return '';
  };

  const getCategory = (note: Note): string => {
    return note.metadata?.category || '';
  };

  const baseNotes = displayedNotes
    .filter((note) => (showSelectedOnly ? note.select_status === 1 : true))
    .filter((note) => (phaseFilter ? getPhase(note) === phaseFilter : true))
    .filter((note) => (categoryFilter ? getCategory(note) === categoryFilter : true))
    .filter((note) => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        note.title?.toLowerCase().includes(query) ||
        note.name?.toLowerCase().includes(query) ||
        note.context?.toLowerCase().includes(query) ||
        note.action?.toLowerCase().includes(query)
      );
    });

  const ragSourceCounts = baseNotes.reduce((acc, note) => {
    const ragTrace = note.metadata?.rag_trace;
    if (Array.isArray(ragTrace)) {
      ragTrace.forEach((item: any) => {
        const source = item?.source || 'unknown';
        acc[source] = (acc[source] || 0) + 1;
      });
    }
    return acc;
  }, {} as Record<string, number>);

  const ragGraphNodes = useMemo(() => {
    const entries = Object.entries(ragSourceCounts);
    if (entries.length === 0) return [];
    const max = Math.max(...entries.map(([, count]) => count));
    return entries.map(([source, count], idx) => ({
      id: source,
      count,
      radius: Math.max(10, Math.round((count / (max || 1)) * 24)),
      x: 60 + (idx % 5) * 80,
      y: 50 + Math.floor(idx / 5) * 80,
    }));
  }, [ragSourceCounts]);

  const filteredNotes = baseNotes
    .filter((note) => {
      if (!showRagOnly) return true;
      const ragTrace = note.metadata?.rag_trace;
      return Array.isArray(ragTrace) && ragTrace.length > 0;
    })
    .filter((note) => {
      if (!ragSourceFilter) return true;
      const ragTrace = note.metadata?.rag_trace;
      return Array.isArray(ragTrace) && ragTrace.some((item: any) => (item?.source || 'unknown') === ragSourceFilter);
    })
    .sort((a, b) => {
      const aTime = new Date(a.created_at).getTime();
      const bTime = new Date(b.created_at).getTime();
      return sortOrder === 'newest' ? bTime - aTime : aTime - bTime;
    });

  const groupedFilteredNotes = Object.entries(notesGroupedByAction).reduce(
    (acc, [action, groupNotes]) => {
      const groupFiltered = groupNotes
        .filter((note) => filteredNotes.some((n) => n.id === note.id));
      if (groupFiltered.length > 0) {
        acc[action] = groupFiltered;
      }
      return acc;
    },
    {} as Record<string, Note[]>
  );
  const selectedCount = filteredNotes.filter((note) => note.select_status === 1).length;
  const phaseOptions = Array.from(
    new Set(notes.map((note) => getPhase(note)).filter(Boolean))
  );
  const categoryOptions = Array.from(
    new Set(notes.map((note) => getCategory(note)).filter(Boolean))
  );

  useEffect(() => {
    try {
      const raw = localStorage.getItem('notes_saved_filters');
      if (raw) {
        setSavedFilters(JSON.parse(raw));
      }
    } catch {
      setSavedFilters([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('notes_saved_filters', JSON.stringify(savedFilters));
  }, [savedFilters]);

  const handleClearFilters = () => {
    setSearchQuery('');
    setPhaseFilter('');
    setCategoryFilter('');
    setShowSelectedOnly(false);
    setShowRagOnly(false);
    setRagSourceFilter('');
  };

  const handleSaveFilters = () => {
    const name = filterNameInput.trim();
    if (!name) return;
    const payload = {
      search: searchQuery,
      phase: phaseFilter,
      category: categoryFilter,
      selectedOnly: showSelectedOnly,
      ragOnly: showRagOnly,
      ragSource: ragSourceFilter,
    };
    setSavedFilters((prev) => [
      { name, filters: payload },
      ...prev.filter((item) => item.name !== name),
    ]);
    setFilterNameInput('');
  };

  const handleApplySaved = (name: string) => {
    const saved = savedFilters.find((item) => item.name === name);
    if (!saved) return;
    setSearchQuery(saved.filters.search);
    setPhaseFilter(saved.filters.phase);
    setCategoryFilter(saved.filters.category);
    setShowSelectedOnly(saved.filters.selectedOnly);
    setShowRagOnly(Boolean(saved.filters.ragOnly));
    setRagSourceFilter(saved.filters.ragSource || '');
  };

  const handleDeleteSaved = (name: string) => {
    setSavedFilters((prev) => prev.filter((item) => item.name !== name));
  };

  // 获取Agent显示名称
  const getActionDisplayName = (action: string): string => {
    const names: Record<string, string> = {
      'character_profile_generator': '人物小传',
      'character_relationship_analyzer': '人物关系',
      'plot_points_analyzer': '情节点分析',
      'story_summary_generator': '故事大纲',
      'major_plot_points_agent': '大情节点',
      'detailed_plot_points_agent': '详细情节点',
      'script_evaluation': '剧本评估',
      'ip_evaluation': 'IP评估',
      'story_evaluation': '故事评估',
    };
    return names[action] || action;
  };

  if (isLoadingNotes) {
    return (
      <div className="h-full flex items-center justify-center gap-3 text-ink-faint">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-pearl-line border-t-studio-teal" />
        <p>{t('studio.notes.loading')}</p>
      </div>
    );
  }

  if (notes.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-ink-faint text-center px-6">
        <div className="w-16 h-16 rounded-2xl bg-pearl-soft flex items-center justify-center mb-4">
          <Layers className="w-8 h-8 text-ink-faint" />
        </div>
        <p className="font-display font-semibold text-ink text-base">{t('studio.notes.empty')}</p>
        <p className="text-xs mt-2 leading-relaxed max-w-xs">
          {t('studio.notes.emptyHint')}
        </p>
      </div>
    );
  }

  if (filteredNotes.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-ink-faint text-center px-6">
        <div className="w-16 h-16 rounded-2xl bg-pearl-soft flex items-center justify-center mb-4">
          <Search className="w-8 h-8 text-ink-faint" />
        </div>
        <p className="font-display font-semibold text-ink text-base">{t('studio.notes.noMatch')}</p>
        <p className="text-xs mt-2">{t('studio.notes.noMatchHint')}</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 过滤器和工具栏 */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2">
            <input
              value={filterNameInput}
              onChange={(e) => setFilterNameInput(e.target.value)}
              placeholder={t('studio.notes.filterName')}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={handleSaveFilters}
              disabled={!filterNameInput.trim()}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              {t('studio.notes.saveFilter')}
            </button>
            <select
              value=""
              onChange={(e) => {
                if (e.target.value) {
                  handleApplySaved(e.target.value);
                }
              }}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">{t('studio.notes.applyFilter')}</option>
              {savedFilters.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
            {savedFilters.length > 0 && (
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) {
                    handleDeleteSaved(e.target.value);
                  }
                }}
                className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">{t('studio.notes.deleteFilter')}</option>
                {savedFilters.map((item) => (
                  <option key={item.name} value={item.name}>
                    {item.name}
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={handleClearFilters}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              {t('studio.notes.clear')}
            </button>
          </div>
          <select
            value={selectedActionFilter || ''}
            onChange={(e) => onActionFilterChange(e.target.value || null)}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">{t('studio.notes.allTypes')}</option>
            {Object.keys(notesGroupedByAction).map((action) => (
              <option key={action} value={action}>
                {getActionDisplayName(action)} ({notesGroupedByAction[action].length})
              </option>
            ))}
          </select>
          <select
            value={phaseFilter}
            onChange={(e) => setPhaseFilter(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">{t('studio.notes.allPhases')}</option>
            {phaseOptions.map((phase) => (
              <option key={phase} value={phase}>
                {phase}
              </option>
            ))}
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">{t('studio.notes.allCategories')}</option>
            {categoryOptions.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-faint" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('studio.notes.searchPlaceholder')}
              className="pl-8 pr-3 py-1.5 text-sm border border-pearl-line rounded-lg bg-white focus:outline-none focus:border-studio-teal focus:ring-1 focus:ring-studio-teal"
            />
          </div>
          <button
            onClick={() => setShowSelectedOnly((prev) => !prev)}
            className={clsx(
              'px-3 py-1.5 text-sm rounded-lg border transition-colors',
              showSelectedOnly
                ? 'border-indigo-500 text-indigo-600 bg-indigo-50'
                : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            )}
          >
            {t('studio.notes.selectedOnly')}
          </button>
          <button
            onClick={() => setShowRagOnly((prev) => !prev)}
            className={clsx(
              'px-3 py-1.5 text-sm rounded-lg border transition-colors',
              showRagOnly
                ? 'border-blue-500 text-blue-600 bg-blue-50'
                : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            )}
          >
            {t('studio.notes.ragOnly')}
          </button>
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as 'newest' | 'oldest')}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="newest">{t('studio.notes.newest')}</option>
            <option value="oldest">{t('studio.notes.oldest')}</option>
          </select>
          <button
            onClick={() => onBulkSelect(filteredNotes, true)}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
          >
            {t('studio.notes.selectAll')}
          </button>
          <button
            onClick={() => onBulkSelect(filteredNotes, false)}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
          >
            {t('studio.notes.deselectAll')}
          </button>
          <div className="flex items-center gap-2">
            <input
              value={bulkComment}
              onChange={(e) => setBulkComment(e.target.value)}
              placeholder={t('studio.notes.bulkComment')}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={async () => {
                const selected = filteredNotes.filter((note) => note.select_status === 1);
                if (selected.length === 0 || !bulkComment.trim()) return;
                await Promise.all(
                  selected.map((note) =>
                    useWorkspaceStore.getState().updateNoteSelection(note, true, bulkComment.trim())
                  )
                );
                setBulkComment('');
              }}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              {t('studio.notes.addComment')}
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onExportSelected} className="btn btn-primary btn-sm">
            <DownloadIcon className="w-3.5 h-3.5" />
            {t('studio.notes.exportSelected', { count: selectedCount })}
          </button>
          <button onClick={() => onExport('txt')} className="btn btn-secondary btn-sm">
            {t('studio.notes.exportTxt')}
          </button>
          <button onClick={() => onExport('md')} className="btn btn-secondary btn-sm">
            {t('studio.notes.exportMd')}
          </button>
        </div>
      </div>

      {Object.keys(ragSourceCounts).length > 0 && (
        <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium text-gray-700">{t('studio.notes.sources')}</div>
            <button
              onClick={() => setShowRagGraph((prev) => !prev)}
              className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              {showRagGraph ? t('studio.notes.hideGraph') : t('studio.notes.showGraph')}
            </button>
          </div>
          {showRagGraph && ragGraphNodes.length > 0 && (
            <div className="mb-3 overflow-auto">
              <svg width="480" height={Math.max(140, Math.ceil(ragGraphNodes.length / 5) * 80)}>
                {ragGraphNodes.map((node) => (
                  <g
                    key={node.id}
                    onClick={() => {
                      setShowRagOnly(true);
                      setRagSourceFilter(node.id);
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <circle cx={node.x} cy={node.y} r={node.radius} fill="#3B82F6" opacity="0.2" />
                    <circle cx={node.x} cy={node.y} r={Math.max(8, node.radius - 5)} fill="#3B82F6" opacity="0.6" />
                    <text x={node.x} y={node.y + node.radius + 10} textAnchor="middle" fontSize="9" fill="#4B5563">
                      {node.id}
                    </text>
                  </g>
                ))}
              </svg>
            </div>
          )}
          <div className="space-y-2 mb-3">
            {Object.entries(ragSourceCounts).map(([source, count]) => {
              const total = Object.values(ragSourceCounts).reduce((sum, v) => sum + v, 0) || 1;
              const percent = Math.round((count / total) * 100);
              return (
                <div key={source}>
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>{source}</span>
                    <span>{percent}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded">
                    <div className="h-1.5 rounded bg-blue-500" style={{ width: `${percent}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(ragSourceCounts).map(([source, count]) => (
              <button
                key={source}
                onClick={() => {
                  setShowRagOnly(true);
                  setRagSourceFilter(source);
                }}
                className={clsx(
                  'px-3 py-1.5 text-xs rounded-full border transition-colors',
                  ragSourceFilter === source
                    ? 'border-blue-500 text-blue-700 bg-blue-50'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                )}
              >
                {source} ({count})
              </button>
            ))}
            {ragSourceFilter && (
              <button
                onClick={() => setRagSourceFilter('')}
                className="px-3 py-1.5 text-xs rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50"
              >
                {t('studio.notes.clearSource')}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Notes列表 */}
      <div className="flex-1 overflow-y-auto space-y-3">
        {Object.entries(groupedFilteredNotes).map(([action, groupNotes]) => (
          <div key={action} className="rounded-xl border border-pearl-line overflow-hidden bg-white">
            {/* 分组标题 */}
            <button
              onClick={() => toggleGroup(action)}
              className="w-full flex items-center justify-between px-4 py-2.5 bg-pearl-soft/60 hover:bg-pearl-soft transition-colors"
            >
              <div className="flex items-center gap-2">
                <ChevronDown
                  className={clsx(
                    'w-4 h-4 text-ink-faint transition-transform',
                    expandedGroups.has(action) || 'transform -rotate-90'
                  )}
                />
                <span className="font-display font-semibold text-ink text-sm">
                  {getActionDisplayName(action)}
                </span>
                <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-pearl-soft text-ink-faint tabular-nums">
                  {groupNotes.length}
                </span>
              </div>
            </button>

            {/* 分组内容 */}
            {expandedGroups.has(action) && (
              <div className="p-3 space-y-2.5">
                {groupNotes.map((note) => (
                  <NoteCard
                    key={note.id}
                    note={note}
                    onToggleSelection={onToggleSelection}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Note卡片组件
interface NoteCardProps {
  note: Note;
  onToggleSelection: (note: Note) => Promise<void>;
}

const PHASE_META: Record<string, { label: string; cls: string }> = {
  planning: { label: 'studio.phase.planning', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  creation: { label: 'studio.phase.creation', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  evaluation: { label: 'studio.phase.evaluation', cls: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  analysis: { label: 'studio.phase.analysis', cls: 'bg-violet-50 text-violet-700 border-violet-200' },
  character: { label: 'studio.phase.character', cls: 'bg-pink-50 text-pink-700 border-pink-200' },
  story: { label: 'studio.phase.story', cls: 'bg-sky-50 text-sky-700 border-sky-200' },
};

function formatNoteDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const diff = Date.now() - d.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return translate('dashboard.time.justNow');
  if (minutes < 60) return translate('studio.minutesAgo', undefined, { m: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return translate('dashboard.time.hoursAgo', undefined, { h: hours });
  const days = Math.floor(hours / 24);
  if (days < 7) return translate('dashboard.time.daysAgo', undefined, { d: days });
  return d.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function NoteCard({ note, onToggleSelection }: NoteCardProps) {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);
  const mindMap = note.metadata?.mind_map;
  const mindMapSvg = mindMap?.svg;
  const selected = note.select_status === 1;
  const phase = note.metadata?.phase || '';
  const phaseMeta = PHASE_META[phase];
  const category = note.metadata?.category || '';
  const ragTrace = Array.isArray(note.metadata?.rag_trace) ? note.metadata.rag_trace : [];
  const ragCount = ragTrace.length;

  return (
    <div
      className={clsx(
        'rounded-xl border p-4 transition-all duration-200',
        selected
          ? 'border-studio-teal bg-studio-teal-soft/30 shadow-sm'
          : 'border-pearl-line bg-white hover:border-studio-teal/30 hover:shadow-sm'
      )}
    >
      <div className="flex items-start gap-3">
        {/* 选择复选框 */}
        <button
          onClick={() => onToggleSelection(note)}
          className="mt-0.5 shrink-0 text-ink-faint hover:text-studio-teal transition-colors"
          title={selected ? t('studio.notes.deselect') : t('studio.notes.select')}
        >
          {selected ? (
            <CheckSquare className="w-5 h-5 text-studio-teal" />
          ) : (
            <Square className="w-5 h-5" />
          )}
        </button>

        {/* Note内容 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap min-w-0">
              <h4 className="font-display font-semibold text-ink text-sm leading-snug truncate">
                {note.title || note.name || t('studio.unnamed')}
              </h4>
              {selected && (
                <span className="px-2 py-0.5 text-[10px] rounded-full bg-studio-teal text-white">
                  {t('studio.notes.selected')}
                </span>
              )}
            </div>
            <span className="text-[10px] text-ink-faint shrink-0 tabular-nums">
              {formatNoteDate(note.created_at)}
            </span>
          </div>

          {(phase || category) && (
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {phaseMeta && (
                <span className={clsx('px-2 py-0.5 text-[10px] rounded-full border', phaseMeta.cls)}>
                  {t(phaseMeta.label)}
                </span>
              )}
              {category && (
                <span className="px-2 py-0.5 text-[10px] rounded-full border border-pearl-line bg-pearl-soft text-ink-muted">
                  {category}
                </span>
              )}
            </div>
          )}

          {!isExpanded ? (
            <p className="text-xs text-ink-muted line-clamp-2 mt-2 leading-relaxed">
              {note.context}
            </p>
          ) : (
            <div className="text-sm text-ink whitespace-pre-wrap mt-2 leading-relaxed">
              {note.context}
            </div>
          )}

          {mindMapSvg && (
            <div className="mt-3 rounded-lg border border-pearl-line bg-pearl-soft/40 p-2.5">
              {mindMap?.title && (
                <div className="text-xs font-medium text-ink-muted mb-1.5">{mindMap.title}</div>
              )}
              <div className="max-h-[180px] overflow-hidden">
                <div
                  className="origin-top-left scale-[0.85]"
                  dangerouslySetInnerHTML={{ __html: mindMapSvg }}
                />
              </div>
            </div>
          )}

          {note.user_comment && (
            <div className="mt-2.5 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 leading-relaxed">
              <span className="font-medium">{t('studio.notes.comment')}</span>
              {note.user_comment}
            </div>
          )}

          <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-pearl-line/70">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="inline-flex items-center gap-1 text-xs text-studio-teal hover:underline"
            >
              {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {isExpanded ? t('dashboard.collapse') : t('studio.notes.expandFull')}
            </button>
            {ragCount > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] text-ink-faint">
                <Link2 className="w-3 h-3" />
                {t('studio.notes.refCount', { count: ragCount })}
              </span>
            )}
          </div>

          {isExpanded && ragCount > 0 && (
            <div className="mt-2 space-y-1.5">
              {ragTrace.map((item: any, idx: number) => (
                <div
                  key={idx}
                  className="px-2.5 py-1.5 bg-pearl-soft/60 rounded-lg text-[10px] text-ink-muted"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-ink truncate">{item.source}</span>
                    {item.filename && (item.project_id || note.metadata?.project_id) && (
                      <a
                        href={`/files?project_id=${item.project_id || note.metadata?.project_id}&search=${encodeURIComponent(item.filename)}`}
                        className="text-studio-teal hover:underline shrink-0"
                      >
                        {t('studio.notes.openFile')}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

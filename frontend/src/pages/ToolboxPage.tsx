/**
 * 工具箱索引 — 次要能力收纳
 */

import { Link, useParams, Navigate } from 'react-router-dom';
import {
  Search,
  ScanText,
  HardDrive,
  Network,
  BookOpen,
  Workflow,
  BarChart3,
  Coins,
  Bot,
  FileText,
  Clapperboard,
  Wrench,
  ClipboardCheck,
  Eye,
} from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { useI18n } from '@/i18n';
import BaiduSearchPage from '@/pages/BaiduSearchPage';
import OCRPage from '@/pages/OCRPage';
import FileSystemPage from '@/pages/FileSystemPage';
import GraphVisualizationPage from '@/pages/GraphVisualizationPage';
import GraphReviewCenterPage from '@/pages/GraphReviewCenterPage';
import KnowledgeBasePage from '@/pages/KnowledgeBasePage';
import WorkflowMonitorPage from '@/pages/WorkflowMonitorPage';
import StatisticsPage from '@/pages/StatisticsPage';
import TokenUsagePage from '@/pages/TokenUsagePage';

const TOOLS = [
  {
    id: 'agent-tools',
    labelKey: 'toolbox.tools.agentTools.label',
    descKey: 'toolbox.tools.agentTools.desc',
    icon: Wrench,
    path: '/toolbox/agent-tools',
  },
  {
    id: 'agent-infra',
    labelKey: 'toolbox.tools.agentInfra.label',
    descKey: 'toolbox.tools.agentInfra.desc',
    icon: Bot,
    path: '/toolbox/agent-infra',
  },
  {
    id: 'context-preview',
    labelKey: 'toolbox.tools.contextPreview.label',
    descKey: 'toolbox.tools.contextPreview.desc',
    icon: Eye,
    path: '/toolbox/context-preview',
  },
  { id: 'baidu', labelKey: 'toolbox.tools.baidu.label', descKey: 'toolbox.tools.baidu.desc', icon: Search, path: '/toolbox/baidu' },
  { id: 'ocr', labelKey: 'toolbox.tools.ocr.label', descKey: 'toolbox.tools.ocr.desc', icon: ScanText, path: '/toolbox/ocr' },
  { id: 'files', labelKey: 'toolbox.tools.files.label', descKey: 'toolbox.tools.files.desc', icon: HardDrive, path: '/toolbox/files' },
  { id: 'graph', labelKey: 'toolbox.tools.graph.label', descKey: 'toolbox.tools.graph.desc', icon: Network, path: '/toolbox/graph' },
  {
    id: 'graph-review',
    labelKey: 'toolbox.tools.graphReview.label',
    descKey: 'toolbox.tools.graphReview.desc',
    icon: ClipboardCheck,
    path: '/toolbox/graph-review',
  },
  { id: 'knowledge', labelKey: 'toolbox.tools.knowledge.label', descKey: 'toolbox.tools.knowledge.desc', icon: BookOpen, path: '/toolbox/knowledge' },
  { id: 'workflow', labelKey: 'toolbox.tools.workflow.label', descKey: 'toolbox.tools.workflow.desc', icon: Workflow, path: '/toolbox/workflow' },
  { id: 'statistics', labelKey: 'toolbox.tools.statistics.label', descKey: 'toolbox.tools.statistics.desc', icon: BarChart3, path: '/toolbox/statistics' },
  { id: 'tokens', labelKey: 'toolbox.tools.tokens.label', descKey: 'toolbox.tools.tokens.desc', icon: Coins, path: '/toolbox/tokens' },
  { id: 'notes', labelKey: 'toolbox.tools.notes.label', descKey: 'toolbox.tools.notes.desc', icon: FileText, path: '/toolbox/notes' },
];

const EMBEDDED: Record<string, React.ComponentType> = {
  baidu: BaiduSearchPage,
  ocr: OCRPage,
  files: FileSystemPage,
  graph: GraphVisualizationPage,
  'graph-review': GraphReviewCenterPage,
  knowledge: KnowledgeBasePage,
  workflow: WorkflowMonitorPage,
  statistics: StatisticsPage,
  tokens: TokenUsagePage,
};

export default function ToolboxPage() {
  const { toolId } = useParams<{ toolId?: string }>();
  const { t } = useI18n();

  if (toolId && EMBEDDED[toolId]) {
    const Comp = EMBEDDED[toolId];
    // 各工具页已统一使用 AppShell，直接渲染即可
    return <Comp />;
  }

  if (toolId === 'notes') {
    return <Navigate to="/notes" replace />;
  }

  if (toolId) {
    return <Navigate to="/toolbox" replace />;
  }

  return (
    <AppShell title={t('toolbox.title')} subtitle={t('toolbox.subtitle')}>
      <div className="p-4 sm:p-8 max-w-5xl mx-auto">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {TOOLS.map((tool, i) => (
            <Link
              key={tool.id}
              to={tool.path}
              className="card card-hover p-5 animate-stagger-in"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <div className="w-10 h-10 rounded-xl bg-studio-teal-soft text-studio-teal flex items-center justify-center mb-3">
                <tool.icon className="w-5 h-5" />
              </div>
              <h3 className="font-display font-semibold text-ink">{t(tool.labelKey)}</h3>
              <p className="text-sm text-ink-muted mt-1">{t(tool.descKey)}</p>
            </Link>
          ))}
          <Link to="/experts" className="card card-hover p-5">
            <div className="w-10 h-10 rounded-xl bg-studio-amber-soft text-studio-amber flex items-center justify-center mb-3">
              <Bot className="w-5 h-5" />
            </div>
            <h3 className="font-display font-semibold text-ink">{t('toolbox.tools.experts.label')}</h3>
            <p className="text-sm text-ink-muted mt-1">{t('toolbox.tools.experts.desc')}</p>
          </Link>
          <Link to="/studio" className="card card-hover p-5">
            <div className="w-10 h-10 rounded-xl bg-paper-cool text-ink-muted flex items-center justify-center mb-3">
              <Clapperboard className="w-5 h-5" />
            </div>
            <h3 className="font-display font-semibold text-ink">{t('toolbox.tools.studio.label')}</h3>
            <p className="text-sm text-ink-muted mt-1">{t('toolbox.tools.studio.desc')}</p>
          </Link>
        </div>
      </div>
    </AppShell>
  );
}

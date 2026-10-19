/**
 * App 根组件 — AI 短剧连载工作室
 */

import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAgentStore } from '@/store/agentStore';
import { useUIStore } from '@/store/uiStore';
import { useSettingsStore } from '@/store/settingsStore';
import { getAgents } from '@/services/agentService';
import { NotificationContainer } from '@/components/notification';
import { GlobalSearch } from '@/components/search';
import { PrivateRoute, PublicRoute } from '@/components/auth';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import UnauthorizedPage from '@/pages/UnauthorizedPage';
import DashboardPage from '@/pages/DashboardPage';
import DramasPage from '@/pages/DramasPage';
import DramaDetailPage from '@/pages/DramaDetailPage';
import EpisodeEditorPage from '@/pages/EpisodeEditorPage';
import MemoryCenterPage from '@/pages/MemoryCenterPage';
import SkillsPage from '@/pages/SkillsPage';
import ToolboxPage from '@/pages/ToolboxPage';
import AgentToolsPage from '@/pages/AgentToolsPage';
import AgentInfraPage from '@/pages/AgentInfraPage';
import ContextPreviewPage from '@/pages/ContextPreviewPage';
import SettingsPage from '@/pages/SettingsPage';
import AgentsHubPage from '@/pages/AgentsHubPage';
import StudioPage from '@/pages/StudioPage';
import MainPage from '@/pages/MainPage';
import AdminPage from '@/pages/AdminPage';
import NotesPage from '@/pages/NotesPage';
import NovelScreeningPage from '@/pages/NovelScreeningPage';
import QualityControlPage from '@/pages/QualityControlPage';
import ReleaseManagementPage from '@/pages/ReleaseManagementPage';
import PipelineManagementPage from '@/pages/PipelineManagementPage';
import GraphReviewCenterPage from '@/pages/GraphReviewCenterPage';
import EvolutionPage from '@/pages/EvolutionPage';
import FeedbackPage from '@/pages/FeedbackPage';
import ABTestPage from '@/pages/ABTestPage';
import ToolsDemoPage from '@/pages/ToolsDemoPage';

function App() {
  const { setAgents } = useAgentStore();
  const { searchOpen, setSearchOpen } = useUIStore();
  const language = useSettingsStore((s) => s.language);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    getAgents()
      .then((list) =>
        setAgents(
          (list || []).filter(
            (a: { id?: string; category?: string }) =>
              a.category !== 'utility' &&
              ![
                'websearch',
                'knowledge',
                'file_reference',
                'document_generator',
                'output_formatter',
                'series_info',
                'series_name_extractor',
                'text_splitter',
                'text_truncator',
              ].includes(a.id || '')
          )
        )
      )
      .catch(console.error);
  }, [setAgents]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setSearchOpen(!searchOpen);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [searchOpen, setSearchOpen]);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <NotificationContainer />
        <GlobalSearch isOpen={searchOpen} onClose={() => setSearchOpen(false)} />

        <Routes>
          <Route
            path="/login"
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <RegisterPage />
              </PublicRoute>
            }
          />
          <Route path="/unauthorized" element={<UnauthorizedPage />} />

          <Route
            path="/"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <DashboardPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/dramas"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <DramasPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/dramas/:dramaId"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <DramaDetailPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/dramas/:dramaId/episodes/:episodeNumber"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <EpisodeEditorPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/studio"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <StudioPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/studio/:dramaId"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <StudioPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/experts"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <AgentsHubPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/memory"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <MemoryCenterPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/memory-settings"
            element={<Navigate to="/memory" replace />}
          />
          <Route
            path="/memory-management"
            element={<Navigate to="/memory" replace />}
          />
          <Route
            path="/skills"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <SkillsPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/toolbox"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ToolboxPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/toolbox/agent-tools"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <AgentToolsPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/toolbox/agent-infra"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <AgentInfraPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/toolbox/context-preview"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ContextPreviewPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/toolbox/:toolId"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ToolboxPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <SettingsPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route path="/agents" element={<Navigate to="/experts" replace />} />
          <Route path="/workspace" element={<Navigate to="/studio" replace />} />
          <Route
            path="/chat"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <MainPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 兼容旧路径 → 工具箱 */}
          <Route path="/baidu" element={<Navigate to="/toolbox/baidu" replace />} />
          <Route path="/ocr" element={<Navigate to="/toolbox/ocr" replace />} />
          <Route path="/files" element={<Navigate to="/toolbox/files" replace />} />
          <Route path="/graph" element={<Navigate to="/toolbox/graph" replace />} />
          <Route path="/knowledge" element={<Navigate to="/toolbox/knowledge" replace />} />
          <Route path="/workflow" element={<Navigate to="/toolbox/workflow" replace />} />
          <Route path="/statistics" element={<Navigate to="/toolbox/statistics" replace />} />
          <Route path="/tokens" element={<Navigate to="/toolbox/tokens" replace />} />
          <Route path="/projects" element={<Navigate to="/dramas" replace />} />
          <Route path="/projects/:projectId" element={<Navigate to="/dramas" replace />} />
          <Route path="/tools" element={<Navigate to="/toolbox" replace />} />

          {/* 原孤儿页正式挂载（实验室） */}
          <Route
            path="/notes"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <NotesPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/novel-screening"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <NovelScreeningPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/quality"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <QualityControlPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/release"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ReleaseManagementPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/pipelines"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <PipelineManagementPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route path="/graph/review" element={<Navigate to="/toolbox/graph-review" replace />} />
          <Route
            path="/evolution"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <EvolutionPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/feedback"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <FeedbackPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/abtest"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ABTestPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/tools-demo"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ToolsDemoPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <PrivateRoute requireAdmin>
                <ErrorBoundary>
                  <AdminPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;

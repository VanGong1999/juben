/**
 * 项目管理页面
 * 展示所有项目，支持创建、编辑、删除项目
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import { useProjectStore } from '@/store/projectStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  FolderPlus,
  Search,
  Grid3x3,
  List,
  Plus,
  MoreVertical,
  Edit,
  Trash2,
  FolderOpen,
  Calendar,
  FileText,
  Tag
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { enUS, zhCN } from 'date-fns/locale';
import type { Project, ProjectStatus } from '@/types';
import { useI18n } from '@/i18n';

const PHASE_META: Record<string, { className: string }> = {
  planning: { className: 'bg-blue-100 text-blue-700' },
  creation: { className: 'bg-emerald-100 text-emerald-700' },
  evaluation: { className: 'bg-orange-100 text-orange-700' },
  analysis: { className: 'bg-purple-100 text-purple-700' },
  workflow: { className: 'bg-slate-100 text-slate-700' },
  character: { className: 'bg-pink-100 text-pink-700' },
  story: { className: 'bg-indigo-100 text-indigo-700' },
  utility: { className: 'bg-gray-100 text-gray-700' },
};

export default function ProjectsPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const navigate = useNavigate();
  const { t, language } = useI18n();

  const {
    projects,
    isLoading,
    error,
    searchQuery,
    selectedTags,
    currentPage,
    total,
    statusFilter,
    loadProjects,
    createProject,
    deleteProject,
    setSearchQuery,
    setSelectedTags,
    setCurrentPage,
    setStatusFilter,
    clearError
  } = useProjectStore();

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [newProjectTags, setNewProjectTags] = useState<string[]>([]);
  const [phaseFilter, setPhaseFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  useEffect(() => {
    loadProjects();
  }, [currentPage, selectedTags, statusFilter]);

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;

    const project = await createProject({
      name: newProjectName,
      description: newProjectDesc,
      tags: newProjectTags
    });

    if (project) {
      setShowCreateModal(false);
      setNewProjectName('');
      setNewProjectDesc('');
      setNewProjectTags([]);
    }
  };

  const handleDeleteProject = async () => {
    if (!projectToDelete) return;

    await deleteProject(projectToDelete.id);
    setShowDeleteModal(false);
    setProjectToDelete(null);
  };

  const openProject = (project: Project) => {
    navigate(`/projects/${project.id}`);
  };

  const filteredProjects = projects.filter(p => {
    // 搜索过滤
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (!p.name.toLowerCase().includes(query) &&
          !(p.description || '').toLowerCase().includes(query) &&
          !(p.tags || []).some(t => t.toLowerCase().includes(query))) {
        return false;
      }
    }

    // 状态过滤
    if (statusFilter !== 'all' && p.status !== statusFilter) {
      return false;
    }

    // 阶段过滤
    if (phaseFilter) {
      if (!p.tags?.includes(`phase:${phaseFilter}`)) {
        return false;
      }
    }

    // 分类过滤
    if (categoryFilter) {
      if (!p.tags?.includes(`category:${categoryFilter}`)) {
        return false;
      }
    }

    return true;
  });

  const getStatusColor = (status: ProjectStatus) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-700';
      case 'completed': return 'bg-blue-100 text-blue-700';
      case 'archived': return 'bg-gray-100 text-gray-700';
      case 'deleted': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getStatusText = (status: ProjectStatus) => {
    switch (status) {
      case 'active': return t('project.status.active');
      case 'completed': return t('project.status.completed');
      case 'archived': return t('project.status.archived');
      case 'deleted': return t('project.status.deleted');
      default: return status;
    }
  };

  const phaseLabel = (phase: string) => {
    const labels: Record<string, string> = {
      planning: t('project.phase.planning'),
      creation: t('project.phase.creation'),
      evaluation: t('project.phase.evaluation'),
      analysis: t('project.phase.analysis'),
      workflow: t('project.phase.workflow'),
      character: t('project.phase.character'),
      story: t('project.phase.story'),
      utility: t('project.phase.utility'),
    };
    return labels[phase] || phase;
  };

  const phaseOptions = Array.from(
    new Set(
      projects.flatMap((project) =>
        (project.tags || [])
          .filter((tag) => tag.startsWith('phase:'))
          .map((tag) => tag.replace('phase:', ''))
      )
    )
  );

  const categoryOptions = Array.from(
    new Set(
      projects.flatMap((project) =>
        (project.tags || [])
          .filter((tag) => tag.startsWith('category:'))
          .map((tag) => tag.replace('category:', ''))
      )
    )
  );

  const renderPhaseBadges = (tags: string[]) => {
    const phases = (tags || [])
      .filter((tag) => tag.startsWith('phase:'))
      .map((tag) => tag.replace('phase:', ''));
    if (phases.length === 0) return null;
    return (
      <div className="flex flex-wrap gap-1 mt-2">
        {phases.map((phase) => {
          const meta = PHASE_META[phase] || { className: 'bg-gray-100 text-gray-700' };
          return (
            <span
              key={phase}
              className={`inline-flex px-2 py-0.5 text-[11px] rounded ${meta.className}`}
            >
              {phaseLabel(phase)}
            </span>
          );
        })}
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-white">
      <MobileMenu />
      <Sidebar />

      <div
        className={`flex flex-col flex-1 transition-all duration-300 ${
          !sidebarOpen ? 'ml-0' : sidebarCollapsed ? 'ml-16' : 'ml-80'
        }`}
      >
        <Header />
        <StatusBar />

        <div className="flex flex-col flex-1 overflow-hidden">
          {/* 页面头部 */}
          <div className="border-b border-gray-200 bg-white">
            <div className="max-w-7xl mx-auto px-6 py-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                    <FolderOpen className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">{t('studio.header.nav.projects')}</h1>
                    <p className="text-sm text-gray-500 mt-1">
                      {t('project.pageSubtitle', { total })}
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setShowCreateModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-all hover-scale"
                >
                  <Plus className="w-4 h-4" />
                  <span className="font-medium">{t('project.newProject')}</span>
                </button>
              </div>

              {/* 工具栏 */}
              <div className="flex items-center gap-4">
                {/* 搜索框 */}
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder={t('project.searchPlaceholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black text-sm"
                  />
                </div>

                {/* 状态过滤 */}
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as ProjectStatus | 'all')}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-black"
                >
                  <option value="all">{t('project.allStatuses')}</option>
                  <option value="active">{t('project.status.active')}</option>
                  <option value="completed">{t('project.status.completed')}</option>
                  <option value="archived">{t('project.status.archived')}</option>
                  <option value="deleted">{t('project.status.deleted')}</option>
                </select>

                {/* 阶段过滤 */}
                <select
                  value={phaseFilter}
                  onChange={(e) => setPhaseFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-black"
                >
                  <option value="">{t('project.allPhases')}</option>
                  {phaseOptions.map((phase) => (
                    <option key={phase} value={phase}>
                      {phase}
                    </option>
                  ))}
                </select>

                {/* 分类过滤 */}
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-black"
                >
                  <option value="">{t('project.allCategories')}</option>
                  {categoryOptions.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>

                {/* 视图切换 */}
                <div className="flex items-center gap-1 border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 hover:bg-gray-100 transition-colors ${
                      viewMode === 'grid' ? 'bg-gray-100' : ''
                    }`}
                  >
                    <Grid3x3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 hover:bg-gray-100 transition-colors ${
                      viewMode === 'list' ? 'bg-gray-100' : ''
                    }`}
                  >
                    <List className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* 项目列表 */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">
              {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                  <button onClick={clearError} className="ml-2 underline hover:text-red-900">
                    {t('project.close')}
                  </button>
                </div>
              )}

              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div className="w-12 h-12 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-500">{t('studio.loading')}</p>
                  </div>
                </div>
              ) : filteredProjects.length === 0 ? (
                <div className="text-center py-16">
                  <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <FolderPlus className="w-10 h-10 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {searchQuery || statusFilter !== 'all' ? t('project.noMatch') : t('empty.noProjects')}
                  </h3>
                  <p className="text-gray-500 mb-6">
                    {searchQuery || statusFilter !== 'all'
                      ? t('project.noMatchHint')
                      : t('project.createFirstProject')}
                  </p>
                  {!searchQuery && statusFilter === 'all' && (
                    <button
                      onClick={() => setShowCreateModal(true)}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-all"
                    >
                      <Plus className="w-4 h-4" />
                      {t('empty.createProject')}
                    </button>
                  )}
                </div>
              ) : viewMode === 'grid' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredProjects.map((project) => (
                    <ProjectCard
                      key={project.id}
                      project={project}
                      onClick={() => openProject(project)}
                      onEdit={(e) => {
                        e.stopPropagation();
                        navigate(`/projects/${project.id}?edit=1`);
                      }}
                      onDelete={(e) => {
                        e.stopPropagation();
                        setProjectToDelete(project);
                        setShowDeleteModal(true);
                      }}
                      getStatusColor={getStatusColor}
                      getStatusText={getStatusText}
                      renderPhaseBadges={renderPhaseBadges}
                    />
                  ))}
                </div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('project.table.name')}</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('project.table.description')}</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('project.table.status')}</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('project.table.fileCount')}</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('project.table.updatedAt')}</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t('project.table.actions')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {filteredProjects.map((project) => (
                        <tr
                          key={project.id}
                          onClick={() => openProject(project)}
                          className="hover:bg-gray-50 cursor-pointer transition-colors"
                        >
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
                                <FolderOpen className="w-5 h-5 text-white" />
                              </div>
                              <div>
                                <div className="font-medium text-gray-900">{project.name}</div>
                                <div className="text-xs text-gray-500">{project.tags.slice(0, 2).map(t => (
                                  <span key={t} className="inline-flex items-center gap-1 mr-2">
                                    <Tag className="w-3 h-3" /> {t}
                                  </span>
                                ))}</div>
                                {renderPhaseBadges(project.tags || [])}
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600 line-clamp-2">
                            {project.description || '-'}
                          </td>
                          <td className="px-6 py-4">
                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
                              {getStatusText(project.status)}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                              <FileText className="w-4 h-4" />
                              {project.file_count}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-4 h-4" />
                              {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true, locale: language === 'zh' ? zhCN : enUS })}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setProjectToDelete(project);
                                setShowDeleteModal(true);
                              }}
                              className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
                            >
                              <Trash2 className="w-4 h-4 text-gray-600" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* 分页 */}
              {total > 20 && (
                <div className="mt-6 flex items-center justify-between border-t border-gray-200 pt-4">
                  <p className="text-sm text-gray-500">
                    {t('project.showRange', {
                      from: Math.min((currentPage - 1) * 20 + 1, filteredProjects.length),
                      to: Math.min(currentPage * 20, filteredProjects.length),
                      total,
                    })}
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1 border border-gray-200 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                    >
                      {t('project.prevPage')}
                    </button>
                    <button
                      onClick={() => setCurrentPage(Math.min(Math.ceil(total / 20), currentPage + 1))}
                      disabled={currentPage >= Math.ceil(total / 20)}
                      className="px-3 py-1 border border-gray-200 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                    >
                      {t('project.nextPage')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />

      {/* 创建项目对话框 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">{t('project.createNewProject')}</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('project.projectNameRequired')}</label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder={t('project.inputProjectName')}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('project.projectDesc')}</label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder={t('project.descPlaceholder')}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">{t('project.tags')}</label>
                <input
                  type="text"
                  value={newProjectTags.join(', ')}
                  onChange={(e) => setNewProjectTags(e.target.value.split(',').map(t => t.trim()).filter(Boolean))}
                  placeholder={t('project.inputTags')}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black"
                />
              </div>

              <div className="flex gap-3 pt-4 border-t border-gray-200">
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewProjectName('');
                    setNewProjectDesc('');
                    setNewProjectTags([]);
                  }}
                  className="flex-1 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  {t('common.cancel')}
                </button>
                <button
                  onClick={handleCreateProject}
                  disabled={!newProjectName.trim() || isLoading}
                  className="flex-1 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? t('project.creating') : t('project.create')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 删除确认对话框 */}
      {showDeleteModal && projectToDelete && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-2">{t('project.deleteProject')}</h2>
            <p className="text-gray-600 mb-6">
              {t('project.deleteProjectConfirm', { name: projectToDelete.name })}
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setProjectToDelete(null);
                }}
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleDeleteProject}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

/**
 * 项目卡片组件
 */
function ProjectCard({
  project,
  onClick,
  onEdit,
  onDelete,
  getStatusColor,
  getStatusText,
  renderPhaseBadges
}: {
  project: Project;
  onClick: () => void;
  onEdit: (e: React.MouseEvent) => void;
  onDelete: (e: React.MouseEvent) => void;
  getStatusColor: (status: ProjectStatus) => string;
  getStatusText: (status: ProjectStatus) => string;
  renderPhaseBadges: (tags: string[]) => React.ReactNode;
}) {
  const { t, language } = useI18n();
  return (
    <div
      onClick={onClick}
      className="group bg-white border border-gray-200 rounded-xl p-5 hover:shadow-lg hover:border-black transition-all cursor-pointer"
    >
      {/* 头部 */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
            <FolderOpen className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 group-hover:text-black transition-colors">
              {project.name}
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              {formatDistanceToNow(new Date(project.created_at), { addSuffix: true, locale: language === 'zh' ? zhCN : enUS })}
            </p>
          </div>
        </div>

        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              // 显示菜单
            }}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <MoreVertical className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>

      {/* 描述 */}
      <p className="text-sm text-gray-600 mb-4 line-clamp-2 min-h-[40px]">
        {project.description || t('project.noDescription')}
      </p>

      {/* 标签 */}
      {project.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {project.tags.slice(0, 3).map(tag => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
            >
              <Tag className="w-3 h-3" />
              {tag}
            </span>
          ))}
          {project.tags.length > 3 && (
            <span className="text-xs text-gray-500">+{project.tags.length - 3}</span>
          )}
        </div>
      )}

      {renderPhaseBadges(project.tags || [])}

      {/* 底部信息 */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <div className="flex items-center gap-1">
            <FileText className="w-4 h-4" />
            <span>{t('project.files', { count: project.file_count })}</span>
          </div>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
            {getStatusText(project.status)}
          </span>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onEdit}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            title={t('project.edit')}
          >
            <Edit className="w-4 h-4 text-gray-500" />
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 hover:bg-red-100 rounded-lg transition-colors"
            title={t('common.delete')}
          >
            <Trash2 className="w-4 h-4 text-red-500" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * 工作流模板管理组件
 */

import React, { useState } from 'react';
import { Plus, Edit, Trash2, Copy, Eye, X } from 'lucide-react';
import { useI18n } from '@/i18n';

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  variables: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowNode {
  id: string;
  type: string;
  name: string;
  config: Record<string, any>;
  position: { x: number; y: number };
}

interface WorkflowTemplateManagerProps {
  isOpen: boolean;
  onClose: () => void;
  templates: WorkflowTemplate[];
  onLoad: (templateId: string) => void;
  onSave: (template: Omit<WorkflowTemplate, 'id' | 'createdAt' | 'updatedAt'>) => Promise<void>;
  onDelete: (templateId: string) => Promise<void>;
}

export const WorkflowTemplateManager: React.FC<WorkflowTemplateManagerProps> = ({
  isOpen,
  onClose,
  templates,
  onLoad,
  onSave,
  onDelete,
}) => {
  const { t, language } = useI18n();
  const [view, setView] = useState<'list' | 'create' | 'edit'>('list');
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  });

  if (!isOpen) return null;

  const handleCreate = () => {
    setView('create');
    setSelectedTemplate(null);
    setFormData({ name: '', description: '' });
  };

  const handleEdit = (template: WorkflowTemplate) => {
    setView('edit');
    setSelectedTemplate(template);
    setFormData({ name: template.name, description: template.description });
  };

  const handleSave = async () => {
    if (!formData.name.trim()) return;

    if (view === 'create') {
      await onSave({
        name: formData.name,
        description: formData.description,
        nodes: [],
        variables: {},
      });
    } else if (view === 'edit' && selectedTemplate) {
      await onSave({
        ...selectedTemplate,
        name: formData.name,
        description: formData.description,
      });
    }

    setView('list');
    setFormData({ name: '', description: '' });
    setSelectedTemplate(null);
  };

  const handleDelete = async (templateId: string) => {
    if (window.confirm(t('chatGraph.workflow.deleteTemplateConfirm'))) {
      await onDelete(templateId);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden mx-4">
        {/* 头部 */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {view === 'list' ? t('chatGraph.workflow.templates') : view === 'create' ? t('chatGraph.workflow.createTemplate') : t('chatGraph.workflow.editTemplate')}
          </h2>
          <button
            onClick={() => {
              onClose();
              setView('list');
              setFormData({ name: '', description: '' });
            }}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-6 overflow-y-auto max-h-[70vh]">
          {view === 'list' && (
            <div className="space-y-4">
              {/* 创建按钮 */}
              <div className="flex justify-end mb-4">
                <button
                  onClick={handleCreate}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  {t('chatGraph.workflow.newTemplate')}
                </button>
              </div>

              {/* 模板列表 */}
              {templates.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <p>{t('chatGraph.workflow.noTemplates')}</p>
                  <p className="text-sm mt-2">{t('chatGraph.workflow.noTemplatesHint')}</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {templates.map((template) => (
                    <div
                      key={template.id}
                      className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 dark:text-white">
                            {template.name}
                          </h3>
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {template.description || t('project.noDescription')}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
                        <span>{t('chatGraph.workflow.nodeCount', { count: template.nodes.length })}</span>
                        <span>{new Date(template.updatedAt).toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US')}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => onLoad(template.id)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                        >
                          <Eye className="w-3 h-3" />
                          {t('workspace.view')}
                        </button>
                        <button
                          onClick={() => handleEdit(template)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                        >
                          <Edit className="w-3 h-3" />
                          {t('project.edit')}
                        </button>
                        <button
                          onClick={() => {
                            const newTemplate = { ...template, id: '', name: `${template.name} ${t('chatGraph.workflow.copySuffix')}` };
                            onSave(newTemplate);
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                        >
                          <Copy className="w-3 h-3" />
                          {t('chatGraph.workflow.duplicate')}
                        </button>
                        <button
                          onClick={() => handleDelete(template.id)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                          {t('common.delete')}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {(view === 'create' || view === 'edit') && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('chatGraph.workflow.templateName')}
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={t('chatGraph.workflow.templateNamePlaceholder')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('ui.description')}
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder={t('chatGraph.workflow.templateDescPlaceholder')}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>

              <div className="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  💡 {t('chatGraph.workflow.templateHint')}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* 底部 */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-between">
          {view !== 'list' && (
            <button
              onClick={() => {
                setView('list');
                setFormData({ name: '', description: '' });
              }}
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg font-medium transition-colors"
            >
              {t('studio.back')}
            </button>
          )}
          {view !== 'list' && (
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setView('list');
                  setFormData({ name: '', description: '' });
                }}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg font-medium transition-colors"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleSave}
                disabled={!formData.name.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('common.save')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

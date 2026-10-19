/**
 * 知识库管理页面
 * 用于管理文档、知识条目和搜索功能
 */

import React, { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import {
  Database,
  Upload,
  Search,
  FileText,
  Trash2,
  Eye,
  Tag,
  TrendingUp,
  Plus,
  FolderOpen,
  BookOpen,
  RefreshCw,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';
import { getKnowledgeCollections, searchKnowledge } from '@/services/extendedApi';

interface KnowledgeDocument {
  id: string;
  title: string;
  content: string;
  category?: string;
  tags?: string[];
  createdAt?: string;
  updatedAt?: string;
  size?: number;
  source?: string;
  relevance?: number;
}

interface KnowledgeCategory {
  name: string;
  description?: string;
  count?: number;
}

export const KnowledgeBasePage: React.FC = () => {
  const { success, error } = useNotificationStore();
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'documents' | 'upload' | 'search' | 'stats'>('documents');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocument | null>(null);
  const [searchResults, setSearchResults] = useState<KnowledgeDocument[]>([]);
  const [categories, setCategories] = useState<KnowledgeCategory[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [localDocuments, setLocalDocuments] = useState<KnowledgeDocument[]>([]);
  const [editingDocumentId, setEditingDocumentId] = useState<string | null>(null);
  const [searchHistory, setSearchHistory] = useState<
    { query: string; timestamp: string; count: number }[]
  >([]);
  const [uploadForm, setUploadForm] = useState({ title: '', content: '', tags: '' });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadMessage, setUploadMessage] = useState('');
  const [stats, setStats] = useState({
    totalDocuments: 0,
    totalCategories: 0,
  });

  useEffect(() => {
    try {
      const raw = localStorage.getItem('knowledge_documents');
      const rawHistory = localStorage.getItem('knowledge_search_history');
      if (raw) {
        const parsed = JSON.parse(raw);
        setLocalDocuments(parsed);
        setDocuments(parsed);
      }
      if (rawHistory) {
        setSearchHistory(JSON.parse(rawHistory));
      }
    } catch {
      setLocalDocuments([]);
    }

    const loadCollections = async () => {
      try {
        const response = await getKnowledgeCollections();
        const collectionList = response.collections || [];
        const mapped = collectionList.map((item) => ({
          name: item.name,
          description: item.info?.description || '',
          count: item.info?.count || item.info?.size || 0,
        }));
        setCategories(mapped);
        setStats({
          totalDocuments: mapped.reduce((acc, item) => acc + (item.count || 0), 0) + localDocuments.length,
          totalCategories: mapped.length,
        });
      } catch (err: any) {
        error(t('toolbox.knowledge.toast.loadFailed'), err?.message || t('toolbox.knowledge.toast.loadFailedDesc'));
      }
    };
    loadCollections();
  }, [localDocuments.length]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      error(t('toolbox.knowledge.toast.searchFailed'), t('toolbox.knowledge.toast.emptyQuery'));
      return;
    }
    try {
      const response = await searchKnowledge(searchQuery.trim(), selectedCategory === 'all' ? undefined : selectedCategory);
      const results = response.search_result?.results || response.search_result?.items || response.search_result || [];
      const mapped: KnowledgeDocument[] = (Array.isArray(results) ? results : []).map((item: any, index: number) => ({
        id: item.id || item.doc_id || `${index}`,
        title: item.title || item.source || `${t('toolbox.knowledge.results')} ${index + 1}`,
        content: item.content || item.text || item.snippet || JSON.stringify(item),
        category: item.collection || selectedCategory,
        source: item.source || item.url,
        size: item.size || item.bytes || item.file_size,
        updatedAt: item.updated_at || item.updatedAt,
        tags: item.tags || [],
        relevance: item.score ?? item.relevance ?? item.similarity,
      }));
      setSearchResults(mapped);
      setActiveTab('search');
      const now = new Date().toISOString();
      const updatedHistory = (() => {
        const existing = searchHistory.find((entry) => entry.query === searchQuery.trim());
        if (existing) {
          return searchHistory.map((entry) =>
            entry.query === searchQuery.trim()
              ? { ...entry, count: entry.count + 1, timestamp: now }
              : entry
          );
        }
        return [{ query: searchQuery.trim(), timestamp: now, count: 1 }, ...searchHistory].slice(0, 20);
      })();
      setSearchHistory(updatedHistory);
      localStorage.setItem('knowledge_search_history', JSON.stringify(updatedHistory));
      success(t('toolbox.knowledge.toast.searchSuccess'), t('toolbox.knowledge.toast.found', { count: mapped.length }));
    } catch (err: any) {
      error(t('toolbox.knowledge.toast.searchFailed'), err?.message || t('toolbox.knowledge.toast.searchFailedDesc'));
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!window.confirm(t('toolbox.knowledge.toast.deleteConfirm'))) return;
    const updated = localDocuments.filter((doc) => doc.id !== docId);
    setLocalDocuments(updated);
    setDocuments(updated);
    localStorage.setItem('knowledge_documents', JSON.stringify(updated));
    success(t('toolbox.knowledge.toast.deleteSuccess'), t('toolbox.knowledge.toast.deleted'));
  };

  const handleViewDocument = (doc: KnowledgeDocument) => {
    setSelectedDocument(doc);
  };

  const handleCreateLocalDoc = () => {
    if (!uploadForm.title.trim() || !uploadForm.content.trim()) {
      error(t('toolbox.knowledge.toast.createFailed'), t('toolbox.knowledge.toast.emptyFields'));
      return;
    }
    const now = new Date().toISOString();
    const doc: KnowledgeDocument = {
      id: editingDocumentId || `local_${Date.now()}`,
      title: uploadForm.title.trim(),
      content: uploadForm.content.trim(),
      category: '本地文档',
      tags: uploadForm.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      createdAt: editingDocumentId
        ? localDocuments.find((doc) => doc.id === editingDocumentId)?.createdAt
        : now,
      updatedAt: now,
    };
    const updated = editingDocumentId
      ? localDocuments.map((item) => (item.id === editingDocumentId ? doc : item))
      : [doc, ...localDocuments];
    setLocalDocuments(updated);
    setDocuments(updated);
    localStorage.setItem('knowledge_documents', JSON.stringify(updated));
    setUploadForm({ title: '', content: '', tags: '' });
    setUploadFile(null);
    setUploadMessage('');
    setEditingDocumentId(null);
    success(
      editingDocumentId ? t('toolbox.knowledge.toast.updateSuccess') : t('toolbox.knowledge.toast.createSuccess'),
      t('toolbox.knowledge.toast.saved')
    );
    setActiveTab('documents');
  };

  const handleUploadFile = (file: File) => {
    const allowed = ['text/plain', 'text/markdown', 'application/json'];
    if (!allowed.includes(file.type) && !file.name.match(/\.(txt|md|markdown|json)$/i)) {
      setUploadMessage(t('toolbox.knowledge.toast.onlyText'));
      return;
    }
    setUploadFile(file);
    setUploadMessage('');
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result || '');
      setUploadForm((prev) => ({
        ...prev,
        title: prev.title || file.name.replace(/\.[^/.]+$/, ''),
        content: text,
      }));
      setUploadMessage(`${t('toolbox.knowledge.toast.loaded')} ${file.name}，${t('toolbox.knowledge.toast.editableAfter')}`);
    };
    reader.onerror = () => {
      setUploadMessage(t('toolbox.knowledge.toast.readFailed'));
    };
    reader.readAsText(file);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === undefined || bytes === null) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatRelevance = (value?: number) => {
    if (value === undefined || value === null) return null;
    if (value <= 1) return `${Math.round(value * 100)}%`;
    if (value <= 100) return `${Math.round(value)}%`;
    return `${Math.round(value)}`;
  };

  const renderDocumentsTab = () => (
    <div className="space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-ink-muted">{t('toolbox.knowledge.stat.totalDocs')}</p>
              <p className="text-2xl font-bold text-ink mt-1">{stats.totalDocuments}</p>
            </div>
            <FileText className="w-8 h-8 text-atelier-teal" />
          </div>
        </div>

        <div className="glass-panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-ink-muted">{t('toolbox.knowledge.stat.categories')}</p>
              <p className="text-2xl font-bold text-ink mt-1">{stats.totalCategories}</p>
            </div>
            <FolderOpen className="w-8 h-8 text-purple-500" />
          </div>
        </div>

        <div className="glass-panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-ink-muted">{t('toolbox.knowledge.stat.localDocs')}</p>
              <p className="text-2xl font-bold text-ink mt-1">{localDocuments.length}</p>
            </div>
            <Database className="w-8 h-8 text-green-500" />
          </div>
        </div>

        <div className="glass-panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-ink-muted">{t('toolbox.knowledge.stat.collections')}</p>
              <p className="text-2xl font-bold text-ink mt-1">{categories.length}</p>
            </div>
            <Search className="w-8 h-8 text-orange-500" />
          </div>
        </div>
      </div>

      {/* 文档列表 */}
      <div className="glass-panel overflow-hidden">
        <div className="px-6 py-4 border-b border-pearl-line flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink">{t('toolbox.knowledge.docList')}</h2>
          <div className="flex items-center gap-3">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-1.5 border border-pearl-line rounded-lg text-sm bg-white/60 focus:outline-none focus:ring-2 focus:ring-atelier-teal/30"
            >
              <option value="all">{t('toolbox.knowledge.allCategories')}</option>
              {localDocuments.length > 0 && (
                <option value="本地文档">{t('toolbox.knowledge.stat.localDocs')} ({localDocuments.length})</option>
              )}
              {categories.map((cat) => (
                <option key={cat.name} value={cat.name}>
                  {cat.name} ({cat.count || 0})
                </option>
              ))}
            </select>
            <button
              onClick={() => setActiveTab('upload')}
              className="btn btn-primary btn-sm"
            >
              <Plus className="w-4 h-4" />
              {t('toolbox.knowledge.tab.upload')}
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-pearl-line">
            <thead className="bg-pearl-soft">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase">{t('toolbox.knowledge.table.title')}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase">{t('toolbox.knowledge.table.category')}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase">{t('toolbox.knowledge.table.tags')}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase">{t('toolbox.knowledge.table.size')}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase">{t('toolbox.knowledge.table.updated')}</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-ink-muted uppercase">{t('toolbox.knowledge.table.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-pearl-line">
              {documents
                .filter((doc) => selectedCategory === 'all' || doc.category === selectedCategory)
                .map((doc) => (
                <tr key={doc.id} className="hover:bg-pearl-soft/60">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-ink-faint" />
                      <div>
                        <div className="text-sm font-medium text-ink">{doc.title}</div>
                        {doc.source && (
                          <div className="text-xs text-ink-muted">{t('toolbox.knowledge.source')}: {doc.source}</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex px-2 py-1 text-xs font-medium bg-atelier-teal-soft text-atelier-teal rounded">
                      {doc.category || t('toolbox.knowledge.unknown')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {(doc.tags || []).slice(0, 2).map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex px-2 py-0.5 text-xs bg-pearl-soft text-ink-muted rounded"
                        >
                          {tag}
                        </span>
                      ))}
                      {(doc.tags || []).length > 2 && (
                        <span className="text-xs text-ink-muted">+{(doc.tags || []).length - 2}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-ink-muted">
                    {doc.size ? formatFileSize(doc.size) : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-ink-muted">
                    {doc.updatedAt ? new Date(doc.updatedAt).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => handleViewDocument(doc)}
                        className="p-1.5 hover:bg-pearl-soft rounded"
                        title={t('toolbox.preview')}
                      >
                        <Eye className="w-4 h-4 text-ink-muted" />
                      </button>
                      {doc.id.startsWith('local_') && (
                        <button
                          onClick={() => handleDeleteDocument(doc.id)}
                          className="p-1.5 hover:bg-red-100 rounded"
                          title={t('common.delete')}
                        >
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 分类统计 */}
      <div className="glass-panel p-6">
        <h3 className="text-lg font-semibold text-ink mb-4">{t('toolbox.knowledge.categoryStats')}</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...(localDocuments.length > 0
            ? [{ name: t('toolbox.knowledge.stat.localDocs'), description: t('toolbox.knowledge.stat.localDocs'), count: localDocuments.length }]
            : []),
            ...categories,
          ].map((cat) => (
            <div key={cat.name} className="border border-pearl-line rounded-lg p-4 hover:shadow-md transition-shadow bg-white/40">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-ink">{cat.name}</h4>
                <span className="text-sm text-ink-muted">{cat.count || 0} {t('toolbox.knowledge.unit')}</span>
              </div>
              <p className="text-sm text-ink-muted">{cat.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderUploadTab = () => (
    <div className="max-w-2xl mx-auto">
      <div className="glass-panel p-6">
        <h2 className="text-lg font-semibold text-ink mb-6">
          {editingDocumentId ? t('toolbox.knowledge.editLocalDoc') : t('toolbox.knowledge.uploadToKb')}
        </h2>

        <div className="space-y-6">
          {/* 本地文档保存 */}
          <div className="border-2 border-dashed border-pearl-line rounded-lg p-8 text-center">
            <Upload className="w-10 h-10 mx-auto mb-4 text-ink-faint" />
            <p className="text-ink-muted mb-2">{t('toolbox.knowledge.dragHint')}</p>
            <p className="text-sm text-ink-muted">{t('toolbox.knowledge.supportFormats')}</p>
            <div className="mt-4">
              <input
                type="file"
                accept=".txt,.md,.markdown,.json,text/plain,text/markdown,application/json"
                onChange={(e) => e.target.files?.[0] && handleUploadFile(e.target.files[0])}
                className="block w-full text-sm text-ink-muted file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-atelier-teal-soft file:text-atelier-teal hover:file:bg-atelier-teal-soft"
              />
            </div>
            {uploadFile && <p className="mt-2 text-xs text-ink-muted">{t('toolbox.graph.fileSelectedName')} {uploadFile.name}</p>}
            {uploadMessage && <p className="mt-3 text-xs text-atelier-teal">{uploadMessage}</p>}
          </div>

          {/* 文档信息 */}
          <div>
            <label className="block text-sm font-medium text-ink mb-2">
              {t('toolbox.knowledge.docTitle')} *
            </label>
            <input
              type="text"
              placeholder={t('toolbox.knowledge.titlePlaceholder')}
              value={uploadForm.title}
              onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
              className="w-full px-3 py-2 border border-pearl-line rounded-lg bg-white/60 focus:outline-none focus:ring-2 focus:ring-atelier-teal/30"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink mb-2">
              {t('toolbox.knowledge.docContent')} *
            </label>
            <textarea
              placeholder={t('toolbox.knowledge.contentPlaceholder')}
              rows={8}
              value={uploadForm.content}
              onChange={(e) => setUploadForm({ ...uploadForm, content: e.target.value })}
              className="w-full px-3 py-2 border border-pearl-line rounded-lg bg-white/60 focus:outline-none focus:ring-2 focus:ring-atelier-teal/30 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink mb-2">
              {t('toolbox.knowledge.tags')}
            </label>
            <input
              type="text"
              placeholder={t('toolbox.knowledge.tagsPlaceholder')}
              value={uploadForm.tags}
              onChange={(e) => setUploadForm({ ...uploadForm, tags: e.target.value })}
              className="w-full px-3 py-2 border border-pearl-line rounded-lg bg-white/60 focus:outline-none focus:ring-2 focus:ring-atelier-teal/30"
            />
          </div>

          <div className="bg-atelier-teal-soft rounded-lg p-4">
            <div className="flex items-start gap-3">
              <BookOpen className="w-5 h-5 text-atelier-teal mt-0.5" />
              <div className="text-sm text-ink-muted">
                <p className="font-medium mb-1">{t('toolbox.knowledge.smartUnderstand')}</p>
                <p>{t('toolbox.knowledge.smartUnderstandDesc')}</p>
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t border-pearl-line">
            <button
              onClick={() => {
                setEditingDocumentId(null);
                setActiveTab('documents');
              }}
              className="flex-1 btn btn-secondary"
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={handleCreateLocalDoc}
              className="flex-1 btn btn-primary"
            >
              {editingDocumentId ? t('toolbox.knowledge.saveChanges') : t('toolbox.knowledge.saveDoc')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderSearchTab = () => (
    <div className="space-y-6">
      <div className="glass-panel p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">{t('toolbox.knowledge.searchTitle')}</h2>

        <div className="flex gap-3 mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder={t('toolbox.knowledge.searchPlaceholder')}
            className="flex-1 px-4 py-2 border border-pearl-line rounded-lg bg-white/60 focus:outline-none focus:ring-2 focus:ring-atelier-teal/30"
          />
          <button
            onClick={handleSearch}
            className="btn btn-primary"
          >
            <Search className="w-4 h-4" />
            {t('nav.search')}
          </button>
        </div>

        <div className="flex items-center gap-4 text-sm text-ink-muted">
          <label className="flex items-center gap-2">
            <input type="checkbox" defaultChecked className="rounded" />
            {t('toolbox.knowledge.semantic')}
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" className="rounded" />
            {t('toolbox.knowledge.fulltext')}
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" defaultChecked className="rounded" />
            {t('toolbox.knowledge.includeSummary')}
          </label>
        </div>
      </div>

      {/* 搜索结果 */}
      {searchResults.length > 0 && (
        <div className="glass-panel p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-ink">
              {t('toolbox.knowledge.results')} ({searchResults.length})
            </h3>
            {(() => {
              const scores = searchResults
                .map((doc) => doc.relevance)
                .filter((value): value is number => value !== undefined && value !== null);
              if (scores.length === 0) return null;
              const avg = scores.reduce((acc, v) => acc + v, 0) / scores.length;
              return (
                <div className="flex items-center gap-2 text-sm text-ink-muted">
                  <TrendingUp className="w-4 h-4" />
                  {t('toolbox.knowledge.avgRelevance')}: {formatRelevance(avg)}
                </div>
              );
            })()}
          </div>

          <div className="space-y-4">
            {searchResults.map((doc, index) => (
              <div
                key={doc.id}
                className="border border-pearl-line rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer bg-white/40"
                onClick={() => handleViewDocument(doc)}
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-atelier-teal-soft rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-atelier-teal">{index + 1}</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium text-ink mb-1">{doc.title}</h4>
                    <p className="text-sm text-ink-muted mb-2 line-clamp-2">
                      {doc.content}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-ink-muted">
                      <span className="px-2 py-0.5 bg-pearl-soft rounded">{doc.category}</span>
                      {doc.size !== undefined && <span>{formatFileSize(doc.size)}</span>}
                      {formatRelevance(doc.relevance) && (
                        <span>{t('toolbox.knowledge.relevance')}: {formatRelevance(doc.relevance)}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderStatsTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 热门分类 */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-semibold text-ink mb-4">{t('toolbox.knowledge.hotCategories')}</h3>
          <div className="space-y-3">
            {[...(localDocuments.length > 0
              ? [{ name: t('toolbox.knowledge.stat.localDocs'), count: localDocuments.length }]
              : []),
              ...categories.map((cat) => ({ name: cat.name, count: cat.count || 0 })),
            ]
              .sort((a, b) => (b.count || 0) - (a.count || 0))
              .slice(0, 6)
              .map((cat, index) => (
                <div key={cat.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-atelier-teal-soft rounded-full flex items-center justify-center text-sm font-medium text-atelier-teal">
                      {index + 1}
                    </span>
                    <span className="text-ink">{cat.name}</span>
                  </div>
                  <span className="text-sm text-ink-muted">{cat.count || 0} {t('toolbox.knowledge.unit')}</span>
                </div>
              ))}
            {categories.length === 0 && localDocuments.length === 0 && (
              <div className="text-sm text-ink-muted">{t('toolbox.knowledge.noCategoryData')}</div>
            )}
          </div>
        </div>

        {/* 概况 */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-semibold text-ink mb-4">{t('toolbox.knowledge.overview')}</h3>
          <div className="space-y-4 text-sm text-ink-muted">
            <div className="flex items-center justify-between">
              <span>{t('toolbox.knowledge.stat.totalDocs')}</span>
              <span className="font-medium">{stats.totalDocuments}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>{t('toolbox.knowledge.stat.collections')}</span>
              <span className="font-medium">{categories.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>{t('toolbox.knowledge.stat.localDocs')}</span>
              <span className="font-medium">{localDocuments.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>{t('toolbox.knowledge.recentSearch')}</span>
              <span className="font-medium">{searchHistory.length}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 搜索记录 */}
      <div className="glass-panel p-6">
        <h3 className="text-lg font-semibold text-ink mb-4">{t('toolbox.knowledge.recentSearch')}</h3>
        {searchHistory.length === 0 ? (
          <div className="text-sm text-ink-muted">{t('toolbox.knowledge.noSearchHistory')}</div>
        ) : (
          <div className="divide-y divide-pearl-line">
            {searchHistory.slice(0, 10).map((item) => (
              <div key={item.query} className="py-2 flex items-center justify-between text-sm">
                <div>
                  <div className="font-medium text-ink">{item.query}</div>
                  <div className="text-xs text-ink-muted">
                    {new Date(item.timestamp).toLocaleString()}
                  </div>
                </div>
                <span className="text-xs text-ink-muted">{t('toolbox.knowledge.count')} {item.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const tabs: { key: 'documents' | 'upload' | 'search' | 'stats'; label: string; resetEdit?: boolean }[] = [
    { key: 'documents', label: t('toolbox.knowledge.tab.documents'), resetEdit: true },
    { key: 'upload', label: t('toolbox.knowledge.tab.upload') },
    { key: 'search', label: t('toolbox.knowledge.tab.search'), resetEdit: true },
    { key: 'stats', label: t('toolbox.knowledge.tab.stats'), resetEdit: true },
  ];

  return (
    <AppShell
      title={t('toolbox.knowledge.title')}
      subtitle={t('toolbox.knowledge.subtitle')}
      actions={
        <div className="flex gap-2">
          <button className="btn btn-ghost btn-sm" title={t('toolbox.refresh')}>
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className="btn btn-primary btn-sm"
          >
            <Upload className="w-4 h-4" />
            {t('toolbox.knowledge.tab.upload')}
          </button>
        </div>
      }
    >
      <div className="px-4 sm:px-8 lg:px-10 py-6 sm:py-8 max-w-6xl mx-auto space-y-6 sm:space-y-8">
        {/* 标签页导航 */}
        <div className="glass-panel p-1 flex items-center gap-1 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => {
                if (tab.resetEdit) setEditingDocumentId(null);
                setActiveTab(tab.key);
              }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? 'bg-atelier-teal text-white'
                  : 'text-ink-muted hover:text-ink'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 内容区 */}
        {activeTab === 'documents' && renderDocumentsTab()}
        {activeTab === 'upload' && renderUploadTab()}
        {activeTab === 'search' && renderSearchTab()}
        {activeTab === 'stats' && renderStatsTab()}
      </div>

      {/* 文档详情弹窗 */}
      {selectedDocument && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="glass-dense rounded-2xl shadow-atelier-lg max-w-3xl w-full max-h-[90vh] overflow-hidden mx-4">
            <div className="p-6 border-b border-pearl-line flex items-center justify-between">
              <h3 className="text-lg font-semibold text-ink">
                {selectedDocument.title}
              </h3>
              <button
                onClick={() => setSelectedDocument(null)}
                className="p-2 hover:bg-pearl-soft rounded-lg"
              >
                ✕
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="flex items-center gap-4 text-sm text-ink-muted mb-4">
                <span className="px-2 py-1 bg-atelier-teal-soft text-atelier-teal rounded">
                  {selectedDocument.category}
                </span>
                <span>{formatFileSize(selectedDocument.size ?? 0)}</span>
                <span>
                  {selectedDocument.updatedAt
                    ? new Date(selectedDocument.updatedAt).toLocaleDateString()
                    : '-'}
                </span>
              </div>
              <div className="flex flex-wrap gap-2 mb-4">
                {(selectedDocument.tags || []).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 bg-pearl-soft text-ink-muted text-xs rounded"
                  >
                    {tag}
                  </span>
                ))}
                {(selectedDocument.tags || []).length === 0 && (
                  <span className="text-xs text-ink-faint">{t('toolbox.knowledge.noTags')}</span>
                )}
              </div>
              <div className="prose prose-sm max-w-none">
                <p className="text-ink-muted whitespace-pre-wrap">{selectedDocument.content}</p>
              </div>
            </div>
            <div className="p-6 border-t border-pearl-line flex justify-end gap-3">
              <button
                onClick={() => setSelectedDocument(null)}
                className="btn btn-secondary"
              >
                {t('toolbox.close')}
              </button>
              {selectedDocument.id.startsWith('local_') && (
                <button
                  onClick={() => {
                    setActiveTab('upload');
                    setUploadForm({
                      title: selectedDocument.title,
                      content: selectedDocument.content,
                      tags: (selectedDocument.tags || []).join(', '),
                    });
                    setEditingDocumentId(selectedDocument.id);
                    setSelectedDocument(null);
                  }}
                  className="btn btn-primary"
                >
                  {t('toolbox.knowledge.continueEdit')}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
};

export default KnowledgeBasePage;

/**
 * 笔记管理页面
 * 管理用户在创作过程中产生的所有笔记（统一杂志编辑风）
 */

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import AppShell from '@/components/layout/AppShell';
import {
  FileText,
  Search,
  Download,
  Trash2,
  Edit,
  Check,
  X,
  Calendar,
  LayoutGrid,
  List,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import * as noteService from '@/services/noteService';
import clsx from 'clsx';
import { useI18n } from '@/i18n';

type Note = {
  id: string;
  user_id: string;
  session_id: string;
  action: string;
  name: string;
  title?: string;
  context: string;
  select_status: number;
  user_comment?: string;
  content_type?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
};

type ContentFilter = 'all' | 'text' | 'markdown' | 'code' | 'image';
type ExportFormat = 'json' | 'md' | 'txt';

export default function NotesPage() {
  const { user } = useAuthStore();
  const { t } = useI18n();

  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNotes, setSelectedNotes] = useState<Set<string>>(new Set());
  const [contentFilter, setContentFilter] = useState<ContentFilter>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('md');
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [editContent, setEditContent] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedOnly, setSelectedOnly] = useState(false);

  // 获取笔记列表
  const loadNotes = async () => {
    if (!user) return;

    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(
        `/api/notes/list/${user.id}?session_id=&content_type=&action=&selected_only=${selectedOnly}&search=${encodeURIComponent(searchQuery)}&limit=100&offset=0`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setNotes(data.notes || []);
      } else {
        setError(t('toolbox.notes.toast.getFailed'));
      }
    } catch (err) {
      console.error('加载笔记失败:', err);
      setError(t('toolbox.notes.toast.loadFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadNotes();
  }, [user, selectedOnly, searchQuery]);

  // 删除笔记
  const handleDeleteNote = async (noteId: string) => {
    if (!confirm(t('toolbox.notes.toast.deleteConfirm'))) return;

    try {
      const response = await fetch(`/api/notes/${noteId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        setNotes(notes.filter(n => n.id !== noteId));
      } else {
        alert(t('toolbox.notes.toast.deleteFailed'));
      }
    } catch (err) {
      console.error('删除笔记失败:', err);
      alert(t('toolbox.notes.toast.deleteFailed'));
    }
  };

  // 保存编辑
  const handleSaveEdit = async () => {
    if (!editingNote || !user) return;

    try {
      const result = await noteService.updateNoteContent(
        editingNote.id,
        user.id,
        editContent
      );

      if (result.success) {
        setNotes(notes.map(n =>
          n.id === editingNote.id
            ? { ...n, context: editContent }
            : n
        ));
        setEditingNote(null);
        setEditContent('');
      } else {
        alert(result.message || t('toolbox.notes.toast.saveFailed'));
      }
    } catch (err) {
      console.error('保存失败:', err);
      alert(t('toolbox.notes.toast.saveFailed'));
    }
  };

  // 切换选择状态
  const toggleSelectNote = (noteId: string) => {
    const newSelected = new Set(selectedNotes);
    if (newSelected.has(noteId)) {
      newSelected.delete(noteId);
    } else {
      newSelected.add(noteId);
    }
    setSelectedNotes(newSelected);
  };

  // 导出笔记
  const handleExportNotes = async () => {
    if (!user) return;

    try {
      const response = await fetch('/api/notes/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          user_id: user.id,
          session_id: '',
          content_types: [],
          export_format: exportFormat,
          include_user_comments: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.exported_data) {
          const blob = new Blob([data.exported_data], {
            type: exportFormat === 'json' ? 'application/json' :
                 exportFormat === 'md' ? 'text/markdown' : 'text/plain'
          });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = data.filename || `notes.${exportFormat}`;
          a.click();
          URL.revokeObjectURL(url);
          setShowExportModal(false);
        }
      } else {
        alert(t('toolbox.notes.toast.exportFailed'));
      }
    } catch (err) {
      console.error('导出失败:', err);
      alert(t('toolbox.notes.toast.exportFailed'));
    }
  };

  // 过滤笔记
  const filteredNotes = notes.filter(note => {
    // 内容类型过滤
    if (contentFilter !== 'all' && note.content_type !== contentFilter) {
      return false;
    }

    // 动作过滤
    if (actionFilter !== 'all' && note.action !== actionFilter) {
      return false;
    }

    return true;
  });

  // 获取所有动作类型
  const actionTypes = Array.from(new Set(notes.map(n => n.action))).sort();

  const getActionIcon = (action: string) => {
    const iconMap: Record<string, string> = {
      'story-analysis': '📖',
      'character-creation': '👤',
      'plot-design': '📝',
      'dialogue-generation': '💬',
      'scene-description': '🎬',
      'script-evaluation': '⭐',
      'mind-map': '🗺️',
      'workflow': '⚙️',
    };
    return iconMap[action] || '📄';
  };

  const getActionLabel = (action: string) => {
    const labelMap: Record<string, string> = {
      'story-analysis': t('toolbox.notes.action.story-analysis'),
      'character-creation': t('toolbox.notes.action.character-creation'),
      'plot-design': t('toolbox.notes.action.plot-design'),
      'dialogue-generation': t('toolbox.notes.action.dialogue-generation'),
      'scene-description': t('toolbox.notes.action.scene-description'),
      'script-evaluation': t('toolbox.notes.action.script-evaluation'),
      'mind-map': t('toolbox.notes.action.mind-map'),
      'workflow': t('toolbox.notes.action.workflow'),
    };
    return labelMap[action] || action;
  };

  return (
    <AppShell
      title={t('toolbox.notes.title')}
      subtitle={t('toolbox.notes.subtitle', { count: notes.length })}
      actions={
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => setShowExportModal(true)}
        >
          <Download className="w-3.5 h-3.5" />
          {t('toolbox.export')}
        </button>
      }
    >
      <div className="p-4 sm:p-8 max-w-6xl mx-auto space-y-5">
        {/* 工具栏 */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-faint" />
            <input
              type="text"
              className="input pl-10"
              placeholder={t('toolbox.notes.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="rounded-lg border border-pearl-line bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:border-atelier-teal"
          >
            <option value="all">{t('toolbox.notes.allTypes')}</option>
            {actionTypes.map(action => (
              <option key={action} value={action}>
                {getActionLabel(action)}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-0.5 p-0.5 rounded-lg border border-pearl-line">
            <button
              type="button"
              onClick={() => setViewMode('grid')}
              className={clsx(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'grid' ? 'bg-pearl-soft text-ink' : 'text-ink-faint hover:text-ink'
              )}
              title={t('toolbox.notes.cardView')}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('list')}
              className={clsx(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'list' ? 'bg-pearl-soft text-ink' : 'text-ink-faint hover:text-ink'
              )}
              title={t('toolbox.notes.listView')}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-center justify-between gap-3 p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => setError('')}
              className="shrink-0 text-xs underline hover:text-red-900"
            >
              {t('toolbox.close')}
            </button>
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-ink-muted">
            <div className="w-10 h-10 border-[3px] border-pearl-line border-t-atelier-teal rounded-full animate-spin" />
            <p className="text-sm mt-3">{t('toolbox.notes.loading')}</p>
          </div>
        ) : filteredNotes.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-pearl-soft flex items-center justify-center mx-auto mb-4">
              <FileText className="w-7 h-7 text-ink-faint" />
            </div>
            <h3 className="font-display text-lg font-semibold text-ink">
              {searchQuery ? t('toolbox.notes.noMatch') : t('toolbox.notes.noNotes')}
            </h3>
            <p className="text-sm text-ink-muted mt-1">
              {searchQuery ? t('toolbox.notes.noMatchHint') : t('toolbox.notes.noNotesHint')}
            </p>
          </div>
        ) : viewMode === 'list' ? (
          <div className="space-y-3">
            {filteredNotes.map((note) => (
              <NoteListItem
                key={note.id}
                note={note}
                isSelected={selectedNotes.has(note.id)}
                isEditing={editingNote?.id === note.id}
                editContent={editContent}
                onToggleSelect={() => toggleSelectNote(note.id)}
                onEdit={() => {
                  setEditingNote(note);
                  setEditContent(note.context);
                }}
                onSave={handleSaveEdit}
                onCancel={() => {
                  setEditingNote(null);
                  setEditContent('');
                }}
                onDelete={() => handleDeleteNote(note.id)}
                onEditContentChange={setEditContent}
                getActionIcon={getActionIcon}
                getActionLabel={getActionLabel}
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredNotes.map((note) => (
              <NoteCard
                key={note.id}
                note={note}
                isSelected={selectedNotes.has(note.id)}
                onToggleSelect={() => toggleSelectNote(note.id)}
                onEdit={() => {
                  setEditingNote(note);
                  setEditContent(note.context);
                }}
                onDelete={() => handleDeleteNote(note.id)}
                getActionIcon={getActionIcon}
                getActionLabel={getActionLabel}
              />
            ))}
          </div>
        )}
      </div>

      {/* 编辑笔记模态框 */}
      {editingNote && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]"
            onClick={() => {
              setEditingNote(null);
              setEditContent('');
            }}
          />
          <div className="relative bg-white rounded-2xl shadow-atelier-lg max-w-3xl w-full max-h-[80vh] flex flex-col animate-slide-up">
            <div className="px-6 py-4 border-b border-pearl-line flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="font-display text-lg font-semibold text-ink">{t('toolbox.notes.editNote')}</h2>
                <p className="text-xs text-ink-muted mt-0.5 truncate">
                  {editingNote.title || editingNote.name}
                </p>
              </div>
              <button
                type="button"
                className="p-2 rounded-lg hover:bg-pearl-soft text-ink-muted shrink-0"
                onClick={() => {
                  setEditingNote(null);
                  setEditContent('');
                }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-full min-h-[400px] p-4 rounded-xl border border-pearl-line bg-white text-sm leading-relaxed text-ink resize-none focus:outline-none focus:border-atelier-teal focus:ring-2 focus:ring-atelier-teal/15"
                placeholder={t('toolbox.notes.contentPlaceholder')}
              />
            </div>

            <div className="px-6 py-4 border-t border-pearl-line flex gap-3">
              <button
                type="button"
                className="btn btn-secondary flex-1"
                onClick={() => {
                  setEditingNote(null);
                  setEditContent('');
                }}
              >
                {t('common.cancel')}
              </button>
              <button type="button" className="btn btn-primary flex-1" onClick={handleSaveEdit}>
                {t('common.save')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 导出模态框 */}
      {showExportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]"
            onClick={() => setShowExportModal(false)}
          />
          <div className="relative bg-white rounded-2xl shadow-atelier-lg max-w-md w-full p-6 animate-slide-up">
            <div className="flex items-start justify-between gap-3 mb-4">
              <h2 className="font-display text-lg font-semibold text-ink">{t('toolbox.notes.exportNote')}</h2>
              <button
                type="button"
                className="p-2 rounded-lg hover:bg-pearl-soft text-ink-muted"
                onClick={() => setShowExportModal(false)}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-ink mb-2">{t('toolbox.notes.exportFormat')}</label>
                <div className="space-y-2">
                  {(['json', 'md', 'txt'] as ExportFormat[]).map((format) => (
                    <label
                      key={format}
                      className="flex items-center gap-2.5 p-2.5 rounded-lg border border-pearl-line cursor-pointer hover:border-atelier-teal/40 transition-colors"
                    >
                      <input
                        type="radio"
                        name="exportFormat"
                        value={format}
                        checked={exportFormat === format}
                        onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
                        className="text-atelier-teal focus:ring-atelier-teal"
                      />
                      <span className="text-sm text-ink">
                        {format === 'json' && t('toolbox.notes.jsonFormat')}
                        {format === 'md' && t('toolbox.notes.mdFormat')}
                        {format === 'txt' && t('toolbox.notes.txtFormat')}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pt-4 border-t border-pearl-line">
                <button
                  type="button"
                  className="btn btn-secondary flex-1"
                  onClick={() => setShowExportModal(false)}
                >
                  {t('common.cancel')}
                </button>
                <button type="button" className="btn btn-primary flex-1" onClick={handleExportNotes}>
                  {t('toolbox.export')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

/**
 * 笔记卡片组件
 */
function NoteCard({
  note,
  isSelected,
  onToggleSelect,
  onEdit,
  onDelete,
  getActionIcon,
  getActionLabel
}: {
  note: Note;
  isSelected: boolean;
  onToggleSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
  getActionIcon: (action: string) => string;
  getActionLabel: (action: string) => string;
}) {
  const { t } = useI18n();
  return (
    <div
      className={clsx(
        'card group p-5 flex flex-col gap-3 transition-all hover:shadow-atelier',
        isSelected && 'ring-2 ring-atelier-teal'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-atelier-teal-soft flex items-center justify-center text-base shrink-0">
            {getActionIcon(note.action)}
          </div>
          <div className="min-w-0">
            <h3 className="font-display font-semibold text-ink text-sm truncate">
              {note.title || note.name}
            </h3>
            <span className="badge badge-default mt-1">{getActionLabel(note.action)}</span>
          </div>
        </div>

        <button
          type="button"
          onClick={onToggleSelect}
          className={clsx(
            'p-1.5 rounded-lg transition-colors shrink-0',
            isSelected ? 'bg-atelier-teal text-white' : 'hover:bg-pearl-soft'
          )}
          title={t('toolbox.notes.select')}
        >
          {isSelected ? (
            <Check className="w-4 h-4" />
          ) : (
            <div className="w-4 h-4 border-2 border-pearl-line rounded" />
          )}
        </button>
      </div>

      <p className="text-sm text-ink-muted leading-relaxed line-clamp-3 min-h-[60px]">
        {note.context}
      </p>

      {note.user_comment && (
        <div className="p-2.5 rounded-lg bg-pearl-soft">
          <p className="text-xs text-ink-muted">{note.user_comment}</p>
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-pearl-line/70">
        <div className="flex items-center gap-1 text-xs text-ink-faint">
          <Calendar className="w-3 h-3" />
          {formatDistanceToNow(new Date(note.created_at), { addSuffix: true, locale: zhCN })}
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            type="button"
            onClick={onEdit}
            className="p-1.5 hover:bg-pearl-soft rounded-lg transition-colors text-ink-muted hover:text-atelier-teal"
            title={t('toolbox.notes.edit')}
          >
            <Edit className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="p-1.5 hover:bg-red-50 rounded-lg transition-colors text-ink-muted hover:text-red-500"
            title={t('common.delete')}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * 笔记列表项组件
 */
function NoteListItem({
  note,
  isSelected,
  isEditing,
  editContent,
  onToggleSelect,
  onEdit,
  onSave,
  onCancel,
  onDelete,
  onEditContentChange,
  getActionIcon,
  getActionLabel
}: {
  note: Note;
  isSelected: boolean;
  isEditing: boolean;
  editContent: string;
  onToggleSelect: () => void;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onDelete: () => void;
  onEditContentChange: (content: string) => void;
  getActionIcon: (action: string) => string;
  getActionLabel: (action: string) => string;
}) {
  const { t } = useI18n();
  return (
    <div
      className={clsx(
        'card group p-4 transition-all hover:shadow-atelier',
        isSelected && 'ring-2 ring-atelier-teal'
      )}
    >
      <div className="flex items-start gap-4">
        <button
          type="button"
          onClick={onToggleSelect}
          className={clsx(
            'mt-0.5 p-1.5 rounded-lg transition-colors shrink-0',
            isSelected ? 'bg-atelier-teal text-white' : 'hover:bg-pearl-soft'
          )}
          title={t('toolbox.notes.select')}
        >
          {isSelected ? (
            <Check className="w-4 h-4" />
          ) : (
            <div className="w-4 h-4 border-2 border-pearl-line rounded" />
          )}
        </button>

        <div className="w-9 h-9 rounded-lg bg-atelier-teal-soft flex items-center justify-center text-base shrink-0">
          {getActionIcon(note.action)}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <div className="min-w-0">
              <h3 className="font-display font-semibold text-ink truncate">
                {note.title || note.name}
              </h3>
              <p className="text-xs text-ink-faint mt-0.5">
                {getActionLabel(note.action)} ·{' '}
                {formatDistanceToNow(new Date(note.created_at), { addSuffix: true, locale: zhCN })}
              </p>
            </div>

            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
              <button
                type="button"
                onClick={onEdit}
                className="p-1.5 hover:bg-pearl-soft rounded-lg transition-colors text-ink-muted hover:text-atelier-teal"
                title={t('toolbox.notes.edit')}
              >
                <Edit className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={onDelete}
                className="p-1.5 hover:bg-red-50 rounded-lg transition-colors text-ink-muted hover:text-red-500"
                title={t('common.delete')}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {isEditing ? (
            <div className="space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => onEditContentChange(e.target.value)}
                className="w-full p-3 rounded-xl border border-pearl-line bg-white text-sm text-ink resize-none focus:outline-none focus:border-atelier-teal focus:ring-2 focus:ring-atelier-teal/15"
                rows={6}
              />
              <div className="flex gap-2">
                <button type="button" className="btn btn-primary btn-sm" onClick={onSave}>
                  {t('common.save')}
                </button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={onCancel}>
                  {t('common.cancel')}
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-ink-muted leading-relaxed">{note.context}</p>
          )}

          {note.user_comment && !isEditing && (
            <div className="mt-2 p-2.5 rounded-lg bg-pearl-soft">
              <p className="text-xs text-ink-muted">{note.user_comment}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

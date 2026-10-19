/**
 * 图谱工具栏组件
 * Graph Toolbar Component
 */

import {
  RefreshCw,
  Download,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
  Grid3x3,
  Network,
  GitBranch,
  CircleDot,
} from 'lucide-react';
import { useI18n } from '@/i18n';

interface GraphToolbarProps {
  onRefresh: () => void;
  onExportImage: () => void;
  onResetView: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onOpenFilter: () => void;
  viewMode: 'force' | 'tree' | 'radial' | 'circle';
  onViewModeChange: (mode: 'force' | 'tree' | 'radial' | 'circle') => void;
  loading: boolean;
  zoom: number;
}

const VIEW_MODES = [
  { value: 'force', icon: Network, labelKey: 'chatGraph.graph.viewMode.force' },
  { value: 'tree', icon: GitBranch, labelKey: 'chatGraph.graph.viewMode.tree' },
  { value: 'radial', icon: CircleDot, labelKey: 'chatGraph.graph.viewMode.radial' },
  { value: 'circle', icon: Grid3x3, labelKey: 'chatGraph.graph.viewMode.circle' },
] as const;

export function GraphToolbar({
  onRefresh,
  onExportImage,
  onResetView,
  onZoomIn,
  onZoomOut,
  onOpenFilter,
  viewMode,
  onViewModeChange,
  loading,
  zoom,
}: GraphToolbarProps) {
  const { t } = useI18n();

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
      {/* 左侧：视图模式和缩放 */}
      <div className="flex items-center space-x-2">
        {/* 视图模式切换 */}
        <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
          {VIEW_MODES.map(({ value, icon: Icon, labelKey }) => (
            <button
              key={value}
              onClick={() => onViewModeChange(value as any)}
              className={`p-2 rounded-md transition-colors ${
                viewMode === value
                  ? 'bg-white shadow-sm text-indigo-600'
                  : 'text-gray-600 hover:bg-white hover:shadow-sm'
              }`}
              title={t(labelKey)}
            >
              <Icon className="w-4 h-4" />
            </button>
          ))}
        </div>

        {/* 缩放控制 */}
        <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1 ml-2">
          <button
            onClick={onZoomOut}
            className="p-2 rounded-md hover:bg-white hover:shadow-sm transition-colors text-gray-600"
            title={t('chatGraph.graph.zoomOut')}
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="px-2 text-sm text-gray-600 font-medium">{Math.round(zoom * 100)}%</span>
          <button
            onClick={onZoomIn}
            className="p-2 rounded-md hover:bg-white hover:shadow-sm transition-colors text-gray-600"
            title={t('chatGraph.graph.zoomIn')}
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={onResetView}
            className="p-2 rounded-md hover:bg-white hover:shadow-sm transition-colors text-gray-600 border-l border-gray-300"
            title={t('chatGraph.graph.resetView')}
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 右侧：操作按钮 */}
      <div className="flex items-center space-x-2">
        {/* 过滤器按钮 */}
        <button
          onClick={onOpenFilter}
          className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          title={t('chatGraph.graph.openFilter')}
        >
          <Filter className="w-4 h-4 mr-2" />
          {t('chatGraph.graph.filterTitle')}
        </button>

        {/* 导出图片按钮 */}
        <button
          onClick={onExportImage}
          className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          title={t('chatGraph.graph.exportImage')}
        >
          <Download className="w-4 h-4 mr-2" />
          {t('studio.export')}
        </button>

        {/* 刷新按钮 */}
        <button
          onClick={onRefresh}
          disabled={loading}
          className={`inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          title={t('chatGraph.graph.refreshData')}
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          {t('studio.refresh')}
        </button>
      </div>
    </div>
  );
}

/**
 * 图谱过滤器组件
 * Graph Filter Component
 */

import { useState, useEffect } from 'react';
import { X, Check } from 'lucide-react';
import { useGraphStore } from '@/store/graphStore';
import type { NodeType, RelationType } from '@/services/graphService';
import { useI18n } from '@/i18n';

interface GraphFilterProps {
  onClose: () => void;
}

const NODE_TYPES: { value: NodeType; labelKey: string; color: string }[] = [
  { value: 'Story', labelKey: 'chatGraph.graph.nodeType.story', color: 'bg-slate-600' },
  { value: 'Character', labelKey: 'chatGraph.graph.nodeType.character', color: 'bg-indigo-500' },
  { value: 'PlotNode', labelKey: 'chatGraph.graph.nodeType.plot', color: 'bg-emerald-500' },
  { value: 'WorldRule', labelKey: 'chatGraph.graph.nodeType.worldRule', color: 'bg-amber-500' },
  { value: 'Location', labelKey: 'chatGraph.graph.nodeType.location', color: 'bg-violet-500' },
  { value: 'Item', labelKey: 'chatGraph.graph.nodeType.item', color: 'bg-pink-500' },
  { value: 'Conflict', labelKey: 'chatGraph.graph.nodeType.conflict', color: 'bg-red-500' },
  { value: 'Theme', labelKey: 'chatGraph.graph.nodeType.theme', color: 'bg-cyan-500' },
  { value: 'Motivation', labelKey: 'chatGraph.graph.nodeType.motivation', color: 'bg-orange-500' },
];

const DEFAULT_RELATION_TYPES: { value: RelationType; labelKey: string }[] = [
  { value: 'SOCIAL_BOND', labelKey: 'chatGraph.graph.relation.socialBond' },
  { value: 'FAMILY_RELATION', labelKey: 'chatGraph.graph.relation.familyRelation' },
  { value: 'ROMANTIC_RELATION', labelKey: 'chatGraph.graph.relation.romanticRelation' },
  { value: 'INFLUENCES', labelKey: 'chatGraph.graph.relation.influences' },
  { value: 'LEADS_TO', labelKey: 'chatGraph.graph.relation.leadsTo' },
  { value: 'NEXT', labelKey: 'chatGraph.graph.relation.next' },
  { value: 'RESOLVES', labelKey: 'chatGraph.graph.relation.resolves' },
  { value: 'COMPLICATES', labelKey: 'chatGraph.graph.relation.complicates' },
  { value: 'INVOLVED_IN', labelKey: 'chatGraph.graph.relation.involvedIn' },
  { value: 'DRIVEN_BY', labelKey: 'chatGraph.graph.relation.drivenBy' },
  { value: 'CONTAINS', labelKey: 'chatGraph.graph.relation.contains' },
  { value: 'VIOLATES', labelKey: 'chatGraph.graph.relation.violates' },
  { value: 'ENFORCES', labelKey: 'chatGraph.graph.relation.enforces' },
  { value: 'LOCATED_IN', labelKey: 'chatGraph.graph.relation.locatedIn' },
  { value: 'LOCATED_AT', labelKey: 'chatGraph.graph.relation.locatedAt' },
  { value: 'OWNS', labelKey: 'chatGraph.graph.relation.owns' },
  { value: 'PART_OF', labelKey: 'chatGraph.graph.relation.partOf' },
  { value: 'REPRESENTS', labelKey: 'chatGraph.graph.relation.represents' },
  { value: 'OPPOSES', labelKey: 'chatGraph.graph.relation.opposes' },
  { value: 'SUPPORTS', labelKey: 'chatGraph.graph.relation.supports' },
];

export function GraphFilter({ onClose }: GraphFilterProps) {
  const { t } = useI18n();
  const { filter, setFilter, relationTypeOptions } = useGraphStore();
  const [localFilter, setLocalFilter] = useState({
    nodeTypes: [...filter.nodeTypes],
    relationTypes: [...filter.relationTypes],
    searchQuery: filter.searchQuery,
  });

  useEffect(() => {
    setLocalFilter({
      nodeTypes: [...filter.nodeTypes],
      relationTypes: [...filter.relationTypes],
      searchQuery: filter.searchQuery,
    });
  }, [filter]);

  const handleNodeTypeToggle = (nodeType: NodeType) => {
    setLocalFilter((prev) => {
      const newTypes = prev.nodeTypes.includes(nodeType)
        ? prev.nodeTypes.filter((t) => t !== nodeType)
        : [...prev.nodeTypes, nodeType];
      return { ...prev, nodeTypes: newTypes };
    });
  };

  const handleRelationTypeToggle = (relationType: RelationType) => {
    setLocalFilter((prev) => {
      const newTypes = prev.relationTypes.includes(relationType)
        ? prev.relationTypes.filter((t) => t !== relationType)
        : [...prev.relationTypes, relationType];
      return { ...prev, relationTypes: newTypes };
    });
  };

  const handleApply = () => {
    setFilter(localFilter);
    onClose();
  };

  const handleReset = () => {
    setFilter({
      nodeTypes: [],
      relationTypes: [],
      searchQuery: '',
    });
    onClose();
  };

  const isNodeTypeSelected = (nodeType: NodeType) => localFilter.nodeTypes.includes(nodeType);
  const isRelationTypeSelected = (relationType: RelationType) =>
    localFilter.relationTypes.includes(relationType);
  const hasSelection =
    localFilter.nodeTypes.length > 0 ||
    localFilter.relationTypes.length > 0 ||
    localFilter.searchQuery.length > 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-end z-50">
      <div className="w-80 bg-white h-full shadow-xl overflow-y-auto">
        {/* 头部 */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">{t('chatGraph.graph.filterTitle')}</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-gray-100 transition-colors"
            title={t('project.close')}
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* 内容 */}
        <div className="px-6 py-4 space-y-6">
          {/* 搜索框 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">{t('chatGraph.graph.searchNodes')}</label>
            <input
              type="text"
              value={localFilter.searchQuery}
              onChange={(e) =>
                setLocalFilter((prev) => ({ ...prev, searchQuery: e.target.value }))
              }
              placeholder={t('chatGraph.graph.searchNodesPlaceholder')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
            />
          </div>

          {/* 节点类型过滤 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">{t('chatGraph.graph.nodeTypeLabel')}</label>
              {localFilter.nodeTypes.length > 0 && (
                <button
                  onClick={() => setLocalFilter((prev) => ({ ...prev, nodeTypes: [] }))}
                  className="text-xs text-indigo-600 hover:text-indigo-700"
                >
                  {t('chatGraph.graph.clear')}
                </button>
              )}
            </div>
            <div className="space-y-2">
              {NODE_TYPES.map(({ value, labelKey, color }) => (
                <button
                  key={value}
                  onClick={() => handleNodeTypeToggle(value)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border transition-colors ${
                    isNodeTypeSelected(value)
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <span className={`w-3 h-3 rounded-full ${color}`} />
                    <span className="text-sm text-gray-700">{t(labelKey)}</span>
                  </div>
                  {isNodeTypeSelected(value) && (
                    <Check className="w-4 h-4 text-indigo-600" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* 关系类型过滤 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">{t('chatGraph.graph.relationTypeLabel')}</label>
              {localFilter.relationTypes.length > 0 && (
                <button
                  onClick={() => setLocalFilter((prev) => ({ ...prev, relationTypes: [] }))}
                  className="text-xs text-indigo-600 hover:text-indigo-700"
                >
                  {t('chatGraph.graph.clear')}
                </button>
              )}
            </div>
            <div className="space-y-2">
              {(relationTypeOptions.length > 0 ? relationTypeOptions : DEFAULT_RELATION_TYPES).map(
                (item) => {
                  const label = 'labelKey' in item ? t(item.labelKey) : item.label;
                  return (
                    <button
                      key={item.value}
                      onClick={() => handleRelationTypeToggle(item.value)}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border transition-colors ${
                        isRelationTypeSelected(item.value)
                          ? 'border-indigo-500 bg-indigo-50'
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <span className="text-sm text-gray-700">{label}</span>
                      {isRelationTypeSelected(item.value) && (
                        <Check className="w-4 h-4 text-indigo-600" />
                      )}
                    </button>
                  );
                }
              )}
            </div>
          </div>
        </div>

        {/* 底部操作按钮 */}
        <div className="sticky bottom-0 bg-white border-t border-gray-200 px-6 py-4">
          <div className="flex space-x-2">
            <button
              onClick={handleReset}
              disabled={!hasSelection}
              className={`flex-1 px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg transition-colors ${
                hasSelection
                  ? 'text-gray-700 hover:bg-gray-50'
                  : 'text-gray-400 cursor-not-allowed'
              }`}
            >
              {t('common.reset')}
            </button>
            <button
              onClick={handleApply}
              className="flex-1 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              {t('chatGraph.graph.apply')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * 图谱统计信息组件
 * Graph Statistics Component
 */

import { Users, FileText, Scroll, Network, TrendingUp, Award } from 'lucide-react';
import type { GraphStatistics } from '@/services/graphService';
import { useI18n } from '@/i18n';

interface GraphStatisticsProps {
  statistics: GraphStatistics;
}

export function GraphStatistics({ statistics }: GraphStatisticsProps) {
  const { t } = useI18n();
  return (
    <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-4 max-w-sm">
      <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
        <Network className="w-4 h-4 mr-2 text-indigo-600" />
        {t('chatGraph.graph.statsTitle')}
      </h3>

      {/* 核心指标 */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="flex items-center space-x-2">
          <Users className="w-4 h-4 text-indigo-500" />
          <div>
            <p className="text-xs text-gray-500">{t('chatGraph.graph.stat.characters')}</p>
            <p className="text-sm font-semibold text-gray-900">{statistics.total_characters}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-emerald-500" />
          <div>
            <p className="text-xs text-gray-500">{t('chatGraph.graph.stat.plots')}</p>
            <p className="text-sm font-semibold text-gray-900">{statistics.total_plot_nodes}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Scroll className="w-4 h-4 text-amber-500" />
          <div>
            <p className="text-xs text-gray-500">{t('chatGraph.graph.stat.worldRules')}</p>
            <p className="text-sm font-semibold text-gray-900">{statistics.total_world_rules}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Network className="w-4 h-4 text-purple-500" />
          <div>
            <p className="text-xs text-gray-500">{t('chatGraph.graph.stat.relationships')}</p>
            <p className="text-sm font-semibold text-gray-900">{statistics.total_relationships}</p>
          </div>
        </div>
      </div>

      {/* 平均张力 */}
      {statistics.average_tension !== undefined && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500 flex items-center">
              <TrendingUp className="w-3 h-3 mr-1" />
              {t('chatGraph.graph.stat.avgTension')}
            </span>
            <span className="text-sm font-semibold text-gray-900">
              {statistics.average_tension.toFixed(1)}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${
                statistics.average_tension > 70
                  ? 'bg-red-500'
                  : statistics.average_tension > 40
                  ? 'bg-yellow-500'
                  : 'bg-green-500'
              }`}
              style={{ width: `${statistics.average_tension}%` }}
            />
          </div>
        </div>
      )}

      {/* 最具连接的角色 */}
      {statistics.most_connected_characters && statistics.most_connected_characters.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-gray-500 mb-2 flex items-center">
            <Award className="w-3 h-3 mr-1" />
            {t('chatGraph.graph.stat.mostConnected')}
          </h4>
          <div className="space-y-1">
            {statistics.most_connected_characters.slice(0, 3).map((character, index) => (
              <div key={character.character_id} className="flex items-center justify-between">
                <span className="text-xs text-gray-700 truncate">
                  {index + 1}. {character.name}
                </span>
                <span className="text-xs font-medium text-indigo-600">
                  {t('chatGraph.graph.stat.connections', { count: character.connection_count })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

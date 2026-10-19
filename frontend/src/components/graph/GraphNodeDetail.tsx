/**
 * 图谱节点详情面板组件
 * Graph Node Detail Panel Component
 */

import { useEffect, useState } from 'react';
import {
  X,
  User,
  FileText,
  Scroll,
  MapPin,
  Heart,
  Zap,
  TrendingUp,
  Edit,
  Trash2,
  BookOpen,
} from 'lucide-react';
import { useGraphStore } from '@/store/graphStore';
import type { NodeType } from '@/services/graphService';
import { useI18n } from '@/i18n';

interface GraphNodeDetailProps {
  nodeId: string;
  onClose: () => void;
}

// 节点类型图标映射
const NODE_ICONS: Record<NodeType, React.ElementType> = {
  Story: BookOpen,
  Character: User,
  PlotNode: FileText,
  WorldRule: Scroll,
  Location: MapPin,
  Item: Zap,
  Conflict: TrendingUp,
  Theme: Heart,
  Motivation: Heart,
};

export function GraphNodeDetail({ nodeId, onClose }: GraphNodeDetailProps) {
  const { t } = useI18n();
  const { nodes, characters, plotNodes, worldRules, deleteNode, saveNodeUpdates } = useGraphStore();
  const [node, setNode] = useState<any>(null);
  const [nodeType, setNodeType] = useState<NodeType | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<Record<string, any>>({});

  useEffect(() => {
    const graphNode = nodes.find((n) => n.id === nodeId);
    if (graphNode) {
      setNode(graphNode.properties ?? {});
      setNodeType(graphNode.type);
      return;
    }

    const character = characters.find((c) => c.character_id === nodeId);
    if (character) {
      setNode(character);
      setNodeType('Character');
      return;
    }

    const plot = plotNodes.find((p) => p.plot_id === nodeId);
    if (plot) {
      setNode(plot);
      setNodeType('PlotNode');
      return;
    }

    const rule = worldRules.find((r) => r.rule_id === nodeId);
    if (rule) {
      setNode(rule);
      setNodeType('WorldRule');
      return;
    }
  }, [nodeId, nodes, characters, plotNodes, worldRules]);

  useEffect(() => {
    if (node) {
      setEditForm({ ...node });
    }
  }, [node]);

  if (!node || !nodeType) {
    return null;
  }

  const Icon = NODE_ICONS[nodeType];
  const isGenericNode = ['Location', 'Item', 'Conflict', 'Theme', 'Motivation'].includes(nodeType);

  const handleDelete = async () => {
    if (confirm(t('chatGraph.graph.deleteNodeConfirm'))) {
      await deleteNode(nodeId, nodeType);
      onClose();
    }
  };

  const handleSave = async () => {
    if (!nodeType) return;
    await saveNodeUpdates(nodeId, nodeType, editForm);
    setIsEditing(false);
  };

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl border-l border-gray-200 overflow-y-auto z-50">
      {/* 头部 */}
      <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
        <div className="flex items-center space-x-2">
          <Icon className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">{t('chatGraph.graph.nodeDetailTitle')}</h2>
        </div>
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
        {/* 基本信息 */}
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-2">{t('chatGraph.graph.basicInfo')}</h3>
          <dl className="space-y-3">
            {nodeType === 'Character' && (
              <>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.characterName')}</dt>
                  <dd className="mt-1 text-sm text-gray-600">
                    {isEditing ? (
                      <input
                        className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.name || ''}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      />
                    ) : (
                      node.name
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('ui.status')}</dt>
                  <dd className="mt-1">
                    {isEditing ? (
                      <select
                        className="rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.status || 'alive'}
                        onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                      >
                        <option value="alive">{t('toolbox.graph.status.alive')}</option>
                        <option value="deceased">{t('toolbox.graph.status.deceased')}</option>
                        <option value="unknown">{t('toolbox.graph.status.unknown')}</option>
                      </select>
                    ) : (
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          node.status === 'alive'
                            ? 'bg-green-100 text-green-800'
                            : node.status === 'deceased'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {node.status === 'alive' ? t('toolbox.graph.status.alive') : node.status === 'deceased' ? t('toolbox.graph.status.deceased') : t('toolbox.graph.status.unknown')}
                      </span>
                    )}
                  </dd>
                </div>
                {(node.location || isEditing) && (
                  <div>
                    <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.location')}</dt>
                    <dd className="mt-1 text-sm text-gray-600">
                      {isEditing ? (
                        <input
                          className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                          value={editForm.location || ''}
                          onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                        />
                      ) : (
                        node.location
                      )}
                    </dd>
                  </div>
                )}
                {node.arc !== undefined && (
                  <div>
                    <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.arc')}</dt>
                    <dd className="mt-1">
                      <div className="flex items-center space-x-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-indigo-600 h-2 rounded-full"
                            style={{ width: `${Math.abs(node.arc)}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-600">{node.arc}</span>
                      </div>
                    </dd>
                  </div>
                )}
              </>
            )}

            {nodeType === 'PlotNode' && (
              <>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.plotTitle')}</dt>
                  <dd className="mt-1 text-sm text-gray-600">
                    {isEditing ? (
                      <input
                        className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.title || ''}
                        onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                      />
                    ) : (
                      node.title
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.sequence')}</dt>
                  <dd className="mt-1 text-sm text-gray-600">
                    {isEditing ? (
                      <input
                        type="number"
                        className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.sequence_number ?? 0}
                        onChange={(e) =>
                          setEditForm({ ...editForm, sequence_number: Number(e.target.value) })
                        }
                      />
                    ) : (
                      `#${node.sequence_number}`
                    )}
                  </dd>
                </div>
                {node.chapter !== null && (
                  <div>
                    <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.chapter')}</dt>
                    <dd className="mt-1 text-sm text-gray-600">{t('chatGraph.graph.chapterFormat', { n: node.chapter })}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.tension')}</dt>
                  <dd className="mt-1">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            node.tension_score > 70
                              ? 'bg-red-500'
                              : node.tension_score > 40
                              ? 'bg-yellow-500'
                              : 'bg-green-500'
                          }`}
                          style={{ width: `${node.tension_score}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-600">{node.tension_score}</span>
                    </div>
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.importance')}</dt>
                  <dd className="mt-1">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-indigo-600 h-2 rounded-full"
                          style={{ width: `${node.importance}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-600">{node.importance}</span>
                    </div>
                  </dd>
                </div>
              </>
            )}

            {nodeType === 'Story' && (
              <>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.storyName')}</dt>
                  <dd className="mt-1 text-sm text-gray-600">
                    {isEditing ? (
                      <input
                        className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.name || ''}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      />
                    ) : (
                      node.name
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('ui.status')}</dt>
                  <dd className="mt-1 text-sm text-gray-600">
                    {isEditing ? (
                      <select
                        className="rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.status || 'active'}
                        onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                      >
                        <option value="active">{t('toolbox.graph.storyStatus.active')}</option>
                        <option value="paused">{t('toolbox.graph.storyStatus.paused')}</option>
                        <option value="archived">{t('toolbox.graph.storyStatus.archived')}</option>
                      </select>
                    ) : (
                      <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-slate-100 text-slate-700">
                        {node.status || 'active'}
                      </span>
                    )}
                  </dd>
                </div>
                {(node.genre || isEditing) && (
                  <div>
                    <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.genre')}</dt>
                    <dd className="mt-1 text-sm text-gray-600">
                      {isEditing ? (
                        <input
                          className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                          value={editForm.genre || ''}
                          onChange={(e) => setEditForm({ ...editForm, genre: e.target.value })}
                        />
                      ) : (
                        node.genre || t('chatGraph.graph.unset')
                      )}
                    </dd>
                  </div>
                )}
              </>
            )}

            {isGenericNode && (
              <>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.name')}</dt>
                  <dd className="mt-1 text-sm text-gray-600">
                    {isEditing ? (
                      <input
                        className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.name || ''}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      />
                    ) : (
                      node.name
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.category')}</dt>
                  <dd className="mt-1 text-sm text-gray-600">
                    {isEditing ? (
                      <input
                        className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.category || ''}
                        onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                      />
                    ) : (
                      node.category || t('chatGraph.graph.unset')
                    )}
                  </dd>
                </div>
              </>
            )}

            {nodeType === 'WorldRule' && (
              <>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.ruleName')}</dt>
                  <dd className="mt-1 text-sm text-gray-600">
                    {isEditing ? (
                      <input
                        className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.name || ''}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      />
                    ) : (
                      node.name
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-900">{t('chatGraph.graph.category')}</dt>
                  <dd className="mt-1">
                    {isEditing ? (
                      <input
                        className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                        value={editForm.rule_type || ''}
                        onChange={(e) => setEditForm({ ...editForm, rule_type: e.target.value })}
                      />
                    ) : (
                      <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800">
                        {node.rule_type}
                      </span>
                    )}
                  </dd>
                </div>
              </>
            )}
          </dl>
        </div>

        {/* 描述 */}
        {(node.description || isEditing) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">{t('ui.description')}</h3>
            {isEditing ? (
              <textarea
                className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                rows={3}
                value={editForm.description || ''}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
              />
            ) : (
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{node.description}</p>
            )}
          </div>
        )}

        {nodeType === 'Story' && (node.tags?.length > 0 || isEditing) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">{t('chatGraph.graph.tags')}</h3>
            {isEditing ? (
              <input
                className="w-full rounded-md border border-gray-200 px-2 py-1 text-sm"
                value={(editForm.tags || []).join(', ')}
                onChange={(e) =>
                  setEditForm({
                    ...editForm,
                    tags: e.target.value
                      .split(',')
                      .map((item: string) => item.trim())
                      .filter(Boolean),
                  })
                }
                placeholder={t('chatGraph.graph.commaSeparated')}
              />
            ) : (
              <div className="flex flex-wrap gap-2">
                {node.tags?.map((tag: string, index: number) => (
                  <span
                    key={index}
                    className="inline-flex px-2 py-1 text-xs font-medium rounded-md bg-slate-100 text-slate-700"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 角色：性格标签 */}
        {nodeType === 'Character' && node.persona && node.persona.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">{t('chatGraph.graph.persona')}</h3>
            <div className="flex flex-wrap gap-2">
              {node.persona.map((trait: string, index: number) => (
                <span
                  key={index}
                  className="inline-flex px-2 py-1 text-xs font-medium rounded-md bg-purple-100 text-purple-800"
                >
                  {trait}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 角色：动机 */}
        {nodeType === 'Character' && node.motivations && node.motivations.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">{t('chatGraph.graph.motivations')}</h3>
            <ul className="space-y-1">
              {node.motivations.map((motivation: string, index: number) => (
                <li key={index} className="text-sm text-gray-600 flex items-start">
                  <Heart className="w-4 h-4 text-pink-500 mr-2 mt-0.5 flex-shrink-0" />
                  {motivation}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 角色：优缺点 */}
        {nodeType === 'Character' && (node.strengths?.length > 0 || node.flaws?.length > 0) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">{t('chatGraph.graph.traits')}</h3>
            <div className="space-y-2">
              {node.strengths && node.strengths.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-green-700">{t('chatGraph.graph.strengths')}</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {node.strengths.map((strength: string, index: number) => (
                      <span
                        key={index}
                        className="inline-flex px-2 py-0.5 text-xs rounded-md bg-green-100 text-green-800"
                      >
                        {strength}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {node.flaws && node.flaws.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-red-700">{t('chatGraph.graph.flaws')}</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {node.flaws.map((flaw: string, index: number) => (
                      <span
                        key={index}
                        className="inline-flex px-2 py-0.5 text-xs rounded-md bg-red-100 text-red-800"
                      >
                        {flaw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 情节：参与角色 */}
        {nodeType === 'PlotNode' && node.characters_involved && node.characters_involved.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">{t('chatGraph.graph.charactersInvolved')}</h3>
            <div className="flex flex-wrap gap-2">
              {node.characters_involved.map((charId: string, index: number) => {
                const char = characters.find((c) => c.character_id === charId);
                return (
                  <span
                    key={index}
                    className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-indigo-100 text-indigo-800"
                  >
                    <User className="w-3 h-3 mr-1" />
                    {char?.name || charId}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* 情节：地点 */}
        {nodeType === 'PlotNode' && node.locations && node.locations.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">{t('chatGraph.graph.locations')}</h3>
            <div className="flex flex-wrap gap-2">
              {node.locations.map((location: string, index: number) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md bg-cyan-100 text-cyan-800"
                >
                  <MapPin className="w-3 h-3 mr-1" />
                  {location}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 世界观规则：约束和示例 */}
        {nodeType === 'WorldRule' && (
          <>
            {node.constraints && node.constraints.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">{t('chatGraph.graph.constraints')}</h3>
                <ul className="space-y-1">
                  {node.constraints.map((constraint: string, index: number) => (
                    <li key={index} className="text-sm text-gray-600 flex items-start">
                      <span className="text-red-500 mr-2">•</span>
                      {constraint}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {node.examples && node.examples.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">{t('chatGraph.graph.examples')}</h3>
                <ul className="space-y-1">
                  {node.examples.map((example: string, index: number) => (
                    <li key={index} className="text-sm text-gray-600 flex items-start">
                      <span className="text-green-500 mr-2">•</span>
                      {example}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {/* 操作按钮 */}
        <div className="pt-4 border-t border-gray-200">
          <div className="flex space-x-2">
            <button
              className="flex-1 inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
              onClick={() => {
                if (isEditing) {
                  handleSave();
                } else {
                  setIsEditing(true);
                }
              }}
            >
              <Edit className="w-4 h-4 mr-2" />
              {isEditing ? t('common.save') : t('project.edit')}
            </button>
            <button
              className="flex-1 inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-300 rounded-lg hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
              onClick={handleDelete}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              {t('common.delete')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

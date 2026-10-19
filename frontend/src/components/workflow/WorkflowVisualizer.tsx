/**
 * 工作流可视化监控组件
 * 基于 React Flow 实现工作流节点的实时监控
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  NodeTypes,
  Edge,
  Node,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  EdgeTypes,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { WorkflowNode } from './WorkflowNode';
import { WorkflowDrawer } from './WorkflowDrawer';
import {
  NodeStatus,
  WorkflowNodeType,
  WorkflowNodeData,
  WorkflowEvent,
  NodeDetails,
} from './types';
import { API_BASE_URL } from '@/services/api';
import { useI18n, type TFunction } from '@/i18n';

// ==================== 节点类型注册 ====================

const nodeTypes: NodeTypes = {
  workflow: WorkflowNode as React.ComponentType<any>,
};

// ==================== 工作流拓扑定义 ====================

interface WorkflowVisualizerProps {
  workflowId?: string;
  onEvent?: (event: WorkflowEvent) => void;
  externalEvents?: WorkflowEvent[];
  className?: string;
}

// 初始节点定义
const createInitialNodes = (t: TFunction): Node<WorkflowNodeData>[] => [
  // 输入验证节点
  {
    id: 'input_validation',
    type: 'workflow',
    position: { x: 250, y: 0 },
    data: {
      id: 'input_validation',
      label: t('chatGraph.workflow.node.inputValidation'),
      description: t('chatGraph.workflow.node.inputValidationDesc'),
      status: NodeStatus.IDLE,
      nodeType: WorkflowNodeType.INPUT,
      icon: 'input',
    },
  },
  // 文本预处理节点
  {
    id: 'text_preprocessing',
    type: 'workflow',
    position: { x: 250, y: 150 },
    data: {
      id: 'text_preprocessing',
      label: t('chatGraph.workflow.node.textPreprocessing'),
      description: t('chatGraph.workflow.node.textPreprocessingDesc'),
      status: NodeStatus.IDLE,
      nodeType: WorkflowNodeType.PREPROCESSING,
      icon: 'preprocessing',
    },
  },
  // 故事大纲节点
  {
    id: 'story_outline',
    type: 'workflow',
    position: { x: 50, y: 300 },
    data: {
      id: 'story_outline',
      label: t('chatGraph.workflow.node.storyOutline'),
      description: t('chatGraph.workflow.node.storyOutlineDesc'),
      status: NodeStatus.IDLE,
      nodeType: WorkflowNodeType.PARALLEL,
      icon: 'parallel',
    },
  },
  // 人物小传节点
  {
    id: 'character_profiles',
    type: 'workflow',
    position: { x: 250, y: 300 },
    data: {
      id: 'character_profiles',
      label: t('chatGraph.workflow.node.characterProfiles'),
      description: t('chatGraph.workflow.node.characterProfilesDesc'),
      status: NodeStatus.IDLE,
      nodeType: WorkflowNodeType.PARALLEL,
      icon: 'parallel',
    },
  },
  // 大情节点节点
  {
    id: 'major_plot_points',
    type: 'workflow',
    position: { x: 450, y: 300 },
    data: {
      id: 'major_plot_points',
      label: t('chatGraph.workflow.node.majorPlotPoints'),
      description: t('chatGraph.workflow.node.majorPlotPointsDesc'),
      status: NodeStatus.IDLE,
      nodeType: WorkflowNodeType.PARALLEL,
      icon: 'parallel',
    },
  },
  // 详细情节点节点
  {
    id: 'detailed_plot_points',
    type: 'workflow',
    position: { x: 650, y: 300 },
    data: {
      id: 'detailed_plot_points',
      label: t('chatGraph.workflow.node.detailedPlotPoints'),
      description: t('chatGraph.workflow.node.detailedPlotPointsDesc'),
      status: NodeStatus.IDLE,
      nodeType: WorkflowNodeType.PARALLEL,
      icon: 'parallel',
    },
  },
  // 思维导图节点
  {
    id: 'mind_map',
    type: 'workflow',
    position: { x: 50, y: 450 },
    data: {
      id: 'mind_map',
      label: t('chatGraph.workflow.node.mindMap'),
      description: t('chatGraph.workflow.node.mindMapDesc'),
      status: NodeStatus.IDLE,
      nodeType: WorkflowNodeType.PARALLEL,
      icon: 'parallel',
    },
  },
  // 结果格式化节点
  {
    id: 'result_formatting',
    type: 'workflow',
    position: { x: 350, y: 450 },
    data: {
      id: 'result_formatting',
      label: t('chatGraph.workflow.node.resultFormatting'),
      description: t('chatGraph.workflow.node.resultFormattingDesc'),
      status: NodeStatus.IDLE,
      nodeType: WorkflowNodeType.OUTPUT,
      icon: 'output',
    },
  },
];

// 初始边定义
const initialEdges: Edge[] = [
  // 输入验证 -> 文本预处理
  {
    id: 'e-input-validation-preprocessing',
    source: 'input_validation',
    target: 'text_preprocessing',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
  // 文本预处理 -> 故事大纲
  {
    id: 'e-preprocessing-story-outline',
    source: 'text_preprocessing',
    target: 'story_outline',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
  // 文本预处理 -> 人物小传
  {
    id: 'e-preprocessing-character-profiles',
    source: 'text_preprocessing',
    target: 'character_profiles',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
  // 文本预处理 -> 大情节点
  {
    id: 'e-preprocessing-major-plot-points',
    source: 'text_preprocessing',
    target: 'major_plot_points',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
  // 文本预处理 -> 详细情节点
  {
    id: 'e-preprocessing-detailed-plot-points',
    source: 'text_preprocessing',
    target: 'detailed_plot_points',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
  // 故事大纲 -> 结果格式化
  {
    id: 'e-story-outline-formatting',
    source: 'story_outline',
    target: 'result_formatting',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
  // 人物小传 -> 结果格式化
  {
    id: 'e-character-profiles-formatting',
    source: 'character_profiles',
    target: 'result_formatting',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
  // 大情节点 -> 详细情节点
  {
    id: 'e-major-detailed-plot-points',
    source: 'major_plot_points',
    target: 'detailed_plot_points',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
  // 详细情节点 -> 结果格式化
  {
    id: 'e-detailed-plot-points-formatting',
    source: 'detailed_plot_points',
    target: 'result_formatting',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
  // 结果格式化 -> 思维导图
  {
    id: 'e-formatting-mind-map',
    source: 'result_formatting',
    target: 'mind_map',
    animated: false,
    style: { stroke: '#94a3b8', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  },
];

// ==================== 主组件 ====================

export const WorkflowVisualizer: React.FC<WorkflowVisualizerProps> = ({
  workflowId,
  onEvent,
  externalEvents,
  className = '',
}) => {
  const { t } = useI18n();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<WorkflowNodeData>>(createInitialNodes(t));
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node<WorkflowNodeData> | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [nodeDetails, setNodeDetails] = useState<NodeDetails | null>(null);
  const lastExternalIndexRef = useRef(0);

  // ==================== SSE 事件监听 ====================

  const applyWorkflowEvent = useCallback((data: WorkflowEvent | any) => {
    if (!externalEvents && onEvent) {
      onEvent(data);
    }
    if (data.event !== 'workflow_node_event') return;
    const { node_name, status, output_snapshot, error } = data.data || data.metadata || {};
    if (!node_name || !status) return;

    setNodes((prevNodes) =>
      prevNodes.map((node) => {
        if (node.id === node_name) {
          return {
            ...node,
            data: {
              ...node.data,
              status: status as NodeStatus,
              outputSnapshot: output_snapshot || node.data.outputSnapshot,
              error: error || node.data.error,
              startTime: node.data.startTime || new Date().toISOString(),
              endTime:
                status === NodeStatus.SUCCESS || status === NodeStatus.FAILED
                  ? new Date().toISOString()
                  : undefined,
              duration:
                status === NodeStatus.SUCCESS || status === NodeStatus.FAILED
                  ? node.data.startTime
                    ? new Date().getTime() - new Date(node.data.startTime).getTime()
                    : undefined
                  : undefined,
            },
          };
        }
        return node;
      })
    );

    if (status === NodeStatus.PROCESSING) {
      setEdges((prevEdges) =>
        prevEdges.map((edge) => {
          if (edge.target === node_name) {
            return { ...edge, animated: true, style: { stroke: '#eab308', strokeWidth: 3 } };
          }
          return edge;
        })
      );
    } else if (status === NodeStatus.SUCCESS) {
      setEdges((prevEdges) =>
        prevEdges.map((edge) => {
          if (edge.target === node_name) {
            return { ...edge, animated: false, style: { stroke: '#22c55e', strokeWidth: 3 } };
          }
          if (edge.source === node_name) {
            return { ...edge, animated: true, style: { stroke: '#eab308', strokeWidth: 3 } };
          }
          return edge;
        })
      );
    } else if (status === NodeStatus.FAILED) {
      setEdges((prevEdges) =>
        prevEdges.map((edge) => {
          if (edge.target === node_name) {
            return { ...edge, animated: false, style: { stroke: '#ef4444', strokeWidth: 3 } };
          }
          return edge;
        })
      );
    }
  }, [externalEvents, onEvent, setNodes, setEdges]);

  useEffect(() => {
    if (!workflowId) return;
    if (externalEvents) return;

    // 创建 EventSource 连接
    const eventSource = new EventSource(
      `${API_BASE_URL}/juben/plot-points-workflow/execute?workflow_id=${workflowId}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        applyWorkflowEvent(data);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [workflowId, externalEvents, applyWorkflowEvent]);

  useEffect(() => {
    if (!externalEvents || externalEvents.length === 0) {
      lastExternalIndexRef.current = 0;
      if (externalEvents) {
        setNodes(createInitialNodes(t));
        setEdges(initialEdges);
      }
      return;
    }
    const startIndex = lastExternalIndexRef.current;
    const slice = externalEvents.slice(startIndex);
    if (slice.length > 0) {
      slice.forEach((event) => applyWorkflowEvent(event));
      lastExternalIndexRef.current = externalEvents.length;
    }
  }, [externalEvents, applyWorkflowEvent]);

  // ==================== 节点点击处理 ====================

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node<WorkflowNodeData>) => {
    setSelectedNode(node);

    // 构建节点详情
    const details: NodeDetails = {
      nodeId: node.id,
      label: node.data.label,
      status: node.data.status,
      input: node.data.metadata?.input,
      output: node.data.metadata?.output,
      intermediateVariables: node.data.metadata?.variables,
      logs: node.data.metadata?.logs || [],
      error: node.data.error,
      duration: node.data.duration,
    };

    setNodeDetails(details);
    setIsDrawerOpen(true);
  }, []);

  // ==================== 连接处理 ====================

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, animated: true }, eds));
    },
    [setEdges]
  );

  // ==================== 状态统计 ====================

  const stats = useMemo(() => {
    const total = nodes.length;
    const completed = nodes.filter((n) => n.data.status === NodeStatus.SUCCESS).length;
    const failed = nodes.filter((n) => n.data.status === NodeStatus.FAILED).length;
    const processing = nodes.filter((n) => n.data.status === NodeStatus.PROCESSING).length;
    const progress = total > 0 ? Math.round((completed / total) * 100) : 0;

    return { total, completed, failed, processing, progress };
  }, [nodes]);

  // ==================== 渲染 ====================

  return (
    <div className={clsx('relative w-full h-full bg-gray-50 dark:bg-gray-900', className)}>
      {/* 状态统计栏 */}
      <div className="absolute top-4 left-4 z-10 bg-white dark:bg-gray-800 rounded-lg shadow-lg px-4 py-2 flex gap-6 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-gray-500">{t('chatGraph.workflow.progress')}</span>
          <span className="font-semibold text-blue-600">{stats.progress}%</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500"></span>
          <span className="text-gray-600 dark:text-gray-300">{t('chatGraph.workflow.completed')} {stats.completed}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></span>
          <span className="text-gray-600 dark:text-gray-300">{t('chatGraph.workflow.processing')} {stats.processing}</span>
        </div>
        {stats.failed > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            <span className="text-gray-600 dark:text-gray-300">{t('chatGraph.workflow.failed')} {stats.failed}</span>
          </div>
        )}
      </div>

      {/* React Flow 画布 */}
      <ReactFlow<Node<WorkflowNodeData>>
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background color="#94a3b8" gap={16} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const status = node.data.status;
            switch (status) {
              case NodeStatus.SUCCESS: return '#22c55e';
              case NodeStatus.PROCESSING: return '#eab308';
              case NodeStatus.FAILED: return '#ef4444';
              default: return '#94a3b8';
            }
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
      </ReactFlow>

      {/* 节点详情抽屉 */}
      <WorkflowDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        details={nodeDetails}
      />
    </div>
  );
};

// 辅助函数: clsx
function clsx(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

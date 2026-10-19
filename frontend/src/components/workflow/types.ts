/**
 * 工作流可视化类型定义
 */

import { Node, Edge } from '@xyflow/react';

// ==================== 工作流节点状态 ====================

export enum NodeStatus {
  IDLE = 'idle',           // 未开始
  WAITING = 'waiting',     // 等待执行
  PROCESSING = 'processing', // 执行中
  SUCCESS = 'success',     // 成功
  FAILED = 'failed',       // 失败
  SKIPPED = 'skipped'      // 跳过
}

// ==================== 工作流节点类型 ====================

export enum WorkflowNodeType {
  INPUT = 'input',              // 输入节点
  PREPROCESSING = 'preprocessing', // 预处理节点
  PARALLEL = 'parallel',        // 并行处理节点
  OUTPUT = 'output',            // 输出节点
  AGGREGATOR = 'aggregator'     // 聚合节点
}

// ==================== 自定义节点数据 ====================

export interface WorkflowNodeData {
  [key: string]: unknown;
  id: string;
  label: string;
  description: string;
  status: NodeStatus;
  nodeType: WorkflowNodeType;
  icon?: string;
  outputSnapshot?: string;
  error?: string;
  startTime?: string;
  endTime?: string;
  duration?: number; // 毫秒
  metadata?: Record<string, any>;
}

// ==================== React Flow 扩展类型 ====================

export type WorkflowNode = Node<WorkflowNodeData>;

export type WorkflowEdge = Edge;

// ==================== SSE 事件类型 ====================

export interface WorkflowNodeEvent {
  event_type: 'workflow_node_event';
  agent_source: string;
  timestamp: string;
  data: string;
  metadata: {
    workflow_id: string;
    node_name: string;
    status: NodeStatus;
    output_snapshot: string;
    error?: string;
  };
}

export interface WorkflowStateEvent {
  event_type: 'workflow_initialized' | 'workflow_completed' | 'workflow_paused' | 'workflow_error';
  workflow_id: string;
  message: string;
  timestamp: string;
  status?: string;
  final_result?: any;
  error?: string;
}

export type WorkflowEvent = WorkflowNodeEvent | WorkflowStateEvent;

// ==================== 工作流拓扑定义 ====================

export interface WorkflowTopology {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  layout: 'dagre' | 'elk' | 'manual';
}

// ==================== 节点详情 ====================

export interface NodeDetails {
  nodeId: string;
  label: string;
  status: NodeStatus;
  input?: any;
  output?: any;
  intermediateVariables?: Record<string, any>;
  logs?: string[];
  error?: string;
  duration?: number;
}

// ==================== 工作流执行状态 ====================

export interface WorkflowExecutionState {
  workflowId: string;
  status: 'initialized' | 'in_progress' | 'paused' | 'completed' | 'failed';
  currentStage: string;
  progress: number; // 0-100
  nodeStates: Map<string, NodeStatus>;
  startTime: string;
  endTime?: string;
}

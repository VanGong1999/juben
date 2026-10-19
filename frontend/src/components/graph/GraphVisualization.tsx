/**
 * 图数据库可视化组件
 * 使用 react-force-graph：补全推断边 + 收紧力导向，避免「中心一团 / 外围散点」
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { NodeObject, LinkObject } from 'react-force-graph-2d';
import {
  forceRadial,
  forceX,
  forceY,
  forceManyBody,
  forceCenter,
  forceCollide,
} from 'd3-force';
import { Info, X, Link2 } from 'lucide-react';
import { useGraphStore } from '@/store/graphStore';
import { GraphToolbar } from './GraphToolbar';
import { GraphNodeDetail } from './GraphNodeDetail';
import { GraphStatistics } from './GraphStatistics';
import { GraphFilter } from './GraphFilter';
import type { NodeType, RelationType } from '@/services/graphService';
import { Loading } from '@/components/common';
import { enrichGraphRelationships, computeNodeDegrees } from '@/utils/graphEnrichment';
import { useI18n } from '@/i18n';

interface GraphVisualizationProps {
  className?: string;
  height?: string | number;
}

const NODE_COLORS: Record<NodeType, string> = {
  Story: '#475569',
  Character: '#6366f1',
  PlotNode: '#10b981',
  WorldRule: '#f59e0b',
  Location: '#8b5cf6',
  Item: '#ec4899',
  Conflict: '#ef4444',
  Theme: '#06b6d4',
  Motivation: '#f97316',
};

const NODE_SIZES: Record<NodeType, number> = {
  Story: 12,
  Character: 8,
  PlotNode: 7,
  WorldRule: 6,
  Location: 5,
  Item: 4,
  Conflict: 6,
  Theme: 5,
  Motivation: 5,
};

const LINK_COLORS: Record<RelationType, string> = {
  SOCIAL_BOND: '#6366f1',
  FAMILY_RELATION: '#7c3aed',
  ROMANTIC_RELATION: '#ec4899',
  INFLUENCES: '#10b981',
  LEADS_TO: '#22c55e',
  NEXT: '#f59e0b',
  RESOLVES: '#0ea5e9',
  COMPLICATES: '#f97316',
  INVOLVED_IN: '#8b5cf6',
  DRIVEN_BY: '#ec4899',
  CONTAINS: '#94a3b8',
  VIOLATES: '#ef4444',
  ENFORCES: '#f59e0b',
  LOCATED_IN: '#06b6d4',
  LOCATED_AT: '#06b6d4',
  OWNS: '#f97316',
  PART_OF: '#14b8a6',
  REPRESENTS: '#a855f7',
  OPPOSES: '#f43f5e',
  SUPPORTS: '#22c55e',
};

const NODE_LABEL_KEYS: Record<NodeType, string> = {
  Story: 'chatGraph.graph.nodeType.story',
  Character: 'chatGraph.graph.nodeType.character',
  PlotNode: 'chatGraph.graph.nodeType.plotNode',
  WorldRule: 'chatGraph.graph.nodeType.worldRule',
  Location: 'chatGraph.graph.nodeType.location',
  Item: 'chatGraph.graph.nodeType.item',
  Conflict: 'chatGraph.graph.nodeType.conflict',
  Theme: 'chatGraph.graph.nodeType.theme',
  Motivation: 'chatGraph.graph.nodeType.motivation',
};

const RELATION_LABEL_KEYS: Record<RelationType, string> = {
  SOCIAL_BOND: 'chatGraph.graph.relation.socialBond',
  FAMILY_RELATION: 'chatGraph.graph.relation.familyRelation',
  ROMANTIC_RELATION: 'chatGraph.graph.relation.romanticRelation',
  INFLUENCES: 'chatGraph.graph.relation.influences',
  LEADS_TO: 'chatGraph.graph.relation.leadsTo',
  NEXT: 'chatGraph.graph.relation.next',
  RESOLVES: 'chatGraph.graph.relation.resolves',
  COMPLICATES: 'chatGraph.graph.relation.complicates',
  INVOLVED_IN: 'chatGraph.graph.relation.involvedIn',
  DRIVEN_BY: 'chatGraph.graph.relation.drivenBy',
  CONTAINS: 'chatGraph.graph.relation.contains',
  VIOLATES: 'chatGraph.graph.relation.violates',
  ENFORCES: 'chatGraph.graph.relation.enforces',
  LOCATED_IN: 'chatGraph.graph.relation.locatedIn',
  LOCATED_AT: 'chatGraph.graph.relation.locatedAt',
  OWNS: 'chatGraph.graph.relation.owns',
  PART_OF: 'chatGraph.graph.relation.partOf',
  REPRESENTS: 'chatGraph.graph.relation.represents',
  OPPOSES: 'chatGraph.graph.relation.opposes',
  SUPPORTS: 'chatGraph.graph.relation.supports',
};

const DASHED_RELATIONS = new Set<RelationType>(['OPPOSES', 'VIOLATES', 'COMPLICATES']);
const THICK_RELATIONS = new Set<RelationType>([
  'SOCIAL_BOND',
  'FAMILY_RELATION',
  'ROMANTIC_RELATION',
  'INVOLVED_IN',
  'DRIVEN_BY',
]);
const STRUCTURAL_RELATIONS = new Set<RelationType>(['CONTAINS']);

export function GraphVisualization({ className = '', height = '100%' }: GraphVisualizationProps) {
  const { t } = useI18n();
  const graphRef = useRef<any>();
  const containerRef = useRef<HTMLDivElement>(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [showLegend, setShowLegend] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [hoverNodeId, setHoverNodeId] = useState<string | null>(null);
  const [hideStructural, setHideStructural] = useState(false);
  const [dims, setDims] = useState({ w: 800, h: 600 });

  const {
    nodes,
    relationships,
    statistics,
    loading,
    error,
    selectedNodeId,
    filter,
    viewMode,
    setSelectedNodeId,
    loadStoryElements,
    loadStatistics,
    setViewMode,
  } = useGraphStore();

  // 稳定引用的图数据（避免每帧 new 对象重置仿真）
  const graphData = useMemo(() => {
    const filteredNodes = nodes.filter((node) => {
      if (filter.nodeTypes.length > 0 && !filter.nodeTypes.includes(node.type as NodeType)) {
        return false;
      }
      if (filter.searchQuery) {
        const query = filter.searchQuery.toLowerCase();
        return (
          node.properties.name?.toLowerCase().includes(query) ||
          node.properties.title?.toLowerCase().includes(query) ||
          node.properties.description?.toLowerCase().includes(query)
        );
      }
      return true;
    });

    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const baseLinks = relationships.filter((link) => {
      if (filter.relationTypes.length > 0 && !filter.relationTypes.includes(link.type as RelationType)) {
        return false;
      }
      return nodeIds.has(link.source) && nodeIds.has(link.target);
    });

    const enriched = enrichGraphRelationships(filteredNodes, baseLinks).filter(
      (link) => nodeIds.has(link.source) && nodeIds.has(link.target)
    );

    const visibleLinks = hideStructural
      ? enriched.filter((l) => !STRUCTURAL_RELATIONS.has(l.type as RelationType))
      : enriched;

    const degrees = computeNodeDegrees(
      filteredNodes.map((n) => n.id),
      visibleLinks
    );

    const nodesData: NodeObject[] = filteredNodes.map((node) => {
      const deg = degrees.get(node.id) || 0;
      const base = NODE_SIZES[node.type as NodeType] || 10;
      return {
        id: node.id,
        name: node.properties.name || node.properties.title || node.id,
        type: node.type,
        ...node.properties,
        color: NODE_COLORS[node.type as NodeType] || '#94a3b8',
        size: base + Math.min(deg * 0.4, 3),
        degree: deg,
      };
    });

    const linksData: LinkObject[] = visibleLinks.map((link) => ({
      id: link.id,
      source: link.source,
      target: link.target,
      type: link.type,
      inferred: Boolean(link.properties?.inferred),
      color: LINK_COLORS[link.type as RelationType] || '#94a3b8',
      ...link.properties,
    }));

    return { nodes: nodesData, links: linksData };
  }, [nodes, relationships, filter, hideStructural]);

  const linkStats = useMemo(
    () => ({
      linkCount: graphData.links.length,
      inferredCount: graphData.links.filter((l: any) => l.inferred).length,
    }),
    [graphData]
  );

  // 邻接表：悬停高亮
  const neighborMap = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const link of graphData.links as any[]) {
      const s = typeof link.source === 'object' ? link.source.id : link.source;
      const t = typeof link.target === 'object' ? link.target.id : link.target;
      if (!map.has(s)) map.set(s, new Set());
      if (!map.has(t)) map.set(t, new Set());
      map.get(s)!.add(t);
      map.get(t)!.add(s);
    }
    return map;
  }, [graphData]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width, height: h } = entry.contentRect;
      if (width > 0 && h > 0) setDims({ w: Math.floor(width), h: Math.floor(h) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!selectedNodeId) return;
    if (!graphRef.current) return;
    const found = (graphData.nodes as any[]).find((n) => n.id === selectedNodeId);
    if (found) {
      setDetailOpen(true);
      graphRef.current.centerAt(found.x || 0, found.y || 0, 400);
      graphRef.current.zoom(1.5, 400);
      setZoom(1.5);
    }
  }, [selectedNodeId, graphData.nodes]);

  const handleNodeClick = useCallback(
    (node: any) => {
      setSelectedNodeId(node.id);
      setDetailOpen(true);
      if (graphRef.current) {
        graphRef.current.centerAt(node.x, node.y, 300);
        graphRef.current.zoom(1.5, 300);
        setZoom(1.5);
      }
    },
    [setSelectedNodeId]
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNodeId(null);
    setDetailOpen(false);
    setHoverNodeId(null);
  }, [setSelectedNodeId]);

  const handleRefresh = useCallback(async () => {
    const { currentStoryId } = useGraphStore.getState();
    if (currentStoryId) {
      await loadStoryElements(currentStoryId);
      await loadStatistics(currentStoryId);
    }
  }, [loadStoryElements, loadStatistics]);

  const handleExportImage = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.downloadImage('graph', 'image/png', {
        backgroundColor: '#ffffff',
        pixelRatio: 2,
      });
    }
  }, []);

  const handleResetView = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 48);
      setZoom(1);
    }
  }, []);

  const handleZoomIn = useCallback(() => {
    const nextZoom = Math.min(zoom + 0.2, 3);
    setZoom(nextZoom);
    graphRef.current?.zoom(nextZoom, 200);
  }, [zoom]);

  const handleZoomOut = useCallback(() => {
    const nextZoom = Math.max(zoom - 0.2, 0.2);
    setZoom(nextZoom);
    graphRef.current?.zoom(nextZoom, 200);
  }, [zoom]);

  useEffect(() => {
    const { currentStoryId } = useGraphStore.getState();
    if (currentStoryId) {
      loadStoryElements(currentStoryId);
      loadStatistics(currentStoryId);
    }
  }, [loadStoryElements, loadStatistics]);

  // 力导向：向心 + 碰撞 + 适度斥力，连线偏短，避免大片空白
  useEffect(() => {
    const g = graphRef.current;
    if (!g) return;

    g.d3Force('center', forceCenter(0, 0).strength(0.08));
    g.d3Force(
      'charge',
      forceManyBody()
        .strength((node: any) => {
          if (node.type === 'Story') return -80;
          if (node.type === 'Character' || node.type === 'PlotNode') return -220;
          return -120;
        })
        .distanceMax(420)
    );
    g.d3Force(
      'collide',
      forceCollide()
        .radius((node: any) => Math.sqrt(node.size || 6) * 1.8 + 10)
        .strength(0.9)
        .iterations(2)
    );

    const linkForce = g.d3Force('link');
    if (linkForce) {
      if (typeof linkForce.distance === 'function') {
        linkForce.distance((link: any) => {
          if (STRUCTURAL_RELATIONS.has(link.type)) return 64;
          if (THICK_RELATIONS.has(link.type)) return 48;
          return 42;
        });
      }
      if (typeof linkForce.strength === 'function') {
        linkForce.strength((link: any) =>
          STRUCTURAL_RELATIONS.has(link.type) ? 0.22 : 0.9
        );
      }
      if (typeof linkForce.iterations === 'function') {
        linkForce.iterations(2);
      }
    }

    g.d3ReheatSimulation();
    const t = window.setTimeout(() => {
      try {
        g.zoomToFit(500, 72);
      } catch {
        /* ignore */
      }
    }, 700);
    return () => window.clearTimeout(t);
  }, [graphData.nodes.length, graphData.links.length, hideStructural, dims.w, dims.h]);

  // 视图模式
  useEffect(() => {
    const g = graphRef.current;
    if (!g) return;

    if (viewMode === 'force') {
      g.d3Force('radial', null);
      g.d3Force('x', null);
      g.d3Force('y', null);
    } else if (viewMode === 'radial') {
      g.d3Force(
        'radial',
        forceRadial((node: any) => {
          if (node.type === 'Story') return 0;
          if (node.type === 'PlotNode') return 90;
          if (node.type === 'Character') return 160;
          return 240;
        }, 0, 0).strength(0.75)
      );
    } else if (viewMode === 'circle') {
      g.d3Force('radial', forceRadial(200, 0, 0).strength(0.9));
    } else if (viewMode === 'tree') {
      g.d3Force(
        'x',
        forceX((node: any) => {
          if (node.type === 'Character') return -180;
          if (node.type === 'PlotNode') return 0;
          if (node.type === 'Story') return 0;
          return 180;
        }).strength(0.55)
      );
      g.d3Force(
        'y',
        forceY((node: any) => {
          if (node.type === 'Story') return -120;
          if (node.type === 'PlotNode') return 0;
          return node.type === 'Character' ? -40 : 80;
        }).strength(0.4)
      );
    }

    g.d3ReheatSimulation();
  }, [viewMode]);

  const isHighlighted = useCallback(
    (nodeId: string) => {
      if (!hoverNodeId && !selectedNodeId) return true;
      const focus = hoverNodeId || selectedNodeId;
      if (!focus) return true;
      if (nodeId === focus) return true;
      return neighborMap.get(focus)?.has(nodeId) || false;
    },
    [hoverNodeId, selectedNodeId, neighborMap]
  );

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-red-50 ${className}`} style={{ height }}>
        <div className="text-center">
          <h3 className="mt-2 text-sm font-medium text-red-800">{t('chatGraph.graph.loadFailed')}</h3>
          <p className="mt-1 text-sm text-red-600">{error}</p>
          <button
            onClick={handleRefresh}
            className="mt-4 inline-flex items-center px-4 py-2 rounded-md text-sm font-medium text-red-700 bg-red-100 hover:bg-red-200"
          >
            {t('common.retry')}
          </button>
        </div>
      </div>
    );
  }

  if (loading && nodes.length === 0) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <Loading size="lg" text={t('ui.loading')} />
      </div>
    );
  }

  if (nodes.length === 0 && !loading) {
    return (
      <div className={`flex items-center justify-center bg-gray-50 ${className}`} style={{ height }}>
        <div className="text-center">
          <h3 className="mt-2 text-sm font-medium text-gray-900">{t('empty.noData')}</h3>
          <p className="mt-1 text-sm text-gray-500">{t('chatGraph.graph.selectStoryOrCreate')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative flex flex-col ${className}`} style={{ height }}>
      <GraphToolbar
        onRefresh={handleRefresh}
        onExportImage={handleExportImage}
        onResetView={handleResetView}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onOpenFilter={() => setFilterOpen(true)}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        loading={loading}
        zoom={zoom}
      />

      {filterOpen && <GraphFilter onClose={() => setFilterOpen(false)} />}

      <div ref={containerRef} className="flex-1 relative min-h-0 bg-[#fafbfc]">
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          width={dims.w}
          height={dims.h}
          backgroundColor="#fafbfc"
          nodeLabel={(node: any) =>
            `${t(NODE_LABEL_KEYS[node.type as NodeType] || node.type)} · ${node.name}`
          }
          nodeColor={(node: any) => node.color}
          nodeVal={(node: any) => node.size || 6}
          nodeRelSize={3.5}
          linkColor={(link: any) => {
            const base = link.color || '#94a3b8';
            if (link.inferred && STRUCTURAL_RELATIONS.has(link.type)) {
              return 'rgba(148,163,184,0.35)';
            }
            return link.inferred ? `${base}aa` : base;
          }}
          linkWidth={(link: any) => {
            if (STRUCTURAL_RELATIONS.has(link.type)) return 0.8;
            if (THICK_RELATIONS.has(link.type as RelationType)) return 2.8;
            return 1.8;
          }}
          linkLineDash={(link: any) => {
            if (link.inferred && STRUCTURAL_RELATIONS.has(link.type)) return [2, 4];
            if (DASHED_RELATIONS.has(link.type as RelationType)) return [5, 3];
            return null;
          }}
          linkDirectionalArrowLength={(link: any) =>
            STRUCTURAL_RELATIONS.has(link.type) ? 0 : 5
          }
          linkDirectionalArrowRelPos={0.92}
          linkDirectionalArrowColor={(link: any) => link.color || '#94a3b8'}
          linkLabel={(link: any) => {
            const label = t(RELATION_LABEL_KEYS[link.type as RelationType] || link.type);
            return link.inferred ? `${label}${t('chatGraph.graph.inferredSuffix')}` : label;
          }}
          linkCurvature={(link: any) => (STRUCTURAL_RELATIONS.has(link.type) ? 0.05 : 0.12)}
          linkDirectionalParticles={(link: any) =>
            THICK_RELATIONS.has(link.type as RelationType) ? 1 : 0
          }
          linkDirectionalParticleWidth={2}
          linkVisibility={() => true}
          nodeCanvasObjectMode={() => 'after'}
          nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const highlighted = isHighlighted(node.id);
            const r = Math.sqrt(Math.max(0, node.size || 6)) * 0.95;

            if (!highlighted) {
              ctx.beginPath();
              ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
              ctx.fillStyle = 'rgba(241,245,249,0.55)';
              ctx.fill();
            }

            // 标签：放大或高亮/高连接度时显示，减少重叠
            const showLabel =
              globalScale > 1.05 ||
              node.degree >= 4 ||
              node.type === 'Story' ||
              node.type === 'Character' ||
              node.id === selectedNodeId ||
              node.id === hoverNodeId;

            if (!showLabel || !node.name) return;

            const fontSize = Math.max(7, Math.min(12, 11 / globalScale));
            ctx.font = `${node.type === 'Story' || node.type === 'Character' ? 600 : 400} ${fontSize}px ui-sans-serif, system-ui, sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            const label = String(node.name).slice(0, 14);
            const tw = ctx.measureText(label).width;
            const pad = 2;
            ctx.fillStyle = highlighted ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0.55)';
            ctx.fillRect(node.x - tw / 2 - pad, node.y + r + 1, tw + pad * 2, fontSize + 3);
            ctx.fillStyle = highlighted ? '#334155' : '#94a3b8';
            ctx.fillText(label, node.x, node.y + r + 2);
          }}
          onNodeClick={handleNodeClick}
          onNodeHover={(node: any) => setHoverNodeId(node?.id || null)}
          onBackgroundClick={handleBackgroundClick}
          cooldownTicks={180}
          d3AlphaDecay={0.022}
          d3VelocityDecay={0.35}
          warmupTicks={40}
          enableNodeDrag
          enableZoomInteraction
          enablePanInteraction
        />

        <div className="absolute top-2 left-2 z-10 flex items-center gap-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/90 border border-pearl-line text-[11px] text-ink-muted shadow-sm">
            <Link2 className="w-3.5 h-3.5" />
            {t('chatGraph.graph.counts', { nodes: graphData.nodes.length, links: linkStats.linkCount })}
            {linkStats.inferredCount > 0 ? t('chatGraph.graph.inferredCount', { count: linkStats.inferredCount }) : ''}
          </div>
          <button
            type="button"
            onClick={() => setHideStructural((v) => !v)}
            className={`px-2.5 py-1.5 rounded-lg border text-[11px] shadow-sm transition-colors ${
              hideStructural
                ? 'bg-ink text-white border-ink'
                : 'bg-white/90 border-pearl-line text-ink-muted hover:bg-white'
            }`}
            title={t('chatGraph.graph.hideStructuralTitle')}
          >
            {hideStructural ? t('chatGraph.graph.showStructural') : t('chatGraph.graph.hideStructural')}
          </button>
        </div>

        <button
          type="button"
          onClick={() => setShowLegend((v) => !v)}
          className="absolute top-2 right-2 z-10 inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/90 border border-pearl-line text-xs font-medium text-ink shadow-sm hover:bg-white transition-colors"
        >
          <Info className="w-3.5 h-3.5" />
          {t('chatGraph.graph.legend')}
        </button>

        {showLegend && (
          <div className="absolute top-11 right-2 z-10 w-64 max-h-[70%] overflow-y-auto rounded-xl bg-white/95 backdrop-blur border border-pearl-line shadow-lg p-3 text-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-ink">{t('chatGraph.graph.legend')}</span>
              <button
                type="button"
                onClick={() => setShowLegend(false)}
                className="p-0.5 rounded hover:bg-pearl-soft text-ink-muted"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="font-medium text-ink-faint uppercase tracking-wider mb-1">{t('chatGraph.graph.nodes')}</div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-1.5 mb-3">
              {(Object.keys(NODE_LABEL_KEYS) as NodeType[]).map((nt) => (
                <div key={nt} className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ background: NODE_COLORS[nt] || '#94a3b8' }}
                  />
                  <span className="text-ink-muted truncate">{t(NODE_LABEL_KEYS[nt])}</span>
                </div>
              ))}
            </div>

            <div className="font-medium text-ink-faint uppercase tracking-wider mb-1">{t('chatGraph.graph.relations')}</div>
            <div className="space-y-1">
              {(Object.keys(RELATION_LABEL_KEYS) as RelationType[]).map((rt) => (
                <div key={rt} className="flex items-center gap-1.5">
                  <span
                    className="inline-block w-5 shrink-0"
                    style={{
                      height: 2,
                      background: DASHED_RELATIONS.has(rt)
                        ? `repeating-linear-gradient(90deg, ${LINK_COLORS[rt] || '#cbd5e1'} 0 4px, transparent 4px 7px)`
                        : LINK_COLORS[rt] || '#cbd5e1',
                    }}
                  />
                  <span className="text-ink-muted truncate">{t(RELATION_LABEL_KEYS[rt])}</span>
                </div>
              ))}
            </div>
            <p className="mt-2 text-[10px] text-ink-faint leading-relaxed">
              {t('chatGraph.graph.legendHint')}
            </p>
          </div>
        )}
      </div>

      {statistics && <GraphStatistics statistics={statistics} />}

      {detailOpen && selectedNodeId && (
        <GraphNodeDetail nodeId={selectedNodeId} onClose={() => setDetailOpen(false)} />
      )}
    </div>
  );
}

export default GraphVisualization;

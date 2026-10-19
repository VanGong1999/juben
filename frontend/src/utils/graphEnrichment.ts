/**
 * 从节点属性推断补全关系边，避免大量孤立节点把力导向撑散。
 */

import type { GraphNode, GraphRelationship, RelationType } from '@/services/graphService';

function nodeName(node: GraphNode): string {
  const p = node.properties || {};
  return String(p.name || p.title || p.label || '').trim();
}

function norm(s: string): string {
  return s.trim().toLowerCase().replace(/\s+/g, '');
}

function makeId(type: string, source: string, target: string): string {
  return `inferred:${type}:${source}->${target}`;
}

function addEdge(
  edges: GraphRelationship[],
  seen: Set<string>,
  type: RelationType,
  source: string,
  target: string,
  properties: Record<string, any> = {}
) {
  if (!source || !target || source === target) return;
  const key = `${type}|${source}|${target}`;
  const rev = `${type}|${target}|${source}`;
  if (seen.has(key) || seen.has(rev)) return;
  seen.add(key);
  edges.push({
    id: makeId(type, source, target),
    type,
    source,
    target,
    properties: { ...properties, inferred: true },
  });
}

/**
 * 基于已有关系 + 节点属性（角色动机、情节点参与者/地点/主题等）补全关系。
 */
export function enrichGraphRelationships(
  nodes: GraphNode[],
  relationships: GraphRelationship[]
): GraphRelationship[] {
  const edges = [...relationships];
  const seen = new Set<string>();
  for (const r of relationships) {
    if (r.source && r.target) {
      seen.add(`${r.type}|${r.source}|${r.target}`);
    }
  }

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const byTypeName = new Map<string, Map<string, GraphNode>>();
  for (const n of nodes) {
    const t = n.type || 'Unknown';
    if (!byTypeName.has(t)) byTypeName.set(t, new Map());
    const name = nodeName(n);
    if (name) byTypeName.get(t)!.set(norm(name), n);
  }

  const findByName = (type: string, name: string): GraphNode | undefined => {
    if (!name) return undefined;
    return byTypeName.get(type)?.get(norm(name));
  };

  const story =
    nodes.find((n) => n.type === 'Story') ||
    nodes.find((n) => (n.labels || []).includes('Story'));

  // Story CONTAINS 所有实体，保证至少连到中心
  if (story) {
    for (const n of nodes) {
      if (n.id === story.id) continue;
      addEdge(edges, seen, 'CONTAINS', story.id, n.id, { reason: 'story_contains' });
    }
  }

  // Character.motivations → Motivation
  for (const n of nodes) {
    if (n.type !== 'Character') continue;
    const mots = (n.properties?.motivations || []) as string[];
    for (const m of mots) {
      const target = findByName('Motivation', m);
      if (target) addEdge(edges, seen, 'DRIVEN_BY', n.id, target.id, { reason: 'character_motivation' });
    }
    const locName = n.properties?.location;
    if (typeof locName === 'string' && locName) {
      const loc = findByName('Location', locName);
      if (loc) addEdge(edges, seen, 'LOCATED_IN', n.id, loc.id, { reason: 'character_location' });
    }
  }

  // PlotNode 属性 → 角色 / 地点 / 主题 / 冲突
  for (const n of nodes) {
    if (n.type !== 'PlotNode') continue;
    const p = n.properties || {};
    for (const name of (p.characters_involved || []) as string[]) {
      const char = findByName('Character', name);
      if (char) addEdge(edges, seen, 'INVOLVED_IN', char.id, n.id, { reason: 'plot_cast' });
    }
    for (const name of (p.locations || []) as string[]) {
      const loc = findByName('Location', name);
      if (loc) addEdge(edges, seen, 'LOCATED_IN', n.id, loc.id, { reason: 'plot_location' });
    }
    for (const name of (p.themes || []) as string[]) {
      const theme = findByName('Theme', name);
      if (theme) addEdge(edges, seen, 'REPRESENTS', n.id, theme.id, { reason: 'plot_theme' });
    }
    for (const name of (p.conflicts || []) as string[]) {
      const conflict = findByName('Conflict', name);
      if (conflict) addEdge(edges, seen, 'COMPLICATES', conflict.id, n.id, { reason: 'plot_conflict' });
    }
  }

  // 同名 Theme ↔ Conflict 弱关联（部分抽取会重复命名）
  for (const theme of nodes.filter((n) => n.type === 'Theme')) {
    const conflict = findByName('Conflict', nodeName(theme));
    if (conflict) {
      addEdge(edges, seen, 'REPRESENTS', conflict.id, theme.id, { reason: 'theme_conflict_alias' });
    }
  }

  // 仍孤立的节点：挂到度最高的同类型邻居或 Story（已 COVER）
  void byId;
  return edges;
}

/** 计算节点度数，便于布局与标签优先级 */
export function computeNodeDegrees(
  nodeIds: string[],
  relationships: GraphRelationship[]
): Map<string, number> {
  const deg = new Map<string, number>();
  for (const id of nodeIds) deg.set(id, 0);
  for (const r of relationships) {
    deg.set(r.source, (deg.get(r.source) || 0) + 1);
    deg.set(r.target, (deg.get(r.target) || 0) + 1);
  }
  return deg;
}

"""
从节点属性推断补全关系边，减少孤立节点。
与前端 frontend/src/utils/graphEnrichment.ts 逻辑对齐。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


def _norm(s: Any) -> str:
    return str(s or "").strip().lower().replace(" ", "")


def _node_name(node: Dict[str, Any]) -> str:
    props = node.get("properties") or node
    return str(props.get("name") or props.get("title") or props.get("label") or "").strip()


def _add_edge(
    edges: List[Dict[str, Any]],
    seen: Set[str],
    rel_type: str,
    source: str,
    target: str,
    properties: Optional[Dict[str, Any]] = None,
) -> None:
    if not source or not target or source == target:
        return
    key = f"{rel_type}|{source}|{target}"
    rev = f"{rel_type}|{target}|{source}"
    if key in seen or rev in seen:
        return
    seen.add(key)
    edges.append(
        {
            "id": f"inferred:{rel_type}:{source}->{target}",
            "type": rel_type,
            "source": source,
            "target": target,
            "properties": {**(properties or {}), "inferred": True},
        }
    )


def enrich_graph_relationships(
    nodes: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    edges = list(relationships or [])
    seen: Set[str] = set()
    for r in edges:
        src, tgt, typ = r.get("source"), r.get("target"), r.get("type")
        if src and tgt and typ:
            seen.add(f"{typ}|{src}|{tgt}")

    by_type_name: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for n in nodes or []:
        t = n.get("type") or "Unknown"
        nm = _norm(_node_name(n))
        if not nm:
            continue
        by_type_name.setdefault(t, {})[nm] = n

    def find(type_name: str, name: str) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        return by_type_name.get(type_name, {}).get(_norm(name))

    story = next((n for n in nodes if n.get("type") == "Story"), None)
    if story:
        sid = story.get("id")
        for n in nodes:
            nid = n.get("id")
            if nid and nid != sid:
                _add_edge(edges, seen, "CONTAINS", sid, nid, {"reason": "story_contains"})

    for n in nodes:
        if n.get("type") != "Character":
            continue
        props = n.get("properties") or {}
        for m in props.get("motivations") or []:
            target = find("Motivation", m)
            if target:
                _add_edge(
                    edges,
                    seen,
                    "DRIVEN_BY",
                    n["id"],
                    target["id"],
                    {"reason": "character_motivation"},
                )
        loc_name = props.get("location")
        if isinstance(loc_name, str) and loc_name:
            loc = find("Location", loc_name)
            if loc:
                _add_edge(
                    edges,
                    seen,
                    "LOCATED_IN",
                    n["id"],
                    loc["id"],
                    {"reason": "character_location"},
                )

    for n in nodes:
        if n.get("type") != "PlotNode":
            continue
        props = n.get("properties") or {}
        for cname in props.get("characters_involved") or []:
            char = find("Character", cname)
            if char:
                _add_edge(
                    edges,
                    seen,
                    "INVOLVED_IN",
                    char["id"],
                    n["id"],
                    {"reason": "plot_cast"},
                )
        for loc_name in props.get("locations") or []:
            loc = find("Location", loc_name)
            if loc:
                _add_edge(
                    edges,
                    seen,
                    "LOCATED_IN",
                    n["id"],
                    loc["id"],
                    {"reason": "plot_location"},
                )
        for tname in props.get("themes") or []:
            theme = find("Theme", tname)
            if theme:
                _add_edge(
                    edges,
                    seen,
                    "REPRESENTS",
                    n["id"],
                    theme["id"],
                    {"reason": "plot_theme"},
                )
        for cname in props.get("conflicts") or []:
            conflict = find("Conflict", cname)
            if conflict:
                _add_edge(
                    edges,
                    seen,
                    "COMPLICATES",
                    conflict["id"],
                    n["id"],
                    {"reason": "plot_conflict"},
                )

    return edges

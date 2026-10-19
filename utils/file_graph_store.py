"""
文件图谱存储 — Neo4j 不可用时的生产级兜底

路径: data/knowledge/graph/{story_id}.json
与 GraphDBManager 关键 API 方法同名，供 get_graph_manager 回退。
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GRAPH_ROOT = PROJECT_ROOT / "data" / "knowledge" / "graph"

DEMO_STORY_ID = "demo_urban_comeback"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _node_id(props: Dict[str, Any]) -> str:
    for k in ("character_id", "plot_id", "rule_id", "node_id", "story_id", "id"):
        if props.get(k):
            return str(props[k])
    return str(props.get("name") or props.get("title") or uuid4().hex[:10])


class FileGraphStore:
    """JSON 文件图谱：短剧创作可用的人物 / 情节点 / 关系网络。"""

    backend = "file"

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root else GRAPH_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._reviews_path = self.root / "_review_queue.json"
        self.driver = None  # 兼容 Neo4j 检查

    async def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if not any(self.root.glob("*.json")) or not (self.root / f"{DEMO_STORY_ID}.json").exists():
            self._seed_demo()
        logger.info("[file_graph] ready at %s", self.root)

    async def close(self) -> None:
        return None

    async def verify_connectivity(self) -> bool:
        return True

    def _story_path(self, story_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in story_id)
        return self.root / f"{safe}.json"

    def _load_story(self, story_id: str) -> Dict[str, Any]:
        path = self._story_path(story_id)
        if not path.exists():
            return {
                "story": None,
                "nodes": [],
                "relationships": [],
            }
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save_story(self, story_id: str, data: Dict[str, Any]) -> None:
        path = self._story_path(story_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)

    def _load_reviews(self) -> List[Dict[str, Any]]:
        if not self._reviews_path.exists():
            return []
        with self._reviews_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save_reviews(self, items: List[Dict[str, Any]]) -> None:
        with self._reviews_path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def _seed_demo(self) -> None:
        """都市逆袭短剧示例图谱 — 可直接在工作室对照使用。"""
        story_id = DEMO_STORY_ID
        chars = [
            {
                "character_id": "char_linxiao",
                "name": "林晓",
                "story_id": story_id,
                "status": "alive",
                "location": "魔都写字楼",
                "persona": ["隐忍", "聪明", "重情义"],
                "arc": 20,
                "backstory": "被家族与未婚夫背叛后进入对手公司卧底",
                "motivations": ["夺回股权", "证明自己"],
                "flaws": ["过度隐忍", "报复心重"],
                "strengths": ["洞察力", "执行力"],
            },
            {
                "character_id": "char_chenshuo",
                "name": "陈朔",
                "story_id": story_id,
                "status": "alive",
                "location": "星海集团",
                "persona": ["强势", "护短", "腹黑"],
                "arc": 10,
                "backstory": "星海少东，表面纨绔实则掌控棋局",
                "motivations": ["巩固集团", "得到林晓真心"],
                "flaws": ["控制欲"],
                "strengths": ["资源", "谋略"],
            },
            {
                "character_id": "char_suwan",
                "name": "苏晚",
                "story_id": story_id,
                "status": "alive",
                "location": "林家",
                "persona": ["心机", "嫉妒"],
                "arc": -30,
                "backstory": "林晓继妹，联合外人抢夺继承权",
                "motivations": ["取代林晓", "上位"],
                "flaws": ["短视"],
                "strengths": ["伪装"],
            },
            {
                "character_id": "char_zhaoming",
                "name": "赵明",
                "story_id": story_id,
                "status": "alive",
                "location": "林家联姻方",
                "persona": ["伪善", "拜金"],
                "arc": -40,
                "backstory": "林晓前未婚夫，背叛联姻",
                "motivations": ["攀附权贵"],
                "flaws": ["软弱"],
                "strengths": ["外表"],
            },
        ]
        plots = [
            {
                "plot_id": "plot_01",
                "story_id": story_id,
                "title": "订婚宴翻车",
                "description": "林晓当众被退婚，家族冷眼，苏晚落井下石",
                "sequence_number": 1,
                "tension_score": 85,
                "chapter": 1,
                "characters_involved": ["char_linxiao", "char_suwan", "char_zhaoming"],
                "locations": ["林家宴会厅"],
                "conflicts": ["家族背叛"],
                "themes": ["逆袭开局"],
                "importance": 90,
            },
            {
                "plot_id": "plot_02",
                "story_id": story_id,
                "title": "星海面试入职",
                "description": "林晓化名进入星海，偶遇陈朔被识破却被留下",
                "sequence_number": 2,
                "tension_score": 70,
                "chapter": 5,
                "characters_involved": ["char_linxiao", "char_chenshuo"],
                "locations": ["星海集团"],
                "conflicts": ["身份隐瞒"],
                "themes": ["假身份"],
                "importance": 80,
            },
            {
                "plot_id": "plot_03",
                "story_id": story_id,
                "title": "股权局中局",
                "description": "苏晚与赵明联手做空林氏，林晓与陈朔反向收网",
                "sequence_number": 3,
                "tension_score": 92,
                "chapter": 40,
                "characters_involved": ["char_linxiao", "char_chenshuo", "char_suwan", "char_zhaoming"],
                "locations": ["交易大厅"],
                "conflicts": ["商业战"],
                "themes": ["打脸反转"],
                "importance": 95,
            },
        ]
        rules = [
            {
                "rule_id": "rule_identity",
                "story_id": story_id,
                "name": "假身份时限",
                "description": "林晓假身份最多维持到第60集，必须主动揭露或被揭穿",
                "rule_type": "plot",
                "constraints": ["不可无限拖延揭身份"],
                "examples": ["面试被识破但暂不公开"],
            }
        ]
        locations = [
            {
                "node_id": "loc_banquet",
                "story_id": story_id,
                "name": "林家宴会厅",
                "description": "开场退婚主场",
                "category": "location",
            },
            {
                "node_id": "loc_xinghai",
                "story_id": story_id,
                "name": "星海集团",
                "description": "逆袭主战场",
                "category": "location",
            },
        ]
        motivations = [
            {
                "node_id": "mot_revenge",
                "story_id": story_id,
                "name": "夺回一切",
                "description": "林晓核心动机",
                "category": "motivation",
            }
        ]

        nodes: List[Dict[str, Any]] = []
        story_props = {
            "story_id": story_id,
            "name": "都市逆袭·假千金",
            "description": "退婚开局的都市商战逆袭短剧示例图谱，用于工具箱可视化与审核演示",
            "genre": "都市逆袭",
            "tags": ["短剧", "商战", "打脸"],
            "status": "active",
            "created_at": _now(),
        }
        nodes.append({"id": story_id, "type": "Story", "labels": ["Story"], "properties": story_props})

        for c in chars:
            nodes.append(
                {
                    "id": c["character_id"],
                    "type": "Character",
                    "labels": ["Character"],
                    "properties": c,
                }
            )
        for p in plots:
            nodes.append({"id": p["plot_id"], "type": "PlotNode", "labels": ["PlotNode"], "properties": p})
        for r in rules:
            nodes.append({"id": r["rule_id"], "type": "WorldRule", "labels": ["WorldRule"], "properties": r})
        for loc in locations:
            nodes.append({"id": loc["node_id"], "type": "Location", "labels": ["Location"], "properties": loc})
        for m in motivations:
            nodes.append({"id": m["node_id"], "type": "Motivation", "labels": ["Motivation"], "properties": m})

        rels = [
            {"id": "r1", "type": "SOCIAL_BOND", "source": "char_linxiao", "target": "char_chenshuo", "properties": {"bond_type": "romantic", "trust_level": 40}},
            {"id": "r2", "type": "SOCIAL_BOND", "source": "char_linxiao", "target": "char_suwan", "properties": {"bond_type": "enemy", "trust_level": -80}},
            {"id": "r3", "type": "SOCIAL_BOND", "source": "char_linxiao", "target": "char_zhaoming", "properties": {"bond_type": "enemy", "trust_level": -90}},
            {"id": "r4", "type": "SOCIAL_BOND", "source": "char_suwan", "target": "char_zhaoming", "properties": {"bond_type": "ally", "trust_level": 50}},
            {"id": "r5", "type": "INVOLVED_IN", "source": "char_linxiao", "target": "plot_01", "properties": {}},
            {"id": "r6", "type": "INVOLVED_IN", "source": "char_suwan", "target": "plot_01", "properties": {}},
            {"id": "r7", "type": "INVOLVED_IN", "source": "char_zhaoming", "target": "plot_01", "properties": {}},
            {"id": "r8", "type": "INVOLVED_IN", "source": "char_linxiao", "target": "plot_02", "properties": {}},
            {"id": "r9", "type": "INVOLVED_IN", "source": "char_chenshuo", "target": "plot_02", "properties": {}},
            {"id": "r10", "type": "NEXT", "source": "plot_01", "target": "plot_02", "properties": {}},
            {"id": "r11", "type": "NEXT", "source": "plot_02", "target": "plot_03", "properties": {}},
            {"id": "r12", "type": "LEADS_TO", "source": "plot_01", "target": "plot_02", "properties": {"description": "退婚后进入星海"}},
            {"id": "r13", "type": "DRIVEN_BY", "source": "char_linxiao", "target": "mot_revenge", "properties": {}},
            {"id": "r14", "type": "LOCATED_IN", "source": "plot_01", "target": "loc_banquet", "properties": {}},
            {"id": "r15", "type": "LOCATED_IN", "source": "plot_02", "target": "loc_xinghai", "properties": {}},
            {"id": "r16", "type": "INFLUENCES", "source": "char_chenshuo", "target": "plot_03", "properties": {"impact_score": 80}},
            {"id": "r17", "type": "OPPOSES", "source": "char_suwan", "target": "char_linxiao", "properties": {}},
            {"id": "r18", "type": "CONTAINS", "source": story_id, "target": "char_linxiao", "properties": {}},
        ]

        data = {
            "story": story_props,
            "nodes": nodes,
            "relationships": rels,
            "updated_at": _now(),
            "backend": "file",
        }
        self._save_story(story_id, data)

        # 示例审核队列（低置信度抽取）
        reviews = [
            {
                "review_id": f"rev_{uuid4().hex[:10]}",
                "story_id": story_id,
                "status": "pending",
                "source": "seed",
                "created_at": _now(),
                "nodes_count": 1,
                "plot_nodes_count": 1,
                "relationships_count": 1,
                "payload": {
                    "nodes": [
                        {
                            "name": "顾北",
                            "type": "Character",
                            "confidence": 0.42,
                            "story_id": story_id,
                            "character_id": "char_gubei_candidate",
                        }
                    ],
                    "plot_nodes": [
                        {
                            "title": "天台对峙",
                            "confidence": 0.55,
                            "story_id": story_id,
                            "plot_id": "plot_candidate_rooftop",
                        }
                    ],
                    "relationships": [
                        {
                            "source": "林晓",
                            "target": "顾北",
                            "type": "SOCIAL_BOND",
                            "confidence": 0.38,
                        }
                    ],
                    "validation_issues": ["人物「顾北」未在既有图谱出现", "关系端点需人工确认"],
                },
            }
        ]
        self._save_reviews(reviews)
        logger.info("[file_graph] seeded demo story %s", story_id)

    # ---- API-compatible methods ----

    async def list_stories(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            out = []
            for path in sorted(self.root.glob("*.json")):
                if path.name.startswith("_"):
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    story = data.get("story")
                    if story:
                        out.append(story)
                except Exception:
                    continue
            return out[:limit]

    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._load_story(story_id)
            return data.get("story")

    async def delete_story(self, story_id: str) -> Dict[str, Any]:
        with self._lock:
            path = self._story_path(story_id)
            if path.exists():
                path.unlink()
                return {"success": True, "deleted": 1}
            return {"success": False, "deleted": 0}

    async def merge_story_element(
        self,
        element_type: Any = None,
        element_data: Any = None,
        version: int = 1,
        *,
        node_type: Any = None,
        data: Any = None,
    ) -> Dict[str, Any]:
        _ = version
        node_type = element_type if element_type is not None else node_type
        data = element_data if element_data is not None else data
        props = data.__dict__ if hasattr(data, "__dict__") else dict(data)
        for k, v in list(props.items()):
            if hasattr(v, "value"):
                props[k] = v.value
        story_id = props.get("story_id")
        if node_type and hasattr(node_type, "value"):
            ntype = node_type.value
        else:
            ntype = str(node_type)
        if ntype == "Story":
            story_id = props.get("story_id")
        if not story_id:
            raise ValueError("story_id required")
        with self._lock:
            store = self._load_story(story_id)
            if ntype == "Story":
                store["story"] = {**props, "created_at": props.get("created_at") or _now()}
                nid = story_id
            else:
                nid = _node_id(props)
            nodes = store.get("nodes") or []
            nodes = [n for n in nodes if n.get("id") != nid]
            nodes.append({"id": nid, "type": ntype, "labels": [ntype], "properties": props})
            store["nodes"] = nodes
            if not store.get("story") and ntype == "Story":
                store["story"] = props
            store["updated_at"] = _now()
            self._save_story(story_id, store)
            return {"success": True, "id": nid, "properties": props}

    async def create_relationship(
        self,
        story_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            store = self._load_story(story_id)
            rid = f"rel_{uuid4().hex[:10]}"
            rel = {
                "id": rid,
                "type": relation_type,
                "source": source_id,
                "target": target_id,
                "properties": properties or {},
            }
            store.setdefault("relationships", []).append(rel)
            store["updated_at"] = _now()
            self._save_story(story_id, store)
            return {"success": True, "relationship": rel, "id": rid}

    async def create_social_bond(
        self,
        character_id_1: str,
        character_id_2: str,
        trust_level: int = 0,
        bond_type: str = "neutral",
        hidden_relation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # 找 story_id
        story_id = None
        for path in self.root.glob("*.json"):
            if path.name.startswith("_"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            ids = {n["id"] for n in data.get("nodes") or []}
            if character_id_1 in ids:
                story_id = (data.get("story") or {}).get("story_id")
                break
        if not story_id:
            return {"success": False, "error": "character not found"}
        return await self.create_relationship(
            story_id,
            character_id_1,
            character_id_2,
            "SOCIAL_BOND",
            {
                "trust_level": trust_level,
                "bond_type": bond_type,
                "hidden_relation": hidden_relation,
                **(metadata or {}),
            },
        )

    async def create_influence(self, **kwargs: Any) -> Dict[str, Any]:
        # 简化：需要 story — 从 from 节点找
        from_id = kwargs.get("from_element_id")
        to_id = kwargs.get("to_element_id")
        story_id = None
        for path in self.root.glob("*.json"):
            if path.name.startswith("_"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            ids = {n["id"] for n in data.get("nodes") or []}
            if from_id in ids:
                story_id = (data.get("story") or {}).get("story_id")
                break
        if not story_id:
            return {"success": False, "error": "element not found"}
        return await self.create_relationship(
            story_id,
            str(from_id),
            str(to_id),
            "INFLUENCES",
            {
                "impact_score": kwargs.get("impact_score", 50),
                "influence_type": kwargs.get("influence_type", "direct"),
                "description": kwargs.get("description"),
                **(kwargs.get("metadata") or {}),
            },
        )

    async def get_story_elements(
        self,
        story_id: str,
        element_types: Optional[List[str]] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> Dict[str, Any]:
        with self._lock:
            store = self._load_story(story_id)
            nodes = store.get("nodes") or []
            if element_types:
                nodes = [n for n in nodes if n.get("type") in element_types]
            nodes = nodes[offset : offset + limit]
            rels = store.get("relationships") or []
            characters = [n["properties"] for n in nodes if n.get("type") == "Character"]
            plot_nodes = [n["properties"] for n in nodes if n.get("type") == "PlotNode"]
            world_rules = [n["properties"] for n in nodes if n.get("type") == "WorldRule"]
            stories = [n["properties"] for n in nodes if n.get("type") == "Story"]
            if store.get("story") and not stories:
                stories = [store["story"]]
            locations = set()
            conflicts = set()
            themes = set()
            for p in plot_nodes:
                for loc in p.get("locations") or []:
                    locations.add(loc)
                for c in p.get("conflicts") or []:
                    conflicts.add(c)
                for t in p.get("themes") or []:
                    themes.add(t)
            try:
                from utils.graph_enrichment import enrich_graph_relationships

                rels = enrich_graph_relationships(nodes, rels)
            except Exception:
                pass
            return {
                "stories": stories,
                "characters": characters,
                "plot_nodes": plot_nodes,
                "world_rules": world_rules,
                "relationships": rels,
                "locations": sorted(locations),
                "conflicts": sorted(conflicts),
                "themes": sorted(themes),
                "nodes": nodes,
                "backend": "file",
            }

    async def get_story_statistics(self, story_id: str) -> Dict[str, Any]:
        els = await self.get_story_elements(story_id)
        chars = els.get("characters") or []
        plots = els.get("plot_nodes") or []
        rules = els.get("world_rules") or []
        rels = els.get("relationships") or []
        avg_t = (
            sum(float(p.get("tension_score") or 0) for p in plots) / len(plots) if plots else 0
        )
        return {
            "story_id": story_id,
            "character_count": len(chars),
            "plot_count": len(plots),
            "rule_count": len(rules),
            "status_distribution": list({c.get("status") for c in chars if c.get("status")}),
            "average_tension": avg_t,
            "social_bond_count": sum(1 for r in rels if r.get("type") == "SOCIAL_BOND"),
            "influence_count": sum(1 for r in rels if r.get("type") == "INFLUENCES"),
            "backend": "file",
        }

    async def get_character_by_id(self, character_id: str) -> Optional[Dict[str, Any]]:
        for path in self.root.glob("*.json"):
            if path.name.startswith("_"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            for n in data.get("nodes") or []:
                if n.get("id") == character_id and n.get("type") == "Character":
                    return n.get("properties")
        return None

    async def get_character_network(
        self, character_id: str, depth: int = 2, include_hidden: bool = False
    ) -> Dict[str, Any]:
        # 简化 1 跳邻居
        for path in self.root.glob("*.json"):
            if path.name.startswith("_"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            rels = [
                r
                for r in data.get("relationships") or []
                if r.get("source") == character_id or r.get("target") == character_id
            ]
            return {
                "character_id": character_id,
                "depth": depth,
                "connections": rels,
                "stats": {"total_connections": len(rels)},
            }
        return {"character_id": character_id, "connections": [], "stats": {"total_connections": 0}}

    async def get_plot_by_story(self, story_id: str, order_by: str = "sequence_number") -> List[Dict[str, Any]]:
        els = await self.get_story_elements(story_id)
        plots = list(els.get("plot_nodes") or [])
        plots.sort(key=lambda p: p.get(order_by) or 0)
        return plots

    async def get_world_rules(self, story_id: str, rule_type: Optional[str] = None) -> List[Dict[str, Any]]:
        els = await self.get_story_elements(story_id)
        rules = list(els.get("world_rules") or [])
        if rule_type:
            rules = [r for r in rules if r.get("rule_type") == rule_type]
        return rules

    async def search_nodes(
        self, story_id: str, query_text: str = "", types: Optional[List[str]] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        els = await self.get_story_elements(story_id)
        q = (query_text or "").lower()
        out = []
        for n in els.get("nodes") or []:
            if types and n.get("type") not in types:
                continue
            blob = json.dumps(n.get("properties") or {}, ensure_ascii=False).lower()
            if not q or q in blob:
                out.append(n)
            if len(out) >= limit:
                break
        return out

    async def search_characters(self, story_id: str, **kwargs: Any) -> List[Dict[str, Any]]:
        els = await self.get_story_elements(story_id)
        term = (kwargs.get("search_term") or "").lower()
        chars = els.get("characters") or []
        if term:
            chars = [c for c in chars if term in json.dumps(c, ensure_ascii=False).lower()]
        return chars[: int(kwargs.get("limit") or 50)]

    async def find_shortest_path(
        self, story_id: str, source_id: str, target_id: str, max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        els = await self.get_story_elements(story_id)
        # BFS
        graph: Dict[str, List[str]] = {}
        for r in els.get("relationships") or []:
            graph.setdefault(r["source"], []).append(r["target"])
            graph.setdefault(r["target"], []).append(r["source"])
        from collections import deque

        q = deque([(source_id, [source_id])])
        seen = {source_id}
        while q:
            cur, path = q.popleft()
            if cur == target_id:
                return [{"nodes": path, "relationships": []}]
            if len(path) > max_depth:
                continue
            for nxt in graph.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, path + [nxt]))
        return []

    async def create_review_queue_entry(
        self, story_id: str, payload: Dict[str, Any], source: str = "manual"
    ) -> Dict[str, Any]:
        with self._lock:
            items = self._load_reviews()
            entry = {
                "review_id": f"rev_{uuid4().hex[:12]}",
                "story_id": story_id,
                "status": "pending",
                "source": source,
                "created_at": _now(),
                "payload": payload,
                "nodes_count": len(payload.get("nodes") or []),
                "plot_nodes_count": len(payload.get("plot_nodes") or []),
                "relationships_count": len(payload.get("relationships") or []),
            }
            items.insert(0, entry)
            self._save_reviews(items)
            return entry

    async def list_review_queue_entries(
        self,
        story_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        with self._lock:
            items = [i for i in self._load_reviews() if i.get("story_id") == story_id]
            if status:
                items = [i for i in items if i.get("status") == status]
            total = len(items)
            page = items[offset : offset + limit]
            return {"items": page, "total": total, "limit": limit, "offset": offset}

    async def get_review_queue_entry(self, review_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for i in self._load_reviews():
                if i.get("review_id") == review_id:
                    return i
            return None

    async def update_review_queue_status(
        self,
        review_id: str,
        status: str,
        result_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            items = self._load_reviews()
            for i in items:
                if i.get("review_id") == review_id:
                    i["status"] = status
                    i["updated_at"] = _now()
                    if result_payload is not None:
                        i["result"] = result_payload
                    self._save_reviews(items)
                    return i
            return None

    async def delete_node(self, node_type: str, node_id: str, story_id: str) -> Dict[str, Any]:
        with self._lock:
            store = self._load_story(story_id)
            before = len(store.get("nodes") or [])
            store["nodes"] = [n for n in store.get("nodes") or [] if n.get("id") != node_id]
            store["relationships"] = [
                r
                for r in store.get("relationships") or []
                if r.get("source") != node_id and r.get("target") != node_id
            ]
            self._save_story(story_id, store)
            return {"success": True, "deleted": before - len(store["nodes"])}

    async def delete_relationship(self, relationship_id: str) -> Dict[str, Any]:
        with self._lock:
            for path in self.root.glob("*.json"):
                if path.name.startswith("_"):
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                before = len(data.get("relationships") or [])
                data["relationships"] = [
                    r for r in data.get("relationships") or [] if r.get("id") != relationship_id
                ]
                if len(data["relationships"]) < before:
                    sid = (data.get("story") or {}).get("story_id") or path.stem
                    self._save_story(sid, data)
                    return {"success": True}
            return {"success": False}


_file_store: Optional[FileGraphStore] = None


async def get_file_graph_store() -> FileGraphStore:
    global _file_store
    if _file_store is None:
        _file_store = FileGraphStore()
        await _file_store.initialize()
    return _file_store

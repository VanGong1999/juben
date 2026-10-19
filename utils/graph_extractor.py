"""
图谱自动抽取服务
从剧本文本中抽取人物/地点/动机/冲突/主题/情节并写入图数据库
"""
from __future__ import annotations

import json
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, validator

from config.settings import JubenSettings
from utils.llm_client import get_llm_client
from utils.graph_manager import (
    GraphDBManager,
    NodeType,
    RelationType,
    CharacterData,
    PlotNodeData,
    GenericNodeData,
    CharacterStatus,
)
from utils.logger import JubenLogger


SYSTEM_PROMPT = """你是专业的剧本知识图谱抽取助手。
请从用户提供的剧本文本中抽取结构化知识，并严格输出 JSON，不要包含多余文字。

抽取目标类型：
- characters: 人物
- locations: 地点
- conflicts: 冲突
- motivations: 动机
- themes: 主题
- plot_nodes: 情节节点
- relations: 关系

关系类型必须来自以下枚举之一：
SOCIAL_BOND, FAMILY_RELATION, ROMANTIC_RELATION,
INFLUENCES, LEADS_TO, NEXT, RESOLVES, COMPLICATES,
INVOLVED_IN, DRIVEN_BY, CONTAINS, VIOLATES, ENFORCES,
LOCATED_IN, LOCATED_AT, OWNS, PART_OF, REPRESENTS, OPPOSES, SUPPORTS

JSON Schema:
{
  "characters": [{"name": "...", "description": "...", "status": "alive|deceased|missing|unknown", "motivations": ["..."], "confidence": 0.0}],
  "locations": [{"name": "...", "description": "...", "category": "...", "confidence": 0.0}],
  "conflicts": [{"name": "...", "description": "...", "confidence": 0.0}],
  "motivations": [{"name": "...", "description": "...", "confidence": 0.0}],
  "themes": [{"name": "...", "description": "...", "confidence": 0.0}],
  "plot_nodes": [{"title": "...", "description": "...", "sequence_number": 1, "characters_involved": ["..."], "locations": ["..."], "conflicts": ["..."], "themes": ["..."], "importance": 50, "confidence": 0.0}],
  "relations": [{"source": "...", "target": "...", "type": "INFLUENCES", "description": "...", "confidence": 0.0}]
}
"""

VALIDATION_PROMPT = """你是剧本知识图谱的校验/去重助手。
请对候选实体与关系进行去重合并、校验关系合法性，并输出规范 JSON。

要求：
1) 合并同名/同义实体，保留最完整描述。
2) 关系的 source/target 必须在最终实体集合中存在，否则标记为无效。
3) relation.type 必须属于允许枚举，否则改为 INFLUENCES 并降低置信度。
4) 每个条目都输出 confidence (0-1) 与 reason。

JSON Schema:
{
  "characters": [{"name": "...", "description": "...", "status": "alive|deceased|missing|unknown", "motivations": ["..."], "confidence": 0.0, "reason": "..."}],
  "locations": [{"name": "...", "description": "...", "category": "...", "confidence": 0.0, "reason": "..."}],
  "conflicts": [{"name": "...", "description": "...", "confidence": 0.0, "reason": "..."}],
  "motivations": [{"name": "...", "description": "...", "confidence": 0.0, "reason": "..."}],
  "themes": [{"name": "...", "description": "...", "confidence": 0.0, "reason": "..."}],
  "plot_nodes": [{"title": "...", "description": "...", "sequence_number": 1, "characters_involved": ["..."], "locations": ["..."], "conflicts": ["..."], "themes": ["..."], "importance": 50, "confidence": 0.0, "reason": "..."}],
  "relations": [{"source": "...", "target": "...", "type": "INFLUENCES", "description": "...", "confidence": 0.0, "valid": true, "reason": "..."}]
}
"""

LOW_CONFIDENCE_THRESHOLD = 0.6

ALIAS_FILE = Path(__file__).resolve().parent.parent / "config" / "graph_aliases.json"


class CharacterItem(BaseModel):
    name: str
    description: Optional[str] = ""
    status: Optional[str] = "unknown"
    motivations: List[str] = Field(default_factory=list)
    confidence: float = 0.5
    reason: Optional[str] = None


class GenericItem(BaseModel):
    name: str
    description: Optional[str] = ""
    category: Optional[str] = None
    confidence: float = 0.5
    reason: Optional[str] = None


class PlotNodeItem(BaseModel):
    title: str
    description: Optional[str] = ""
    sequence_number: int = 1
    characters_involved: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    importance: float = 50
    confidence: float = 0.5
    reason: Optional[str] = None


class RelationItem(BaseModel):
    source: str
    target: str
    type: str = RelationType.INFLUENCES.value
    description: Optional[str] = ""
    confidence: float = 0.5
    valid: Optional[bool] = True
    reason: Optional[str] = None

    @validator("type")
    def _validate_type(cls, v: str) -> str:
        return _normalize_relation_type(v)


class ExtractionPayload(BaseModel):
    characters: List[CharacterItem] = Field(default_factory=list)
    locations: List[GenericItem] = Field(default_factory=list)
    conflicts: List[GenericItem] = Field(default_factory=list)
    motivations: List[GenericItem] = Field(default_factory=list)
    themes: List[GenericItem] = Field(default_factory=list)
    plot_nodes: List[PlotNodeItem] = Field(default_factory=list)
    relations: List[RelationItem] = Field(default_factory=list)


class ValidationPayload(ExtractionPayload):
    pass


def _safe_json_loads(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    # 优先提取 ```json ... ```
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        text = fenced.group(1)
    # 尝试截取最外层 JSON
    brace = re.search(r"(\{.*\})", text, flags=re.S)
    if brace:
        text = brace.group(1)
    return json.loads(text)


def _normalize_relation_type(value: str) -> str:
    if not value:
        return RelationType.INFLUENCES.value
    value = value.strip().upper()
    # 兼容常见别名
    aliases = {
        "CAUSES": "LEADS_TO",
        "CAUSES_TO": "LEADS_TO",
        "FOLLOWS": "NEXT",
        "LOCATION": "LOCATED_IN",
        "LOCATED": "LOCATED_IN",
        "IN_LOCATION": "LOCATED_IN",
        "CONTAIN": "CONTAINS",
    }
    value = aliases.get(value, value)
    allowed = {rt.value for rt in RelationType}
    return value if value in allowed else RelationType.INFLUENCES.value


def _confidence(value: Any, default: float = 0.5) -> float:
    try:
        numeric = float(value)
        if numeric < 0:
            return 0.0
        if numeric > 1:
            return 1.0
        return numeric
    except Exception:
        return default


def _best_item(current: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    if not current:
        return candidate
    c_conf = _confidence(current.get("confidence"))
    n_conf = _confidence(candidate.get("confidence"))
    if n_conf > c_conf:
        return candidate
    if n_conf == c_conf and len(candidate.get("description") or "") > len(current.get("description") or ""):
        return candidate
    return current


def _load_aliases() -> Dict[str, Dict[str, str]]:
    if ALIAS_FILE.exists():
        try:
            raw = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
            return {k: {kk.lower(): vv for kk, vv in (raw.get(k, {}) or {}).items()} for k in raw}
        except Exception:
            return {}
    return {}


def _normalize_entity_name(name: str, alias_map: Dict[str, str]) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"\s+", "", name).strip()
    lower = cleaned.lower()
    return alias_map.get(lower, cleaned)


def _validate_payload(data: Dict[str, Any], schema: BaseModel) -> Dict[str, Any]:
    try:
        parsed = schema.parse_obj(data)
        return json.loads(parsed.json())
    except ValidationError:
        # 回退到尽可能保留结构
        return data if isinstance(data, dict) else {}


def _stable_id(prefix: str, story_id: str, name: str) -> str:
    base = f"{story_id}:{prefix}:{name}".encode("utf-8")
    digest = hashlib.md5(base).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _chunk_text(text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
    if not text:
        return []
    if chunk_size <= 0:
        return [text]
    if len(text) <= chunk_size:
        return [text]
    chunks: List[str] = []
    start = 0
    max_iterations = (len(text) // max(1, chunk_size - overlap)) + 50
    iteration = 0
    while start < len(text):
        iteration += 1
        if iteration > max_iterations:
            break
        end = min(start + chunk_size, len(text))
        # 句子边界优化
        if end < len(text):
            for sep in ["。", "！", "？", "\n", "；"]:
                pos = text.rfind(sep, start + int(chunk_size * 0.6), end)
                if pos > start:
                    end = pos + 1
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        next_start = end - overlap
        if next_start <= start:
            next_start = start + 1
        start = next_start
    return chunks


class GraphExtractionService:
    """图谱自动抽取与落库服务"""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.settings = JubenSettings()
        self.provider = provider or self.settings.default_provider
        self.model = model
        self.logger = JubenLogger("GraphExtractionService")
        self.client = get_llm_client(provider=self.provider, model=self.model)
        self.aliases = _load_aliases()

    async def extract_and_store(
        self,
        graph_db: GraphDBManager,
        story_id: str,
        content: str,
        chunk_size: int = 4000,
        overlap: int = 200,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        chunks = _chunk_text(content, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            return {"success": False, "error": "内容为空或分块失败"}

        registry: Dict[Tuple[str, str], Dict[str, Any]] = {}
        plot_nodes: List[Dict[str, Any]] = []
        relations: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(chunks):
            extracted = await self._extract_chunk(chunk, index=idx + 1)
            for item in extracted.get("characters", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("characters", {}))
                if name:
                    item["name"] = name
                    registry[(NodeType.CHARACTER.value, name.lower())] = _best_item(
                        registry.get((NodeType.CHARACTER.value, name.lower()), {}),
                        item,
                    )
            for item in extracted.get("locations", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("locations", {}))
                if name:
                    item["name"] = name
                    registry[(NodeType.LOCATION.value, name.lower())] = _best_item(
                        registry.get((NodeType.LOCATION.value, name.lower()), {}),
                        item,
                    )
            for item in extracted.get("conflicts", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("conflicts", {}))
                if name:
                    item["name"] = name
                    registry[(NodeType.CONFLICT.value, name.lower())] = _best_item(
                        registry.get((NodeType.CONFLICT.value, name.lower()), {}),
                        item,
                    )
            for item in extracted.get("themes", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("themes", {}))
                if name:
                    item["name"] = name
                    registry[(NodeType.THEME.value, name.lower())] = _best_item(
                        registry.get((NodeType.THEME.value, name.lower()), {}),
                        item,
                    )
            for item in extracted.get("motivations", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("motivations", {}))
                if name:
                    item["name"] = name
                    registry[(NodeType.MOTIVATION.value, name.lower())] = _best_item(
                        registry.get((NodeType.MOTIVATION.value, name.lower()), {}),
                        item,
                    )
            for item in extracted.get("plot_nodes", []) or []:
                plot_nodes.append(item)
            for rel in extracted.get("relations", []) or []:
                relations.append(rel)

        validated = await self._validate_and_merge(registry, plot_nodes, relations)

        registry = validated.get("registry", registry)
        plot_nodes = validated.get("plot_nodes", plot_nodes)
        relations = validated.get("relations", relations)
        validation_issues = validated.get("validation_issues", [])

        # 建立名称->ID映射
        id_map: Dict[str, str] = {}
        created_nodes = []
        pending_nodes = []

        for (node_type, name_lower), item in registry.items():
            name = (item.get("name") or "").strip()
            if not name:
                continue
            confidence = _confidence(item.get("confidence"))
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                pending_nodes.append({
                    "type": node_type,
                    "name": name,
                    "description": item.get("description"),
                    "category": item.get("category"),
                    "status": item.get("status"),
                    "motivations": item.get("motivations") or [],
                    "confidence": confidence,
                    "reason": item.get("reason") or "低置信度",
                })
                continue
            if node_type == NodeType.CHARACTER.value:
                status_value = (item.get("status") or "unknown").lower()
                if status_value not in {s.value for s in CharacterStatus}:
                    status_value = CharacterStatus.UNKNOWN.value
                character_id = _stable_id("char", story_id, name)
                id_map[name_lower] = character_id
                if not dry_run:
                    data = CharacterData(
                        character_id=character_id,
                        name=name,
                        story_id=story_id,
                        status=CharacterStatus(status_value),
                        location=item.get("location"),
                        persona=[],
                        arc=0,
                        backstory=item.get("description"),
                        motivations=item.get("motivations") or [],
                        flaws=[],
                        strengths=[],
                        metadata={"source": "auto_extraction"},
                    )
                    await graph_db.merge_story_element(NodeType.CHARACTER, data)
                created_nodes.append({
                    "type": node_type,
                    "id": character_id,
                    "name": name,
                    "confidence": confidence,
                    "description": item.get("description"),
                    "status": status_value,
                    "motivations": item.get("motivations") or [],
                })
            else:
                node_id = _stable_id("node", story_id, f"{node_type}:{name}")
                id_map[name_lower] = node_id
                if not dry_run:
                    data = GenericNodeData(
                        node_id=node_id,
                        story_id=story_id,
                        name=name,
                        description=item.get("description") or "",
                        category=item.get("category"),
                        metadata={"source": "auto_extraction"},
                    )
                    await graph_db.merge_story_element(NodeType(node_type), data)
                created_nodes.append({
                    "type": node_type,
                    "id": node_id,
                    "name": name,
                    "confidence": confidence,
                    "description": item.get("description"),
                    "category": item.get("category"),
                })

        created_plots = []
        pending_plots = []
        for i, plot in enumerate(plot_nodes):
            title = (plot.get("title") or "").strip()
            if not title:
                continue
            confidence = _confidence(plot.get("confidence"))
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                pending_plots.append({
                    "type": NodeType.PLOT_NODE.value,
                    "title": title,
                    "description": plot.get("description") or "",
                    "sequence_number": plot.get("sequence_number") or (i + 1),
                    "characters_involved": plot.get("characters_involved") or [],
                    "locations": plot.get("locations") or [],
                    "conflicts": plot.get("conflicts") or [],
                    "themes": plot.get("themes") or [],
                    "importance": plot.get("importance") or 50,
                    "confidence": confidence,
                    "reason": plot.get("reason") or "低置信度",
                })
                continue
            plot_id = _stable_id("plot", story_id, f"{i}:{title}")
            if not dry_run:
                data = PlotNodeData(
                    plot_id=plot_id,
                    story_id=story_id,
                    title=title,
                    description=plot.get("description") or "",
                    sequence_number=int(plot.get("sequence_number") or (i + 1)),
                    tension_score=float(plot.get("tension_score") or 50),
                    timestamp=None,
                    chapter=plot.get("chapter"),
                    characters_involved=plot.get("characters_involved") or [],
                    locations=plot.get("locations") or [],
                    conflicts=plot.get("conflicts") or [],
                    themes=plot.get("themes") or [],
                    importance=float(plot.get("importance") or 50),
                    metadata={"source": "auto_extraction"},
                )
                await graph_db.merge_story_element(NodeType.PLOT_NODE, data)
            created_plots.append({
                "type": NodeType.PLOT_NODE.value,
                "id": plot_id,
                "title": title,
                "confidence": confidence,
                "description": plot.get("description") or "",
                "sequence_number": plot.get("sequence_number") or (i + 1),
                "characters_involved": plot.get("characters_involved") or [],
                "locations": plot.get("locations") or [],
                "conflicts": plot.get("conflicts") or [],
                "themes": plot.get("themes") or [],
                "importance": plot.get("importance") or 50,
            })

        created_rels = []
        pending_rels = []
        for rel in relations:
            source = (rel.get("source") or "").strip()
            target = (rel.get("target") or "").strip()
            if not source or not target:
                continue
            confidence = _confidence(rel.get("confidence"))
            source_id = id_map.get(source.lower())
            target_id = id_map.get(target.lower())
            if not source_id or not target_id:
                pending_rels.append({
                    "source": source,
                    "target": target,
                    "type": _normalize_relation_type(rel.get("type") or ""),
                    "description": rel.get("description"),
                    "confidence": confidence,
                    "reason": rel.get("reason") or "关系端点不存在",
                })
                continue
            rel_type = _normalize_relation_type(rel.get("type") or "")
            props = {}
            if rel.get("description"):
                props["description"] = rel.get("description")
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                pending_rels.append({
                    "source": source,
                    "target": target,
                    "type": rel_type,
                    "description": rel.get("description"),
                    "confidence": confidence,
                    "reason": rel.get("reason") or "低置信度",
                    "source_id": source_id,
                    "target_id": target_id,
                })
                continue
            if not dry_run:
                result = await graph_db.create_relationship(
                    story_id=story_id,
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=rel_type,
                    properties=props,
                )
                created_rels.append({
                    "type": rel_type,
                    "id": result.get("id"),
                    "source": source_id,
                    "target": target_id,
                    "source_name": source,
                    "target_name": target,
                    "confidence": confidence,
                    "description": rel.get("description"),
                })
            else:
                created_rels.append({
                    "type": rel_type,
                    "source": source_id,
                    "target": target_id,
                    "source_name": source,
                    "target_name": target,
                    "confidence": confidence,
                    "description": rel.get("description"),
                })

        return {
            "success": True,
            "chunks": len(chunks),
            "nodes_created": len(created_nodes),
            "plot_nodes_created": len(created_plots),
            "relationships_created": len(created_rels),
            "nodes": created_nodes,
            "plot_nodes": created_plots,
            "relationships": created_rels,
            "pending_review": {
                "nodes": pending_nodes,
                "plot_nodes": pending_plots,
                "relationships": pending_rels,
            },
            "validation_issues": validation_issues,
        }

    async def apply_review(
        self,
        graph_db: GraphDBManager,
        story_id: str,
        review_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """将人工确认的低置信度条目落库"""
        nodes = review_payload.get("nodes", []) or []
        plot_nodes = review_payload.get("plot_nodes", []) or []
        relationships = review_payload.get("relationships", []) or []

        id_map: Dict[str, str] = {}
        created_nodes = []
        created_plots = []
        created_rels = []
        errors: List[str] = []

        for item in nodes:
            node_type = item.get("type")
            name = (item.get("name") or "").strip()
            if not node_type or not name:
                continue
            if node_type == NodeType.CHARACTER.value:
                status_value = (item.get("status") or "unknown").lower()
                if status_value not in {s.value for s in CharacterStatus}:
                    status_value = CharacterStatus.UNKNOWN.value
                character_id = _stable_id("char", story_id, name)
                id_map[name.lower()] = character_id
                data = CharacterData(
                    character_id=character_id,
                    name=name,
                    story_id=story_id,
                    status=CharacterStatus(status_value),
                    location=item.get("location"),
                    persona=[],
                    arc=0,
                    backstory=item.get("description"),
                    motivations=item.get("motivations") or [],
                    flaws=[],
                    strengths=[],
                    metadata={"source": "manual_review"},
                )
                await graph_db.merge_story_element(NodeType.CHARACTER, data)
                created_nodes.append({"type": node_type, "id": character_id, "name": name})
            elif node_type == NodeType.PLOT_NODE.value:
                # plot_nodes 单独处理
                continue
            else:
                try:
                    node_enum = NodeType(node_type)
                except Exception:
                    errors.append(f"未知节点类型: {node_type}")
                    continue
                node_id = _stable_id("node", story_id, f"{node_type}:{name}")
                id_map[name.lower()] = node_id
                data = GenericNodeData(
                    node_id=node_id,
                    story_id=story_id,
                    name=name,
                    description=item.get("description") or "",
                    category=item.get("category"),
                    metadata={"source": "manual_review"},
                )
                await graph_db.merge_story_element(node_enum, data)
                created_nodes.append({"type": node_type, "id": node_id, "name": name})

        for i, plot in enumerate(plot_nodes):
            title = (plot.get("title") or "").strip()
            if not title:
                continue
            plot_id = _stable_id("plot", story_id, f"{i}:{title}")
            data = PlotNodeData(
                plot_id=plot_id,
                story_id=story_id,
                title=title,
                description=plot.get("description") or "",
                sequence_number=int(plot.get("sequence_number") or (i + 1)),
                tension_score=float(plot.get("tension_score") or 50),
                timestamp=None,
                chapter=plot.get("chapter"),
                characters_involved=plot.get("characters_involved") or [],
                locations=plot.get("locations") or [],
                conflicts=plot.get("conflicts") or [],
                themes=plot.get("themes") or [],
                importance=float(plot.get("importance") or 50),
                metadata={"source": "manual_review"},
            )
            await graph_db.merge_story_element(NodeType.PLOT_NODE, data)
            created_plots.append({"type": NodeType.PLOT_NODE.value, "id": plot_id, "title": title})

        # 关系处理
        for rel in relationships:
            source = (rel.get("source") or "").strip()
            target = (rel.get("target") or "").strip()
            source_id = rel.get("source_id") or id_map.get(source.lower())
            target_id = rel.get("target_id") or id_map.get(target.lower())
            if not source_id or not target_id:
                errors.append(f"关系端点不存在: {source}->{target}")
                continue
            rel_type = _normalize_relation_type(rel.get("type") or "")
            props = {}
            if rel.get("description"):
                props["description"] = rel.get("description")
            result = await graph_db.create_relationship(
                story_id=story_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=rel_type,
                properties=props,
            )
            created_rels.append({"type": rel_type, "id": result.get("id"), "source": source_id, "target": target_id})

        return {
            "success": True,
            "nodes_created": len(created_nodes),
            "plot_nodes_created": len(created_plots),
            "relationships_created": len(created_rels),
            "nodes": created_nodes,
            "plot_nodes": created_plots,
            "relationships": created_rels,
            "errors": errors,
        }

    async def _validate_and_merge(
        self,
        registry: Dict[Tuple[str, str], Dict[str, Any]],
        plot_nodes: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """二阶段校验：合并/去重/关系合法性"""
        try:
            payload = {
                "characters": [item for (t, _), item in registry.items() if t == NodeType.CHARACTER.value][:200],
                "locations": [item for (t, _), item in registry.items() if t == NodeType.LOCATION.value][:200],
                "conflicts": [item for (t, _), item in registry.items() if t == NodeType.CONFLICT.value][:200],
                "motivations": [item for (t, _), item in registry.items() if t == NodeType.MOTIVATION.value][:200],
                "themes": [item for (t, _), item in registry.items() if t == NodeType.THEME.value][:200],
                "plot_nodes": plot_nodes[:200],
                "relations": relations[:200],
            }

            messages = [
                {"role": "system", "content": VALIDATION_PROMPT},
                {"role": "user", "content": f"候选数据如下：\\n{json.dumps(payload, ensure_ascii=False)}"},
            ]
            response = await self.client.chat(messages, temperature=0.1, max_tokens=2000)
            merged = _safe_json_loads(response)
            merged = _validate_payload(merged, ValidationPayload)

            # 重新构建 registry
            merged_registry: Dict[Tuple[str, str], Dict[str, Any]] = {}
            for item in merged.get("characters", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("characters", {}))
                if name:
                    item["name"] = name
                    merged_registry[(NodeType.CHARACTER.value, name.lower())] = item
            for item in merged.get("locations", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("locations", {}))
                if name:
                    item["name"] = name
                    merged_registry[(NodeType.LOCATION.value, name.lower())] = item
            for item in merged.get("conflicts", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("conflicts", {}))
                if name:
                    item["name"] = name
                    merged_registry[(NodeType.CONFLICT.value, name.lower())] = item
            for item in merged.get("motivations", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("motivations", {}))
                if name:
                    item["name"] = name
                    merged_registry[(NodeType.MOTIVATION.value, name.lower())] = item
            for item in merged.get("themes", []) or []:
                name = _normalize_entity_name(item.get("name") or "", self.aliases.get("themes", {}))
                if name:
                    item["name"] = name
                    merged_registry[(NodeType.THEME.value, name.lower())] = item

            merged_plot_nodes = merged.get("plot_nodes", plot_nodes) or []
            merged_relations = merged.get("relations", relations) or []
            # 关系合法性二次检查
            name_set = {key[1] for key in merged_registry.keys()}
            normalized_relations = []
            all_aliases: Dict[str, str] = {}
            for group in self.aliases.values():
                all_aliases.update(group)
            for rel in merged_relations:
                rel_type = _normalize_relation_type(rel.get("type") or "")
                rel["type"] = rel_type
                src = _normalize_entity_name(rel.get("source") or "", all_aliases).strip().lower()
                tgt = _normalize_entity_name(rel.get("target") or "", all_aliases).strip().lower()
                if not src or not tgt or src not in name_set or tgt not in name_set:
                    rel["valid"] = False
                    rel["reason"] = rel.get("reason") or "关系端点不存在"
                else:
                    rel["valid"] = rel.get("valid", True)
                normalized_relations.append(rel)

            return {
                "registry": merged_registry or registry,
                "plot_nodes": merged_plot_nodes,
                "relations": normalized_relations,
                "validation_issues": merged.get("validation_issues", []),
            }
        except Exception as e:
            self.logger.warning(f"二阶段校验失败，使用回退逻辑: {e}")
            return {"registry": registry, "plot_nodes": plot_nodes, "relations": relations, "validation_issues": [str(e)]}

    async def _extract_chunk(self, text: str, index: int = 1) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"文本片段#{index}：\\n{text}\\n\\n请按JSON输出。"},
        ]
        response = await self.client.chat(messages, temperature=0.2, max_tokens=2000)
        try:
            data = _safe_json_loads(response)
            data = _validate_payload(data, ExtractionPayload)
            # 补齐置信度字段
            for key in ["characters", "locations", "conflicts", "motivations", "themes", "plot_nodes", "relations"]:
                for item in data.get(key, []) or []:
                    if "confidence" not in item:
                        item["confidence"] = 0.5
            return data
        except Exception as e:
            self.logger.error(f"解析抽取结果失败: {e}")
            return {}

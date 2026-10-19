"""
生产级剧本创作图谱存储引擎
Graph Database Manager for Screenplay Creation

功能特性：
1. Neo4j 异步驱动与高级连接池管理
2. 生产级 Schema 设计（节点、关系、属性）
3. 原子性操作保证数据一致性
4. 索引优化查询性能
5. 事务管理和错误恢复
6. 深度网络分析（社交、因果）

作者：Claude
创建时间：2025-02-08
"""

import asyncio
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from uuid import uuid4

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncManagedTransaction
from neo4j.exceptions import (
    ServiceUnavailable,
    TransientError,
    ClientError,
    SessionExpired
)

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# 配置日志
logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """图谱节点类型枚举"""
    STORY = "Story"                  # 故事节点
    CHARACTER = "Character"           # 角色节点
    PLOT_NODE = "PlotNode"            # 情节节点
    WORLD_RULE = "WorldRule"          # 世界观规则
    LOCATION = "Location"             # 地点节点
    ITEM = "Item"                     # 物品节点
    CONFLICT = "Conflict"             # 冲突节点
    THEME = "Theme"                   # 主题节点
    MOTIVATION = "Motivation"         # 动机节点（新增）


class RelationType(str, Enum):
    """图谱关系类型枚举"""
    # 角色关系
    SOCIAL_BOND = "SOCIAL_BOND"       # 社交关系
    FAMILY_RELATION = "FAMILY_RELATION"  # 家庭关系
    ROMANTIC_RELATION = "ROMANTIC_RELATION"  # 感情关系

    # 情节关系
    INFLUENCES = "INFLUENCES"         # 影响/因果
    LEADS_TO = "LEADS_TO"             # 导致
    NEXT = "NEXT"                     # 下一情节（新增，用于顺序）
    RESOLVES = "RESOLVES"             # 解决
    COMPLICATES = "COMPLICATES"       # 复杂化

    # 角色与情节关系
    INVOLVED_IN = "INVOLVED_IN"       # 参与情节（新增）
    DRIVEN_BY = "DRIVEN_BY"           # 被动机驱动（新增）

    # 世界关系
    CONTAINS = "CONTAINS"             # 包含
    VIOLATES = "VIOLATES"             # 违反
    ENFORCES = "ENFORCES"             # 强制
    LOCATED_IN = "LOCATED_IN"         # 位于
    LOCATED_AT = "LOCATED_AT"         # 位置
    OWNS = "OWNS"                     # 拥有
    PART_OF = "PART_OF"               # 属于
    REPRESENTS = "REPRESENTS"         # 代表
    OPPOSES = "OPPOSES"               # 反对
    SUPPORTS = "SUPPORTS"             # 支持


class CharacterStatus(str, Enum):
    """角色状态枚举"""
    ALIVE = "alive"
    DECEASED = "deceased"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass
class CharacterData:
    """角色节点数据模型"""
    character_id: str
    name: str
    story_id: str
    status: CharacterStatus = CharacterStatus.ALIVE
    location: Optional[str] = None
    persona: List[str] = field(default_factory=list)  # 性格标签
    arc: float = 0.0  # 成长曲线值 (-100 到 100)
    backstory: Optional[str] = None
    motivations: List[str] = field(default_factory=list)
    flaws: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    first_appearance: Optional[int] = None  # 首次出现章节
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "story_id": self.story_id,
            "status": self.status.value,
            "location": self.location,
            "persona": self.persona,
            "arc": self.arc,
            "backstory": self.backstory,
            "motivations": self.motivations,
            "flaws": self.flaws,
            "strengths": self.strengths,
            "first_appearance": self.first_appearance,
            "metadata": self.metadata,
        }


@dataclass
class StoryData:
    """故事节点数据模型"""
    story_id: str
    name: str
    description: str = ""
    genre: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "tags": self.tags,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class GenericNodeData:
    """通用节点数据模型（Location/Item/Conflict/Theme/Motivation）"""
    node_id: str
    story_id: str
    name: str
    description: str = ""
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "story_id": self.story_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "metadata": self.metadata,
        }


@dataclass
class PlotNodeData:
    """情节节点数据模型"""
    plot_id: str
    story_id: str
    title: str
    description: str
    sequence_number: int
    tension_score: float = 50.0  # 张力得分 (0-100)
    timestamp: Optional[datetime] = None
    chapter: Optional[int] = None
    characters_involved: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    importance: float = 50.0  # 重要性得分 (0-100)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plot_id": self.plot_id,
            "story_id": self.story_id,
            "title": self.title,
            "description": self.description,
            "sequence_number": self.sequence_number,
            "tension_score": self.tension_score,
            "timestamp": self.timestamp.isoformat() if self.timestamp else datetime.now(timezone.utc).isoformat(),
            "chapter": self.chapter,
            "characters_involved": self.characters_involved,
            "locations": self.locations,
            "conflicts": self.conflicts,
            "themes": self.themes,
            "importance": self.importance,
            "metadata": self.metadata,
        }


@dataclass
class WorldRuleData:
    """世界观规则数据模型"""
    rule_id: str
    story_id: str
    name: str
    description: str
    rule_type: str  # magic, physics, social, etc.
    severity: str = "strict"  # strict, moderate, flexible
    consequences: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "story_id": self.story_id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type,
            "severity": self.severity,
            "consequences": self.consequences,
            "exceptions": self.exceptions,
            "constraints": self.constraints,
            "examples": self.examples,
            "metadata": self.metadata,
        }


def _neo4j_to_jsonable(obj: Any) -> Any:
    """将 Neo4j 返回对象递归转换为 JSON 可序列化类型。

    Neo4j 驱动返回的 created_at/updated_at/timestamp 等为 neo4j.time.DateTime，
    无法被 FastAPI/Pydantic 直接序列化，需在此统一转换。
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _neo4j_to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_neo4j_to_jsonable(v) for v in obj]
    if hasattr(obj, "iso_format"):
        return obj.iso_format()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


class GraphDBManager:
    """
    生产级剧本创作图谱存储引擎

    特性：
    1. 异步连接池管理
    2. 自动重试和错误恢复
    3. 事务管理
    4. 索引优化
    5. 原子性操作
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "",
        database: str = "neo4j",
        max_connection_pool_size: int = 50,
        max_connection_lifetime: int = 3600,
        connection_acquisition_timeout: int = 60,
        max_transaction_retry_time: int = 30,
    ):
        """
        初始化图数据库管理器

        Args:
            uri: Neo4j 连接 URI
            username: 数据库用户名
            password: 数据库密码
            database: 数据库名称
            max_connection_pool_size: 最大连接池大小
            max_connection_lifetime: 连接最大存活时间（秒）
            connection_acquisition_timeout: 连接获取超时时间（秒）
            max_transaction_retry_time: 事务最大重试时间（秒）
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Optional[AsyncDriver] = None

        # 连接池配置
        self.max_connection_pool_size = max_connection_pool_size
        self.max_connection_lifetime = max_connection_lifetime
        self.connection_acquisition_timeout = connection_acquisition_timeout
        self.max_transaction_retry_time = max_transaction_retry_time

        # 事务统计
        self._transaction_stats = {
            "total_transactions": 0,
            "successful_transactions": 0,
            "failed_transactions": 0,
            "retries": 0,
        }

        logger.info(f"GraphDBManager 初始化: {uri}@{database}")

    async def initialize(self):
        """
        初始化连接池并创建Schema
        """
        try:
            # 创建异步驱动
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_pool_size=self.max_connection_pool_size,
                max_connection_lifetime=self.max_connection_lifetime,
                connection_acquisition_timeout=self.connection_acquisition_timeout,
                max_transaction_retry_time=self.max_transaction_retry_time,
            )

            # 验证连接
            await self.verify_connectivity()

            # 创建Schema和索引
            await self.create_schema()

            logger.info("GraphDBManager 初始化完成")

        except Exception as e:
            logger.error(f"GraphDBManager 初始化失败: {e}")
            raise

    async def close(self):
        """关闭连接池"""
        if self.driver:
            await self.driver.close()
            logger.info("GraphDBManager 连接已关闭")

    @asynccontextmanager
    async def _get_session(self):
        """
        获取数据库会话（上下文管理器）

        Yields:
            AsyncSession: Neo4j 异步会话
        """
        if not self.driver:
            raise RuntimeError("Driver 未初始化，请先调用 initialize()")

        async with self.driver.session(database=self.database) as session:
            yield session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, TransientError, SessionExpired)),
    )
    async def verify_connectivity(self) -> bool:
        """
        验证数据库连接（带重试）

        Returns:
            bool: 连接是否成功
        """
        try:
            async with self._get_session() as session:
                result = await session.run("RETURN 1 AS test")
                record = await result.single()
                if record and record["test"] == 1:
                    logger.info("Neo4j 连接验证成功")
                    return True
        except Exception as e:
            logger.error(f"Neo4j 连接验证失败: {e}")
            raise

        return False

    async def create_schema(self):
        """
        创建生产级 Schema：
        1. 唯一性约束
        2. 索引优化
        3. 全文搜索索引
        """
        constraints_and_indexes = [
            # ============ Story 节点约束和索引 ============
            "CREATE CONSTRAINT story_id_unique IF NOT EXISTS FOR (s:Story) REQUIRE s.story_id IS UNIQUE",
            "CREATE INDEX story_status_idx IF NOT EXISTS FOR (s:Story) WHERE s.status IS NOT NULL",
            "CREATE FULLTEXT INDEX story_fulltext IF NOT EXISTS FOR (s:Story) ON EACH [s.name, s.description]",

            # ============ GraphReviewQueue 约束和索引 ============
            "CREATE CONSTRAINT graph_review_id_unique IF NOT EXISTS FOR (r:GraphReviewQueue) REQUIRE r.review_id IS UNIQUE",
            "CREATE INDEX graph_review_story_idx IF NOT EXISTS FOR (r:GraphReviewQueue) WHERE r.story_id IS NOT NULL",
            "CREATE INDEX graph_review_status_idx IF NOT EXISTS FOR (r:GraphReviewQueue) WHERE r.status IS NOT NULL",

            # ============ Character 节点约束和索引 ============
            # 唯一性约束
            "CREATE CONSTRAINT character_id_unique IF NOT EXISTS FOR (c:Character) REQUIRE c.character_id IS UNIQUE",
            "CREATE CONSTRAINT character_story_unique IF NOT EXISTS FOR (c:Character) REQUIRE (c.story_id, c.name) IS UNIQUE",

            # 属性索引
            "CREATE INDEX character_status_idx IF NOT EXISTS FOR (c:Character) WHERE c.status IS NOT NULL",
            "CREATE INDEX character_location_idx IF NOT EXISTS FOR (c:Character) WHERE c.location IS NOT NULL",
            "CREATE INDEX character_arc_idx IF NOT EXISTS FOR (c:Character) WHERE c.arc IS NOT NULL",
            "CREATE INDEX character_story_idx IF NOT EXISTS FOR (c:Character) WHERE c.story_id IS NOT NULL",

            # 全文搜索索引
            "CREATE FULLTEXT INDEX character_fulltext IF NOT EXISTS FOR (c:Character) ON EACH [c.name, c.backstory]",

            # ============ PlotNode 节点约束和索引 ============
            # 唯一性约束
            "CREATE CONSTRAINT plot_id_unique IF NOT EXISTS FOR (p:PlotNode) REQUIRE p.plot_id IS UNIQUE",
            "CREATE CONSTRAINT plot_story_sequence_unique IF NOT EXISTS FOR (p:PlotNode) REQUIRE (p.story_id, p.sequence_number) IS UNIQUE",

            # 属性索引
            "CREATE INDEX plot_tension_idx IF NOT EXISTS FOR (p:PlotNode) WHERE p.tension_score IS NOT NULL",
            "CREATE INDEX plot_importance_idx IF NOT EXISTS FOR (p:PlotNode) WHERE p.importance IS NOT NULL",
            "CREATE INDEX plot_chapter_idx IF NOT EXISTS FOR (p:PlotNode) WHERE p.chapter IS NOT NULL",
            "CREATE INDEX plot_story_idx IF NOT EXISTS FOR (p:PlotNode) WHERE p.story_id IS NOT NULL",

            # 全文搜索索引
            "CREATE FULLTEXT INDEX plot_fulltext IF NOT EXISTS FOR (p:PlotNode) ON EACH [p.title, p.description]",

            # ============ WorldRule 节点约束和索引 ============
            # 唯一性约束
            "CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:WorldRule) REQUIRE r.rule_id IS UNIQUE",
            "CREATE CONSTRAINT rule_story_unique IF NOT EXISTS FOR (r:WorldRule) REQUIRE (r.story_id, r.name) IS UNIQUE",

            # 属性索引
            "CREATE INDEX rule_type_idx IF NOT EXISTS FOR (r:WorldRule) WHERE r.rule_type IS NOT NULL",
            "CREATE INDEX rule_severity_idx IF NOT EXISTS FOR (r:WorldRule) WHERE r.severity IS NOT NULL",
            "CREATE INDEX rule_story_idx IF NOT EXISTS FOR (r:WorldRule) WHERE r.story_id IS NOT NULL",

            # 全文搜索索引
            "CREATE FULLTEXT INDEX rule_fulltext IF NOT EXISTS FOR (r:WorldRule) ON EACH [r.name, r.description]",

            # ============ 关系索引 ============
            "CREATE INDEX social_bond_trust_idx IF NOT EXISTS FOR ()-[r:SOCIAL_BOND]-() WHERE r.trust_level IS NOT NULL",
            "CREATE INDEX influences_impact_idx IF NOT EXISTS FOR ()-[r:INFLUENCES]-() WHERE r.impact_score IS NOT NULL",

            # ============ 通用节点约束 ============
            "CREATE CONSTRAINT location_node_id_unique IF NOT EXISTS FOR (n:Location) REQUIRE n.node_id IS UNIQUE",
            "CREATE CONSTRAINT item_node_id_unique IF NOT EXISTS FOR (n:Item) REQUIRE n.node_id IS UNIQUE",
            "CREATE CONSTRAINT conflict_node_id_unique IF NOT EXISTS FOR (n:Conflict) REQUIRE n.node_id IS UNIQUE",
            "CREATE CONSTRAINT theme_node_id_unique IF NOT EXISTS FOR (n:Theme) REQUIRE n.node_id IS UNIQUE",
            "CREATE CONSTRAINT motivation_node_id_unique IF NOT EXISTS FOR (n:Motivation) REQUIRE n.node_id IS UNIQUE",

            "CREATE INDEX location_story_idx IF NOT EXISTS FOR (n:Location) WHERE n.story_id IS NOT NULL",
            "CREATE INDEX item_story_idx IF NOT EXISTS FOR (n:Item) WHERE n.story_id IS NOT NULL",
            "CREATE INDEX conflict_story_idx IF NOT EXISTS FOR (n:Conflict) WHERE n.story_id IS NOT NULL",
            "CREATE INDEX theme_story_idx IF NOT EXISTS FOR (n:Theme) WHERE n.story_id IS NOT NULL",
            "CREATE INDEX motivation_story_idx IF NOT EXISTS FOR (n:Motivation) WHERE n.story_id IS NOT NULL",
        ]

        async with self._get_session() as session:
            for query in constraints_and_indexes:
                try:
                    await session.run(query)
                    logger.debug(f"执行 Schema: {query[:60]}...")
                except ClientError as e:
                    if e.code == "Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists":
                        logger.debug(f"Schema 已存在，跳过: {query[:60]}...")
                    else:
                        logger.warning(f"创建 Schema 警告: {e}")

        logger.info("Schema 创建完成")

    # ============ 原子性操作 ============

    async def merge_story_element(
        self,
        element_type: NodeType,
        element_data: Union[StoryData, CharacterData, PlotNodeData, WorldRuleData, GenericNodeData],
        version: int = 1,
    ) -> Dict[str, Any]:
        """
        原子性合并故事元素（使用 MERGE）

        确保实体唯一性，记录版本和更新时间

        Args:
            element_type: 节点类型
            element_data: 节点数据
            version: 版本号

        Returns:
            Dict: 操作结果
        """
        self._transaction_stats["total_transactions"] += 1

        try:
            async with self._get_session() as session:
                if element_type == NodeType.STORY:
                    result = await self._merge_story(session, element_data, version)
                elif element_type == NodeType.CHARACTER:
                    result = await self._merge_character(session, element_data, version)
                elif element_type == NodeType.PLOT_NODE:
                    result = await self._merge_plot_node(session, element_data, version)
                elif element_type == NodeType.WORLD_RULE:
                    result = await self._merge_world_rule(session, element_data, version)
                elif element_type in {
                    NodeType.LOCATION,
                    NodeType.ITEM,
                    NodeType.CONFLICT,
                    NodeType.THEME,
                    NodeType.MOTIVATION,
                }:
                    result = await self._merge_generic_node(session, element_type, element_data, version)
                else:
                    raise ValueError(f"不支持的节点类型: {element_type}")

                self._transaction_stats["successful_transactions"] += 1
                return result

        except Exception as e:
            self._transaction_stats["failed_transactions"] += 1
            logger.error(f"merge_story_element 失败: {e}")
            raise

    async def _merge_character(
        self,
        session,
        data: CharacterData,
        version: int,
    ) -> Dict[str, Any]:
        """合并角色节点（原子操作）"""
        query = f"""
        MERGE (c:{NodeType.CHARACTER.value} {{character_id: $character_id}})
        ON CREATE SET
            c.created_at = datetime($timestamp),
            c.version = $version,
            c.first_appearance = $first_appearance
        ON MATCH SET
            c.updated_at = datetime($timestamp),
            c.version = $version,
            c.arc = COALESCE($arc, c.arc),
            c.status = COALESCE($status, c.status),
            c.location = COALESCE($location, c.location)
        SET
            c.name = $name,
            c.story_id = $story_id,
            c.persona = $persona,
            c.backstory = $backstory,
            c.motivations = $motivations,
            c.flaws = $flaws,
            c.strengths = $strengths,
            c.metadata = $metadata
        RETURN c
        """

        params = {
            "character_id": data.character_id,
            "name": data.name,
            "story_id": data.story_id,
            "status": data.status.value,
            "location": data.location,
            "persona": data.persona,
            "arc": data.arc,
            "backstory": data.backstory,
            "motivations": data.motivations,
            "flaws": data.flaws,
            "strengths": data.strengths,
            "first_appearance": data.first_appearance,
            "metadata": json.dumps(data.metadata, ensure_ascii=False),
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = await session.run(query, params)
        record = await result.single()

        if record:
            node = record["c"]
            return {
                "success": True,
                "element_id": data.character_id,
                "type": NodeType.CHARACTER.value,
                "created": node.get("created_at") is not None,
                "updated": node.get("updated_at") is not None,
                "version": version,
                "node": _neo4j_to_jsonable(dict(node)),
            }

        return {"success": False, "error": "创建节点失败"}

    async def _merge_story(
        self,
        session,
        data: StoryData,
        version: int,
    ) -> Dict[str, Any]:
        """合并故事节点（原子操作）"""
        query = f"""
        MERGE (s:{NodeType.STORY.value} {{story_id: $story_id}})
        ON CREATE SET
            s.created_at = datetime($timestamp),
            s.version = $version
        ON MATCH SET
            s.updated_at = datetime($timestamp),
            s.version = $version
        SET
            s.name = $name,
            s.description = $description,
            s.genre = $genre,
            s.tags = $tags,
            s.status = $status,
            s.metadata = $metadata
        RETURN s
        """

        params = {
            "story_id": data.story_id,
            "name": data.name,
            "description": data.description,
            "genre": data.genre,
            "tags": data.tags,
            "status": data.status,
            "metadata": json.dumps(data.metadata, ensure_ascii=False),
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = await session.run(query, params)
        record = await result.single()

        if record:
            node = record["s"]
            return {
                "success": True,
                "element_id": data.story_id,
                "type": NodeType.STORY.value,
                "created": node.get("created_at") is not None,
                "updated": node.get("updated_at") is not None,
                "version": version,
                "node": _neo4j_to_jsonable(dict(node)),
            }

        return {"success": False, "error": "创建节点失败"}

    async def _merge_generic_node(
        self,
        session,
        node_type: NodeType,
        data: GenericNodeData,
        version: int,
    ) -> Dict[str, Any]:
        """合并通用节点（原子操作）"""
        query = f"""
        MERGE (n:{node_type.value} {{node_id: $node_id}})
        ON CREATE SET
            n.created_at = datetime($timestamp),
            n.version = $version
        ON MATCH SET
            n.updated_at = datetime($timestamp),
            n.version = $version
        SET
            n.story_id = $story_id,
            n.name = $name,
            n.description = $description,
            n.category = $category,
            n.metadata = $metadata
        RETURN n
        """

        params = {
            "node_id": data.node_id,
            "story_id": data.story_id,
            "name": data.name,
            "description": data.description,
            "category": data.category,
            "metadata": json.dumps(data.metadata, ensure_ascii=False),
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = await session.run(query, params)
        record = await result.single()

        if record:
            node = record["n"]
            return {
                "success": True,
                "element_id": data.node_id,
                "type": node_type.value,
                "created": node.get("created_at") is not None,
                "updated": node.get("updated_at") is not None,
                "version": version,
                "node": _neo4j_to_jsonable(dict(node)),
            }

        return {"success": False, "error": "创建节点失败"}

    async def _merge_plot_node(
        self,
        session,
        data: PlotNodeData,
        version: int,
    ) -> Dict[str, Any]:
        """合并情节节点（原子操作，按 story_id + sequence_number 唯一）"""
        query = f"""
        MERGE (p:{NodeType.PLOT_NODE.value} {{story_id: $story_id, sequence_number: $sequence_number}})
        ON CREATE SET
            p.plot_id = $plot_id,
            p.created_at = datetime($timestamp),
            p.version = $version
        ON MATCH SET
            p.updated_at = datetime($timestamp),
            p.version = $version,
            p.tension_score = $tension_score,
            p.importance = $importance
        SET
            p.title = $title,
            p.description = $description,
            p.timestamp = datetime($timestamp),
            p.chapter = $chapter,
            p.characters_involved = $characters_involved,
            p.locations = $locations,
            p.conflicts = $conflicts,
            p.themes = $themes,
            p.metadata = $metadata
        RETURN p
        """

        params = {
            "plot_id": data.plot_id,
            "story_id": data.story_id,
            "title": data.title,
            "description": data.description,
            "sequence_number": data.sequence_number,
            "tension_score": data.tension_score,
            "timestamp": data.timestamp.isoformat() if data.timestamp else datetime.now(timezone.utc).isoformat(),
            "chapter": data.chapter,
            "characters_involved": data.characters_involved,
            "locations": data.locations,
            "conflicts": data.conflicts,
            "themes": data.themes,
            "importance": data.importance,
            "metadata": json.dumps(data.metadata, ensure_ascii=False),
            "version": version,
        }

        result = await session.run(query, params)
        record = await result.single()

        if record:
            node = record["p"]
            return {
                "success": True,
                "element_id": data.plot_id,
                "type": NodeType.PLOT_NODE.value,
                "created": node.get("created_at") is not None,
                "updated": node.get("updated_at") is not None,
                "version": version,
                "node": _neo4j_to_jsonable(dict(node)),
            }

        return {"success": False, "error": "创建节点失败"}

    async def _merge_world_rule(
        self,
        session,
        data: WorldRuleData,
        version: int,
    ) -> Dict[str, Any]:
        """合并世界观规则节点（原子操作）"""
        query = f"""
        MERGE (r:{NodeType.WORLD_RULE.value} {{rule_id: $rule_id}})
        ON CREATE SET
            r.created_at = datetime($timestamp),
            r.version = $version
        ON MATCH SET
            r.updated_at = datetime($timestamp),
            r.version = $version
        SET
            r.story_id = $story_id,
            r.name = $name,
            r.description = $description,
            r.rule_type = $rule_type,
            r.severity = $severity,
            r.consequences = $consequences,
            r.exceptions = $exceptions,
            r.constraints = $constraints,
            r.examples = $examples,
            r.metadata = $metadata
        RETURN r
        """

        params = {
            "rule_id": data.rule_id,
            "story_id": data.story_id,
            "name": data.name,
            "description": data.description,
            "rule_type": data.rule_type,
            "severity": data.severity,
            "consequences": data.consequences,
            "exceptions": data.exceptions,
            "constraints": data.constraints,
            "examples": data.examples,
            "metadata": json.dumps(data.metadata, ensure_ascii=False),
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = await session.run(query, params)
        record = await result.single()

        if record:
            node = record["r"]
            return {
                "success": True,
                "element_id": data.rule_id,
                "type": NodeType.WORLD_RULE.value,
                "created": node.get("created_at") is not None,
                "updated": node.get("updated_at") is not None,
                "version": version,
                "node": _neo4j_to_jsonable(dict(node)),
            }

        return {"success": False, "error": "创建节点失败"}

    # ============ 关系操作 ============

    async def create_social_bond(
        self,
        character_id_1: str,
        character_id_2: str,
        trust_level: int = 0,  # -100 到 100
        bond_type: str = "neutral",  # friend, enemy, neutral, family, romantic
        hidden_relation: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        创建角色间的社交关系

        Args:
            character_id_1: 角色1 ID
            character_id_2: 角色2 ID
            trust_level: 信任等级 (-100 到 100)
            bond_type: 关系类型
            hidden_relation: 隐藏关系描述
            metadata: 额外元数据

        Returns:
            Dict: 操作结果
        """
        self._transaction_stats["total_transactions"] += 1

        if not -100 <= trust_level <= 100:
            raise ValueError("trust_level 必须在 -100 到 100 之间")

        query = f"""
        MATCH (c1:{NodeType.CHARACTER.value} {{character_id: $character_id_1}})
        MATCH (c2:{NodeType.CHARACTER.value} {{character_id: $character_id_2}})
        MERGE (c1)-[r:{RelationType.SOCIAL_BOND.value}]->(c2)
        ON CREATE SET
            r.created_at = datetime($timestamp),
            r.trust_level = $trust_level,
            r.bond_type = $bond_type,
            r.hidden_relation = $hidden_relation,
            r.metadata = $metadata
        ON MATCH SET
            r.updated_at = datetime($timestamp),
            r.trust_level = $trust_level,
            r.bond_type = $bond_type,
            r.hidden_relation = COALESCE($hidden_relation, r.hidden_relation),
            r.metadata = COALESCE($metadata, r.metadata)
        RETURN r
        """

        params = {
            "character_id_1": character_id_1,
            "character_id_2": character_id_2,
            "trust_level": trust_level,
            "bond_type": bond_type,
            "hidden_relation": hidden_relation,
            "metadata": json.dumps(metadata or {}, ensure_ascii=False),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            async with self._get_session() as session:
                result = await session.run(query, params)
                record = await result.single()

                self._transaction_stats["successful_transactions"] += 1

                if record:
                    rel = record["r"]
                    return {
                        "success": True,
                        "type": RelationType.SOCIAL_BOND.value,
                        "from": character_id_1,
                        "to": character_id_2,
                        "trust_level": trust_level,
                        "bond_type": bond_type,
                        "relation": _neo4j_to_jsonable(dict(rel)),
                    }

                return {"success": False, "error": "创建关系失败"}

        except Exception as e:
            self._transaction_stats["failed_transactions"] += 1
            logger.error(f"create_social_bond 失败: {e}")
            raise

    async def create_influence(
        self,
        from_element_id: str,
        to_element_id: str,
        impact_score: float = 50.0,  # 0-100
        influence_type: str = "direct",  # direct, indirect, catalytic
        description: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        创建元素间的影响关系

        Args:
            from_element_id: 源元素ID
            to_element_id: 目标元素ID
            impact_score: 影响程度 (0-100)
            influence_type: 影响类型
            description: 影响描述
            metadata: 额外元数据

        Returns:
            Dict: 操作结果
        """
        self._transaction_stats["total_transactions"] += 1

        if not 0 <= impact_score <= 100:
            raise ValueError("impact_score 必须在 0 到 100 之间")

        query = f"""
        MATCH (from)
        WHERE from.character_id = $from_id OR from.plot_id = $from_id OR from.rule_id = $from_id
        MATCH (to)
        WHERE to.character_id = $to_id OR to.plot_id = $to_id OR to.rule_id = $to_id
        MERGE (from)-[r:{RelationType.INFLUENCES.value}]->(to)
        ON CREATE SET
            r.created_at = datetime($timestamp),
            r.impact_score = $impact_score,
            r.influence_type = $influence_type,
            r.description = $description,
            r.metadata = $metadata
        ON MATCH SET
            r.updated_at = datetime($timestamp),
            r.impact_score = $impact_score,
            r.influence_type = $influence_type,
            r.description = COALESCE($description, r.description),
            r.metadata = COALESCE($metadata, r.metadata)
        RETURN r
        """

        params = {
            "from_id": from_element_id,
            "to_id": to_element_id,
            "impact_score": impact_score,
            "influence_type": influence_type,
            "description": description,
            "metadata": json.dumps(metadata or {}, ensure_ascii=False),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            async with self._get_session() as session:
                result = await session.run(query, params)
                record = await result.single()

                self._transaction_stats["successful_transactions"] += 1

                if record:
                    rel = record["r"]
                    return {
                        "success": True,
                        "type": RelationType.INFLUENCES.value,
                        "from": from_element_id,
                        "to": to_element_id,
                        "impact_score": impact_score,
                        "influence_type": influence_type,
                        "relation": _neo4j_to_jsonable(dict(rel)),
                    }

                return {"success": False, "error": "创建关系失败"}

        except Exception as e:
            self._transaction_stats["failed_transactions"] += 1
            logger.error(f"create_influence 失败: {e}")
            raise

    # ============ 网络分析 ============

    async def get_character_network(
        self,
        character_id: str,
        depth: int = 2,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """
        获取角色的深度社交和因果网络

        Args:
            character_id: 角色ID
            depth: 遍历深度（默认2）
            include_hidden: 是否包含隐藏关系

        Returns:
            Dict: 角色网络数据
        {
            "character": {...},
            "social_network": [...],
            "influence_network": [...],
            "statistics": {...}
        }
        """
        query = f"""
        MATCH (center:{NodeType.CHARACTER.value} {{character_id: $character_id}})

        // 获取社交网络（双向）
        CALL {{
            WITH center
            MATCH (center)-[r1:SOCIAL_BOND*1..{depth}]-(connected:{NodeType.CHARACTER.value})
            RETURN connected,
                   r1,
                   'social' AS network_type,
                   length(r1) AS distance
        }}

        // 获取影响网络（出向）
        CALL {{
            WITH center
            MATCH (center)-[r2:INFLUENCES*1..{depth}]->(influenced)
            RETURN influenced AS connected,
                   r2,
                   'influence_out' AS network_type,
                   length(r2) AS distance
        }}

        // 获取影响网络（入向）
        CALL {{
            WITH center
            MATCH (influencer)-[r3:INFLUENCES*1..{depth}]->(center)
            RETURN influencer AS connected,
                   r3,
                   'influence_in' AS network_type,
                   length(r3) AS distance
        }}

        RETURN center,
               collect(DISTINCT {{
                 node: connected,
                 relationships: CASE network_type
                   WHEN 'social' THEN [r in r1 | r {{
                     type: 'SOCIAL_BOND',
                     trust_level: r.trust_level,
                     bond_type: r.bond_type,
                     hidden_relation: {include_hidden} OR r.hidden_relation IS NOT NULL ? r.hidden_relation : NULL,
                     distance: distance
                   }}]
                   WHEN 'influence_out' THEN [r in r2 | r {{
                     type: 'INFLUENCES',
                     impact_score: r.impact_score,
                     influence_type: r.influence_type,
                     direction: 'outgoing',
                     distance: distance
                   }}]
                   WHEN 'influence_in' THEN [r in r3 | r {{
                     type: 'INFLUENCES',
                     impact_score: r.impact_score,
                     influence_type: r.influence_type,
                     direction: 'incoming',
                     distance: distance
                   }}]
                 END,
                 network_type: network_type,
                 distance: distance
               }}) AS network_data
        """

        try:
            async with self._get_session() as session:
                result = await session.run(query, {"character_id": character_id})
                record = await result.single()

                if not record:
                    return {
                        "success": False,
                        "error": "角色不存在",
                        "character_id": character_id,
                    }

                center = _neo4j_to_jsonable(dict(record["center"]))
                network_data = record["network_data"]

                # 分类整理网络数据
                social_network = []
                influence_out = []
                influence_in = []

                stats = {
                    "total_connections": len(network_data),
                    "social_connections": 0,
                    "influence_outgoing": 0,
                    "influence_incoming": 0,
                    "average_trust_level": 0,
                    "average_impact_score": 0,
                    "hidden_relations_count": 0,
                }

                trust_levels = []
                impact_scores = []

                for item in network_data:
                    node = dict(item["node"])
                    network_type = item["network_type"]
                    distance = item["distance"]

                    for rel in item["relationships"]:
                        if rel["type"] == "SOCIAL_BOND":
                            social_network.append({
                                "character": node,
                                "trust_level": rel["trust_level"],
                                "bond_type": rel["bond_type"],
                                "hidden_relation": rel.get("hidden_relation"),
                                "distance": distance,
                            })
                            stats["social_connections"] += 1
                            trust_levels.append(rel["trust_level"])
                            if rel.get("hidden_relation"):
                                stats["hidden_relations_count"] += 1

                        elif rel["type"] == "INFLUENCES":
                            influence_data = {
                                "element": node,
                                "impact_score": rel["impact_score"],
                                "influence_type": rel["influence_type"],
                                "distance": distance,
                            }

                            if rel["direction"] == "outgoing":
                                influence_out.append(influence_data)
                                stats["influence_outgoing"] += 1
                            else:
                                influence_in.append(influence_data)
                                stats["influence_incoming"] += 1

                            impact_scores.append(rel["impact_score"])

                # 计算统计数据
                if trust_levels:
                    stats["average_trust_level"] = sum(trust_levels) / len(trust_levels)
                if impact_scores:
                    stats["average_impact_score"] = sum(impact_scores) / len(impact_scores)

                return {
                    "success": True,
                    "character": center,
                    "social_network": social_network,
                    "influence_network": {
                        "outgoing": influence_out,
                        "incoming": influence_in,
                    },
                    "statistics": stats,
                }

        except Exception as e:
            logger.error(f"get_character_network 失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "character_id": character_id,
            }

    # ============ 审核队列（GraphReviewQueue） ============

    def _serialize_review_node(self, node: Any) -> Dict[str, Any]:
        data = _neo4j_to_jsonable(dict(node))
        for key in ("created_at", "updated_at"):
            value = data.get(key)
            if hasattr(value, "isoformat"):
                data[key] = value.isoformat()
            elif value is not None:
                data[key] = str(value)
        for field in ("payload", "result"):
            raw = data.get(field)
            if isinstance(raw, str):
                try:
                    data[field] = json.loads(raw)
                except Exception:
                    data[field] = raw
        return data

    async def create_review_queue_entry(
        self,
        story_id: str,
        payload: Dict[str, Any],
        source: str = "extract",
        status: str = "pending",
    ) -> Dict[str, Any]:
        review_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        nodes_count = len(payload.get("nodes") or [])
        plot_nodes_count = len(payload.get("plot_nodes") or [])
        relationships_count = len(payload.get("relationships") or [])
        payload_json = json.dumps(payload, ensure_ascii=False)

        query = """
        CREATE (r:GraphReviewQueue {
            review_id: $review_id,
            story_id: $story_id,
            status: $status,
            source: $source,
            nodes_count: $nodes_count,
            plot_nodes_count: $plot_nodes_count,
            relationships_count: $relationships_count,
            created_at: datetime($timestamp),
            updated_at: datetime($timestamp),
            payload: $payload
        })
        RETURN r
        """

        params = {
            "review_id": review_id,
            "story_id": story_id,
            "status": status,
            "source": source,
            "nodes_count": nodes_count,
            "plot_nodes_count": plot_nodes_count,
            "relationships_count": relationships_count,
            "timestamp": timestamp,
            "payload": payload_json,
        }

        async with self._get_session() as session:
            result = await session.run(query, params)
            record = await result.single()
            if record:
                return self._serialize_review_node(record["r"])
        return {"review_id": review_id, "story_id": story_id, "status": status}

    async def list_review_queue_entries(
        self,
        story_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        status_value = status or ""
        query = """
        MATCH (r:GraphReviewQueue {story_id: $story_id})
        WHERE $status = "" OR r.status = $status
        RETURN r
        ORDER BY r.created_at DESC
        SKIP $offset
        LIMIT $limit
        """
        count_query = """
        MATCH (r:GraphReviewQueue {story_id: $story_id})
        WHERE $status = "" OR r.status = $status
        RETURN count(r) AS total
        """
        params = {"story_id": story_id, "status": status_value, "limit": limit, "offset": offset}
        async with self._get_session() as session:
            count_result = await session.run(count_query, params)
            count_record = await count_result.single()
            total = count_record["total"] if count_record else 0

            result = await session.run(query, params)
            items = []
            async for record in result:
                items.append(self._serialize_review_node(record["r"]))
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def get_review_queue_entry(self, review_id: str) -> Optional[Dict[str, Any]]:
        query = "MATCH (r:GraphReviewQueue {review_id: $review_id}) RETURN r"
        async with self._get_session() as session:
            result = await session.run(query, {"review_id": review_id})
            record = await result.single()
            if record:
                return self._serialize_review_node(record["r"])
        return None

    async def update_review_queue_status(
        self,
        review_id: str,
        status: str,
        result_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        timestamp = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(result_payload, ensure_ascii=False) if result_payload is not None else None
        query = """
        MATCH (r:GraphReviewQueue {review_id: $review_id})
        SET r.status = $status,
            r.updated_at = datetime($timestamp)
        FOREACH (_ IN CASE WHEN $result_payload IS NULL THEN [] ELSE [1] END |
            SET r.result = $result_payload
        )
        RETURN r
        """
        params = {
            "review_id": review_id,
            "status": status,
            "timestamp": timestamp,
            "result_payload": payload_json,
        }
        async with self._get_session() as session:
            result = await session.run(query, params)
            record = await result.single()
            if record:
                return self._serialize_review_node(record["r"])
        return None

    # ============ 查询操作 ============

    async def get_character_by_id(self, character_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取角色"""
        query = f"""
        MATCH (c:{NodeType.CHARACTER.value} {{character_id: $character_id}})
        RETURN c
        """

        try:
            async with self._get_session() as session:
                result = await session.run(query, {"character_id": character_id})
                record = await result.single()

                if record:
                    return _neo4j_to_jsonable(dict(record["c"]))

                return None

        except Exception as e:
            logger.error(f"get_character_by_id 失败: {e}")
            raise

    async def get_plot_by_story(
        self,
        story_id: str,
        order_by: str = "sequence_number",
    ) -> List[Dict[str, Any]]:
        """获取故事的所有情节（按顺序）"""
        valid_order_fields = ["sequence_number", "tension_score", "importance", "chapter", "timestamp"]
        if order_by not in valid_order_fields:
            raise ValueError(f"order_by 必须是以下之一: {valid_order_fields}")

        query = f"""
        MATCH (p:{NodeType.PLOT_NODE.value} {{story_id: $story_id}})
        RETURN p
        ORDER BY p.{order_by} ASC
        """

        try:
            async with self._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                records = await result.data()

                return [_neo4j_to_jsonable(dict(record["p"])) for record in records]

        except Exception as e:
            logger.error(f"get_plot_by_story 失败: {e}")
            raise

    async def search_characters(
        self,
        story_id: str,
        search_term: Optional[str] = None,
        status: Optional[CharacterStatus] = None,
        min_arc: Optional[float] = None,
        max_arc: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        搜索角色（支持多种过滤条件）

        Args:
            story_id: 故事ID
            search_term: 搜索关键词（全文本搜索）
            status: 角色状态过滤
            min_arc: 最小成长值
            max_arc: 最大成长值
            limit: 返回结果数量限制

        Returns:
            List[Dict]: 角色列表
        """
        conditions = ["c.story_id = $story_id"]
        params = {"story_id": story_id, "limit": limit}

        if search_term:
            conditions.append("toLower(c.name) CONTAINS toLower($search_term)")
            params["search_term"] = search_term

        if status:
            conditions.append("c.status = $status")
            params["status"] = status.value

        if min_arc is not None:
            conditions.append("c.arc >= $min_arc")
            params["min_arc"] = min_arc

        if max_arc is not None:
            conditions.append("c.arc <= $max_arc")
            params["max_arc"] = max_arc

        where_clause = " AND ".join(conditions)

        query = f"""
        MATCH (c:{NodeType.CHARACTER.value})
        WHERE {where_clause}
        RETURN c
        ORDER BY c.arc DESC
        LIMIT $limit
        """

        try:
            async with self._get_session() as session:
                result = await session.run(query, params)
                records = await result.data()

                return [_neo4j_to_jsonable(dict(record["c"])) for record in records]

        except Exception as e:
            logger.error(f"search_characters 失败: {e}")
            raise

    async def get_world_rules(
        self,
        story_id: str,
        rule_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取世界观规则"""
        conditions = ["r.story_id = $story_id"]
        params = {"story_id": story_id}

        if rule_type:
            conditions.append("r.rule_type = $rule_type")
            params["rule_type"] = rule_type

        where_clause = " AND ".join(conditions)

        query = f"""
        MATCH (r:{NodeType.WORLD_RULE.value})
        WHERE {where_clause}
        RETURN r
        ORDER BY r.severity, r.name
        """

        try:
            async with self._get_session() as session:
                result = await session.run(query, params)
                records = await result.data()

                return [_neo4j_to_jsonable(dict(record["r"])) for record in records]

        except Exception as e:
            logger.error(f"get_world_rules 失败: {e}")
            raise

    # ============ 统计和分析 ============

    async def get_story_statistics(self, story_id: str) -> Dict[str, Any]:
        """
        获取故事统计信息

        Returns:
            Dict: 统计数据
        """
        query = f"""
        MATCH (s:{NodeType.STORY.value} {{story_id: $story_id}})
        OPTIONAL MATCH (c:{NodeType.CHARACTER.value} {{story_id: $story_id}})
        WITH s, count(DISTINCT c) AS character_count

        OPTIONAL MATCH (p:{NodeType.PLOT_NODE.value} {{story_id: $story_id}})
        WITH character_count, count(DISTINCT p) AS plot_count

        OPTIONAL MATCH (r:{NodeType.WORLD_RULE.value} {{story_id: $story_id}})
        WITH character_count, plot_count, count(DISTINCT r) AS rule_count

        // 角色状态分布
        OPTIONAL MATCH (c2:{NodeType.CHARACTER.value} {{story_id: $story_id}})
        WITH character_count, plot_count, rule_count,
             collect(DISTINCT c2.status) AS status_list

        // 平均张力
        OPTIONAL MATCH (p2:{NodeType.PLOT_NODE.value} {{story_id: $story_id}})
        WITH character_count, plot_count, rule_count, status_list,
             avg(p2.tension_score) AS avg_tension

        // 关系统计
        OPTIONAL MATCH ()-[rel:SOCIAL_BOND]->()
        WITH character_count, plot_count, rule_count, status_list, avg_tension,
             count(DISTINCT rel) AS social_bond_count

        OPTIONAL MATCH ()-[rel2:INFLUENCES]->()
        WITH character_count, plot_count, rule_count, status_list, avg_tension,
             social_bond_count, count(DISTINCT rel2) AS influence_count

        RETURN character_count, plot_count, rule_count, status_list,
               avg_tension, social_bond_count, influence_count
        """

        try:
            async with self._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                record = await result.single()

                if record:
                    return {
                        "story_id": story_id,
                        "character_count": record["character_count"],
                        "plot_count": record["plot_count"],
                        "rule_count": record["rule_count"],
                        "status_distribution": record["status_list"],
                        "average_tension": record["avg_tension"],
                        "social_bond_count": record["social_bond_count"],
                        "influence_count": record["influence_count"],
                    }

                return {
                    "story_id": story_id,
                    "character_count": 0,
                    "plot_count": 0,
                    "rule_count": 0,
                    "status_distribution": [],
                    "average_tension": 0,
                    "social_bond_count": 0,
                    "influence_count": 0,
                }

        except Exception as e:
            logger.error(f"get_story_statistics 失败: {e}")
            raise

    # ============ 读取与维护 ============

    def _resolve_node_id(self, node: Any) -> str:
        """从节点属性中解析统一ID（优先节点自身唯一 ID，最后才是 story_id）"""
        if not node:
            return ""
        for key in ("character_id", "plot_id", "rule_id", "node_id", "story_id", "id", "name", "title"):
            value = node.get(key) if hasattr(node, "get") else None
            if value:
                return str(value)
        try:
            return str(node.id)
        except Exception:
            return ""

    async def get_story_elements(
        self,
        story_id: str,
        element_types: Optional[List[str]] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """获取故事的所有元素与关系"""
        labels = element_types or [
            NodeType.STORY.value,
            NodeType.CHARACTER.value,
            NodeType.PLOT_NODE.value,
            NodeType.WORLD_RULE.value,
            NodeType.LOCATION.value,
            NodeType.ITEM.value,
            NodeType.CONFLICT.value,
            NodeType.THEME.value,
            NodeType.MOTIVATION.value,
        ]

        query = """
        MATCH (n)
        WHERE n.story_id = $story_id AND any(l IN labels(n) WHERE l IN $labels)
        WITH n
        SKIP $offset
        LIMIT $limit
        WITH collect(DISTINCT n) AS nodes
        OPTIONAL MATCH (a)-[r]->(b)
        WHERE a.story_id = $story_id AND b.story_id = $story_id
          AND any(l IN labels(a) WHERE l IN $labels)
          AND any(l IN labels(b) WHERE l IN $labels)
        RETURN nodes, collect(DISTINCT r) AS relationships
        """

        try:
            async with self._get_session() as session:
                result = await session.run(
                    query,
                    {"story_id": story_id, "labels": labels, "limit": limit, "offset": offset},
                )
                record = await result.single()

                nodes = record["nodes"] if record else []
                relationships = record["relationships"] if record else []

                stories = []
                characters = []
                plot_nodes = []
                world_rules = []
                locations = set()
                conflicts = set()
                themes = set()
                graph_nodes = []

                for node in nodes:
                    node_labels = list(node.labels)
                    node_type = node_labels[0] if node_labels else "Unknown"
                    node_dict = _neo4j_to_jsonable(dict(node))
                    node_id = self._resolve_node_id(node_dict)
                    graph_nodes.append({
                        "id": node_id,
                        "labels": node_labels,
                        "properties": node_dict,
                        "type": node_type,
                    })

                    if node_type == NodeType.CHARACTER.value:
                        characters.append(node_dict)
                    elif node_type == NodeType.STORY.value:
                        stories.append(node_dict)
                    elif node_type == NodeType.PLOT_NODE.value:
                        plot_nodes.append(node_dict)
                        for loc in node_dict.get("locations", []) or []:
                            locations.add(loc)
                        for conflict in node_dict.get("conflicts", []) or []:
                            conflicts.add(conflict)
                        for theme in node_dict.get("themes", []) or []:
                            themes.add(theme)
                    elif node_type == NodeType.WORLD_RULE.value:
                        world_rules.append(node_dict)

                graph_relationships = []
                for rel in relationships:
                    try:
                        start_node = rel.start_node
                        end_node = rel.end_node
                        source_id = self._resolve_node_id(dict(start_node))
                        target_id = self._resolve_node_id(dict(end_node))
                        graph_relationships.append({
                            "id": str(rel.id),
                            "type": rel.type,
                            "source": source_id,
                            "target": target_id,
                            "properties": _neo4j_to_jsonable(dict(rel)),
                        })
                    except Exception:
                        continue

                try:
                    from utils.graph_enrichment import enrich_graph_relationships

                    graph_relationships = enrich_graph_relationships(
                        graph_nodes, graph_relationships
                    )
                except Exception as enrich_err:
                    logger.warning(f"关系推断补全跳过: {enrich_err}")

                return {
                    "stories": stories,
                    "characters": characters,
                    "plot_nodes": plot_nodes,
                    "world_rules": world_rules,
                    "relationships": graph_relationships,
                    "locations": sorted(locations),
                    "conflicts": sorted(conflicts),
                    "themes": sorted(themes),
                    "nodes": graph_nodes,
                }

        except Exception as e:
            logger.error(f"get_story_elements 失败: {e}")
            return {
                "stories": [],
                "characters": [],
                "plot_nodes": [],
                "world_rules": [],
                "relationships": [],
                "locations": [],
                "conflicts": [],
                "themes": [],
                "nodes": [],
            }

    async def search_nodes(
        self,
        story_id: str,
        query_text: str,
        node_types: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """搜索故事中的节点"""
        labels = node_types or [
            NodeType.STORY.value,
            NodeType.CHARACTER.value,
            NodeType.PLOT_NODE.value,
            NodeType.WORLD_RULE.value,
            NodeType.LOCATION.value,
            NodeType.ITEM.value,
            NodeType.CONFLICT.value,
            NodeType.THEME.value,
            NodeType.MOTIVATION.value,
        ]

        query = """
        MATCH (n)
        WHERE n.story_id = $story_id
          AND any(l IN labels(n) WHERE l IN $labels)
          AND (
            toLower(coalesce(n.name, '')) CONTAINS $q OR
            toLower(coalesce(n.title, '')) CONTAINS $q OR
            toLower(coalesce(n.description, '')) CONTAINS $q
          )
        RETURN n
        LIMIT $limit
        """

        try:
            async with self._get_session() as session:
                result = await session.run(
                    query,
                    {"story_id": story_id, "labels": labels, "q": query_text.lower(), "limit": limit},
                )
                records = await result.values("n")

                results = []
                for node in records:
                    node = node[0]  # result.values() 返回 [[node], ...]
                    node_labels = list(node.labels)
                    node_type = node_labels[0] if node_labels else "Unknown"
                    node_dict = _neo4j_to_jsonable(dict(node))
                    results.append({
                        "id": self._resolve_node_id(node_dict),
                        "labels": node_labels,
                        "properties": node_dict,
                        "type": node_type,
                    })
                return results
        except Exception as e:
            logger.error(f"search_nodes 失败: {e}")
            return []

    async def list_stories(self, limit: int = 200) -> List[Dict[str, Any]]:
        """列出所有故事"""
        query = """
        MATCH (s:Story)
        RETURN s
        ORDER BY s.created_at DESC
        LIMIT $limit
        """
        try:
            async with self._get_session() as session:
                result = await session.run(query, {"limit": limit})
                records = await result.values("s")
                return [_neo4j_to_jsonable(dict(node[0])) for node in records]
        except Exception as e:
            logger.error(f"list_stories 失败: {e}")
            return []

    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """获取故事详情"""
        query = "MATCH (s:Story {story_id: $story_id}) RETURN s"
        try:
            async with self._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                record = await result.single()
                return _neo4j_to_jsonable(dict(record["s"])) if record else None
        except Exception as e:
            logger.error(f"get_story 失败: {e}")
            return None

    async def delete_story(self, story_id: str) -> Dict[str, Any]:
        """删除故事（包含所有关联节点）"""
        query = """
        MATCH (s:Story {story_id: $story_id})
        OPTIONAL MATCH (n {story_id: $story_id})
        DETACH DELETE s, n
        RETURN count(s) AS deleted
        """
        try:
            async with self._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                record = await result.single()
                deleted = record["deleted"] if record else 0
                return {"success": deleted > 0, "deleted": deleted}
        except Exception as e:
            logger.error(f"delete_story 失败: {e}")
            raise

    async def create_relationship(
        self,
        story_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """创建通用关系"""
        query = f"""
        MATCH (a {{story_id: $story_id}}), (b {{story_id: $story_id}})
        WHERE (a.character_id = $source_id OR a.plot_id = $source_id OR a.rule_id = $source_id OR a.node_id = $source_id OR a.story_id = $source_id)
          AND (b.character_id = $target_id OR b.plot_id = $target_id OR b.rule_id = $target_id OR b.node_id = $target_id OR b.story_id = $target_id)
        MERGE (a)-[r:{relation_type}]->(b)
        SET r += $props
        RETURN r, id(r) AS rid
        """
        try:
            async with self._get_session() as session:
                result = await session.run(
                    query,
                    {"story_id": story_id, "source_id": source_id, "target_id": target_id, "props": properties or {}},
                )
                record = await result.single()
                if record:
                    rel = record["r"]
                    return {"success": True, "relationship": _neo4j_to_jsonable(dict(rel)), "id": str(record["rid"])}
                return {"success": False, "error": "创建关系失败"}
        except Exception as e:
            logger.error(f"create_relationship 失败: {e}")
            raise

    async def find_shortest_path(
        self,
        story_id: str,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> List[Dict[str, Any]]:
        """查找最短路径"""
        query = f"""
        MATCH (a {{story_id: $story_id}}), (b {{story_id: $story_id}})
        WHERE (a.character_id = $source_id OR a.plot_id = $source_id OR a.rule_id = $source_id OR a.node_id = $source_id OR a.story_id = $source_id)
          AND (b.character_id = $target_id OR b.plot_id = $target_id OR b.rule_id = $target_id OR b.node_id = $target_id OR b.story_id = $target_id)
        MATCH p = shortestPath((a)-[*..{max_depth}]-(b))
        RETURN p
        """
        try:
            async with self._get_session() as session:
                result = await session.run(query, {"story_id": story_id, "source_id": source_id, "target_id": target_id})
                record = await result.single()
                if not record:
                    return []
                path = record["p"]
                nodes = [dict(n) for n in path.nodes]
                relationships = [_neo4j_to_jsonable(dict(r)) for r in path.relationships]
                return [{"nodes": nodes, "relationships": relationships}]
        except Exception as e:
            logger.error(f"find_shortest_path 失败: {e}")
            return []

    async def update_node(
        self,
        node_type: NodeType,
        node_id: str,
        story_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新节点属性"""
        id_field = {
            NodeType.STORY: "story_id",
            NodeType.CHARACTER: "character_id",
            NodeType.PLOT_NODE: "plot_id",
            NodeType.WORLD_RULE: "rule_id",
            NodeType.LOCATION: "node_id",
            NodeType.ITEM: "node_id",
            NodeType.CONFLICT: "node_id",
            NodeType.THEME: "node_id",
            NodeType.MOTIVATION: "node_id",
        }.get(node_type)

        if not id_field:
            raise ValueError(f"不支持更新的节点类型: {node_type}")

        updates = {k: v for k, v in updates.items() if k not in {id_field, "story_id"}}

        if not updates:
            return {"success": False, "error": "无可更新字段"}

        set_clauses = [f"n.{key} = ${key}" for key in updates.keys()]
        set_query = ", ".join(set_clauses)

        query = f"""
        MATCH (n:{node_type.value} {{{id_field}: $node_id, story_id: $story_id}})
        SET {set_query}
        RETURN n
        """

        try:
            async with self._get_session() as session:
                result = await session.run(query, {"node_id": node_id, "story_id": story_id, **updates})
                record = await result.single()
                if record:
                    node = record["n"]
                    return {"success": True, "node": _neo4j_to_jsonable(dict(node))}
                return {"success": False, "error": "节点不存在"}
        except Exception as e:
            logger.error(f"update_node 失败: {e}")
            raise

    async def delete_node(
        self,
        node_type: NodeType,
        node_id: str,
        story_id: str,
    ) -> Dict[str, Any]:
        """删除节点（包含关系）"""
        id_field = {
            NodeType.STORY: "story_id",
            NodeType.CHARACTER: "character_id",
            NodeType.PLOT_NODE: "plot_id",
            NodeType.WORLD_RULE: "rule_id",
            NodeType.LOCATION: "node_id",
            NodeType.ITEM: "node_id",
            NodeType.CONFLICT: "node_id",
            NodeType.THEME: "node_id",
            NodeType.MOTIVATION: "node_id",
        }.get(node_type)

        if not id_field:
            raise ValueError(f"不支持删除的节点类型: {node_type}")

        query = f"""
        MATCH (n:{node_type.value} {{{id_field}: $node_id, story_id: $story_id}})
        DETACH DELETE n
        RETURN count(n) AS deleted
        """

        try:
            async with self._get_session() as session:
                result = await session.run(query, {"node_id": node_id, "story_id": story_id})
                record = await result.single()
                deleted = record["deleted"] if record else 0
                return {"success": deleted > 0, "deleted": deleted}
        except Exception as e:
            logger.error(f"delete_node 失败: {e}")
            raise

    async def delete_relationship(self, relationship_id: str) -> Dict[str, Any]:
        """删除关系"""
        query = """
        MATCH ()-[r]->()
        WHERE id(r) = toInteger($rel_id)
        DELETE r
        RETURN count(r) AS deleted
        """
        try:
            async with self._get_session() as session:
                result = await session.run(query, {"rel_id": relationship_id})
                record = await result.single()
                deleted = record["deleted"] if record else 0
                return {"success": deleted > 0, "deleted": deleted}
        except Exception as e:
            logger.error(f"delete_relationship 失败: {e}")
            raise

    async def execute_query(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """执行自定义 Cypher 查询（默认只允许读操作）"""
        unsafe_keywords = ["create ", "merge ", "delete ", "detach ", "set ", "call "]
        if any(keyword in cypher.lower() for keyword in unsafe_keywords):
            if os.getenv("GRAPH_QUERY_WRITE_ENABLED", "false").lower() != "true":
                raise ValueError("Write queries are disabled. Set GRAPH_QUERY_WRITE_ENABLED=true to allow.")

        try:
            async with self._get_session() as session:
                result = await session.run(cypher, parameters or {})
                return await result.data()
        except Exception as e:
            logger.error(f"execute_query 失败: {e}")
            raise

    def get_transaction_stats(self) -> Dict[str, Any]:
        """获取事务统计信息"""
        return self._transaction_stats.copy()


# ============ 单例模式 ============

_graph_manager_instance: Optional[GraphDBManager] = None


_graph_backend: str = "unknown"


async def get_graph_manager(
    uri: str = "bolt://localhost:7687",
    username: str = "neo4j",
    password: str = "",
    database: str = "neo4j",
):
    """
    获取图谱管理器单例。

    优先 Neo4j；连接失败时自动回退到 FileGraphStore（data/knowledge/graph），
    保证工具箱图谱页在无 Neo4j 时仍可生产级演示与审核。
    """
    global _graph_manager_instance, _graph_backend

    if _graph_manager_instance is not None:
        return _graph_manager_instance

    try:
        mgr = GraphDBManager(
            uri=uri,
            username=username,
            password=password,
            database=database,
        )
        await mgr.initialize()
        _graph_manager_instance = mgr
        _graph_backend = "neo4j"
        logger.info("图谱后端: Neo4j")
        return _graph_manager_instance
    except Exception as e:
        logger.warning("Neo4j 不可用，回退 FileGraphStore: %s", e)
        from utils.file_graph_store import get_file_graph_store

        _graph_manager_instance = await get_file_graph_store()
        _graph_backend = "file"
        return _graph_manager_instance


def get_graph_backend() -> str:
    return _graph_backend


async def close_graph_manager():
    """关闭 GraphDBManager 连接"""
    global _graph_manager_instance, _graph_backend

    if _graph_manager_instance:
        close = getattr(_graph_manager_instance, "close", None)
        if close:
            await close()
        _graph_manager_instance = None
        _graph_backend = "unknown"

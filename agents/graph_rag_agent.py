"""
GraphRAG 集成 Agent
GraphRAG Integration Agent

结合知识图谱和RAG（检索增强生成）的智能Agent：
1. 基于图谱的上下文检索
2. 多跳推理查询
3. 实体关系分析
4. 智能问答和内容生成

参考资源:
- GraphRAG最佳实践: https://www.51cto.com/aigc/7892.html
- Neo4j + LangChain: https://adg.csdn.net/6970ab1e437a6b40336b21b2.html

作者：Claude
创建时间：2025-02-08
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from agents.base_juben_agent import BaseJubenAgent
from utils.llm_client import get_llm_client
from utils.graph_enhanced import get_enhanced_graph_manager, GraphRAGQuery
from utils.project_types import StreamContentType

logger = logging.getLogger(__name__)


class QuestionType(str, Enum):
    """问题类型"""
    FACTUAL = "factual"           # 事实性问题（谁、什么、哪里）
    RELATIONSHIP = "relationship"  # 关系性问题（A与B的关系）
    TEMPORAL = "temporal"         # 时序性问题（何时、顺序）
    CAUSAL = "causal"             # 因果性问题（为什么、导致）
    ANALYTICAL = "analytical"     # 分析性问题（分析、对比）
    CREATIVE = "creative"         # 创作性问题（基于世界观生成）


@dataclass
class GraphContext:
    """图谱上下文"""
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    paths: List[List[Dict[str, Any]]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        """转换为文本格式（用于LLM）"""
        parts = []

        if self.entities:
            parts.append("## 相关实体\n")
            for entity in self.entities[:10]:  # 限制数量
                labels = entity.get("labels", [])
                props = entity.get("properties", entity)
                name = props.get("name", props.get("title", str(props.get("id", ""))))
                parts.append(f"- {':'.join(labels)}: {name}")

        if self.relationships:
            parts.append("\n## 关系网络\n")
            for rel in self.relationships[:10]:
                rel_type = rel.get("type", "")
                parts.append(f"- {rel_type}")

        if self.paths:
            parts.append("\n## 关联路径\n")
            for i, path in enumerate(self.paths[:5]):
                parts.append(f"- 路径 {i+1}: {' -> '.join([p.get('name', str(p.get('id', ''))) for p in path])}")

        return "\n".join(parts)


@dataclass
class RAGResponse:
    """RAG响应"""
    answer: str
    context: GraphContext
    confidence: float
    sources: List[str] = field(default_factory=list)
    reasoning: Optional[str] = None


class GraphRAGAgent(BaseJubenAgent):
    """
    GraphRAG 集成 Agent

    功能：
    1. 基于图谱的智能问答
    2. 多跳推理
    3. 实体关系分析
    4. 剧情一致性检查
    5. 世界观合规验证
    """

    def __init__(self, model_provider: str = "deepseek"):
        super().__init__("graph_rag_agent", model_provider)
        self.llm_client = get_llm_client(provider=model_provider)
        self.graph_manager = None

    async def _ensure_graph_manager(self):
        """惰性初始化图谱管理器（避免在同步 __init__ 里创建 task）。"""
        if self.graph_manager is None:
            self.graph_manager = await get_enhanced_graph_manager()
        return self.graph_manager

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理GraphRAG请求

        支持的操作类型：
        1. ask_question - 智能问答
        2. analyze_entity - 实体分析
        3. find_paths - 寻找路径
        4. check_consistency - 一致性检查
        5. verify_world_rules - 世界观验证
        """
        operation = request_data.get("operation", "ask_question")
        await self._ensure_graph_manager()

        if operation == "ask_question":
            async for event in self._ask_question(request_data):
                yield event
        elif operation == "analyze_entity":
            async for event in self._analyze_entity(request_data):
                yield event
        elif operation == "find_paths":
            async for event in self._find_paths(request_data):
                yield event
        elif operation == "check_consistency":
            async for event in self._check_consistency(request_data):
                yield event
        elif operation == "verify_world_rules":
            async for event in self._verify_world_rules(request_data):
                yield event
        else:
            yield {
                "event_type": "error",
                "data": {"error": f"未知操作类型: {operation}"}
            }

    async def _ask_question(
        self,
        request_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        智能问答

        Args:
            request_data: {
                "story_id": str,
                "question": str,
                "question_type": str (optional)
            }
        """
        story_id = request_data.get("story_id")
        question = request_data.get("question")

        if not story_id or not question:
            yield {
                "event_type": "error",
                "data": {"error": "缺少必需参数: story_id, question"}
            }
            return

        yield {
            "event_type": "tool_processing",
            "data": {"message": "正在分析问题..."}
        }

        # 分析问题类型
        question_type = await self._classify_question(question)

        # 从图谱检索相关上下文
        context = await self._retrieve_context(story_id, question, question_type)

        # 生成回答
        yield {
            "event_type": "tool_processing",
            "data": {"message": "正在生成回答..."}
        }

        answer = await self._generate_answer(question, context, question_type)

        yield {
            "event_type": "tool_complete",
            "data": {
                "result": {
                    "question": question,
                    "answer": answer.answer,
                    "confidence": answer.confidence,
                    "context_summary": context.to_text(),
                    "sources": answer.sources
                }
            }
        }

    async def _classify_question(self, question: str) -> QuestionType:
        """
        分类问题类型

        Args:
            question: 问题文本

        Returns:
            问题类型
        """
        # 使用LLM分类问题
        prompt = f"""请分类以下问题，选择最合适的类型：

问题: {question}

类型:
1. factual - 事实性问题（谁、什么、哪里）
2. relationship - 关系性问题（A与B的关系）
3. temporal - 时序性问题（何时、顺序）
4. causal - 因果性问题（为什么、导致）
5. analytical - 分析性问题（分析、对比）
6. creative - 创作性问题（基于世界观生成）

只返回类型名称，不要其他内容。"""

        try:
            response = await self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )

            answer = response.get("content", "").strip().lower()

            # 映射到枚举
            for qt in QuestionType:
                if qt.value in answer:
                    return qt

            return QuestionType.FACTUAL  # 默认

        except Exception as e:
            logger.error(f"问题分类失败: {e}")
            return QuestionType.FACTUAL

    async def _retrieve_context(
        self,
        story_id: str,
        question: str,
        question_type: QuestionType
    ) -> GraphContext:
        """
        从图谱检索相关上下文

        Args:
            story_id: 故事ID
            question: 问题
            question_type: 问题类型

        Returns:
            图谱上下文
        """
        context = GraphContext()

        try:
            # 提取问题中的关键词
            keywords = await self._extract_keywords(question)

            # 根据问题类型执行不同的查询
            if question_type == QuestionType.RELATIONSHIP:
                # 查询关系
                query = """
                MATCH (a)-[r]-(b)
                WHERE a.story_id = $story_id OR b.story_id = $story_id
                RETURN a, r, b
                LIMIT 20
                """
                records, _ = await self.graph_manager.execute_query(
                    query,
                    parameters={"story_id": story_id}
                )

                for record in records:
                    context.relationships.append({
                        "type": record.get("r", {}).get("type", ""),
                        "source": record.get("a", {}),
                        "target": record.get("b", {})
                    })

            elif question_type == QuestionType.TEMPORAL:
                # 查询时序信息
                query = """
                MATCH (p:PlotNode)
                WHERE p.story_id = $story_id
                RETURN p
                ORDER BY p.sequence_number
                LIMIT 30
                """
                records, _ = await self.graph_manager.execute_query(
                    query,
                    parameters={"story_id": story_id}
                )

                for record in records:
                    plot = record.get("p", {})
                    context.entities.append({
                        "labels": ["PlotNode"],
                        "properties": plot
                    })

            else:
                # 通用查询：全文搜索
                for keyword in keywords[:5]:
                    query = f"""
                    CALL db.index.fulltext.queryNodes('character_fulltext', '{keyword}')
                    YIELD node, score
                    WHERE node.story_id = '{story_id}'
                    RETURN node, score
                    LIMIT 5
                    """

                    try:
                        records, _ = await self.graph_manager.execute_query(query)
                        for record in records:
                            context.entities.append({
                                "labels": list(record.get("node", {}).get("labels", [])),
                                "properties": dict(record.get("node", {}))
                            })
                    except:
                        pass

        except Exception as e:
            logger.error(f"检索上下文失败: {e}")

        return context

    async def _extract_keywords(self, question: str) -> List[str]:
        """从问题中提取关键词"""
        # 简单实现：使用分词或规则
        # 实际应用中可以使用更复杂的NLP方法
        import re

        # 移除标点符号
        clean_question = re.sub(r'[^\w\s]', '', question)

        # 分词
        words = clean_question.split()

        # 过滤停用词
        stopwords = {"的", "是", "在", "有", "和", "与", "了", "吗", "呢", "如何", "什么", "谁", "哪里"}
        keywords = [w for w in words if w not in stopwords and len(w) > 1]

        return keywords

    async def _generate_answer(
        self,
        question: str,
        context: GraphContext,
        question_type: QuestionType
    ) -> RAGResponse:
        """
        基于上下文生成回答

        Args:
            question: 问题
            context: 图谱上下文
            question_type: 问题类型

        Returns:
            RAG响应
        """
        prompt = f"""你是一个专业的剧本创作助手。请根据以下图谱信息回答用户问题。

## 用户问题
{question}

## 图谱上下文
{context.to_text()}

## 要求
1. 基于图谱信息给出准确回答
2. 如果图谱信息不足，诚实说明
3. 保持回答简洁明了
4. 可以适当推理，但要明确标注

请回答:"""

        try:
            response = await self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            answer = response.get("content", "")

            # 评估置信度（简单实现）
            confidence = 0.7
            if len(context.entities) > 0 or len(context.relationships) > 0:
                confidence = 0.9
            elif "不知道" in answer or "无法确定" in answer:
                confidence = 0.3

            return RAGResponse(
                answer=answer,
                context=context,
                confidence=confidence,
                sources=[f"graph_{story_id}"]
            )

        except Exception as e:
            logger.error(f"生成回答失败: {e}")
            return RAGResponse(
                answer=f"抱歉，生成回答时出错: {str(e)}",
                context=context,
                confidence=0.0
            )

    async def _analyze_entity(
        self,
        request_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        分析实体

        Args:
            request_data: {
                "story_id": str,
                "entity_id": str,
                "entity_type": str,
                "depth": int (optional, default 2)
            }
        """
        yield {
            "event_type": "tool_processing",
            "data": {"message": "正在分析实体..."}
        }

        story_id = request_data.get("story_id")
        entity_id = request_data.get("entity_id")
        entity_type = request_data.get("entity_type", "Character")
        depth = request_data.get("depth", 2)

        # 获取实体上下文
        query = GraphRAGQuery.get_context_for_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            depth=depth,
            limit=50
        )

        records, _ = await self.graph_manager.execute_query(
            query,
            parameters={"entity_id": entity_id}
        )

        # 生成分析报告
        prompt = f"""请分析以下实体及其关系网络：

## 实体ID: {entity_id}
## 类型: {entity_type}

## 相关数据
{records[:20]}

请提供：
1. 实体概述
2. 主要关系
3. 在故事中的作用
4. 建议的情节发展方向"""

        response = await self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )

        yield {
            "event_type": "tool_complete",
            "data": {
                "result": {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "analysis": response.get("content", ""),
                    "related_entities_count": len(records) if isinstance(records, list) else 0
                }
            }
        }

    async def _find_paths(
        self,
        request_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        寻找实体间的路径

        Args:
            request_data: {
                "story_id": str,
                "start_entity": str,
                "end_entity": str,
                "max_depth": int (optional, default 5)
            }
        """
        yield {
            "event_type": "tool_processing",
            "data": {"message": "正在寻找路径..."}
        }

        start_entity = request_data.get("start_entity")
        end_entity = request_data.get("end_entity")
        max_depth = request_data.get("max_depth", 5)

        query = f"""
        MATCH path = shortestPath(
            (start{{character_id: $start_entity}})-[*1..{max_depth}]-(end{{character_id: $end_entity}})
        )
        RETURN [node in nodes(path) | node.name] as path_names,
               [rel in relationships(path) | type(rel)] as rel_types
        """

        try:
            records, _ = await self.graph_manager.execute_query(
                query,
                parameters={
                    "start_entity": start_entity,
                    "end_entity": end_entity
                }
            )

            if not records or len(records) == 0:
                yield {
                    "event_type": "tool_complete",
                    "data": {
                        "result": {
                            "start_entity": start_entity,
                            "end_entity": end_entity,
                            "paths": [],
                            "message": "未找到路径"
                        }
                    }
                }
                return

            paths = []
            for record in records:
                paths.append({
                    "path": record.get("path_names", []),
                    "relationships": record.get("rel_types", [])
                })

            yield {
                "event_type": "tool_complete",
                "data": {
                    "result": {
                        "start_entity": start_entity,
                        "end_entity": end_entity,
                        "paths": paths,
                        "path_count": len(paths)
                    }
                }
            }

        except Exception as e:
            yield {
                "event_type": "error",
                "data": {"error": f"路径查找失败: {str(e)}"}
            }

    async def _check_consistency(
        self,
        request_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        检查剧情一致性

        Args:
            request_data: {
                "story_id": str,
                "check_type": str (optional)
            }
        """
        yield {
            "event_type": "tool_processing",
            "data": {"message": "正在检查一致性..."}
        }

        # 调用逻辑一致性检测Agent
        from agents.logic_consistency_agent import LogicConsistencyAgent

        agent = LogicConsistencyAgent()

        async for event in agent.process_request(request_data):
            yield event

    async def _verify_world_rules(
        self,
        request_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        验证世界观合规性

        Args:
            request_data: {
                "story_id": str,
                "plot_data": Dict[str, Any]
            }
        """
        yield {
            "event_type": "tool_processing",
            "data": {"message": "正在验证世界观规则..."}
        }

        story_id = request_data.get("story_id")
        plot_data = request_data.get("plot_data", {})

        # 查询相关世界观规则
        query = """
        MATCH (w:WorldRule)
        WHERE w.story_id = $story_id
        RETURN w
        """

        try:
            records, _ = await self.graph_manager.execute_query(
                query,
                parameters={"story_id": story_id}
            )

            world_rules = []
            for record in records:
                rule = record.get("w", {})
                world_rules.append({
                    "name": rule.get("name", ""),
                    "description": rule.get("description", ""),
                    "rule_type": rule.get("rule_type", ""),
                    "severity": rule.get("severity", "strict")
                })

            # 使用LLM验证
            prompt = f"""请验证以下情节是否遵守世界观规则：

## 情节信息
{plot_data}

## 世界观规则
{world_rules}

请检查：
1. 是否违反任何规则
2. 如有违反，严重程度如何
3. 给出修改建议

返回格式：
- 违反规则：[是/否]
- 违反规则列表：[...]
- 严重程度：[critical/high/medium/low/none]
- 修改建议：[...]"""

            response = await self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            yield {
                "event_type": "tool_complete",
                "data": {
                    "result": {
                        "story_id": story_id,
                        "verification": response.get("content", ""),
                        "rules_checked": len(world_rules)
                    }
                }
            }

        except Exception as e:
            yield {
                "event_type": "error",
                "data": {"error": f"世界观验证失败: {str(e)}"}
            }

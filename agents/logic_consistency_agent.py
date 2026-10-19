"""
剧本逻辑一致性检测 Agent
Logic Consistency Detection Agent for Screenplay Creation

功能核心：
基于图数据库执行 Cypher 逻辑审计，检测剧本中的逻辑矛盾和冲突

审计规则：
1. 时空冲突：同一时间点，同一角色不能出现在两个地点
2. 生命状态：已死亡角色不能有后续行动
3. 动机缺失：重大事件需要有动机支持
4. 关系一致：社交关系变化需要合理解释
5. 知识连续：角色能力/记忆需要保持一致
6. 世界观冲突：情节不能违反世界观规则

工作流程：
- 扫描图数据库中的角色、情节、关系
- 执行 Cypher 查询检测逻辑冲突
- 生成一致性报告
- 如果分数 < 80，触发回滚机制

作者：Claude
创建时间：2025-02-08
"""

import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_juben_agent import BaseJubenAgent


class IssueSeverity(str, Enum):
    """问题严重程度"""
    CRITICAL = "critical"    # 严重冲突，必须修复
    HIGH = "high"           # 高优先级，强烈建议修复
    MEDIUM = "medium"       # 中等优先级，建议修复
    LOW = "low"            # 低优先级，可选择性修复
    INFO = "info"          # 信息提示


class IssueCategory(str, Enum):
    """问题类别"""
    SPATIOTEMPORAL = "spatiotemporal"    # 时空冲突
    CHARACTER_STATUS = "character_status"  # 角色状态
    MOTIVATION = "motivation"            # 动机缺失
    RELATIONSHIP = "relationship"        # 关系一致性
    KNOWLEDGE = "knowledge"              # 知识连续性
    WORLD_RULE = "world_rule"            # 世界观冲突
    PLOT_COHERENCE = "plot_coherence"    # 情节连贯性


@dataclass
class ConsistencyIssue:
    """一致性问题"""
    issue_id: str
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    location: str  # 问题位置（章节/情节ID）
    affected_elements: List[str]  # 受影响的元素ID
    evidence: Dict[str, Any] = field(default_factory=dict)  # 证据
    suggested_fix: Optional[str] = None  # 修复建议
    confidence: float = 1.0  # 确信度 (0-1)


@dataclass
class ConsistencyReport:
    """一致性报告"""
    story_id: str
    scan_time: str
    overall_score: float  # 总体分数 (0-100)
    passed: bool  # 是否通过（分数 >= 80）
    issues: List[ConsistencyIssue]
    statistics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class LogicConsistencyAgent(BaseJubenAgent):
    """
    剧本逻辑一致性检测 Agent

    核心功能：
    1. 基于图数据库的逻辑审计
    2. 多维度一致性检测
    3. 自动生成修复建议
    4. 触发回滚机制
    """

    def __init__(self, model_provider: str = "deepseek"):
        """初始化逻辑一致性检测 Agent"""
        super().__init__("logic_consistency", model_provider)

        # 审计配置
        self.passing_score = 80.0
        self.critical_threshold = 60.0

        # 审计规则权重
        self.rule_weights = {
            IssueCategory.SPATIOTEMPORAL: 0.25,
            IssueCategory.CHARACTER_STATUS: 0.20,
            IssueCategory.MOTIVATION: 0.15,
            IssueCategory.RELATIONSHIP: 0.10,
            IssueCategory.KNOWLEDGE: 0.10,
            IssueCategory.WORLD_RULE: 0.10,
            IssueCategory.PLOT_COHERENCE: 0.10,
        }

        # 严重程度扣分
        self.severity_penalties = {
            IssueSeverity.CRITICAL: 25.0,
            IssueSeverity.HIGH: 15.0,
            IssueSeverity.MEDIUM: 8.0,
            IssueSeverity.LOW: 3.0,
            IssueSeverity.INFO: 0.0,
        }

        self.logger.info("逻辑一致性检测 Agent 初始化完成")

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理逻辑一致性检测请求

        Args:
            request_data: 请求数据
                - story_id: 故事ID
                - scan_depth: 扫描深度（可选）
                - check_rules: 要检查的规则列表（可选，默认全部）
            context: 上下文信息

        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            story_id = request_data.get("story_id", "")
            scan_depth = request_data.get("scan_depth", "all")
            check_rules = request_data.get("check_rules", [])
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"

            if not story_id:
                yield {
                    "event_type": "error",
                    "data": {
                        "error": "缺少 story_id 参数",
                        "message": "请提供要检测的故事ID"
                    }
                }
                return

            self.logger.info(f"开始逻辑一致性检测: story_id={story_id}")

            # 发送开始事件
            yield {
                "event_type": "tool_start",
                "data": {
                    "tool_name": "logic_consistency_check",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "story_id": story_id,
                }
            }

            # 进度更新
            yield {
                "event_type": "tool_processing",
                "data": {
                    "message": "正在连接图数据库...",
                    "progress": 10,
                }
            }

            # 获取图数据库连接
            from utils.graph_manager import get_graph_manager
            graph_manager = await get_graph_manager()

            # 执行一致性检测
            yield {
                "event_type": "tool_processing",
                "data": {
                    "message": "正在执行逻辑审计...",
                    "progress": 30,
                }
            }

            report = await self.perform_consistency_check(
                graph_manager=graph_manager,
                story_id=story_id,
                scan_depth=scan_depth,
                check_rules=check_rules,
            )

            # 发送检测结果
            yield {
                "event_type": "tool_processing",
                "data": {
                    "message": "正在生成检测报告...",
                    "progress": 80,
                }
            }

            # 生成可读报告
            report_text = await self._generate_readable_report(report)

            # 把报告正文作为 llm_chunk 流式输出（否则 tool_complete 的 result 不显示为正文）
            if report_text:
                yield {"event_type": "llm_chunk", "data": report_text, "metadata": {}}

            yield {
                "event_type": "tool_complete",
                "data": {
                    "tool_name": "logic_consistency_check",
                    "result": {
                        "report": report.__dict__,
                        "report_text": report_text,
                        "passed": report.passed,
                        "score": report.overall_score,
                        "issue_count": len(report.issues),
                        "critical_issues": len([i for i in report.issues if i.severity == IssueSeverity.CRITICAL]),
                        "rollback_required": not report.passed,
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            }

            # 如果未通过，发送回滚建议
            if not report.passed:
                yield {
                    "event_type": "rollback_suggested",
                    "data": {
                        "reason": f"逻辑一致性检测未通过（分数: {report.overall_score:.2f}）",
                        "score": report.overall_score,
                        "threshold": self.passing_score,
                        "critical_issues": len([i for i in report.issues if i.severity == IssueSeverity.CRITICAL]),
                        "recommendations": report.recommendations,
                    }
                }

        except Exception as e:
            self.logger.error(f"逻辑一致性检测失败: {e}")
            yield {
                "event_type": "error",
                "data": {
                    "error": str(e),
                    "message": "逻辑一致性检测过程中发生错误"
                }
            }

    async def perform_consistency_check(
        self,
        graph_manager,
        story_id: str,
        scan_depth: str = "all",
        check_rules: List[str] = None,
    ) -> ConsistencyReport:
        """
        执行一致性检查

        Args:
            graph_manager: 图数据库管理器
            story_id: 故事ID
            scan_depth: 扫描深度
            check_rules: 要检查的规则列表

        Returns:
            ConsistencyReport: 一致性报告
        """
        issues = []
        statistics = {}

        # 确定要检查的规则
        if not check_rules:
            check_rules = [
                "spatiotemporal",
                "character_status",
                "motivation",
                "relationship",
                "knowledge",
                "world_rule",
                "plot_coherence",
            ]

        # 1. 时空冲突检测
        if "spatiotemporal" in check_rules:
            spatial_issues = await self._check_spatial_consistency(
                graph_manager, story_id
            )
            issues.extend(spatial_issues)
            statistics["spatial_checks"] = len(spatial_issues)

        # 2. 生命状态检测
        if "character_status" in check_rules:
            status_issues = await self._check_character_status_consistency(
                graph_manager, story_id
            )
            issues.extend(status_issues)
            statistics["status_checks"] = len(status_issues)

        # 3. 动机缺失检测
        if "motivation" in check_rules:
            motivation_issues = await self._check_motivation_consistency(
                graph_manager, story_id
            )
            issues.extend(motivation_issues)
            statistics["motivation_checks"] = len(motivation_issues)

        # 4. 关系一致性检测
        if "relationship" in check_rules:
            relationship_issues = await self._check_relationship_consistency(
                graph_manager, story_id
            )
            issues.extend(relationship_issues)
            statistics["relationship_checks"] = len(relationship_issues)

        # 5. 知识连续性检测
        if "knowledge" in check_rules:
            knowledge_issues = await self._check_knowledge_consistency(
                graph_manager, story_id
            )
            issues.extend(knowledge_issues)
            statistics["knowledge_checks"] = len(knowledge_issues)

        # 6. 世界观冲突检测
        if "world_rule" in check_rules:
            rule_issues = await self._check_world_rule_consistency(
                graph_manager, story_id
            )
            issues.extend(rule_issues)
            statistics["rule_checks"] = len(rule_issues)

        # 7. 情节连贯性检测
        if "plot_coherence" in check_rules:
            plot_issues = await self._check_plot_coherence(
                graph_manager, story_id
            )
            issues.extend(plot_issues)
            statistics["plot_coherence_checks"] = len(plot_issues)

        # 计算总体分数
        overall_score = self._calculate_overall_score(issues)

        # 生成建议
        recommendations = self._generate_recommendations(issues)

        return ConsistencyReport(
            story_id=story_id,
            scan_time=datetime.now(timezone.utc).isoformat(),
            overall_score=overall_score,
            passed=overall_score >= self.passing_score,
            issues=issues,
            statistics=statistics,
            recommendations=recommendations,
        )

    async def _check_spatial_consistency(
        self,
        graph_manager,
        story_id: str,
    ) -> List[ConsistencyIssue]:
        """
        检查时空一致性

        规则：同一时间点，同一角色不能出现在两个地点
        """
        issues = []

        # Cypher 查询：查找同一角色的时空冲突
        query = """
        MATCH (c:Character {story_id: $story_id})
        MATCH (c)-[:INVOLVED_IN]->(p1:PlotNode {story_id: $story_id})
        MATCH (c)-[:INVOLVED_IN]->(p2:PlotNode {story_id: $story_id})
        WHERE p1.sequence_number = p2.sequence_number
          AND p1 <> p2
          AND p1.location IS NOT NULL
          AND p2.location IS NOT NULL
          AND p1.location <> p2.location
        RETURN c.character_id AS character_id,
               c.name AS character_name,
               p1.sequence_number AS seq,
               p1.title AS plot1_title,
               p1.location AS location1,
               p2.title AS plot2_title,
               p2.location AS location2
        ORDER BY seq
        """

        try:
            async with graph_manager._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                records = await result.data()

                for idx, record in enumerate(records):
                    issue = ConsistencyIssue(
                        issue_id=f"spatial_{idx}_{story_id}",
                        category=IssueCategory.SPATIOTEMPORAL,
                        severity=IssueSeverity.CRITICAL,
                        title=f"角色出现在两个不同地点",
                        description=f"角色「{record['character_name']}」在第 {record['seq']} 章同时出现在 {record['location1']}（{record['plot1_title']}）和 {record['location2']}（{record['plot2_title']}）",
                        location=f"第 {record['seq']} 章",
                        affected_elements=[
                            record['character_id'],
                            f"plot_seq_{record['seq']}",
                        ],
                        evidence={
                            "sequence_number": record['seq'],
                            "location1": record['location1'],
                            "location2": record['location2'],
                            "plot1": record['plot1_title'],
                            "plot2": record['plot2_title'],
                        },
                        suggested_fix=f"修改其中一个情节的地点，或调整情节顺序使角色有时间移动",
                        confidence=0.95,
                    )
                    issues.append(issue)

        except Exception as e:
            self.logger.error(f"时空一致性检查失败: {e}")

        return issues

    async def _check_character_status_consistency(
        self,
        graph_manager,
        story_id: str,
    ) -> List[ConsistencyIssue]:
        """
        检查角色状态一致性

        规则：已死亡角色不能有后续行动
        """
        issues = []

        # Cypher 查询：查找已死亡角色的后续行动
        query = """
        // 找到所有死亡角色及其死亡位置
        MATCH (c:Character {story_id: $story_id})
        WHERE c.status = 'deceased'

        // 找到该角色参与的情节
        MATCH (c)-[:INVOLVED_IN]->(death_plot:PlotNode {story_id: $story_id})
        WITH c, death_plot, min(death_plot.sequence_number) AS death_seq

        // 查找死亡后的情节
        MATCH (c)-[:INVOLVED_IN]->(after_plot:PlotNode {story_id: $story_id})
        WHERE after_plot.sequence_number > death_seq
        RETURN c.character_id AS character_id,
               c.name AS character_name,
               death_seq AS death_sequence,
               collect({
                 seq: after_plot.sequence_number,
                 title: after_plot.title,
                 description: after_plot.description
               }) AS afterlife_actions
        ORDER BY death_sequence
        """

        try:
            async with graph_manager._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                records = await result.data()

                for idx, record in enumerate(records):
                    actions = record['afterlife_actions']
                    action_summary = ", ".join([f"第{a['seq']}章《{a['title']}》" for a in actions[:3]])
                    if len(actions) > 3:
                        action_summary += f" 等{len(actions)}个情节"

                    issue = ConsistencyIssue(
                        issue_id=f"status_{idx}_{story_id}",
                        category=IssueCategory.CHARACTER_STATUS,
                        severity=IssueSeverity.CRITICAL,
                        title=f"已死亡角色有后续行动",
                        description=f"角色「{record['character_name']}」在第 {record['death_sequence']} 章后死亡，但仍有后续行动：{action_summary}",
                        location=f"第 {record['death_sequence']} 章之后",
                        affected_elements=[
                            record['character_id'],
                            *[f"plot_{a['seq']}" for a in actions],
                        ],
                        evidence={
                            "death_sequence": record['death_sequence'],
                            "afterlife_actions": actions,
                        },
                        suggested_fix=f"删除死亡后的角色行动，或修改角色状态为「失踪/假死」",
                        confidence=1.0,
                    )
                    issues.append(issue)

        except Exception as e:
            self.logger.error(f"角色状态一致性检查失败: {e}")

        return issues

    async def _check_motivation_consistency(
        self,
        graph_manager,
        story_id: str,
    ) -> List[ConsistencyIssue]:
        """
        检查动机一致性

        规则：重大事件需要有动机支持
        """
        issues = []

        # Cypher 查询：查找高重要性但缺乏动机连接的情节
        query = """
        // 查找高重要性情节
        MATCH (p:PlotNode {story_id: $story_id})
        WHERE p.importance >= 80

        // 查找涉及的角色
        MATCH (p)-[:INVOLVED_IN]-(c:Character {story_id: $story_id})

        // 检查角色是否有相关动机
        OPTIONAL MATCH (c)-[m:DRIVEN_BY]->(motivation)

        WITH p, c, count(motivation) AS motivation_count

        // 如果主角角缺乏动机连接
        WHERE motivation_count = 0

        RETURN p.plot_id AS plot_id,
               p.title AS plot_title,
               p.sequence_number AS seq,
               p.importance AS importance,
               p.description AS description,
               collect(DISTINCT c.name) AS characters_without_motivation
        ORDER BY importance DESC, seq
        """

        try:
            async with graph_manager._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                records = await result.data()

                for idx, record in enumerate(records):
                    characters = "、".join(record['characters_without_motivation'])

                    issue = ConsistencyIssue(
                        issue_id=f"motivation_{idx}_{story_id}",
                        category=IssueCategory.MOTIVATION,
                        severity=IssueSeverity.HIGH,
                        title=f"重大情节缺乏动机支撑",
                        description=f"情节「{record['plot_title']}」重要性为 {record['importance']}，但涉及角色 {characters} 缺乏明确的动机连接",
                        location=f"第 {record['seq']} 章",
                        affected_elements=[record['plot_id']],
                        evidence={
                            "importance": record['importance'],
                            "description": record['description'],
                            "characters": record['characters_without_motivation'],
                        },
                        suggested_fix=f"为相关角色添加动机，或降低情节重要性",
                        confidence=0.75,
                    )
                    issues.append(issue)

        except Exception as e:
            self.logger.error(f"动机一致性检查失败: {e}")

        return issues

    async def _check_relationship_consistency(
        self,
        graph_manager,
        story_id: str,
    ) -> List[ConsistencyIssue]:
        """
        检查关系一致性

        规则：社交关系变化需要合理过渡
        """
        issues = []

        # Cypher 查询：查找突兀的信任等级变化
        query = """
        // 查找同一对角色的多个关系
        MATCH (c1:Character {story_id: $story_id})-[r1:SOCIAL_BOND]->(c2:Character {story_id: $story_id})

        // 获取涉及这些角色的情节序列
        OPTIONAL MATCH (c1)-[:INVOLVED_IN]->(p1:PlotNode)
        OPTIONAL MATCH (c2)-[:INVOLVED_IN]->(p2:PlotNode)

        // 查找关系时间线索索
        WITH c1, c2, r1,
             min(p1.sequence_number) AS c1_first_appearance,
             min(p2.sequence_number) AS c2_first_appearance

        // 查找信任等级的剧烈变化
        MATCH (c1)-[r2:SOCIAL_BOND]->(c2)
        WHERE r1.created_at < r2.created_at
          AND abs(r1.trust_level - r2.trust_level) >= 50

        RETURN c1.character_id AS char1_id,
               c1.name AS char1_name,
               c2.character_id AS char2_id,
               c2.name AS char2_name,
               r1.trust_level AS old_trust,
               r2.trust_level AS new_trust,
               r1.bond_type AS old_type,
               r2.bond_type AS new_type,
               r1.created_at AS old_time,
               r2.created_at AS new_time
        ORDER BY r2.created_at
        """

        try:
            async with graph_manager._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                records = await result.data()

                for idx, record in enumerate(records):
                    trust_change = record['new_trust'] - record['old_trust']

                    issue = ConsistencyIssue(
                        issue_id=f"relationship_{idx}_{story_id}",
                        category=IssueCategory.RELATIONSHIP,
                        severity=IssueSeverity.MEDIUM,
                        title=f"社交关系变化突兀",
                        description=f"{record['char1_name']} 与 {record['char2_name']} 的信任等级从 {record['old_trust']} 突变为 {record['new_trust']}（变化: {trust_change:+d}）",
                        location=f"整个故事",
                        affected_elements=[
                            record['char1_id'],
                            record['char2_id'],
                        ],
                        evidence={
                            "old_trust": record['old_trust'],
                            "new_trust": record['new_trust'],
                            "old_type": record['old_type'],
                            "new_type": record['new_type'],
                            "change": trust_change,
                        },
                        suggested_fix=f"在关系变化之间添加过渡情节，展示关系演变过程",
                        confidence=0.70,
                    )
                    issues.append(issue)

        except Exception as e:
            self.logger.error(f"关系一致性检查失败: {e}")

        return issues

    async def _check_knowledge_consistency(
        self,
        graph_manager,
        story_id: str,
    ) -> List[ConsistencyIssue]:
        """
        检查知识连续性

        规则：角色能力/记忆需要保持一致
        """
        issues = []

        # Cypher 查询：查找能力不一致
        query = """
        // 查找角色能力变化
        MATCH (c:Character {story_id: $story_id})

        // 假设我们在节点中存储了能力信息（通过 metadata）
        WHERE c.strengths IS NOT NULL

        // 查找角色参与的情节
        MATCH (c)-[:INVOLVED_IN]->(p:PlotNode {story_id: $story_id})

        // 检查情节描述是否与角色能力一致
        // 这里简化处理，实际需要 NLP 分析
        WHERE (p.description CONTAINS '剑法' AND NOT '剑' IN c.strengths)
           OR (p.description CONTAINS '内功' AND NOT '内功' IN c.strengths)

        RETURN c.character_id AS character_id,
               c.name AS character_name,
               c.strengths AS strengths,
               collect({
                 seq: p.sequence_number,
                 title: p.title,
                 description: p.description
               }) AS mismatched_plots
        LIMIT 10
        """

        try:
            async with graph_manager._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                records = await result.data()

                for idx, record in enumerate(records):
                    plots_info = "; ".join([
                        f"第{p['seq']}章「{p['title']}」"
                        for p in record['mismatched_plots'][:3]
                    ])

                    issue = ConsistencyIssue(
                        issue_id=f"knowledge_{idx}_{story_id}",
                        category=IssueCategory.KNOWLEDGE,
                        severity=IssueSeverity.MEDIUM,
                        title=f"角色能力与情节描述不一致",
                        description=f"角色「{record['character_name']}」的能力（{record['strengths']}）与情节描述不匹配：{plots_info}",
                        location="多处",
                        affected_elements=[record['character_id']],
                        evidence={
                            "strengths": record['strengths'],
                            "mismatched_plots": record['mismatched_plots'],
                        },
                        suggested_fix=f"修改角色能力设定，或调整情节描述使其与能力一致",
                        confidence=0.65,
                    )
                    issues.append(issue)

        except Exception as e:
            self.logger.error(f"知识连续性检查失败: {e}")

        return issues

    async def _check_world_rule_consistency(
        self,
        graph_manager,
        story_id: str,
    ) -> List[ConsistencyIssue]:
        """
        检查世界观规则一致性

        规则：情节不能违反世界观规则
        """
        issues = []

        # Cypher 查询：查找违反世界观规则的情节
        query = """
        // 查找所有世界观规则
        MATCH (r:WorldRule {story_id: $story_id})

        // 查找违反规则的情节（假设有 VIOLATES 关系）
        OPTIONAL MATCH (p:PlotNode {story_id: $story_id})-[v:VIOLATES]->(r)

        // 如果没有显式的违反关系，通过关键词匹配
        WITH r, collect(DISTINCT p) AS violating_plots

        // 另外检查规则关键词在情节中的出现
        MATCH (p:PlotNode {story_id: $story_id})
        WHERE any(rule IN collect(r.name)
                WHERE p.description CONTAINS rule
                OR p.title CONTAINS rule)

        RETURN r.rule_id AS rule_id,
               r.name AS rule_name,
               r.description AS rule_description,
               r.severity AS rule_severity,
               r.consequences AS consequences,
               collect(DISTINCT {
                 plot_id: p.plot_id,
                 title: p.title,
                 seq: p.sequence_number,
                 description: p.description
               }) AS potential_violations
        ORDER BY r.severity DESC
        """

        try:
            async with graph_manager._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                records = await result.data()

                for idx, record in enumerate(records):
                    violations = record['potential_violations']
                    if not violations:
                        continue

                    violation_info = ", ".join([
                        f"第{v['seq']}章《{v['title']}》"
                        for v in violations[:2]
                    ])

                    severity = IssueSeverity.HIGH if record['rule_severity'] == 'strict' else IssueSeverity.MEDIUM

                    issue = ConsistencyIssue(
                        issue_id=f"world_rule_{idx}_{story_id}",
                        category=IssueCategory.WORLD_RULE,
                        severity=severity,
                        title=f"情节可能违反世界观规则",
                        description=f"情节内容涉及规则「{record['rule_name']}」（{record['rule_description']}），可能违反后果：{record['consequences']}。涉及情节：{violation_info}",
                        location="多处",
                        affected_elements=[record['rule_id'], *[v['plot_id'] for v in violations]],
                        evidence={
                            "rule_name": record['rule_name'],
                            "rule_severity": record['rule_severity'],
                            "consequences": record['consequences'],
                            "violations": violations,
                        },
                        suggested_fix=f"审查情节内容，确保遵守世界观规则，或设置例外情况",
                        confidence=0.60,
                    )
                    issues.append(issue)

        except Exception as e:
            self.logger.error(f"世界观规则一致性检查失败: {e}")

        return issues

    async def _check_plot_coherence(
        self,
        graph_manager,
        story_id: str,
    ) -> List[ConsistencyIssue]:
        """
        检查情节连贯性

        规则：情节之间应该有合理的因果关系
        """
        issues = []

        # Cypher 查询：查找缺乏因果连接的情节
        query = """
        // 查找所有情节
        MATCH (p:PlotNode {story_id: $story_id})

        // 查找序列号相邻的情节
        MATCH (p)-[:NEXT]->(next_plot:PlotNode {story_id: $story_id})
        WHERE next_plot.sequence_number = p.sequence_number + 1

        // 检查是否有影响关系
        OPTIONAL MATCH (p)-[i:INFLUENCES]->(next_plot)

        WITH p, next_plot, i

        // 如果没有直接影响，检查间接路径
        WHERE i IS NULL

        // 检查通过中转情节的影响
        OPTIONAL MATCH path = (p)-[:INFLUENCES*1..3]->(next_plot)

        WITH p, next_plot, path IS NOT NULL AS has_indirect_influence

        // 既没有直接影响也没有间接影响
        WHERE has_indirect_influence = false

        RETURN p.plot_id AS plot1_id,
               p.title AS plot1_title,
               p.sequence_number AS seq1,
               p.importance AS importance1,
               next_plot.plot_id AS plot2_id,
               next_plot.title AS plot2_title,
               next_plot.sequence_number AS seq2,
               next_plot.importance AS importance2
        ORDER BY seq1
        LIMIT 20
        """

        try:
            async with graph_manager._get_session() as session:
                result = await session.run(query, {"story_id": story_id})
                records = await result.data()

                for idx, record in enumerate(records):
                    issue = ConsistencyIssue(
                        issue_id=f"plot_coherence_{idx}_{story_id}",
                        category=IssueCategory.PLOT_COHERENCE,
                        severity=IssueSeverity.LOW,
                        title=f"相邻情节缺乏因果连接",
                        description=f"第 {record['seq1']} 章《{record['plot1_title']}》与第 {record['seq2']} 章《{record['plot2_title']}》之间缺乏明确的因果关系",
                        location=f"第 {record['seq1']}-{record['seq2']} 章",
                        affected_elements=[
                            record['plot1_id'],
                            record['plot2_id'],
                        ],
                        evidence={
                            "sequence_gap": [record['seq1'], record['seq2']],
                            "importances": [record['importance1'], record['importance2']],
                        },
                        suggested_fix=f"添加过渡情节或建立两个情节间的因果关系",
                        confidence=0.50,
                    )
                    issues.append(issue)

        except Exception as e:
            self.logger.error(f"情节连贯性检查失败: {e}")

        return issues

    def _calculate_overall_score(
        self,
        issues: List[ConsistencyIssue],
    ) -> float:
        """
        计算总体一致性分数

        Args:
            issues: 所有问题列表

        Returns:
            float: 分数 (0-100)
        """
        total_score = 100.0

        for issue in issues:
            penalty = self.severity_penalties.get(issue.severity, 5.0)
            weighted_penalty = penalty * issue.confidence
            total_score -= weighted_penalty

        return max(0.0, min(100.0, total_score))

    def _generate_recommendations(
        self,
        issues: List[ConsistencyIssue],
    ) -> List[str]:
        """
        生成修复建议

        Args:
            issues: 所有问题列表

        Returns:
            List[str]: 建议列表
        """
        recommendations = []

        # 按严重程度和类别统计
        critical_count = len([i for i in issues if i.severity == IssueSeverity.CRITICAL])
        high_count = len([i for i in issues if i.severity == IssueSeverity.HIGH])

        # 总体建议
        if critical_count > 0:
            recommendations.append(f"发现 {critical_count} 个严重逻辑冲突，必须优先修复")
        if high_count > 0:
            recommendations.append(f"发现 {high_count} 个高优先级问题，强烈建议修复")

        # 按类别建议
        category_counts = {}
        for issue in issues:
            category = issue.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

        if category_counts.get("spatiotemporal", 0) > 0:
            recommendations.append("存在时空冲突，建议梳理角色时间线和位置信息")
        if category_counts.get("character_status", 0) > 0:
            recommendations.append("存在角色状态不一致问题，需要确认角色生死状态")
        if category_counts.get("motivation", 0) > 0:
            recommendations.append("部分重大情节缺乏动机支撑，建议补充角色动机")
        if category_counts.get("world_rule", 0) > 0:
            recommendations.append("存在违反世界观规则的内容，需要修改或设置例外")

        return recommendations

    async def _generate_readable_report(
        self,
        report: ConsistencyReport,
    ) -> str:
        """
        生成可读报告

        Args:
            report: 一致性报告

        Returns:
            str: 可读报告文本
        """
        lines = [
            "# 剧本逻辑一致性检测报告",
            "",
            f"**故事ID**: {report.story_id}",
            f"**检测时间**: {report.scan_time}",
            f"**总体分数**: {report.overall_score:.2f}",
            f"**检测结果**: {'✅ 通过' if report.passed else '❌ 未通过'}",
            "",
            f"## 问题概览",
            "",
            f"- 总问题数: {len(report.issues)}",
            f"  - 严重: {len([i for i in report.issues if i.severity == IssueSeverity.CRITICAL])}",
            f"  - 高优先级: {len([i for i in report.issues if i.severity == IssueSeverity.HIGH])}",
            f"  - 中等: {len([i for i in report.issues if i.severity == IssueSeverity.MEDIUM])}",
            f"  - 低: {len([i for i in report.issues if i.severity == IssueSeverity.LOW])}",
            "",
        ]

        # 统计信息
        if report.statistics:
            lines.append("## 检测统计")
            lines.append("")
            for key, value in report.statistics.items():
                lines.append(f"- {key}: {value}")
            lines.append("")

        # 按严重程度分组显示问题
        issues_by_severity = {
            IssueSeverity.CRITICAL: [i for i in report.issues if i.severity == IssueSeverity.CRITICAL],
            IssueSeverity.HIGH: [i for i in report.issues if i.severity == IssueSeverity.HIGH],
            IssueSeverity.MEDIUM: [i for i in report.issues if i.severity == IssueSeverity.MEDIUM],
            IssueSeverity.LOW: [i for i in report.issues if i.severity == IssueSeverity.LOW],
        }

        for severity, severity_issues in issues_by_severity.items():
            if not severity_issues:
                continue

            severity_name = {
                IssueSeverity.CRITICAL: "严重",
                IssueSeverity.HIGH: "高",
                IssueSeverity.MEDIUM: "中等",
                IssueSeverity.LOW: "低",
            }[severity]

            lines.append(f"## {severity_name}问题 ({len(severity_issues)})")
            lines.append("")

            for idx, issue in enumerate(severity_issues[:10], 1):  # 最多显示10个
                lines.append(f"### {idx}. {issue.title}")
                lines.append("")
                lines.append(f"**类别**: {issue.category.value}")
                lines.append(f"**位置**: {issue.location}")
                lines.append(f"**描述**: {issue.description}")
                if issue.suggested_fix:
                    lines.append(f"**修复建议**: {issue.suggested_fix}")
                lines.append("")

            if len(severity_issues) > 10:
                lines.append(f"... 还有 {len(severity_issues) - 10} 个{severity_name}问题")
                lines.append("")

        # 建议
        if report.recommendations:
            lines.append("## 修复建议")
            lines.append("")
            for idx, rec in enumerate(report.recommendations, 1):
                lines.append(f"{idx}. {rec}")
            lines.append("")

        # 结果判断
        if report.passed:
            lines.append("## ✅ 检测通过")
            lines.append("")
            lines.append("剧本逻辑一致性良好，可以继续创作！")
        else:
            lines.append("## ❌ 检测未通过")
            lines.append("")
            lines.append(f"总体分数 ({report.overall_score:.2f}) 低于通过标准 ({self.passing_score})")
            lines.append("")
            lines.append("### 建议:")
            lines.append("1. 优先修复严重和高优先级问题")
            lines.append("2. 修复后重新检测")
            lines.append("3. 可以使用「回滚」功能恢复到上一版本")

        return "\n".join(lines)

    def get_agent_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "logic_consistency",
            "capabilities": [
                "时空一致性检测",
                "角色状态一致性检测",
                "动机一致性检测",
                "关系一致性检测",
                "知识连续性检测",
                "世界观规则一致性检测",
                "情节连贯性检测",
            ],
            "audit_rules": [
                "spatiotemporal",
                "character_status",
                "motivation",
                "relationship",
                "knowledge",
                "world_rule",
                "plot_coherence",
            ],
            "scoring": {
                "passing_score": self.passing_score,
                "critical_threshold": self.critical_threshold,
            },
        })
        return base_info

"""
带逻辑一致性检测的工作流示例
Workflow with Logic Consistency Check

演示如何在剧本创作工作流中集成逻辑一致性检测
"""

import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional

from agents.base_juben_agent import BaseJubenAgent
from agents.logic_consistency_agent import LogicConsistencyAgent
from utils.graph_manager import (
    get_graph_manager,
    CharacterData,
    PlotNodeData,
    NodeType,
    CharacterStatus,
)

logger = logging.getLogger(__name__)


class CreativeWorkflowWithConsistencyCheck:
    """
    带逻辑一致性检测的创作工作流

    工作流程：
    1. Creator Agent 生成剧本
    2. 保存到图数据库
    3. LogicConsistency Agent 检测一致性
    4. 如果分数 < 80，回滚并提示修改
    5. 如果分数 >= 80，继续下一步
    """

    def __init__(self, model_provider: str = "deepseek"):
        """初始化工作流"""
        self.creator_agent = None  # 这里应该是实际的创作 Agent
        self.consistency_agent = LogicConsistencyAgent(model_provider)
        self.graph_manager = None

        self.passing_score = 80.0
        self.max_retries = 3

    async def initialize(self):
        """初始化图数据库连接"""
        self.graph_manager = await get_graph_manager()

    async def create_plot_with_validation(
        self,
        story_id: str,
        plot_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        创建情节并进行一致性验证

        Args:
            story_id: 故事ID
            plot_data: 情节数据
            context: 上下文信息

        Yields:
            Dict: 流式响应事件
        """
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                # 步骤 1: 创建情节
                yield {
                    "event_type": "tool_processing",
                    "data": {
                        "message": f"正在生成情节（尝试 {retry_count + 1}/{self.max_retries}）...",
                        "step": "creation",
                        "retry": retry_count,
                    }
                }

                # 这里应该调用 Creator Agent 生成情节
                # 为了演示，我们直接使用传入的数据
                plot = PlotNodeData(
                    plot_id=plot_data.get("plot_id", f"plot_{plot_data.get('sequence_number', 0)}"),
                    story_id=story_id,
                    title=plot_data.get("title", ""),
                    description=plot_data.get("description", ""),
                    sequence_number=plot_data.get("sequence_number", 0),
                    tension_score=plot_data.get("tension_score", 50.0),
                    chapter=plot_data.get("chapter"),
                    characters_involved=plot_data.get("characters_involved", []),
                    locations=plot_data.get("locations", []),
                    importance=plot_data.get("importance", 50.0),
                )

                # 保存到图数据库
                yield {
                    "event_type": "tool_processing",
                    "data": {
                        "message": "正在保存到图数据库...",
                        "step": "saving",
                    }
                }

                await self.graph_manager.merge_story_element(
                    element_type=NodeType.PLOT_NODE,
                    element_data=plot,
                )

                # 步骤 2: 逻辑一致性检测
                yield {
                    "event_type": "tool_processing",
                    "data": {
                        "message": "正在执行逻辑一致性检测...",
                        "step": "consistency_check",
                    }
                }

                check_result = await self._run_consistency_check(story_id)

                # 步骤 3: 检查结果
                if check_result["passed"]:
                    # 通过检测
                    yield {
                        "event_type": "tool_complete",
                        "data": {
                            "message": "情节创建成功并通过一致性检测",
                            "step": "complete",
                            "score": check_result["score"],
                            "retry_count": retry_count,
                            "plot_id": plot.plot_id,
                        }
                    }
                    return  # 成功完成

                else:
                    # 未通过检测
                    retry_count += 1

                    if retry_count < self.max_retries:
                        # 回滚并重试
                        yield {
                            "event_type": "rollback_suggested",
                            "data": {
                                "message": "一致性检测未通过，将回滚并重新生成",
                                "step": "rollback",
                                "score": check_result["score"],
                                "threshold": self.passing_score,
                                "critical_issues": check_result["critical_issues"],
                                "recommendations": check_result["recommendations"],
                                "retry_count": retry_count,
                                "max_retries": self.max_retries,
                            }
                        }

                        # 执行回滚
                        await self._rollback_plot(story_id, plot.plot_id)

                        # 生成修改建议
                        suggestions = await self._generate_improvement_suggestions(
                            plot_data,
                            check_result["issues"],
                        )

                        yield {
                            "event_type": "improvement_suggestion",
                            "data": {
                                "message": "修改建议",
                                "suggestions": suggestions,
                            }
                        }

                        # 继续下一次尝试（在实际场景中，这里会反馈给 Creator Agent）
                        continue

                    else:
                        # 达到最大重试次数
                        yield {
                            "event_type": "tool_complete",
                            "data": {
                                "message": f"已达到最大重试次数（{self.max_retries}），创作失败",
                                "step": "failed",
                                "score": check_result["score"],
                                "retry_count": retry_count,
                                "final_report": check_result["report"],
                            }
                        }
                        return  # 失败但完成

            except Exception as e:
                yield {
                    "event_type": "error",
                    "data": {
                        "error": str(e),
                        "message": "情节创建过程中发生错误",
                        "retry_count": retry_count,
                    }
                }
                return

    async def _run_consistency_check(
        self,
        story_id: str,
    ) -> Dict[str, Any]:
        """
        运行一致性检测

        Returns:
            Dict: 检测结果
        """
        request_data = {
            "story_id": story_id,
            "scan_depth": "recent",  # 只扫描最近的情节
        }

        result = None
        async for event in self.consistency_agent.process_request(request_data):
            if event.get("event_type") == "tool_complete":
                data = event["data"]["result"]
                result = {
                    "passed": data["passed"],
                    "score": data["score"],
                    "critical_issues": data["critical_issues"],
                    "issues": data["report"]["issues"],
                    "recommendations": data["report"]["recommendations"],
                    "report": data["report"],
                }
                break

        if result is None:
            # 默认通过（如果检测失败）
            result = {
                "passed": True,
                "score": 100.0,
                "critical_issues": 0,
                "issues": [],
                "recommendations": [],
            }

        return result

    async def _rollback_plot(
        self,
        story_id: str,
        plot_id: str,
    ):
        """
        回滚情节（从图数据库中删除）

        Args:
            story_id: 故事ID
            plot_id: 要删除的情节ID
        """
        query = """
        MATCH (p:PlotNode {plot_id: $plot_id, story_id: $story_id})
        DETACH DELETE p
        """

        async with self.graph_manager._get_session() as session:
            await session.run(query, {"plot_id": plot_id, "story_id": story_id})

    async def _generate_improvement_suggestions(
        self,
        original_plot_data: Dict[str, Any],
        issues: list,
    ) -> List[str]:
        """
        生成改进建议

        Args:
            original_plot_data: 原始情节数据
            issues: 检测到的问题列表

        Returns:
            List[str]: 建议列表
        """
        suggestions = []

        # 根据问题生成建议
        for issue in issues:
            if issue["category"] == "spatiotemporal":
                suggestions.append("调整情节地点，确保角色不会同时出现在两个地点")
            elif issue["category"] == "character_status":
                suggestions.append("检查角色状态，确保已死亡角色没有后续行动")
            elif issue["category"] == "motivation":
                suggestions.append("为相关角色添加明确的动机")
            elif issue["category"] == "world_rule":
                suggestions.append("修改情节内容以符合世界观规则，或设置例外情况")

        # 去重
        suggestions = list(set(suggestions))

        return suggestions if suggestions else ["请根据具体问题调整情节内容"]


# ============ 使用示例 ============


async def example_workflow():
    """
    工作流使用示例

    演示如何创建带逻辑一致性检测的剧本创作工作流
    """
    workflow = CreativeWorkflowWithConsistencyCheck()
    await workflow.initialize()

    # 模拟情节生成
    plot_data = {
        "plot_id": "plot_010",
        "title": "血战暗夜谷",
        "description": "林萧与黑风在暗夜谷展开生死对决",
        "sequence_number": 10,
        "tension_score": 95.0,
        "chapter": 10,
        "characters_involved": ["char_001", "char_003"],
        "locations": ["暗夜谷"],
        "importance": 95.0,
    }

    # 执行工作流
    async for event in workflow.create_plot_with_validation(
        story_id="story_001",
        plot_data=plot_data,
    ):
        event_type = event.get("event_type")
        data = event.get("data", {})

        if event_type == "tool_processing":
            logger.info(f"[进度] {data.get('message', '')}")

        elif event_type == "rollback_suggested":
            logger.info(f"[回滚] 检测未通过（分数: {data['score']:.2f}）")
            logger.info(f"[建议] {data['recommendations']}")

        elif event_type == "improvement_suggestion":
            logger.info(f"[建议] {data['suggestions']}")

        elif event_type == "tool_complete":
            if data.get("step") == "complete":
                logger.info(f"[成功] {data['message']}")
            elif data.get("step") == "failed":
                logger.info(f"[失败] {data['message']}")

        elif event_type == "error":
            logger.info(f"[错误] {data['message']}")


async def example_batch_creation_with_validation():
    """
    批量创建情节并进行验证

    演示如何创建多个情节，每个都经过一致性检测
    """
    workflow = CreativeWorkflowWithConsistencyCheck()
    await workflow.initialize()

    plots = [
        {
            "plot_id": "plot_001",
            "title": "初入江湖",
            "description": "林萧离开家乡，踏上复仇之路",
            "sequence_number": 1,
            "tension_score": 30.0,
            "chapter": 1,
            "characters_involved": ["char_001"],
            "locations": ["家乡"],
            "importance": 60.0,
        },
        {
            "plot_id": "plot_002",
            "title": "拜师学艺",
            "description": "林萧偶遇白云飞，被收为弟子",
            "sequence_number": 2,
            "tension_score": 45.0,
            "chapter": 2,
            "characters_involved": ["char_001", "char_002"],
            "locations": ["白云山"],
            "importance": 75.0,
        },
        # ... 更多情节
    ]

    for plot_data in plots:
        logger.info(f"\n正在创建: {plot_data['title']}")

        async for event in workflow.create_plot_with_validation(
            story_id="story_001",
            plot_data=plot_data,
        ):
            if event.get("event_type") == "tool_complete":
                if event["data"].get("step") == "complete":
                    logger.info(f"✓ 创建成功（分数: {event['data']['score']:.2f}）")
                    break
                elif event["data"].get("step") == "failed":
                    logger.info(f"✗ 创建失败（达到最大重试次数）")
                    break


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("逻辑一致性检测工作流示例")
    logger.info("=" * 60)

    # 运行示例
    asyncio.run(example_workflow())

    # 或运行批量示例
    # asyncio.run(example_batch_creation_with_validation())

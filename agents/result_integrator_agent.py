from typing import AsyncGenerator, Dict, Any, Optional, List

"""
结果整合智能体
基于agent as tool机制，负责整合多个情节点分析结果

业务处理逻辑：
1. 输入处理：接收多个情节点分析结果，支持多种数据格式
2. 结果整合：整合多个情节点分析结果，形成综合分析报告
3. 去重处理：移除重复或相似的情节点内容
4. 内容分类：按照戏剧功能对情节点进行分类整理
5. 排序优化：按照在故事中的出现顺序排列情节点
6. 结构梳理：提供整体的戏剧结构分析
7. 内容优化：优化整合后的内容结构和可读性
8. 输出格式化：生成结构化的综合分析报告
9. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
from datetime import datetime

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from agents.base_juben_agent import BaseJubenAgent


class ResultIntegratorAgent(BaseJubenAgent):
    """
    结果整合智能体

    功能：
    1. 整合多个情节点分析结果
    2. 去重和合并相似内容
    3. 生成最终的综合分析报告
    """

    def __init__(self, model_provider: str = "deepseek"):
        """初始化结果整合智能体"""
        super().__init__("result_integrator", model_provider)

        # 加载系统提示词
        self.logger.info("结果整合智能体初始化完成")

    # 系统提示词由基类自动加载，无需重写

    async def integrate_results(self, results: List[str]) -> str:
        """
        整合多个分析结果

        Args:
            results: 分析结果列表

        Returns:
            str: 整合后的结果
        """
        try:
            if not results:
                return "没有可整合的结果"

            # 构建用户提示词
            results_text = "\n\n".join([f"分析结果 {i+1}:\n{result}" for i, result in enumerate(results)])

            user_prompt = f"""
请整合以下多个情节点分析结果：

{results_text}

请按照整合原则进行整合，生成最终的综合分析报告。
"""

            # 使用基类的 _call_llm 方法（需要传入 messages 列表）
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的故事分析结果整合专家。请将多个分析结果整合成一个完整、连贯、无重复的综合报告。",
                },
                {"role": "user", "content": user_prompt},
            ]

            response = await self._call_llm(
                messages=messages,
                user_id="system",
                session_id="result_integration",
            )

            return response

        except Exception as e:
            self.logger.error(f"结果整合失败: {e}")
            return f"整合失败: {str(e)}"
    
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理请求 - 支持Agent as Tool机制
        
        Args:
            request_data: 请求数据
            context: 上下文信息
                - user_id: 用户ID
                - session_id: 会话ID  
                - parent_agent: 父智能体名称（Agent as Tool模式）
                - tool_call: 是否为工具调用
                
        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            input_text = request_data.get("input", "")
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            parent_agent = context.get("parent_agent", "") if context else ""
            tool_call = context.get("tool_call", False) if context else False
            
            if tool_call:
                self.logger.info(f"🔧 Agent as Tool模式，父智能体: {parent_agent}")
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 提取请求参数
            results = request_data.get("results", [])
            user_id = request_data.get("user_id", "unknown")
            session_id = request_data.get("session_id", "unknown")
            
            self.logger.info(f"处理结果整合请求: results_count={len(results)}")
            
            # 执行结果整合
            integrated_result = await self.integrate_results(results)
            
            # 发送整合结果
            yield {
                "type": "result_integration_result",
                "data": {
                    "integrated_result": integrated_result,
                    "input_results_count": len(results)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # 发送Token统计
            await self._send_token_summary()
            
        except Exception as e:
            self.logger.error(f"结果整合处理失败: {e}")
            yield {
                "type": "error",
                "data": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
        finally:
            # 清理Token累加器
            await self._cleanup_token_accumulator()
    
    async def _init_token_accumulator(self, user_id: str, session_id: str):
        """初始化Token累加器"""
        try:
            # create_token_accumulator 为同步函数，不接受 agent_name 参数
            self.current_token_accumulator_key = create_token_accumulator(
                user_id=user_id,
                session_id=session_id,
            )
            self.logger.info(f"Token累加器初始化成功: {self.current_token_accumulator_key}")
        except Exception as e:
            self.logger.error(f"Token累加器初始化失败: {e}")
    
    async def _send_token_summary(self):
        """发送Token统计摘要（复用基类的 get_token_billing_summary）"""
        try:
            summary = await self.get_token_billing_summary()
            if summary:
                self.logger.info(f"Token使用统计: {summary}")
        except Exception as e:
            self.logger.error(f"获取Token统计失败: {e}")
    
    async def _cleanup_token_accumulator(self):
        """清理Token累加器"""
        try:
            if self.current_token_accumulator_key:
                # 这里可以添加清理逻辑
                self.current_token_accumulator_key = None
        except Exception as e:
            self.logger.error(f"清理Token累加器失败: {e}")

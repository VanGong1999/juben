"""
大情节点智能体
基于coze工作流中的大情节点分析功能，专门负责大情节点生成

业务处理逻辑：
1. 输入处理：接收故事文本或故事梗概
2. 宏观分析：对故事进行整体结构分析
3. 大情节点提取：提取故事的主要情节点
4. 情节点描述：为每个大情节点生成简洁的描述
5. 时间线构建：构建情节发展的时间线和逻辑关系
6. 结构优化：优化情节点的时间顺序和逻辑关系
7. 输出格式化：返回结构化的大情节点分析数据
8. 质量控制：确保大情节点的准确性和完整性

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_juben_agent import BaseJubenAgent


class MajorPlotPointsAgent(BaseJubenAgent):
    """
    大情节点智能体

    核心功能：
    1. 分析故事整体结构
    2. 生成主要情节点描述
    3. 提供情节发展的时间线
    4. 支持批处理模式
    5. 流式输出支持

    基于coze工作流中的大情节点分析功能设计
    """

    def __init__(self, model_provider: str = "deepseek"):
        """初始化大情节点智能体"""
        super().__init__("major_plot_points", model_provider)

        # 系统提示词配置
        self.system_prompt = """你是一位专业的编剧和故事分析师，擅长分析故事结构并提取主要情节点。

## 你的任务
请根据提供的故事文本或故事梗概，完成以下任务：

1. **整体结构分析**：分析故事的整体结构，包括起承转合
2. **大情节点提取**：提取故事的主要情节点（通常为8-15个）
3. **情节点描述**：为每个大情节点生成简洁的描述（50-100字）
4. **时间线构建**：构建情节发展的时间线和逻辑关系

## 输出格式
请按照以下格式输出：

# 大情节点分析

## 故事结构概述
[对故事整体结构的简要分析，100-200字]

## 主要情节点

### 情节点1：[标题]
- **时间/阶段**：[故事中的时间或阶段]
- **情节点描述**：[50-100字的描述]
- **关键要素**：[涉及的人物、地点、事件等]

### 情节点2：[标题]
...

## 情节发展时间线
[按时间顺序梳理的情节发展脉络]

## 注意事项
- 大情节点数量控制在8-15个之间
- 每个情节点描述简洁明了，50-100字
- 确保覆盖故事的主要情节发展
- 突出故事的关键转折点
"""

        # 批处理配置
        self.batch_size = 10
        self.max_retries = 3

        self.logger.info("大情节点智能体初始化完成")


    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理大情节点分析请求

        Args:
            request_data: 请求数据，包含input等
            context: 上下文信息

        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            input_text = request_data.get("input", "")
            if not input_text:
                yield {
                    "event_type": "error",
                    "data": "缺少输入文本",
                    "timestamp": datetime.now().isoformat()
                }
                return

            # 发送开始处理事件
            yield {
                "event_type": "processing_start",
                "data": "开始分析大情节点",
                "timestamp": datetime.now().isoformat(),
                "input_length": len(input_text)
            }

            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"

            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)

            # 构建消息
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"请分析以下故事的大情节点：\n\n{input_text}"}
            ]

            # 流式调用LLM
            async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                yield await self._emit_event("llm_chunk", chunk)

            # 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")

            # 发送完成事件
            yield {
                "event_type": "processing_complete",
                "data": "大情节点分析完成",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"大情节点分析失败: {e}")
            yield {
                "event_type": "error",
                "data": f"大情节点分析失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def _analyze_major_plot_points(self, input_text: str) -> AsyncGenerator[Dict[str, Any], None]:
        """分析大情节点"""
        try:
            # 构建用户提示词
            user_prompt = f"""
请分析以下故事的大情节点：

{input_text}

请按照系统提示词的要求，提取故事的主要情节点（8-15个），并为每个情节点生成简洁的描述。
"""

            # 使用基类的_call_llm方法进行流式调用
            async for chunk in self._stream_llm(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt
            ):
                yield {
                    "type": "content",
                    "content": chunk,
                    "timestamp": datetime.now().isoformat()
                }

            # 发送完成事件
            yield {
                "type": "processing_complete",
                "message": "大情节点分析完成",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            yield {
                "type": "error",
                "message": f"LLM调用失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def process_batch(
        self,
        inputs: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        批处理模式处理多个输入

        Args:
            inputs: 输入文本列表
            context: 上下文信息

        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            yield {
                "type": "batch_start",
                "message": f"开始批处理，共{len(inputs)}个输入",
                "timestamp": datetime.now().isoformat(),
                "batch_size": len(inputs)
            }

            # 分批处理
            for i in range(0, len(inputs), self.batch_size):
                batch = inputs[i:i + self.batch_size]

                yield {
                    "type": "batch_processing",
                    "message": f"处理批次 {i//self.batch_size + 1}",
                    "timestamp": datetime.now().isoformat(),
                    "batch_index": i//self.batch_size + 1,
                    "batch_size": len(batch)
                }

                # 并行处理当前批次
                tasks = [self._process_single_input(text, i + j) for j, text in enumerate(batch)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                for j, result in enumerate(results):
                    if isinstance(result, Exception):
                        yield {
                            "type": "batch_error",
                            "message": f"批次{i//self.batch_size + 1}第{j+1}项处理失败: {str(result)}",
                            "timestamp": datetime.now().isoformat(),
                            "batch_index": i//self.batch_size + 1,
                            "item_index": j + 1
                        }
                    else:
                        yield {
                            "type": "batch_result",
                            "result": result,
                            "timestamp": datetime.now().isoformat(),
                            "batch_index": i//self.batch_size + 1,
                            "item_index": j + 1
                        }

            yield {
                "type": "batch_complete",
                "message": "批处理完成",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"批处理失败: {e}")
            yield {
                "type": "batch_error",
                "message": f"批处理失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def _process_single_input(self, input_text: str, index: int) -> Dict[str, Any]:
        """处理单个输入"""
        try:
            # 构建用户提示词
            user_prompt = f"""
请分析以下故事的大情节点：

{input_text}

请按照系统提示词的要求，提取故事的主要情节点（8-15个），并为每个情节点生成简洁的描述。
"""

            # 使用基类的_call_llm方法
            response = await self._call_llm(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt
            )

            return {
                "index": index,
                "input": input_text,
                "major_plot_points": response,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"处理单个输入失败: {e}")
            return {
                "index": index,
                "input": input_text,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "major_plot_points",
            "description": "大情节点智能体 - 专门负责大情节点分析",
            "capabilities": [
                "故事整体结构分析",
                "大情节点提取（8-15个）",
                "情节点描述生成（50-100字）",
                "情节发展时间线构建",
                "批处理支持"
            ],
            "configuration": {
                "batch_size": self.batch_size,
                "max_retries": self.max_retries,
                "plot_points_count": "8-15个",
                "description_length": "50-100字"
            }
        })
        return base_info

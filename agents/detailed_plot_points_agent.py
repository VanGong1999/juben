"""
详细情节点智能体
基于coze工作流中的详细情节点分析功能，专门负责详细情节点生成

业务处理逻辑：
1. 输入处理：接收故事文本或大情节点分析结果
2. 详细分析：基于大情节点进行更深入的情节分析
3. 情节点细化：将大情节点分解为更细致的子情节点
4. 情节描述：为每个详细情节点生成丰富的描述内容
5. 发展脉络：提供情节发展的详细说明和逻辑关系
6. 内容扩展：补充大情节点中未涵盖的细节和过渡情节
7. 结构优化：优化情节点的时间顺序和逻辑关系
8. 输出格式化：返回结构化的详细情节点分析数据
9. 质量控制：确保详细情节点的准确性和完整性

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

from .base_juben_agent import BaseJubenAgent


class DetailedPlotPointsAgent(BaseJubenAgent):
    """
    详细情节点智能体
    
    核心功能：
    1. 基于大情节点进行详细分析
    2. 生成更细致的情节点描述
    3. 提供情节发展的详细说明
    4. 支持批处理模式
    5. 流式输出支持
    
    基于coze工作流中的详细情节点分析功能设计
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化详细情节点智能体"""
        super().__init__("detailed_plot_points", model_provider)
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 批处理配置
        self.batch_size = 10
        self.max_retries = 3
        
        self.logger.info("详细情节点智能体初始化完成")
    
    
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理详细情节点分析请求（支持 /juben/chat 和独立接口）

        Args:
            request_data: 请求数据，包含 input 等
            context: 上下文信息（user_id / session_id 等）

        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            input_text = request_data.get("input", "") or request_data.get("text", "")
            user_id = (context or {}).get("user_id", "unknown")
            session_id = (context or {}).get("session_id", "unknown")

            if not input_text or not isinstance(input_text, str):
                yield {
                    "type": "error",
                    "message": "缺少输入文本",
                    "timestamp": datetime.now().isoformat()
                }
                return

            # 初始化 Token 累加器（与其他 Agent 保持一致）
            await self.initialize_token_accumulator(user_id, session_id)

            # 发送开始处理事件
            yield {
                "type": "processing_start",
                "message": "开始分析详细情节点",
                "timestamp": datetime.now().isoformat(),
                "input_length": len(input_text)
            }

            # 调用LLM分析详细情节点（统一通过 _stream_llm，避免不同provider返回结构差异）
            async for event in self._analyze_detailed_plot_points(
                input_text=input_text,
                user_id=user_id,
                session_id=session_id,
            ):
                yield event

        except Exception as e:
            self.logger.error(f"详细情节点分析失败: {e}")
            yield {
                "type": "error",
                "message": f"详细情节点分析失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def _analyze_detailed_plot_points(
        self,
        input_text: str,
        user_id: str = "unknown",
        session_id: str = "unknown",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        分析详细情节点

        使用 BaseJubenAgent._stream_llm 进行流式调用，输出统一的文本分片，
        避免直接依赖底层 llm_client 的返回结构。
        """
        try:
            # 构建用户提示词
            user_prompt = f"""
请基于以下大情节点内容，进行详细的情节点分析：

{input_text}

请按照系统提示词的要求，对每个情节点进行深入分析，生成详细的情节描述和情节发展说明。
"""

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # 使用统一的流式封装，chunk 一定是字符串
            async for chunk in self._stream_llm(
                messages,
                user_id=user_id,
                session_id=session_id,
                temperature=0.7,
                max_tokens=3000,
            ):
                if isinstance(chunk, str) and chunk.strip():
                    yield {
                        "type": "content",
                        "content": chunk,
                        "timestamp": datetime.now().isoformat(),
                    }

            # 发送完成事件
            yield {
                "type": "processing_complete",
                "message": "详细情节点分析完成",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            yield {
                "type": "error",
                "message": f"LLM调用失败: {str(e)}",
                "timestamp": datetime.now().isoformat(),
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
请基于以下大情节点内容，进行详细的情节点分析：

{input_text}

请按照系统提示词的要求，对每个情节点进行深入分析，生成详细的情节描述和情节发展说明。
"""
            
            # 调用LLM（模型名称由全局配置自行决定，不再直接访问 config.llm_model）
            response = await self.llm_client.achat(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            return {
                "index": index,
                "input": input_text,
                "detailed_analysis": response.content,
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
        return {
            "agent_name": self.agent_name,
            "description": "详细情节点智能体 - 专门负责详细情节点分析",
            "capabilities": [
                "情节点深入分析",
                "情节发展说明",
                "逻辑关系分析",
                "情节优化建议",
                "批处理支持"
            ],
            "configuration": {
                "batch_size": self.batch_size,
                "max_retries": self.max_retries,
                "max_analysis_length": "200-300字"
            }
        }

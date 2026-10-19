from typing import AsyncGenerator, Dict, Any, Optional, List
import asyncio

"""
情节点戏剧功能分析工作流智能体
基于agent as tool机制，实现智能体间的模块化外包和上下文隔离

业务处理逻辑：
1. 输入处理：接收故事文本，支持长文本截断和分割处理
2. 工作流编排：协调情节点戏剧功能分析的完整流程
3. 智能体调用：使用Agent as Tool机制调用专业分析智能体
   - TextTruncatorAgent：文本截断处理
   - TextSplitterAgent：文本分割处理
   - DramaAnalysisAgent：情节点戏剧功能分析
   - ResultIntegratorAgent：结果整合
4. 上下文隔离：确保每次调用的独立性和准确性
5. 并行处理：支持多个智能体的并行调用，提高效率
6. 结果整合：汇总各个智能体的分析结果
7. 输出格式化：生成完整的情节点戏剧功能分析报告
8. 质量控制：确保分析结果的准确性和完整性

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
from datetime import datetime

# 🔧 修复：导入缺失的Token累加器函数
try:
    from ..utils.token_accumulator import create_token_accumulator, get_billing_summary
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.token_accumulator import create_token_accumulator, get_billing_summary

try:
    from .base_juben_agent import BaseJubenAgent
    from .text_truncator_agent import TextTruncatorAgent
    from .text_splitter_agent import TextSplitterAgent
    from .drama_analysis_agent import DramaAnalysisAgent
    from .result_integrator_agent import ResultIntegratorAgent
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_juben_agent import BaseJubenAgent
from agents.text_truncator_agent import TextTruncatorAgent
from agents.text_splitter_agent import TextSplitterAgent
from agents.drama_analysis_agent import DramaAnalysisAgent
from agents.result_integrator_agent import ResultIntegratorAgent


class DramaWorkflowAgent(BaseJubenAgent):
    """
    情节点戏剧功能分析工作流智能体
    
    功能：
    1. 编排整个情节点分析工作流
    2. 管理智能体间的调用和上下文隔离
    3. 实现agent as tool机制
    4. 支持并行处理和结果整合
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化情节点工作流智能体"""
        super().__init__("drama_workflow", model_provider)
        
        # 加载系统提示词
        # 初始化子智能体（作为工具使用）
        self.text_truncator = TextTruncatorAgent(model_provider)
        self.text_splitter = TextSplitterAgent(model_provider)
        self.drama_analysis = DramaAnalysisAgent(model_provider)
        self.result_integrator = ResultIntegratorAgent(model_provider)
        
        # 工作流配置
        self.max_chunk_size = 10000  # 文本块最大大小
        self.max_parallel_analysis = 10  # 最大并行分析数量
        
        self.logger.info("情节点戏剧功能分析工作流智能体初始化完成")
    
    # 系统提示词由基类自动加载，无需重写
    
    async def _call_text_truncator(self, text: str, max_length: int, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        调用文本截断智能体（作为工具）（增强版：带超时控制）

        Args:
            text: 输入文本
            max_length: 最大长度
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Dict: 截断结果
        """
        try:
            # ========== 参数验证 ==========
            if not text or not isinstance(text, str):
                return {"code": 400, "data": "", "msg": "输入文本为空或类型不正确"}

            if max_length <= 0:
                self.logger.warning(f"max_length参数不合法({max_length})，使用默认值50000")
                max_length = 50000

            request_data = {
                "text": text,
                "max_length": max_length,
                "user_id": user_id,
                "session_id": session_id
            }

            # 直接调用截断逻辑，避免依赖事件格式差异
            result = await self.text_truncator.truncate_text(
                text,
                max_length=max_length,
            )

            if result.get("success"):
                return {
                    "code": 200,
                    "data": result.get("data", text[:max_length]),
                    "msg": result.get("msg", "截断成功"),
                }

            # 降级：即便失败也返回部分文本，避免整个工作流失败
            return {
                "code": 500,
                "data": result.get("data", text[:max_length]),
                "msg": result.get("msg", "截断失败"),
            }

        except ValueError as e:
            self.logger.error(f"调用文本截断智能体参数错误: {e}")
            return {"code": 400, "data": "", "msg": f"参数错误: {str(e)}"}
        except Exception as e:
            self.logger.error(f"调用文本截断智能体失败: {e}")
            return {"code": 500, "data": "", "msg": f"截断失败: {str(e)}"}
    
    async def _call_text_splitter(self, text: str, chunk_size: int, user_id: str, session_id: str) -> List[str]:
        """
        调用文本分割智能体（作为工具）（增强版：带参数验证）

        Args:
            text: 输入文本
            chunk_size: 分割大小
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            List[str]: 分割后的文本块
        """
        try:
            # ========== 参数验证 ==========
            if not text or not isinstance(text, str):
                self.logger.error("输入文本为空或类型不正确")
                return []

            if chunk_size <= 0:
                self.logger.warning(f"chunk_size参数不合法({chunk_size})，使用默认值10000")
                chunk_size = 10000

            request_data = {
                "text": text,
                "chunk_size": chunk_size,
                "user_id": user_id,
                "session_id": session_id
            }

            # 直接调用分割逻辑，避免依赖事件格式差异
            # 这里使用默认模式的 split_text
            chunks = await self.text_splitter.split_text(
                text,
                chunk_size=chunk_size,
                overlap=200,
                preserve_sentences=True,
            )

            # 验证返回结果
            if not isinstance(chunks, list):
                self.logger.error(f"分割返回非列表类型: {type(chunks)}")
                return [text]

            # 过滤空chunk
            chunks = [c for c in chunks if c and isinstance(c, str) and len(c.strip()) > 0]

            if not chunks:
                self.logger.warning("分割后没有有效chunk，使用原文作为唯一chunk")
                return [text]

            return chunks

        except ValueError as e:
            self.logger.error(f"调用文本分割智能体参数错误: {e}")
            # 降级处理：使用安全的简单分割
            safe_chunk_size = max(1, min(chunk_size if chunk_size > 0 else 10000, len(text)))
            return [text[i:min(i + safe_chunk_size, len(text))] for i in range(0, len(text), safe_chunk_size)]
        except Exception as e:
            self.logger.error(f"调用文本分割智能体失败: {e}")
            # 降级处理：返回原文作为唯一chunk
            return [text]
    
    async def _call_drama_analysis(self, text: str, user_id: str, session_id: str) -> str:
        """
        调用情节点分析智能体（作为工具）（增强版：带超时控制）

        Args:
            text: 输入文本
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            str: 分析结果
        """
        import asyncio

        try:
            # ========== 参数验证 ==========
            if not text or not isinstance(text, str):
                return "错误：输入文本为空或类型不正确"

            request_data = {
                "input": text,
                "user_id": user_id,
                "session_id": session_id
            }

            # 收集流式响应（带超时）
            result = ""

            async def collect_result():
                nonlocal result
                async for event in self.drama_analysis.process_request(request_data):
                    et = event.get("type") or event.get("event_type")
                    # DramaAnalysisAgent 使用 type="drama_analysis" 输出完整分析文本
                    if et == "drama_analysis":
                        content = event.get("content") or event.get("data") or ""
                        if isinstance(content, str):
                            result = content
                        break

            # 使用超时控制
            try:
                await asyncio.wait_for(collect_result(), timeout=120)
            except asyncio.TimeoutError:
                self.logger.error("情节点分析智能体调用超时(120秒)")
                return "分析超时(120秒)"

            return result

        except ValueError as e:
            self.logger.error(f"调用情节点分析智能体参数错误: {e}")
            return f"参数错误: {str(e)}"
        except Exception as e:
            self.logger.error(f"调用情节点分析智能体失败: {e}")
            return f"分析失败: {str(e)}"

    async def _call_result_integrator(self, results: List[str], user_id: str, session_id: str) -> str:
        """
        调用结果整合智能体（作为工具）（增强版：带超时控制）

        Args:
            results: 分析结果列表
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            str: 整合结果
        """
        import asyncio

        try:
            # ========== 参数验证 ==========
            if not results or not isinstance(results, list):
                return "错误：分析结果为空或类型不正确"

            request_data = {
                "results": results,
                "user_id": user_id,
                "session_id": session_id
            }

            # 收集流式响应（带超时）
            result = ""

            async def collect_result():
                nonlocal result
                async for event in self.result_integrator.process_request(request_data):
                    if event["type"] == "result_integration_result":
                        result = event["data"]["integrated_result"]
                        break

            # 使用超时控制
            try:
                await asyncio.wait_for(collect_result(), timeout=60)
            except asyncio.TimeoutError:
                self.logger.error("结果整合智能体调用超时(60秒)")
                return "\n\n".join(results)  # 降级：简单拼接

            return result

        except ValueError as e:
            self.logger.error(f"调用结果整合智能体参数错误: {e}")
            return f"参数错误: {str(e)}"
        except Exception as e:
            self.logger.error(f"调用结果整合智能体失败: {e}")
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
        
        # 提取请求参数（兼容 /juben/chat 的 input/query 字段）
        raw_text = (
            request_data.get("text")
            or request_data.get("input")
            or request_data.get("query")
            or ""
        )
        text = raw_text if isinstance(raw_text, str) else str(raw_text)

        # 优先从 context 取 user/session，其次退回 request_data
        user_id = (context or {}).get("user_id") or request_data.get("user_id", "unknown")
        session_id = (context or {}).get("session_id") or request_data.get("session_id", "unknown")
        
        self.logger.info(f"处理情节点戏剧功能分析工作流请求: text_length={len(text)}")
        
        try:
            # 如果文本为空，直接返回友好的错误事件
            if not text.strip():
                self.logger.error("情节点戏剧功能分析工作流失败: 输入文本为空")
                yield {
                    "type": "workflow_error",
                    "data": {"error": "输入文本为空，无法进行分析"},
                    "timestamp": datetime.now().isoformat()
                }
                return

            # 初始化Token累加器
            await self._init_token_accumulator(user_id, session_id)
            
            # 发送工作流开始事件
            yield {
                "type": "workflow_start",
                "data": {"message": "开始情节点戏剧功能分析工作流"},
                "timestamp": datetime.now().isoformat()
            }
            
            # 步骤1: 文本截断处理
            yield {
                "type": "workflow_step",
                "data": {"step": 1, "message": "步骤1: 文本截断处理"},
                "timestamp": datetime.now().isoformat()
            }
            
            truncated_result = await self._call_text_truncator(text, 50000, user_id, session_id)
            if truncated_result["code"] != 200:
                raise Exception(f"文本截断失败: {truncated_result['msg']}")
            
            truncated_text = truncated_result["data"]
            
            # 步骤2: 文本分割处理
            yield {
                "type": "workflow_step",
                "data": {"step": 2, "message": "步骤2: 文本分割处理"},
                "timestamp": datetime.now().isoformat()
            }
            
            text_chunks = await self._call_text_splitter(truncated_text, self.max_chunk_size, user_id, session_id)
            if not text_chunks:
                raise Exception("文本分割失败")
            
            yield {
                "type": "workflow_progress",
                "data": {"message": f"文本已分割为{len(text_chunks)}个片段"},
                "timestamp": datetime.now().isoformat()
            }
            
            # 步骤3: 并行情节点分析
            yield {
                "type": "workflow_step",
                "data": {"step": 3, "message": "步骤3: 并行情节点分析"},
                "timestamp": datetime.now().isoformat()
            }
            
            # 创建分析任务
            analysis_tasks = []
            for i, chunk in enumerate(text_chunks[:self.max_parallel_analysis]):
                task = self._call_drama_analysis(chunk, user_id, session_id)
                analysis_tasks.append(task)
            
            # 并行执行分析
            analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # 过滤成功的结果
            valid_results = []
            for i, result in enumerate(analysis_results):
                if isinstance(result, str) and result and not result.startswith("分析失败"):
                    valid_results.append(result)
                else:
                    self.logger.warning(f"第{i+1}个文本片段分析失败")
            
            yield {
                "type": "workflow_progress",
                "data": {"message": f"完成{len(valid_results)}个文本片段的分析"},
                "timestamp": datetime.now().isoformat()
            }
            
            # 步骤4: 结果整合
            if valid_results:
                yield {
                    "type": "workflow_step",
                    "data": {"step": 4, "message": "步骤4: 整合分析结果"},
                    "timestamp": datetime.now().isoformat()
                }
                
                integrated_result = await self._call_result_integrator(valid_results, user_id, session_id)

                # 先以 llm_chunk 形式输出可直接展示的文本结果，供前端聊天窗口使用
                if isinstance(integrated_result, str) and integrated_result.strip():
                    yield {
                        "type": "llm_chunk",
                        "content": integrated_result,
                        "timestamp": datetime.now().isoformat()
                    }

                # 再发送结构化的工作流结果，便于后续可视化或导出
                yield {
                    "type": "workflow_result",
                    "data": {
                        "final_result": integrated_result,
                        "processed_chunks": len(valid_results),
                        "total_chunks": len(text_chunks)
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                yield {
                    "type": "workflow_complete",
                    "data": {"message": "情节点戏剧功能分析工作流完成"},
                    "timestamp": datetime.now().isoformat()
                }
            else:
                yield {
                    "type": "workflow_error",
                    "data": {"message": "没有有效的分析结果"},
                    "timestamp": datetime.now().isoformat()
                }
            
            # 发送Token统计
            await self._send_token_summary()
            
        except Exception as e:
            self.logger.error(f"情节点戏剧功能分析工作流失败: {e}")
            yield {
                "type": "workflow_error",
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
                session_id=session_id
            )
            self.logger.info(f"Token累加器初始化成功: {self.current_token_accumulator_key}")
        except Exception as e:
            self.logger.error(f"Token累加器初始化失败: {e}")
    
    async def _send_token_summary(self):
        """发送Token统计摘要"""
        try:
            if self.current_token_accumulator_key:
                # get_billing_summary 为同步函数，无需 await
                summary = get_billing_summary(self.current_token_accumulator_key)
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

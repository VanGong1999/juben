"""
大情节点与详细情节点一键生成工作流智能体
基于agent as tool机制，实现智能体间的模块化外包和上下文隔离

业务处理逻辑：
1. 输入处理：接收故事文本，支持长文本截断和分割处理
2. 工作流编排：协调大情节点和详细情节点的生成流程
3. 智能体调用：使用Agent as Tool机制调用专业分析智能体
   - PlotPointsAnalyzerAgent：生成大情节点分析
   - DetailedPlotPointsAgent：生成详细情节点分析
4. 上下文隔离：确保每次调用的独立性和准确性
5. 并行处理：支持多个智能体的并行调用，提高效率
6. 结果整合：汇总大情节点和详细情节点的分析结果
7. 批处理协调：支持大批量文本的并行处理
8. 输出格式化：生成完整的双情节点分析报告
9. 质量控制：确保分析结果的准确性和完整性

代码作者：宫灵瑞
创建时间：2024年10月19日
"""
import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
import uuid

from .base_juben_agent import BaseJubenAgent
from utils.text_processor import TextTruncator, TextSplitter
from utils.batch_processor import BatchProcessor


class PlotPointsWorkflowAgent(BaseJubenAgent):
    """
    大情节点与详细情节点一键生成工作流智能体
    
    核心功能：
    1. 工作流编排和协调
    2. 智能体间的模块化外包
    3. 上下文隔离管理
    4. 批处理协调
    5. 结果整合和格式化
    
    工作流程：
    输入处理 → 文本分析 → 并行智能体调用 → 结果整合 → 输出
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化情节点工作流智能体"""
        super().__init__("plot_points_workflow", model_provider)
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 初始化文本处理工具
        self.text_truncator = TextTruncator()
        self.text_splitter = TextSplitter()
        self.batch_processor = BatchProcessor()
        
        # Agent as Tool机制 - 子智能体注册表（延迟加载）
        self.sub_agents = {}
        
        # 可调用的工具智能体映射
        self.available_tools = {
            "text_processor": "文本处理智能体",
            "story_summary": "故事大纲智能体",
            "major_plot_points": "大情节点智能体", 
            "mind_map": "思维导图智能体",
            "detailed_plot_points": "详细情节点智能体",
            "output_formatter": "输出整理智能体"
        }
        
        # 工作流配置参数
        self.default_chunk_size = 10000
        self.default_length_size = 50000
        self.batch_parallel_limit = 10
        self.batch_max_iterations = 100
        
        # 工作流状态管理
        self.workflow_state = {
            "current_step": None,
            "processed_chunks": [],
            "agent_results": {},
            "start_time": None,
            "end_time": None
        }
        
        self.logger.info("大情节点工作流智能体初始化完成（支持Agent as Tool机制）")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理情节点工作流请求
        
        Args:
            request_data: 请求数据，包含input、file、chunk_size、length_size等
            context: 上下文信息
            
        Yields:
            Dict[str, Any]: 流式响应事件
        """
        # 记录用户与会话信息，子Agent调用会复用
        user_id = context.get("user_id", "unknown") if context else "unknown"
        session_id = context.get("session_id", "unknown") if context else "unknown"
        self.workflow_state["user_id"] = user_id
        self.workflow_state["session_id"] = session_id

        try:
            # 初始化工作流状态
            self.workflow_state["start_time"] = datetime.now()
            self.workflow_state["current_step"] = "initialization"
            
            # 发送工作流开始事件
            yield {
                "type": "workflow_start",
                "message": "开始执行大情节点与详细情节点生成工作流",
                "timestamp": datetime.now().isoformat(),
                "workflow_id": str(uuid.uuid4())
            }
            
            # 步骤1：输入处理和验证
            async for event in self._process_input_validation(request_data):
                yield event
            
            # 步骤2：文本预处理
            async for event in self._process_text_preprocessing(request_data):
                yield event
            
            # 步骤3：批处理协调
            async for event in self._process_batch_coordination():
                yield event
            
            # 步骤4：智能体并行调用
            async for event in self._process_agent_coordination():
                yield event
            
            # 步骤5：结果整合
            async for event in self._process_result_integration():
                yield event
            
            # 完成工作流
            self.workflow_state["end_time"] = datetime.now()
            yield {
                "type": "workflow_complete",
                "message": "大情节点与详细情节点生成工作流执行完成",
                "timestamp": datetime.now().isoformat(),
                "processing_time": self._calculate_processing_time()
            }
            
        except Exception as e:
            self.logger.error(f"工作流执行失败: {e}")
            yield {
                "type": "workflow_error",
                "message": f"工作流执行失败: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def _process_input_validation(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """处理输入验证"""
        self.workflow_state["current_step"] = "input_validation"
        
        # 验证必需参数
        required_params = ["input"]
        missing_params = [param for param in required_params if param not in request_data]
        
        if missing_params:
            yield {
                "type": "validation_error",
                "message": f"缺少必需参数: {', '.join(missing_params)}",
                "timestamp": datetime.now().isoformat()
            }
            return
        
        # 设置默认参数
        chunk_size = request_data.get("chunk_size", self.default_chunk_size)
        length_size = request_data.get("length_size", self.default_length_size)
        
        # 存储参数到工作流状态
        self.workflow_state["params"] = {
            "chunk_size": chunk_size,
            "length_size": length_size,
            "input": request_data["input"],
            "file": request_data.get("file")
        }
        
        yield {
            "type": "input_validated",
            "message": "输入参数验证通过",
            "timestamp": datetime.now().isoformat(),
            "params": self.workflow_state["params"]
        }
    
    async def _process_text_preprocessing(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """处理文本预处理（增强版：带参数验证和错误处理）"""
        self.workflow_state["current_step"] = "text_preprocessing"

        input_text = request_data.get("input", "")
        length_size = self.workflow_state["params"].get("length_size", self.default_length_size)
        chunk_size = self.workflow_state["params"].get("chunk_size", self.default_chunk_size)

        # ========== 参数验证 ==========
        if not input_text:
            yield {
                "type": "text_processing_error",
                "message": "输入文本为空",
                "timestamp": datetime.now().isoformat()
            }
            return

        if length_size <= 0:
            self.logger.warning(f"length_size参数不合法({length_size})，使用默认值")
            length_size = self.default_length_size

        if chunk_size <= 0:
            self.logger.warning(f"chunk_size参数不合法({chunk_size})，使用默认值")
            chunk_size = self.default_chunk_size

        yield {
            "type": "text_processing_start",
            "message": "开始文本预处理",
            "timestamp": datetime.now().isoformat()
        }

        try:
            # 文本截断处理
            result_truncate = await self.text_truncator.truncate_text(
                input_text,
                max_length=length_size
            )

            # 处理返回结果（可能是字符串或字典）
            if isinstance(result_truncate, dict):
                if result_truncate.get("success"):
                    truncated_text = result_truncate.get("data", input_text[:length_size])
                else:
                    self.logger.error(f"文本截断失败: {result_truncate.get('msg')}")
                    truncated_text = input_text[:length_size]
            else:
                truncated_text = str(result_truncate)

            yield {
                "type": "text_truncated",
                "message": f"文本截断完成，长度: {len(truncated_text)}",
                "timestamp": datetime.now().isoformat()
            }

            # 文本分割处理
            chunks = await self.text_splitter.split_text(
                truncated_text,
                chunk_size=chunk_size
            )

            # 验证返回结果
            if not isinstance(chunks, list):
                self.logger.error(f"split_text返回非列表类型: {type(chunks)}")
                chunks = [truncated_text]

            # 过滤空chunk
            chunks = [c for c in chunks if c and isinstance(c, str) and len(c.strip()) > 0]

            if not chunks:
                self.logger.warning("分割后没有有效chunk，使用截断文本作为唯一chunk")
                chunks = [truncated_text]

            self.workflow_state["processed_chunks"] = chunks

            yield {
                "type": "text_split_complete",
                "message": f"文本分割完成，共{len(chunks)}个片段",
                "timestamp": datetime.now().isoformat(),
                "chunk_count": len(chunks)
            }

        except ValueError as e:
            self.logger.error(f"文本预处理参数错误: {e}")
            yield {
                "type": "text_processing_error",
                "message": f"参数错误: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"文本预处理失败: {e}")
            yield {
                "type": "text_processing_error",
                "message": f"文本预处理失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _process_batch_coordination(self) -> AsyncGenerator[Dict[str, Any], None]:
        """处理批处理协调"""
        self.workflow_state["current_step"] = "batch_coordination"
        
        chunks = self.workflow_state["processed_chunks"]
        
        yield {
            "type": "batch_processing_start",
            "message": f"开始批处理，共{len(chunks)}个文本片段",
            "timestamp": datetime.now().isoformat(),
            "parallel_limit": self.batch_parallel_limit
        }
        
        # 配置批处理器（兼容新的BatchProcessor接口）
        # 旧代码使用 .configure(...)，现在 BatchProcessor 提供 set_parallel_limit / set_max_iterations
        try:
            self.batch_processor.set_parallel_limit(self.batch_parallel_limit)
            self.batch_processor.set_max_iterations(self.batch_max_iterations)
        except AttributeError:
            # 向后兼容：如果未来重新引入 configure 方法，则优先调用
            try:
                configure = getattr(self.batch_processor, "configure", None)
                if configure:
                    configure(
                        parallel_limit=self.batch_parallel_limit,
                        max_iterations=self.batch_max_iterations
                    )
            except Exception as e:
                self.logger.warning(f"批处理器配置失败，使用默认参数: {e}")
        
        yield {
            "type": "batch_processor_configured",
            "message": "批处理器配置完成",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _process_agent_coordination(self) -> AsyncGenerator[Dict[str, Any], None]:
        """处理智能体协调"""
        self.workflow_state["current_step"] = "agent_coordination"
        
        yield {
            "type": "agent_coordination_start",
            "message": "开始智能体协调执行",
            "timestamp": datetime.now().isoformat()
        }
        
        # 并行调用各个智能体
        agent_tasks = [
            self._call_story_summary_agent(),
            self._call_major_plot_points_agent(),
            self._call_mind_map_agent(),
            self._call_detailed_plot_points_agent()
        ]
        
        # 等待所有智能体完成
        results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"智能体{i}执行失败: {result}")
                yield {
                    "type": "agent_error",
                    "message": f"智能体{i}执行失败: {str(result)}",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                self.workflow_state["agent_results"][f"agent_{i}"] = result
                yield {
                    "type": "agent_complete",
                    "message": f"智能体{i}执行完成",
                    "timestamp": datetime.now().isoformat()
                }
    
    async def _call_story_summary_agent(self) -> Dict[str, Any]:
        """调用故事大纲智能体，返回真实LLM结果"""
        try:
            from .story_summary_generator_agent import StorySummaryGeneratorAgent

            agent = StorySummaryGeneratorAgent()
            base_text = "\n\n".join(self.workflow_state.get("processed_chunks", []))
            user_id = self.workflow_state.get("user_id", "unknown")
            session_id = self.workflow_state.get("session_id", "unknown")

            request_data = {"input": base_text}
            sub_context = {
                "user_id": user_id,
                "session_id": session_id,
                "parent_agent": "plot_points_workflow",
                "tool_call": True,
            }

            chunks: list[str] = []
            async for event in agent.process_request(request_data, sub_context):
                et = event.get("event_type") or event.get("type")
                if et in ("llm_chunk", "content"):
                    # StorySummaryGeneratorAgent 使用 event_type="llm_chunk"
                    data = event.get("data") or event.get("content") or ""
                    if isinstance(data, str):
                        chunks.append(data)

            return {
                "type": "story_summary",
                "content": "".join(chunks),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"调用故事大纲智能体失败: {e}")
            return {
                "type": "story_summary",
                "content": f"故事大纲生成失败: {e}",
                "timestamp": datetime.now().isoformat(),
            }
    
    async def _call_major_plot_points_agent(self) -> Dict[str, Any]:
        """调用大情节点智能体，返回真实LLM结果"""
        try:
            from .major_plot_points_agent import MajorPlotPointsAgent

            agent = MajorPlotPointsAgent()
            base_text = "\n\n".join(self.workflow_state.get("processed_chunks", []))
            user_id = self.workflow_state.get("user_id", "unknown")
            session_id = self.workflow_state.get("session_id", "unknown")

            request_data = {"input": base_text}
            sub_context = {
                "user_id": user_id,
                "session_id": session_id,
                "parent_agent": "plot_points_workflow",
                "tool_call": True,
            }

            chunks: list[str] = []
            async for event in agent.process_request(request_data, sub_context):
                et = event.get("event_type") or event.get("type")
                if et in ("llm_chunk", "content"):
                    data = event.get("data") or event.get("content") or ""
                    if isinstance(data, str):
                        chunks.append(data)

            content = "".join(chunks)
            # 将结果暂存，便于详细情节点复用
            self.workflow_state.setdefault("intermediate", {})["major_plot_points"] = content

            return {
                "type": "major_plot_points",
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"调用大情节点智能体失败: {e}")
            return {
                "type": "major_plot_points",
                "content": f"大情节点分析失败: {e}",
                "timestamp": datetime.now().isoformat(),
            }
    
    async def _call_mind_map_agent(self) -> Dict[str, Any]:
        """调用思维导图智能体，返回真实MindMap JSON"""
        try:
            from .mind_map_agent import MindMapAgent

            agent = MindMapAgent()
            # 优先使用大情节点结果生成思维导图，没有则用原始文本
            major_text = self.workflow_state.get("intermediate", {}).get(
                "major_plot_points"
            )
            if not major_text:
                major_text = "\n\n".join(self.workflow_state.get("processed_chunks", []))

            user_id = self.workflow_state.get("user_id", "unknown")
            session_id = self.workflow_state.get("session_id", "unknown")

            request_data = {"input": major_text}
            sub_context = {
                "user_id": user_id,
                "session_id": session_id,
                "parent_agent": "plot_points_workflow",
                "tool_call": True,
            }

            mindmap_json = ""
            async for event in agent.process_request(request_data, sub_context):
                et = event.get("event_type") or event.get("type")
                if et in ("message", "llm_chunk", "content"):
                    data = event.get("data") or event.get("content") or ""
                    if isinstance(data, str):
                        mindmap_json += data

            return {
                "type": "mind_map",
                "json": mindmap_json,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"调用思维导图智能体失败: {e}")
            return {
                "type": "mind_map",
                "json": "",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
    
    async def _call_detailed_plot_points_agent(self) -> Dict[str, Any]:
        """调用详细情节点智能体，返回真实LLM结果"""
        try:
            from .detailed_plot_points_agent import DetailedPlotPointsAgent

            agent = DetailedPlotPointsAgent()
            # 详细情节点优先基于大情节点文本
            base_text = self.workflow_state.get("intermediate", {}).get(
                "major_plot_points"
            )
            if not base_text:
                base_text = "\n\n".join(self.workflow_state.get("processed_chunks", []))

            user_id = self.workflow_state.get("user_id", "unknown")
            session_id = self.workflow_state.get("session_id", "unknown")

            request_data = {"input": base_text}
            sub_context = {
                "user_id": user_id,
                "session_id": session_id,
                "parent_agent": "plot_points_workflow",
                "tool_call": True,
            }

            chunks: list[str] = []
            async for event in agent.process_request(request_data, sub_context):
                et = event.get("event_type") or event.get("type")
                if et in ("llm_chunk", "content"):
                    data = event.get("data") or event.get("content") or ""
                    if isinstance(data, str):
                        chunks.append(data)

            return {
                "type": "detailed_plot_points",
                "content": "".join(chunks),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"调用详细情节点智能体失败: {e}")
            return {
                "type": "detailed_plot_points",
                "content": f"详细情节点分析失败: {e}",
                "timestamp": datetime.now().isoformat(),
            }
    
    async def _process_result_integration(self) -> AsyncGenerator[Dict[str, Any], None]:
        """处理结果整合"""
        self.workflow_state["current_step"] = "result_integration"
        
        yield {
            "type": "result_integration_start",
            "message": "开始结果整合",
            "timestamp": datetime.now().isoformat()
        }
        
        # 整合所有智能体的结果（结构化）
        final_result = {
            "story_summary": self.workflow_state["agent_results"].get("agent_0", {}).get("content", ""),
            "major_plot_points": self.workflow_state["agent_results"].get("agent_1", {}).get("content", ""),
            "mind_map": {
                "pic": self.workflow_state["agent_results"].get("agent_2", {}).get("pic", ""),
                "jump_link": self.workflow_state["agent_results"].get("agent_2", {}).get("jump_link", "")
            },
            "detailed_plot_points": self.workflow_state["agent_results"].get("agent_3", {}).get("content", ""),
            "metadata": {
                "processing_time": self._calculate_processing_time(),
                "chunks_processed": len(self.workflow_state["processed_chunks"]),
                "agents_used": list(self.available_tools.keys())
            }
        }

        # 构建可直接展示的文本结果，供前端聊天窗口使用
        try:
            text_parts = []
            if final_result["story_summary"]:
                text_parts.append("【故事大纲】")
                text_parts.append(final_result["story_summary"])
                text_parts.append("")
            if final_result["major_plot_points"]:
                text_parts.append("【大情节点分析】")
                text_parts.append(final_result["major_plot_points"])
                text_parts.append("")
            if final_result["detailed_plot_points"]:
                text_parts.append("【详细情节点分析】")
                text_parts.append(final_result["detailed_plot_points"])
                text_parts.append("")
            if final_result["mind_map"].get("jump_link") or final_result["mind_map"].get("pic"):
                text_parts.append("【思维导图】")
                pic = final_result["mind_map"].get("pic")
                link = final_result["mind_map"].get("jump_link")
                if pic:
                    text_parts.append(f"图片链接：{pic}")
                if link:
                    text_parts.append(f"编辑链接：{link}")
                text_parts.append("")

            final_text = "\n".join(text_parts).strip()
        except Exception as e:
            self.logger.error(f"构建情节点工作流文本结果失败: {e}")
            final_text = ""

        # 将最终文本作为 llm_chunk 事件输出，便于前端直接展示
        if final_text:
            yield {
                "type": "llm_chunk",
                "content": final_text,
                "timestamp": datetime.now().isoformat()
            }

        yield {
            "type": "final_result",
            "message": "结果整合完成",
            "timestamp": datetime.now().isoformat(),
            "result": final_result
        }
    
    def _calculate_processing_time(self) -> str:
        """计算处理时间"""
        if self.workflow_state["start_time"] and self.workflow_state["end_time"]:
            duration = self.workflow_state["end_time"] - self.workflow_state["start_time"]
            return str(duration.total_seconds()) + "秒"
        return "未知"
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        调用其他智能体作为工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            Dict[str, Any]: 工具执行结果
        """
        if tool_name not in self.available_tools:
            raise ValueError(f"未知工具: {tool_name}")
        
        # 延迟加载子智能体
        if tool_name not in self.sub_agents:
            self.sub_agents[tool_name] = await self._load_sub_agent(tool_name)
        
        # 调用子智能体
        sub_agent = self.sub_agents[tool_name]
        return await sub_agent.process_request(kwargs)
    
    async def _load_sub_agent(self, tool_name: str):
        """延迟加载子智能体"""
        # 这里应该根据tool_name动态加载对应的智能体
        # 暂时返回None
        return None
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """获取工作流信息"""
        return {
            "agent_name": self.agent_name,
            "description": "大情节点与详细情节点一键生成工作流智能体",
            "available_tools": self.available_tools,
            "workflow_state": self.workflow_state,
            "configuration": {
                "default_chunk_size": self.default_chunk_size,
                "default_length_size": self.default_length_size,
                "batch_parallel_limit": self.batch_parallel_limit,
                "batch_max_iterations": self.batch_max_iterations
            }
        }

from typing import AsyncGenerator, Dict, Any, Optional, List

"""
小说初筛评估和分析智能体 - 基于Agent as Tool机制
实现coze工作流的小说初筛评估功能

业务处理逻辑：
1. 输入处理：接收小说文本，支持长文本截断和分割处理
2. 故事大纲总结：使用StorySummaryGeneratorAgent生成故事大纲
3. 多轮评估：循环10次对小说进行深度评估分析
4. 评分统计：汇总多轮评估结果，进行评分统计分析
5. 评级逻辑：根据评分统计结果进行A/B/C/D等级评定
6. 子智能体调用：使用Agent as Tool机制调用专业评估子智能体
7. 上下文隔离：确保每次评估的独立性和准确性
8. 结果整合：汇总评估结果，生成完整的评估报告
9. 输出格式化：返回结构化的评估数据和评级结果

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

from utils.text_processor import TextSplitter

class NovelScreeningEvaluationAgent(BaseJubenAgent):
    """
    小说初筛评估和分析智能体
    
    核心功能：
    1. 文本截断和分割处理
    2. 故事大纲总结
    3. 多轮故事评估（循环10次）
    4. 评分统计和评级逻辑
    5. Agent as Tool机制：调用子智能体作为工具
    6. 模块化外包：智能体间相互调用，上下文隔离
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化小说初筛评估智能体"""
        super().__init__("novel_screening_evaluation", model_provider)
        
        # 系统提示词配置（从prompts文件夹加载）
        # 初始化文本处理器
        self.text_splitter = TextSplitter()
        
        # Agent as Tool机制 - 子智能体注册表（延迟加载）
        self.sub_agents = {}
        
        # 可调用的工具智能体映射
        self.available_tools = {
            "story_summary_generator": "故事梗概生成智能体",
            "story_evaluation": "故事评估智能体",
            "score_analyzer": "评分分析智能体",
            "text_truncator": "文本截断工具"
        }
        
        # 工作流配置
        self.evaluation_rounds = 10  # 评估轮次
        self.batch_parallel_limit = 10  # 批处理并行数量
        self.batch_max_iterations = 100  # 批处理最大迭代次数
        self.default_chunk_size = 10000  # 默认文本块大小
        self.default_length_size = 800  # 默认截断长度
        
        # 工作流状态
        self.workflow_state = {
            "current_step": None,
            "processing_file": False,
            "evaluation_results": [],
            "final_rating": None
        }
        
        self.logger.info("小说初筛评估智能体初始化完成（支持Agent as Tool机制）")
    
    # 系统提示词由基类自动加载，无需重写
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理小说初筛评估请求
        
        Args:
            request_data: 包含file, chunk_size, length_size, short_file, theme等参数
            context: 上下文信息
            
        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            # 发送开始事件
            yield {
                "event_type": "workflow_start",
                "data": {
                    "agent_name": self.agent_name,
                    "workflow": "novel_screening_evaluation",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # 解析输入参数
            file_content = request_data.get("file", "")
            chunk_size = request_data.get("chunk_size", self.default_chunk_size)
            length_size = request_data.get("length_size", self.default_length_size)
            short_file_content = request_data.get("short_file", "")
            theme = request_data.get("theme", "小说")
            
            # 更新工作流状态
            self.workflow_state["current_step"] = "input_parsing"
            
            yield {
                "event_type": "workflow_step",
                "data": {
                    "step": "input_parsing",
                    "message": "正在解析输入参数...",
                    "parameters": {
                        "has_file": bool(file_content),
                        "has_short_file": bool(short_file_content),
                        "theme": theme,
                        "chunk_size": chunk_size,
                        "length_size": length_size
                    }
                }
            }
            
            # 判断用户是否上传了文件，选择处理分支
            if file_content:
                # 第一个分支：处理完整文件
                async for event in self._process_full_file_branch(
                    file_content, chunk_size, length_size, theme, context
                ):
                    yield event
            elif short_file_content:
                # 第二个分支：处理短文件
                async for event in self._process_short_file_branch(
                    short_file_content, length_size, theme, context
                ):
                    yield event
            else:
                # 没有文件输入，返回错误
                yield {
                    "event_type": "error",
                    "data": {
                        "error": "没有提供文件内容",
                        "message": "请提供file或short_file参数"
                    }
                }
                return
            
            # 发送工作流完成事件
            yield {
                "event_type": "workflow_complete",
                "data": {
                    "agent_name": self.agent_name,
                    "final_rating": self.workflow_state.get("final_rating"),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"处理小说初筛评估请求时发生错误: {str(e)}")
            yield {
                "event_type": "error",
                "data": {
                    "error": str(e),
                    "message": "小说初筛评估过程中发生错误"
                }
            }
    
    async def _process_full_file_branch(
        self, 
        file_content: str, 
        chunk_size: int, 
        length_size: int, 
        theme: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理完整文件分支"""
        
        # 2.1.1 文本截断
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "text_truncation",
                "message": "正在进行文本截断处理..."
            }
        }
        
        truncated_text = await self._truncate_text(file_content, length_size)
        
        # 2.1.2 文本分割
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "text_splitting",
                "message": "正在进行文本分割处理..."
            }
        }
        
        text_chunks = await self._split_text(truncated_text, chunk_size)
        
        # 2.1.3 批处理 - 故事大纲总结
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "story_summary",
                "message": "正在生成故事大纲总结..."
            }
        }
        
        summary_results = await self._batch_process_summary(text_chunks, context)
        
        # 2.1.4 整合各阶段总结
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "summary_integration",
                "message": "正在整合各阶段总结..."
            }
        }
        
        integrated_summary = await self._integrate_summaries(summary_results)
        
        # 2.1.5 循环评估（10次）
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "story_evaluation",
                "message": f"正在进行故事评估（{self.evaluation_rounds}轮）..."
            }
        }
        
        evaluation_results = await self._batch_evaluate_story(
            integrated_summary, theme, context
        )
        
        # 2.1.6 评分统计和分析
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "score_analysis",
                "message": "正在进行评分统计和分析..."
            }
        }
        
        final_analysis = await self._analyze_scores(evaluation_results)
        
        # 2.1.7 创建文档
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "document_creation",
                "message": "正在创建评估结果文档..."
            }
        }
        
        document_result = await self._create_evaluation_document(final_analysis)
        
        # 更新工作流状态
        self.workflow_state["final_rating"] = self._extract_rating_from_analysis(final_analysis)
        self.workflow_state["evaluation_results"] = evaluation_results
        
        # 返回最终结果
        yield {
            "event_type": "final_result",
            "data": {
                "workflow": "full_file_branch",
                "document_url": document_result.get("url"),
                "analysis": final_analysis,
                "rating": self.workflow_state["final_rating"]
            }
        }
    
    async def _process_short_file_branch(
        self, 
        short_file_content: str, 
        length_size: int, 
        theme: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理短文件分支"""
        
        # 2.2.1 文本截断
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "text_truncation",
                "message": "正在进行文本截断处理..."
            }
        }
        
        truncated_text = await self._truncate_text(short_file_content, length_size)
        
        # 2.2.2 循环评估（10次）
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "story_evaluation",
                "message": f"正在进行故事评估（{self.evaluation_rounds}轮）..."
            }
        }
        
        evaluation_results = await self._batch_evaluate_story(
            truncated_text, theme, context
        )
        
        # 2.2.3 评分统计和分析
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "score_analysis",
                "message": "正在进行评分统计和分析..."
            }
        }
        
        final_analysis = await self._analyze_scores(evaluation_results)
        
        # 2.2.4 创建文档
        yield {
            "event_type": "workflow_step",
            "data": {
                "step": "document_creation",
                "message": "正在创建评估结果文档..."
            }
        }
        
        document_result = await self._create_evaluation_document(final_analysis)
        
        # 更新工作流状态
        self.workflow_state["final_rating"] = self._extract_rating_from_analysis(final_analysis)
        self.workflow_state["evaluation_results"] = evaluation_results
        
        # 返回最终结果
        yield {
            "event_type": "final_result",
            "data": {
                "workflow": "short_file_branch",
                "document_url": document_result.get("url"),
                "analysis": final_analysis,
                "rating": self.workflow_state["final_rating"]
            }
        }
    
    async def _truncate_text(self, text: str, max_length: int) -> str:
        """文本截断功能（增强版：带参数验证和错误处理）"""
        try:
            # ========== 参数验证 ==========
            if not text or not isinstance(text, str):
                return ""

            if max_length <= 0:
                self.logger.warning(f"max_length参数不合法({max_length})，使用默认值800")
                max_length = 800

            # 调用文本截断工具智能体
            tool_result = await self._call_agent_as_tool(
                "text_truncator",
                {"text": text, "max_length": max_length}
            )

            # 处理返回结果
            if isinstance(tool_result, dict):
                if tool_result.get("success"):
                    return tool_result.get("truncated_text", tool_result.get("data", text[:max_length]))
                else:
                    self.logger.error(f"文本截断失败: {tool_result.get('error')}")
                    return text[:max_length]
            else:
                return str(tool_result) if tool_result else text[:max_length]

        except Exception as e:
            self.logger.warning(f"文本截断工具调用失败，使用默认截断: {str(e)}")
            # 降级处理：使用安全的截断
            safe_length = max(1, min(max_length if max_length > 0 else 800, len(text)))
            return text[:safe_length]

    async def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """文本分割功能（增强版：带参数验证和错误处理）"""
        try:
            # ========== 参数验证 ==========
            if not text or not isinstance(text, str):
                return []

            if chunk_size <= 0:
                self.logger.warning(f"chunk_size参数不合法({chunk_size})，使用默认值10000")
                chunk_size = 10000

            # 调用text_splitter进行分割
            chunks = await self.text_splitter.split_text(text, chunk_size)

            # 验证返回结果
            if not isinstance(chunks, list):
                self.logger.error(f"split_text返回非列表类型: {type(chunks)}")
                chunks = []

            # 过滤空chunk
            chunks = [c for c in chunks if c and isinstance(c, str) and len(c.strip()) > 0]

            if not chunks:
                self.logger.warning("分割后没有有效chunk，使用原文作为唯一chunk")
                return [text]

            return chunks

        except Exception as e:
            self.logger.warning(f"文本分割失败，使用默认分割: {str(e)}")
            # 降级处理：使用安全的简单分割
            safe_chunk_size = max(1, min(chunk_size if chunk_size > 0 else 10000, len(text)))
            return [text[i:min(i + safe_chunk_size, len(text))] for i in range(0, len(text), safe_chunk_size)]
    
    async def _batch_process_summary(
        self, 
        text_chunks: List[str], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """批处理故事大纲总结"""
        summary_results = []
        
        # 并行处理文本块（限制并发数量）
        semaphore = asyncio.Semaphore(self.batch_parallel_limit)
        
        async def process_chunk(chunk):
            async with semaphore:
                try:
                    # 调用故事大纲总结工具智能体
                    tool_result = await self._call_agent_as_tool(
                        "story_summary", 
                        {"text": chunk}
                    )
                    return tool_result.get("summary", "")
                except Exception as e:
                    self.logger.error(f"故事大纲总结失败: {str(e)}")
                    return ""
        
        # 执行并行处理
        tasks = [process_chunk(chunk) for chunk in text_chunks]
        summary_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤异常结果
        summary_results = [result for result in summary_results if isinstance(result, str) and result]
        
        return summary_results
    
    async def _integrate_summaries(self, summaries: List[str]) -> str:
        """整合各阶段总结"""
        return "\n\n".join(summaries)
    
    async def _batch_evaluate_story(
        self, 
        story_text: str, 
        theme: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """批处理故事评估（循环10次）"""
        evaluation_results = []
        
        # 并行处理评估（限制并发数量）
        semaphore = asyncio.Semaphore(self.batch_parallel_limit)
        
        async def evaluate_story(round_num):
            async with semaphore:
                try:
                    # 调用故事评估工具智能体
                    tool_result = await self._call_agent_as_tool(
                        "story_evaluation", 
                        {"story_text": story_text, "theme": theme, "round": round_num}
                    )
                    return tool_result.get("evaluation", "")
                except Exception as e:
                    self.logger.error(f"故事评估第{round_num}轮失败: {str(e)}")
                    return ""
        
        # 执行并行评估
        tasks = [evaluate_story(i+1) for i in range(self.evaluation_rounds)]
        evaluation_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤异常结果
        evaluation_results = [result for result in evaluation_results if isinstance(result, str) and result]
        
        return evaluation_results
    
    async def _analyze_scores(self, evaluation_results: List[str]) -> str:
        """评分统计和分析 - 使用基类方法"""
        try:
            # 提取评分
            scores = []
            detailed_results = []
            
            for result in evaluation_results:
                # 提取评分 - 使用基类方法
                extracted_scores = self.extract_scores_from_text(result)
                total_score = extracted_scores.get("total_score") or extracted_scores.get("overall_evaluation")
                if total_score:
                    scores.append(total_score)
                
                detailed_results.append({
                    "score": total_score,
                    "text": result
                })
            
            # 计算评级 - 使用基类方法
            attention_level = self.calculate_rating_level(scores, self.evaluation_rounds)
            
            # 生成分析摘要 - 使用基类方法
            analysis = self.generate_analysis_summary(scores, attention_level, detailed_results)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"评分分析失败: {str(e)}")
            return "评分分析过程中发生错误"
    
    async def _create_evaluation_document(self, analysis: str) -> Dict[str, Any]:
        """创建评估结果文档"""
        try:
            # 这里应该调用文档创建工具
            # 暂时返回模拟结果
            return {
                "success": True,
                "url": f"https://example.com/document/{int(time.time())}",
                "title": "小说初筛评估结果"
            }
        except Exception as e:
            self.logger.error(f"文档创建失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _extract_rating_from_analysis(self, analysis: str) -> Optional[str]:
        """从分析结果中提取评级 - 使用基类方法"""
        return self.extract_rating_from_analysis(analysis)
    
    async def _call_agent_as_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用其他智能体作为工具 - Agent as Tool机制的核心实现（增强版：带超时）

        Args:
            tool_name: 工具智能体名称
            tool_input: 工具输入参数
            context: 上下文信息

        Returns:
            Dict: 工具调用结果
        """
        import asyncio

        try:
            # ========== 参数验证 ==========
            if not tool_name or not isinstance(tool_name, str):
                return {
                    "success": False,
                    "error": f"无效的工具名称: {type(tool_name).__name__}",
                    "tool_name": tool_name
                }

            if not tool_input or not isinstance(tool_input, dict):
                return {
                    "success": False,
                    "error": f"无效的工具输入: {type(tool_input).__name__}",
                    "tool_name": tool_name
                }

            # 统一 SubagentRunner：别名 → 真实 agent_id
            agent_id_map = {
                "story_summary": "story_summary_generator",
                "story_evaluation": "story_evaluation",
                "score_analyzer": "score_analyzer",
                "text_truncator": "text_truncator",
            }
            agent_id = agent_id_map.get(tool_name, tool_name)
            task = (
                tool_input.get("input")
                or tool_input.get("query")
                or tool_input.get("text")
                or str(tool_input)
            )
            depth = int((context or {}).get("subagent_depth") or 0)
            spawn_result = await self.spawn_subagent(
                agent_id,
                str(task),
                context=context,
                timeout=60,
                depth=depth,
            )
            return {
                "success": spawn_result.get("success", False),
                "result": spawn_result.get("result") or "",
                "error": spawn_result.get("error"),
                "tool_name": tool_name,
            }

        except ValueError as e:
            self.logger.error(f"工具调用参数错误: {e}")
            return {
                "success": False,
                "error": f"参数错误: {str(e)}",
                "tool_name": tool_name
            }
        except Exception as e:
            self.logger.error(f"调用工具智能体{tool_name}失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    async def _get_tool_agent(self, tool_name: str):
        """获取工具智能体实例（延迟加载）"""
        if tool_name not in self.sub_agents:
            try:
                if tool_name == "story_summary":
                    from .story_summary_generator_agent import StorySummaryGeneratorAgent
                    self.sub_agents[tool_name] = StorySummaryGeneratorAgent()
                elif tool_name == "story_evaluation":
                    from .story_evaluation_agent import StoryEvaluationAgent
                    self.sub_agents[tool_name] = StoryEvaluationAgent()
                elif tool_name == "score_analyzer":
                    from .score_analyzer_agent import ScoreAnalyzerAgent
                    self.sub_agents[tool_name] = ScoreAnalyzerAgent()
                elif tool_name == "text_truncator":
                    from .text_truncator_agent import TextTruncatorAgent
                    self.sub_agents[tool_name] = TextTruncatorAgent()
                else:
                    self.logger.error(f"未知的工具智能体: {tool_name}")
                    return None
            except ImportError as e:
                self.logger.error(f"导入工具智能体{tool_name}失败: {str(e)}")
                return None

        return self.sub_agents.get(tool_name)
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """获取工作流信息"""
        return {
            "agent_name": self.agent_name,
            "description": "小说初筛评估和分析智能体",
            "available_tools": self.available_tools,
            "workflow_state": self.workflow_state,
            "configuration": {
                "evaluation_rounds": self.evaluation_rounds,
                "batch_parallel_limit": self.batch_parallel_limit,
                "batch_max_iterations": self.batch_max_iterations,
                "default_chunk_size": self.default_chunk_size,
                "default_length_size": self.default_length_size
            }
        }

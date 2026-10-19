"""
故事五元素分析智能体
基于Coze工作流设计的故事分析系统，包含五个子智能体的专业分析

业务处理逻辑：
1. 文本预处理：使用TextTruncator和TextSplitter处理长文本
2. 批处理机制：支持大批量文本的并行处理
3. 五个专业子智能体协调：
   - StoryTypeAnalyzerAgent：题材类型与创意提炼
   - StorySummaryGeneratorAgent：故事梗概生成（800-2500字）
   - CharacterProfileGeneratorAgent：人物小传生成（至少8个人物）
   - CharacterRelationshipAnalyzerAgent：人物关系分析（至少12对关系）
   - PlotPointsAnalyzerAgent：大情节点分析（按发展阶段排列）
4. 思维导图生成：使用MindMapGenerator生成可视化思维导图
5. Agent as Tool：调用子智能体作为工具，实现上下文隔离
6. 结果整合：汇总五个子智能体的分析结果
7. 输出格式化：生成完整的五元素分析报告

代码作者：宫灵瑞
创建时间：2024年10月19日
"""
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
import json
import re

try:
    from .base_juben_agent import BaseJubenAgent
    from ..utils.text_processor import TextTruncator, TextSplitter
    from ..utils.batch_processor import BatchProcessor
    from ..utils.mind_map_generator import MindMapGenerator
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from agents.base_juben_agent import BaseJubenAgent
    from utils.text_processor import TextTruncator, TextSplitter
    from utils.batch_processor import BatchProcessor
    from utils.mind_map_generator import MindMapGenerator


class StoryFiveElementsAgent(BaseJubenAgent):
    """
    故事五元素分析智能体 - 支持Agent as Tool机制
    
    核心功能：
    1. 文本截断和分割处理
    2. 批处理机制
    3. 五个专业子智能体分析：
       - 题材类型与创意提炼
       - 故事梗概
       - 人物小传
       - 人物关系
       - 大情节点
    4. 思维导图生成
    5. Agent as Tool: 调用子智能体作为工具
    6. 模块化外包: 智能体间相互调用，上下文隔离
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化故事五元素分析智能体"""
        super().__init__("story_five_elements", model_provider)
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 初始化文本处理工具
        self.text_truncator = TextTruncator()
        self.text_splitter = TextSplitter()
        self.batch_processor = BatchProcessor()
        self.mind_map_generator = MindMapGenerator()
        
        # Agent as Tool机制 - 子智能体注册表（延迟加载）
        self.sub_agents = {}
        # 🆕 【新增】子智能体加载锁（防止竞态条件）
        self._sub_agents_lock = asyncio.Lock()
        
        # 可调用的工具智能体映射
        self.available_tools = {
            "story_type_analyzer": "题材类型与创意提炼智能体",
            "story_summary_generator": "故事梗概生成智能体", 
            "character_profile_generator": "人物小传生成智能体",
            "character_relationship_analyzer": "人物关系分析智能体",
            "plot_points_analyzer": "大情节点分析智能体"
        }
        
        # 默认参数配置
        self.default_chunk_size = 10000
        self.default_length_size = 50000
        self.batch_parallel_limit = 10
        self.batch_max_iterations = 100

        # 工具调用超时和重试配置
        self.tool_call_timeout = 30
        self.tool_call_max_retries = 3
        
        self.logger.info("故事五元素分析智能体初始化完成（支持Agent as Tool机制）")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理故事五元素分析请求
        
        Args:
            request_data: 请求数据
            context: 上下文信息
            
        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            input_text = request_data.get("input", "")
            input_file = request_data.get("file")
            chunk_size = request_data.get("chunk_size", self.default_chunk_size)
            length_size = request_data.get("length_size", self.default_length_size)
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            
            self.logger.info(f"开始处理故事五元素分析请求: {input_text[:100]}...")
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 发送开始处理事件
            yield await self._emit_event("system", "📚 开始故事五元素分析...")
            
            # 1. 文本截断处理
            yield await self._emit_event("system", "✂️ 正在处理输入文本...")
            truncated_text = await self._truncate_text(input_text, input_file, length_size)
            yield await self._emit_event("system", f"✅ 文本截断完成，长度: {len(truncated_text)} 字符")
            
            # 2. 文本分割处理
            yield await self._emit_event("system", "📄 正在分割文本...")
            text_chunks = await self._split_text(truncated_text, chunk_size)
            yield await self._emit_event("system", f"✅ 文本分割完成，共 {len(text_chunks)} 个片段")
            
            # 3. 批处理总结
            yield await self._emit_event("system", "🔄 正在批处理文本片段...")
            batch_summaries = await self._batch_process_chunks(text_chunks, user_id, session_id)
            yield await self._emit_event("system", f"✅ 批处理完成，获得 {len(batch_summaries)} 个总结")
            
            # 4. 整合批处理结果
            yield await self._emit_event("system", "📋 正在整合分析结果...")
            integrated_summary = await self._integrate_summaries(batch_summaries)
            yield await self._emit_event("system", "✅ 结果整合完成")
            
            # 5. 五个子智能体分析
            analysis_results = {}
            
            # 5.1 题材类型与创意提炼
            yield await self._emit_event("system", "🎭 正在进行题材类型与创意提炼分析...")
            analysis_results["story_type"] = await self._call_sub_agent("story_type_analyzer", integrated_summary, context)
            yield await self._emit_event("system", "✅ 题材类型分析完成")
            
            # 5.2 故事梗概
            yield await self._emit_event("system", "📖 正在生成故事梗概...")
            analysis_results["story_summary"] = await self._call_sub_agent("story_summary_generator", integrated_summary, context)
            yield await self._emit_event("system", "✅ 故事梗概生成完成")
            
            # 5.3 人物小传
            yield await self._emit_event("system", "👥 正在生成人物小传...")
            analysis_results["character_profiles"] = await self._call_sub_agent("character_profile_generator", integrated_summary, context)
            yield await self._emit_event("system", "✅ 人物小传生成完成")
            
            # 5.4 人物关系
            yield await self._emit_event("system", "🔗 正在分析人物关系...")
            analysis_results["character_relationships"] = await self._call_sub_agent("character_relationship_analyzer", integrated_summary, context)
            yield await self._emit_event("system", "✅ 人物关系分析完成")
            
            # 5.5 大情节点
            yield await self._emit_event("system", "🎬 正在分析大情节点...")
            analysis_results["plot_points"] = await self._call_sub_agent("plot_points_analyzer", integrated_summary, context)
            yield await self._emit_event("system", "✅ 大情节点分析完成")
            
            # 6. 生成思维导图
            yield await self._emit_event("system", "🗺️ 正在生成思维导图...")
            mind_map_result = await self._generate_mind_map(analysis_results["plot_points"])
            analysis_results["mind_map"] = mind_map_result
            yield await self._emit_event("system", "✅ 思维导图生成完成")
            
            # 7. 整理最终输出
            yield await self._emit_event("system", "📝 正在整理最终分析结果...")
            final_result = await self._compile_final_result(analysis_results)
            
            # 8. 流式输出最终结果
            yield await self._emit_event("system", "🎉 故事五元素分析完成！")
            yield await self._emit_event("final_result", final_result)
            
            # 9. 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")
            
        except Exception as e:
            self.logger.error(f"处理请求失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")
    
    async def _truncate_text(self, input_text: str, input_file: Optional[str], length_size: int) -> str:
        """截断文本（增强版：带参数验证和错误处理）"""
        try:
            # ========== 参数验证 ==========
            if length_size <= 0:
                self.logger.warning(f"length_size参数不合法({length_size})，使用默认值50000")
                length_size = 50000

            # 检查input_file是否存在
            if input_file:
                from pathlib import Path
                file_path = Path(input_file)
                if not file_path.exists():
                    self.logger.warning(f"文件不存在: {input_file}，使用输入文本")
                    input_file = None

            if input_file:
                # 如果有文件，从文件读取内容
                result = await self.text_truncator.truncate_file(input_file, length_size)
                if isinstance(result, dict):
                    if result.get("success"):
                        return result.get("data", "")
                    else:
                        self.logger.error(f"文本截断失败: {result.get('msg')}")
                        # 降级处理：直接截断输入文本
                        if input_text:
                            return input_text[:length_size]
                        return ""
                return str(result)
            else:
                # 直接截断输入文本
                result = await self.text_truncator.truncate_text(input_text, length_size)
                if isinstance(result, dict):
                    if result.get("success"):
                        return result.get("data", input_text[:length_size] if input_text else "")
                    else:
                        self.logger.error(f"文本截断失败: {result.get('msg')}")
                        # 降级处理：直接截断
                        return input_text[:length_size] if input_text else ""
                return str(result)

        except ValueError as e:
            self.logger.error(f"文本截断参数错误: {e}")
            # 降级处理：使用安全的截断
            safe_length = max(1, min(length_size, len(input_text)))
            return input_text[:safe_length] if input_text else ""
        except Exception as e:
            self.logger.error(f"文本截断失败: {e}")
            # 降级处理：返回原始文本（限制长度）
            safe_length = max(1, min(length_size if length_size > 0 else 50000, len(input_text)))
            return input_text[:safe_length] if input_text else ""

    async def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """分割文本（增强版：带参数验证和错误处理）"""
        try:
            # ========== 参数验证 ==========
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

            self.logger.info(f"文本分割完成: {len(chunks)}个chunk")
            return chunks

        except ValueError as e:
            self.logger.error(f"文本分割参数错误: {e}")
            # 降级处理：使用安全的简单分割
            safe_chunk_size = max(1, min(chunk_size, len(text)))
            return [text[i:min(i + safe_chunk_size, len(text))] for i in range(0, len(text), safe_chunk_size)]
        except Exception as e:
            self.logger.error(f"文本分割失败: {e}")
            # 降级处理：返回原文作为单个chunk
            return [text]
    
    async def _batch_process_chunks(self, chunks: List[str], user_id: str, session_id: str) -> List[str]:
        """批处理文本片段（并发版本）"""
        try:
            # ========== 并发控制 ==========
            # 使用信号量限制并发数量，避免资源耗尽
            semaphore = asyncio.Semaphore(5)  # 最多5个并发任务

            async def process_chunk_with_semaphore(chunk: str, index: int) -> tuple:
                """带信号量控制的片段处理"""
                async with semaphore:
                    self.logger.info(f"处理文本片段 {index+1}/{len(chunks)}")
                    try:
                        # 设置单个片段处理超时（3分钟）
                        summary = await asyncio.wait_for(
                            self._generate_chunk_summary(chunk, user_id, session_id),
                            timeout=180.0
                        )
                        return (index, summary)
                    except asyncio.TimeoutError:
                        self.logger.warning(f"片段 {index+1} 处理超时")
                        return (index, f"处理超时")
                    except Exception as e:
                        self.logger.error(f"片段 {index+1} 处理失败: {e}")
                        return (index, f"处理失败: {str(e)}")

            # ========== 并发处理所有片段 ==========
            tasks = [
                process_chunk_with_semaphore(chunk, i)
                for i, chunk in enumerate(chunks)
            ]

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 按原始顺序整理结果
            summaries = [None] * len(chunks)
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"任务异常: {result}")
                    continue
                if isinstance(result, tuple):
                    index, summary = result
                    summaries[index] = summary

            # 填充失败的结果
            for i, summary in enumerate(summaries):
                if summary is None:
                    summaries[i] = f"处理失败"

            return summaries

        except Exception as e:
            self.logger.error(f"批处理失败: {e}")
            return [f"处理失败: {str(e)}" for _ in chunks]
    
    async def _generate_chunk_summary(self, chunk: str, user_id: str, session_id: str) -> str:
        """生成单个片段的总结"""
        try:
            # 构建总结提示词
            summary_prompt = f"""
## Profile:
- role: 资深的故事编辑
- language: 中文
- description: 对提供的故事文本的进行阅读与理解，总结提炼其中的人物、人物关系、情节，并整理成行文流畅的故事大纲。

## Constrains:
- 请严格控制你总结的故事文本内容字数在300个汉字以上，500个汉字以下，切记不要超过500个汉字。。
- 请严格按照文本原文所表达的意思总结文本主要内容，不要自行进行创作与改编。
- 请直接输出所总结的文本主要内容，不要带任何其他标题。
- 请避免出现幻觉，不要将提示词的任何内容带进你输出的回答中。
- 输出回答时，不要对文本内容做任何总结、评述性的概述。
- 输出回答时，不要重复输出相同的内容。

## Skills:
- 善于准确地总结故事文本中的人物、人物关系、人物行动、事件情节。
- 擅长辨别故事文本中第一人称叙事与第三人称叙事的区别，并用第三人称进行准确地总结。
- 擅长理解复杂的人物身份、人物关系，并进行准确地总结。
- 擅长用优美准确的语言总结梗概。

## Workflows:
- 第一步，对提供的故事文本进行深入地阅读，准确理解故事文本中的人物、人物关系、事件情节。
- 第二步，根据第一步的阅读，将故事文本总结为一篇行文流畅的故事大纲。要求字数严格保持在300个汉字以上，500个汉字以下，切记不要超过500个汉字。

## OutputFormat:
<用流畅的文字总结故事大纲，不要带任何其他标题。>

## 故事文本：
{chunk}
"""
            
            # 调用LLM生成总结
            messages = [{"role": "user", "content": summary_prompt}]
            summary = await self._call_llm(messages, user_id, session_id)
            
            return summary
        except Exception as e:
            self.logger.error(f"生成片段总结失败: {e}")
            return f"总结生成失败: {str(e)}"
    
    async def _integrate_summaries(self, summaries: List[str]) -> str:
        """整合所有总结"""
        try:
            integrated_text = "\n\n".join(summaries)
            return integrated_text
        except Exception as e:
            self.logger.error(f"整合总结失败: {e}")
            return "整合失败"
    
    async def _call_sub_agent(self, agent_name: str, input_text: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """调用子智能体（增强版：带超时控制）"""
        import asyncio

        try:
            # ========== 参数验证 ==========
            if not agent_name or not isinstance(agent_name, str):
                return {"success": False, "error": f"无效的智能体名称: {type(agent_name).__name__}", "agent_name": str(agent_name)}

            if not input_text or not isinstance(input_text, str):
                return {"success": False, "error": "输入文本为空或类型不正确", "agent_name": agent_name}

            # 获取子智能体实例
            sub_agent = await self._get_sub_agent(agent_name)
            if not sub_agent:
                return {"success": False, "error": f"无法获取子智能体: {agent_name}", "agent_name": agent_name}

            # 构建请求数据
            request_data = {
                "input": input_text,
                "query": input_text
            }

            # 创建独立的上下文
            sub_context = {
                "user_id": context.get("user_id", "unknown") if context else "unknown",
                "session_id": context.get("session_id", "unknown") if context else "unknown",
                "parent_agent": "story_five_elements",
                "tool_call": True,
                "original_context": context
            }

            # 调用子智能体并收集结果（带超时）
            results = []

            async def collect_results():
                async for event in sub_agent.process_request(request_data, sub_context):
                    if event.get("event_type") == "llm_chunk":
                        results.append(event.get("data", ""))

            # 使用超时控制
            try:
                await asyncio.wait_for(collect_results(), timeout=120)
            except asyncio.TimeoutError:
                self.logger.error(f"子智能体 {agent_name} 调用超时(120秒)")
                return {
                    "success": False,
                    "error": f"调用超时(120秒): {agent_name}",
                    "agent_name": agent_name
                }

            # 整合结果
            combined_result = "".join(results)

            return {
                "success": True,
                "agent_name": agent_name,
                "result": combined_result
            }

        except ValueError as e:
            self.logger.error(f"调用子智能体参数错误: {e}")
            return {
                "success": False,
                "error": f"参数错误: {str(e)}",
                "agent_name": agent_name
            }
        except Exception as e:
            self.logger.error(f"调用子智能体 {agent_name} 失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent_name": agent_name
            }
    
    async def _get_sub_agent(self, agent_name: str):
        """获取子智能体实例（延迟加载，带锁保护防止竞态条件）"""
        # ========== 第一次检查（无锁，快速路径） ==========
        if agent_name in self.sub_agents:
            return self.sub_agents[agent_name]

        # ========== 加锁保护创建过程 ==========
        async with self._sub_agents_lock:
            # ========== 第二次检查（双重检查锁定模式） ==========
            # 防止多个协程同时通过第一次检查后重复创建
            if agent_name in self.sub_agents:
                return self.sub_agents[agent_name]

            try:
                # 根据智能体类型创建实例
                if agent_name == "story_type_analyzer":
                    from .story_type_analyzer_agent import StoryTypeAnalyzerAgent
                    self.sub_agents[agent_name] = StoryTypeAnalyzerAgent()
                elif agent_name == "story_summary_generator":
                    from .story_summary_generator_agent import StorySummaryGeneratorAgent
                    self.sub_agents[agent_name] = StorySummaryGeneratorAgent()
                elif agent_name == "character_profile_generator":
                    from .character_profile_generator_agent import CharacterProfileGeneratorAgent
                    self.sub_agents[agent_name] = CharacterProfileGeneratorAgent()
                elif agent_name == "character_relationship_analyzer":
                    from .character_relationship_analyzer_agent import CharacterRelationshipAnalyzerAgent
                    self.sub_agents[agent_name] = CharacterRelationshipAnalyzerAgent()
                elif agent_name == "plot_points_analyzer":
                    from .plot_points_analyzer_agent import PlotPointsAnalyzerAgent
                    self.sub_agents[agent_name] = PlotPointsAnalyzerAgent()
                else:
                    self.logger.error(f"未知的子智能体类型: {agent_name}")
                    return None

                self.logger.info(f"子智能体 {agent_name} 加载成功")

            except Exception as e:
                self.logger.error(f"加载子智能体 {agent_name} 失败: {e}")
                return None

        return self.sub_agents.get(agent_name)
    
    async def _generate_mind_map(self, plot_points_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成思维导图"""
        try:
            if not plot_points_result.get("success"):
                return {"success": False, "error": "情节点分析失败"}
            
            plot_points_text = plot_points_result.get("result", "")
            mind_map_result = await self.mind_map_generator.generate_mind_map(plot_points_text)
            
            return mind_map_result
        except Exception as e:
            self.logger.error(f"生成思维导图失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _compile_final_result(self, analysis_results: Dict[str, Any]) -> str:
        """整理最终结果"""
        try:
            final_result = f"""## 题材类型与创意提炼
{analysis_results.get("story_type", {}).get("result", "分析失败")}

## 故事梗概
{analysis_results.get("story_summary", {}).get("result", "生成失败")}

## 人物小传
{analysis_results.get("character_profiles", {}).get("result", "生成失败")}

## 人物关系
{analysis_results.get("character_relationships", {}).get("result", "分析失败")}

## 大情节点
{analysis_results.get("plot_points", {}).get("result", "分析失败")}

## 思维导图
"""
            
            # 添加思维导图信息
            mind_map = analysis_results.get("mind_map", {})
            if mind_map.get("success"):
                mind_map_data = mind_map.get("data_struct", {})
                if mind_map_data.get("pic"):
                    final_result += f"![思维导图]({mind_map_data['pic']})\n\n"
                if mind_map_data.get("jump_link"):
                    final_result += f"[编辑思维导图]({mind_map_data['jump_link']})\n\n"
            else:
                final_result += "思维导图生成失败\n\n"
            
            return final_result
        except Exception as e:
            self.logger.error(f"整理最终结果失败: {e}")
            return f"结果整理失败: {str(e)}"
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "story_five_elements",
            "capabilities": [
                "文本截断和分割",
                "批处理机制",
                "题材类型与创意提炼",
                "故事梗概生成",
                "人物小传生成",
                "人物关系分析",
                "大情节点分析",
                "思维导图生成",
                "Agent as Tool机制",
                "智能体间相互调用"
            ],
            "supported_inputs": [
                "文本输入",
                "文件输入"
            ],
            "available_tools": self.available_tools,
            "agent_as_tool_enabled": True,
            "default_parameters": {
                "chunk_size": self.default_chunk_size,
                "length_size": self.default_length_size,
                "batch_parallel_limit": self.batch_parallel_limit,
                "batch_max_iterations": self.batch_max_iterations
            }
        })
        return base_info

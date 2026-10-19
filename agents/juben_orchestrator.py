"""
Juben Orchestrator - 竖屏短剧策划编排器
 的orchestrator设计，专门用于竖屏短剧策划工作流编排
 

核心功能：
1. 智能任务分解和编排
2. Agent as Tool机制实现
3. 工作流状态管理
4. 错误恢复和重试机制
5. 并发控制和性能优化
6. 🚀 连接池管理（新增）
7. 🧠 性能优化配置（新增）
8. 🛑 停止管理机制（新增）
9. 🎯 多模态处理（新增）
10. 📝 Notes系统（新增）
11. 🔍 智能引用解析（新增）
"""
import asyncio
import json
import time
import re
from typing import AsyncGenerator, Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import uuid

from .base_juben_agent import BaseJubenAgent
from utils.logger import JubenLogger
from utils.error_handler import JubenErrorHandler
from utils.workflow_manager import WorkflowManager
from utils.agent_registry import AgentRegistry
from utils.context_builder import get_juben_context_builder
from utils.reference_resolver import get_juben_reference_resolver
from utils.multimodal_processor import get_multimodal_processor


class JubenOrchestrator(BaseJubenAgent):
    """
    竖屏短剧策划编排器
    
    核心职责：
    1. 🎬 工作流编排：将复杂任务分解为可执行的步骤
    2. 🔧 Agent管理：统一管理和调度所有专业Agent
    3. 📊 状态跟踪：监控工作流执行状态和进度
    4. 🛡️ 错误处理：优雅处理异常和失败重试
    5. 🚀 性能优化：并发控制和资源管理
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化编排器"""
        super().__init__("juben_orchestrator", model_provider)
        
        # 工作流管理
        self.workflow_manager = WorkflowManager()
        self.agent_registry = AgentRegistry()
        
        # 错误处理
        self.error_handler = JubenErrorHandler()
        
        # 🆕 【新增】ReAct模式配置
        self.max_iterations = 4  # 最大迭代次数
        self.thinking_budget = 512  # 思考预算
        self.enable_react_mode = True  # 启用ReAct模式
        
        # 🆕 【新增】Agent as Tool机制
        self.agent_tools = {}  # Agent工具注册表
        self._register_agent_tools()
        
        # 并发控制
        self.max_concurrent_agents = 6  # 限制并发Agent数量
        self.agent_semaphore = asyncio.Semaphore(self.max_concurrent_agents)
        
        # 工作流状态
        self.active_workflows = {}  # 活跃的工作流
        self.workflow_results = {}  # 工作流结果缓存
        
        # 🆕 【新增】ReAct状态跟踪
        self.react_states = {}  # ReAct状态缓存
        self.action_history = {}  # 动作历史记录
        
        # 性能统计
        self.performance_stats = {
            'total_workflows': 0,
            'successful_workflows': 0,
            'failed_workflows': 0,
            'average_execution_time': 0.0,
            'concurrent_peaks': [],
            'react_iterations': 0,  # ReAct迭代次数统计
            'agent_tool_calls': 0   # Agent工具调用次数
        }
        
        self.logger.info("🎬 Juben编排器初始化完成")
        self.logger.info(f"🔧 并发控制: 最大并发Agent={self.max_concurrent_agents}")
        self.logger.info(f"🧠 ReAct模式: {'启用' if self.enable_react_mode else '禁用'}, 最大迭代={self.max_iterations}")
        self.logger.info(f"🛠️ Agent工具: {len(self.agent_tools)}个已注册")
        self.logger.info(f"📊 支持的工作流类型: {list(self.workflow_manager.get_supported_workflows())}")
    
    def _register_agent_tools(self):
        """🆕 注册Agent工具"""
        try:
            # 注册故事分析相关Agent
            self.agent_tools.update({
                'story_evaluation': {
                    'name': '故事大纲评估',
                    'description': '对故事大纲进行专业评估和分析',
                    'agent_class': 'StoryOutlineEvaluationAgent',
                    'category': 'evaluation'
                },
                'ip_evaluation': {
                    'name': 'IP初筛评估',
                    'description': '对IP内容进行初筛评估',
                    'agent_class': 'IPEvaluationAgent',
                    'category': 'evaluation'
                },
                'character_analysis': {
                    'name': '角色分析',
                    'description': '分析角色设定和人物关系',
                    'agent_class': 'CharacterRelationshipAgent',
                    'category': 'analysis'
                },
                'plot_points': {
                    'name': '情节点分析',
                    'description': '分析故事情节点和结构',
                    'agent_class': 'MajorPlotPointsAgent',
                    'category': 'analysis'
                },
                'series_analysis': {
                    'name': '剧集分析',
                    'description': '分析已播剧集和系列信息',
                    'agent_class': 'SeriesAnalysisAgent',
                    'category': 'analysis'
                },
                'story_creation': {
                    'name': '故事创作',
                    'description': '创作新的故事内容',
                    'agent_class': 'ShortDramaCreatorAgent',
                    'category': 'creation'
                },
                'websearch': {
                    'name': '网络搜索',
                    'description': '搜索网络信息和数据',
                    'agent_class': 'WebsearchAgent',
                    'category': 'research'
                },
                'knowledge_search': {
                    'name': '知识库检索',
                    'description': '从知识库中检索相关信息',
                    'agent_class': 'KnowledgeAgent',
                    'category': 'research'
                }
            })
            
            self.logger.info(f"✅ Agent工具注册完成: {len(self.agent_tools)}个工具")
            
        except Exception as e:
            self.logger.error(f"❌ Agent工具注册失败: {e}")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理编排请求
        
        Args:
            request_data: 请求数据
            context: 上下文信息
            
        Yields:
            Dict: 流式响应事件
        """
        user_id = request_data.get("user_id", "unknown")
        session_id = request_data.get("session_id", "unknown")
        instruction = request_data.get("instruction", "")
        
        # 初始化Token累加器
        await self.initialize_token_accumulator(user_id, session_id)
        
        try:
            self.logger.info(f"🎬 开始编排任务: {instruction[:100]}...")
            
            # 发送编排开始事件
            yield await self._emit_event(
                "orchestrator_start",
                f"开始编排竖屏短剧策划任务: {instruction}",
                {"workflow_type": "juben_planning", "status": "starting"}
            )
            
            # 分析任务类型并选择工作流
            workflow_type = await self._analyze_task_type(instruction, context)
            self.logger.info(f"🎯 识别工作流类型: {workflow_type}")
            
            # 创建工作流实例
            workflow_id = str(uuid.uuid4())
            workflow = await self.workflow_manager.create_workflow(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                instruction=instruction,
                user_id=user_id,
                session_id=session_id,
                context=context
            )
            
            # 记录活跃工作流
            self.active_workflows[workflow_id] = workflow
            
            # 执行工作流
            async for event in self._execute_workflow(workflow, user_id, session_id):
                yield event
            
            # 清理工作流
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
            
            # 更新性能统计
            self._update_performance_stats(workflow)
            
            self.logger.info(f"✅ 编排任务完成: {workflow_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 编排任务失败: {e}")
            yield await self._emit_event(
                "orchestrator_error",
                f"编排任务失败: {str(e)}",
                {"error_type": "orchestration_failed", "error": str(e)}
            )
            raise
    
    async def _analyze_task_type(self, instruction: str, context: Optional[Dict[str, Any]]) -> str:
        """
        分析任务类型，选择合适的工作流
        
        Args:
            instruction: 用户指令
            context: 上下文信息
            
        Returns:
            str: 工作流类型
        """
        try:
            # 构建分析提示词
            analysis_prompt = f"""
            请分析以下竖屏短剧策划任务，选择最合适的工作流类型：

            用户指令: {instruction}
            
            可选工作流类型：
            1. story_analysis - 故事分析工作流（分析现有故事、IP评估）
            2. story_creation - 故事创作工作流（从零开始创作故事）
            3. character_development - 角色开发工作流（人物设定、关系分析）
            4. plot_development - 情节开发工作流（情节点设计、结构分析）
            5. drama_evaluation - 短剧评估工作流（剧本评估、市场分析）
            6. series_analysis - 剧集分析工作流（已播剧集分析）
            
            请根据任务内容选择最合适的工作流类型，只返回工作流类型名称。
            """
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": analysis_prompt}
            ]
            
            # 调用LLM分析
            response = await self._call_llm(messages, user_id="system", session_id="analysis")
            
            # 解析响应，提取工作流类型
            workflow_type = self._extract_workflow_type(response)
            
            if workflow_type not in self.workflow_manager.get_supported_workflows():
                self.logger.warning(f"⚠️ 未识别的工作流类型: {workflow_type}，使用默认类型")
                workflow_type = "story_analysis"  # 默认工作流
            
            return workflow_type
            
        except Exception as e:
            self.logger.error(f"❌ 任务类型分析失败: {e}")
            return "story_analysis"  # 默认工作流
    
    def _extract_workflow_type(self, response: str) -> str:
        """从LLM响应中提取工作流类型"""
        response_lower = response.lower().strip()
        
        # 映射关键词到工作流类型
        workflow_mapping = {
            "story_analysis": ["分析", "评估", "ip", "故事分析", "剧本分析"],
            "story_creation": ["创作", "编写", "创作故事", "写故事", "故事创作"],
            "character_development": ["角色", "人物", "角色设定", "人物关系"],
            "plot_development": ["情节", "情节点", "结构", "情节设计"],
            "drama_evaluation": ["评估", "评价", "短剧评估", "剧本评估"],
            "series_analysis": ["剧集", "系列", "已播", "剧集分析"]
        }
        
        for workflow_type, keywords in workflow_mapping.items():
            if any(keyword in response_lower for keyword in keywords):
                return workflow_type
        
        return "story_analysis"  # 默认类型
    
    async def _execute_workflow(
        self, 
        workflow: Dict[str, Any], 
        user_id: str, 
        session_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行工作流
        
        Args:
            workflow: 工作流实例
            user_id: 用户ID
            session_id: 会话ID
            
        Yields:
            Dict: 工作流执行事件
        """
        workflow_id = workflow["workflow_id"]
        workflow_type = workflow["workflow_type"]
        steps = workflow["steps"]
        
        self.logger.info(f"🎬 开始执行工作流: {workflow_id}, 类型: {workflow_type}, 步骤数: {len(steps)}")
        
        # 发送工作流开始事件
        yield await self._emit_event(
            "workflow_start",
            f"开始执行{workflow_type}工作流",
            {"workflow_id": workflow_id, "workflow_type": workflow_type, "total_steps": len(steps)}
        )
        
        # 执行工作流步骤
        step_results = []
        for step_index, step in enumerate(steps):
            try:
                self.logger.info(f"🔄 执行步骤 {step_index + 1}/{len(steps)}: {step['name']}")
                
                # 发送步骤开始事件
                yield await self._emit_event(
                    "step_start",
                    f"开始执行步骤: {step['name']}",
                    {"step_index": step_index, "step_name": step['name'], "agent_type": step['agent_type']}
                )
                
                # 执行步骤
                step_result = await self._execute_step(step, user_id, session_id, workflow_id)
                step_results.append(step_result)
                
                # 发送步骤完成事件
                yield await self._emit_event(
                    "step_complete",
                    f"步骤完成: {step['name']}",
                    {"step_index": step_index, "step_name": step['name'], "result": step_result}
                )
                
                # 检查是否需要停止工作流
                if step_result.get("should_stop", False):
                    self.logger.info(f"🛑 工作流在步骤 {step_index + 1} 处停止")
                    break
                
            except Exception as e:
                self.logger.error(f"❌ 步骤执行失败: {step['name']}, 错误: {e}")
                
                # 发送步骤错误事件
                yield await self._emit_event(
                    "step_error",
                    f"步骤执行失败: {step['name']}",
                    {"step_index": step_index, "step_name": step['name'], "error": str(e)}
                )
                
                # 根据错误处理策略决定是否继续
                if not step.get("continue_on_error", True):
                    self.logger.error(f"🛑 工作流因步骤失败而停止: {step['name']}")
                    break
        
            # 整合结果
            final_result = await self._integrate_results(step_results, workflow)
            
            # 保存工作流结果到文件系统
            save_result = await self._save_workflow_output(final_result, user_id, session_id, workflow_type)
            
            # 发送工作流完成事件
            yield await self._emit_event(
                "workflow_complete",
                f"工作流执行完成: {workflow_type}",
                {
                    "workflow_id": workflow_id, 
                    "workflow_type": workflow_type, 
                    "result": final_result,
                    "save_result": save_result
                }
            )
            
            # 保存工作流结果
            self.workflow_results[workflow_id] = final_result
        
        self.logger.info(f"✅ 工作流执行完成: {workflow_id}")
    
    async def _save_workflow_output(
        self, 
        workflow_result: Dict[str, Any], 
        user_id: str, 
        session_id: str, 
        workflow_type: str
    ) -> Dict[str, Any]:
        """保存工作流输出到文件系统"""
        try:
            # 确定输出标签
            output_tag = self._determine_workflow_output_tag(workflow_type)
            
            # 保存工作流结果
            save_result = await self.auto_save_output(
                output_content=workflow_result,
                user_id=user_id,
                session_id=session_id,
                file_type="json",
                metadata={
                    "workflow_type": workflow_type,
                    "output_tag": output_tag,
                    "execution_timestamp": datetime.now().isoformat(),
                    "orchestrator_version": "1.0"
                }
            )
            
            if save_result.get("success"):
                self.logger.info(f"💾 工作流输出保存成功: {workflow_type} -> {output_tag}")
            else:
                self.logger.error(f"❌ 工作流输出保存失败: {save_result.get('error')}")
            
            return save_result
            
        except Exception as e:
            self.logger.error(f"❌ 保存工作流输出失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _determine_workflow_output_tag(self, workflow_type: str) -> str:
        """根据工作流类型确定输出标签"""
        workflow_tag_mapping = {
            "story_analysis": "story_analysis",
            "story_creation": "drama_creation", 
            "character_development": "character_development",
            "plot_development": "plot_development",
            "drama_evaluation": "drama_evaluation",
            "series_analysis": "series_analysis"
        }
        
        return workflow_tag_mapping.get(workflow_type, "drama_planning")
    
    async def _execute_step(
        self, 
        step: Dict[str, Any], 
        user_id: str, 
        session_id: str, 
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        执行单个工作流步骤
        
        Args:
            step: 步骤配置
            user_id: 用户ID
            session_id: 会话ID
            workflow_id: 工作流ID
            
        Returns:
            Dict: 步骤执行结果
        """
        agent_type = step["agent_type"]
        step_name = step["name"]
        step_config = step.get("config", {})
        
        try:
            # 获取Agent实例
            agent = await self.agent_registry.get_agent(agent_type)
            if not agent:
                raise ValueError(f"未找到Agent: {agent_type}")
            
            # 构建步骤请求
            step_request = {
                "instruction": step.get("instruction", ""),
                "user_id": user_id,
                "session_id": session_id,
                "workflow_id": workflow_id,
                "step_name": step_name,
                "config": step_config
            }
            
            # 使用信号量控制并发
            async with self.agent_semaphore:
                self.logger.info(f"🤖 调用Agent: {agent_type}")
                
                # 执行Agent
                start_time = time.time()
                result = await agent.process_request(step_request)
                execution_time = time.time() - start_time
                
                self.logger.info(f"✅ Agent执行完成: {agent_type}, 耗时: {execution_time:.2f}s")
                
                return {
                    "step_name": step_name,
                    "agent_type": agent_type,
                    "execution_time": execution_time,
                    "result": result,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"❌ Agent执行失败: {agent_type}, 错误: {e}")
            return {
                "step_name": step_name,
                "agent_type": agent_type,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _integrate_results(
        self, 
        step_results: List[Dict[str, Any]], 
        workflow: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        整合工作流结果
        
        Args:
            step_results: 步骤结果列表
            workflow: 工作流配置
            
        Returns:
            Dict: 整合后的结果
        """
        try:
            # 构建整合提示词
            integration_prompt = f"""
            请整合以下竖屏短剧策划工作流的执行结果：

            工作流类型: {workflow['workflow_type']}
            原始指令: {workflow['instruction']}
            
            步骤执行结果:
            """
            
            for i, result in enumerate(step_results):
                integration_prompt += f"\n步骤 {i+1}: {result['step_name']}\n"
                integration_prompt += f"执行状态: {'成功' if result['success'] else '失败'}\n"
                if result['success']:
                    integration_prompt += f"结果: {result['result']}\n"
                else:
                    integration_prompt += f"错误: {result['error']}\n"
            
            integration_prompt += """
            
            请基于以上结果，生成一个完整的竖屏短剧策划方案，包括：
            1. 故事概述
            2. 主要角色设定
            3. 核心情节结构
            4. 市场定位分析
            5. 实施建议
            
            请以结构化的JSON格式输出结果。
            """
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": integration_prompt}
            ]
            
            # 调用LLM整合结果
            response = await self._call_llm(messages, user_id="system", session_id="integration")
            
            # 尝试解析JSON响应
            try:
                integrated_result = json.loads(response)
            except json.JSONDecodeError:
                # 如果不是JSON格式，创建结构化结果
                integrated_result = {
                    "summary": response,
                    "workflow_type": workflow['workflow_type'],
                    "execution_summary": {
                        "total_steps": len(step_results),
                        "successful_steps": len([r for r in step_results if r['success']]),
                        "failed_steps": len([r for r in step_results if not r['success']])
                    },
                    "step_results": step_results
                }
            
            return integrated_result
            
        except Exception as e:
            self.logger.error(f"❌ 结果整合失败: {e}")
            return {
                "error": f"结果整合失败: {str(e)}",
                "workflow_type": workflow['workflow_type'],
                "step_results": step_results
            }
    
    def _update_performance_stats(self, workflow: Dict[str, Any]):
        """更新性能统计"""
        self.performance_stats['total_workflows'] += 1
        
        if workflow.get('success', True):
            self.performance_stats['successful_workflows'] += 1
        else:
            self.performance_stats['failed_workflows'] += 1
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        if workflow_id in self.active_workflows:
            return {
                "workflow_id": workflow_id,
                "status": "running",
                "workflow": self.active_workflows[workflow_id]
            }
        elif workflow_id in self.workflow_results:
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": self.workflow_results[workflow_id]
            }
        else:
            return None
    
    async def stop_workflow(self, workflow_id: str) -> bool:
        """停止工作流"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            # 这里可以实现工作流停止逻辑
            del self.active_workflows[workflow_id]
            return True
        return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_stats.copy()
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "orchestrator_type": "juben_planning",
            "max_concurrent_agents": self.max_concurrent_agents,
            "supported_workflows": self.workflow_manager.get_supported_workflows(),
            "performance_stats": self.performance_stats
        })
        return base_info
    
    # ==================== 增强功能方法（新增） ====================
    
    async def build_enhanced_context(
        self,
        user_id: str,
        session_id: str,
        instruction: str,
        include_notes: bool = True,
        include_files: bool = True,
        include_chat_history: bool = True
    ) -> str:
        """构建增强的上下文"""
        try:
            # 使用上下文构建器
            context_builder = get_juben_context_builder()
            
            # 构建基础上下文
            base_context = await context_builder.build_action_context(
                user_id=user_id,
                session_id=session_id,
                instruction=instruction,
                action="orchestration"
            )
            
            # 构建完整上下文
            full_context = await context_builder.build_full_context(
                user_id=user_id,
                session_id=session_id,
                base_prompt=base_context,
                current_query=instruction,
                include_notes=include_notes,
                include_files=include_files,
                include_chat_history=include_chat_history
            )
            
            return full_context
            
        except Exception as e:
            self.logger.error(f"构建增强上下文失败: {e}")
            return f"## 当前任务\n指令: {instruction}\n操作类型: orchestration"
    
    async def resolve_references_in_text(self, text: str, user_id: str, session_id: str) -> str:
        """解析文本中的引用"""
        try:
            reference_resolver = get_juben_reference_resolver()
            return await reference_resolver.resolve_references(text, user_id, session_id)
        except Exception as e:
            self.logger.error(f"解析引用失败: {e}")
            return text
    
    async def process_multimodal_content(
        self,
        user_id: str,
        session_id: str,
        file_refs: List[str]
    ) -> Dict[str, Any]:
        """处理多模态内容"""
        try:
            multimodal_processor = get_multimodal_processor()
            return await multimodal_processor.get_file_content_for_agent(
                user_id, session_id, file_refs
            )
        except Exception as e:
            self.logger.error(f"处理多模态内容失败: {e}")
            return {"files": [], "content": "", "error": str(e)}
    
    async def create_workflow_note(
        self,
        user_id: str,
        session_id: str,
        workflow_type: str,
        workflow_data: Dict[str, Any]
    ) -> bool:
        """创建工作流Note"""
        try:
            note_id = await self.get_next_action_id(user_id, session_id, "workflow")
            note_name = f"workflow{note_id}"
            
            # 构建Note内容
            note_content = f"工作流类型: {workflow_type}\n"
            note_content += f"工作流数据: {json.dumps(workflow_data, ensure_ascii=False, indent=2)}"
            
            # 创建Note
            success = await self.create_note(
                user_id=user_id,
                session_id=session_id,
                action="workflow",
                name=note_name,
                context=note_content,
                title=f"工作流: {workflow_type}",
                select=1  # 自动选中
            )
            
            if success:
                self.logger.info(f"📝 创建工作流Note成功: {note_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"创建工作流Note失败: {e}")
            return False
    
    async def get_workflow_notes(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """获取工作流Notes"""
        try:
            return await self.get_notes_by_action(user_id, session_id, "workflow")
        except Exception as e:
            self.logger.error(f"获取工作流Notes失败: {e}")
            return []
    
    async def update_agent_call_stats(self, agent_name: str, success: bool, duration: float):
        """更新Agent调用统计"""
        try:
            if agent_name not in self.agent_call_stats:
                self.agent_call_stats[agent_name] = {
                    'total_calls': 0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'total_duration': 0.0,
                    'average_duration': 0.0
                }
            
            stats = self.agent_call_stats[agent_name]
            stats['total_calls'] += 1
            stats['total_duration'] += duration
            stats['average_duration'] = stats['total_duration'] / stats['total_calls']
            
            if success:
                stats['successful_calls'] += 1
            else:
                stats['failed_calls'] += 1
            
        except Exception as e:
            self.logger.error(f"更新Agent调用统计失败: {e}")
    
    async def get_agent_call_stats(self) -> Dict[str, Any]:
        """获取Agent调用统计"""
        try:
            return {
                'agent_stats': self.agent_call_stats.copy(),
                'total_agents': len(self.agent_call_stats),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"获取Agent调用统计失败: {e}")
            return {'error': str(e)}
    
    async def optimize_workflow_performance(self, workflow_id: str) -> Dict[str, Any]:
        """优化工作流性能"""
        try:
            if workflow_id not in self.active_workflows:
                return {'error': '工作流不存在'}
            
            workflow = self.active_workflows[workflow_id]
            optimization_suggestions = []
            
            # 分析工作流性能
            if workflow.get('duration', 0) > 300:  # 超过5分钟
                optimization_suggestions.append("考虑并行执行某些步骤")
            
            if workflow.get('agent_calls', 0) > 10:
                optimization_suggestions.append("考虑合并某些Agent调用")
            
            if workflow.get('error_count', 0) > 0:
                optimization_suggestions.append("检查错误处理机制")
            
            return {
                'workflow_id': workflow_id,
                'optimization_suggestions': optimization_suggestions,
                'current_performance': {
                    'duration': workflow.get('duration', 0),
                    'agent_calls': workflow.get('agent_calls', 0),
                    'error_count': workflow.get('error_count', 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"优化工作流性能失败: {e}")
            return {'error': str(e)}
    
    async def get_enhanced_performance_info(self) -> Dict[str, Any]:
        """获取增强的性能信息"""
        try:
            base_performance = self.get_performance_info()
            agent_stats = await self.get_agent_call_stats()
            
            return {
                **base_performance,
                'agent_call_stats': agent_stats,
                'active_workflows': len(self.active_workflows),
                'workflow_history': len(self.workflow_history),
                'enhanced_features': {
                    'context_builder': True,
                    'reference_resolver': True,
                    'multimodal_processor': True,
                    'notes_system': True,
                    'stop_management': True
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取增强性能信息失败: {e}")
            return {'error': str(e)}
    
    # ==================== 新增ReAct模式核心功能 ====================
    
    async def _prewarm_connection_pools(self, user_id: str, session_id: str):
        """🚀 【连接池预热】在并发执行前预热连接池"""
        try:
            # 获取连接池管理器并直接调用预热方法
            pool_manager = await self.get_connection_pool_manager()
            
            if pool_manager and hasattr(pool_manager, 'prewarm_pools'):
                # 使用连接池管理器内置的预热功能
                prewarming_result = await pool_manager.prewarm_pools(['high_priority', 'normal'])
                
                if 'error' in prewarming_result:
                    self.logger.error(f"❌ 连接池预热失败: {prewarming_result['error']}")
                else:
                    success_count = prewarming_result.get('success_count', 0)
                    total_count = prewarming_result.get('total_count', 0)
                    duration = prewarming_result.get('duration', 0)
                    self.logger.info(f"🔥 连接池预热完成: {success_count}/{total_count} 成功, 耗时: {duration:.2f}s")
            
        except Exception as e:
            self.logger.error(f"❌ 连接池预热失败: {e}")
    
    async def _monitor_concurrent_execution(self, active_agents: int):
        """🚀 【监控】并发执行监控"""
        self._concurrent_stats['concurrent_peaks'].append(active_agents)
        
        # 如果接近连接池限制，记录警告
        if active_agents >= self.max_concurrent_agents * 0.8:
            self.logger.warning(f"⚠️ 并发agents接近限制: {active_agents}/{self.max_concurrent_agents}")
        
        # 获取连接池统计
        try:
            stats = await self.get_connection_stats()
            if stats:
                self.logger.debug(f"📊 连接池使用统计: Redis请求={stats.get('redis_requests', 0)}, "
                                f"失败={stats.get('redis_failures', 0)}")
        except Exception:
            pass  # 忽略统计获取失败
    
    async def get_concurrent_stats(self) -> dict:
        """🚀 【新增】获取并发执行统计信息"""
        stats = self._concurrent_stats.copy()
        
        # 计算统计指标
        if stats['concurrent_peaks']:
            stats['max_concurrent'] = max(stats['concurrent_peaks'])
            stats['avg_concurrent'] = sum(stats['concurrent_peaks']) / len(stats['concurrent_peaks'])
        else:
            stats['max_concurrent'] = 0
            stats['avg_concurrent'] = 0
        
        # 添加连接池健康状态
        try:
            health_status = await self.health_check_connections()
            stats['connection_health'] = health_status
        except Exception:
            stats['connection_health'] = {'overall_status': 'unknown'}
        
        return stats
    
    async def get_connection_stats(self) -> Optional[Dict[str, Any]]:
        """获取连接池统计信息"""
        try:
            pool_manager = await self.get_connection_pool_manager()
            if pool_manager and hasattr(pool_manager, 'get_stats'):
                return await pool_manager.get_stats()
        except Exception as e:
            self.logger.error(f"❌ 获取连接池统计失败: {e}")
        return None
    
    async def health_check_connections(self) -> Dict[str, Any]:
        """健康检查连接池"""
        try:
            pool_manager = await self.get_connection_pool_manager()
            if pool_manager and hasattr(pool_manager, 'health_check'):
                return await pool_manager.health_check()
        except Exception as e:
            self.logger.error(f"❌ 连接池健康检查失败: {e}")
        return {'overall_status': 'error', 'error': 'Health check failed'}
    
    def set_mergeable_actions(self, action_types: set):
        """设置需要合并结果的action类型"""
        self.mergeable_actions = action_types
        self.logger.info(f"🔧 更新合并配置: {action_types}")
    
    def add_mergeable_action(self, action_type: str):
        """添加需要合并的action类型"""
        self.mergeable_actions.add(action_type)
        self.logger.info(f"🔧 添加合并类型: {action_type}, 当前配置: {self.mergeable_actions}")
    
    def remove_mergeable_action(self, action_type: str):
        """移除不需要合并的action类型"""
        self.mergeable_actions.discard(action_type)
        self.logger.info(f"🔧 移除合并类型: {action_type}, 当前配置: {self.mergeable_actions}")
    
    # ==================== 新增Agent调用管理 ====================
    
    async def call_agent_as_tool(
        self,
        agent_name: str,
        request_data: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """🛠️ 将Agent作为工具调用"""
        try:
            if agent_name not in self.agent_tools:
                raise ValueError(f"未注册的Agent工具: {agent_name}")
            
            agent_info = self.agent_tools[agent_name]
            agent_class_name = agent_info['agent_class']
            
            # 获取Agent实例
            agent = await self.agent_registry.get_agent(agent_class_name)
            if not agent:
                raise ValueError(f"未找到Agent实例: {agent_class_name}")
            
            # 构建请求数据
            tool_request = {
                **request_data,
                "user_id": user_id,
                "session_id": session_id,
                "called_as_tool": True,
                "tool_name": agent_name
            }
            
            # 执行Agent调用
            start_time = time.time()
            result = await agent.process_request(tool_request)
            execution_time = time.time() - start_time
            
            # 更新统计
            self.performance_stats['agent_tool_calls'] += 1
            await self.update_agent_call_stats(agent_name, True, execution_time)
            
            self.logger.info(f"🛠️ Agent工具调用成功: {agent_name}, 耗时: {execution_time:.2f}s")
            
            return {
                "agent_name": agent_name,
                "result": result,
                "execution_time": execution_time,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Agent工具调用失败: {agent_name}, 错误: {e}")
            await self.update_agent_call_stats(agent_name, False, 0)
            
            return {
                "agent_name": agent_name,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
    
    async def batch_call_agents(
        self,
        agent_calls: List[Dict[str, Any]],
        user_id: str,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """🔄 批量调用多个Agent"""
        try:
            self.logger.info(f"🔄 开始批量调用{len(agent_calls)}个Agent")
            
            # 使用信号量控制并发
            async with self.agent_semaphore:
                # 创建并发任务
                tasks = []
                for call_config in agent_calls:
                    agent_name = call_config.get("agent_name")
                    request_data = call_config.get("request_data", {})
                    
                    if agent_name:
                        task = self.call_agent_as_tool(agent_name, request_data, user_id, session_id)
                        tasks.append(task)
                
                # 并发执行所有任务
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        processed_results.append({
                            "agent_name": agent_calls[i].get("agent_name", "unknown"),
                            "error": str(result),
                            "success": False,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        processed_results.append(result)
                
                self.logger.info(f"✅ 批量Agent调用完成: {len(processed_results)}个结果")
                return processed_results
                
        except Exception as e:
            self.logger.error(f"❌ 批量Agent调用失败: {e}")
            return [{"error": str(e), "success": False}]
    
    # ==================== 新增工作流管理功能 ====================
    
    async def create_dynamic_workflow(
        self,
        workflow_config: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> str:
        """🔄 创建动态工作流"""
        try:
            workflow_id = str(uuid.uuid4())
            
            # 验证工作流配置
            validated_config = await self._validate_workflow_config(workflow_config)
            
            # 创建工作流实例
            workflow = {
                "workflow_id": workflow_id,
                "workflow_type": validated_config.get("type", "dynamic"),
                "name": validated_config.get("name", f"动态工作流_{workflow_id[:8]}"),
                "description": validated_config.get("description", ""),
                "steps": validated_config.get("steps", []),
                "config": validated_config.get("config", {}),
                "created_at": datetime.now().isoformat(),
                "created_by": user_id,
                "session_id": session_id,
                "status": "created"
            }
            
            # 保存工作流
            await self.workflow_manager.save_workflow(workflow)
            
            self.logger.info(f"✅ 动态工作流创建成功: {workflow_id}")
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"❌ 创建动态工作流失败: {e}")
            raise
    
    async def _validate_workflow_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证工作流配置"""
        try:
            # 基本验证
            required_fields = ["type", "steps"]
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"工作流配置缺少必需字段: {field}")
            
            # 验证步骤配置
            steps = config.get("steps", [])
            for i, step in enumerate(steps):
                if "agent_type" not in step:
                    raise ValueError(f"步骤{i+1}缺少agent_type字段")
                
                if step["agent_type"] not in self.agent_tools:
                    raise ValueError(f"步骤{i+1}使用了未注册的Agent: {step['agent_type']}")
            
            return config
            
        except Exception as e:
            self.logger.error(f"❌ 工作流配置验证失败: {e}")
            raise
    
    async def execute_dynamic_workflow(
        self,
        workflow_id: str,
        user_id: str,
        session_id: str,
        input_data: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """🔄 执行动态工作流"""
        try:
            # 获取工作流配置
            workflow = await self.workflow_manager.get_workflow(workflow_id)
            if not workflow:
                raise ValueError(f"未找到工作流: {workflow_id}")
            
            self.logger.info(f"🔄 开始执行动态工作流: {workflow_id}")
            
            # 发送工作流开始事件
            yield await self._emit_event(
                "dynamic_workflow_start",
                f"开始执行动态工作流: {workflow['name']}",
                {"workflow_id": workflow_id, "workflow_name": workflow['name']}
            )
            
            # 执行工作流步骤
            step_results = []
            for step_index, step in enumerate(workflow['steps']):
                try:
                    # 发送步骤开始事件
                    yield await self._emit_event(
                        "dynamic_step_start",
                        f"开始执行步骤: {step.get('name', f'步骤{step_index+1}')}",
                        {"step_index": step_index, "step_name": step.get('name')}
                    )
                    
                    # 执行步骤
                    step_result = await self._execute_dynamic_step(
                        step, user_id, session_id, workflow_id, input_data
                    )
                    step_results.append(step_result)
                    
                    # 发送步骤完成事件
                    yield await self._emit_event(
                        "dynamic_step_complete",
                        f"步骤完成: {step.get('name', f'步骤{step_index+1}')}",
                        {"step_index": step_index, "result": step_result}
                    )
                    
                except Exception as e:
                    self.logger.error(f"❌ 动态步骤执行失败: {step.get('name')}, 错误: {e}")
                    
                    # 发送步骤错误事件
                    yield await self._emit_event(
                        "dynamic_step_error",
                        f"步骤执行失败: {step.get('name')}",
                        {"step_index": step_index, "error": str(e)}
                    )
                    
                    # 根据配置决定是否继续
                    if not step.get("continue_on_error", True):
                        break
            
            # 整合结果
            final_result = await self._integrate_dynamic_results(step_results, workflow)
            
            # 发送工作流完成事件
            yield await self._emit_event(
                "dynamic_workflow_complete",
                f"动态工作流执行完成: {workflow['name']}",
                {"workflow_id": workflow_id, "result": final_result}
            )
            
            self.logger.info(f"✅ 动态工作流执行完成: {workflow_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 动态工作流执行失败: {e}")
            yield await self._emit_event(
                "dynamic_workflow_error",
                f"动态工作流执行失败: {str(e)}",
                {"workflow_id": workflow_id, "error": str(e)}
            )
            raise
    
    async def _execute_dynamic_step(
        self,
        step: Dict[str, Any],
        user_id: str,
        session_id: str,
        workflow_id: str,
        input_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行动态工作流步骤"""
        try:
            agent_type = step["agent_type"]
            step_name = step.get("name", f"步骤_{agent_type}")
            step_config = step.get("config", {})
            
            # 构建步骤请求
            step_request = {
                "instruction": step.get("instruction", ""),
                "user_id": user_id,
                "session_id": session_id,
                "workflow_id": workflow_id,
                "step_name": step_name,
                "config": step_config,
                "input_data": input_data or {}
            }
            
            # 调用Agent
            result = await self.call_agent_as_tool(
                agent_type, step_request, user_id, session_id
            )
            
            return {
                "step_name": step_name,
                "agent_type": agent_type,
                "result": result,
                "success": result.get("success", False),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 动态步骤执行失败: {e}")
            return {
                "step_name": step.get("name", "unknown"),
                "agent_type": step.get("agent_type", "unknown"),
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _integrate_dynamic_results(
        self,
        step_results: List[Dict[str, Any]],
        workflow: Dict[str, Any]
    ) -> Dict[str, Any]:
        """整合动态工作流结果"""
        try:
            # 构建整合提示词
            integration_prompt = f"""
            请整合以下动态工作流的执行结果：
            
            工作流名称: {workflow.get('name', '未知')}
            工作流描述: {workflow.get('description', '')}
            
            步骤执行结果:
            """
            
            for i, result in enumerate(step_results):
                integration_prompt += f"\n步骤 {i+1}: {result['step_name']}\n"
                integration_prompt += f"执行状态: {'成功' if result['success'] else '失败'}\n"
                if result['success']:
                    integration_prompt += f"结果: {result['result']}\n"
                else:
                    integration_prompt += f"错误: {result['error']}\n"
            
            integration_prompt += """
            
            请基于以上结果，生成一个完整的总结报告，包括：
            1. 执行概览
            2. 关键结果
            3. 问题和建议
            4. 后续行动建议
            
            请以结构化的JSON格式输出结果。
            """
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": integration_prompt}
            ]
            
            # 调用LLM整合结果
            response = await self._call_llm(messages, user_id="system", session_id="dynamic_integration")
            
            # 尝试解析JSON响应
            try:
                integrated_result = json.loads(response)
            except json.JSONDecodeError:
                # 如果不是JSON格式，创建结构化结果
                integrated_result = {
                    "summary": response,
                    "workflow_name": workflow.get('name', ''),
                    "execution_summary": {
                        "total_steps": len(step_results),
                        "successful_steps": len([r for r in step_results if r['success']]),
                        "failed_steps": len([r for r in step_results if not r['success']])
                    },
                    "step_results": step_results
                }
            
            return integrated_result
            
        except Exception as e:
            self.logger.error(f"❌ 动态结果整合失败: {e}")
            return {
                "error": f"结果整合失败: {str(e)}",
                "workflow_name": workflow.get('name', ''),
                "step_results": step_results
            }
    
    # ==================== 新增智能路由功能 ====================
    
    async def intelligent_agent_routing(
        self,
        request_data: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """🧠 智能Agent路由"""
        try:
            instruction = request_data.get("instruction", "")
            context = request_data.get("context", {})
            
            # 分析请求特征
            request_features = await self._analyze_request_features(instruction, context)
            
            # 选择最佳Agent
            selected_agent = await self._select_best_agent(request_features)
            
            # 构建路由建议
            routing_suggestion = {
                "selected_agent": selected_agent,
                "confidence": request_features.get("confidence", 0.5),
                "alternative_agents": request_features.get("alternatives", []),
                "reasoning": request_features.get("reasoning", ""),
                "estimated_duration": request_features.get("estimated_duration", 0)
            }
            
            self.logger.info(f"🧠 智能路由完成: {selected_agent}, 置信度: {routing_suggestion['confidence']}")
            
            return routing_suggestion
            
        except Exception as e:
            self.logger.error(f"❌ 智能路由失败: {e}")
            return {
                "selected_agent": "story_evaluation",
                "confidence": 0.1,
                "error": str(e)
            }
    
    async def _analyze_request_features(
        self,
        instruction: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析请求特征"""
        try:
            # 构建分析提示词
            analysis_prompt = f"""
            请分析以下请求的特征，为智能路由提供决策依据：
            
            用户指令: {instruction}
            上下文信息: {json.dumps(context, ensure_ascii=False)}
            
            可选Agent工具:
            {json.dumps(list(self.agent_tools.keys()), ensure_ascii=False)}
            
            请分析并返回以下信息：
            1. 最适合的Agent工具
            2. 备选Agent工具（按优先级排序）
            3. 选择置信度（0-1）
            4. 选择理由
            5. 预估执行时间（秒）
            
            请以JSON格式返回分析结果。
            """
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": analysis_prompt}
            ]
            
            # 调用LLM分析
            response = await self._call_llm(messages, user_id="system", session_id="routing_analysis")
            
            # 解析响应
            try:
                features = json.loads(response)
                return features
            except json.JSONDecodeError:
                # 回退到基于关键词的简单分析
                return self._fallback_routing_analysis(instruction)
                
        except Exception as e:
            self.logger.error(f"❌ 请求特征分析失败: {e}")
            return self._fallback_routing_analysis(instruction)
    
    def _fallback_routing_analysis(self, instruction: str) -> Dict[str, Any]:
        """回退路由分析"""
        instruction_lower = instruction.lower()
        
        # 基于关键词的简单路由
        routing_keywords = {
            'story_evaluation': ['分析', '评估', '故事', '剧本'],
            'ip_evaluation': ['ip', '初筛', '筛选'],
            'character_analysis': ['角色', '人物', '关系'],
            'plot_points': ['情节', '情节点', '结构'],
            'series_analysis': ['剧集', '系列', '已播'],
            'story_creation': ['创作', '编写', '创作故事'],
            'websearch': ['搜索', '查找', '信息'],
            'knowledge_search': ['知识', '检索', '查询']
        }
        
        for agent_name, keywords in routing_keywords.items():
            if any(keyword in instruction_lower for keyword in keywords):
                return {
                    "selected_agent": agent_name,
                    "alternatives": [],
                    "confidence": 0.7,
                    "reasoning": f"基于关键词匹配: {keywords}",
                    "estimated_duration": 30
                }
        
        # 默认路由
        return {
            "selected_agent": "story_evaluation",
            "alternatives": ["ip_evaluation", "character_analysis"],
            "confidence": 0.3,
            "reasoning": "默认路由到故事评估",
            "estimated_duration": 45
        }
    
    async def _select_best_agent(self, features: Dict[str, Any]) -> str:
        """选择最佳Agent"""
        try:
            selected_agent = features.get("selected_agent", "story_evaluation")
            
            # 验证Agent是否存在
            if selected_agent not in self.agent_tools:
                self.logger.warning(f"⚠️ 选择的Agent不存在: {selected_agent}，使用默认Agent")
                selected_agent = "story_evaluation"
            
            return selected_agent
            
        except Exception as e:
            self.logger.error(f"❌ 选择最佳Agent失败: {e}")
            return "story_evaluation"
    
    # ==================== 新增性能优化功能 ====================
    
    async def optimize_agent_performance(
        self,
        agent_name: str,
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """🚀 优化Agent性能"""
        try:
            # 分析性能数据
            optimization_suggestions = []
            
            avg_duration = performance_data.get("average_duration", 0)
            success_rate = performance_data.get("success_rate", 0)
            error_rate = performance_data.get("error_rate", 0)
            
            # 基于性能指标生成优化建议
            if avg_duration > 60:
                optimization_suggestions.append("考虑优化Agent处理逻辑，减少执行时间")
            
            if success_rate < 0.8:
                optimization_suggestions.append("检查Agent错误处理机制，提高成功率")
            
            if error_rate > 0.1:
                optimization_suggestions.append("分析错误模式，改进异常处理")
            
            # 生成优化配置
            optimization_config = {
                "agent_name": agent_name,
                "current_performance": performance_data,
                "optimization_suggestions": optimization_suggestions,
                "recommended_config": self._generate_optimization_config(performance_data)
            }
            
            self.logger.info(f"🚀 Agent性能优化分析完成: {agent_name}")
            
            return optimization_config
            
        except Exception as e:
            self.logger.error(f"❌ Agent性能优化失败: {e}")
            return {"error": str(e)}
    
    def _generate_optimization_config(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成优化配置"""
        config = {}
        
        avg_duration = performance_data.get("average_duration", 0)
        success_rate = performance_data.get("success_rate", 0)
        
        # 基于性能调整配置
        if avg_duration > 60:
            config["timeout"] = max(120, avg_duration * 1.5)
            config["enable_caching"] = True
        
        if success_rate < 0.8:
            config["retry_count"] = 3
            config["retry_delay"] = 2
        
        return config
    
    async def get_system_health_status(self) -> Dict[str, Any]:
        """🏥 获取系统健康状态"""
        try:
            health_status = {
                "overall_status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {}
            }
            
            # 检查各个组件状态
            components = {
                "agent_registry": await self._check_agent_registry_health(),
                "workflow_manager": await self._check_workflow_manager_health(),
                "connection_pools": await self._check_connection_pools_health(),
                "notes_system": await self._check_notes_system_health(),
                "performance": await self._check_performance_health()
            }
            
            health_status["components"] = components
            
            # 确定整体状态
            unhealthy_components = [
                name for name, status in components.items() 
                if status.get("status") != "healthy"
            ]
            
            if unhealthy_components:
                health_status["overall_status"] = "degraded"
                health_status["unhealthy_components"] = unhealthy_components
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"❌ 获取系统健康状态失败: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _check_agent_registry_health(self) -> Dict[str, Any]:
        """检查Agent注册表健康状态"""
        try:
            registered_agents = len(self.agent_tools)
            return {
                "status": "healthy",
                "registered_agents": registered_agents,
                "details": f"已注册{registered_agents}个Agent工具"
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_workflow_manager_health(self) -> Dict[str, Any]:
        """检查工作流管理器健康状态"""
        try:
            active_workflows = len(self.active_workflows)
            return {
                "status": "healthy",
                "active_workflows": active_workflows,
                "details": f"当前有{active_workflows}个活跃工作流"
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_connection_pools_health(self) -> Dict[str, Any]:
        """检查连接池健康状态"""
        try:
            pool_manager = await self.get_connection_pool_manager()
            if pool_manager and hasattr(pool_manager, 'health_check'):
                health_status = await pool_manager.health_check()
                return health_status
            else:
                return {"status": "unknown", "details": "连接池管理器不可用"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_notes_system_health(self) -> Dict[str, Any]:
        """检查Notes系统健康状态"""
        try:
            if hasattr(self, 'notes_manager') and self.notes_manager:
                return {"status": "healthy", "details": "Notes系统可用"}
            else:
                return {"status": "unhealthy", "details": "Notes系统未初始化"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_performance_health(self) -> Dict[str, Any]:
        """检查性能健康状态"""
        try:
            stats = self.get_performance_stats()
            success_rate = stats.get('successful_workflows', 0) / max(stats.get('total_workflows', 1), 1)
            
            if success_rate > 0.9:
                status = "healthy"
            elif success_rate > 0.7:
                status = "degraded"
            else:
                status = "unhealthy"
            
            return {
                "status": status,
                "success_rate": success_rate,
                "total_workflows": stats.get('total_workflows', 0),
                "details": f"工作流成功率: {success_rate:.2%}"
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

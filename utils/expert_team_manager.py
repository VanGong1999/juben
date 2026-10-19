"""
专家团队管理器 - AI组建自己的专家团队
 架构的Sub-agent专家团队管理系统
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid
from enum import Enum

try:
    from ..config.settings import JubenSettings
    from ..utils.logger import JubenLogger
    from ..utils.storage_manager import JubenStorageManager
    from ..utils.llm_client import JubenLLMClient
    from ..utils.performance_monitor import PerformanceMonitor, get_performance_monitor
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.storage_manager import JubenStorageManager
    from utils.llm_client import JubenLLMClient
    from utils.performance_monitor import PerformanceMonitor, get_performance_monitor


class ExpertType(Enum):
    """专家类型"""
    ANALYST = "analyst"  # 分析师
    CREATOR = "creator"  # 创作者
    EVALUATOR = "evaluator"  # 评估师
    RESEARCHER = "researcher"  # 研究员
    COORDINATOR = "coordinator"  # 协调员
    SPECIALIST = "specialist"  # 专业师


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExpertProfile:
    """专家档案"""
    id: str
    name: str
    expert_type: ExpertType
    specialization: List[str]
    capabilities: List[str]
    experience_level: int  # 1-10
    success_rate: float  # 0-1
    response_time: float  # 平均响应时间（秒）
    availability: bool
    current_workload: int  # 当前工作负载
    max_workload: int  # 最大工作负载
    created_at: str = ""
    last_active: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_active:
            self.last_active = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TeamTask:
    """团队任务"""
    id: str
    title: str
    description: str
    task_type: str
    priority: int  # 1-10
    assigned_expert: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    dependencies: List[str] = None
    estimated_duration: float = 0.0  # 预计持续时间（秒）
    actual_duration: float = 0.0  # 实际持续时间（秒）
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TeamCollaboration:
    """团队协作"""
    id: str
    session_id: str
    user_id: str
    main_agent: str
    participating_experts: List[str]
    collaboration_type: str  # parallel, sequential, hierarchical
    status: str
    created_at: str = ""
    completed_at: Optional[str] = None
    results: Dict[str, Any] = None
    coordination_strategy: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.results is None:
            self.results = {}
        if self.metadata is None:
            self.metadata = {}


class ExpertTeamManager:
    """专家团队管理器"""
    
    def __init__(self, model_provider: str = "deepseek"):
        """
        初始化专家团队管理器
        
        Args:
            model_provider: 模型提供商
        """
        self.config = JubenSettings()
        self.logger = JubenLogger("ExpertTeamManager", level=self.config.log_level)
        self.storage_manager = JubenStorageManager()
        self.llm_client = JubenLLMClient(model_provider)
        self.performance_monitor = get_performance_monitor()
        
        # 专家团队
        self.experts: Dict[str, ExpertProfile] = {}
        self.active_tasks: Dict[str, TeamTask] = {}
        self.collaborations: Dict[str, TeamCollaboration] = {}
        
        # 团队配置
        self.team_config = {
            "max_parallel_tasks": 5,
            "task_timeout": 300,  # 5分钟
            "expert_rotation": True,
            "load_balancing": True,
            "quality_threshold": 0.8
        }
        
        # 专家注册表
        self.expert_registry: Dict[str, Callable] = {}
        
        self.logger.info("专家团队管理器初始化完成")
    
    async def initialize(self):
        """初始化团队管理器"""
        try:
            await self.storage_manager.initialize()
            await self._initialize_expert_team()
            self.logger.info("✅ 专家团队管理器初始化成功")
        except Exception as e:
            self.logger.error(f"❌ 专家团队管理器初始化失败: {e}")
            raise
    
    async def _initialize_expert_team(self):
        """初始化专家团队"""
        try:
            # 创建核心专家团队
            experts = [
                ExpertProfile(
                    id="story_analyst",
                    name="故事分析师",
                    expert_type=ExpertType.ANALYST,
                    specialization=["故事结构", "情节分析", "角色发展"],
                    capabilities=["文本分析", "结构评估", "趋势预测"],
                    experience_level=9,
                    success_rate=0.95,
                    response_time=2.5,
                    availability=True,
                    current_workload=0,
                    max_workload=3
                ),
                ExpertProfile(
                    id="content_creator",
                    name="内容创作者",
                    expert_type=ExpertType.CREATOR,
                    specialization=["剧本创作", "对话编写", "场景描述"],
                    capabilities=["创意生成", "内容创作", "风格适配"],
                    experience_level=8,
                    success_rate=0.92,
                    response_time=3.0,
                    availability=True,
                    current_workload=0,
                    max_workload=2
                ),
                ExpertProfile(
                    id="quality_evaluator",
                    name="质量评估师",
                    expert_type=ExpertType.EVALUATOR,
                    specialization=["质量评估", "标准检查", "改进建议"],
                    capabilities=["质量分析", "标准评估", "优化建议"],
                    experience_level=9,
                    success_rate=0.98,
                    response_time=1.8,
                    availability=True,
                    current_workload=0,
                    max_workload=4
                ),
                ExpertProfile(
                    id="research_specialist",
                    name="研究专家",
                    expert_type=ExpertType.RESEARCHER,
                    specialization=["市场研究", "用户分析", "竞品分析"],
                    capabilities=["数据收集", "趋势分析", "洞察提取"],
                    experience_level=8,
                    success_rate=0.90,
                    response_time=4.0,
                    availability=True,
                    current_workload=0,
                    max_workload=2
                ),
                ExpertProfile(
                    id="team_coordinator",
                    name="团队协调员",
                    expert_type=ExpertType.COORDINATOR,
                    specialization=["任务分配", "进度管理", "资源协调"],
                    capabilities=["项目管理", "团队协调", "流程优化"],
                    experience_level=10,
                    success_rate=0.96,
                    response_time=1.5,
                    availability=True,
                    current_workload=0,
                    max_workload=5
                )
            ]
            
            # 注册专家
            for expert in experts:
                self.experts[expert.id] = expert
                self.logger.info(f"👨‍💼 注册专家: {expert.name} ({expert.expert_type.value})")
            
            self.logger.info(f"✅ 专家团队初始化完成: {len(self.experts)} 位专家")
            
        except Exception as e:
            self.logger.error(f"初始化专家团队失败: {e}")
            raise
    
    async def create_expert_team(
        self,
        user_id: str,
        session_id: str,
        main_agent: str,
        task_description: str,
        collaboration_type: str = "parallel"
    ) -> TeamCollaboration:
        """
        创建专家团队
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            main_agent: 主Agent
            task_description: 任务描述
            collaboration_type: 协作类型
            
        Returns:
            团队协作对象
        """
        try:
            self.logger.info(f"👥 创建专家团队: {user_id}/{session_id}")
            
            # 分析任务需求
            task_analysis = await self._analyze_task_requirements(task_description)
            
            # 选择专家团队
            selected_experts = await self._select_expert_team(task_analysis)
            
            # 创建团队协作
            collaboration_id = str(uuid.uuid4())
            collaboration = TeamCollaboration(
                id=collaboration_id,
                session_id=session_id,
                user_id=user_id,
                main_agent=main_agent,
                participating_experts=selected_experts,
                collaboration_type=collaboration_type,
                status="active",
                coordination_strategy=self._determine_coordination_strategy(
                    collaboration_type, len(selected_experts)
                ),
                metadata={
                    "task_description": task_description,
                    "task_analysis": task_analysis,
                    "created_by": main_agent
                }
            )
            
            self.collaborations[collaboration_id] = collaboration
            
            # 更新专家工作负载
            for expert_id in selected_experts:
                if expert_id in self.experts:
                    self.experts[expert_id].current_workload += 1
                    self.experts[expert_id].last_active = datetime.now().isoformat()
            
            self.logger.info(f"✅ 专家团队创建成功: {len(selected_experts)} 位专家参与")
            return collaboration
            
        except Exception as e:
            self.logger.error(f"❌ 创建专家团队失败: {e}")
            raise
    
    async def _analyze_task_requirements(self, task_description: str) -> Dict[str, Any]:
        """分析任务需求"""
        try:
            # 构建任务分析提示词
            prompt = f"""
你是一个专业的任务分析专家，需要分析任务需求并确定所需的专家类型。

## 任务描述
{task_description}

## 分析要求
请分析这个任务需要哪些类型的专家，并按照以下格式输出：

```json
{{
    "required_expert_types": ["analyst", "creator", "evaluator"],
    "task_complexity": 8,
    "estimated_duration": 300,
    "parallel_possible": true,
    "dependencies": ["research", "analysis"],
    "quality_requirements": "high",
    "special_requirements": ["创意能力", "分析能力"]
}}
```

请确保分析准确，能够指导专家团队的选择。
"""
            
            # 调用LLM分析
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            if response and response.get('content'):
                # 解析LLM响应
                return self._parse_task_analysis(response['content'])
            else:
                # 使用默认分析
                return self._default_task_analysis(task_description)
                
        except Exception as e:
            self.logger.error(f"分析任务需求失败: {e}")
            return self._default_task_analysis(task_description)
    
    def _parse_task_analysis(self, llm_response: str) -> Dict[str, Any]:
        """解析任务分析结果"""
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                return self._default_task_analysis("")
        except Exception as e:
            self.logger.error(f"解析任务分析失败: {e}")
            return self._default_task_analysis("")
    
    def _default_task_analysis(self, task_description: str) -> Dict[str, Any]:
        """默认任务分析"""
        return {
            "required_expert_types": ["analyst", "evaluator"],
            "task_complexity": 5,
            "estimated_duration": 180,
            "parallel_possible": True,
            "dependencies": [],
            "quality_requirements": "medium",
            "special_requirements": []
        }
    
    async def _select_expert_team(self, task_analysis: Dict[str, Any]) -> List[str]:
        """选择专家团队"""
        try:
            required_types = task_analysis.get('required_expert_types', [])
            selected_experts = []
            
            # 根据需求选择专家
            for expert_id, expert in self.experts.items():
                if not expert.availability:
                    continue
                
                if expert.current_workload >= expert.max_workload:
                    continue
                
                # 检查专家类型是否匹配
                if expert.expert_type.value in required_types:
                    selected_experts.append(expert_id)
                elif expert.expert_type == ExpertType.COORDINATOR:
                    # 协调员总是需要的
                    selected_experts.append(expert_id)
            
            # 确保至少有一个专家
            if not selected_experts:
                # 选择最可用的专家
                available_experts = [
                    (expert_id, expert) for expert_id, expert in self.experts.items()
                    if expert.availability and expert.current_workload < expert.max_workload
                ]
                if available_experts:
                    # 按成功率排序
                    available_experts.sort(key=lambda x: x[1].success_rate, reverse=True)
                    selected_experts.append(available_experts[0][0])
            
            self.logger.info(f"🎯 选择专家团队: {selected_experts}")
            return selected_experts
            
        except Exception as e:
            self.logger.error(f"选择专家团队失败: {e}")
            return []
    
    def _determine_coordination_strategy(self, collaboration_type: str, expert_count: int) -> str:
        """确定协调策略"""
        if collaboration_type == "parallel":
            return "并行处理，结果整合"
        elif collaboration_type == "sequential":
            return "顺序处理，流水线作业"
        elif collaboration_type == "hierarchical":
            return "分层处理，主从协调"
        else:
            return "自适应协调"
    
    async def assign_task_to_expert(
        self,
        collaboration_id: str,
        task_title: str,
        task_description: str,
        expert_id: str,
        priority: int = 5
    ) -> TeamTask:
        """
        分配任务给专家
        
        Args:
            collaboration_id: 协作ID
            task_title: 任务标题
            task_description: 任务描述
            expert_id: 专家ID
            priority: 优先级
            
        Returns:
            任务对象
        """
        try:
            # 创建任务
            task_id = str(uuid.uuid4())
            task = TeamTask(
                id=task_id,
                title=task_title,
                description=task_description,
                task_type="expert_task",
                priority=priority,
                assigned_expert=expert_id,
                status=TaskStatus.PENDING,
                estimated_duration=self._estimate_task_duration(task_description, expert_id),
                metadata={
                    "collaboration_id": collaboration_id,
                    "created_by": "team_manager"
                }
            )
            
            self.active_tasks[task_id] = task
            
            # 更新专家状态
            if expert_id in self.experts:
                self.experts[expert_id].current_workload += 1
                self.experts[expert_id].last_active = datetime.now().isoformat()
            
            self.logger.info(f"📋 任务已分配: {task_title} -> {expert_id}")
            return task
            
        except Exception as e:
            self.logger.error(f"分配任务失败: {e}")
            raise
    
    def _estimate_task_duration(self, task_description: str, expert_id: str) -> float:
        """估算任务持续时间"""
        try:
            if expert_id in self.experts:
                expert = self.experts[expert_id]
                base_duration = expert.response_time
                
                # 根据任务复杂度调整
                complexity_factor = len(task_description) / 100  # 基于描述长度
                estimated_duration = base_duration * (1 + complexity_factor)
                
                return min(estimated_duration, 300)  # 最多5分钟
            else:
                return 60.0  # 默认1分钟
                
        except Exception as e:
            self.logger.error(f"估算任务持续时间失败: {e}")
            return 60.0
    
    async def execute_expert_task(
        self,
        task_id: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行专家任务
        
        Args:
            task_id: 任务ID
            input_data: 输入数据
            
        Returns:
            任务结果
        """
        try:
            if task_id not in self.active_tasks:
                raise ValueError(f"任务不存在: {task_id}")
            
            task = self.active_tasks[task_id]
            expert_id = task.assigned_expert
            
            if not expert_id or expert_id not in self.experts:
                raise ValueError(f"专家不存在: {expert_id}")
            
            expert = self.experts[expert_id]
            
            # 更新任务状态
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now().isoformat()
            
            self.logger.info(f"🚀 开始执行任务: {task.title} (专家: {expert.name})")
            
            # 记录性能监控
            with self.performance_monitor.monitor_performance(
                "ExpertTeamManager", 
                f"execute_task_{expert_id}",
                {"task_id": task_id, "expert": expert.name}
            ):
                # 执行专家任务
                result = await self._execute_expert_workflow(
                    expert, task, input_data
                )
            
            # 更新任务结果
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.result = result
            task.actual_duration = (
                datetime.fromisoformat(task.completed_at) - 
                datetime.fromisoformat(task.started_at)
            ).total_seconds()
            
            # 更新专家统计
            expert.current_workload = max(0, expert.current_workload - 1)
            expert.last_active = datetime.now().isoformat()
            
            # 更新成功率
            if result.get('success', False):
                expert.success_rate = (expert.success_rate * 0.9) + 0.1
            else:
                expert.success_rate = expert.success_rate * 0.95
            
            self.logger.info(f"✅ 任务执行完成: {task.title}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 执行专家任务失败: {e}")
            
            # 更新任务状态
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.now().isoformat()
            
            return {"success": False, "error": str(e)}
    
    async def _execute_expert_workflow(
        self,
        expert: ExpertProfile,
        task: TeamTask,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行专家工作流"""
        try:
            # 根据专家类型选择执行策略
            if expert.expert_type == ExpertType.ANALYST:
                return await self._execute_analyst_workflow(expert, task, input_data)
            elif expert.expert_type == ExpertType.CREATOR:
                return await self._execute_creator_workflow(expert, task, input_data)
            elif expert.expert_type == ExpertType.EVALUATOR:
                return await self._execute_evaluator_workflow(expert, task, input_data)
            elif expert.expert_type == ExpertType.RESEARCHER:
                return await self._execute_researcher_workflow(expert, task, input_data)
            elif expert.expert_type == ExpertType.COORDINATOR:
                return await self._execute_coordinator_workflow(expert, task, input_data)
            else:
                return await self._execute_generic_workflow(expert, task, input_data)
                
        except Exception as e:
            self.logger.error(f"执行专家工作流失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_analyst_workflow(
        self,
        expert: ExpertProfile,
        task: TeamTask,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行分析师工作流"""
        try:
            # 构建分析提示词
            prompt = f"""
你是一位专业的{expert.specialization[0]}，请分析以下内容：

任务: {task.title}
描述: {task.description}
输入数据: {input_data}

请提供专业的分析结果，包括：
1. 核心发现
2. 关键洞察
3. 建议和推荐
4. 风险评估

请确保分析专业、深入、实用。
"""
            
            # 调用LLM进行分析
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            if response and response.get('content'):
                return {
                    "success": True,
                    "expert_type": expert.expert_type.value,
                    "expert_name": expert.name,
                    "analysis_result": response['content'],
                    "confidence": expert.success_rate,
                    "execution_time": task.actual_duration
                }
            else:
                return {
                    "success": False,
                    "error": "分析失败：无法生成分析结果"
                }
                
        except Exception as e:
            self.logger.error(f"分析师工作流执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_creator_workflow(
        self,
        expert: ExpertProfile,
        task: TeamTask,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行创作者工作流"""
        try:
            # 构建创作提示词
            prompt = f"""
你是一位专业的{expert.specialization[0]}，请创作以下内容：

任务: {task.title}
描述: {task.description}
输入数据: {input_data}

请提供高质量的创作内容，包括：
1. 创意构思
2. 内容创作
3. 风格适配
4. 质量检查

请确保创作内容专业、创新、实用。
"""
            
            # 调用LLM进行创作
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.7
            )
            
            if response and response.get('content'):
                return {
                    "success": True,
                    "expert_type": expert.expert_type.value,
                    "expert_name": expert.name,
                    "creation_result": response['content'],
                    "confidence": expert.success_rate,
                    "execution_time": task.actual_duration
                }
            else:
                return {
                    "success": False,
                    "error": "创作失败：无法生成创作内容"
                }
                
        except Exception as e:
            self.logger.error(f"创作者工作流执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_evaluator_workflow(
        self,
        expert: ExpertProfile,
        task: TeamTask,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行评估师工作流"""
        try:
            # 构建评估提示词
            prompt = f"""
你是一位专业的{expert.specialization[0]}，请评估以下内容：

任务: {task.title}
描述: {task.description}
输入数据: {input_data}

请提供专业的评估结果，包括：
1. 质量评分（1-10分）
2. 优势分析
3. 改进建议
4. 总体评价

请确保评估客观、专业、实用。
"""
            
            # 调用LLM进行评估
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.2
            )
            
            if response and response.get('content'):
                return {
                    "success": True,
                    "expert_type": expert.expert_type.value,
                    "expert_name": expert.name,
                    "evaluation_result": response['content'],
                    "confidence": expert.success_rate,
                    "execution_time": task.actual_duration
                }
            else:
                return {
                    "success": False,
                    "error": "评估失败：无法生成评估结果"
                }
                
        except Exception as e:
            self.logger.error(f"评估师工作流执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_researcher_workflow(
        self,
        expert: ExpertProfile,
        task: TeamTask,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行研究员工作流"""
        try:
            # 构建研究提示词
            prompt = f"""
你是一位专业的{expert.specialization[0]}，请研究以下内容：

任务: {task.title}
描述: {task.description}
输入数据: {input_data}

请提供专业的研究结果，包括：
1. 研究背景
2. 关键发现
3. 数据洞察
4. 趋势分析

请确保研究深入、准确、有价值。
"""
            
            # 调用LLM进行研究
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2500,
                temperature=0.4
            )
            
            if response and response.get('content'):
                return {
                    "success": True,
                    "expert_type": expert.expert_type.value,
                    "expert_name": expert.name,
                    "research_result": response['content'],
                    "confidence": expert.success_rate,
                    "execution_time": task.actual_duration
                }
            else:
                return {
                    "success": False,
                    "error": "研究失败：无法生成研究结果"
                }
                
        except Exception as e:
            self.logger.error(f"研究员工作流执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_coordinator_workflow(
        self,
        expert: ExpertProfile,
        task: TeamTask,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行协调员工作流"""
        try:
            # 构建协调提示词
            prompt = f"""
你是一位专业的{expert.specialization[0]}，请协调以下任务：

任务: {task.title}
描述: {task.description}
输入数据: {input_data}

请提供专业的协调结果，包括：
1. 任务分解
2. 资源分配
3. 进度规划
4. 风险控制

请确保协调高效、合理、可行。
"""
            
            # 调用LLM进行协调
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            if response and response.get('content'):
                return {
                    "success": True,
                    "expert_type": expert.expert_type.value,
                    "expert_name": expert.name,
                    "coordination_result": response['content'],
                    "confidence": expert.success_rate,
                    "execution_time": task.actual_duration
                }
            else:
                return {
                    "success": False,
                    "error": "协调失败：无法生成协调结果"
                }
                
        except Exception as e:
            self.logger.error(f"协调员工作流执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_generic_workflow(
        self,
        expert: ExpertProfile,
        task: TeamTask,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行通用工作流"""
        try:
            # 构建通用提示词
            prompt = f"""
你是一位专业的{expert.name}，请处理以下任务：

任务: {task.title}
描述: {task.description}
输入数据: {input_data}

请提供专业的处理结果，确保质量高、实用性强。
"""
            
            # 调用LLM进行处理
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.5
            )
            
            if response and response.get('content'):
                return {
                    "success": True,
                    "expert_type": expert.expert_type.value,
                    "expert_name": expert.name,
                    "processing_result": response['content'],
                    "confidence": expert.success_rate,
                    "execution_time": task.actual_duration
                }
            else:
                return {
                    "success": False,
                    "error": "处理失败：无法生成处理结果"
                }
                
        except Exception as e:
            self.logger.error(f"通用工作流执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_team_status(self) -> Dict[str, Any]:
        """获取团队状态"""
        try:
            # 统计专家状态
            total_experts = len(self.experts)
            available_experts = sum(1 for expert in self.experts.values() if expert.availability)
            busy_experts = sum(1 for expert in self.experts.values() if expert.current_workload > 0)
            
            # 统计任务状态
            total_tasks = len(self.active_tasks)
            pending_tasks = sum(1 for task in self.active_tasks.values() if task.status == TaskStatus.PENDING)
            in_progress_tasks = sum(1 for task in self.active_tasks.values() if task.status == TaskStatus.IN_PROGRESS)
            completed_tasks = sum(1 for task in self.active_tasks.values() if task.status == TaskStatus.COMPLETED)
            failed_tasks = sum(1 for task in self.active_tasks.values() if task.status == TaskStatus.FAILED)
            
            # 统计协作状态
            total_collaborations = len(self.collaborations)
            active_collaborations = sum(1 for collab in self.collaborations.values() if collab.status == "active")
            
            return {
                "team_status": {
                    "total_experts": total_experts,
                    "available_experts": available_experts,
                    "busy_experts": busy_experts,
                    "utilization_rate": busy_experts / total_experts if total_experts > 0 else 0
                },
                "task_status": {
                    "total_tasks": total_tasks,
                    "pending_tasks": pending_tasks,
                    "in_progress_tasks": in_progress_tasks,
                    "completed_tasks": completed_tasks,
                    "failed_tasks": failed_tasks,
                    "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0
                },
                "collaboration_status": {
                    "total_collaborations": total_collaborations,
                    "active_collaborations": active_collaborations
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取团队状态失败: {e}")
            return {"error": str(e)}


# 全局专家团队管理器实例
_global_team_manager = None

def get_expert_team_manager() -> ExpertTeamManager:
    """获取全局专家团队管理器"""
    global _global_team_manager
    if _global_team_manager is None:
        _global_team_manager = ExpertTeamManager()
    return _global_team_manager

async def create_expert_team(
    user_id: str,
    session_id: str,
    main_agent: str,
    task_description: str,
    collaboration_type: str = "parallel"
) -> TeamCollaboration:
    """创建专家团队（便捷函数）"""
    manager = get_expert_team_manager()
    await manager.initialize()
    return await manager.create_expert_team(user_id, session_id, main_agent, task_description, collaboration_type)


def main():
    """主函数 - 用于测试和演示"""
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建专家团队管理器
    manager = ExpertTeamManager()
    
    # 模拟团队管理测试
    logger.info("专家团队管理器测试完成")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

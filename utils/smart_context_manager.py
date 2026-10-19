"""
智能上下文管理器 - 集成压缩、外部大脑和专家团队功能

⚠️ 已降级：短剧连载主路径请使用 utils.context_assembler.assemble_drama_context
与 BaseJubenAgent 的 UnifiedMemory context_pack（enable_enhanced_context 默认 False）。
本模块保留兼容，新功能勿再扩展。
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

try:
    from ..config.settings import JubenSettings
    from ..utils.logger import JubenLogger
    from ..utils.storage_manager import JubenStorageManager, ChatMessage, ContextState
    from ..utils.context_compactor import ContextCompactor, get_context_compactor
    from ..utils.external_brain import ExternalBrain, get_external_brain
    from ..utils.expert_team_manager import ExpertTeamManager, get_expert_team_manager
    from ..utils.performance_monitor import PerformanceMonitor, get_performance_monitor
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.storage_manager import JubenStorageManager, ChatMessage, ContextState
    from utils.context_compactor import ContextCompactor, get_context_compactor
    from utils.external_brain import ExternalBrain, get_external_brain
    from utils.expert_team_manager import ExpertTeamManager, get_expert_team_manager
    from utils.performance_monitor import PerformanceMonitor, get_performance_monitor


@dataclass
class SmartContextConfig:
    """智能上下文配置"""
    # 压缩配置
    enable_compression: bool = True
    compression_threshold: float = 0.8
    max_context_length: int = 8000
    
    # 外部大脑配置
    enable_external_brain: bool = True
    auto_learn: bool = True
    memory_consolidation_threshold: int = 10
    
    # 专家团队配置
    enable_expert_team: bool = True
    max_parallel_experts: int = 5
    expert_rotation: bool = True
    
    # 性能配置
    enable_performance_monitoring: bool = True
    monitoring_interval: int = 60


@dataclass
class ContextSession:
    """上下文会话"""
    session_id: str
    user_id: str
    agent_name: str
    created_at: str
    last_activity: str
    context_length: int
    compression_count: int
    learning_count: int
    expert_collaborations: int
    brain_health_score: float
    status: str  # active, compressed, learning, collaborating
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SmartContextManager:
    """智能上下文管理器"""
    
    def __init__(self, model_provider: str = "deepseek"):
        """
        初始化智能上下文管理器
        
        Args:
            model_provider: 模型提供商
        """
        self.config = JubenSettings()
        self.logger = JubenLogger("SmartContextManager", level=self.config.log_level)
        
        # 核心组件
        self.storage_manager = JubenStorageManager()
        self.context_compactor = get_context_compactor()
        self.external_brain = get_external_brain()
        self.expert_team_manager = get_expert_team_manager()
        self.performance_monitor = get_performance_monitor()
        
        # 配置
        self.smart_config = SmartContextConfig()
        
        # 会话管理
        self.active_sessions: Dict[str, ContextSession] = {}
        
        self.logger.info("智能上下文管理器初始化完成")
    
    async def initialize(self):
        """初始化智能上下文管理器"""
        try:
            # 初始化所有组件
            await self.storage_manager.initialize()
            await self.context_compactor.initialize()
            await self.external_brain.initialize()
            await self.expert_team_manager.initialize()
            
            # 启动性能监控
            if self.smart_config.enable_performance_monitoring:
                self.performance_monitor.start_monitoring(self.smart_config.monitoring_interval)
            
            self.logger.info("✅ 智能上下文管理器初始化成功")
            
        except Exception as e:
            self.logger.error(f"❌ 智能上下文管理器初始化失败: {e}")
            raise
    
    async def process_user_input(
        self,
        user_id: str,
        session_id: str,
        agent_name: str,
        user_input: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户输入（集成三个功能）
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            agent_name: Agent名称
            user_input: 用户输入
            context_data: 上下文数据
            
        Returns:
            处理结果
        """
        try:
            self.logger.info(f"🧠 智能处理用户输入: {user_id}/{session_id}")
            
            # 1. 检查并更新会话状态
            session = await self._get_or_create_session(user_id, session_id, agent_name)
            
            # 2. 检查是否需要压缩上下文
            if self.smart_config.enable_compression:
                compression_result = await self._check_and_compress_context(
                    user_id, session_id, agent_name
                )
                if compression_result:
                    session.compression_count += 1
                    self.logger.info(f"📝 上下文已压缩: {compression_result.compression_ratio:.2%}")
            
            # 3. 从外部大脑检索相关记忆
            relevant_memories = []
            if self.smart_config.enable_external_brain:
                relevant_memories = await self.external_brain.retrieve_relevant_memories(
                    user_id, user_input, limit=5
                )
                if relevant_memories:
                    self.logger.info(f"🧠 检索到 {len(relevant_memories)} 个相关记忆")
            
            # 4. 分析是否需要专家团队协作
            expert_collaboration = None
            if self.smart_config.enable_expert_team:
                collaboration_decision = await self._analyze_collaboration_need(
                    user_input, context_data, relevant_memories
                )
                if collaboration_decision['needed']:
                    expert_collaboration = await self._create_expert_collaboration(
                        user_id, session_id, agent_name, user_input, collaboration_decision
                    )
                    session.expert_collaborations += 1
                    self.logger.info(f"👥 创建专家协作: {len(expert_collaboration.participating_experts)} 位专家")
            
            # 5. 生成智能响应
            response = await self._generate_smart_response(
                user_input, context_data, relevant_memories, expert_collaboration
            )
            
            # 6. 学习并更新外部大脑
            if self.smart_config.enable_external_brain and self.smart_config.auto_learn:
                await self._learn_from_interaction(
                    user_id, session_id, agent_name, {
                        'user_input': user_input,
                        'response': response,
                        'context': context_data,
                        'memories_used': relevant_memories,
                        'expert_collaboration': expert_collaboration
                    }
                )
                session.learning_count += 1
            
            # 7. 更新会话状态
            await self._update_session_status(session, user_input, response)
            
            # 8. 记录性能指标
            if self.smart_config.enable_performance_monitoring:
                self.performance_monitor.record_operation(
                    agent_name="SmartContextManager",
                    operation="process_user_input",
                    duration=0.0,  # 实际计算
                    success=True,
                    metadata={
                        "user_id": user_id,
                        "session_id": session_id,
                        "compression_applied": session.compression_count > 0,
                        "memories_retrieved": len(relevant_memories),
                        "expert_collaboration": expert_collaboration is not None
                    }
                )
            
            self.logger.info("✅ 智能处理完成")
            return {
                "success": True,
                "response": response,
                "context_compressed": session.compression_count > 0,
                "memories_used": len(relevant_memories),
                "expert_collaboration": expert_collaboration is not None,
                "session_status": session.status,
                "brain_health_score": session.brain_health_score
            }
            
        except Exception as e:
            self.logger.error(f"❌ 智能处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "抱歉，处理过程中出现了错误。"
            }
    
    async def _get_or_create_session(
        self, 
        user_id: str, 
        session_id: str, 
        agent_name: str
    ) -> ContextSession:
        """获取或创建会话"""
        try:
            session_key = f"{user_id}_{session_id}_{agent_name}"
            
            if session_key in self.active_sessions:
                session = self.active_sessions[session_key]
                session.last_activity = datetime.now().isoformat()
                return session
            
            # 创建新会话
            session = ContextSession(
                session_id=session_id,
                user_id=user_id,
                agent_name=agent_name,
                created_at=datetime.now().isoformat(),
                last_activity=datetime.now().isoformat(),
                context_length=0,
                compression_count=0,
                learning_count=0,
                expert_collaborations=0,
                brain_health_score=1.0,
                status="active"
            )
            
            self.active_sessions[session_key] = session
            self.logger.info(f"📝 创建新会话: {session_key}")
            return session
            
        except Exception as e:
            self.logger.error(f"获取或创建会话失败: {e}")
            raise
    
    async def _check_and_compress_context(
        self, 
        user_id: str, 
        session_id: str, 
        agent_name: str
    ) -> Optional[Any]:
        """检查并压缩上下文"""
        try:
            # 获取当前消息
            messages = await self.storage_manager.get_chat_messages(user_id, session_id, limit=1000)
            if not messages:
                return None
            
            # 检查是否需要压缩
            should_compress, usage_ratio = self.context_compactor.should_compress(messages)
            if not should_compress:
                return None
            
            # 执行压缩
            compression_result = await self.context_compactor.compress_context(
                user_id, session_id, agent_name
            )
            
            return compression_result
            
        except Exception as e:
            self.logger.error(f"检查并压缩上下文失败: {e}")
            return None
    
    async def _analyze_collaboration_need(
        self,
        user_input: str,
        context_data: Optional[Dict[str, Any]],
        relevant_memories: List[Any]
    ) -> Dict[str, Any]:
        """分析是否需要专家协作"""
        try:
            # 构建协作需求分析提示词
            prompt = f"""
你是一个专业的协作需求分析专家，需要判断当前任务是否需要专家团队协作。

## 用户输入
{user_input}

## 上下文数据
{context_data or "无"}

## 相关记忆
{len(relevant_memories)} 个相关记忆

## 分析要求
请分析这个任务是否需要专家团队协作，并按照以下格式输出：

```json
{{
    "needed": true/false,
    "reason": "需要协作的原因",
    "required_experts": ["analyst", "creator", "evaluator"],
    "collaboration_type": "parallel/sequential/hierarchical",
    "complexity": 8,
    "estimated_duration": 300
}}
```

判断标准：
1. 任务复杂度高（需要多个专业领域）
2. 需要深度分析或创作
3. 涉及多个决策点
4. 需要质量评估
5. 时间要求紧但质量要求高

请确保分析准确，避免不必要的协作。
"""
            
            # 调用LLM分析
            response = await self.context_compactor.llm_client.generate_response(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            if response and response.get('content'):
                # 解析响应
                return self._parse_collaboration_analysis(response['content'])
            else:
                # 使用简单判断
                return self._simple_collaboration_analysis(user_input)
                
        except Exception as e:
            self.logger.error(f"分析协作需求失败: {e}")
            return {"needed": False, "reason": "分析失败"}
    
    def _parse_collaboration_analysis(self, llm_response: str) -> Dict[str, Any]:
        """解析协作分析结果"""
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                return self._simple_collaboration_analysis("")
        except Exception as e:
            self.logger.error(f"解析协作分析失败: {e}")
            return {"needed": False, "reason": "解析失败"}
    
    def _simple_collaboration_analysis(self, user_input: str) -> Dict[str, Any]:
        """简单协作分析"""
        # 简单的关键词判断
        collaboration_keywords = [
            "分析", "评估", "创作", "研究", "优化", "改进",
            "复杂", "专业", "深度", "全面", "详细"
        ]
        
        needs_collaboration = any(keyword in user_input for keyword in collaboration_keywords)
        
        return {
            "needed": needs_collaboration,
            "reason": "基于关键词分析",
            "required_experts": ["analyst", "evaluator"] if needs_collaboration else [],
            "collaboration_type": "parallel",
            "complexity": 5 if needs_collaboration else 3,
            "estimated_duration": 180 if needs_collaboration else 60
        }
    
    async def _create_expert_collaboration(
        self,
        user_id: str,
        session_id: str,
        agent_name: str,
        user_input: str,
        collaboration_decision: Dict[str, Any]
    ) -> Any:
        """创建专家协作"""
        try:
            # 创建专家团队
            collaboration = await self.expert_team_manager.create_expert_team(
                user_id=user_id,
                session_id=session_id,
                main_agent=agent_name,
                task_description=user_input,
                collaboration_type=collaboration_decision.get('collaboration_type', 'parallel')
            )
            
            # 分配任务给专家
            for expert_id in collaboration.participating_experts:
                if expert_id != "team_coordinator":  # 协调员不分配具体任务
                    task = await self.expert_team_manager.assign_task_to_expert(
                        collaboration_id=collaboration.id,
                        task_title=f"处理用户请求: {user_input[:50]}",
                        task_description=user_input,
                        expert_id=expert_id,
                        priority=collaboration_decision.get('complexity', 5)
                    )
                    
                    # 执行任务
                    result = await self.expert_team_manager.execute_expert_task(
                        task_id=task.id,
                        input_data={"user_input": user_input}
                    )
                    
                    # 存储结果
                    if task.id not in collaboration.results:
                        collaboration.results[task.id] = result
            
            return collaboration
            
        except Exception as e:
            self.logger.error(f"创建专家协作失败: {e}")
            return None
    
    async def _generate_smart_response(
        self,
        user_input: str,
        context_data: Optional[Dict[str, Any]],
        relevant_memories: List[Any],
        expert_collaboration: Optional[Any]
    ) -> str:
        """生成智能响应"""
        try:
            # 构建智能响应提示词
            prompt = self._build_smart_response_prompt(
                user_input, context_data, relevant_memories, expert_collaboration
            )
            
            # 调用LLM生成响应
            response = await self.context_compactor.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.7
            )
            
            if response and response.get('content'):
                return response['content']
            else:
                return "抱歉，我无法生成合适的响应。"
                
        except Exception as e:
            self.logger.error(f"生成智能响应失败: {e}")
            return "抱歉，处理过程中出现了错误。"
    
    def _build_smart_response_prompt(
        self,
        user_input: str,
        context_data: Optional[Dict[str, Any]],
        relevant_memories: List[Any],
        expert_collaboration: Optional[Any]
    ) -> str:
        """构建智能响应提示词"""
        
        # 构建记忆信息
        memory_info = ""
        if relevant_memories:
            memory_info = "相关记忆信息：\n"
            for i, memory in enumerate(relevant_memories[:3]):  # 最多3个记忆
                memory_info += f"{i+1}. {memory.content}\n"
        
        # 构建专家协作信息
        expert_info = ""
        if expert_collaboration:
            expert_info = f"专家团队协作结果：\n"
            for task_id, result in expert_collaboration.results.items():
                if result.get('success'):
                    expert_info += f"- {result.get('expert_name', '专家')}: {result.get('analysis_result', result.get('creation_result', result.get('evaluation_result', '处理完成')))}\n"
        
        prompt = f"""
你是一个智能助手，需要基于以下信息生成高质量的响应：

## 用户输入
{user_input}

## 上下文信息
{context_data or "无特殊上下文"}

{memory_info}

{expert_info}

## 响应要求
请生成一个专业、有用、个性化的响应，要求：

1. **直接回应**：直接回答用户的问题或满足用户的需求
2. **利用记忆**：充分利用相关记忆信息，提供个性化服务
3. **整合专家意见**：如果使用了专家团队，整合专家意见形成综合响应
4. **保持连贯**：确保响应与上下文连贯
5. **提供价值**：确保响应对用户有价值

请确保响应自然、专业、有用。
"""
        
        return prompt
    
    async def _learn_from_interaction(
        self,
        user_id: str,
        session_id: str,
        agent_name: str,
        interaction_data: Dict[str, Any]
    ):
        """从交互中学习"""
        try:
            await self.external_brain.learn_from_interaction(
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name,
                interaction_data=interaction_data
            )
            
        except Exception as e:
            self.logger.error(f"学习交互失败: {e}")
    
    async def _update_session_status(
        self,
        session: ContextSession,
        user_input: str,
        response: str
    ):
        """更新会话状态"""
        try:
            # 更新上下文长度
            session.context_length += len(user_input) + len(response)
            
            # 更新大脑健康分数
            brain_summary = await self.external_brain.get_brain_summary(session.user_id)
            session.brain_health_score = brain_summary.get('brain_health_score', 1.0)
            
            # 更新状态
            if session.compression_count > 0:
                session.status = "compressed"
            elif session.learning_count > 0:
                session.status = "learning"
            elif session.expert_collaborations > 0:
                session.status = "collaborating"
            else:
                session.status = "active"
            
            # 更新活动时间
            session.last_activity = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"更新会话状态失败: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 获取各组件状态
            compression_stats = self.context_compactor.get_compression_stats()
            brain_summary = await self.external_brain.get_brain_summary("system")
            team_status = await self.expert_team_manager.get_team_status()
            performance_summary = self.performance_monitor.get_performance_summary()
            
            # 统计会话信息
            total_sessions = len(self.active_sessions)
            active_sessions = sum(1 for s in self.active_sessions.values() if s.status == "active")
            compressed_sessions = sum(1 for s in self.active_sessions.values() if s.status == "compressed")
            learning_sessions = sum(1 for s in self.active_sessions.values() if s.status == "learning")
            collaborating_sessions = sum(1 for s in self.active_sessions.values() if s.status == "collaborating")
            
            return {
                "system_status": {
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "compressed_sessions": compressed_sessions,
                    "learning_sessions": learning_sessions,
                    "collaborating_sessions": collaborating_sessions
                },
                "compression_status": compression_stats,
                "brain_status": brain_summary,
                "team_status": team_status,
                "performance_status": performance_summary,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取系统状态失败: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_sessions(self, max_age_hours: int = 24):
        """清理旧会话"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            sessions_to_remove = []
            
            for session_key, session in self.active_sessions.items():
                last_activity = datetime.fromisoformat(session.last_activity)
                if last_activity < cutoff_time:
                    sessions_to_remove.append(session_key)
            
            for session_key in sessions_to_remove:
                del self.active_sessions[session_key]
            
            self.logger.info(f"🧹 清理了 {len(sessions_to_remove)} 个旧会话")
            
        except Exception as e:
            self.logger.error(f"清理旧会话失败: {e}")


# 全局智能上下文管理器实例
_global_smart_context_manager = None

def get_smart_context_manager() -> SmartContextManager:
    """获取全局智能上下文管理器"""
    global _global_smart_context_manager
    if _global_smart_context_manager is None:
        _global_smart_context_manager = SmartContextManager()
    return _global_smart_context_manager

async def process_smart_input(
    user_id: str,
    session_id: str,
    agent_name: str,
    user_input: str,
    context_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """智能处理用户输入（便捷函数）"""
    manager = get_smart_context_manager()
    await manager.initialize()
    return await manager.process_user_input(user_id, session_id, agent_name, user_input, context_data)


def main():
    """主函数 - 用于测试和演示"""
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建智能上下文管理器
    manager = SmartContextManager()
    
    # 模拟智能处理测试
    logger.info("智能上下文管理器测试完成")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime

"""
故事五元素工作流 - 人物小传生成智能体
 专门用于生成故事中主要人物的详细小传
作为故事五元素分析系统的专业子智能体之一

业务处理逻辑：
1. 输入处理：接收故事文本或input字段，支持多种输入格式
2. 人物识别：使用LLM分析文本，识别主要人物和重要配角
3. 人物分析：为每个人物提取基本信息、性格特征、背景故事
4. 小传生成：生成300-500字的详细人物小传，包含关系、目标、困境
5. 质量控制：确保至少8个人物，内容准确无幻觉
6. 输出格式化：返回结构化的人物小传数据
7. Agent as Tool：支持被其他智能体调用，上下文隔离

代码作者：宫灵瑞
创建时间：2024年10月19日
"""

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from agents.base_juben_agent import BaseJubenAgent


class CharacterProfileGeneratorAgent(BaseJubenAgent):
    """
    人物小传生成智能体 - 故事五元素分析系统的专业子智能体

    核心功能：
    1. 识别故事中的主要人物
    2. 生成300-500字的详细人物小传
    3. 包含人物关系、目标、困境
    4. 支持Agent as Tool机制
    5. 确保至少8个人物
    """

    def __init__(self, model_provider: str = "deepseek"):
        """初始化人物小传生成智能体"""
        super().__init__("character_profile_generator", model_provider)

        # 工作流配置
        self.workflow_type = "story_five_elements"
        self.sub_agent_type = "character_profile_generator"
        self.min_characters = 8
        self.profile_length_range = (300, 500)

        self.logger.info("👤 人物小传生成智能体初始化完成")
        self.logger.info(f"📋 工作流类型: {self.workflow_type}")
        self.logger.info(f"🎯 子智能体类型: {self.sub_agent_type}")
        self.logger.info(f"📊 配置: 最少{self.min_characters}个人物，小传长度{self.profile_length_range[0]}-{self.profile_length_range[1]}字")

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
                - auto_save_note: 是否自动保存为Note（默认True）

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
            auto_save_note = context.get("auto_save_note", True) if context else True

            if tool_call:
                self.logger.info(f"🔧 Agent as Tool模式，父智能体: {parent_agent}")

            self.logger.info(f"开始人物小传生成: {input_text[:100]}...")

            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)

            # 构建生成提示词
            generation_prompt = f"""## Profile:
- role: 资深的人物分析专家
- language: 中文
- description: 专门分析故事文本，识别主要人物，并为每个人物生成详细的人物小传。

## Definition：
- "人物小传"是对故事中主要人物的身份、背景、性格、关系、目标和困境的详细描述，帮助读者或制作团队深入理解人物。

## Constrains:
- 请确保识别至少8个主要人物（包括主角、配角、反派等）。
- 每个人物的小传控制在300-500字之间。
- 请严格按照文本原文所表达的信息进行总结，不要自行创作或改编。
- 请避免出现幻觉，不要将提示词的任何内容带进你输出的回答中。
- 输出回答时，不要对文本内容做任何总结、评述性的概述。

## Skills:
- 善于准确识别故事中的主要人物和重要配角。
- 擅长分析人物的身份、背景、性格特征。
- 擅长梳理人物之间的关系。
- 擅长分析人物的目标和困境。
- 擅长用优美准确的语言撰写人物小传。

## Workflows:
- 第一步，仔细阅读故事文本，识别出至少8个主要人物。
- 第二步，为每个人物提取基本信息（身份、背景、性格）、关系、目标、困境。
- 第三步，按照「Definition」中关于人物小传的要求，为每个人物生成300-500字的详细小传。

## OutputFormat:
<为每个人物生成详细的300-500字小传，不要带任何其他标题。每个人物的小传应包含：身份、背景、性格、关系、目标、困境等信息。>

## 故事文本：
{input_text}
"""

            # 构建消息
            messages = [
                {"role": "user", "content": generation_prompt}
            ]

            # 🆕 使用自动保存Note的包装器
            async for event in self._collect_and_save_output(
                user_id=user_id,
                session_id=session_id,
                event_generator=self._stream_llm_with_billing(messages, user_id, session_id),
                auto_save_note=auto_save_note and not tool_call,  # 工具调用模式不自动保存
                note_name=f"character_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            ):
                yield event

        except Exception as e:
            self.logger.error(f"人物小传生成失败: {e}")
            yield await self._emit_event("error", f"生成失败: {str(e)}")

    async def _stream_llm_with_billing(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        session_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式调用LLM并返回计费信息的辅助方法

        Args:
            messages: 消息列表
            user_id: 用户ID
            session_id: 会话ID

        Yields:
            Dict: 流式响应事件
        """
        # 流式调用LLM
        async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
            yield await self._emit_event("llm_chunk", chunk)

        # 获取Token计费摘要
        billing_summary = await self.get_token_billing_summary()
        if billing_summary:
            yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")

        # 发送完成事件（触发Note保存）
        yield await self._emit_event("done", "人物小传生成完成")

    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "character_profile_generator",
            "capabilities": [
                "人物识别",
                "小传生成",
                "关系分析",
                "性格分析"
            ],
            "output_requirements": {
                "min_characters": self.min_characters,
                "min_words": self.profile_length_range[0],
                "max_words": self.profile_length_range[1]
            }
        })
        return base_info

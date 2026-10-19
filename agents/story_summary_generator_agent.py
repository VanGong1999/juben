from typing import AsyncGenerator, Dict, Any, Optional

"""
故事五元素工作流 - 故事梗概生成智能体
 专门用于生成行文流畅的故事梗概
作为故事五元素分析系统的专业子智能体之一

业务处理逻辑：
1. 输入处理：接收故事文本或input字段，支持长文本处理
2. 内容分析：深入分析故事文本内容，理解故事结构和主题
3. 梗概生成：生成800-2500字的流畅故事梗概，第三人称叙事
4. 内容覆盖：确保覆盖故事全文内容，无遗漏重要情节
5. 质量控制：避免幻觉和创作改编，严格按照原文分析
6. 输出格式化：返回结构化的故事梗概数据
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

class StorySummaryGeneratorAgent(BaseJubenAgent):
    """
    故事梗概生成智能体 - 故事五元素分析系统的专业子智能体
    
    核心功能：
    1. 深入分析故事文本内容
    2. 整理成行文流畅的故事梗概（800-2500字）
    3. 确保覆盖故事全文内容，无遗漏
    4. 支持Agent as Tool机制，可被其他智能体调用
    5. 第三人称叙事，避免幻觉和创作改编
    
    作为故事五元素工作流中的专业子智能体，专门负责故事梗概生成任务
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化故事梗概生成智能体"""
        super().__init__("story_summary_generator", model_provider)
        
        # 系统提示词配置（从prompts文件夹加载）
        # 工作流配置
        self.workflow_type = "story_five_elements"
        self.sub_agent_type = "story_summary_generator"
        self.summary_length_range = (800, 2500)  # 故事梗概800-2500字
        self.narrative_style = "第三人称"  # 叙事风格要求
        
        self.logger.info("📖 故事梗概生成智能体初始化完成")
        self.logger.info(f"📋 工作流类型: {self.workflow_type}")
        self.logger.info(f"🎯 子智能体类型: {self.sub_agent_type}")
        self.logger.info(f"📊 配置: 梗概长度{self.summary_length_range[0]}-{self.summary_length_range[1]}字，叙事风格: {self.narrative_style}")
    
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
        try:
            # 提取请求信息
            input_text = request_data.get("input", "")
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            parent_agent = context.get("parent_agent", "") if context else ""
            tool_call = context.get("tool_call", False) if context else False

            if tool_call:
                self.logger.info(f"🔧 Agent as Tool模式，父智能体: {parent_agent}")

            self.logger.info(f"开始故事梗概生成: {input_text[:100]}...")

            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 构建生成提示词
            generation_prompt = f"""
## Profile:
- role: 资深的编剧
- language: 中文
- description: 深入分析一段故事文本的内容，将其主要内容整理成行文流畅的的故事梗概。

## Definition：
- "故事梗概"用于简洁明快地介绍故事的基本情节、走向，包括主要角色、主要冲突和解决方案。梗概的目标是让观众（或可能的投资人、制片人）快速理解故事的核心内容和售卖点，而无需深入到具体的情节或角色发展中。

## Constrains:
- 请严格控制你总结的故事梗概内容字数在800个汉字以上，2500个汉字以下，切记不要超过2500个汉字。
- 请严格确保你对故事文本的阅读与总结覆盖到故事文本的全文，不要有遗漏。
- 请严格按照文本原文所表达的意思总结主要内容，不要自行进行创作与改编。
- 请直接输出所总结的文本主要内容，不要带任何其他标题。
- 请避免出现幻觉，不要将提示词的任何内容带进你输出的回答中。
- 输出回答时，不要对文本内容做任何总结、评述性的概述。
- 输出回答时，不要为了凑字数重复输出相同的内容。

## Skills:
- 善于准确地总结故事文本中的人物、人物关系、人物行动、事件情节。
- 擅长辨别故事文本中第一人称叙事与第三人称叙事的区别，并用第三人称进行准确地总结。
- 擅长理解复杂的人物身份、人物关系，并进行准确地总结。
- 擅长通过故事文本的上下文关系，对故事文本中表述重复、混乱、断裂的部分进行梳理，从而总结出准确的故事信息。
- 擅长用优美准确的语言总结故事梗概。

## Workflows:
- 第一步，对提供的故事文本进行深入地阅读，准确理解故事文本中的人物、人物关系、事件情节。
- 第二步，根据第一步的阅读，结合「Definition」中有关故事梗概的相关介绍，将故事文本总结为一篇行文流畅的故事梗概。要求字数严格保持在800个汉字以上，2500个汉字以下，切记不要超过2500个汉字。

## OutputFormat:
<用优美的格式、流畅的文字总结故事梗概，不要带任何其他标题。要求字数严格保持在800个汉字以上，2500个汉字以下，切记不要超过2500个汉字。>

## 故事文本：
{input_text}
"""
            
            # 构建消息
            messages = [
                {"role": "user", "content": generation_prompt}
            ]
            
            # 流式调用LLM
            async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                yield await self._emit_event("llm_chunk", chunk)
            
            # 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")
            
        except Exception as e:
            self.logger.error(f"故事梗概生成失败: {e}")
            yield await self._emit_event("error", f"生成失败: {str(e)}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "story_summary_generator",
            "capabilities": [
                "故事内容分析",
                "行文流畅梗概生成",
                "字数控制（800-2500字）",
                "全文覆盖检查",
                "第三人称叙事转换"
            ],
            "output_requirements": {
                "min_words": 800,
                "max_words": 2500,
                "format": "第三人称叙事",
                "coverage": "全文覆盖"
            }
        })
        return base_info

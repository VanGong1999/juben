from typing import AsyncGenerator, Dict, Any, Optional

"""
IP 初筛评估智能体
基于 agent-as-tool 机制，实现智能体间的模块化外包和上下文隔离

业务处理逻辑：
1. 输入处理：接收 IP 内容信息，支持“自由输入文案”和结构化字段两种方式；
2. IP 内容分析：对 IP 内容进行深入评估分析；
3. 影视改编价值评估：基于多维度评分框架进行打分；
4. 市场潜力分析：评估 IP 在影视市场的改编潜力；
5. IP 价值判断：判断 IP 是否适合进行影视改编；
6. 改编建议：提供具体的改编建议和方向；
7. 输出格式化：返回结构化的 IP 评估数据；
8. Agent as Tool：支持被其他智能体调用，实现上下文隔离。

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

    from agents.base_juben_agent import BaseJubenAgent  # type: ignore


class IPEvaluationAgent(BaseJubenAgent):
    """
    IP初筛评估智能体
    
    核心功能：
    1. 对IP内容进行深入评估分析
    2. 基于Story Evaluation Framework进行多维度评分
    3. 提供影视改编价值判断
    4. 支持Agent as Tool机制
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        super().__init__("ip_evaluation", model_provider)

        # IP 评估配置（仅用于提示词说明）
        self.evaluation_dimensions = ["IP价值", "改编潜力", "市场前景", "内容质量"]
        self.adaptation_factors = ["故事完整性", "人物塑造", "情节结构", "商业价值"]

        self.logger.info("🎭 IP初筛评估智能体初始化完成")
        self.logger.info(f"📊 评估维度: {len(self.evaluation_dimensions)}个")
        self.logger.info(f"🎯 改编因素: {len(self.adaptation_factors)}个")

    # 系统提示词由基类自动加载，无需重写

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理 IP 价值评估请求（支持 Agent as Tool 以及直接聊天调用）

        Args:
            request_data: 请求数据
            context: 上下文信息
                - user_id: 用户ID
                - session_id: 会话ID
                - parent_agent: 父智能体名称（Agent as Tool模式）
                - tool_call: 是否为工具调用

        Yields:
            Dict: 流式响应事件（遵循 BaseJubenAgent._emit_event 统一格式）
        """
        try:
            # 提取基础上下文
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            parent_agent = context.get("parent_agent", "") if context else ""
            tool_call = context.get("tool_call", False) if context else False

            if tool_call:
                self.logger.info(f"🔧 IP评估 Agent 作为工具被调用，父智能体: {parent_agent}")

            # 初始化 Token 累加器
            await self.initialize_token_accumulator(user_id, session_id)

            # ===== 1. 解析输入 =====
            # 支持两种使用方式：
            # - 方式 A：纯文本 input（前端当前就是这种用法）
            # - 方式 B：结构化字段 name/type/theme/author/content/content1
            input_text = str(request_data.get("input", "") or "").strip()

            name = str(request_data.get("name", "") or "").strip()
            theme = str(request_data.get("theme", "") or "").strip()
            ip_type = str(request_data.get("type", "") or "").strip()
            author = str(request_data.get("author", "") or "").strip()
            content = str(request_data.get("content", "") or "").strip()
            content1 = str(request_data.get("content1", "") or "").strip()

            # 如果结构化字段为空，则把 input 视为 IP 简介/内容
            if not any([name, theme, ip_type, author, content, content1]) and input_text:
                content = input_text

            if not any([content, content1]):
                # 没有可评估内容，直接返回错误事件
                self.logger.warning("IP评估请求缺少内容")
                yield await self._emit_event("error", "IP评估失败：未提供可评估的内容")
                return

            # ===== 2. 发送开始事件 =====
            start_msg = f"开始对 IP 进行价值评估{'（工具调用）' if tool_call else ''}..."
            yield await self._emit_event(
                "system",
                start_msg,
                metadata={
                    "ip_name": name or None,
                    "ip_type": ip_type or None,
                },
            )

            # ===== 3. 构建评估提示词 =====
            evaluation_prompt = self._build_evaluation_prompt(
                {
                    "name": name,
                    "theme": theme,
                    "ip_type": ip_type,
                    "author": author,
                    "content": content,
                    "content1": content1,
                }
            )

            messages = [
                # system 提示词由 _stream_llm 自动注入，这里只传 user 即可
                {"role": "user", "content": evaluation_prompt}
            ]

            # ===== 4. 流式调用 LLM 并按统一格式返回 =====
            yield await self._emit_event("system", "🧠 正在分析 IP 价值与改编潜力...")

            async for chunk in self._stream_llm(
                messages, user_id=user_id, session_id=session_id
            ):
                if not chunk:
                    continue
                # 统一用 llm_chunk 事件，让前端按普通文本流式拼接
                yield await self._emit_event("llm_chunk", chunk)

            # ===== 5. 完成与计费信息 =====
            yield await self._emit_event("system", "✅ IP评估分析完成")

            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                billing_msg = (
                    f"📊 Token消耗: {billing_summary['total_tokens']} tokens, "
                    f"积分扣减: {billing_summary['deducted_points']} 积分"
                )
                yield await self._emit_event("billing", billing_msg)

        except Exception as e:
            self.logger.error(f"IP评估失败: {e}")
            yield await self._emit_event("error", f"IP评估失败: {str(e)}")

    def _build_evaluation_prompt(self, data: Dict[str, Any]) -> str:
        """
        构建 IP 评估提示词（统一在这里处理文案，便于后续优化）
        """
        name = data.get("name") or ""
        theme = data.get("theme") or ""
        ip_type = data.get("ip_type") or ""
        author = data.get("author") or ""
        content = data.get("content") or ""
        content1 = data.get("content1") or ""

        basic_info_lines = []
        if name:
            basic_info_lines.append(f"IP名称：{name}")
        if ip_type:
            basic_info_lines.append(f"IP类型：{ip_type}")
        if theme:
            basic_info_lines.append(f"主题：{theme}")
        if author:
            basic_info_lines.append(f"作者：{author}")

        basic_info = "\n".join(basic_info_lines) if basic_info_lines else "（未提供结构化基本信息）"

        prompt = f"""
你是一名资深的 IP 价值评估专家，请站在影视改编与商业开发的角度，对下述 IP 进行系统评估，并给出清晰、结构化的结论和建议。

【IP 基本信息】
{basic_info}

【IP 主要内容 / 简介】
{content or '（未提供）'}

【补充内容】
{content1 or '（无）'}

请从以下维度进行评估，并用中文详细展开（可以使用分点、小标题等清晰结构）：
1. IP 价值评估（原创性、世界观、人物吸引力、故事卖点等）；
2. 改编潜力评估（改编成短剧/长剧/电影/综艺的可行性，适配的载体与平台）；
3. 市场前景评估（目标受众、市场需求匹配度、竞品环境、变现路径等）；
4. 内容质量评估（故事完整性、人物塑造、情节节奏、文本成熟度等）；
5. 综合结论与评级（建议给出清晰的等级：S/A/B/C，并解释理由）；
6. 具体改编建议（可以考虑题材方向、集数体量、核心卖点强化方式等）。

要求：
- 用专业、易懂的影视从业者视角进行分析；
- 结构清晰，便于后续整理成「IP评估报告」；
- 如存在重大风险点或硬伤，请在结论中显式强调。
"""
        return prompt.strip()

    async def evaluate_ip_content(
        self,
        ip_name: str,
        ip_type: str,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Agent as Tool: 评估IP内容
        
        Args:
            ip_name: IP名称
            ip_type: IP类型
            content: IP内容
            context: 上下文信息
            
        Returns:
            Dict[str, Any]: 评估结果
        """
        request_data = {
            "name": ip_name,
            "type": ip_type,
            "content": content,
        }

        result = {
            "ip_name": ip_name,
            "ip_type": ip_type,
            "evaluation_result": "",
            "adaptation_recommendation": "",
            "market_potential": "",
            "content_quality": ""
        }

        # 收集流式输出
        async for event in self.process_request(request_data, context):
            # 这里复用统一事件格式：llm_chunk 视为正文
            if event.get("event_type") == "llm_chunk":
                chunk = event.get("data", "")
                if isinstance(chunk, str):
                    result["evaluation_result"] += chunk

        return result

    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "agent_name": "IP初筛评估智能体",
            "agent_type": "evaluation",
            "description": "对IP内容进行深入评估分析，判断其影视改编价值和市场潜力",
            "capabilities": [
                "IP价值评估",
                "改编潜力分析", 
                "市场前景评估",
                "内容质量评估",
                "改编建议提供",
                "Agent as Tool支持"
            ],
            "evaluation_dimensions": self.evaluation_dimensions,
            "adaptation_factors": self.adaptation_factors,
            "supported_formats": ["文本", "文档", "链接"],
            "output_format": "结构化评估报告"
        }

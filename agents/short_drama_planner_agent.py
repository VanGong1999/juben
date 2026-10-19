"""
竖屏短剧策划Agent
专业的竖屏短剧策划助手，基于爆款引擎理论

业务处理逻辑：
1. 输入处理：接收策划需求，支持多种输入格式和文件引用
2. 情绪价值分析：基于情绪价值第一性原理进行深度分析
3. 钩子设计：应用黄金三秒钩子法则设计开头吸引力
4. 结构设计：使用期待-压抑-爆发三幕式结构设计故事框架
5. 人设设计：基于人设即容器理论进行角色设计
6. 商业化优化：应用商业化卡点逻辑优化故事结构
7. 智能体协作：使用Agent as Tool机制调用其他专业智能体
8. 上下文隔离：确保智能体调用的独立性和准确性
9. 输出格式化：生成完整的竖屏短剧策划方案

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
import json
import re

try:
    from .base_juben_agent import BaseJubenAgent
    from ..utils.intent_recognition import IntentRecognizer
    from ..utils.url_extractor import URLExtractor
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from agents.base_juben_agent import BaseJubenAgent
    from utils.intent_recognition import IntentRecognizer
    from utils.url_extractor import URLExtractor


class ShortDramaPlannerAgent(BaseJubenAgent):
    """
    竖屏短剧策划Agent - 支持Agent as Tool机制
    
    核心功能：
    1. 情绪价值第一性原理分析
    2. 黄金三秒钩子法则应用
    3. 期待-压抑-爆发三幕式结构设计
    4. 人设即容器理论指导
    5. 商业化卡点逻辑优化
    6. Agent as Tool: 调用其他智能体作为工具
    7. 模块化外包: 智能体间相互调用，上下文隔离
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化竖屏短剧策划Agent"""
        super().__init__("short_drama_planner", model_provider)
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 初始化意图识别器
        self.intent_recognizer = IntentRecognizer()
        
        # 初始化URL提取器
        self.url_extractor = URLExtractor()
        
        # 子专家走统一 SubagentRunner；纯工具走 agent_tools harness
        self.sub_agents = {}
        self.allowed_subagents = [
            "short_drama_creator",
            "short_drama_evaluation",
            "creator",
            "evaluation",
        ]

        # 可调用能力：纯工具 + 少数子专家
        self.available_tools = {
            "web_search": "网络搜索",
            "knowledge_query": "知识库查询",
            "file_reference": "文件引用解析",
            "creator": "创作助手（子专家）",
            "evaluation": "评估分析（子专家）",
        }
        # 旧名兼容
        self._tool_aliases = {
            "websearch": "web_search",
            "knowledge": "knowledge_query",
        }

        self.logger.info("竖屏短剧策划Agent初始化完成（工具调用 + 子专家）")
    
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理竖屏短剧策划请求

        Args:
            request_data: 请求数据
            context: 上下文信息

        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            user_input = request_data.get("input", "")
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            model = context.get("model") if context else None  # 获取模型参数

            self.logger.info(f"开始处理短剧策划请求: {user_input}, model: {model}")

            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)

            # 发送开始处理事件
            yield await self._emit_event("system", "🎬 开始分析您的短剧策划需求...")

            # 1. 意图识别
            yield await self._emit_event("system", "🔍 正在分析您的需求意图...")
            intent_result = await self._analyze_intent(user_input)
            yield await self._emit_event("system", f"✅ 意图识别完成: {intent_result['intent']}")

            # 2. URL提取（如果有）
            urls = self.url_extractor.extract_urls(user_input)
            if urls:
                yield await self._emit_event("system", f"📎 发现{len(urls)}个链接，正在提取内容...")
                url_contents = await self._extract_url_contents(urls)
                yield await self._emit_event("system", "✅ URL内容提取完成")
            else:
                url_contents = []

            # 3. 智能工具调用 - Agent as Tool机制
            search_results = {}
            knowledge_results = {}
            tool_results = {}

            # 根据意图决定调用哪些工具智能体
            # 将用户输入添加到意图结果中
            intent_result["user_input"] = user_input
            tools_to_call = self._determine_tools_to_call(intent_result)

            for tool_name in tools_to_call:
                label = self.available_tools.get(tool_name, tool_name)
                yield await self._emit_event("system", f"🔧 调用工具 {label}...")

                tool_result = await self._call_agent_as_tool(tool_name, user_input, intent_result, context)
                tool_results[tool_name] = tool_result

                if tool_name in ("web_search", "websearch"):
                    search_results = tool_result
                elif tool_name in ("knowledge_query", "knowledge"):
                    knowledge_results = tool_result

                yield await self._emit_event("system", f"✅ {label} 调用完成")

            # 4. 构建上下文
            context_data = {
                "user_input": user_input,
                "intent": intent_result,
                "search_results": search_results,
                "knowledge_results": knowledge_results,
                "tool_results": tool_results,
                "url_contents": url_contents,
                "user_id": user_id,
                "session_id": session_id,
                "model": model  # 传递模型参数
            }

            # 5. 生成策划方案
            yield await self._emit_event("system", "🎭 正在生成专业的短剧策划方案...")

            async for chunk in self._generate_planning_response(context_data):
                yield chunk

            # 6. 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")

            # 7. 发送完成事件
            yield await self._emit_event("system", "🎉 短剧策划方案生成完成！")

        except Exception as e:
            self.logger.error(f"处理请求失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户意图"""
        try:
            intent_result = await self.intent_recognizer.analyze(user_input)
            return intent_result
        except Exception as e:
            self.logger.error(f"意图识别失败: {e}")
            return {
                "intent": "creation_assistance",
                "confidence": 0.5,
                "needs_web_search": False,
                "needs_knowledge_base": True
            }
    
    async def _extract_url_contents(self, urls: List[str]) -> List[Dict[str, Any]]:
        """提取URL内容"""
        contents = []
        for url in urls:
            try:
                content = await self.url_extractor.extract_content(url)
                contents.append({
                    "url": url,
                    "content": content,
                    "success": True
                })
            except Exception as e:
                self.logger.error(f"URL内容提取失败 {url}: {e}")
                contents.append({
                    "url": url,
                    "content": "",
                    "success": False,
                    "error": str(e)
                })
        return contents
    
    def _build_search_query(self, user_input: str, intent_result: Dict[str, Any]) -> str:
        """构建搜索查询"""
        intent = intent_result.get("intent", "")
        
        if intent == "web_search":
            return user_input
        elif intent == "creation_assistance":
            # 为创作辅助添加市场相关关键词
            return f"{user_input} 短剧市场趋势 热门题材"
        else:
            return user_input
    
    def _build_knowledge_query(self, user_input: str, intent_result: Dict[str, Any]) -> str:
        """构建知识库查询"""
        intent = intent_result.get("intent", "")
        
        if intent == "knowledge_base":
            return user_input
        elif intent == "creation_assistance":
            # 为创作辅助添加技巧相关关键词
            return f"{user_input} 创作技巧 剧本结构"
        else:
            return user_input
    
    async def _generate_planning_response(self, context_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """生成策划响应"""
        try:
            # 构建提示词
            prompt = self._build_planning_prompt(context_data)

            # 构建消息
            messages = [
                {"role": "user", "content": prompt}
            ]

            # 获取用户ID、会话ID和模型
            user_id = context_data.get("user_id", "unknown")
            session_id = context_data.get("session_id", "unknown")
            model = context_data.get("model")  # 获取模型参数

            # 流式调用LLM（带追踪）
            if model:
                async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id, model=model):
                    yield await self._emit_event("llm_chunk", chunk)
            else:
                async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                    yield await self._emit_event("llm_chunk", chunk)
                
        except Exception as e:
            self.logger.error(f"生成策划响应失败: {e}")
            yield await self._emit_event("error", f"生成响应失败: {str(e)}")
    
    def _build_planning_prompt(self, context_data: Dict[str, Any]) -> str:
        """构建策划提示词"""
        user_input = context_data["user_input"]
        intent = context_data["intent"]
        search_results = context_data.get("search_results", {})
        knowledge_results = context_data.get("knowledge_results", {})
        tool_results = context_data.get("tool_results", {})
        url_contents = context_data.get("url_contents", [])
        
        # 构建用户查询部分
        user_query_section = f"""
## 用户需求
{user_input}

## 需求分析
- 意图类型: {intent.get('intent', 'unknown')}
- 置信度: {intent.get('confidence', 0)}

## 市场信息
"""
        
        # 搜索 / 知识库：新 harness 返回 result(llm_text)；兼容旧 results 列表
        search_text = search_results.get("result") or ""
        if search_results.get("success") and search_text:
            user_query_section += "\n### 最新市场动态\n"
            user_query_section += f"{str(search_text)[:1200]}\n"
        elif search_results.get("success") and search_results.get("results"):
            user_query_section += "\n### 最新市场动态\n"
            for i, result in enumerate(search_results["results"][:3], 1):
                user_query_section += f"{i}. {result.get('title', '')}\n"
                user_query_section += f"   {result.get('content', '')[:200]}...\n"

        knowledge_text = knowledge_results.get("result") or ""
        if knowledge_results.get("success") and knowledge_text:
            user_query_section += "\n### 专业知识参考\n"
            user_query_section += f"{str(knowledge_text)[:1200]}\n"
        elif knowledge_results.get("success") and knowledge_results.get("results"):
            user_query_section += "\n### 专业知识参考\n"
            for i, result in enumerate(knowledge_results["results"][:3], 1):
                user_query_section += f"{i}. {result.get('title', '')}\n"
                user_query_section += f"   {result.get('content', '')[:200]}...\n"

        if tool_results:
            user_query_section += "\n### 工具调用结果\n"
            for tool_name, tool_result in tool_results.items():
                if tool_result.get("success"):
                    user_query_section += f"#### {self.available_tools.get(tool_name, tool_name)}\n"
                    body = tool_result.get("result") or tool_result.get("llm_text") or ""
                    user_query_section += f"{str(body)[:800]}\n"
        
        # 添加URL内容
        if url_contents:
            user_query_section += "\n### 参考资料\n"
            for i, content in enumerate(url_contents[:2], 1):
                if content.get("success"):
                    user_query_section += f"{i}. {content.get('url', '')}\n"
                    user_query_section += f"   {content.get('content', '')[:200]}...\n"
        
        # 将用户查询部分添加到系统提示词后面
        full_prompt = f"{self.system_prompt}\n\n{user_query_section}"
        
        return full_prompt
    
    def _determine_tools_to_call(self, intent_result: Dict[str, Any]) -> List[str]:
        """根据意图结果确定需要调用的工具智能体"""
        tools = []
        
        # 根据意图类型决定调用哪些工具
        intent = intent_result.get("intent", "")
        user_input = intent_result.get("user_input", "")
        
        # 检测文件引用
        if self._has_file_references(user_input):
            tools.append("file_reference")

        if intent == "web_search" or intent_result.get("needs_web_search", False):
            tools.append("web_search")

        if intent == "knowledge_base" or intent_result.get("needs_knowledge_base", False):
            tools.append("knowledge_query")

        if intent == "creation_assistance":
            tools.extend(["knowledge_query", "web_search"])

        return list(dict.fromkeys(tools))
    
    def _has_file_references(self, text: str) -> bool:
        """检测文本中是否包含文件引用"""
        if not text:
            return False
        
        # 检测@符号引用
        at_ref_pattern = r'@(file\d+|image\d+|document\d+|pdf\d+|excel\d+|audio\d+|video\d+)'
        if re.search(at_ref_pattern, text, re.IGNORECASE):
            return True
        
        # 检测自然语言引用
        natural_patterns = [
            r"第([一二三四五六七八九十\d]+)个文件",
            r"最新上传的(.+)",
            r"刚才上传的(.+)",
            r"那个(.+)文件",
            r"我的(.+)文件",
            r"(.+)文件"
        ]
        
        for pattern in natural_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    async def _call_agent_as_tool(self, tool_name: str, user_input: str, intent_result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        调用工具或子专家。
        纯工具（web_search / knowledge_query / file_reference）走 agent_tools harness；
        creator / evaluation 仍作为子专家。
        """
        import asyncio

        tool_name = self._tool_aliases.get(tool_name, tool_name)

        try:
            if not user_input or not isinstance(user_input, str):
                return {
                    "success": False,
                    "error": f"无效的用户输入: {type(user_input).__name__}",
                    "tool_name": tool_name,
                }

            # —— 纯工具：ToolDefinition.execute ——
            if tool_name in ("web_search", "knowledge_query", "file_reference"):
                from utils.agent_tools import ToolContext, get_tool_harness

                harness = get_tool_harness()
                params: Dict[str, Any] = {}
                if tool_name in ("web_search", "knowledge_query"):
                    params = {"query": user_input, "top_k": 5}
                elif tool_name == "file_reference":
                    # 启发式取路径；否则把整段文本当说明返回失败提示
                    m = re.search(r"(projects/[^\s]+|skills/[^\s]+|[\w./-]+\.(?:md|txt|json))", user_input)
                    if not m:
                        return {
                            "success": False,
                            "error": "未识别到可引用文件路径",
                            "tool_name": tool_name,
                        }
                    params = {"path": m.group(1)}

                ctx = ToolContext(
                    user_id=(context or {}).get("user_id", "unknown"),
                    session_id=(context or {}).get("session_id"),
                    drama_id=(context or {}).get("drama_id") or (context or {}).get("project_id"),
                    agent_id="short_drama_planner",
                )
                packed = await asyncio.wait_for(
                    harness.execute(tool_name, params, ctx=ctx),
                    timeout=60,
                )
                return {
                    "success": packed.get("success", False),
                    "tool_name": tool_name,
                    "result": packed.get("llm_text") or "",
                    "details": (packed.get("result") or {}).get("details"),
                    "error": packed.get("error"),
                }

            # —— 子专家：统一 spawn_subagent ——
            if tool_name in ("creator", "evaluation", "short_drama_creator", "short_drama_evaluation"):
                depth = int((context or {}).get("subagent_depth") or 0)
                return await self.spawn_subagent(
                    tool_name,
                    user_input,
                    context=context,
                    timeout=120,
                    depth=depth,
                )

            return {
                "success": False,
                "error": f"无法获取子专家: {tool_name}",
                "tool_name": tool_name,
            }

        except ValueError as e:
            self.logger.error(f"工具调用参数错误: {e}")
            return {"success": False, "error": f"参数错误: {str(e)}", "tool_name": tool_name}
        except Exception as e:
            self.logger.error(f"调用工具 {tool_name} 失败: {e}")
            return {"success": False, "error": str(e), "tool_name": tool_name}

    async def _get_tool_agent(self, agent_name: str):
        """兼容旧调用：优先走 spawn；保留延迟加载作后备。"""
        alias = {
            "creator": "short_drama_creator",
            "evaluation": "short_drama_evaluation",
        }.get(agent_name, agent_name)
        if agent_name not in self.sub_agents and alias not in self.sub_agents:
            try:
                if agent_name in ("creator", "short_drama_creator"):
                    from .short_drama_creator_agent import ShortDramaCreatorAgent
                    self.sub_agents["creator"] = ShortDramaCreatorAgent()
                elif agent_name in ("evaluation", "short_drama_evaluation"):
                    from .short_drama_evaluation_agent import ShortDramaEvaluationAgent
                    self.sub_agents["evaluation"] = ShortDramaEvaluationAgent()
                else:
                    self.logger.error(f"未知的子专家类型: {agent_name}")
                    return None
                self.logger.info(f"子专家 {agent_name} 加载成功")
            except Exception as e:
                self.logger.error(f"加载子专家 {agent_name} 失败: {e}")
                return None
        return self.sub_agents.get(agent_name) or self.sub_agents.get(
            "creator" if "creator" in agent_name else "evaluation"
        )
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "short_drama_planner",
            "capabilities": [
                "情绪价值分析",
                "黄金三秒钩子设计",
                "三幕式结构规划",
                "人设容器设计",
                "商业化卡点设置",
                "专业策划方案生成",
                "工具调用（web_search / knowledge_query）",
                "子专家协作（creator / evaluation）",
            ],
            "supported_intents": [
                "creation_assistance",
                "web_search",
                "knowledge_base",
                "url_extraction",
            ],
            "available_tools": self.available_tools,
            "tool_harness": "agent_tools",
        })
        return base_info

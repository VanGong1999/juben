"""
已播剧集分析与拉工作流智能体
基于Coze工作流设计的剧集分析系统，支持剧名提取、剧集信息获取、联网搜索、拉片分析等功能

业务处理逻辑：
1. 输入处理：接收剧集相关信息，支持多种输入格式
2. 剧名提取：从输入文本中智能提取剧集名称
3. 剧集信息获取：通过SeriesInfoClient获取详细的剧集信息
4. 联网搜索：使用WebSearchAgent进行相关信息的网络搜索
5. 拉片分析：对剧集内容进行专业的拉片分析
6. 多智能体协作：协调多个专业智能体完成复杂分析任务
7. 结果整合：汇总各个智能体的分析结果
8. 输出格式化：生成完整的剧集分析报告
9. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2024年10月19日
"""
import asyncio
import re
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
import json

try:
    from .base_juben_agent import BaseJubenAgent
    from ..utils.intent_recognition import IntentRecognizer
    from ..utils.series_info_client import SeriesInfoClient
    from ..utils.text_processor import TextSplitter
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from agents.base_juben_agent import BaseJubenAgent
    from utils.intent_recognition import IntentRecognizer
    from utils.series_info_client import SeriesInfoClient
    from utils.text_processor import TextSplitter


class SeriesAnalysisAgent(BaseJubenAgent):
    """
    已播剧集分析与拉工作流智能体 - 支持Agent as Tool机制
    
    核心功能：
    1. 意图识别 - 判断用户输入是否包含电视剧名称
    2. 剧名提取 - 从用户输入中精准提取电视剧剧名
    3. 剧集信息获取 - 获取剧集基础信息和分集剧情
    4. 联网搜索 - 获取最新的剧集相关信息
    5. 拉片分析 - 分析各集的情节点和戏剧功能
    6. 故事五元素分析 - 集成故事五元素工作流
    7. 结果整合 - 整合所有分析结果
    8. Agent as Tool: 调用其他智能体作为工具
    9. 模块化外包: 智能体间相互调用，上下文隔离
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化已播剧集分析智能体"""
        super().__init__("series_analysis", model_provider)
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 初始化工具
        self.intent_recognizer = IntentRecognizer()
        self.series_info_client = SeriesInfoClient()
        self.text_splitter = TextSplitter()
        
        # Agent as Tool机制 - 子智能体注册表（延迟加载）
        self.sub_agents = {}
        
        # 可调用的工具智能体映射
        self.available_tools = {
            "websearch": "网络搜索工具",
            "story_five_elements": "故事五元素分析工具",
            "series_name_extractor": "剧名提取智能体",
            "series_info_analyzer": "剧集信息分析智能体",
            "episode_analysis": "拉片分析智能体"
        }
        
        self.logger.info("已播剧集分析智能体初始化完成（支持Agent as Tool机制）")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理已播剧集分析请求
        
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
            
            self.logger.info(f"开始已播剧集分析请求: {user_input[:100]}...")
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 发送开始处理事件
            yield await self._emit_event("system", "📺 开始已播剧集分析...")
            
            # 1. 意图识别
            yield await self._emit_event("system", "🔍 正在进行意图识别...")
            intent_result = await self._analyze_intent(user_input)
            yield await self._emit_event("system", f"✅ 意图识别完成: {intent_result.get('intent', 'unknown')}")
            
            # 2. 剧名提取
            if intent_result.get("has_series_name", False):
                yield await self._emit_event("system", "📝 正在提取剧集名称...")
                series_name = await self._extract_series_name(user_input)
                yield await self._emit_event("system", f"✅ 剧名提取完成: {series_name}")
                
                # 3. 并发执行三个主要任务
                yield await self._emit_event("system", "🔄 开始并发分析任务...")
                
                # 3.1 剧集信息获取
                series_info_task = asyncio.create_task(
                    self._get_series_info(series_name, context)
                )
                
                # 3.2 联网搜索
                web_search_task = asyncio.create_task(
                    self._web_search_series(series_name, context)
                )
                
                # 3.3 故事五元素分析（如果有分集剧情）
                five_elements_task = None
                
                # 等待剧集信息获取完成
                series_info_result = await series_info_task
                if series_info_result.get("success") and series_info_result.get("tv_episode_plot"):
                    # 启动故事五元素分析
                    five_elements_task = asyncio.create_task(
                        self._analyze_five_elements(series_info_result["tv_episode_plot"], context)
                    )
                
                # 等待联网搜索完成
                web_search_result = await web_search_task
                
                # 等待故事五元素分析完成（如果启动了）
                five_elements_result = None
                if five_elements_task:
                    five_elements_result = await five_elements_task
                
                # 4. 章节切分和拉片分析
                episode_analysis_result = None
                if series_info_result.get("success") and series_info_result.get("tv_episode_plot"):
                    yield await self._emit_event("system", "📚 正在进行章节切分...")
                    episodes = await self._split_episodes(series_info_result["tv_episode_plot"])
                    yield await self._emit_event("system", f"✅ 章节切分完成，共 {len(episodes)} 集")
                    
                    yield await self._emit_event("system", "🎬 正在进行拉片分析...")
                    episode_analysis_result = await self._analyze_episodes(episodes, context)
                    yield await self._emit_event("system", "✅ 拉片分析完成")
                
                # 5. 整合结果
                yield await self._emit_event("system", "📋 正在整合分析结果...")
                final_result = await self._integrate_results(
                    series_info_result, 
                    web_search_result, 
                    episode_analysis_result,
                    five_elements_result,
                    series_info_result.get("tv_episode_plot", "")
                )
                
                # 6. 流式输出最终结果
                yield await self._emit_event("system", "🎉 已播剧集分析完成！")
                yield await self._emit_event("final_result", final_result)
                
            else:
                # 如果没有剧集名称，直接调用大模型回复
                yield await self._emit_event("system", "💬 正在生成回复...")
                async for chunk in self._generate_direct_response(user_input, context):
                    yield chunk
            
            # 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")
            
        except Exception as e:
            self.logger.error(f"已播剧集分析失败: {e}")
            yield await self._emit_event("error", f"分析失败: {str(e)}")
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户意图"""
        try:
            # 检测是否包含剧集名称
            has_series_name = self._detect_series_name(user_input)
            
            return {
                "intent": "series_analysis" if has_series_name else "general_chat",
                "has_series_name": has_series_name,
                "confidence": 0.9 if has_series_name else 0.5
            }
        except Exception as e:
            self.logger.error(f"意图识别失败: {e}")
            return {
                "intent": "general_chat",
                "has_series_name": False,
                "confidence": 0.3
            }
    
    def _detect_series_name(self, text: str) -> bool:
        """检测文本中是否包含剧集名称"""
        # 检测常见的剧集名称模式
        patterns = [
            r'《[^》]+》',  # 《剧名》格式
            r'"[^"]+"',     # "剧名"格式
            r'[《"]\s*[^》"]+\s*[》"]',  # 带空格的格式
            r'(电视剧|剧集|连续剧|短剧|网剧).*?(好看|评价|分析|剧情)',  # 包含剧集相关词汇
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    async def _extract_series_name(self, user_input: str) -> str:
        """提取剧集名称"""
        try:
            # 构建剧名提取提示词
            extract_prompt = f"""
# 角色
你是一个专注的剧集名称提取员，能够从用户输入信息中精准提取电视剧剧名。

## 技能
### 技能 1: 提取电视剧剧名
1. 当用户输入包含电视剧剧名的信息时，直接输出电视剧剧名。例如用户输入"《去有风的地方》好看吗"，输出"去有风的地方"；若输入"帮我搜一下去有风的地方"，同样输出"去有风的地方"。

## 限制:
- 只输出电视剧剧名，拒绝回答与提取电视剧剧名无关的话题。
- 输出内容需简洁，仅为电视剧剧名。

## 用户输入：
{user_input}
"""
            
            # 调用LLM提取剧名
            messages = [{"role": "user", "content": extract_prompt}]
            series_name = await self._call_llm(messages, "unknown", "unknown")
            
            # 清理提取的剧名
            series_name = series_name.strip()
            series_name = re.sub(r'^["《]|["》]$', '', series_name)  # 移除引号和书名号
            series_name = series_name.strip()
            
            return series_name if series_name else "未知剧集"
        except Exception as e:
            self.logger.error(f"剧名提取失败: {e}")
            return "未知剧集"
    
    async def _get_series_info(self, series_name: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """获取剧集信息"""
        try:
            result = await self.series_info_client.get_series_info(series_name)
            return result
        except Exception as e:
            self.logger.error(f"获取剧集信息失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "tv_info": "",
                "tv_episode_plot": ""
            }
    
    async def _web_search_series(self, series_name: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """联网搜索剧集信息（增强版：带超时控制）"""
        import asyncio

        try:
            # ========== 参数验证 ==========
            if not series_name or not isinstance(series_name, str):
                return {
                    "success": False,
                    "error": "剧集名称为空或类型不正确",
                    "results": ""
                }

            # 调用网络搜索智能体
            websearch_agent = await self._get_sub_agent("websearch")
            if websearch_agent:
                search_request = {
                    "input": f"{series_name} 电视剧 剧情 评价 分析",
                    "query": f"{series_name} 电视剧 剧情 评价 分析"
                }

                search_context = {
                    "user_id": context.get("user_id", "unknown") if context else "unknown",
                    "session_id": context.get("session_id", "unknown") if context else "unknown",
                    "parent_agent": "series_analysis",
                    "tool_call": True
                }

                # 收集搜索结果（带超时）
                results = []

                async def collect_results():
                    async for event in websearch_agent.process_request(search_request, search_context):
                        if event.get("event_type") == "llm_chunk":
                            results.append(event.get("data", ""))

                # 使用超时控制
                try:
                    await asyncio.wait_for(collect_results(), timeout=60)
                except asyncio.TimeoutError:
                    self.logger.error(f"网络搜索智能体调用超时(60秒): {series_name}")
                    return {
                        "success": False,
                        "error": "搜索超时(60秒)",
                        "results": ""
                    }

                return {
                    "success": True,
                    "results": "".join(results)
                }
            else:
                return {
                    "success": False,
                    "error": "无法获取网络搜索智能体",
                    "results": ""
                }
        except ValueError as e:
            self.logger.error(f"联网搜索参数错误: {e}")
            return {
                "success": False,
                "error": f"参数错误: {str(e)}",
                "results": ""
            }
        except Exception as e:
            self.logger.error(f"联网搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": ""
            }

    async def _analyze_five_elements(self, episode_plot: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """故事五元素分析（增强版：带超时控制）"""
        import asyncio

        try:
            # ========== 参数验证 ==========
            if not episode_plot or not isinstance(episode_plot, str):
                return {
                    "success": False,
                    "error": "剧集情节为空或类型不正确",
                    "results": ""
                }

            # 调用故事五元素分析智能体
            five_elements_agent = await self._get_sub_agent("story_five_elements")
            if five_elements_agent:
                analysis_request = {
                    "input": episode_plot,
                    "file": None,
                    "chunk_size": 10000,
                    "length_size": 50000
                }

                analysis_context = {
                    "user_id": context.get("user_id", "unknown") if context else "unknown",
                    "session_id": context.get("session_id", "unknown") if context else "unknown",
                    "parent_agent": "series_analysis",
                    "tool_call": True
                }

                # 收集分析结果（带超时）
                results = []

                async def collect_results():
                    async for event in five_elements_agent.process_request(analysis_request, analysis_context):
                        if event.get("event_type") == "llm_chunk":
                            results.append(event.get("data", ""))

                # 使用超时控制
                try:
                    await asyncio.wait_for(collect_results(), timeout=180)
                except asyncio.TimeoutError:
                    self.logger.error("故事五元素分析智能体调用超时(180秒)")
                    return {
                        "success": False,
                        "error": "分析超时(180秒)",
                        "results": ""
                    }

                return {
                    "success": True,
                    "results": "".join(results)
                }
            else:
                return {
                    "success": False,
                    "error": "无法获取故事五元素分析智能体",
                    "results": ""
                }
        except ValueError as e:
            self.logger.error(f"故事五元素分析参数错误: {e}")
            return {
                "success": False,
                "error": f"参数错误: {str(e)}",
                "results": ""
            }
        except Exception as e:
            self.logger.error(f"故事五元素分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": ""
            }
    
    async def _split_episodes(self, episode_plot: str) -> List[str]:
        """章节切分"""
        try:
            # 使用正则表达式切分章节
            pattern = r'第\s*(\d+)\s*集[:]?'
            episodes = re.split(pattern, episode_plot)
            
            # 重新组织章节
            result = []
            for i in range(1, len(episodes), 2):
                if i + 1 < len(episodes):
                    episode_num = episodes[i]
                    episode_content = episodes[i + 1]
                    if episode_content.strip():
                        result.append(f"第{episode_num}集: {episode_content.strip()}")
            
            return result
        except Exception as e:
            self.logger.error(f"章节切分失败: {e}")
            return [episode_plot]
    
    async def _analyze_episodes(self, episodes: List[str], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """拉片分析"""
        try:
            # 构建拉片分析提示词
            analysis_prompt = f"""
## Role: 资深的编剧

## Profile:
- language: 中文
- description: 深入分析一段故事文本的内容，根据情节点的定义，总结提炼其中主要的情节点，并对情节点在整个故事中的功能进行分析。

## Background:
- 用户拥有一段故事文本，想要知道故事中有哪些情节点并想要了解这些情节点在故事中发挥了什么戏剧上的作用与功能，现在需要你来帮忙总结、分析，从而帮助用于清楚地了解故事文本的脉络与结构。

## Definition1
- "情节点"是一个编剧概念，其具体定义如下：指故事中的关键情节或事件，它们对于情节发展和角色之间的情感关系具有重要的影响，通常是故事中的转折点，能够引发剧情的变化、冲突的升级或者角色的成长。

## Definition2
- "戏剧功能"是一个编剧概念，其具体定义如下：是指情节在故事中的作用和影响。它往往能帮助推动故事发展，塑造角色，揭示主题，创造冲突或紧张，并激发观众或读者的兴趣和情感反应。情节通过这些方式来提升故事的质量和效果，使其更具吸引力。

## Goals:
- 对提供的故事文本进行深入的阅读与理解，总结其中主要的情节点。
- 对总结的情节点的戏剧功能进行分析，为用户提供参考。

## Constrains:
- 你要控制对每个情节点的表述不要超过100个字，但不要暴露你的字数。
- 所总结的情节点最少不得少于五个。
- 请严格按照故事文本原文所表达的意思总结情节点，不要自行进行创作与改编。
- 阅读文本要避免幻觉，不要将提示词内的词句带进生成的答案中。
- 不要使用阿拉伯数字为情节点标号。

## Skills:
- 善于理解抽象的编剧概念，并应用于故事文本的阅历于理解中。
- 对于故事的脉络与结构有着深刻的理解与洞察。
- 有着高潮的编剧理论与编剧技巧，明白戏剧功能的各项维度与意义。

## Workflows:
- 第一步，你作为一位资深的故事编辑，你将对由我提供的故事文本进行充分的阅读。
- 第二步，根据，「Definition1」中对情节点的介绍，你要对文本进行分析与提炼，总结出故事文本中的情节点，并结合「Definition2」中对戏剧功能的介绍，分析每个情节点的戏剧功能。

## OutputFormat:
【情节点】：<列出总结的单个情节点。>
【戏剧功能】：<对以上情节点的戏剧功能进行分析总结。>

【情节点】：<列出总结的单个情节点。>
【戏剧功能】：<对以上情节点的戏剧功能进行分析总结。>
……依次类推，直到介绍完故事文本中所有你认为的情节点.，情节点不得少于五个。

以下是用户输入的电视剧各分集剧情
-----------------------------------------------
{chr(10).join(episodes[:5])}  # 只分析前5集避免过长
"""
            
            # 调用LLM进行拉片分析
            messages = [{"role": "user", "content": analysis_prompt}]
            analysis_result = await self._call_llm(messages, "unknown", "unknown")
            
            return {
                "success": True,
                "results": analysis_result
            }
        except Exception as e:
            self.logger.error(f"拉片分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": ""
            }
    
    async def _integrate_results(
        self, 
        series_info_result: Dict[str, Any],
        web_search_result: Dict[str, Any], 
        episode_analysis_result: Dict[str, Any],
        five_elements_result: Optional[Dict[str, Any]],
        episode_plot: str
    ) -> str:
        """整合所有分析结果"""
        try:
            # 构建最终结果
            final_result = "# 剧集信息\n"
            if series_info_result.get("success") and series_info_result.get("tv_info"):
                final_result += series_info_result["tv_info"] + "\n\n"
            else:
                final_result += "剧集信息获取失败\n\n"
            
            # 故事五元素分析结果
            if five_elements_result and five_elements_result.get("success"):
                final_result += "# 五元素分析\n"
                final_result += five_elements_result["results"] + "\n\n"
            else:
                final_result += "# 五元素分析\n"
                final_result += "故事五元素分析失败或未执行\n\n"
            
            # 拉片分析结果
            if episode_analysis_result and episode_analysis_result.get("success"):
                final_result += "# 拉片分析\n"
                final_result += episode_analysis_result["results"] + "\n\n"
            else:
                final_result += "# 拉片分析\n"
                final_result += "拉片分析失败\n\n"
            
            # 联网搜索结果
            if web_search_result and web_search_result.get("success"):
                final_result += "# 联网搜索信息\n"
                final_result += web_search_result["results"] + "\n\n"
            else:
                final_result += "# 联网搜索信息\n"
                final_result += "联网搜索失败\n\n"
            
            # 分集剧情
            if episode_plot:
                final_result += "# 分集剧情\n"
                final_result += episode_plot + "\n\n"
            
            return final_result
        except Exception as e:
            self.logger.error(f"结果整合失败: {e}")
            return f"结果整合失败: {str(e)}"
    
    async def _generate_direct_response(self, user_input: str, context: Optional[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """生成直接回复"""
        try:
            # 构建回复提示词
            response_prompt = f"""
你是一个专业的剧集分析助手，能够帮助用户分析电视剧、提供剧集信息、进行拉片分析等。

请根据用户的问题提供专业、准确的回答。

用户问题：{user_input}
"""
            
            # 构建消息
            messages = [
                {"role": "user", "content": response_prompt}
            ]
            
            # 获取用户ID和会话ID
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            
            # 流式调用LLM
            async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                yield await self._emit_event("llm_chunk", chunk)
                
        except Exception as e:
            self.logger.error(f"生成直接回复失败: {e}")
            yield await self._emit_event("error", f"生成回复失败: {str(e)}")
    
    async def _get_sub_agent(self, agent_name: str):
        """获取子智能体实例（延迟加载）"""
        if agent_name not in self.sub_agents:
            try:
                if agent_name == "websearch":
                    from .websearch_agent import WebSearchAgent
                    self.sub_agents[agent_name] = WebSearchAgent()
                elif agent_name == "story_five_elements":
                    from .story_five_elements_agent import StoryFiveElementsAgent
                    self.sub_agents[agent_name] = StoryFiveElementsAgent()
                else:
                    self.logger.error(f"未知的子智能体类型: {agent_name}")
                    return None
                
                self.logger.info(f"子智能体 {agent_name} 加载成功")
                
            except Exception as e:
                self.logger.error(f"加载子智能体 {agent_name} 失败: {e}")
                return None
        
        return self.sub_agents[agent_name]
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "series_analysis",
            "capabilities": [
                "意图识别",
                "剧名提取",
                "剧集信息获取",
                "联网搜索",
                "拉片分析",
                "故事五元素分析",
                "章节切分",
                "结果整合",
                "Agent as Tool机制",
                "智能体间相互调用"
            ],
            "supported_intents": [
                "series_analysis",
                "general_chat"
            ],
            "available_tools": self.available_tools,
            "agent_as_tool_enabled": True
        })
        return base_info

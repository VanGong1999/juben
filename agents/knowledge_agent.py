"""
竖屏短剧知识库查询智能体
 专注于知识库查询和信息检索

业务处理逻辑：
1. 输入处理：接收查询请求，支持多种查询格式和意图识别
2. 意图识别：使用IntentRecognizer分析用户查询意图
3. URL提取：从查询中提取相关的URL链接信息
4. 知识库查询：在竖屏短剧知识库中进行信息检索
5. 信息过滤：根据查询意图过滤和排序检索结果
6. 内容生成：基于检索结果生成结构化的回答
7. 上下文管理：维护查询历史和上下文信息
8. 输出格式化：返回结构化的知识库查询结果
9. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2024年10月19日
"""
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import json

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


class KnowledgeAgent(BaseJubenAgent):
    """
    竖屏短剧知识库查询智能体
    
    功能：
    1. 知识库语义搜索
    2. 专业知识提取
    3. 知识内容总结
    4. 多集合查询支持
    5. 知识推荐和关联
    """
    
    def __init__(self):
        super().__init__("knowledge", model_provider="deepseek")
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 初始化专用组件
        self.intent_recognizer = IntentRecognizer()
        self.url_extractor = URLExtractor()
        
        # 知识库配置
        self.knowledge_config = {
            "default_collection": "script_segments",
            "available_collections": [
                "script_segments",      # 剧本桥段库
                "drama_highlights"      # 短剧高能情节库
            ],
            "default_top_k": 5,
            "max_top_k": 20
        }
        
        self.logger.info("竖屏短剧知识库查询智能体初始化完成")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理知识库查询请求
        
        Args:
            request_data: 请求数据
            context: 上下文信息
            
        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            query = request_data.get("query", request_data.get("input", ""))
            instruction = request_data.get("instruction", query)
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            collection = request_data.get("collection", self.knowledge_config["default_collection"])
            top_k = request_data.get("top_k", self.knowledge_config["default_top_k"])
            
            self.logger.info(f"开始处理知识库查询请求: {instruction}")
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 发送开始处理事件
            yield await self._emit_event("system", f"📚 开始知识库查询: {instruction}")
            
            # 1. 意图识别
            yield await self._emit_event("system", "🔍 正在分析查询意图...")
            intent_result = await self._analyze_intent(instruction)
            yield await self._emit_event("system", f"✅ 意图识别完成: {intent_result['intent']}")
            
            # 2. URL提取和内容获取
            urls = self.url_extractor.extract_urls(instruction)
            url_contents = []
            if urls:
                yield await self._emit_event("system", f"📎 发现{len(urls)}个链接，正在提取内容...")
                url_contents = await self._extract_url_contents(urls)
                yield await self._emit_event("system", "✅ URL内容提取完成")
            
            # 3. 知识库查询
            yield await self._emit_event("system", "📚 正在查询知识库...")
            knowledge_results = await self._search_knowledge_base(instruction, collection=collection, top_k=top_k)
            yield await self._emit_event("system", "✅ 知识库查询完成")
            
            # 4. 格式化知识库结果
            formatted_results = self._format_knowledge_results(knowledge_results, instruction)
            
            # 5. 发送知识库查询结果
            yield await self._emit_event("knowledge_results", formatted_results)
            
            # 6. 智能总结知识内容
            if formatted_results:
                yield await self._emit_event("system", "📝 正在分析和总结知识内容...")
                
                async for chunk in self._generate_knowledge_summary(instruction, knowledge_results, user_id, session_id):
                    yield chunk
                
                yield await self._emit_event("system", "✅ 知识内容总结完成")
            
            # 7. 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")
            
            # 8. 发送完成事件
            yield await self._emit_event("system", "🎯 知识库查询任务完成！")
            
        except Exception as e:
            self.logger.error(f"处理知识库查询请求失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户查询意图"""
        try:
            # 知识库相关的意图识别
            intent_result = await self.intent_recognizer.analyze(user_input)
            
            # 根据查询需求调整意图
            if "剧本" in user_input or "桥段" in user_input or "情节" in user_input:
                intent_result.update({
                    "intent": "script_knowledge",
                    "needs_knowledge_base": True,
                    "needs_web_search": False,
                    "preferred_collection": "script_segments"
                })
            elif "高能" in user_input or "爆点" in user_input or "爽点" in user_input:
                intent_result.update({
                    "intent": "drama_highlights",
                    "needs_knowledge_base": True,
                    "needs_web_search": False,
                    "preferred_collection": "drama_highlights"
                })
            elif "知识" in user_input or "查询" in user_input or "检索" in user_input:
                intent_result.update({
                    "intent": "general_knowledge",
                    "needs_knowledge_base": True,
                    "needs_web_search": False
                })
            elif "技巧" in user_input or "方法" in user_input or "经验" in user_input:
                intent_result.update({
                    "intent": "skill_knowledge",
                    "needs_knowledge_base": True,
                    "needs_web_search": False
                })
            
            return intent_result
        except Exception as e:
            self.logger.error(f"意图识别失败: {e}")
            return {
                "intent": "general_knowledge",
                "confidence": 0.5,
                "needs_knowledge_base": True,
                "needs_web_search": False
            }
    
    async def _extract_url_contents(self, urls: List[str]) -> List[Dict[str, Any]]:
        """提取URL内容"""
        contents = []
        for url in urls:
            try:
                content = await self.url_extractor.extract_content(url)
                contents.append(content)
            except Exception as e:
                self.logger.error(f"提取URL内容失败 {url}: {e}")
                contents.append({
                    "url": url,
                    "success": False,
                    "error": str(e)
                })
        return contents
    
    def _format_knowledge_results(self, knowledge_results: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """格式化知识库查询结果"""
        formatted_results = []
        
        if not knowledge_results.get("success", False):
            return formatted_results
        
        raw_results = knowledge_results.get("results", [])
        # 兼容 BaseJubenAgent 返回结构：
        # {"success": True, "results": {"success": True, "results": [...]}}
        if isinstance(raw_results, dict):
            results = raw_results.get("results", []) or []
        else:
            results = raw_results or []
        
        for i, result in enumerate(results):
            formatted_result = {
                "id": f"knowledge_{i+1}",
                "type": "knowledge",
                "title": result.get("title", f"知识点 {i+1}"),
                "content": result.get("content", ""),
                "similarity": result.get("similarity", 0.0),
                "source": result.get("source", ""),
                "chunk_index": result.get("chunk_index", 0)
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _extract_knowledge_content(self, knowledge_results: Dict[str, Any]) -> str:
        """从知识库查询结果中提取文本内容用于总结"""
        content_list = []
        
        if not knowledge_results.get("success", False):
            return "无知识库查询结果"
        
        raw_results = knowledge_results.get("results", [])
        if isinstance(raw_results, dict):
            results = raw_results.get("results", []) or []
        else:
            results = raw_results or []
        
        for i, result in enumerate(results):
            title = result.get("title", f"知识点 {i+1}")
            content = result.get("content", "")
            similarity = result.get("similarity", 0.0)
            source = result.get("source", "")
            
            result_text = f"知识点{i+1}:\n标题: {title}\n相似度: {similarity:.2f}\n来源: {source}\n内容: {content}\n"
            content_list.append(result_text)
        
        return "\n".join(content_list)
    
    def _build_knowledge_summary_prompt(self, original_query: str, knowledge_content: str) -> str:
        """构建知识总结的用户提示词"""
        return f"""用户查询需求: {original_query}

以下是知识库查询返回的结果:
{knowledge_content}

请根据用户的查询需求，将上述知识库内容整理为数个有用的知识点。每个知识点应该有完整的背景、方法和应用场景，而不是碎片化的信息。使用合适的颗粒度进行整理。

要求：
1. 保持知识的准确性和专业性
2. 按照逻辑顺序组织知识点
3. 突出与查询需求最相关的内容
4. 提供实用的建议和技巧
5. 确保内容的完整性和可操作性
"""
    
    async def _generate_knowledge_summary(self, query: str, knowledge_results: Dict[str, Any], user_id: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """生成知识总结"""
        try:
            # 构建总结提示词
            knowledge_content = self._extract_knowledge_content(knowledge_results)
            user_prompt = self._build_knowledge_summary_prompt(query, knowledge_content)
            
            # 构建消息
            messages = [
                {"role": "user", "content": user_prompt}
            ]
            
            # 流式调用LLM（带追踪）
            async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                yield await self._emit_event("llm_chunk", chunk)
                
        except Exception as e:
            self.logger.error(f"生成知识总结失败: {e}")
            yield await self._emit_event("error", f"生成总结失败: {str(e)}")
    
    def get_available_collections(self) -> List[Dict[str, str]]:
        """获取可用的知识库集合"""
        collections = []
        for collection_name in self.knowledge_config["available_collections"]:
            if collection_name == "script_segments":
                collections.append({
                    "name": collection_name,
                    "display_name": "剧本桥段库",
                    "description": "包含各种经典剧本桥段和情节模板"
                })
            elif collection_name == "drama_highlights":
                collections.append({
                    "name": collection_name,
                    "display_name": "短剧高能情节库",
                    "description": "包含短剧中的高能情节和爆点设计"
                })
        return collections
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "knowledge",
            "description": "竖屏短剧知识库查询智能体，专注于知识库查询和信息检索",
            "capabilities": [
                "知识库语义搜索",
                "专业知识提取",
                "知识内容总结",
                "多集合查询支持",
                "知识推荐和关联"
            ],
            "knowledge_config": self.knowledge_config,
            "available_collections": self.get_available_collections()
        })
        return base_info

"""
已播剧集分析与拉工作流 - 剧集名称提取智能体
 提供剧集名称提取服务
"""

import re
from typing import Dict, Any, Optional
from .base_juben_agent import BaseJubenAgent


class SeriesNameExtractorAgent(BaseJubenAgent):
    """剧集名称提取智能体"""
    
    def __init__(self, model_provider: str = "deepseek"):
        super().__init__("series_name_extractor", model_provider)
        self._load_series_name_extractor_prompt()
    
    def _load_series_name_extractor_prompt(self) -> str:
        """加载剧集名称提取提示词"""
        return """
# 角色
你是一个专注的剧集名称提取员，能够从用户输入信息中精准提取电视剧剧名。

## 技能
### 技能 1: 提取电视剧剧名
1. 当用户输入包含电视剧剧名的信息时，直接输出电视剧剧名。例如用户输入"《去有风的地方》好看吗"，输出"去有风的地方"；若输入"帮我搜一下去有风的地方"，同样输出"去有风的地方"。

## 限制:
- 只输出电视剧剧名，拒绝回答与提取电视剧剧名无关的话题。
- 输出内容需简洁，仅为电视剧剧名。
"""
    
    async def extract_series_name(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """提取剧集名称"""
        try:
            # 构建请求数据
            request_data = {
                "message": user_input,
                "context": context or {}
            }
            
            # 处理请求
            result = await self._process_request(request_data, context)
            
            return {
                "success": True,
                "series_name": result.get("content", "").strip(),
                "original_input": user_input
            }
            
        except Exception as e:
            self.logger.error(f"提取剧集名称失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "series_name": "",
                "original_input": user_input
            }
    
    async def process_request(self, request_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """处理剧集名称提取请求"""
        try:
            user_input = request_data.get("message", "")
            
            # 使用正则表达式提取可能的剧集名称
            series_name = self._extract_series_name_regex(user_input)
            
            if series_name:
                return {
                    "content": series_name,
                    "extraction_method": "regex"
                }
            
            # 如果正则提取失败，使用LLM提取
            return await self._extract_with_llm(user_input, context)
            
        except Exception as e:
            self.logger.error(f"处理剧集名称提取请求失败: {str(e)}")
            raise
    
    def _extract_series_name_regex(self, text: str) -> str:
        """使用正则表达式提取剧集名称"""
        # 匹配《》中的内容
        pattern1 = r'《([^》]+)》'
        match1 = re.search(pattern1, text)
        if match1:
            return match1.group(1)
        
        # 匹配常见的剧集名称模式
        patterns = [
            r'《([^》]+)》',
            r'电视剧《([^》]+)》',
            r'剧集《([^》]+)》',
            r'《([^》]+)》好看吗',
            r'《([^》]+)》怎么样',
            r'《([^》]+)》评价'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return ""
    
    async def _extract_with_llm(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """使用LLM提取剧集名称"""
        try:
            # 构建提示词
            system_prompt = self._load_series_name_extractor_prompt()
            user_prompt = f"用户输入：{user_input}"
            
            # 调用LLM
            response = await self._call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context=context
            )
            
            return {
                "content": response.strip(),
                "extraction_method": "llm"
            }
            
        except Exception as e:
            self.logger.error(f"LLM提取剧集名称失败: {str(e)}")
            return {
                "content": "",
                "extraction_method": "llm_failed",
                "error": str(e)
            }

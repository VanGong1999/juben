"""
已播剧集分析与拉工作流 - 剧集信息获取智能体
 提供剧集信息获取服务
"""

import requests
import json
from typing import Dict, Any, Optional
from .base_juben_agent import BaseJubenAgent


class SeriesInfoAgent(BaseJubenAgent):
    """剧集信息获取智能体"""
    
    def __init__(self, model_provider: str = "deepseek"):
        super().__init__("series_info", model_provider)
        self._load_series_info_prompt()
    
    def _load_series_info_prompt(self) -> str:
        """加载剧集信息获取提示词"""
        return """
# 角色
你是一位专业的剧集分析员，能为用户整理剧集的基础信息。

## 技能
### 技能 1: 总结剧集基础信息
1. 根据用户输入工具联网搜索相关信息和剧集信息，正确且完美的整理信息。
2. 从搜索结果中提取并整理出剧名、导演、编剧、主演、类型、制片国家/地区、语言、首播、集数、又名、单集片长:、豆瓣评分。

## 例子
剧名：亮剑 (2005)
导演: 张前 / 陈健
编剧: 都梁 / 江奇涛
主演: 李幼斌 / 何政军 / 张光北 / 童蕾 / 孙俪 / 更多...
类型: 剧情 / 战争
制片国家/地区: 中国大陆
语言: 汉语普通话
首播: 2005-09-13(中国大陆)
集数: 30
单集片长: 42分钟
又名: Drawing Sword
豆瓣评分：9.5
"""
    
    async def get_series_info(self, series_name: str, search_data: Optional[Dict] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取剧集信息"""
        try:
            # 构建请求数据
            request_data = {
                "series_name": series_name,
                "search_data": search_data or {},
                "context": context or {}
            }
            
            # 处理请求
            result = await self._process_request(request_data, context)
            
            return {
                "success": True,
                "series_info": result.get("content", ""),
                "series_name": series_name
            }
            
        except Exception as e:
            self.logger.error(f"获取剧集信息失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "series_info": "",
                "series_name": series_name
            }
    
    async def process_request(self, request_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """处理剧集信息获取请求"""
        try:
            series_name = request_data.get("series_name", "")
            search_data = request_data.get("search_data", {})
            
            # 构建提示词
            system_prompt = self._load_series_info_prompt()
            user_prompt = f"""
联网信息：
{json.dumps(search_data, ensure_ascii=False, indent=2)}
-------------------
剧集名称：{series_name}
"""
            
            # 调用LLM
            response = await self._call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context=context
            )
            
            return {
                "content": response,
                "series_name": series_name
            }
            
        except Exception as e:
            self.logger.error(f"处理剧集信息获取请求失败: {str(e)}")
            raise
    
    async def get_series_episode_plot(self, series_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取剧集分集剧情"""
        try:
            # 这里可以调用实际的API获取分集剧情
            # 目前返回模拟数据
            episode_plot = f"""
第1集：{series_name}的开篇，主要角色登场，故事背景介绍。
第2集：剧情发展，主要冲突出现。
第3集：冲突升级，角色关系变化。
...
"""
            
            return {
                "success": True,
                "episode_plot": episode_plot,
                "series_name": series_name
            }
            
        except Exception as e:
            self.logger.error(f"获取剧集分集剧情失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "episode_plot": "",
                "series_name": series_name
            }

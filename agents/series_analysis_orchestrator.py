"""
已播剧集分析与拉工作流 - 编排器
 提供完整的剧集分析服务
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from .base_juben_agent import BaseJubenAgent
from .series_name_extractor_agent import SeriesNameExtractorAgent
from .series_info_agent import SeriesInfoAgent
from .drama_analysis_agent import DramaAnalysisAgent
from .story_five_elements_agent import StoryFiveElementsAgent
from .websearch_agent import WebSearchAgent


class SeriesAnalysisOrchestrator(BaseJubenAgent):
    """已播剧集分析与拉工作流编排器"""
    
    def __init__(self, model_provider: str = "deepseek"):
        super().__init__("series_analysis_orchestrator", model_provider)
        
        # 初始化子智能体
        self.series_name_extractor = SeriesNameExtractorAgent(model_provider)
        self.series_info_agent = SeriesInfoAgent(model_provider)
        self.drama_analysis_agent = DramaAnalysisAgent(model_provider)
        self.story_five_elements_agent = StoryFiveElementsAgent(model_provider)
        self.websearch_agent = WebSearchAgent()
        
        # 工作流状态
        self.workflow_state = {
            "workflow_id": None,
            "start_time": None,
            "end_time": None,
            "current_step": None,
            "series_name": "",
            "analysis_results": {},
            "final_result": None
        }
    
    async def execute_series_analysis(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行完整的剧集分析工作流"""
        try:
            self.workflow_state["start_time"] = asyncio.get_event_loop().time()
            self.workflow_state["workflow_id"] = f"series_analysis_{int(self.workflow_state['start_time'])}"
            
            # 步骤1：意图识别和剧名提取
            self.workflow_state["current_step"] = "extract_series_name"
            series_name_result = await self.series_name_extractor.extract_series_name(user_input, context)
            
            if not series_name_result["success"]:
                return {
                    "success": False,
                    "error": "无法提取剧集名称",
                    "workflow_state": self.workflow_state
                }
            
            series_name = series_name_result["series_name"]
            self.workflow_state["series_name"] = series_name
            
            # 步骤2：并发执行三个主要任务
            self.workflow_state["current_step"] = "parallel_analysis"
            
            # 创建并发任务
            tasks = [
                self._get_series_info(series_name, context),
                self._get_web_search_results(series_name, context),
                self._get_episode_plot(series_name, context)
            ]
            
            # 执行并发任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            series_info_result, web_search_result, episode_plot_result = results
            
            # 步骤3：如果有分集剧情，进行故事五元素分析
            five_elements_result = None
            if episode_plot_result and not isinstance(episode_plot_result, Exception):
                self.workflow_state["current_step"] = "five_elements_analysis"
                five_elements_result = await self._analyze_five_elements(
                    episode_plot_result.get("episode_plot", ""), context
                )
            
            # 步骤4：章节切分和拉片分析
            self.workflow_state["current_step"] = "drama_analysis"
            drama_analysis_result = None
            if episode_plot_result and not isinstance(episode_plot_result, Exception):
                drama_analysis_result = await self._analyze_drama(
                    episode_plot_result.get("episode_plot", ""), context
                )
            
            # 步骤5：整合所有结果
            self.workflow_state["current_step"] = "integrate_results"
            final_result = await self._integrate_results({
                "series_info": series_info_result,
                "web_search": web_search_result,
                "episode_plot": episode_plot_result,
                "five_elements": five_elements_result,
                "drama_analysis": drama_analysis_result
            })
            
            self.workflow_state["final_result"] = final_result
            self.workflow_state["end_time"] = asyncio.get_event_loop().time()
            
            return {
                "success": True,
                "series_name": series_name,
                "analysis_result": final_result,
                "workflow_state": self.workflow_state
            }
            
        except Exception as e:
            self.logger.error(f"剧集分析工作流执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workflow_state": self.workflow_state
            }
    
    async def _get_series_info(self, series_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取剧集信息"""
        try:
            return await self.series_info_agent.get_series_info(series_name, context=context)
        except Exception as e:
            self.logger.error(f"获取剧集信息失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _get_web_search_results(self, series_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取联网搜索结果"""
        try:
            search_query = f"{series_name} 电视剧 评价 分析"
            return await self.websearch_agent.search_web(search_query, context=context)
        except Exception as e:
            self.logger.error(f"联网搜索失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _get_episode_plot(self, series_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取分集剧情"""
        try:
            return await self.series_info_agent.get_series_episode_plot(series_name, context=context)
        except Exception as e:
            self.logger.error(f"获取分集剧情失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_five_elements(self, episode_plot: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """故事五元素分析"""
        try:
            return await self.story_five_elements_agent.analyze_story_five_elements(episode_plot, context=context)
        except Exception as e:
            self.logger.error(f"故事五元素分析失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_drama(self, episode_plot: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """拉片分析"""
        try:
            return await self.drama_analysis_agent.analyze_drama(episode_plot, context=context)
        except Exception as e:
            self.logger.error(f"拉片分析失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _integrate_results(self, results: Dict[str, Any]) -> str:
        """整合所有分析结果"""
        try:
            # 构建整合结果
            integrated_result = "# 剧集分析报告\n\n"
            
            # 剧集信息
            if results.get("series_info", {}).get("success"):
                integrated_result += "## 剧集信息\n"
                integrated_result += results["series_info"]["series_info"] + "\n\n"
            
            # 五元素分析
            if results.get("five_elements", {}).get("success"):
                integrated_result += "## 五元素分析\n"
                integrated_result += results["five_elements"]["analysis_result"] + "\n\n"
            
            # 拉片分析
            if results.get("drama_analysis", {}).get("success"):
                integrated_result += "## 拉片分析\n"
                integrated_result += results["drama_analysis"]["analysis_result"] + "\n\n"
            
            # 联网搜索信息
            if results.get("web_search", {}).get("success"):
                integrated_result += "## 网络评价\n"
                integrated_result += results["web_search"]["search_result"] + "\n\n"
            
            # 分集剧情
            if results.get("episode_plot", {}).get("success"):
                integrated_result += "## 分集剧情\n"
                integrated_result += results["episode_plot"]["episode_plot"] + "\n\n"
            
            return integrated_result
            
        except Exception as e:
            self.logger.error(f"整合结果失败: {str(e)}")
            return f"结果整合失败: {str(e)}"
    
    async def process_request(self, request_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """处理剧集分析请求"""
        try:
            user_input = request_data.get("message", "")
            return await self.execute_series_analysis(user_input, context)
        except Exception as e:
            self.logger.error(f"处理剧集分析请求失败: {str(e)}")
            raise

"""
智谱AI搜索客户端
基于智谱AI的web_search功能，提供网络搜索服务
"""
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# 设置日志
logger = logging.getLogger(__name__)

try:
    from zhipuai import ZhipuAI
except ImportError:
    logger.error("zhipuai包未安装，请运行: pip install zhipuai")
    ZhipuAI = None


class ZhipuSearchClient:
    """智谱AI搜索客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化智谱搜索客户端
        
        Args:
            api_key: 智谱AI API密钥，如果不提供则使用环境变量
        """
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        if not self.api_key:
            raise ValueError("未提供智谱AI API密钥")
        
        if ZhipuAI is None:
            raise ImportError("zhipuai包未安装")
        
        self.client = ZhipuAI(api_key=self.api_key)
        self.search_engine = "search-std"
        self.default_count = 5
        self.default_content_size = "medium"
        
        logger.info("智谱AI搜索客户端初始化成功")
    
    def search_web(self, query: str, count: Optional[int] = None, content_size: Optional[str] = None) -> Dict[str, Any]:
        """
        搜索网络内容
        
        Args:
            query: 搜索关键词
            count: 返回结果的条数，范围1-50，默认5
            content_size: 控制网页摘要的字数，默认medium
            
        Returns:
            Dict: 搜索结果
        """
        try:
            actual_count = count or self.default_count
            actual_content_size = content_size or self.default_content_size
            
            logger.info(f"开始搜索: {query}, 数量: {actual_count}")
            
            response = self.client.web_search.web_search(
                search_engine=self.search_engine,
                search_query=query,
                count=actual_count,
                content_size=actual_content_size
            )
            
            # 解析搜索结果
            results = self._parse_search_response(response)
            
            return {
                "success": True,
                "query": query,
                "count": actual_count,
                "results": results,
                "source": "zhipu_ai"
            }
            
        except Exception as e:
            logger.error(f"智谱AI搜索失败: {e}")
            return {
                "success": False,
                "error": f"搜索失败: {str(e)}",
                "query": query,
                "results": []
            }
    
    def _parse_search_response(self, response) -> List[Dict[str, Any]]:
        """
        解析智谱AI搜索结果
        
        Args:
            response: 智谱AI返回的响应对象
            
        Returns:
            List: 解析后的结果列表
        """
        results = []
        
        try:
            if hasattr(response, 'search_result') and response.search_result:
                for item in response.search_result:
                    result = {
                        "title": getattr(item, 'title', ''),
                        "content": getattr(item, 'content', ''),
                        "url": getattr(item, 'link', ''),
                        "source": getattr(item, 'media', '网络搜索'),
                        "publish_date": getattr(item, 'publish_date', ''),
                        "platform": "智谱搜索"
                    }
                    results.append(result)
            
            logger.info(f"解析搜索结果完成，获得{len(results)}条结果")
            return results
            
        except Exception as e:
            logger.error(f"解析搜索结果失败: {e}")
            return []
    
    def search_web_simple_format(self, query: str, count: Optional[int] = None) -> Dict[str, Any]:
        """
        搜索网络内容并返回简化格式
        
        Args:
            query: 搜索关键词
            count: 返回结果的条数
            
        Returns:
            Dict: 简化格式的搜索结果
        """
        search_result = self.search_web(query, count)
        
        if search_result.get("success"):
            return {
                "success": True,
                "posts": search_result.get("results", [])
            }
        else:
            return {
                "success": False,
                "posts": [],
                "error": search_result.get("error", "搜索失败")
            }


# 创建全局实例（缺少 ZHIPU_API_KEY 或 zhipuai 包时不阻断启动，降级为 None）
try:
    zhipu_search = ZhipuSearchClient()
except (ValueError, ImportError) as e:
    logger.warning(f"智谱搜索客户端未初始化（缺少 ZHIPU_API_KEY 或 zhipuai 包）：{e}")
    zhipu_search = None


if __name__ == "__main__":
    # 测试搜索功能
    client = ZhipuSearchClient()
    
    logger.info("=== 智谱AI搜索测试 ===")
    result = client.search_web("短剧市场趋势分析", count=3)
    logger.info(f"搜索结果: {result}")

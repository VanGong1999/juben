"""
工具调用系统
让 Agent 能够调用外部工具和服务
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
import httpx
import json

logger = logging.getLogger(__name__)


class Tool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """获取工具的 JSON Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters()
        }

    def _get_parameters(self) -> Dict[str, Any]:
        """获取参数定义"""
        return {}


class SearchURLTool(Tool):
    """
    搜索网页工具
    根据文档: tools/搜索网页并且返回结果.md
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="search_url",
            description="搜索互联网并返回相关网页结果，包括标题、URL、摘要等信息"
        )
        self.api_key = api_key

    async def execute(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        执行搜索

        Args:
            query: 搜索关键词
            max_results: 最大返回结果数

        Returns:
            搜索结果列表
        """
        try:
            from utils.agent_tools.external import _run_web_search

            result = await _run_web_search(query=query, top_k=max_results)

            # 转换为文档格式
            formatted_results = []
            for ref in result.get('references', []):
                formatted_results.append({
                    "title": ref.get('title', ''),
                    "url": ref.get('url', ''),
                    "image_url": ref.get('image', '') or '',
                    "logo_url": "",
                    "sitename": ref.get('site_name') or self._extract_domain(ref.get('url', '')),
                    "summary": ref.get('content', ''),
                    "has_image": bool(ref.get('image')),
                    "provider": result.get("provider") or "deepseek",
                })

            return {
                "log_id": f"tool_{id(self)}",
                "msg": "success",
                "code": 0,
                "data": formatted_results,
                "provider": result.get("provider") or "deepseek",
            }

        except Exception as e:
            logger.error(f"[搜索工具] 执行失败: {e}")
            return {
                "log_id": f"tool_{id(self)}",
                "msg": str(e),
                "code": -1,
                "data": []
            }

    def _extract_domain(self, url: str) -> str:
        """从 URL 中提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or ""
        except:
            return ""

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数，默认10",
                    "default": 10
                }
            },
            "required": ["query"]
        }


class KnowledgeBaseTool(Tool):
    """知识库查询工具"""

    def __init__(self):
        super().__init__(
            name="knowledge_base",
            description="查询项目知识库，获取相关的剧本创作资料和参考信息"
        )
        self.kb_client = None

    def _get_kb_client(self):
        """获取知识库客户端实例"""
        if self.kb_client is None:
            try:
                from utils.knowledge_base_client import knowledge_base_client
                self.kb_client = knowledge_base_client
            except ImportError:
                logger.warning("知识库客户端不可用")
                return None
        return self.kb_client

    async def execute(
        self,
        query: str,
        collection: str = "script_segments",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """查询知识库"""
        try:
            kb_client = self._get_kb_client()
            if not kb_client:
                return {
                    "log_id": f"kb_{id(self)}",
                    "msg": "知识库客户端不可用",
                    "code": -1,
                    "data": []
                }

            # 调用知识库客户端搜索
            result = await kb_client.search(
                query=query,
                collection=collection,
                top_k=top_k
            )

            if result.get("success"):
                # 格式化返回结果
                formatted_data = []
                for item in result.get("results", []):
                    formatted_data.append({
                        "title": item.get("title", ""),
                        "content": item.get("content", ""),
                        "score": item.get("similarity", 0.0),
                        "source": "knowledge_base",
                        "collection": collection
                    })

                return {
                    "log_id": f"kb_{id(self)}",
                    "msg": "success",
                    "code": 0,
                    "data": formatted_data
                }
            else:
                return {
                    "log_id": f"kb_{id(self)}",
                    "msg": result.get("error", "查询失败"),
                    "code": -1,
                    "data": []
                }

        except Exception as e:
            logger.error(f"[知识库工具] 执行失败: {e}")
            return {
                "log_id": f"kb_{id(self)}",
                "msg": str(e),
                "code": -1,
                "data": []
            }


class BaikeSearchTool(Tool):
    """百度百科搜索工具"""

    def __init__(self):
        super().__init__(
            name="baike_search",
            description="搜索百度百科，获取词条的详细解释和相关信息"
        )

    async def execute(
        self,
        query: str,
        include_videos: bool = False
    ) -> Dict[str, Any]:
        """执行百科搜索"""
        try:
            from utils.baidu_client import get_baidu_client

            client = get_baidu_client()

            # 并发查询百科和视频
            import asyncio
            tasks = [client.get_lemma_content(query)]

            if include_videos:
                tasks.append(client.search_second_know_video(query, limit=3))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            baike_result = results[0] if not isinstance(results[0], Exception) else None
            video_result = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else None

            data = {
                "baike": baike_result.get('result', {}) if baike_result else None,
                "videos": video_result.get('result', []) if video_result else []
            }

            return {
                "log_id": f"baike_{id(self)}",
                "msg": "success",
                "code": 0,
                "data": data
            }

        except Exception as e:
            logger.error(f"[百科工具] 执行失败: {e}")
            return {
                "log_id": f"baike_{id(self)}",
                "msg": str(e),
                "code": -1,
                "data": {}
            }


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool
        logger.info(f"[工具注册] 已注册工具: {tool.name}")

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的 Schema"""
        return [tool.get_schema() for tool in self._tools.values()]


class ToolExecutor:
    """工具执行器"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._execution_history: List[Dict[str, Any]] = []

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行工具

        Args:
            tool_name: 工具名称
            parameters: 工具参数
            context: 执行上下文

        Returns:
            执行结果
        """
        tool = self.registry.get(tool_name)
        if not tool:
            logger.error(f"[工具执行] 工具不存在: {tool_name}")
            return {
                "success": False,
                "error": f"工具不存在: {tool_name}",
                "tool_name": tool_name
            }

        logger.info(f"[工具执行] 正在执行工具: {tool_name}, 参数: {parameters}")

        try:
            result = await tool.execute(**parameters)

            # 记录执行历史
            self._execution_history.append({
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "timestamp": self._get_timestamp()
            })

            return {
                "success": True,
                "tool_name": tool_name,
                "result": result
            }

        except Exception as e:
            logger.error(f"[工具执行] 执行失败: {tool_name}, 错误: {e}")
            return {
                "success": False,
                "tool_name": tool_name,
                "error": str(e)
            }

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._execution_history.copy()

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# ==================== 全局实例 ====================

# 创建工具注册表
_tool_registry = ToolRegistry()

class DramaReadTool(Tool):
    """读取短剧文件夹内容（大纲 / bible / 分集）"""

    def __init__(self):
        super().__init__(
            name="drama_read",
            description="读取短剧文件夹中的大纲、设定或指定分集正文",
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "kind": {"type": "string", "enum": ["outline", "bible", "episode", "meta"]},
                "episode_number": {"type": "integer"},
            },
            "required": ["drama_id", "kind"],
        }

    async def execute(self, drama_id: str, kind: str = "meta", episode_number: int = 1, **kwargs) -> Dict[str, Any]:
        from utils.drama_manager import get_drama_manager
        mgr = get_drama_manager()
        if kind == "meta":
            data = await mgr.get_drama(drama_id)
            return {"success": True, "data": data}
        if kind == "outline":
            drama = await mgr.get_drama(drama_id)
            return {"success": True, "data": (drama or {}).get("outline", "")}
        if kind == "bible":
            drama = await mgr.get_drama(drama_id)
            return {"success": True, "data": (drama or {}).get("bible", {})}
        if kind == "episode":
            ep = await mgr.get_episode(drama_id, int(episode_number))
            return {"success": True, "data": ep}
        return {"success": False, "error": f"未知 kind: {kind}"}


class DramaWriteEpisodeTool(Tool):
    """写入 / 生成指定分集"""

    def __init__(self):
        super().__init__(
            name="drama_write_episode",
            description="为指定短剧生成或写入某一集剧本",
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "episode_number": {"type": "integer"},
                "instruction": {"type": "string"},
            },
            "required": ["drama_id", "episode_number"],
        }

    async def execute(
        self,
        drama_id: str,
        episode_number: int,
        instruction: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        from utils.drama_manager import get_drama_manager
        mgr = get_drama_manager()
        result = await mgr.write_episode_with_llm(drama_id, int(episode_number), instruction or None)
        return {"success": True, "data": result}


class MemorySearchTool(Tool):
    """检索用户 / 剧级记忆摘要"""

    def __init__(self):
        super().__init__(
            name="memory_search",
            description="检索用户画像或项目记忆相关信息",
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "query": {"type": "string"},
            },
            "required": ["user_id"],
        }

    async def execute(self, user_id: str, query: str = "", **kwargs) -> Dict[str, Any]:
        try:
            from utils.memory_manager import get_user_profile_manager
            manager = get_user_profile_manager()
            profile = await manager.get_profile(user_id)
            return {
                "success": True,
                "data": {
                    "profile": profile.to_dict() if profile else None,
                    "query": query,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# 注册所有工具
def register_default_tools():
    """注册默认工具"""
    _tool_registry.register(SearchURLTool())
    _tool_registry.register(KnowledgeBaseTool())
    _tool_registry.register(BaikeSearchTool())
    _tool_registry.register(DramaReadTool())
    _tool_registry.register(DramaWriteEpisodeTool())
    _tool_registry.register(MemorySearchTool())


# 创建工具执行器
_tool_executor: Optional[ToolExecutor] = None


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表"""
    return _tool_registry


def get_tool_executor() -> ToolExecutor:
    """获取工具执行器"""
    global _tool_executor
    if _tool_executor is None:
        register_default_tools()
        _tool_executor = ToolExecutor(_tool_registry)
    return _tool_executor


# ==================== 测试代码 ====================

if __name__ == "__main__":
    import asyncio

    async def test_tools():
        """测试工具系统"""
        logger.info("=" * 60)
        logger.info("工具系统测试")
        logger.info("=" * 60)

        # 初始化
        register_default_tools()
        executor = get_tool_executor()

        # 测试搜索工具
        logger.info("\n1. 测试搜索工具:")
        logger.info("-" * 40)
        result = await executor.execute("search_url", {"query": "去有风的地方", "max_results": 5})
        logger.info(f"执行成功: {result['success']}")
        if result['success']:
            data = result['result']['data']
            logger.info(f"返回 {len(data)} 条结果")
            for item in data[:2]:
                logger.info(f"  - {item['title']}")
                logger.info(f"    {item['url']}")

        # 测试百科工具
        logger.info("\n2. 测试百科工具:")
        logger.info("-" * 40)
        result = await executor.execute("baike_search", {"query": "刘德华"})
        logger.info(f"执行成功: {result['success']}")

        logger.info("\n" + "=" * 60)
        logger.info("测试完成")
        logger.info("=" * 60)

    asyncio.run(test_tools())

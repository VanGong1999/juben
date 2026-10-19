"""
注册全部 Prebuilt + External 工具
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .prebuilt import get_prebuilt_tools
from .external import get_external_tools
from .orchestration_tools import get_orchestration_tools
from .meta_tools import get_meta_tools
from .wiki_tools import get_wiki_tools

if TYPE_CHECKING:
    from .registry import ToolRegistry

logger = logging.getLogger(__name__)

# 旧 agent id / 旧 tool_system 名称 → 新工具名
LEGACY_NAME_ALIASES = {
    "websearch": "web_search",
    "search_url": "web_search",
    "knowledge": "knowledge_query",
    "knowledge_base": "knowledge_query",
    "file_reference": "file_reference",
    "document_generator": "generate_document",
    "output_formatter": "format_output",
    "series_info": "extract_series_info",
    "series_name_extractor": "extract_series_name",
    "text_splitter": "text_split",
    "text_truncator": "text_truncate",
}

# 常驻完整 schema 的核心工具（其余走 Deferred Tool Loading 名录）
ALWAYS_LOAD_NAMES = frozenset(
    {
        "read",
        "write",
        "edit",
        "ls",
        "grep",
        "find",
        "date",
        "spawn_subagent",
        "transfer_to",
        "compose_agents",
        "return_to_conductor",
        "tool_search",
        "skill_search",
        "load_skill",
        "agent_search",
        "wiki_read",
        "wiki_search",
    }
)


def register_all_tools(registry: "ToolRegistry") -> int:
    """向 registry 注册全部工具，返回数量。"""
    count = 0
    for tool in get_prebuilt_tools():
        if tool.name in ALWAYS_LOAD_NAMES:
            tool.always_load = True
        registry.register(tool)
        count += 1
    for tool in get_external_tools():
        # 外部工具默认 deferred（always_load=False）
        registry.register(tool)
        count += 1
    for tool in get_orchestration_tools():
        tool.always_load = True
        registry.register(tool)
        count += 1
    for tool in get_meta_tools():
        tool.always_load = True
        registry.register(tool)
        count += 1
    for tool in get_wiki_tools():
        if tool.name in ALWAYS_LOAD_NAMES:
            tool.always_load = True
        registry.register(tool)
        count += 1
    logger.info(
        "[agent_tools] registered %d tools (prebuilt+external+orchestration+meta+wiki)",
        count,
    )
    return count


def resolve_tool_name(name: str) -> str:
    """解析旧名到新工具名。"""
    if not name:
        return name
    return LEGACY_NAME_ALIASES.get(name, name)

"""
Agent Tools Harness — 工具供 Agent 调用，不是独立专家。

两类：
  PREBUILT  — read / write / edit / ls / grep / find / date（沙箱）
  EXTERNAL  — web_search / knowledge_query / text_* / extract_* / format_* / …
"""

from .types import (
    ToolCategory,
    ToolContent,
    ToolContext,
    ToolDefinition,
    ToolResult,
    ToolUpdateCallback,
    new_tool_call_id,
)
from .sandbox import PathSandbox, SandboxError, SandboxProfile, sandbox_from_context
from .registry import ToolRegistry, ToolHarness, get_agent_tool_registry, get_tool_harness
from .bootstrap import register_all_tools, resolve_tool_name, LEGACY_NAME_ALIASES

__all__ = [
    "ToolCategory",
    "ToolContent",
    "ToolContext",
    "ToolDefinition",
    "ToolResult",
    "ToolUpdateCallback",
    "new_tool_call_id",
    "PathSandbox",
    "SandboxError",
    "SandboxProfile",
    "sandbox_from_context",
    "ToolRegistry",
    "ToolHarness",
    "get_agent_tool_registry",
    "get_tool_harness",
    "register_all_tools",
    "resolve_tool_name",
    "LEGACY_NAME_ALIASES",
]

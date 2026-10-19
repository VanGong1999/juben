"""
MCP Tool Bridge — 完整 stdio ClientSession 生命周期
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional  # noqa: F401 — Dict used by _bridges

logger = logging.getLogger(__name__)


class McpToolBridge:
    """
    用法:
      bridge = McpToolBridge()
      ok = await bridge.connect_stdio("npx", ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
      for t in bridge.as_tool_definitions():
          registry.register(t)
      ...
      await bridge.close()
    """

    def __init__(self) -> None:
        self._tools_meta: List[Dict[str, Any]] = []
        self._session: Any = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._connected = False
        self.server_name: str = "mcp"
        self._stdio_params: Any = None
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._connected and self._session is not None

    async def connect_stdio(self, command: str, args: Optional[List[str]] = None) -> bool:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            logger.warning("[mcp] package not installed: pip install mcp")
            return False

        async with self._lock:
            await self.close()
            try:
                params = StdioServerParameters(command=command, args=args or [])
                self._stdio_params = params
                self.server_name = command.replace("/", "_")
                stack = AsyncExitStack()
                read, write = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                listed = await session.list_tools()
                tools = []
                for t in getattr(listed, "tools", None) or []:
                    tools.append(
                        {
                            "name": getattr(t, "name", ""),
                            "description": getattr(t, "description", "") or "",
                            "inputSchema": getattr(t, "inputSchema", None)
                            or getattr(t, "input_schema", None)
                            or {"type": "object", "properties": {}},
                        }
                    )
                self._tools_meta = tools
                self._session = session
                self._exit_stack = stack
                self._connected = True
                logger.info("[mcp] connected %s tools=%s", command, len(tools))
                return True
            except Exception:
                logger.exception("[mcp] connect_stdio failed")
                await self.close()
                return False

    def register_remote_tools(self, tools: List[Dict[str, Any]]) -> None:
        self._tools_meta = list(tools)
        self._connected = True

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self._session is None:
            return {
                "ok": False,
                "error": f"MCP tool '{name}' 无活跃 session，请先 connect_stdio 或自定义 execute",
            }
        try:
            result = await self._session.call_tool(name, arguments or {})
            # 规范化 content
            texts = []
            for c in getattr(result, "content", None) or []:
                if getattr(c, "type", "") == "text" or hasattr(c, "text"):
                    texts.append(getattr(c, "text", str(c)))
                else:
                    texts.append(str(c))
            return {"ok": True, "raw": "\n".join(texts) if texts else str(result), "result": result}
        except Exception as e:
            logger.exception("[mcp] call_tool %s failed", name)
            return {"ok": False, "error": str(e)}

    def as_tool_definitions(self) -> List[Any]:
        from utils.agent_tools.types import ToolCategory, ToolDefinition, ToolResult

        defs: List[ToolDefinition] = []
        bridge = self

        for meta in self._tools_meta:
            name = meta.get("name") or ""
            if not name:
                continue
            description = meta.get("description") or f"MCP tool {name}"
            params = meta.get("inputSchema") or meta.get("parameters") or {
                "type": "object",
                "properties": {},
            }
            safe_server = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.server_name)
            tool_name = f"mcp__{safe_server}__{name}"

            async def execute(
                tool_call_id: str,
                p: Dict[str, Any],
                ctx: Any = None,
                on_update: Any = None,
                *,
                _mcp_name: str = name,
            ) -> ToolResult:
                out = await bridge.call_tool(_mcp_name, p)
                if not out.get("ok"):
                    return ToolResult.fail(out.get("error") or "mcp call failed")
                return ToolResult.text(str(out.get("raw")), details={"mcp": True, "name": _mcp_name})

            defs.append(
                ToolDefinition(
                    name=tool_name,
                    label=f"MCP:{name}",
                    description=description,
                    parameters=params if isinstance(params, dict) else {"type": "object", "properties": {}},
                    execute=execute,
                    category=ToolCategory.EXTERNAL,
                    dangerous=True,
                    tags=["mcp", safe_server],
                )
            )
        return defs

    async def close(self) -> None:
        if self._exit_stack is not None:
            try:
                await self._exit_stack.aclose()
            except Exception:
                logger.debug("mcp exit_stack close failed", exc_info=True)
        self._exit_stack = None
        self._session = None
        self._connected = False


_bridges: Dict[str, McpToolBridge] = {}


async def get_mcp_bridge(name: str = "default") -> McpToolBridge:
    if name not in _bridges:
        _bridges[name] = McpToolBridge()
    return _bridges[name]

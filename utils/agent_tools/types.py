"""
ToolDefinition — 现代 Agent Harness 工具契约（对齐 pi-agent / Electric Agents）

工具供 Agent 调用，不是独立专家。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union
import uuid


class ToolCategory(str, Enum):
    """两类工具：预置（harness） / 外部（设计期或运行时注册）"""

    PREBUILT = "prebuilt"
    EXTERNAL = "external"


@dataclass
class ToolContent:
    type: str  # text | image
    text: str = ""
    url: str = ""


@dataclass
class ToolResult:
    """execute 的标准返回：content 给 LLM，details 给 UI / 审计"""

    content: List[ToolContent]
    details: Dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    error: Optional[str] = None

    @staticmethod
    def text(text: str, *, details: Optional[Dict[str, Any]] = None, ok: bool = True) -> "ToolResult":
        return ToolResult(
            content=[ToolContent(type="text", text=text)],
            details=details or {},
            ok=ok,
        )

    @staticmethod
    def fail(message: str, *, details: Optional[Dict[str, Any]] = None) -> "ToolResult":
        return ToolResult(
            content=[ToolContent(type="text", text=f"Error: {message}")],
            details=details or {},
            ok=False,
            error=message,
        )

    def to_llm_text(self) -> str:
        parts = [c.text for c in self.content if c.type == "text" and c.text]
        return "\n".join(parts) if parts else (self.error or "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "error": self.error,
            "content": [{"type": c.type, "text": c.text, "url": c.url} for c in self.content],
            "details": self.details,
        }


@dataclass
class ToolContext:
    """执行上下文：沙箱根、作品、取消信号、审计、egress 用户对象"""

    user_id: str = "default_user"
    drama_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    workspace_root: Optional[str] = None  # 默认项目根
    allow_write: bool = True
    confirm_dangerous: bool = False
    user: Any = None  # RBAC / egress 用
    sandbox_profile: str = "drama"  # readonly | drama | elevated
    workload_id: Optional[str] = None  # Agent Substrate 工作负载
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 简易取消：调用方可设 metadata["aborted"]=True
    aborted: bool = False

    def check_aborted(self) -> None:
        if self.aborted or self.metadata.get("aborted"):
            raise InterruptedError("tool call aborted")

    def __post_init__(self) -> None:
        # 同步 profile 到 metadata，供 PathSandbox 读取
        if self.sandbox_profile and not self.metadata.get("sandbox_profile"):
            self.metadata["sandbox_profile"] = self.sandbox_profile


# JSON Schema 风格参数（Python 侧等价 TypeBox）
JSONSchema = Dict[str, Any]

ToolUpdateCallback = Callable[[Dict[str, Any]], Union[None, Awaitable[None]]]

ToolExecuteFn = Callable[
    [str, Dict[str, Any], Optional[ToolContext], Optional[ToolUpdateCallback]],
    Awaitable[ToolResult],
]


@dataclass
class ToolDefinition:
    """
    name: 模型 tool call 使用
    label: UI 展示
    description: 给 LLM 的说明
    parameters: JSON Schema
    execute: 执行体
    """

    name: str
    label: str
    description: str
    parameters: JSONSchema
    execute: ToolExecuteFn
    category: ToolCategory = ToolCategory.EXTERNAL
    # 安全与策略
    requires_sandbox: bool = False  # 文件类必须 True
    dangerous: bool = False  # 写盘 / 外网
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    # Deferred Tool Loading：True = 完整 schema 常驻；False = 仅名录，需 tool_search 后再加载
    always_load: bool = False

    def openai_schema(self) -> Dict[str, Any]:
        """OpenAI / GLM function-calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
                or {"type": "object", "properties": {}, "additionalProperties": False},
            },
        }

    def catalog_line(self) -> str:
        """渐进式披露：名录一行（不含完整 parameters）。"""
        desc = (self.description or "").replace("\n", " ").strip()
        if len(desc) > 120:
            desc = desc[:117] + "…"
        return f"- `{self.name}` — {self.label}: {desc}"

    def ui_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "requires_sandbox": self.requires_sandbox,
            "dangerous": self.dangerous,
            "enabled": self.enabled,
            "tags": self.tags,
            "always_load": self.always_load,
        }


def new_tool_call_id(prefix: str = "call") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

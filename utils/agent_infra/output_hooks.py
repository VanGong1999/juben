"""
Agent 输出 Hooks — 在 agent 产出内容离开进程前做过滤

对照 utils/agent_infra/prompt_hooks.py（输入侧），本模块负责输出侧：
- 注册可叠加的输出过滤器（OutputHook）
- 内置默认脱敏器：过滤 API Key / secret / token（→ "xx"）

约定：
- 每个 hook 是 `Callable[[str], str]`，入参/出参都是字符串
- 多个 hook 按 priority 从大到小依次执行（链式过滤）
- 任一 hook 抛异常不阻断输出（降级返回原串），仅记录 warning
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.secret_redaction import redact_secrets

logger = logging.getLogger(__name__)

OutputHook = Callable[[str], str]

# 视为密钥的字段名：dict 中命中该键时，其字符串值整体打码（值本身可能无固定格式）
_SECRET_KEY_NAME_RE = re.compile(
    r"(?i)(?:api[_-]?key|apikey|access[_-]?key|secret[_-]?key|secret"
    r"|token|password|passwd|authorization|bearer|credential)"
)


def _is_secret_key_name(key: Any) -> bool:
    return isinstance(key, str) and bool(_SECRET_KEY_NAME_RE.fullmatch(key.strip()))


class OutputHookRegistry:
    """进程内输出过滤器注册表。"""

    def __init__(self) -> None:
        self._hooks: List[Tuple[str, OutputHook, int]] = []

    def register(
        self,
        fn: OutputHook,
        *,
        name: str = "",
        priority: int = 100,
    ) -> None:
        self._hooks.append((name or getattr(fn, "__name__", "anon"), fn, priority))

    def clear(self) -> None:
        self._hooks.clear()

    def apply(self, content: str) -> str:
        if not content:
            return content
        out = content
        for name, fn, _ in sorted(self._hooks, key=lambda h: -h[2]):
            try:
                out = fn(out)
            except Exception as e:  # noqa: BLE001 —— 过滤失败不能阻断输出
                logger.warning("output hook %s failed: %s", name, e)
        return out


_registry: Optional[OutputHookRegistry] = None


def get_output_hooks() -> OutputHookRegistry:
    global _registry
    if _registry is None:
        _registry = OutputHookRegistry()
        # 内置默认：API Key / secret 脱敏
        _registry.register(redact_secrets, name="builtin_secret_redaction", priority=1000)
    return _registry


def redact_agent_output(content: str) -> str:
    """对一段 agent 输出应用全部 output hooks。"""
    return get_output_hooks().apply(content)


def redact_event(event: Any) -> Any:
    """
    对单个 agent 事件做递归脱敏：
    - str 直接过滤
    - dict/list 递归过滤其中的字符串值（保留键名与结构）
    - 其他类型原样返回
    """
    if isinstance(event, str):
        return redact_agent_output(event)
    if isinstance(event, dict):
        out: Dict[Any, Any] = {}
        for k, v in event.items():
            if isinstance(v, str):
                if _is_secret_key_name(k):
                    out[k] = "xx"
                else:
                    out[k] = redact_agent_output(v)
            elif isinstance(v, (dict, list)):
                out[k] = redact_event(v)
            else:
                out[k] = v
        return out
    if isinstance(event, list):
        return [redact_event(x) for x in event]
    return event

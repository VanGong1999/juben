"""
MemoryCuratorAgent — 专职记忆管理专家

职责（对齐生产 Agent Memory 架构）:
- Recall: 检索情节 / 语义 / 向量
- Reflection: 成败归因
- Skill extraction: 成功路径晋升
- Dreaming: 离线整理（用户显式请求时）
- Governance: 删除、常驻编辑（受注入扫描）

不把历史全文塞进上下文；优先 search + read_slice。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_minimal_tool_agent():
    """独立加载 sibling，避开 agents/__init__ 重型导入。"""
    path = Path(__file__).with_name("minimal_tool_agent.py")
    spec = importlib.util.spec_from_file_location("minimal_tool_agent_standalone", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.MinimalToolAgent


MinimalToolAgent = _load_minimal_tool_agent()

MEMORY_CURATOR_PROMPT = """你是短剧工作室的「记忆策展人」(Memory Curator)。

## 你的工作方式
1. 常驻记忆(USER.md / MEMORY.md / RULES.md)短硬高密度，像索引页。
2. 历史记忆(episodes / semantic / topics)可搜、可局部读，不要请求把全部历史塞进上下文。
3. Recall：先 memory_search，必要时 memory_read_slice 读原文片段。
4. Reflection：对关键成败调用 memory_reflect，绑定 episode。
5. Skill extraction：重复成功路径用 memory_promote_skill 沉淀为可复用步骤。
6. Dreaming：仅在用户要求「整理记忆/做梦/归档」时调用 memory_dream，不要每轮跑。
7. 治理：错误事实用 memory_delete；写常驻用 memory_write_resident（有注入防护）。

## 业务语境
用户在做竖屏短剧连载。优先关注：open_thread、cliffhanger、人物性状、平台规则、失败教训。

## 输出
用中文简要说明你做了什么操作、改了哪些记忆、建议用户下一步。不要编造未检索到的事实。
"""

MEMORY_TOOLS: List[str] = [
    "memory_search",
    "memory_read_slice",
    "memory_write_fact",
    "memory_write_resident",
    "memory_record_episode",
    "memory_reflect",
    "memory_promote_skill",
    "memory_forget",
    "memory_dream",
    "memory_delete",
]


class MemoryCuratorAgent(MinimalToolAgent):
    def __init__(
        self,
        agent_name: str = "memory_curator",
        model_provider: str = "deepseek",
        model: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(
            agent_name=agent_name,
            system_prompt=MEMORY_CURATOR_PROMPT,
            tool_names=list(MEMORY_TOOLS),
            max_steps=int(kwargs.get("max_steps") or 10),
            model_provider=model_provider,
            model=model,
        )

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ):
        # 记忆策展默认允许写工具（仍受 Tool ACL / dangerous 标记约束）
        context = dict(context or {})
        request_data = dict(request_data or {})
        context.setdefault("allow_write", True)
        request_data.setdefault("allow_write", True)
        async for ev in super().process_request(request_data, context):
            yield ev

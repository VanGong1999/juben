"""
统一的Agent调用入口

为所有API路由提供一致的上下文增强注入能力，避免在各处重复判断。
"""
import asyncio
from typing import Any, Dict, Optional, AsyncGenerator
from utils.output_constraints import get_output_constraint_template


async def build_agent_generator(
    agent: Any,
    request_data: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    构建Agent请求生成器

    - 自动启用增强上下文（如果agent支持）
    - 基于请求数据选择RAG/智能选择开关
    """
    # 输出侧 hooks（内置 API Key / secret 脱敏）；惰性导入避免 import 环
    from utils.agent_infra.output_hooks import redact_event

    enable_rag = bool(
        request_data.get("enable_knowledge_base")
        or request_data.get("enable_rag")
        or request_data.get("enable_auto_rag")
    )
    enable_smart_select = bool(request_data.get("enable_smart_select"))

    has_enhanced = hasattr(agent, "process_request_with_enhanced_context")

    # 老专家（BaseJubenAgent 系）自己拼 prompt、不走 assemble_budgeted_messages，
    # 故在此注入「共享作品上下文」（题材/世界观/人物/大纲），让专家知道当前作品、不割裂。
    # 总控/轻量 agent 走 assemble_budgeted_messages，已注入，避免重复。
    if has_enhanced:
        drama_id = (
            (context or {}).get("drama_id")
            or (context or {}).get("project_id")
            or request_data.get("drama_id")
            or request_data.get("project_id")
        )
        if drama_id:
            try:
                from utils.drama_context import (
                    build_drama_context_block,
                    context_sections_for,
                    extract_focus_episode,
                )

                # 按 agent 类别只注入它需要的最小上下文；评估点名某集时注入该集全文
                sections = None
                try:
                    agent_id = getattr(agent, "agent_id", None) or getattr(agent, "name", None)
                    if agent_id:
                        from config.agents import get_agent_config

                        cfg = get_agent_config(agent_id)
                        if cfg:
                            sections = context_sections_for(cfg.get("category"))
                except Exception:
                    sections = None

                inp = request_data.get("input") or request_data.get("query") or ""
                focus_ep = extract_focus_episode(str(inp))
                budget = 3500
                focus_chars = 12000
                if focus_ep and (sections is None or "episodes" in (sections or set())):
                    budget = 16000
                elif focus_ep:
                    budget = 12000

                block = await build_drama_context_block(
                    drama_id,
                    budget_chars=budget,
                    focus_episode_chars=focus_chars,
                    sections=sections,
                    focus_episode=focus_ep,
                    query=str(inp),
                    include_catalog=True,
                )
                if block:
                    request_data = dict(request_data)
                    prefix = f"【当前作品上下文】\n{block}\n\n—— 以下是用户请求 ——\n"
                    request_data["input"] = prefix + str(inp)
                    request_data["query"] = prefix + str(inp)
            except Exception:
                pass

    if "output_constraint_template" not in request_data:
        request_data["output_constraint_template"] = get_output_constraint_template()

    # 检查agent是否有process_request_with_enhanced_context方法
    if has_enhanced:
        result = agent.process_request_with_enhanced_context(
            request_data,
            context,
            enable_rag=enable_rag,
            enable_smart_select=enable_smart_select,
            context_sources=request_data.get("context_sources"),
        )
    else:
        result = agent.process_request(request_data, context)

    # 如果返回的是协程，需要先await
    if asyncio.iscoroutine(result):
        result = await result

    # 处理不同类型的返回值
    if isinstance(result, dict):
        # 返回的是字典，作为单个事件yield
        yield redact_event(result)
    elif isinstance(result, AsyncGenerator):
        # 返回的是异步生成器，迭代并yield每个事件
        async for event in result:
            yield redact_event(event)
    else:
        # 其他类型，尝试作为生成器处理
        try:
            async for event in result:
                yield redact_event(event)
        except TypeError:
            # 如果无法迭代，作为单个事件yield
            yield redact_event(result)

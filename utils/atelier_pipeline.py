"""
Atelier 多智能体创作编排

首页对话入口：propose plan → confirm run → 逐步执行核心专家 → 产物落盘 Drama。
顶层为可确认 DAG，不使用 LLM-native tool-calling loop。
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiofiles

from utils.agent_dispatch import build_agent_generator
from utils.drama_manager import get_drama_manager

logger = logging.getLogger(__name__)

# 白名单步骤（与 frontend CORE_AGENT_IDS 对齐）
STEP_CATALOG: List[Dict[str, Any]] = [
    {
        "module": "planning",
        "agent_id": "short_drama_planner",
        "title": "策划立项",
        "rationale": "题材定位、创意卖点与商业化卡点",
        "kind": "planning",
        "agent_name": "短剧策划助手",
        "category": "planning",
        "depends_on": [],
        "is_reviewer": False,
        "timeout_s": 300,
        "max_attempts": 2,
    },
    {
        "module": "story",
        "agent_id": "story_five_elements",
        "title": "故事结构",
        "rationale": "五元素拆解，夯实世界观与主线",
        "kind": "story",
        "agent_name": "故事五元素分析",
        "category": "story",
        "depends_on": ["planning"],
        "is_reviewer": False,
        "timeout_s": 300,
        "max_attempts": 2,
    },
    {
        "module": "plot",
        "agent_id": "major_plot_points",
        "title": "情节点",
        "rationale": "大情节点与节奏转折",
        "kind": "plot",
        "agent_name": "大情节点分析",
        "category": "analysis",
        "depends_on": ["story"],
        "is_reviewer": False,
        "timeout_s": 300,
        "max_attempts": 2,
    },
    {
        "module": "character",
        "agent_id": "character_profile_generator",
        "title": "人物小传",
        "rationale": "主要角色小传，同步进 bible",
        "kind": "character",
        "agent_name": "人物小传生成",
        "category": "character",
        "depends_on": ["story"],
        "is_reviewer": False,
        "timeout_s": 300,
        "max_attempts": 2,
    },
    {
        "module": "creation",
        "agent_id": "short_drama_creator",
        "title": "样章创作",
        "rationale": "生成第 1 集样章，验证人设与节奏",
        "kind": "creation",
        "agent_name": "短剧创作助手",
        "category": "creation",
        "depends_on": ["plot", "character"],
        "is_reviewer": False,
        "timeout_s": 600,
        "max_attempts": 2,
    },
    {
        "module": "evaluation",
        "agent_id": "short_drama_evaluation",
        "title": "质量评估",
        "rationale": "多维打分与诊断建议",
        "kind": "evaluation",
        "agent_name": "短剧评估助手",
        "category": "evaluation",
        "depends_on": ["creation"],
        "is_reviewer": True,
        "requires_approval": False,
        "timeout_s": 300,
        "max_attempts": 2,
    },
]

MODULE_BY_AGENT = {s["agent_id"]: s["module"] for s in STEP_CATALOG}
CATALOG_BY_AGENT = {s["agent_id"]: s for s in STEP_CATALOG}
ALLOWED_AGENT_IDS = set(CATALOG_BY_AGENT.keys())

# 前置创作阶段（分集连载前的必经策划/知识设定/人物/情节点），情节点默认包含
PREFLIGHT_MODULES = ["planning", "story", "plot", "character"]
MODULE_ORDER = {s["module"]: i for i, s in enumerate(STEP_CATALOG)}

# Agent 运行时加载统一入口（单一事实源，见 utils/agent_runtime.py）
from utils.agent_runtime import load_agent  # noqa: E402


def propose_plan(
    query: str,
    constraints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """根据 query + 模块勾选生成可编辑执行计划（不落盘）。"""
    constraints = dict(constraints or {})
    modules = constraints.get("modules")
    if not modules:
        modules = [s["module"] for s in STEP_CATALOG]
    module_set = set(modules)

    steps = []
    # module -> step_id，用于把 depends_on(module) 解析为 step id
    module_step_ids: Dict[str, str] = {}
    for i, spec in enumerate(STEP_CATALOG):
        enabled = spec["module"] in module_set
        step_id = f"step_{i + 1}_{spec['module']}"
        module_step_ids[spec["module"]] = step_id
        dep_modules = list(spec.get("depends_on") or [])
        depends_on = [module_step_ids[m] for m in dep_modules if m in module_step_ids and m in module_set]
        steps.append(
            {
                "id": step_id,
                "agent_id": spec["agent_id"],
                "title": spec["title"],
                "rationale": spec["rationale"],
                "kind": spec["kind"],
                "agent_name": spec["agent_name"],
                "category": spec["category"],
                "module": spec["module"],
                "enabled": enabled,
                "status": "pending" if enabled else "skipped",
                "depends_on": depends_on,
                "is_reviewer": bool(spec.get("is_reviewer")),
                "requires_approval": bool(spec.get("requires_approval")),
                "timeout_s": spec.get("timeout_s", 300),
                "max_attempts": spec.get("max_attempts", 2),
                "attempts": 0,
            }
        )

    return {
        "query": (query or "").strip(),
        "constraints": {
            "title": (constraints.get("title") or "").strip(),
            "genre": constraints.get("genre") or "都市情感",
            "total_episodes": int(constraints.get("total_episodes") or 80),
            "audience": constraints.get("audience") or "",
            "tone": constraints.get("tone") or "",
            "modules": list(module_set),
            "drama_id": constraints.get("drama_id") or None,
            "user_id": constraints.get("user_id") or "default_user",
        },
        "steps": steps,
    }


def _run_path(drama_id: str) -> Path:
    return Path("projects") / drama_id / "atelier_run.json"


async def _save_run(run: Dict[str, Any]) -> None:
    drama_id = run["drama_id"]
    path = _run_path(drama_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    run["updated_at"] = datetime.now().isoformat()
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(run, ensure_ascii=False, indent=2))
    # WAL：append-only 事件日志，便于 Replay
    try:
        from utils.agent_infra.durable import DurableRunStore

        store = DurableRunStore()
        await store.append_event(
            run.get("run_id") or drama_id,
            {
                "type": "run_checkpoint",
                "drama_id": drama_id,
                "status": run.get("status"),
                "current_step_id": run.get("current_step_id"),
                "steps": [
                    {"id": s.get("id"), "status": s.get("status"), "attempts": s.get("attempts")}
                    for s in (run.get("steps") or [])
                ],
            },
        )
    except Exception:
        logger.debug("atelier WAL append skipped", exc_info=True)


async def load_run(run_id: str, drama_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """按 run_id 加载；若给了 drama_id 则直接读该作品文件。"""
    if drama_id:
        path = _run_path(drama_id)
        if not path.exists():
            return None
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
        if data.get("run_id") == run_id:
            return data
        return None

    base = Path("projects")
    if not base.exists():
        return None
    for folder in base.iterdir():
        if not folder.is_dir():
            continue
        path = folder / "atelier_run.json"
        if not path.exists():
            continue
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            if data.get("run_id") == run_id:
                return data
        except Exception:
            logger.exception("读取 atelier_run 失败: %s", path)
    return None


async def load_run_for_drama(drama_id: str) -> Optional[Dict[str, Any]]:
    path = _run_path(drama_id)
    if not path.exists():
        return None
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        return json.loads(await f.read())


def _normalize_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """只保留白名单 agent，保持用户给定顺序。"""
    normalized: List[Dict[str, Any]] = []
    for i, raw in enumerate(steps or []):
        agent_id = (raw.get("agent_id") or "").strip()
        if agent_id not in ALLOWED_AGENT_IDS:
            continue
        spec = CATALOG_BY_AGENT[agent_id]
        enabled = bool(raw.get("enabled", True))
        step_id = raw.get("id") or f"step_{i + 1}_{spec['module']}"
        status = raw.get("status") or ("pending" if enabled else "skipped")
        if not enabled:
            status = "skipped"
        normalized.append(
            {
                "id": step_id,
                "agent_id": agent_id,
                "title": raw.get("title") or spec["title"],
                "rationale": raw.get("rationale") or spec["rationale"],
                "kind": spec["kind"],
                "agent_name": spec["agent_name"],
                "category": spec["category"],
                "module": spec["module"],
                "enabled": enabled,
                "status": status,
                "artifact_id": raw.get("artifact_id"),
                "error": raw.get("error"),
                "depends_on": list(raw.get("depends_on") or spec.get("depends_on") or []),
                "is_reviewer": bool(raw.get("is_reviewer", spec.get("is_reviewer"))),
                "requires_approval": bool(raw.get("requires_approval", spec.get("requires_approval"))),
                "timeout_s": int(raw.get("timeout_s") or spec.get("timeout_s") or 300),
                "max_attempts": int(raw.get("max_attempts") or spec.get("max_attempts") or 2),
                "attempts": int(raw.get("attempts") or 0),
            }
        )
    return normalized


def step_dependencies_satisfied(run: Dict[str, Any], step: Dict[str, Any]) -> bool:
    """DAG：depends_on 中的步骤均需 done（或 skipped 且非必须）。"""
    by_id = {s["id"]: s for s in run.get("steps") or []}
    for dep_id in step.get("depends_on") or []:
        # depends_on 可能是 module 名或 step id
        dep = by_id.get(dep_id)
        if not dep:
            dep = next((s for s in by_id.values() if s.get("module") == dep_id), None)
        if not dep:
            return False
        if not dep.get("enabled"):
            continue
        if dep.get("status") != "done":
            return False
    return True


async def create_run(
    query: str,
    constraints: Dict[str, Any],
    steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """确认计划：创建或绑定 Drama，写入 atelier_run.json。"""
    mgr = get_drama_manager()
    constraints = dict(constraints or {})
    user_id = constraints.get("user_id") or "default_user"
    drama_id = constraints.get("drama_id")
    title = (constraints.get("title") or "").strip()
    genre = constraints.get("genre") or "都市情感"
    total_episodes = int(constraints.get("total_episodes") or 80)
    description = (query or "").strip()

    if drama_id:
        drama = await mgr.get_drama(drama_id)
        if not drama:
            raise ValueError("短剧不存在")
        # 同步关键约束
        meta = await mgr._load_meta(drama_id)
        if meta:
            if title:
                meta["title"] = title
            meta["genre"] = genre
            meta["total_episodes"] = total_episodes
            if description and not (meta.get("description") or "").strip():
                meta["description"] = description[:2000]
            meta["updated_at"] = datetime.now().isoformat()
            async with aiofiles.open(mgr._drama_json(drama_id), "w", encoding="utf-8") as f:
                await f.write(json.dumps(meta, ensure_ascii=False, indent=2))
        drama_title = title or drama.get("title") or "未命名短剧"
    else:
        if not title:
            # 从 query 截取临时标题，策划步骤后可再改
            title = (description[:24] + "…") if len(description) > 24 else (description or "未命名短剧")
        meta = await mgr.create_drama(
            title=title,
            description=description[:2000],
            genre=genre,
            total_episodes=total_episodes,
            tags=["atelier"],
            user_id=user_id,
        )
        drama_id = meta["id"]
        drama_title = meta["title"]

    normalized = _normalize_steps(steps)
    if not any(s["enabled"] for s in normalized):
        raise ValueError("至少启用一个步骤")

    run_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    run = {
        "run_id": run_id,
        "drama_id": drama_id,
        "drama_title": drama_title,
        "query": description,
        "constraints": {
            "title": title,
            "genre": genre,
            "total_episodes": total_episodes,
            "audience": constraints.get("audience") or "",
            "tone": constraints.get("tone") or "",
            "modules": [s["module"] for s in normalized if s["enabled"]],
            "user_id": user_id,
        },
        "steps": normalized,
        "status": "ready",
        "current_step_id": next((s["id"] for s in normalized if s["enabled"] and s["status"] == "pending"), None),
        "created_at": now,
        "updated_at": now,
    }
    await _save_run(run)
    return run


async def patch_run(
    run_id: str,
    *,
    constraints: Optional[Dict[str, Any]] = None,
    steps: Optional[List[Dict[str, Any]]] = None,
    drama_id: Optional[str] = None,
) -> Dict[str, Any]:
    run = await load_run(run_id, drama_id=drama_id)
    if not run:
        raise ValueError("编排任务不存在")

    if constraints:
        merged = {**(run.get("constraints") or {}), **constraints}
        # 不允许通过 patch 改 drama 绑定
        merged.pop("drama_id", None)
        if "total_episodes" in merged:
            merged["total_episodes"] = int(merged["total_episodes"] or 80)
        run["constraints"] = merged

        mgr = get_drama_manager()
        meta = await mgr._load_meta(run["drama_id"])
        if meta:
            if merged.get("title"):
                meta["title"] = merged["title"]
                run["drama_title"] = merged["title"]
            if merged.get("genre"):
                meta["genre"] = merged["genre"]
            if merged.get("total_episodes"):
                meta["total_episodes"] = int(merged["total_episodes"])
            meta["updated_at"] = datetime.now().isoformat()
            async with aiofiles.open(mgr._drama_json(run["drama_id"]), "w", encoding="utf-8") as f:
                await f.write(json.dumps(meta, ensure_ascii=False, indent=2))

    if steps is not None:
        # 保留已完成步骤的状态与产物
        done_map = {
            s["id"]: s
            for s in run.get("steps") or []
            if s.get("status") in ("done", "running", "error")
        }
        normalized = _normalize_steps(steps)
        for s in normalized:
            prev = done_map.get(s["id"])
            if prev and prev.get("status") == "done":
                s["status"] = "done"
                s["enabled"] = True
                s["artifact_id"] = prev.get("artifact_id")
            elif not s["enabled"]:
                s["status"] = "skipped"
            elif s.get("status") not in ("done", "running"):
                s["status"] = "pending"
        run["steps"] = normalized

    run["current_step_id"] = next(
        (
            s["id"]
            for s in run["steps"]
            if s.get("enabled") and s.get("status") == "pending"
        ),
        None,
    )
    if run["current_step_id"] is None and all(
        s.get("status") in ("done", "skipped") for s in run["steps"]
    ):
        run["status"] = "completed"
    else:
        run["status"] = "ready"
    await _save_run(run)
    return run


def _build_step_prompt(run: Dict[str, Any], step: Dict[str, Any]) -> str:
    c = run.get("constraints") or {}
    parts = [
        f"【用户需求】\n{run.get('query') or ''}",
        f"【作品】{run.get('drama_title') or c.get('title') or ''}",
        f"【题材】{c.get('genre') or ''}",
        f"【集数】{c.get('total_episodes') or ''}",
    ]
    if c.get("audience"):
        parts.append(f"【受众】{c['audience']}")
    if c.get("tone"):
        parts.append(f"【调性】{c['tone']}")
    parts.append(f"【当前任务】{step.get('title')} — {step.get('rationale')}")

    # 注入绑定到该专家的写作技能（前置创作团队按 member 继承 skill）
    skills_block = _bound_skills_block(step.get("agent_id") or "")
    if skills_block:
        parts.append(skills_block)

    parts.append("请基于以上约束与写作规范完成本步骤产出，输出完整可落盘正文。")
    return "\n".join(parts)


def _bound_skills_block(agent_id: str) -> str:
    """返回绑定到 agent_id 的 skills 正文块（无则空串）。"""
    if not agent_id:
        return ""
    from utils.skill_loader import skills_for_agent

    skills = skills_for_agent(agent_id)
    if not skills:
        return ""
    chunks = ["\n## 写作规范（绑定技能，请严格遵守）"]
    for s in skills:
        body = (s.get("body") or "").strip()
        if not body:
            continue
        chunks.append(f"### {s.get('name')}（{s.get('id')}）\n{body}")
    return "\n".join(chunks) if len(chunks) > 1 else ""


async def _persist_step_result(
    run: Dict[str, Any],
    step: Dict[str, Any],
    content: str,
) -> Optional[str]:
    text = (content or "").strip()
    if not text:
        return None

    mgr = get_drama_manager()
    drama_id = run["drama_id"]
    artifact = await mgr.save_artifact(
        drama_id,
        content=text,
        agent_id=step["agent_id"],
        agent_name=step.get("agent_name") or "",
        category=step.get("category") or "",
        kind=step.get("kind") or "",
        title=f"{step.get('title')} · Atelier",
        user_prompt=(run.get("query") or "")[:2000],
        sync_bible=True,
    )

    # 知识设定/世界观：story 步骤写入 bible/world.md
    if step.get("module") == "story":
        try:
            world_path = Path("projects") / drama_id / "bible" / "world.md"
            world_path.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            block = (
                f"# {run.get('drama_title') or ''} · 知识设定 / 世界观\n\n"
                f"> 来自 {step.get('agent_name') or step.get('agent_id')} · {stamp}\n\n{text}\n"
            )
            async with aiofiles.open(world_path, "w", encoding="utf-8") as f:
                await f.write(block)
        except Exception:
            logger.exception("写入世界观 bible 失败")

    # 情节点：尝试写入 outline
    if step.get("module") == "plot":
        try:
            outline_path = Path("projects") / drama_id / "outline" / "series_outline.md"
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            async with aiofiles.open(outline_path, "a", encoding="utf-8") as f:
                await f.write(f"\n\n## 情节点 · {stamp}\n\n{text}\n")
        except Exception:
            logger.exception("写入 outline 失败")

    # 样章：写入 ep_001
    if step.get("module") == "creation":
        try:
            ep_path = Path("projects") / drama_id / "episodes" / "ep_001.md"
            ep_path.parent.mkdir(parents=True, exist_ok=True)
            body = text if text.lstrip().startswith("#") else f"# 第 1 集\n\n{text}"
            async with aiofiles.open(ep_path, "w", encoding="utf-8") as f:
                await f.write(body)
            meta = await mgr._load_meta(drama_id)
            if meta:
                meta["status"] = "serializing"
                meta["updated_at"] = datetime.now().isoformat()
                async with aiofiles.open(mgr._drama_json(drama_id), "w", encoding="utf-8") as f:
                    await f.write(json.dumps(meta, ensure_ascii=False, indent=2))
        except Exception:
            logger.exception("写入样章失败")

    return artifact.get("id")


async def execute_step(
    run_id: str,
    step_id: str,
    *,
    drama_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    model_provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """执行单步：流式转发 Agent 事件，结束后落盘并更新 run。"""
    run = await load_run(run_id, drama_id=drama_id)
    if not run:
        yield {"event_type": "error", "data": "编排任务不存在"}
        return

    step = next((s for s in run["steps"] if s["id"] == step_id), None)
    if not step:
        yield {"event_type": "error", "data": "步骤不存在"}
        return
    if not step.get("enabled"):
        yield {"event_type": "error", "data": "步骤已跳过，无法执行"}
        return
    if step.get("status") == "done":
        yield {"event_type": "system", "data": "该步骤已完成"}
        yield {"event_type": "complete", "data": {"run": run, "step_id": step_id}}
        return

    if not step_dependencies_satisfied(run, step):
        yield {
            "event_type": "error",
            "data": f"依赖未完成，无法执行：{step.get('depends_on') or []}",
        }
        return

    from utils.agent_infra.retry import IdempotencyStore

    idem = IdempotencyStore()
    next_attempt = int(step.get("attempts") or 0) + 1
    idem_key = IdempotencyStore.make_key(run_id, step_id, next_attempt, "execute")
    cached = await idem.get(idem_key)
    if cached and cached.get("artifact_id"):
        step["status"] = "done"
        step["artifact_id"] = cached.get("artifact_id")
        step["attempts"] = next_attempt
        await _save_run(run)
        yield {"event_type": "system", "data": "幂等命中，跳过重复执行"}
        yield {"event_type": "complete", "data": {"run": run, "step_id": step_id, "idempotent": True}}
        return

    step["status"] = "running"
    step["attempts"] = next_attempt
    run["status"] = "running"
    run["current_step_id"] = step_id
    await _save_run(run)

    yield {
        "event_type": "system",
        "data": f"开始执行：{step.get('title')}（{step.get('agent_name')}）",
        "metadata": {"step_id": step_id, "agent_id": step["agent_id"]},
    }

    prompt = _build_step_prompt(run, step)
    uid = user_id or (run.get("constraints") or {}).get("user_id") or "default_user"
    sid = session_id or f"atelier_{run_id}_{step_id}"

    request_data = {
        "input": prompt,
        "query": prompt,
        "stream_mode": True,
        "drama_id": run["drama_id"],
        "project_id": run["drama_id"],
        "model_provider": model_provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
    }
    context = {
        "user_id": uid,
        "session_id": sid,
        "drama_id": run["drama_id"],
        "project_id": run["drama_id"],
        "atelier_run_id": run_id,
        "atelier_step_id": step_id,
        "model_provider": model_provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
    }

    chunks: List[str] = []
    try:
        # 有用户凭证时用新实例，避免污染缓存中的默认客户端
        use_fresh = bool(api_key or base_url or model_provider or model)
        agent = load_agent(step["agent_id"], fresh=use_fresh)
        if hasattr(agent, "apply_llm_overrides"):
            agent.apply_llm_overrides(
                provider=model_provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
            )
        async for event in build_agent_generator(agent, request_data, context):
            if not isinstance(event, dict):
                continue
            et = event.get("event_type") or event.get("type") or "message"
            data = event.get("data", event.get("content", ""))
            # 兼容多种「最终内容」事件类型：llm_chunk/message/content/final_result
            if et in ("llm_chunk", "message", "content", "final_result") and isinstance(data, str):
                chunks.append(data)
            # 透传给前端
            yield {
                "event_type": et,
                "data": data,
                "metadata": {
                    **(event.get("metadata") or {}),
                    "step_id": step_id,
                    "agent_id": step["agent_id"],
                },
            }

        content = "".join(chunks).strip()
        if not content:
            # 部分 agent 可能把全文放在最终事件
            content = "".join(
                str(c) for c in chunks if c
            ).strip()

        artifact_id = await _persist_step_result(run, step, content)
        step["status"] = "done"
        step["artifact_id"] = artifact_id
        step["error"] = None
        await idem.put(idem_key, {"artifact_id": artifact_id, "step_id": step_id})

        # 推进 current
        run["current_step_id"] = next(
            (
                s["id"]
                for s in run["steps"]
                if s.get("enabled") and s.get("status") == "pending"
            ),
            None,
        )
        if run["current_step_id"] is None:
            run["status"] = "completed"
        else:
            run["status"] = "ready"
        await _save_run(run)

        yield {
            "event_type": "system",
            "data": f"✅ {step.get('title')} 已完成并落盘",
            "metadata": {"step_id": step_id, "artifact_id": artifact_id},
        }
        yield {
            "event_type": "complete",
            "data": {
                "run_id": run_id,
                "drama_id": run["drama_id"],
                "step_id": step_id,
                "artifact_id": artifact_id,
                "run": run,
            },
        }
    except Exception as e:
        logger.exception("Atelier 步骤执行失败: %s/%s", run_id, step_id)
        step["status"] = "error"
        step["error"] = str(e)
        run["status"] = "error"
        await _save_run(run)
        yield {"event_type": "error", "data": str(e), "metadata": {"step_id": step_id}}


def build_dag_scheduler(run: Dict[str, Any]):
    """把 atelier run 转为 DAGScheduler。"""
    from utils.agent_infra.orchestration import DAGScheduler, OrchestrationNode, OrchestrationPlan

    nodes = []
    for s in run.get("steps") or []:
        if not s.get("enabled", True):
            continue
        nodes.append(
            OrchestrationNode(
                node_id=s["id"],
                agent_id=s.get("agent_id") or "",
                title=s.get("title") or "",
                depends_on=list(s.get("depends_on") or []),
                is_reviewer=bool(s.get("is_reviewer")),
                requires_approval=bool(s.get("requires_approval")),
            )
        )
        # 同步已有状态
        status = s.get("status") or "pending"
        from utils.agent_infra.orchestration import NodeStatus

        mapping = {
            "pending": NodeStatus.PENDING,
            "running": NodeStatus.RUNNING,
            "done": NodeStatus.DONE,
            "error": NodeStatus.FAILED,
            "skipped": NodeStatus.SKIPPED,
            "waiting_approval": NodeStatus.WAITING_APPROVAL,
        }
        nodes[-1].status = mapping.get(status, NodeStatus.PENDING)
    plan = OrchestrationPlan(plan_id=run.get("run_id") or "atelier", nodes=nodes)
    return DAGScheduler(plan)


async def list_ready_steps(run_id: str, *, drama_id: Optional[str] = None) -> List[Dict[str, Any]]:
    run = await load_run(run_id, drama_id=drama_id)
    if not run:
        return []
    sched = build_dag_scheduler(run)
    return [n.to_dict() for n in sched.ready_nodes()]


async def auto_advance(
    run_id: str,
    *,
    drama_id: Optional[str] = None,
    user_id: Optional[str] = None,
    enqueue: bool = True,
    max_parallel: int = 2,
) -> Dict[str, Any]:
    """
    自动推进：找出就绪步骤，可选入队 Redis/内存 Worker 并行执行。
    """
    run = await load_run(run_id, drama_id=drama_id)
    if not run:
        raise ValueError("编排任务不存在")

    ready = await list_ready_steps(run_id, drama_id=drama_id or run.get("drama_id"))
    ready = ready[:max_parallel]
    enqueued = []

    if enqueue and ready:
        try:
            from utils.agent_infra.redis_queue import get_redis_task_queue, get_redis_worker_pool

            await get_redis_worker_pool()
            q = await get_redis_task_queue()
            for node in ready:
                job = await q.enqueue(
                    "atelier_step",
                    {
                        "run_id": run_id,
                        "step_id": node["node_id"],
                        "drama_id": run.get("drama_id"),
                        "user_id": user_id or (run.get("constraints") or {}).get("user_id"),
                    },
                    idempotency_key=f"atelier:{run_id}:{node['node_id']}:{node.get('status')}",
                )
                enqueued.append(job.to_dict())
        except Exception:
            logger.warning("Redis enqueue failed, fallback in-process queue", exc_info=True)
            from utils.agent_infra.queue import get_task_queue, get_worker_pool

            pool = await get_worker_pool()

            async def _handler(job):
                chunks = []
                async for ev in execute_step(
                    job.payload["run_id"],
                    job.payload["step_id"],
                    drama_id=job.payload.get("drama_id"),
                    user_id=job.payload.get("user_id"),
                ):
                    if ev.get("event_type") == "complete":
                        chunks.append(ev.get("data"))
                return chunks

            pool.register("atelier_step", _handler)
            q = get_task_queue()
            for node in ready:
                job = await q.enqueue(
                    "atelier_step",
                    {
                        "run_id": run_id,
                        "step_id": node["node_id"],
                        "drama_id": run.get("drama_id"),
                        "user_id": user_id,
                    },
                )
                enqueued.append(job.to_dict())

    return {
        "run_id": run_id,
        "drama_id": run.get("drama_id"),
        "ready": ready,
        "enqueued": enqueued,
    }


async def decide_step_approval(
    run_id: str,
    step_id: str,
    *,
    approve: bool,
    comment: str = "",
    drama_id: Optional[str] = None,
    decided_by: Optional[str] = None,
) -> Dict[str, Any]:
    """HITL：审批 reviewer / requires_approval 步骤。"""
    run = await load_run(run_id, drama_id=drama_id)
    if not run:
        raise ValueError("编排任务不存在")
    step = next((s for s in run["steps"] if s["id"] == step_id), None)
    if not step:
        raise ValueError("步骤不存在")
    if approve:
        step["status"] = "done"
        step["approval"] = {"approved": True, "comment": comment, "by": decided_by}
    else:
        step["status"] = "error"
        step["error"] = f"rejected: {comment}"
        step["approval"] = {"approved": False, "comment": comment, "by": decided_by}
    await _save_run(run)
    return run


# ---------- 前置创作（Preflight）：分集连载前的策划/知识设定/人物/情节点 ----------


async def start_preflight(
    drama_id: str,
    *,
    user_id: str = "default_user",
    query: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """为一作品创建「前置创作」编排并后台执行（策划→故事→人物/情节点）。

    已有 run 则复用并重跑未完成步骤；force=True 时全部启用步骤重跑（重新生成）。
    返回 run（含 steps 状态），执行在后台 asyncio task 中进行，前端轮询 run 状态。
    """
    mgr = get_drama_manager()
    drama = await mgr.get_drama(drama_id)
    if not drama:
        raise ValueError("短剧不存在")

    existing = await load_run_for_drama(drama_id)
    if existing and existing.get("preflight"):
        run = existing
        for s in run["steps"]:
            # force=True：全部启用步骤重跑；否则只重跑未完成的（error/pending/running）
            if s.get("enabled") and (force or s.get("status") in ("error", "pending", "running")):
                s["status"] = "pending"
                s["error"] = None
                if force:
                    s["artifact_id"] = None
        run["status"] = "ready"
        run["current_step_id"] = next(
            (s["id"] for s in run["steps"] if s.get("enabled") and s.get("status") == "pending"),
            None,
        )
        await _save_run(run)
    else:
        q = (
            (query or "").strip()
            or (drama.get("description") or "").strip()
            or (drama.get("title") or "").strip()
            or "未命名短剧"
        )
        constraints = {
            "title": drama.get("title") or "",
            "genre": drama.get("genre") or "都市情感",
            "total_episodes": int(drama.get("total_episodes") or 80),
            "audience": "",
            "tone": "",
            "modules": list(PREFLIGHT_MODULES),
            "drama_id": drama_id,
            "user_id": user_id,
        }
        plan = propose_plan(q, constraints)
        steps = [s for s in plan["steps"] if s.get("enabled")]
        run = await create_run(q, constraints, steps)
        run["preflight"] = True
        await _save_run(run)

    asyncio.create_task(_run_preflight_steps(run["run_id"], drama_id))
    return run


def _find_step(run: Dict[str, Any], step_id: str) -> Optional[Dict[str, Any]]:
    return next((s for s in run.get("steps") or [] if s["id"] == step_id), None)


def _build_preflight_team(run: Dict[str, Any]):
    """把 run 的启用步骤转成 AgentTeam 定义（前置创作团队）。"""
    from utils.agent_infra.team import TeamDefinition, TeamTask

    done_ids = {s["id"] for s in run.get("steps") or [] if s.get("status") == "done"}
    tasks: List[TeamTask] = []
    for s in run.get("steps") or []:
        if not s.get("enabled"):
            continue
        if s.get("status") == "done":
            continue
        # 依赖里去掉已完成步骤（其产物已落盘到 bible/outline）
        deps = [d for d in (s.get("depends_on") or []) if d not in done_ids]
        tasks.append(
            TeamTask(
                task_id=s["id"],
                agent_id=s.get("agent_id") or "",
                title=s.get("title") or "",
                prompt=_build_step_prompt(run, s),
                depends_on=deps,
                is_reviewer=bool(s.get("is_reviewer")),
                requires_approval=bool(s.get("requires_approval")),
            )
        )
    return TeamDefinition(
        team_id=f"preflight_{run.get('drama_id') or 'drama'}",
        lead_agent_id="juben_conductor",
        tasks=tasks,
        shared_task=(run.get("query") or "").strip(),
        synthesize=True,
    )


async def _finalize_preflight_run(run: Dict[str, Any]) -> None:
    """统一收尾：更新 run 状态并落盘。"""
    steps = run.get("steps") or []
    run["current_step_id"] = next(
        (s["id"] for s in steps if s.get("enabled") and s.get("status") == "pending"),
        None,
    )
    if all(s.get("status") in ("done", "skipped") for s in steps):
        run["status"] = "completed"
    elif any(s.get("status") == "error" for s in steps):
        run["status"] = "error"
    else:
        run["status"] = "ready"
    await _save_run(run)


async def _run_preflight_steps(run_id: str, drama_id: str) -> None:
    """用 AgentTeam 执行前置创作（策划→故事→人物/情节点按 DAG 并行，lead 合成）。

    与旧串行循环相比：就绪步骤并行生成（人物/情节点可同时跑），产物落盘用锁串行化，
    避免 run.json / 产物文件互相覆盖；最后 lead 合成一份「前置创作摘要」。
    """
    from utils.agent_infra.team import AgentTeam

    run = await load_run(run_id, drama_id=drama_id)
    if not run:
        return
    uid = (run.get("constraints") or {}).get("user_id") or "default_user"

    team = _build_preflight_team(run)
    if not team.tasks:
        await _finalize_preflight_run(run)
        return

    # 落盘串行化：并发只发生在 LLM 生成阶段
    lock = asyncio.Lock()

    async def on_task_done(task_id: str, result) -> None:
        step = _find_step(run, task_id)
        if not step:
            return
        async with lock:
            if result.success:
                content = (result.content or "").strip()
                if content:
                    step["artifact_id"] = await _persist_step_result(run, step, content)
                step["status"] = "done"
                step["error"] = None
            else:
                step["status"] = "error"
                step["error"] = result.error or "failed"
            await _save_run(run)

    context = {
        "user_id": uid,
        "session_id": f"atelier_{run_id}_preflight",
        "drama_id": drama_id,
        "project_id": drama_id,
    }

    result = None
    try:
        result = await AgentTeam(max_parallel=2).run(
            team,
            context=context,
            parent_agent_id=team.lead_agent_id,
            on_task_done=on_task_done,
        )
    except Exception:
        logger.exception("前置创作团队执行异常")

    # 保存 lead 合成摘要（agent team 的最终交付）
    if result and result.synthesis:
        try:
            mgr = get_drama_manager()
            await mgr.save_artifact(
                drama_id,
                content=result.synthesis,
                agent_id=team.lead_agent_id,
                agent_name="前置创作队长",
                category="planning",
                kind="summary",
                title="前置创作完成摘要 · AgentTeam",
                user_prompt=(run.get("query") or "")[:2000],
                sync_bible=True,
            )
        except Exception:
            logger.exception("保存前置创作合成摘要失败")

    await _finalize_preflight_run(run)

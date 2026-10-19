#!/usr/bin/env python3
"""
Agent Infra 评测 CI 入口

用法:
  ./venv/bin/python scripts/run_agent_evals.py
  ./venv/bin/python scripts/run_agent_evals.py --dataset evals/agent_smoke.jsonl --min-rate 1.0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


async def smoke_agent(inp):
    from utils.agent_infra.handoffs import (
        CONDUCTOR_AGENT_ID,
        apply_handoff,
        resolve_turn_agent,
        return_to_conductor,
    )
    from utils.agent_infra.orchestration import HandoffSpec
    from utils.agent_infra.swarm import CompositionPlan
    from utils.agent_tools import get_agent_tool_registry

    registry = get_agent_tool_registry()
    names = [t.name for t in registry.list()]
    check = inp.get("check")
    content = inp.get("echo") or inp.get("query") or ""

    # 编排工具是否注册
    if check == "orchestration_tools":
        needed = ["spawn_subagent", "transfer_to", "compose_agents", "return_to_conductor"]
        ok = all(n in names for n in needed)
        return {
            "content": ",".join(needed) if ok else "missing",
            "tool_names": names,
            "score": 100 if ok else 0,
            "tool_history": [{"tool_name": n} for n in needed if n in names],
        }

    # auto 路由 → conductor
    if check == "resolve_auto":
        r = resolve_turn_agent(agent_id=None, session_id=f"eval_{uuid.uuid4().hex[:8]}")
        ok = r.get("agent_id") == CONDUCTOR_AGENT_ID
        return {
            "content": r.get("agent_id") or "",
            "score": 100 if ok else 0,
            "tool_names": names,
            "tool_history": [],
        }

    # handoff 后 resolve 指向专家
    if check == "handoff":
        sid = f"eval_ho_{uuid.uuid4().hex[:8]}"
        apply_handoff(
            sid,
            HandoffSpec(
                from_agent=CONDUCTOR_AGENT_ID,
                to_agent="short_drama_creator",
                reason="eval",
            ),
        )
        r = resolve_turn_agent(agent_id="auto", session_id=sid)
        ok = r.get("agent_id") == "short_drama_creator"
        return_to_conductor(sid, reason="eval cleanup")
        return {
            "content": r.get("agent_id") or "",
            "score": 100 if ok else 0,
            "tool_names": names,
            "tool_history": [],
        }

    # composition plan 规范化
    if check == "compose_plan":
        plan = CompositionPlan.from_dict(
            {
                "mode": "parallel",
                "shared_task": "smoke",
                "agents": ["short_drama_planner", "short_drama_evaluation"],
                "nodes": [
                    {"agent_id": "short_drama_planner"},
                    {"agent_id": "short_drama_evaluation"},
                ],
            }
        )
        plan._normalize_mode()
        ok = plan.mode == "parallel" and len(plan.nodes) == 2 and all(
            not n.depends_on for n in plan.nodes
        )
        return {
            "content": plan.mode if ok else "bad",
            "score": 100 if ok else 0,
            "tool_names": names,
            "tool_history": [],
        }

    return {
        "content": content,
        "tool_names": names,
        "score": 100 if "read" in names and "date" in names else 0,
        "tool_history": [{"tool_name": "date"}] if "date" in names else [],
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run agent infra eval suites")
    parser.add_argument("--dataset", default="evals/agent_smoke.jsonl")
    parser.add_argument("--suite-id", default="ci")
    parser.add_argument("--min-rate", type=float, default=1.0)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    from utils.agent_infra.eval_runner import EvalRunner

    cases = await EvalRunner.load_dataset(str(ROOT / args.dataset))
    report = await EvalRunner(smoke_agent).run_suite(cases, suite_id=args.suite_id)
    data = report.to_dict()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if report.success_rate < args.min_rate:
        print(f"FAIL success_rate={report.success_rate} < {args.min_rate}", file=sys.stderr)
        return 1
    print(f"PASS success_rate={report.success_rate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

#!/usr/bin/env python3
"""全面 Agent 端到端测试（真实 LLM）：8 集短剧 · 多智能体协作 · 所有相关 agent · 连贯性验证。

流程：
  1. 创建 8 集测试剧（重生复仇爽剧）
  2. 前置创作（AgentTeam：策划→故事→人物/情节点 DAG 并行）
  3. 逐个真实调用分析类/创作类/评估类 agent（走 /juben/chat，project_id 绑定作品，共享上下文）
  4. 验证：每个 agent 产出非空、关键实体前后一致（不割裂）

用法：venv/bin/python scripts/e2e_all_agents_test.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime

import httpx

BASE = "http://localhost:8000"
POLL_INTERVAL = 3.0
PREFLIGHT_TIMEOUT = 600.0


def _post(path: str, json: dict | None = None):
    r = httpx.post(f"{BASE}{path}", json=json, timeout=120.0)
    r.raise_for_status()
    return r.json()


def _get(path: str):
    r = httpx.get(f"{BASE}{path}", timeout=30.0)
    r.raise_for_status()
    return r.json()


def _chat(agent_id: str, prompt: str, project_id: str, session_id: str) -> str:
    """通过 /juben/chat 调用指定 agent，收集 SSE 正文（llm_chunk/final_result/content）。"""
    collected: list[str] = []
    body = {
        "input": prompt,
        "agent_id": agent_id,
        "project_id": project_id,
        "user_id": "default_user",
        "session_id": session_id,
    }
    with httpx.stream("POST", f"{BASE}/juben/chat", json=body, timeout=180.0) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                ev = json.loads(payload)
            except Exception:
                continue
            # 只收集正文事件（message），跳过 agent_decision/其他元事件
            if ev.get("event") != "message":
                continue
            data = ev.get("data") or {}
            c = data.get("content") if isinstance(data, dict) else None
            if isinstance(c, str):
                collected.append(c)
    return "".join(collected).strip()


# 分析/创作/评估类 agent 的测试任务（input 简短，作品上下文由 project_id 注入）
AGENT_TASKS = [
    ("story_type_analyzer", "请判断这部剧的故事类型与题材赛道"),
    ("story_summary_generator", "请为这部剧生成精炼的故事大纲"),
    ("story_evaluation", "请评估这部剧的故事质量与吸引力"),
    ("story_outline_evaluation", "请评估这部剧的大纲完整性与可行性"),
    ("character_relationship_analyzer", "请分析这部剧主要人物之间的关系网络"),
    ("plot_points_analyzer", "请分析这部剧的情节点设计与节奏"),
    ("script_evaluation", "请评估这部剧剧本的诊断与优化方向"),
    ("drama_analysis", "请深度分析这部剧的剧本结构与价值"),
]


def main() -> int:
    title = f"E2E全量Agent测试_{datetime.now().strftime('%H%M%S')}"
    print(f"① 创建 8 集测试剧：{title}")
    created = _post("/juben/dramas", {
        "title": title,
        "description": "重生复仇爽剧：女主重生回到三年前，向欺辱她的豪门家族复仇，一路打脸逆袭并收获真爱。",
        "genre": "都市情感",
        "total_episodes": 8,
        "type": "short_drama",
    })
    drama_id = created["drama"]["id"]
    print(f"    drama_id={drama_id}")

    print("\n② 前置创作（策划→故事→人物/情节点）")
    _post(f"/juben/atelier/dramas/{drama_id}/preflight", {"user_id": "default_user", "force": True})
    start = time.time()
    run = None
    while time.time() - start < PREFLIGHT_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        run = _get(f"/juben/atelier/dramas/{drama_id}/run").get("run")
        if run and run.get("status") in ("completed", "error"):
            break
    if not run or run.get("status") != "completed":
        print(f"    ⚠️ 前置创作未完成: {run.get('status') if run else '无 run'}")
        return 1
    preflight_steps = run.get("steps") or []
    step_desc = " · ".join(f"{s.get('title')}={s.get('status')}" for s in preflight_steps)
    print(f"    完成：{step_desc}")

    # 从人物小传里提取主角名（第一个 ## 标题），用于连贯性验证
    drama = _get(f"/juben/dramas/{drama_id}")["drama"]
    characters = (drama.get("bible") or {}).get("characters") or ""
    protagonist = None
    skip_heads = ("人物小传", "人物设定", "主要人物", "角色")
    for line in characters.split("\n"):
        line = line.strip()
        if line.startswith("## "):
            name = line[3:].strip()
            if name and not name.startswith(skip_heads):
                protagonist = name.split()[0] if name else None
                break
    # 兜底：人物名可能是 **名字** 加粗格式（LLM 产出格式不稳定）
    if not protagonist:
        m = re.search(r"\*\*([^*\n]{2,8})\*\*", characters)
        if m:
            protagonist = m.group(1).strip()
    print(f"    主角（从人物小传提取）：{protagonist or '（未提取到）'}")

    print("\n③ 逐个调用分析/创作/评估 agent")
    results: list[tuple[str, str, int, str]] = []
    for i, (agent_id, task) in enumerate(AGENT_TASKS, 1):
        sid = f"e2e_{drama_id}_{agent_id}"
        try:
            content = _chat(agent_id, task, drama_id, sid)
            n = len(content)
            results.append((agent_id, content, n, "✅"))
            print(f"    [{i}/{len(AGENT_TASKS)}] {agent_id}: {n} 字 ✅")
        except Exception as e:
            results.append((agent_id, "", 0, "❌"))
            print(f"    [{i}/{len(AGENT_TASKS)}] {agent_id}: ❌ {e}")

    # ④ 连贯性验证
    print("\n④ 连贯性验证（关键实体在产出中是否一致）")
    all_text = "".join(c for _, c, _, _ in results)
    checks = {
        "题材「重生」": "重生" in all_text,
        "题材「复仇」": "复仇" in all_text,
    }
    if protagonist:
        checks[f"主角「{protagonist}」"] = protagonist in all_text
    for label, ok in checks.items():
        print(f"    {'✅' if ok else '❌'} {label}")

    # ⑤ 产出摘要（人工核查是否跑偏）
    print("\n⑤ 各 agent 产出摘要")
    for agent_id, content, n, mark in results:
        preview = content.replace("\n", " ")[:130] if content else "（空）"
        print(f"    {mark} [{agent_id}] {preview}…")

    empty = [aid for aid, c, _, _ in results if not c]
    consistency = all(checks.values())
    ok = not empty and consistency and protagonist is not None
    print(f"\n{'✅ PASS' if ok else '❌ FAIL'} — drama_id={drama_id}（前端 /dramas 与 /studio/{drama_id} 可查看）")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

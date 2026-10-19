#!/usr/bin/env python3
"""
端到端：创建 5 集短剧 → 写入前置产物 → 分集连载编排（连贯性草稿 + 并行 subagents）

用法（项目根目录）:
  source venv/bin/activate
  python scripts/test_episode_batch_5ep.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


PREFLIGHT = {
    "planning": """# 策划立项
题材：都市逆袭爽文 · 重生打脸
卖点：前世被未婚夫与闺蜜陷害破产，重生后用商业情报层层反击
受众：18–35 女频偏爽感
卡点：每集结尾抛更大反转；第3集付费卡点「假合同真相」
""",
    "story": """# 故事五元素
主角：林晚（28，前世卖身抵债，重生带三年记忆）
反派：陈昊（未婚夫）、苏晴（闺蜜）
主线目标：夺回公司股权、公开真相
世界观：当代都市，短视频电商创业圈
主题：信任崩塌后的清醒与反击
""",
    "character": """# 人物小传
## 林晚
冷静、算计、嘴硬心软。重生后不再无条件信任。台词短促有力。
## 陈昊
表面温柔，实则利用林晚资源。傲慢、怕公开。
## 苏晴
绿茶人设，擅长舆论操控。
## 顾琛
商业对手转盟友，话少、关键时刻递刀子。
""",
    "plot": """# 大情节点（5集版）
1. 婚礼当日当众退婚，亮出假合同线索
2. 公司被夺，林晚反向收购供应链
3. 付费卡点：顾琛送来关键证据，陈昊反咬
4. 苏晴舆论战，林晚直播反杀
5. 股权夺回 + 更大幕后黑手现身
""",
}


async def main() -> None:
    from utils.drama_manager import get_drama_manager
    from utils.agent_runtime import load_agent, clear_agent_cache

    mgr = get_drama_manager()
    drama = await mgr.create_drama(
        title="重生之商业反杀",
        description="前世被未婚夫与闺蜜算计破产，重生后用商业情报层层打脸。五集测试短剧。",
        genre="都市逆袭",
        total_episodes=5,
        tags=["test", "episode_batch", "5ep"],
        user_id="default_user",
    )
    drama_id = drama["id"]
    print(f"✅ 创建短剧 drama_id={drama_id}")
    print(f"   工作室路径: /studio/{drama_id}")

    # 前置产物
    for kind, content in PREFLIGHT.items():
        await mgr.save_artifact(
            drama_id,
            content=content,
            agent_id=f"seed_{kind}",
            agent_name="测试种子",
            kind=kind,
            title=f"前置·{kind}",
            sync_bible=True,
        )
    outline = """# 系列大纲
一句话：重生女用商业情报打脸渣男闺蜜，五集从退婚到股权夺回。

## 三幕
- 退婚立钩
- 供应链与证据战
- 舆论反杀与幕后现身

## 分集节拍
第1集 | 婚礼退婚 | 怒
第2集 | 供应链反杀 | 爽
第3集 | 证据与反咬 | 压→爆
第4集 | 直播舆论战 | 爽
第5集 | 股权+幕后 | 爆+悬念
"""
    outline_path = mgr._dir(drama_id) / "outline" / "series_outline.md"
    outline_path.parent.mkdir(parents=True, exist_ok=True)
    outline_path.write_text(outline, encoding="utf-8")
    print("✅ 前置产物已写入（策划/故事/人物/情节点/大纲）")

    clear_agent_cache("episode_batch_creator")
    clear_agent_cache("episode_writer")
    agent = load_agent("episode_batch_creator", fresh=True)

    request_data = {
        "input": "前置已完成。请并行写第1–5集，偏爽感打脸，避免重复桥段，每集结尾有卡点。",
        "query": "写第1到第5集",
        "from_episode": 1,
        "to_episode": 5,
        "drama_id": drama_id,
        "target_words": 700,
        "user_requirements": "偏爽感打脸，避免重复桥段，每集结尾卡点",
    }
    context = {
        "drama_id": drama_id,
        "project_id": drama_id,
        "user_id": "default_user",
        "session_id": f"test_batch_{drama_id[:8]}",
        "from_episode": 1,
        "to_episode": 5,
        "target_words": 700,
    }

    print("🚀 启动分集连载编排（连贯性草稿 → 并行 5 个 episode_writer）…")
    sub_starts = 0
    sub_ends = 0
    async for ev in agent.process_request(request_data, context):
        et = ev.get("event_type")
        data = ev.get("data")
        meta = ev.get("metadata") or {}
        if et == "system":
            print(f"  [system] {str(data)[:100]}")
        elif et == "subagent_start":
            sub_starts += 1
            ep = meta.get("episode_number") or (data or {}).get("episode_number")
            print(f"  [subagent_start] 第{ep}集")
        elif et == "subagent_end":
            sub_ends += 1
            ep = meta.get("episode_number") or (data or {}).get("episode_number")
            ok = meta.get("success", (data or {}).get("success"))
            wc = (data or {}).get("word_count")
            print(f"  [subagent_end] 第{ep}集 success={ok} words={wc}")
        elif et == "complete":
            print(f"  [complete] success={(data or {}).get('success')}")

    # 校验落盘
    episodes = []
    for n in range(1, 6):
        ep = await mgr.get_episode(drama_id, n)
        episodes.append(ep)
        status = ep.get("status")
        wc = ep.get("word_count") or 0
        print(f"  📄 第{n}集 status={status} words={wc} title={ep.get('title')}")

    continuity = mgr._dir(drama_id) / "outline" / "continuity_draft.json"
    print(f"  📎 continuity_draft exists={continuity.exists()}")

    done = sum(1 for e in episodes if e.get("status") == "done" and (e.get("word_count") or 0) > 100)
    result = {
        "drama_id": drama_id,
        "studio_url": f"/studio/{drama_id}",
        "subagent_starts": sub_starts,
        "subagent_ends": sub_ends,
        "episodes_done": done,
        "continuity_draft": continuity.exists(),
        "ok": done >= 4 and continuity.exists() and sub_starts >= 5,
    }
    out = ROOT / "data" / "test_episode_batch_5ep_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        sys.exit(1)
    print(f"\n🎉 打开前端工作室查看: /studio/{drama_id}")


if __name__ == "__main__":
    asyncio.run(main())

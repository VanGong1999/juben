"""Context cache 断线修复的单测：DeepSeek 命中统计 + 压缩触发边界。"""

from __future__ import annotations

import pytest


def test_normalize_cache_usage_deepseek():
    from utils.agent_infra.prompt_cache import normalize_cache_usage

    # DeepSeek 自动前缀缓存字段
    norm = normalize_cache_usage(
        {
            "prompt_tokens": 1000,
            "completion_tokens": 200,
            "total_tokens": 1200,
            "prompt_cache_hit_tokens": 800,
            "prompt_cache_miss_tokens": 200,
        }
    )
    assert norm["cacheRead"] == 800
    assert norm["cacheWrite"] == 200

    # prefix_* 别名兜底
    norm2 = normalize_cache_usage(
        {
            "prompt_tokens": 1000,
            "prefix_hit_tokens": 700,
            "prefix_miss_tokens": 300,
        }
    )
    assert norm2["cacheRead"] == 700
    assert norm2["cacheWrite"] == 300


def test_normalize_cache_usage_openai_unchanged():
    from utils.agent_infra.prompt_cache import normalize_cache_usage

    norm = normalize_cache_usage(
        {
            "prompt_tokens": 1000,
            "completion_tokens": 200,
            "prompt_tokens_details": {
                "cached_tokens": 500,
                "cache_write_tokens": 500,
            },
        }
    )
    assert norm["cacheRead"] == 500
    assert norm["cacheWrite"] == 500


@pytest.mark.asyncio
async def test_compact_messages_idempotent_no_recompact():
    from utils.agent_infra.cache_compaction import compact_messages, should_compact
    from utils.agent_infra.prompt_cache import PromptCacheConfig

    msgs = [{"role": "system", "content": "stable rules", "_cacheable": True}]
    for i in range(40):
        msgs.append({"role": "user", "content": ("x" * 800) + f" turn-{i}"})
        msgs.append({"role": "assistant", "content": ("y" * 800) + f" ans-{i}"})

    cfg = PromptCacheConfig(compact_threshold_chars=5000, keep_recent_messages=4)
    assert should_compact(msgs, cfg)

    result = await compact_messages(msgs, client=None, config=cfg, session_id="test-cache-1")
    assert result.mode in ("compact", "self_compact")
    assert result.kept_recent == 4
    assert result.dropped_count > 0
    # 摘要作为 system 消息落位，稳定 system 前缀仍在最前
    contents = [str(m.get("content") or "") for m in result.messages]
    assert any("Context Compaction Summary" in c for c in contents)
    assert contents[0] == "stable rules"

    # 压缩后历史已低于阈值，二次调用不得再次压缩（防 OpenClaw 重复压缩 bug）
    assert not should_compact(result.messages, cfg)
    second = await compact_messages(result.messages, client=None, config=cfg, session_id="test-cache-1")
    assert second.mode == "none"
    assert len(second.messages) == len(result.messages)

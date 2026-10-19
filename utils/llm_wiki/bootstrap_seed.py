"""空库时写入短剧创作种子 wiki + 一份 raw，便于开箱即用。"""

from __future__ import annotations

from .store import LlmWikiStore


def seed_if_empty(store: LlmWikiStore) -> bool:
    pages = store.list_wiki_pages()
    # overview 不算实质内容
    real = [p for p in pages if p.slug != "overview"]
    if real:
        return False

    store.write_raw(
        "craft/hook-paywall-notes.txt",
        """【原始笔记】集末钩与付费卡点
- 每集结尾必须留下「必须知道答案」的问题
- 付费卡点打在情绪峰值 + 悬念未解的交叉处
- 五种钩：悬念 / 反转 / 情绪 / 危机 / 信息，轮换使用
- 反转钩全剧建议 5–7 次封顶，避免疲劳
""",
        overwrite=True,
    )

    store.write_wiki_page(
        category="craft",
        slug="hook-3s",
        title="前三秒钩子",
        summary="竖屏短剧开场 3 秒必须建立冲突/悬念/人物欲望，否则划走",
        body="""# 前三秒钩子

## Summary
开场 3 秒内给出：**冲突 / 悬念 / 欲望** 至少其一，并露出人物目标。

## 硬规则
- 禁止闷场铺垫超过 3 秒
- 第一句对白或第一个动作必须「有事发生」
- 人物欲望要可感知（要什么、怕失去什么）

## 来源
见 `raw/craft/hook-paywall-notes.txt`（相关笔记）。
""",
        tags=["hook", "opening"],
        sources=["craft/hook-paywall-notes.txt"],
        cache_tier="L3",
        rebuild_index=False,
    )

    store.write_wiki_page(
        category="craft",
        slug="cliffhanger",
        title="集末钩与付费卡点",
        summary="集末留「必须知道答案」的问题；付费卡点打在情绪峰值+悬念未解",
        body="""# 集末钩与付费卡点

## Summary
制造观众「必须知道答案」的问题 → **不给答案**。付费卡点落在情绪峰值与悬念未解交叉处。

## 5 种集末钩
| 类型 | 机制 |
|------|------|
| 悬念钩 | 接近答案 → 揭晓前切断 |
| 反转钩 | 以为 A → 最后一秒是 B |
| 情绪钩 | 情绪冲顶 → 切断 |
| 危机钩 | 生死/毁灭一线 → 硬切 |
| 信息钩 | 关键文件/人出现但未看清 |

## 硬规则
- 疑问必须服务主线
- 下一集必须回应（可不完全解答）
- 反转钩全剧 5–7 次封顶

## 原文
细节与案例见 `[[sources]]` → `raw/craft/hook-paywall-notes.txt`，用 `raw_read` 下钻。
""",
        tags=["hook", "paywall", "commercial"],
        sources=["craft/hook-paywall-notes.txt"],
        cache_tier="L2",
        rebuild_index=False,
    )

    store.write_wiki_page(
        category="concepts",
        slug="emotion-first",
        title="情绪优先叙事",
        summary="短剧以情绪节拍驱动，情节为情绪服务，而非相反",
        body="""# 情绪优先叙事

## Summary
先定「这一集观众要感到什么」，再安排情节动作。

## Checklist
- 每集一个主情绪弧（起→推→爆→余韵/切断）
- 信息量服从情绪，不堆设定
- 爽点/虐点/甜点轮换，避免单一刺激疲劳
""",
        tags=["emotion", "pacing"],
        sources=[],
        cache_tier="L3",
        rebuild_index=False,
    )

    store.write_wiki_page(
        category="concepts",
        slug="ip-value-lens",
        title="IP 价值评估透镜",
        summary="从可改编性、受众、系列化潜力、差异化四个透镜看 IP",
        body="""# IP 价值评估透镜

## Summary
评估故事/小说 IP 是否值得改编短剧时，固定走四个透镜。

## 四透镜
1. **可改编性**：冲突是否可视化、节奏是否适合竖屏切片
2. **受众**：核心人群是否清晰、付费意愿
3. **系列化**：能否支撑 60–100 集钩子而不崩
4. **差异化**：相对同赛道爆款的不可替代点

wiki 不够时，回到评估报告原文或小说原文（`raw_read`）。
""",
        tags=["ip", "evaluation"],
        sources=[],
        cache_tier="L3",
        rebuild_index=False,
    )

    store.rebuild_index()
    store.append_log("seed_if_empty: craft+concepts seeded")
    return True

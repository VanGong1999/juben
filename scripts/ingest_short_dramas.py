"""把「1、完结新文」短剧库整理进 LLM Wiki。

只提取文件名里的元信息（剧名/性别向/集数/题材/对标），生成：
  - L3 原文索引 `raw/short-dramas/catalog.md`：全部案例清单（按题材分组）
  - L2 技法页  `craft/genres-playbook.md`：短剧题材赛道指南（每赛道套路 + 案例）

用法：venv/bin/python scripts/ingest_short_dramas.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_wiki.store import LlmWikiStore  # noqa: E402

SRC = PROJECT_ROOT / "1、完结新文"
DRAMA_DIR = SRC / "短剧"

# 题材赛道：关键词 -> 赛道名（顺序即优先级，一个文件可命中多赛道）
GENRES: list[tuple[str, list[str]]] = [
    ("战神·赘婿·神医", ["战神", "赘婿", "狂婿", "帝婿", "神婿", "神医", "鬼手", "武神", "御厨", "锦衣卫"]),
    ("重生·穿越", ["重生", "穿越", "书穿", "古穿今", "穿到", "穿成", "穿书", "重返", "平行世界"]),
    ("甜宠·萌宝·闪婚", ["甜宠", "甜文", "宠文", "萌宝", "闪婚", "娇妻", "恋爱脑", "多宝", "父凭子贵", "小娇妻"]),
    ("虐恋·复仇·追妻", ["虐恋", "虐妻", "复仇", "虐渣", "追妻", "焚心", "离婚", "弃女", "真假千金", "替身", "渣过"]),
    ("悬疑·灵异·惊悚", ["悬疑", "灵异", "惊悚", "凶宅", "狼人杀", "探案", "迷踪", "妖门", "七月半", "客栈", "快递", "危机四伏", "执念"]),
    ("古装·宫斗·仙侠", ["宫斗", "古装", "古言", "仙侠", "宫廷", "皇后", "女帝", "将军", "花魁", "锦鲤", "太子", "县令", "王妃", "狐妖", "太医"]),
    ("都市·职场·商战", ["都市", "职场", "总裁", "商战", "神豪", "首富", "巨富", "财神", "offer", "娱乐圈", "顶流"]),
    ("种田·民国·末世·校园", ["种田", "田园", "民国", "末世", "校园", "校霸", "校花", "班花", "军婚", "福妻"]),
]

_TITLE_RE = re.compile(r"《([^》]+)》")
_EP_RE = re.compile(r"(\d+)\s*集")
_MATCH_RE = re.compile(r"对标[《\s]*([^）)】]+)")


def _classify(name: str) -> list[str]:
    hits = []
    for genre, kws in GENRES:
        if any(k in name for k in kws):
            hits.append(genre)
    return hits or ["其他"]


def _extract_title(name: str) -> str:
    m = _TITLE_RE.search(name)
    return m.group(1) if m else name.split(".")[0]


def _extract_meta(name: str) -> dict:
    meta: dict = {}
    meta["gender"] = "男主" if "男主" in name else ("女主" if "女主" in name else "")
    m = _EP_RE.search(name)
    meta["episodes"] = m.group(1) if m else ""
    m = _MATCH_RE.search(name)
    meta["benchmark"] = m.group(1).strip() if m else ""
    return meta


def _collect() -> tuple[list[tuple[str, str]], list[str]]:
    """返回 (短剧列表[(文件名, 完整标题)], 小说列表)。"""
    dramas: list[tuple[str, str]] = []
    if DRAMA_DIR.exists():
        for f in sorted(DRAMA_DIR.iterdir()):
            if f.suffix.lower() in (".docx", ".doc", ".pdf"):
                dramas.append((f.name, _extract_title(f.name)))
    novels: list[str] = []
    if SRC.exists():
        for f in sorted(SRC.iterdir()):
            if f.suffix == ".txt":
                novels.append(_extract_title(f.name))
    return dramas, novels


def _build_catalog(dramas: list[tuple[str, str]], novels: list[str]) -> str:
    by_genre: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for name, title in dramas:
        for g in _classify(name):
            by_genre[g].append((name, title))

    lines = [
        "---",
        "title: 完结新文短剧案例清单",
        "summary: 题材赛道分组下的真实短剧剧本/小说文件名索引",
        "---",
        "",
        "# 完结新文 · 短剧案例清单（L3 索引）",
        "",
        f"短剧剧本 {len(dramas)} 部 · 小说 IP {len(novels)} 本。按题材赛道分组，",
        "文件名即含题材/性别向/集数/对标信息，便于 agent 检索真实案例。",
        "",
    ]
    for genre, _ in GENRES:
        items = by_genre.get(genre, [])
        if not items:
            continue
        lines.append(f"## {genre}（{len(items)} 部）")
        lines.append("")
        for name, title in items:
            lines.append(f"- `{name}`")
        lines.append("")

    others = by_genre.get("其他", [])
    if others:
        lines.append(f"## 其他（{len(others)} 部）")
        lines.append("")
        for name, _ in others:
            lines.append(f"- `{name}`")
        lines.append("")

    if novels:
        lines.append(f"## 小说 IP（{len(novels)} 本，待改编）")
        lines.append("")
        for t in novels:
            lines.append(f"- 《{t}》")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _build_playbook(dramas: list[tuple[str, str]]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for name, _ in dramas:
        for g in _classify(name):
            counts[g] += 1

    total = len(dramas)
    body_lines = [
        "# 短剧题材赛道指南",
        "",
        "本页来自「完结新文」真实短剧库的题材分布，供策划/评估 Agent 判断题材选择与套路。",
        f"样本 {total} 部小程序短剧（多为 1 分钟 100 集、含前 10 集试稿）。",
        "",
    ]
    for genre, kws in GENRES:
        n = counts.get(genre, 0)
        if not n:
            continue
        body_lines.append(f"## {genre}（{n} 部）")
        body_lines.append("")
        body_lines.append(f"- **关键词**：{'、'.join(kws[:6])}")
        body_lines.append(f"- **占比**：约 {n * 100 // max(total, 1)}%")
        body_lines.append("- **套路要点**：见下表")
        body_lines.append("")
    body = "\n".join(body_lines)

    # 每个赛道的套路要点（结合 skills 知识提炼）
    genre_tips = {
        "战神·赘婿·神医": "身份碾压+打脸复仇；受辱够狠、揭露有仪式感；男频爽剧，前 3 秒直接打脸或身份反转。",
        "重生·穿越": "极端困境开局→重生/穿越觉醒→改写命运；谷底够低、转机有伏笔、翻盘分步。",
        "甜宠·萌宝·闪婚": "情绪兑现为核心（甜/宠）；先婚后爱、萌宝助攻；每集一个可感知的甜点。",
        "虐恋·复仇·追妻": "压抑→释放的虐恋曲线；追妻火葬场、真假千金、替身；情感爆发是核心爽点。",
        "悬疑·灵异·惊悚": "信息差+反转；集末悬念钩；对标《不良执念清除师》式单元+主线。",
        "古装·宫斗·仙侠": "宫斗权谋/仙侠虐恋；身份、阵营、伏笔回收；正面对决留后段。",
        "都市·职场·商战": "都市逆袭/职场升级；爽点在「原来你早算到了」的智斗破局。",
        "种田·民国·末世·校园": "题材细分赛道；种田看经营、民国看风云、末世看生存、校园看反差。",
    }
    lines = ["# 短剧题材赛道指南", "", "真实短剧库题材分布与套路要点，供策划/评估 Agent 参考。", ""]
    for genre, kws in GENRES:
        n = counts.get(genre, 0)
        if not n:
            continue
        lines.append(f"## {genre}（{n} 部）")
        lines.append("")
        lines.append(f"- 关键词：{'、'.join(kws[:6])}")
        lines.append(f"- 套路要点：{genre_tips.get(genre, '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    dramas, novels = _collect()
    if not dramas and not novels:
        print("未找到「1、完结新文」内容")
        return

    store = LlmWikiStore()
    catalog = _build_catalog(dramas, novels)
    store.write_raw("short-dramas/catalog.md", catalog, overwrite=True)

    playbook = _build_playbook(dramas)
    store.write_wiki_page(
        category="craft",
        slug="genres-playbook",
        title="短剧题材赛道指南",
        summary="战神/赘婿、重生穿越、甜宠萌宝、虐恋复仇、悬疑灵异、古装仙侠、都市商战等赛道套路与占比",
        body=playbook,
        tags=["genres", "topics", "短剧"],
        sources=["short-dramas/catalog.md"],
        cache_tier="L2",
        rebuild_index=False,
    )
    store.rebuild_index()
    stats = store.stats()
    print(f"短剧 {len(dramas)} 部 · 小说 {len(novels)} 本")
    print(f"已生成 raw/short-dramas/catalog.md + craft/genres-playbook.md")
    print(f"wiki_pages={stats['wiki_pages']}")


if __name__ == "__main__":
    main()

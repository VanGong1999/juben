"""
图谱自动校验与剧本一致性检测
"""
import re
from typing import Any, Dict, List, Tuple, Optional

from utils.graph_manager import get_graph_manager


async def validate_graph(story_id: str) -> Dict[str, Any]:
    manager = await get_graph_manager()
    data = await manager.get_story_elements(story_id)
    nodes = data.get("nodes", [])
    relationships = data.get("relationships", [])

    plot_nodes = [n for n in nodes if "PlotNode" in n.get("labels", []) or n.get("plot_id")]
    plot_by_id = {n.get("plot_id") or n.get("id") or n.get("title"): n for n in plot_nodes}
    seq_numbers = {}
    for node in plot_nodes:
        seq = node.get("sequence_number")
        if seq is None:
            continue
        seq_numbers.setdefault(seq, []).append(node)

    issues: List[Dict[str, Any]] = []
    for seq, items in seq_numbers.items():
        if len(items) > 1:
            issues.append({
                "type": "sequence_duplicate",
                "message": f"情节顺序重复: 序号 {seq} 出现 {len(items)} 次",
                "nodes": [i.get("plot_id") or i.get("id") or i.get("title") for i in items],
            })

    # 关系冲突：同一对角色出现家庭关系与恋爱关系
    relation_map: Dict[Tuple[str, str], set] = {}
    for rel in relationships:
        rel_type = rel.get("type") or rel.get("relationship_type")
        source = rel.get("source") or rel.get("source_id")
        target = rel.get("target") or rel.get("target_id")
        if not source or not target:
            continue
        key = tuple(sorted([str(source), str(target)]))
        relation_map.setdefault(key, set()).add(rel_type)

    for key, rel_types in relation_map.items():
        if "FAMILY_RELATION" in rel_types and "ROMANTIC_RELATION" in rel_types:
            issues.append({
                "type": "relationship_conflict",
                "message": f"关系冲突: {key[0]} 与 {key[1]} 同时存在家庭与恋爱关系",
                "source_id": key[0],
                "target_id": key[1],
            })

    # 时间线校验：NEXT 关系与 sequence_number 不一致
    for rel in relationships:
        rel_type = rel.get("type") or rel.get("relationship_type")
        if rel_type != "NEXT":
            continue
        source = rel.get("source") or rel.get("source_id")
        target = rel.get("target") or rel.get("target_id")
        src = plot_by_id.get(source)
        tgt = plot_by_id.get(target)
        if src and tgt:
            if src.get("sequence_number") is not None and tgt.get("sequence_number") is not None:
                if tgt.get("sequence_number") <= src.get("sequence_number"):
                    issues.append({
                        "type": "timeline_conflict",
                        "message": f"时间线冲突: NEXT 关系顺序异常 ({src.get('title') or source} -> {tgt.get('title') or target})",
                        "source_id": source,
                        "target_id": target,
                    })

    return {
        "story_id": story_id,
        "issues": issues,
        "issue_count": len(issues),
        "status": "pass" if len(issues) == 0 else "warning",
    }


def _extract_dialogues(text: str) -> Dict[str, List[str]]:
    dialogues: Dict[str, List[str]] = {}
    for line in text.splitlines():
        line = line.strip()
        match = re.match(r"^([\\u4e00-\\u9fffA-Za-z0-9_]{2,10})[:：](.+)$", line)
        if not match:
            continue
        name = match.group(1)
        content = match.group(2).strip()
        if not content:
            continue
        dialogues.setdefault(name, []).append(content)
    return dialogues


def _compute_style_metrics(lines: List[str]) -> Dict[str, float]:
    total = len(lines)
    if total == 0:
        return {"avg_len": 0, "exclaim_rate": 0, "question_rate": 0, "short_rate": 0}
    lens = [len(l) for l in lines]
    avg_len = sum(lens) / total
    exclaim_rate = sum(1 for l in lines if "!" in l or "！" in l) / total
    question_rate = sum(1 for l in lines if "?" in l or "？" in l) / total
    short_rate = sum(1 for l in lines if len(l) <= 8) / total
    return {
        "avg_len": round(avg_len, 2),
        "exclaim_rate": round(exclaim_rate, 4),
        "question_rate": round(question_rate, 4),
        "short_rate": round(short_rate, 4),
    }


def _detect_style_inconsistency(metrics: Dict[str, float]) -> bool:
    if metrics["avg_len"] >= 28 and metrics["short_rate"] >= 0.6:
        return True
    if metrics["avg_len"] <= 10 and metrics["short_rate"] <= 0.2:
        return True
    return False


def check_character_consistency(script_text: str) -> Dict[str, Any]:
    dialogues = _extract_dialogues(script_text)
    issues = []
    details = []
    for name, lines in dialogues.items():
        metrics = _compute_style_metrics(lines)
        inconsistent = _detect_style_inconsistency(metrics)
        if inconsistent:
            issues.append(f"{name} 的说话风格波动较大")
        details.append({
            "character": name,
            "lines": len(lines),
            "metrics": metrics,
            "inconsistent": inconsistent
        })

    return {
        "issue_count": len(issues),
        "issues": issues,
        "details": details,
        "status": "pass" if len(issues) == 0 else "warning"
    }


async def check_character_motivation_consistency(script_text: str) -> Dict[str, Any]:
    """
    使用 LLM 检测人物动机一致性（高质量推理）
    """
    try:
        from utils.llm_client import get_llm_client
    except Exception:
        return {"status": "error", "issues": ["LLM客户端不可用"]}

    prompt = (
        "请基于以下剧本内容，检测人物动机是否一致、是否存在前后矛盾。"
        "输出 JSON，字段包含: issues(数组), summary(字符串), score(0-100)。\n\n"
        f"剧本内容：\n{script_text[:8000]}"
    )

    llm = get_llm_client()
    try:
        result = await llm.chat([
            {"role": "system", "content": "你是剧本一致性审计专家，务必只输出JSON对象。"},
            {"role": "user", "content": prompt},
        ], temperature=0.2, max_tokens=1500)
    except Exception as e:
        return {"status": "error", "issues": [str(e)]}

    try:
        import json
        data = json.loads(result)
        return {"status": "ok", **data}
    except Exception:
        return {"status": "error", "issues": ["LLM输出非JSON"], "raw": result}

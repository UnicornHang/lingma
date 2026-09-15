"""世界观一致性 —— 规则抽取 + 启发式扫描 + issue 合并。

LLM 审校之外先跑本地规则:从世界书抽出「无法/不能/禁止」类约束,
若待检正文出现被禁止的片段则立刻标记。无 LLM 时也能给出可用结果。
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.models.world import WorldBible
from app.schemas.world import ConsistencyIssue

# 捕获「无法飞行」「不能踏空」中的动作片段
_NEGATION_RE = re.compile(r"(无法|不能|不可|禁止|不得)(.{1,12})")
_ISSUE_TYPES = {
    "geography_conflict",
    "faction_conflict",
    "power_system_violation",
    "timeline_conflict",
    "rule_violation",
    "culture_conflict",
    "other",
}


def serialize_world_brief(bible: WorldBible | None, max_chars: int = 4000) -> str:
    """把世界书压成 prompt 用的短文本。"""
    if bible is None:
        return ""
    chunks: list[str] = []
    if bible.raw_text:
        chunks.append(bible.raw_text.strip())
    for label, value in (
        ("geography", bible.geography),
        ("factions", bible.factions),
        ("power_system", bible.power_system),
        ("timeline", bible.timeline),
        ("rules", bible.rules),
        ("culture", bible.culture),
    ):
        if not value:
            continue
        chunks.append(f"{label}: {_to_preview(value, 500)}")
    text = "\n".join(chunks).strip()
    return text[:max_chars]


def is_world_empty(bible: WorldBible | None) -> bool:
    """世界书是否没有任何可对照内容。"""
    if bible is None:
        return True
    if (bible.raw_text or "").strip():
        return False
    return not any(
        [
            bible.geography,
            bible.factions,
            bible.power_system,
            bible.timeline,
            bible.rules,
            bible.culture,
        ]
    )


def extract_rule_lines(bible: WorldBible | None) -> list[str]:
    """从规则/力量体系/正文中抽出可供启发式匹配的设定句。"""
    if bible is None:
        return []
    lines: list[str] = []
    lines.extend(_flatten_rules(bible.rules))
    if isinstance(bible.power_system, dict):
        lines.extend(_flatten_rules(bible.power_system.get("rules")))
        for key in ("description", "name"):
            v = bible.power_system.get(key)
            if isinstance(v, str) and v.strip():
                lines.append(v.strip())
    if bible.raw_text:
        for raw_line in bible.raw_text.replace("\r\n", "\n").split("\n"):
            s = raw_line.strip().lstrip("#-•* ").strip()
            if len(s) >= 4:
                lines.append(s)
    # 去重保序
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    return unique


def heuristic_scan(text: str, rules: list[str]) -> list[ConsistencyIssue]:
    """根据「无法/不能」类规则扫描正文。"""
    if not text or not rules:
        return []
    issues: list[ConsistencyIssue] = []
    seen: set[tuple[str, str]] = set()
    for rule in rules:
        for match in _NEGATION_RE.finditer(rule):
            fragment = match.group(2).strip(" ，。；、,.!！？?\"'「」")
            if len(fragment) < 2:
                continue
            idx = text.find(fragment)
            if idx < 0:
                continue
            key = (fragment, rule)
            if key in seen:
                continue
            seen.add(key)
            snippet = _snippet_around(text, idx, fragment)
            issue_type = (
                "power_system_violation"
                if any(k in rule for k in ("境", "阶", "期", "飞行", "修炼", "力量"))
                else "rule_violation"
            )
            issues.append(
                ConsistencyIssue(
                    type=issue_type,  # type: ignore[arg-type]
                    severity="error",
                    text=snippet,
                    rule_violated=rule[:300],
                    suggestion=f"正文出现「{fragment}」,与设定「{rule}」冲突,请改写以符合世界书。",
                    dimension="power_system" if issue_type == "power_system_violation" else "rules",
                    source="heuristic",
                )
            )
    return issues


def parse_llm_issues(payload: Any) -> tuple[list[ConsistencyIssue], str]:
    """解析 LLM JSON 为 issue 列表 + summary。非法条目跳过。"""
    if not isinstance(payload, dict):
        return [], ""
    summary = str(payload.get("summary") or "")
    raw_issues = payload.get("issues")
    if not isinstance(raw_issues, list):
        return [], summary
    out: list[ConsistencyIssue] = []
    for item in raw_issues[:12]:
        if not isinstance(item, dict):
            continue
        issue_type = str(item.get("type") or "other")
        if issue_type not in _ISSUE_TYPES:
            issue_type = "other"
        severity = str(item.get("severity") or "warning")
        if severity not in ("error", "warning", "info"):
            severity = "warning"
        text = str(item.get("text") or "").strip()
        rule = str(item.get("rule_violated") or "").strip()
        if not text or not rule:
            continue
        out.append(
            ConsistencyIssue(
                type=issue_type,  # type: ignore[arg-type]
                severity=severity,  # type: ignore[arg-type]
                text=text[:200],
                rule_violated=rule[:300],
                suggestion=str(item.get("suggestion") or "")[:300],
                dimension=str(item.get("dimension") or "other")[:40],
                source="llm",
            )
        )
    return out, summary


def merge_issues(
    heuristic: list[ConsistencyIssue], llm: list[ConsistencyIssue]
) -> list[ConsistencyIssue]:
    """启发式优先,LLM 补充;按 (rule, text) 去重。"""
    merged: list[ConsistencyIssue] = []
    seen: set[tuple[str, str]] = set()
    for issue in heuristic + llm:
        key = (issue.rule_violated[:80], issue.text[:80])
        if key in seen:
            continue
        seen.add(key)
        merged.append(issue)
    return merged[:12]


def _flatten_rules(value: Any) -> list[str]:
    """rules 字段可能是 list[str] / list[dict] / dict。"""
    lines: list[str] = []
    if isinstance(value, str) and value.strip():
        lines.append(value.strip())
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                lines.append(item.strip())
            elif isinstance(item, dict):
                desc = item.get("description") or item.get("rule") or item.get("name")
                if isinstance(desc, str) and desc.strip():
                    lines.append(desc.strip())
    elif isinstance(value, dict):
        entries = value.get("entries") or value.get("rules") or value.get("items")
        if entries is not None:
            lines.extend(_flatten_rules(entries))
        else:
            for v in value.values():
                if isinstance(v, str) and v.strip():
                    lines.append(v.strip())
    return lines


def _to_preview(value: Any, max_chars: int) -> str:
    """JSON 预览截断。"""
    if isinstance(value, str):
        return value[:max_chars]
    try:
        return json.dumps(value, ensure_ascii=False)[:max_chars]
    except TypeError:
        return str(value)[:max_chars]


def _snippet_around(text: str, idx: int, fragment: str) -> str:
    """截取冲突片段附近上下文。"""
    start = max(0, idx - 12)
    end = min(len(text), idx + len(fragment) + 12)
    snippet = text[start:end].replace("\n", " ").strip()
    return snippet[:80]

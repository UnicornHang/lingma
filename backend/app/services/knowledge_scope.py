"""知情范围启发式：角色未知事实不得与角色名同时出现在正文近邻。

确定性扫描，不调用 LLM；给 Critic 当一致性提示，不替代考据党评分。
"""
from __future__ import annotations

from typing import Any

# 过短片段误报高，忽略
_MIN_FACT_LEN = 4
_WINDOW = 80
_MAX_ISSUES = 8


def format_knowledge_brief(payload: dict[str, Any] | None, max_chars: int = 2500) -> str:
    """把账本压成 Critic 可读的知情范围短卡。"""
    if not payload:
        return ""
    lines: list[str] = ["【知情范围（账本事实，优先于文笔）】"]
    authors = payload.get("author_timeline") or []
    if authors:
        texts = [str(e.get("text") or "").strip() for e in authors if isinstance(e, dict)]
        texts = [t for t in texts if t][:12]
        if texts:
            lines.append("作者真相（角色未必知道）：" + "；".join(texts))
    chars = payload.get("characters") or {}
    if isinstance(chars, dict):
        for slot in list(chars.values())[:20]:
            if not isinstance(slot, dict):
                continue
            name = str(slot.get("name") or "").strip() or "未命名"
            known = [str(x).strip() for x in (slot.get("known_facts") or []) if str(x).strip()]
            unknown = [str(x).strip() for x in (slot.get("unknown_facts") or []) if str(x).strip()]
            lines.append(
                f"{name}｜已知：{'、'.join(known[:8]) or '无'}｜未知：{'、'.join(unknown[:8]) or '无'}"
            )
    text = "\n".join(lines)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def scan_knowledge_leaks(chapter_text: str, payload: dict[str, Any] | None) -> list[str]:
    """扫描正文是否让角色提前知道其「未知」或作者真相。"""
    text = (chapter_text or "").strip()
    if not text or not payload:
        return []
    issues: list[str] = []
    chars = payload.get("characters") or {}
    if not isinstance(chars, dict):
        return []

    author_secrets = [
        str(e.get("text") or "").strip()
        for e in (payload.get("author_timeline") or [])
        if isinstance(e, dict)
    ]
    author_secrets = [s for s in author_secrets if len(s) >= _MIN_FACT_LEN]

    for slot in chars.values():
        if not isinstance(slot, dict):
            continue
        name = str(slot.get("name") or "").strip()
        if len(name) < 2:
            continue
        secrets = [
            str(x).strip()
            for x in (slot.get("unknown_facts") or [])
            if len(str(x).strip()) >= _MIN_FACT_LEN
        ]
        secrets.extend(author_secrets)
        for secret in secrets:
            if _near(text, name, secret, _WINDOW):
                issues.append(
                    f"知情越界：正文近邻同时出现「{name}」与其不应知道的「{secret}」"
                )
            if len(issues) >= _MAX_ISSUES:
                return _dedupe(issues)
    return _dedupe(issues)


def _near(text: str, name: str, secret: str, window: int) -> bool:
    """名称与秘密片段在 window 字符内共现。"""
    start = 0
    while True:
        idx = text.find(secret, start)
        if idx < 0:
            return False
        left = max(0, idx - window)
        right = min(len(text), idx + len(secret) + window)
        if name in text[left:right]:
            return True
        start = idx + 1


def _dedupe(items: list[str]) -> list[str]:
    """保持顺序去重。"""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out

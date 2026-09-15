"""追踪账本 payload 的纯函数：空结构、提交合并、派生上下文卡。

对话不负责记忆；本模块保证「一份权威、其余派生」。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

# 续写状态卡硬上限（字符），与 Oh Story 上下文卡 ≤12KB 同量级
CONTEXT_CARD_MAX_CHARS = 12_000
# 单章增量记录硬上限
CHAPTER_RECORD_MAX_CHARS = 3_072


def empty_payload() -> dict[str, Any]:
    """返回空权威 payload。"""
    return {
        "version": 1,
        "last_chapter_id": None,
        "foreshadows": [],
        "characters": {},
        "author_timeline": [],
        "reader_timeline": [],
        "chapter_records": [],
        "chapter_constraints": {},
    }


def normalize_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    """补齐缺字段，避免旧库或空 dict 缺键。"""
    base = empty_payload()
    if not raw:
        return base
    merged = {**base, **raw}
    for key in (
        "foreshadows",
        "author_timeline",
        "reader_timeline",
        "chapter_records",
    ):
        if not isinstance(merged.get(key), list):
            merged[key] = []
    for key in ("characters", "chapter_constraints"):
        if not isinstance(merged.get(key), dict):
            merged[key] = {}
    return merged


def empty_constraints() -> dict[str, Any]:
    """本章约束锁空结构。"""
    return {
        "word_count_min": None,
        "word_count_max": None,
        "must_happen": [],
        "must_not_happen": [],
        "time_anchor": "",
        "stop_point": "",
        "end_hook_debt": "",
    }


def merge_constraints(
    outline_constraints: dict[str, Any] | None,
    payload_constraints: dict[str, Any] | None,
) -> dict[str, Any]:
    """细纲字段优先于账本缓存；空列表/空字符串不覆盖已有值。"""
    out = empty_constraints()
    for src in (payload_constraints or {}, outline_constraints or {}):
        for key, value in src.items():
            if key not in out:
                continue
            if value in (None, "", []):
                continue
            out[key] = value
    return out


def apply_commit(payload: dict[str, Any], commit: dict[str, Any]) -> dict[str, Any]:
    """把一章增量写入权威 payload，返回新副本。

    ``commit`` 约定字段见 ``TrackingCommitRequest``。
    """
    state = normalize_payload(deepcopy(payload))
    chapter_id = commit.get("chapter_id")
    if chapter_id:
        state["last_chapter_id"] = str(chapter_id)

    for item in commit.get("foreshadows_planted") or []:
        fid = str(item.get("id") or uuid4())
        state["foreshadows"].append(
            {
                "id": fid,
                "title": str(item.get("title") or "").strip() or "未命名伏笔",
                "description": str(item.get("description") or "").strip(),
                "status": "open",
                "planted_chapter_id": str(chapter_id) if chapter_id else None,
                "payoff_chapter_id": None,
                "character_names": list(item.get("character_names") or []),
            }
        )

    paid_ids = {str(x) for x in (commit.get("foreshadows_paid") or []) if x}
    if paid_ids:
        for fs in state["foreshadows"]:
            if str(fs.get("id")) in paid_ids and fs.get("status") == "open":
                fs["status"] = "paid"
                fs["payoff_chapter_id"] = str(chapter_id) if chapter_id else fs.get(
                    "payoff_chapter_id"
                )

    chars: dict[str, Any] = state["characters"]
    for upd in commit.get("character_updates") or []:
        cid = str(upd.get("character_id") or "")
        if not cid:
            continue
        slot = chars.setdefault(
            cid,
            {
                "name": upd.get("name") or "",
                "location": "",
                "goal": "",
                "known_facts": [],
                "unknown_facts": [],
                "open_threads": [],
            },
        )
        if upd.get("name"):
            slot["name"] = upd["name"]
        if upd.get("location") is not None:
            slot["location"] = upd["location"]
        if upd.get("goal") is not None:
            slot["goal"] = upd["goal"]
        if upd.get("known_facts") is not None:
            slot["known_facts"] = []
            _extend_unique(slot["known_facts"], upd.get("known_facts") or [])
        else:
            _extend_unique(slot["known_facts"], upd.get("known_facts_add") or [])
        if upd.get("unknown_facts") is not None:
            slot["unknown_facts"] = []
            _extend_unique(slot["unknown_facts"], upd.get("unknown_facts") or [])
        else:
            _extend_unique(slot["unknown_facts"], upd.get("unknown_facts_add") or [])
        if upd.get("open_threads") is not None:
            slot["open_threads"] = list(upd["open_threads"])

    _append_timeline(state["author_timeline"], commit.get("author_events") or [], chapter_id)
    _append_timeline(state["reader_timeline"], commit.get("reader_events") or [], chapter_id)

    note = str(commit.get("note") or "").strip()
    if len(note) > CHAPTER_RECORD_MAX_CHARS:
        note = note[:CHAPTER_RECORD_MAX_CHARS]
    if note or chapter_id:
        state["chapter_records"].append(
            {
                "chapter_id": str(chapter_id) if chapter_id else None,
                "note": note,
            }
        )
        # 只保留最近 200 条增量，避免 payload 线性膨胀
        state["chapter_records"] = state["chapter_records"][-200:]

    return state


def _extend_unique(target: list, extras: list) -> None:
    """把 extras 追加到 target，去重且跳过空串。"""
    seen = {str(x) for x in target}
    for item in extras:
        text = str(item).strip()
        if not text or text in seen:
            continue
        target.append(text)
        seen.add(text)


def _append_timeline(timeline: list, events: list, chapter_id: Any) -> None:
    """向作者真相或读者已知追加事件。"""
    for event in events:
        text = str(event).strip()
        if not text:
            continue
        timeline.append(
            {
                "text": text,
                "chapter_id": str(chapter_id) if chapter_id else None,
            }
        )
    timeline[:] = timeline[-80:]


def upsert_foreshadow(payload: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    """新建或更新一条伏笔（不改 revision，由 service 负责）。"""
    state = normalize_payload(deepcopy(payload))
    fid = str(item.get("id") or uuid4())
    existing = next((f for f in state["foreshadows"] if str(f.get("id")) == fid), None)
    record = {
        "id": fid,
        "title": str(item.get("title") or (existing or {}).get("title") or "未命名伏笔"),
        "description": str(
            item.get("description")
            if item.get("description") is not None
            else (existing or {}).get("description")
            or ""
        ),
        "status": str(item.get("status") or (existing or {}).get("status") or "open"),
        "planted_chapter_id": item.get("planted_chapter_id")
        if "planted_chapter_id" in item
        else (existing or {}).get("planted_chapter_id"),
        "payoff_chapter_id": item.get("payoff_chapter_id")
        if "payoff_chapter_id" in item
        else (existing or {}).get("payoff_chapter_id"),
        "character_names": list(
            item.get("character_names")
            if item.get("character_names") is not None
            else (existing or {}).get("character_names")
            or []
        ),
    }
    if existing:
        existing.update(record)
    else:
        state["foreshadows"].append(record)
    return state


def build_context_card(
    payload: dict[str, Any],
    *,
    constraints: dict[str, Any],
    appearing_character_ids: list[str],
) -> dict[str, Any]:
    """派生续写状态卡：只含本章不知道就会写错的信息。"""
    state = normalize_payload(payload)
    char_map: dict[str, Any] = state["characters"]
    appearing = []
    for cid in appearing_character_ids:
        slot = char_map.get(cid)
        if slot:
            appearing.append({"character_id": cid, **slot})

    names = {str(s.get("name") or "") for s in appearing}
    open_fs = []
    for fs in state["foreshadows"]:
        if fs.get("status") != "open":
            continue
        fs_names = set(fs.get("character_names") or [])
        if not appearing_character_ids or not fs_names or fs_names & names:
            open_fs.append(fs)

    card = {
        "constraints": constraints,
        "character_states": appearing,
        "open_foreshadows": open_fs[:20],
        "author_timeline": state["author_timeline"][-8:],
        "reader_timeline": state["reader_timeline"][-8:],
        "last_chapter_id": state.get("last_chapter_id"),
    }
    return card

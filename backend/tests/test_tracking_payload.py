"""追踪账本 payload 纯函数测试。"""
from app.services.tracking_payload import (
    apply_commit,
    build_context_card,
    empty_payload,
    merge_constraints,
    normalize_payload,
)


def test_normalize_fills_missing_keys():
    """空 dict 补齐权威结构。"""
    out = normalize_payload({})
    assert out["foreshadows"] == []
    assert out["characters"] == {}
    assert out["version"] == 1


def test_apply_commit_plants_and_pays_foreshadow():
    """埋笔与兑现走同一权威 JSON。"""
    state = empty_payload()
    state = apply_commit(
        state,
        {
            "chapter_id": "c1",
            "foreshadows_planted": [{"title": "白驴", "description": "灵兽伏笔"}],
            "note": "第一章埋笔",
        },
    )
    assert len(state["foreshadows"]) == 1
    fid = state["foreshadows"][0]["id"]
    assert state["foreshadows"][0]["status"] == "open"
    state = apply_commit(
        state,
        {"chapter_id": "c2", "foreshadows_paid": [fid]},
    )
    assert state["foreshadows"][0]["status"] == "paid"
    assert state["last_chapter_id"] == "c2"


def test_apply_commit_separates_author_and_reader_timeline():
    """作者真相与读者已知分开记。"""
    state = apply_commit(
        empty_payload(),
        {
            "chapter_id": "c1",
            "author_events": ["凶手是哥哥"],
            "reader_events": ["主角收到匿名信"],
        },
    )
    assert state["author_timeline"][0]["text"] == "凶手是哥哥"
    assert state["reader_timeline"][0]["text"] == "主角收到匿名信"


def test_merge_constraints_outline_wins():
    """细纲约束覆盖账本缓存的空值。"""
    merged = merge_constraints(
        {"must_happen": ["对决"], "word_count_min": 2000},
        {"must_happen": ["旧"], "time_anchor": "三日后"},
    )
    assert merged["must_happen"] == ["对决"]
    assert merged["time_anchor"] == "三日后"
    assert merged["word_count_min"] == 2000


def test_context_card_only_loads_appearing_characters():
    """写前只带出场角色状态。"""
    payload = empty_payload()
    payload["characters"] = {
        "a": {"name": "甲", "location": "京城", "goal": "", "known_facts": ["有一封信"], "unknown_facts": ["信是哥哥寄的"], "open_threads": []},
        "b": {"name": "乙", "location": "江南", "goal": "", "known_facts": [], "unknown_facts": [], "open_threads": []},
    }
    card = build_context_card(
        payload,
        constraints={"must_happen": ["对质"]},
        appearing_character_ids=["a"],
    )
    assert len(card["character_states"]) == 1
    assert card["character_states"][0]["name"] == "甲"
    assert "信是哥哥寄的" in card["character_states"][0]["unknown_facts"]

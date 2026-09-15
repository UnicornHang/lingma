"""知情范围启发式。"""
from app.services.knowledge_scope import format_knowledge_brief, scan_knowledge_leaks
from app.services.tracking_payload import empty_payload


def test_scan_flags_name_near_unknown_fact():
    payload = empty_payload()
    payload["characters"] = {
        "a": {
            "name": "林墨",
            "known_facts": [],
            "unknown_facts": ["凶手是哥哥"],
        }
    }
    text = "林墨冷声道：凶手是哥哥，我早就知道了。"
    issues = scan_knowledge_leaks(text, payload)
    assert any("知情越界" in i and "林墨" in i for i in issues)


def test_scan_ignores_secret_without_character_name():
    payload = empty_payload()
    payload["characters"] = {
        "a": {"name": "林墨", "unknown_facts": ["凶手是哥哥"]},
    }
    text = "旁白缓缓揭开：凶手是哥哥。"
    assert scan_knowledge_leaks(text, payload) == []


def test_format_knowledge_brief_includes_unknown():
    payload = empty_payload()
    payload["author_timeline"] = [{"text": "玉佩是诅咒"}]
    payload["characters"] = {"a": {"name": "苏婉", "known_facts": [], "unknown_facts": ["玉佩是诅咒"]}}
    brief = format_knowledge_brief(payload)
    assert "知情范围" in brief
    assert "苏婉" in brief
    assert "玉佩是诅咒" in brief

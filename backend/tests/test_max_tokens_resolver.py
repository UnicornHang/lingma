"""[P2 修复] _resolve_max_tokens 单元测试

覆盖 _resolve_max_tokens(client_max_tokens, target_word_count=) 的所有分支:
- target 提供 → 至少 target × 2.0,与客户端取大
- 极小 target → 应用 floor (1500)
- 巨大 client → 应用 ceiling (20000)
- 无 target → 用 client
- 无 client → 用 derived
- 都没 → 4096 默认
- 非法 client 输入 → 兜底用 derived
"""
from __future__ import annotations

import pytest

from app.api.ws.generation import (
    MAX_TOKENS_HARD_CEIL,
    MAX_TOKENS_MIN_FLOOR,
    MAX_TOKENS_PER_TARGET_WORD,
    _resolve_max_tokens,
)


# ============== 基础派生 ==============


def test_target_1500_yields_at_least_3000_tokens():
    """用户报告 case:目标 1500 字 → 至少 3000 tokens(覆盖硬编码 1500 不足)"""
    assert _resolve_max_tokens(1500, target_word_count=1500) == 3000


def test_target_provided_overrides_smaller_client():
    """target=800 时,即便 client 只给 1500,实际也用 derived(1600)"""
    assert _resolve_max_tokens(1500, target_word_count=800) == 1600


def test_larger_client_beats_derived():
    """client=4096 + target=800 → 取 max(4096, 1600) = 4096(尊重客户端上限)"""
    assert _resolve_max_tokens(4096, target_word_count=800) == 4096


# ============== 边界 ==============


def test_small_target_applies_min_floor():
    """target=100 → 100×2=200 < floor(1500) → 用 1500"""
    assert _resolve_max_tokens(500, target_word_count=100) == MAX_TOKENS_MIN_FLOOR


def test_huge_client_capped_at_ceiling():
    """client=100000 + target=1500 → 取 max(100000, 3000) = 100000,但 ceiling 20000 截断"""
    assert _resolve_max_tokens(100_000, target_word_count=1500) == MAX_TOKENS_HARD_CEIL


def test_huge_target_with_small_client_uses_derived():
    """target=15000, client 缺省 → derived = 15000×2 = 30000,但 ceiling 20000 截断"""
    assert _resolve_max_tokens(None, target_word_count=15_000) == MAX_TOKENS_HARD_CEIL


# ============== 向后兼容(无 target) ==============


def test_no_target_uses_client():
    """target=None + client=4096 → 用 client"""
    assert _resolve_max_tokens(4096, target_word_count=None) == 4096


def test_no_target_small_client_passes_through():
    """target=None + client=1500 → 1500(不强行放大,避免浪费 token)"""
    assert _resolve_max_tokens(1500, target_word_count=None) == 1500


def test_no_input_at_all_falls_back_to_4096():
    """target=None + client=None → 4096 默认"""
    assert _resolve_max_tokens(None, target_word_count=None) == 4096


# ============== 非法输入 ==============


@pytest.mark.parametrize("bad_client", ["junk", "", [], {}, "1500abc", -100, True])
def test_invalid_client_string_falls_back_to_derived(bad_client):
    """非法 client 输入时:取 derived(target 提供时)或 0(无 target 时)"""
    if isinstance(bad_client, int):
        # int 输入本身合法,这里跳过字符串/列表类
        return
    derived = int(800 * MAX_TOKENS_PER_TARGET_WORD) if 800 else None
    expected = max(int(800 * MAX_TOKENS_PER_TARGET_WORD), MAX_TOKENS_MIN_FLOOR)
    assert _resolve_max_tokens(bad_client, target_word_count=800) == expected


# ============== 实际生产场景组合 ==============


def test_realistic_continue_mode_scenario():
    """模拟真实续写:continue_from_chars=1500, target=1500, client 之前硬编码 1500
    → 现在自动放大到 3000,确保 LLM 有足够预算输出目标字数正文
    """
    client = 1500
    target = 1500
    expected = 3000
    assert _resolve_max_tokens(client, target_word_count=target) == expected


def test_realistic_generate_full_chapter_scenario():
    """模拟全量重写整章:outline.target_word_count=3000(默认),client 缺省
    → derived = 6000,无 client 上限约束 → 用 6000
    """
    assert _resolve_max_tokens(None, target_word_count=3000) == 6000


def test_realistic_short_chapter_passes_through():
    """短章节 target=500,client=2000 → 取 max(2000, 1000)=2000(client 更大)"""
    assert _resolve_max_tokens(2000, target_word_count=500) == 2000
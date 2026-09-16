"""Plot Agent 的 Prompt 模板

SYSTEM：短纪律 + 最小 JSON 样例，逼模型少 think、一次只出 1 卷。
USER：只带本卷需要的上下文，避免把全书规划再喂进去。
"""
from __future__ import annotations

import re
from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.work import Work

_EMPTY = "（未指定）"
_VOL_LINE_RE = re.compile(r"第\s*(\d+)\s*卷")
_CN_VOL_LINE_RE = re.compile(r"第\s*([一二三四五六七八九十]+)\s*卷")
_ARABIC_VOL_TITLE_RE = re.compile(r"^第\s*(\d+)\s*卷")
_CN_DIGITS = "零一二三四五六七八九"
_CN_TO_INT = {ch: i for i, ch in enumerate(_CN_DIGITS)}
_LOGLINE_MAX = 80
_HINT_GLOBAL_MAX = 240
_HINT_VOL_MAX = 160


def chinese_volume_num(n: int) -> str:
    """把卷序号转成中文数字：4 → 四，10 → 十。"""
    if n <= 0:
        return str(n)
    if n < 10:
        return _CN_DIGITS[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + _CN_DIGITS[n - 10]
    if n < 100:
        tens, ones = divmod(n, 10)
        head = _CN_DIGITS[tens] + "十"
        return head if ones == 0 else head + _CN_DIGITS[ones]
    return str(n)


def chinese_volume_label(n: int) -> str:
    """卷标题前缀：第四卷。"""
    return f"第{chinese_volume_num(n)}卷"


def _cn_num_to_int(text: str) -> int | None:
    """解析「四」「十」「十一」这类中文数字。"""
    raw = (text or "").strip()
    if not raw:
        return None
    if raw == "十":
        return 10
    if raw.startswith("十"):
        ones = _CN_TO_INT.get(raw[1:])
        return 10 + ones if ones is not None else None
    if raw.endswith("十") and len(raw) == 2:
        tens = _CN_TO_INT.get(raw[0])
        return tens * 10 if tens else None
    if len(raw) == 1:
        return _CN_TO_INT.get(raw)
    return None


def normalize_vol_title(vol_no: int, title: str | None) -> str:
    """把「第4卷 · 人间烽火」统一成「第四卷 · 人间烽火」。"""
    label = chinese_volume_label(vol_no)
    t = (title or "").strip()
    m = _ARABIC_VOL_TITLE_RE.match(t)
    if m:
        rest = t[m.end():].lstrip(" ··")
        return f"{label} · {rest}" if rest else label
    if t.startswith(label):
        return t
    if t:
        return t if "卷" in t[:8] else f"{label} · {t}"
    return label


def _clip(text: str | None, limit: int) -> str:
    """截断过长上下文，减少模型把预算花在复述上。"""
    value = (text or "").strip()
    if not value:
        return _EMPTY
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "…"


def compact_volume_hint(extra_hint: str | None, vol_no: int) -> str:
    """从全书附加说明里只抽出本卷相关句，丢掉其它卷的详细规划。"""
    if not extra_hint or not extra_hint.strip():
        return ""
    global_lines: list[str] = []
    this_vol: list[str] = []
    saw_volume_line = False
    for raw in extra_hint.strip().splitlines():
        line = raw.strip()
        if not line:
            continue
        matched = _VOL_LINE_RE.search(line)
        cn_matched = _CN_VOL_LINE_RE.search(line) if not matched else None
        if not matched and not cn_matched:
            global_lines.append(line)
            continue
        saw_volume_line = True
        line_vol = int(matched.group(1)) if matched else _cn_num_to_int(cn_matched.group(1) if cn_matched else "")
        if line_vol == vol_no:
            this_vol.append(line)
    if not saw_volume_line:
        return _clip(extra_hint, _HINT_GLOBAL_MAX + _HINT_VOL_MAX)
    parts: list[str] = []
    if global_lines:
        parts.append(_clip("；".join(global_lines), _HINT_GLOBAL_MAX))
    if this_vol:
        parts.append("本卷：" + _clip(" ".join(this_vol), _HINT_VOL_MAX))
    return "\n".join(parts)


def build_plot_system_prompt() -> str:
    """单卷大纲的系统提示：样例先行，禁止 think 和多余字段。"""
    return dedent(
        """\
        你是网文主编。立刻输出 JSON，不要前言、不要分析。

        唯一合法形态（volumes 长度必须为 1）：
        {"volumes":[{"vol_no":1,"vol_title":"第一卷 · 青山少年","summary":"本卷写沈砚从武道世家少年到家破人亡。开篇十年苦练枪拳弓，仙门修士踏碎沈家，他以凡人枪术杀出重围，查明灭门与仙凡壁垒有关。中段逃亡查凶，与幸存亲故短暂会合又失散。卷末他带着亡父断枪北上，既要寻回亲人，也要向视凡人命如草芥的修仙体系讨一个说法，为后文踏入仙门埋下仇恨与方法。","chapters":[{"title":"第1章 校场枪鸣","summary":"沈砚校场夺魁，却被路过修士贬为凡人把戏。他连夜加练，镖局血书传来，章末握枪出门，杀意已起。","target_word_count":3000}]}]}

        纪律：
        1. 第一个字符必须是 { ，最后一个字符必须是 } 。
        2. 只输出 JSON 对象，禁止 markdown fence，禁止任何 XML/HTML（包括 <think>）。
        3. 本轮只输出 1 卷，禁止写其它卷。
        4. volume.summary 约200字（180～220），写清本卷起承转合与卷末状态，不要一句了事。
        5. chapter 只有 title、summary、target_word_count。chapter.summary 约60字（50～80），写清起因、转折、章末钩子。
        6. 不要 beats / characters_involved / world_refs / key_events。
        7. 章数必须与用户要求完全一致。JSON 外不要写任何字。
        8. vol_title 必须用中文数字，写成「第一卷 · 短标题」，禁止「第1卷」「第4卷」。
        9. JSON 字符串内部禁止英文双引号 "，口调用「」，书名用《》。
        """
    ).strip()


def build_plot_user_prompt(
    *,
    work: "Work",
    total_volumes: int,
    target_chapter_count: int,
    extra_hint: str | None = None,
) -> str:
    genre = work.genre.value if hasattr(work.genre, "value") else (work.genre or _EMPTY)
    style_keywords = "、".join(work.style_keywords or []) or _EMPTY
    target_audience = "、".join(work.target_audience or []) or _EMPTY

    extra_text = f"\n【用户附加要求】\n{extra_hint.strip()}\n" if extra_hint and extra_hint.strip() else ""

    avg_chapters_per_vol = max(1, target_chapter_count // max(1, total_volumes))

    return dedent(
        f"""\
        【作品标题】{work.title}

        【类型】{genre}
        【一句话简介】{work.logline or _EMPTY}
        【风格关键词】{style_keywords}
        【目标读者】{target_audience}
        【备注】{getattr(work, "notes", None) or _EMPTY}

        【任务约束】
        - 总卷数：{total_volumes}
        - 总章节数：{target_chapter_count}（建议每卷约 {avg_chapters_per_vol} 章,可上下浮动 1-2）
        - 章节目标字数:3000 字左右{extra_text}

        现在请直接输出 JSON，从 {{ 开始，不要 think。
        """
    ).strip()


def split_chapter_counts(total_chapters: int, total_volumes: int) -> list[int]:
    """把总章数尽量均分到各卷。"""
    vols = max(1, total_volumes)
    chapters = max(1, total_chapters)
    base = chapters // vols
    rem = chapters % vols
    return [base + (1 if i < rem else 0) for i in range(vols)]


def build_plot_one_volume_user_prompt(
    *,
    work: "Work",
    vol_no: int,
    total_volumes: int,
    chapter_count: int,
    chapter_start: int,
    extra_hint: str | None = None,
    prior_volumes: list[tuple[int, str, str]] | None = None,
    retry_note: str | None = None,
) -> str:
    """只生成一卷：上下文尽量短，结尾用样例锁格式。"""
    genre = work.genre.value if hasattr(work.genre, "value") else (work.genre or _EMPTY)
    style = "、".join((getattr(work, "style_keywords", None) or [])[:4])
    hint = compact_volume_hint(extra_hint, vol_no)
    extra_text = f"\n{hint}\n" if hint else ""
    prior_text = ""
    if prior_volumes:
        lines = [
            f"- {chinese_volume_label(n)}《{title}》：{_clip(summary, 80)}"
            for n, title, summary in prior_volumes
        ]
        prior_text = "前卷（勿重复）：\n" + "\n".join(lines) + "\n"
    retry_text = f"\n重试：{retry_note}\n" if retry_note else ""
    chapter_end = chapter_start + chapter_count - 1
    example = (
        '{"volumes":[{"vol_no":'
        f"{vol_no}"
        ',"vol_title":"'
        f"{chinese_volume_label(vol_no)} · 短标题"
        '","summary":"（约200字，写本卷起承转合与卷末状态）","chapters":[{"title":"'
        f"第{chapter_start}章 短标题"
        '","summary":"（约60字，写起因、转折、章末钩子）","target_word_count":3000}]}]}'
    )

    return dedent(
        f"""\
        书名：{work.title}
        类型：{genre}
        简介：{_clip(work.logline, _LOGLINE_MAX)}
        风格：{style or _EMPTY}
        {prior_text}{extra_text}{retry_text}
        任务：只写第 {vol_no}/{total_volumes} 卷（标题用「{chinese_volume_label(vol_no)} · 短标题」）。
        - vol_no={vol_no}
        - 正好 {chapter_count} 章（第 {chapter_start}～{chapter_end} 章）
        - 卷 summary 约200字；每章 summary 约60字
        - 每章只要 title、summary、target_word_count=3000
        - volumes 只能有 1 个元素
        - 字符串内不要英文双引号，口调用「」

        按此形态填内容（共 {chapter_count} 章，summary 必须写够字数）：
        {example}

        第一个字符必须是 {{
        """
    ).strip()


def build_plot_expand_system_prompt() -> str:
    """扩写单章细纲：样例先行，禁止 think 和正文。"""
    return dedent(
        """\
        你是网文主编。立刻输出 JSON，不要前言、不要分析。

        唯一合法形态：
        {"title":"第1章 青山枪童","summary":"沈砚十年苦练枪拳弓，父亲带回镖师考核提前的消息。他立志夺魁承继父业，章末月下加练，枪尖挑破晨雾。","beats":["校场苦练见枪意","父亲带回考核消息","月下加练立志"],"characters_involved":["沈砚","沈彪"],"target_word_count":3000,"write_constraints":{"must_happen":["立志参加镖师考核","月下加练挑破晨雾"],"must_not_happen":["本章即灭门"],"time_anchor":"考核公布当夜","stop_point":"枪尖挑破晨雾","end_hook_debt":"考核将至","word_count_min":null,"word_count_max":null}}

        纪律：
        1. 第一个字符必须是 { ，最后一个字符必须是 } 。
        2. 只输出 JSON 对象，禁止 markdown fence，禁止任何 XML/HTML（包括 <think>）。
        3. 禁止写章节正文。只规划简介、节拍、约束锁。
        4. 字段不得增减。summary 4～8 句。beats 3～6 条，每条一句。must_happen 2～6 条。
        5. JSON 字符串内部禁止英文双引号，口调用「」，书名用《》。
        6. 保留用户已有设定，只补可执行细节，不要推翻标题主旨。角色不得提前知道未知真相。
        """
    ).strip()


def build_plot_expand_user_prompt(
    *,
    work: "Work",
    node_title: str,
    node_type: str,
    summary: str,
    beats: list[str],
    characters_involved: list[str],
    target_word_count: int,
    constraints: dict,
    parent_title: str = "",
    knowledge_brief: str = "",
    extra_hint: str | None = None,
) -> str:
    """把当前章纲与作品上下文交给 Plot 扩写。"""
    genre = work.genre.value if hasattr(work.genre, "value") else (work.genre or _EMPTY)
    beats_text = "\n".join(f"- {b}" for b in beats) or "（无）"
    must = constraints.get("must_happen") or []
    must_not = constraints.get("must_not_happen") or []
    extra_text = (
        f"\n【用户附加要求】\n{extra_hint.strip()}\n"
        if extra_hint and extra_hint.strip()
        else ""
    )
    knowledge_text = f"\n{knowledge_brief.strip()}\n" if knowledge_brief.strip() else ""
    parent_text = f"【所属卷】{parent_title}\n" if parent_title else ""

    return dedent(
        f"""\
        【作品标题】{work.title}
        【类型】{genre}
        【一句话简介】{work.logline or _EMPTY}
        {parent_text}【节点类型】{node_type}
        【当前标题】{node_title}
        【当前简介】{summary or _EMPTY}
        【当前节拍】
        {beats_text}
        【出场角色】{"、".join(characters_involved) or _EMPTY}
        【目标字数】{target_word_count}
        【已有必须发生】{"；".join(must) or _EMPTY}
        【已有禁止发生】{"；".join(must_not) or _EMPTY}
        【已有章尾新债】{constraints.get("end_hook_debt") or _EMPTY}
        {knowledge_text}{extra_text}
        请扩写本章细纲，直接输出 JSON。
        """
    ).strip()

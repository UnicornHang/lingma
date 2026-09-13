"""中文网文 AI 痕迹检测器。

移植自 zenstory-ai/oh-story-claudecode 的 ``skills/story-long-write/scripts/check-ai-patterns.js``
(2026-09 快照, v0.7.10)。仅保留对 ZhiMeng 最有价值的 10 类高风险模式,覆盖:

- **blocking**(生成/润色必须改):
  - 否定+肯定翻转("不是 X,而是 Y" 同一句)
  - 反序对比("是 A,不是 B" — not-is 变种)
  - 否定排比("没有 X,没有 Y…连排")
  - 音量反差("声音不高…却…" / "声音不大…却…")
  - em-dash(按功能改写,不机械删)
  - 章尾预告式总结("没人知道/才刚刚开始/正朝着…")
  - 章尾状态总结体("这一夜注定/这一切都结束了/命运的齿轮/新的人生…")

- **advisory**(提示审视,合理用法可保留):
  - 微动作复读(`了+下/阵/圈/道/眼/口/气/会`)
  - 套式反应细节(指节/嘴角/喉结/眼眶 + 轻微动作)
  - 抽象总结复读(命运/棋局/这一刻终于明白)

判定原则:
- 密度与频次双门槛同时满足才报,单次出现不报
- 段落级聚合,支持 `.ai_patterns_whitelist` 文本豁免
- 不重写文本,只报告 findings —— 修复要靠上下文(通常删否定铺垫直接写肯定词,或用动作/细节代替)

调用示例::

    findings = AIPatternDetector().detect(text)
    blocking = [f for f in findings if f.severity == Severity.BLOCKING]

每个 finding 携带:
- ``category`` 短码
- ``severity`` 等级
- ``start/end`` 字符偏移(半开区间)
- ``snippet`` 触发片段(最多 80 字)
- ``message`` 人话描述
- ``rule`` 触发的具体规则(正则或阈值)
"""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """finding 严重等级"""

    BLOCKING = "blocking"  # 必须修(生成/润色阶段硬阻断)
    ADVISORY = "advisory"  # 建议审视(可保留)


@dataclass(slots=True)
class PatternFinding:
    """单条 AI 痕迹命中"""

    category: str
    severity: Severity
    start: int
    end: int
    snippet: str
    message: str
    rule: str = ""

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity.value,
            "start": self.start,
            "end": self.end,
            "snippet": self.snippet,
            "message": self.message,
            "rule": self.rule,
        }


# ==================== 工具函数 ====================


# 跳过引号内(对话/弹幕/系统播报)
_QUOTE_CHARS = frozenset({
    '"',  # ASCII "  (U+0022)
    "'",  # ASCII '  (U+0027)
    "“", "”",  # 中文双引号 " "  (U+201C / U+201D)
    "‘", "’",  # 中文单引号 ' '  (U+2018 / U+2019)
    "「", "」",  # 日式/中文直角引号 (U+300C / U+300D)
    "『", "』",  # 日式二重引号 (U+300E / U+300F)
})


def _iter_narrative_segments(text: str) -> Iterable[tuple[int, int, str]]:
    """把文本切成"叙述段"(引号外)和"对话段"(引号内)两段。

    返回: (start_in_original, end_in_original, segment_text)
    """
    if not text:
        return
    i = 0
    n = len(text)
    buf_start = 0
    in_quote = False
    while i < n:
        ch = text[i]
        if ch in _QUOTE_CHARS:
            # 切到当前 buf 末尾(叙述段),然后切换引号状态
            if not in_quote:
                if buf_start < i:
                    yield buf_start, i, text[buf_start:i]
                buf_start = i
                in_quote = True
            else:
                # 引号结束,产出对话段
                yield buf_start, i + 1, text[buf_start : i + 1]
                buf_start = i + 1
                in_quote = False
        i += 1
    if buf_start < n:
        yield buf_start, n, text[buf_start:n]


def _snippet(text: str, start: int, end: int, *, max_chars: int = 60) -> str:
    """取一段并截断,前后省略号。"""
    raw = text[start:end]
    if len(raw) <= max_chars:
        return raw
    half = max_chars // 2
    return raw[:half] + "…" + raw[-half:]


# ==================== 检测器主类 ====================


class AIPatternDetector:
    """AI 痕迹检测器。无状态,detect() 可重入。"""

    # ===== 阻断类规则 =====

    # 反序对比:"是 A,不是 B" / "是A，不是B" —— not-is 反序变种
    # 不加前置 lookbehind —— "这是 X,不是 Y" 同样该报;
    # 内部要求 ",不是" 已能排除大量误报(单独成句的"是" + 不跟",不是"无关)
    _RE_NOT_IS_REVERSE: ClassVar[re.Pattern[str]] = re.compile(
        r"是[^。！？!?\n]{0,30}[,，][^。！？!?\n]{0,30}?不是[^。！？!?\n]{0,30}",
    )

    # 否定排比(连排):"没有X，没有Y" / "没X，没Y" / "没有X,没有Y,没有Z"
    _RE_NEGATION_PARADE: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:没有|没|无)[^。！？!?\n]{1,20}[,，;；][^。！？!?\n]{0,20}?"
        r"(?:没有|没|无)[^。！？!?\n]{1,20}(?:[,，;；][^。！？!?\n]{0,20}?(?:没有|没|无))",
    )

    # 音量反差:"声音不高…却…" / "声音不大…却…" / "声音很轻…却…"
    _RE_VOICE_CONTRAST: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:声音|嗓音|语气)[^。！？!?\n]{0,12}"
        r"(?:不高|不大|很轻|极轻|压得极低|放得很低)[^。！？!?\n]{0,20}?却[^。！？!?\n]{0,30}",
    )

    # em-dash(中文破折号 ——) —— 用于功能性标记,成片出现提示
    _RE_EM_DASH: ClassVar[re.Pattern[str]] = re.compile(r"——")

    # 章尾预告式总结:篇章最后 ~200 字窗口内
    _RE_TRAILER_ENDING: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:没人|没有人|谁都不知道|谁也不曾想到)[^。！？!?\n]{0,40}"
        r"(?:才(刚刚)?开始|正(在|朝着)[^。！？!?\n]{0,8}(?:压|袭|来))",
    )
    _RE_TRAILER_SUMMARY: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:这一夜(注定|终将)|这一切都(结束了|才刚开始)|"
        r"新的人生(才)?刚刚开始|命运的齿轮(开始)?转动|"
        r"故事(才)?刚刚开始)",
    )

    # ===== 建议类规则 =====

    # 微动作复读:`了+下/阵/圈/道/眼/口/气/会`
    _RE_MICRO_ACTION: ClassVar[re.Pattern[str]] = re.compile(
        r"了(?:[一两三几半])?[下阵圈道眼口气会]",
    )

    # 套式反应细节:身体部位 + 轻微动作
    # gap 上限 8:既覆盖"他肩膀在寒风中不由自主地绷紧"这种典型链,
    # 又防止连续多组身体部位(逗号分隔)被合并成一个 match
    _RE_STOCK_REACTION: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:指尖|手指|指节|手背|掌心|拳头|袖口|衣角|裙角|下唇|嘴唇|唇角|嘴角|眉头|眼底|眸光|目光|视线|肩膀|呼吸)"
        r"[^。！？!?\n]{0,8}"
        r"(?:轻轻|微微|缓缓|悄然|不自觉|无意识|下意识|攥紧|握紧|收紧|绞紧|泛白|发白|叩|敲|摩挲|抿紧|抿成|移开|垂下|躲开|一颤|颤了?一下|顿了?一下)",
    )

    # 抽象总结复读:命运/棋局/这一刻终于明白
    _RE_ABSTRACT_SUMMARY: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:这一刻(?:他|她)?(?:终于)?(?:明白|懂得|知道)|"
        r"命运(?:的)?(?:齿轮|之轮|的(?:一|那)(?:刻|瞬间))|"
        r"如同?一盘(?:棋|对局|大棋))",
    )

    # ===== 否定+肯定翻转(同句) =====
    # 例:"不是 X,而是 Y" / "并非 X,而是 Y"
    _RE_NEG_POS_FLIP: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:不是|并非|并不是|并?不?是|绝非|并不是)"
        r"[^。！？!?\n]{0,30}?[,，;；]"
        r"[^。！？!?\n]{0,30}?"
        r"(?:而是|就是|而是说|恰恰是|其实是)",
    )

    # ===== 阈值 =====
    MICRO_ACTION_MIN_HITS = 5  # 全文至少 5 次才报
    STOCK_REACTION_MIN_HITS = 3  # 全文至少 3 处才报
    ABSTRACT_SUMMARY_MIN_HITS = 2
    EM_DASH_MIN_HITS = 6  # 全文至少 6 个破折号才报
    TRAILER_WINDOW_CHARS = 250  # 章尾窗口

    # ===== 白名单:豁免正则(命中后跳过) =====
    DEFAULT_WHITELIST: ClassVar[list[re.Pattern[str]]] = [
        # 合理对话内自指
        re.compile(r"\"[^\"]{0,40}不是[^\"]{0,40}\""),
        re.compile(r"\"[^\"]{0,40}没有[^\"]{0,40}\""),
    ]

    def __init__(self, *, extra_whitelist: Iterable[re.Pattern[str]] | None = None) -> None:
        self._whitelist: list[re.Pattern[str]] = list(self.DEFAULT_WHITELIST)
        if extra_whitelist:
            self._whitelist.extend(extra_whitelist)

    # ===== 入口 =====

    def detect(self, text: str) -> list[PatternFinding]:
        """跑全部规则,返回 findings(已按 start 排序)。"""
        if not text or not text.strip():
            return []

        findings: list[PatternFinding] = []
        findings.extend(self._detect_neg_pos_flip(text))
        findings.extend(self._detect_not_is_reverse(text))
        findings.extend(self._detect_negation_parade(text))
        findings.extend(self._detect_voice_contrast(text))
        findings.extend(self._detect_em_dash(text))
        findings.extend(self._detect_trailer_ending(text))
        findings.extend(self._detect_micro_action_tic(text))
        findings.extend(self._detect_stock_reaction_tic(text))
        findings.extend(self._detect_abstract_summary_tic(text))

        # 白名单过滤:任何被白名单命中的区间,对应 finding 丢弃
        findings = self._apply_whitelist(text, findings)

        findings.sort(key=lambda f: f.start)
        return findings

    # ===== 白名单 =====

    def _apply_whitelist(
        self, text: str, findings: list[PatternFinding]
    ) -> list[PatternFinding]:
        if not findings or not self._whitelist:
            return findings
        keep: list[PatternFinding] = []
        for f in findings:
            span_text = text[f.start : f.end]
            whitelisted = False
            for pat in self._whitelist:
                if pat.search(span_text):
                    whitelisted = True
                    break
            if not whitelisted:
                keep.append(f)
        return keep

    # ===== 阻断类 =====

    def _detect_neg_pos_flip(self, text: str) -> list[PatternFinding]:
        return [
            PatternFinding(
                category="neg-pos-flip",
                severity=Severity.BLOCKING,
                start=m.start(),
                end=m.end(),
                snippet=_snippet(text, m.start(), m.end()),
                message="同句否定+肯定翻转(不是X,而是Y),删除否定铺垫直接写肯定词",
                rule="不是/并非 + , + 而是/就是",
            )
            for m in self._RE_NEG_POS_FLIP.finditer(text)
        ]

    def _detect_not_is_reverse(self, text: str) -> list[PatternFinding]:
        return [
            PatternFinding(
                category="not-is-reverse",
                severity=Severity.BLOCKING,
                start=m.start(),
                end=m.end(),
                snippet=_snippet(text, m.start(), m.end()),
                message="反序对比(是A,不是B),AI 反序变种,改写或拆句",
                rule="是 + , + 不是",
            )
            for m in self._RE_NOT_IS_REVERSE.finditer(text)
        ]

    def _detect_negation_parade(self, text: str) -> list[PatternFinding]:
        return [
            PatternFinding(
                category="negation-parade",
                severity=Severity.BLOCKING,
                start=m.start(),
                end=m.end(),
                snippet=_snippet(text, m.start(), m.end()),
                message="否定排比(没有X,没有Y…),成片出现有模板感,拆开或换说法",
                rule="没有/没 + , + 没有/没 + …",
            )
            for m in self._RE_NEGATION_PARADE.finditer(text)
        ]

    def _detect_voice_contrast(self, text: str) -> list[PatternFinding]:
        return [
            PatternFinding(
                category="voice-contrast",
                severity=Severity.BLOCKING,
                start=m.start(),
                end=m.end(),
                snippet=_snippet(text, m.start(), m.end()),
                message="音量反差(声音不高…却…),改用动作或直接陈述",
                rule="声音/嗓音/语气 + 不高/不大/很轻 + 却",
            )
            for m in self._RE_VOICE_CONTRAST.finditer(text)
        ]

    def _detect_em_dash(self, text: str) -> list[PatternFinding]:
        hits = list(self._RE_EM_DASH.finditer(text))
        if len(hits) < self.EM_DASH_MIN_HITS:
            return []
        # 一次性报一条聚合 finding,指向首个 em-dash
        first = hits[0]
        return [
            PatternFinding(
                category="em-dash-density",
                severity=Severity.BLOCKING,
                start=first.start(),
                end=first.end(),
                snippet=f"共 {len(hits)} 处 ——",
                message=f"破折号 —— 全文出现 {len(hits)} 次,提示按功能改写",
                rule=f"em-dash count ≥ {self.EM_DASH_MIN_HITS}",
            )
        ]

    def _detect_trailer_ending(self, text: str) -> list[PatternFinding]:
        # 章尾窗口
        window_start = max(0, len(text) - self.TRAILER_WINDOW_CHARS)
        window = text[window_start:]
        findings: list[PatternFinding] = []
        for pat, cat, msg in [
            (
                self._RE_TRAILER_ENDING,
                "trailer-ending",
                "章尾预告式总结(没人知道/才刚开始/正朝着…压了过去),删除或换悬念留白",
            ),
            (
                self._RE_TRAILER_SUMMARY,
                "trailer-summary",
                "章尾状态总结体(这一夜注定/这一切都结束了/命运的齿轮),改成动作或场景收尾",
            ),
        ]:
            for m in pat.finditer(window):
                findings.append(
                    PatternFinding(
                        category=cat,
                        severity=Severity.BLOCKING,
                        start=window_start + m.start(),
                        end=window_start + m.end(),
                        snippet=_snippet(text, window_start + m.start(), window_start + m.end()),
                        message=msg,
                        rule=cat,
                    )
                )
        return findings

    # ===== 建议类 =====

    def _detect_micro_action_tic(self, text: str) -> list[PatternFinding]:
        # 只扫叙述段(引号外);对话/系统播报里成片的"了+下"是正常表达
        hits: list[re.Match[str]] = []
        for seg_start, _, seg_text in _iter_narrative_segments(text):
            if not seg_text or seg_text[0] in _QUOTE_CHARS:
                continue  # 跳过对话段
            for m in self._RE_MICRO_ACTION.finditer(seg_text):
                # 还原到原文本位置
                hits.append(
                    type("Hit", (), {"start": seg_start + m.start(), "end": seg_start + m.end()})()
                )
        if len(hits) < self.MICRO_ACTION_MIN_HITS:
            return []
        # 报聚合 finding
        first = hits[0]
        return [
            PatternFinding(
                category="micro-action-tic",
                severity=Severity.ADVISORY,
                start=first.start,
                end=first.end,
                snippet=f"共 {len(hits)} 处 `了+下/阵/圈…`",
                message=f"微动作复读(了+下/阵/圈/道),{len(hits)} 处,提示电报体风险",
                rule=f"micro-action count ≥ {self.MICRO_ACTION_MIN_HITS}",
            )
        ]

    def _detect_stock_reaction_tic(self, text: str) -> list[PatternFinding]:
        hits = list(self._RE_STOCK_REACTION.finditer(text))
        if len(hits) < self.STOCK_REACTION_MIN_HITS:
            return []
        first = hits[0]
        return [
            PatternFinding(
                category="stock-reaction-tic",
                severity=Severity.ADVISORY,
                start=first.start(),
                end=first.end(),
                snippet=f"共 {len(hits)} 处身体部位+轻量动作",
                message=f"套式反应细节(指节/嘴角/喉结+轻轻/微微/攥紧),{len(hits)} 处,提示审视",
                rule=f"stock-reaction count ≥ {self.STOCK_REACTION_MIN_HITS}",
            )
        ]

    def _detect_abstract_summary_tic(self, text: str) -> list[PatternFinding]:
        hits = list(self._RE_ABSTRACT_SUMMARY.finditer(text))
        if len(hits) < self.ABSTRACT_SUMMARY_MIN_HITS:
            return []
        first = hits[0]
        return [
            PatternFinding(
                category="abstract-summary-tic",
                severity=Severity.ADVISORY,
                start=first.start(),
                end=first.end(),
                snippet=f"共 {len(hits)} 处抽象总结",
                message=f"抽象总结复读(命运/这一刻终于明白/如同棋局),{len(hits)} 处,提示审视",
                rule=f"abstract-summary count ≥ {self.ABSTRACT_SUMMARY_MIN_HITS}",
            )
        ]


# ==================== 便捷函数 ====================


def detect_ai_patterns(text: str) -> list[dict]:
    """便捷函数,直接返回 dict 列表(供 API 序列化)。"""
    detector = AIPatternDetector()
    return [f.to_dict() for f in detector.detect(text)]


def summarize(findings: list[PatternFinding] | list[dict]) -> dict:
    """汇总一组 findings,返回按 category/severity 聚合的统计。"""
    by_cat: dict[str, int] = {}
    by_sev: dict[str, int] = {"blocking": 0, "advisory": 0}
    for f in findings:
        if isinstance(f, PatternFinding):
            cat = f.category
            sev = f.severity.value
        else:
            cat = f["category"]
            sev = f["severity"]
        by_cat[cat] = by_cat.get(cat, 0) + 1
        by_sev[sev] = by_sev.get(sev, 0) + 1
    return {
        "total": len(findings),
        "by_category": by_cat,
        "by_severity": by_sev,
    }

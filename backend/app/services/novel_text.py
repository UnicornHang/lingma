"""网文正文后处理：剥提示词泄漏、补自然段、转 TipTap。

续写/润色模型常把整章写成一段，或把 JSON 样例里的尖括号占位符抄进正文。
入库和回写编辑器前统一走这里，保证段落可排版、检测能落到「本段」。
"""
from __future__ import annotations

import re

# 润色 JSON 样例被模型原样写入正文的常见泄漏
_LEAK_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"<改写后片段[^>]*>"),
    re.compile(r"<原片段[^>]*>"),
    re.compile(r"<finding[^>]*>"),
    re.compile(r"若判定无需改写[,，]?填原文"),
    re.compile(r"</?think>"),
)

_SENT_END_RE = re.compile(r"(?<=[。！？…])")
# 句末后接开引号 → 对话另起一段
_DIALOGUE_OPEN_RE = re.compile(r"([。！？…])\s*(?=[「“\"『])")
# 闭引号后接叙述
_DIALOGUE_CLOSE_RE = re.compile(r"([」”\"』])\s+(?=\S)")
# 场景切换：句末后的独立破折号，不切「沈砚——中靶」这种句内破折号
_SCENE_BREAK_RE = re.compile(r"([。！？…」”\"』])\s*——\s+")

_MAX_PARA = 120


def strip_prompt_leaks(text: str) -> str:
    """去掉润色/思维链提示词泄漏，避免尖括号样例进入正文。"""
    if not text:
        return text
    out = text
    for pat in _LEAK_RES:
        out = pat.sub("", out)
    return out


def is_leaked_rewrite(text: str) -> bool:
    """改写结果是否是提示词占位，而不是可落地的句子。"""
    if not text or not text.strip():
        return True
    s = text.strip()
    if s.startswith("<") or "改写后片段" in s or "若判定无需改写" in s:
        return True
    if s.startswith("{") and "rewritten" in s:
        return True
    return False


def normalize_novel_paragraphs(text: str, *, max_para: int = _MAX_PARA) -> str:
    """把墙式正文切成网文自然段：对话独立、场景切换空行、过长段按句切开。"""
    if not text or not text.strip():
        return text or ""
    t = strip_prompt_leaks(text).replace("\r\n", "\n").replace("\r", "\n")
    t = t.strip()
    if t.count("\n") >= 3:
        parts = [p.strip() for p in re.split(r"\n+", t) if p.strip()]
        return "\n\n".join(parts)

    t = _DIALOGUE_OPEN_RE.sub(r"\1\n\n", t)
    t = _DIALOGUE_CLOSE_RE.sub(r"\1\n\n", t)
    t = _SCENE_BREAK_RE.sub(r"\1\n\n——\n\n", t)
    return _split_long_blocks(t, max_para)


def _split_long_blocks(text: str, max_para: int) -> str:
    """超长块在句号处切开，每段大约 max_para 字。"""
    out: list[str] = []
    for block in re.split(r"\n+", text):
        block = block.strip()
        if not block:
            continue
        if len(block) <= max_para:
            out.append(block)
            continue
        buf = ""
        for sent in _SENT_END_RE.split(block):
            if not sent:
                continue
            if buf and len(buf) + len(sent) > max_para:
                out.append(buf.strip())
                buf = sent
            else:
                buf += sent
        if buf.strip():
            out.append(buf.strip())
    return "\n\n".join(out)


def plain_to_tiptap_doc(plain: str) -> dict:
    """纯文本按空行/换行切成 TipTap doc，空文给一个空段。"""
    normalized = normalize_novel_paragraphs(plain) if plain else ""
    blocks = [b.strip() for b in re.split(r"\n+", normalized) if b.strip()]
    if not blocks:
        return {"type": "doc", "content": [{"type": "paragraph"}]}
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": block}],
            }
            for block in blocks
        ],
    }

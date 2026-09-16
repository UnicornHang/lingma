"""大纲 JSON 抽取：截断、夹 think、单章脏数据时尽量保住已写完的卷。"""
from __future__ import annotations

import json
import logging
import re

from app.agents.character_agent import (
    _extract_json_object,
    _matching_brace_end,
    _strip_llm_think,
)
from app.prompts.plot_prompts import chinese_volume_label, normalize_vol_title
from app.schemas.outline import PlotChapter, PlotVolume

logger = logging.getLogger(__name__)

# 单卷失败后最多再试几次，避免 think/截断导致整卷跳过
OUTLINE_VOLUME_ATTEMPTS = 3

def _unescape_json_str(value: str) -> str:
    """把 JSON 字符串字面量还原成原文。"""
    try:
        parsed = json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value
    return parsed if isinstance(parsed, str) else value


_STR_FIELD_RE = re.compile(r'"(vol_title|summary)"\s*:\s*"((?:\\.|[^"\\])*)"')
_VOL_NO_RE = re.compile(r'"vol_no"\s*:\s*(\d+)')


def _unescape_loose(value: str) -> str:
    """尽量还原常见转义，失败则原样返回。"""
    return (
        value.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def _normalize_inner_ascii_quotes(s: str) -> str:
    """把未转义英文双引号配成「」，避免简介在第一个引号处被截断。"""
    if '"' not in s:
        return s
    out: list[str] = []
    opening = True
    for ch in s:
        if ch == '"':
            out.append("「" if opening else "」")
            opening = not opening
        else:
            out.append(ch)
    return "".join(out)


def _extract_json_string_until_key(text: str, key: str, next_key: str) -> str:
    """取出 "key":"值，允许值内有未转义引号，直到下一个字段 next_key。"""
    marker = f'"{key}"'
    i = text.find(marker)
    if i < 0:
        return ""
    colon = text.find(":", i + len(marker))
    if colon < 0:
        return ""
    j = colon + 1
    n = len(text)
    while j < n and text[j] in " \n\r\t":
        j += 1
    if j >= n or text[j] != '"':
        return ""
    start = j + 1
    nxt = text.find(f'"{next_key}"', start)
    raw = text[start:] if nxt < 0 else text[start:nxt]
    raw = raw.rstrip()
    if raw.endswith(","):
        raw = raw[:-1].rstrip()
    if raw.endswith('"'):
        raw = raw[:-1]
    return _normalize_inner_ascii_quotes(_unescape_loose(raw))


def salvage_json_dict_array(text: str, key: str) -> list[dict]:
    """从 `"key":[{...},{...` 中捞出已经写完的对象，遇到截断即停。"""
    if not text:
        return []
    marker = text.find(f'"{key}"')
    if marker < 0:
        return []
    bracket = text.find("[", marker)
    if bracket < 0:
        return []
    items: list[dict] = []
    i = bracket + 1
    n = len(text)
    while i < n:
        while i < n and text[i] in " \n\r\t,":
            i += 1
        if i >= n or text[i] == "]":
            break
        if text[i] != "{":
            break
        end = _matching_brace_end(text, i)
        if end is None:
            break
        snippet = text[i : end + 1]
        try:
            parsed = json.loads(snippet)
        except json.JSONDecodeError:
            break
        if isinstance(parsed, dict):
            items.append(parsed)
        i = end + 1
    return items


def salvage_volume_dicts(text: str) -> list[dict]:
    """从被截断的 {"volumes":[{...},{... 中捞出已经写完的卷对象。"""
    return salvage_json_dict_array(text, "volumes")


def salvage_partial_volume(text: str) -> dict | None:
    """单卷 JSON 在 chapters 中途被截断时，捞出已闭合的章。"""
    if not text:
        return None
    chapters = salvage_json_dict_array(text, "chapters")
    if not chapters:
        return None
    cut = text.find('"chapters"')
    head = text[:cut] if cut >= 0 else text
    vol_no = 1
    no_m = _VOL_NO_RE.search(head)
    if no_m:
        vol_no = int(no_m.group(1))
    title = _extract_json_string_until_key(text, "vol_title", "summary")
    summary = _extract_json_string_until_key(text, "summary", "chapters")
    if not title or not summary:
        for m in _STR_FIELD_RE.finditer(head):
            field, value = m.group(1), m.group(2)
            decoded = _unescape_json_str(value)
            if field == "vol_title" and not title:
                title = decoded
            elif field == "summary" and not summary:
                summary = decoded
    return {
        "vol_no": vol_no,
        "vol_title": title or chinese_volume_label(vol_no),
        "summary": summary,
        "chapters": chapters,
    }


def coerce_plot_volume(item: dict) -> PlotVolume | None:
    """单章校验失败时丢掉该章，而不是整卷作废。"""
    raw_chapters = item.get("chapters") or []
    good: list[dict] = []
    if isinstance(raw_chapters, list):
        for ch in raw_chapters:
            if not isinstance(ch, dict):
                continue
            try:
                PlotChapter.model_validate(ch)
            except Exception:
                continue
            good.append(ch)
    vol_no = int(item.get("vol_no") or 1)
    payload = {
        **item,
        "vol_no": vol_no,
        "chapters": good,
        "vol_title": normalize_vol_title(vol_no, item.get("vol_title")),
        "summary": _normalize_inner_ascii_quotes(str(item.get("summary") or "")),
    }
    try:
        vol = PlotVolume.model_validate(payload)
    except Exception as e:
        logger.warning("PlotVolume 校验失败: %s", e)
        return None
    if not vol.chapters:
        return None
    return vol


def parse_outline_volumes(raw_content: str) -> list[PlotVolume]:
    """从 LLM 原文抽出 PlotVolume 列表；截断/夹 think 时尽量 salvage。"""
    json_text = _extract_json_object(raw_content or "")
    volumes_payload: list | None = None
    if json_text:
        try:
            parsed = json.loads(json_text)
            if isinstance(parsed, dict):
                maybe = parsed.get("volumes")
                if isinstance(maybe, list):
                    volumes_payload = maybe
                elif "chapters" in parsed or "vol_title" in parsed:
                    volumes_payload = [parsed]
                else:
                    volumes_payload = None
            elif isinstance(parsed, list):
                volumes_payload = parsed
        except json.JSONDecodeError:
            volumes_payload = salvage_volume_dicts(json_text)
    stripped = _strip_llm_think(raw_content or "") or raw_content
    if not volumes_payload:
        volumes_payload = salvage_volume_dicts(stripped)

    volumes: list[PlotVolume] = []
    for i, item in enumerate(volumes_payload or []):
        if not isinstance(item, dict):
            logger.warning("PlotAgent 第 %d 卷不是 dict: %r", i, item)
            continue
        vol = coerce_plot_volume(item)
        if vol is None:
            logger.warning("PlotAgent 第 %d 卷校验后无可用章", i)
            continue
        volumes.append(vol)

    source = json_text or stripped or ""
    partial = salvage_partial_volume(source)
    extra = coerce_plot_volume(partial) if partial else None
    if volumes:
        if extra is not None:
            v0 = volumes[0]
            updates: dict = {}
            if extra.summary and len(extra.summary) > len(v0.summary or ""):
                updates["summary"] = extra.summary
            if len(extra.chapters) > len(v0.chapters):
                updates["chapters"] = extra.chapters
            if extra.vol_title and extra.vol_title != v0.vol_title:
                updates["vol_title"] = extra.vol_title
            if updates:
                volumes[0] = v0.model_copy(update=updates)
        return volumes
    return [extra] if extra is not None else []


def parse_one_volume(raw_content: str, vol_no: int) -> PlotVolume | None:
    """解析本轮应产出的那一卷，并强制 vol_no 与中文卷名。"""
    volumes = parse_outline_volumes(raw_content)
    if not volumes:
        return None
    v = volumes[0]
    return v.model_copy(
        update={
            "vol_no": vol_no,
            "vol_title": normalize_vol_title(vol_no, v.vol_title),
        }
    )

"""Editor Agent 的 Prompt 模板

SYSTEM 角色 = 资深中文小说编辑 + AI 痕迹辨别经验;
USER 角色 = 原章节正文 + 检测器产出的 findings 列表 + 改写约束。

设计原则:
- 给 LLM 看具体 finding(类别 + 片段 + 位置),不做空泛的"请写得自然一点"
- 要求 LLM 逐条给出修改理由与修改结果
- 输出稳定 JSON,便于 API 序列化与前端高亮
- 强制保留原意、保留已有对话与设定,只改"AI 腔"
"""
from __future__ import annotations

import json
from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.ai_pattern_detector import PatternFinding


def build_editor_system_prompt() -> str:
    return dedent(
        """\
        你是一位资深中文网络小说编辑,同时熟悉 AI 生成文本的常见痕迹。
        你的任务是基于检测器给出的 finding 列表,**只重写有问题的片段**,
        保留原意、保留已有对话与设定、保留原作文风。

        改写原则(由硬到软):
        1. 阻断类(blocking)finding 必须处理:删除否定铺垫、用动作或细节替代抽象总结、把对比句拆成动作。
        2. 建议类(advisory)finding 审慎处理:合理用法可保留,只在明显重复或电报体时改写。
        3. 不要修改未在 finding 中标出的句子 —— 你的工作是"去 AI 味",不是改稿。
        4. 不要加入新设定、新角色、新剧情 —— 改了出问题。
        5. 不要输出 markdown fence;直接输出 JSON。

        输出格式(JSON object,严格遵守):
        {
          "rewrites": [
            {
              "category": "<finding 类别>",
              "original": "<原片段>",
              "rewritten": "<改写后片段;若判定无需改写,填原文>",
              "reason": "<一句话说明为什么要这样改,便于用户审阅>"
            }
          ],
          "summary": "<整章一句话总结:本次主要消除了哪些 AI 痕迹,共 N 处>"
        }
        """
    ).strip()


# 向后兼容
SYSTEM_PROMPT = build_editor_system_prompt()


def build_editor_user_prompt(
    *,
    chapter_text: str,
    findings: list["PatternFinding"],
    style_keywords: list[str] | None = None,
    preserve_length: bool = True,
) -> str:
    """构造 Editor 的 user prompt。

    - chapter_text: 章节原文(截取 finding 周边 ±60 字作为上下文)
    - findings: 检测器输出,按 start 排序
    - style_keywords: 作品的风格关键词,作为改写风格锚
    - preserve_length: 是否要求改写后字数变化不超过 ±15%
    """
    parts: list[str] = []

    style_line = ""
    if style_keywords:
        style_line = f"【文风关键词】{('、'.join(style_keywords))}\n"

    length_line = (
        "【字数约束】改写后片段与原片段字数偏差不超过 ±15%。\n"
        if preserve_length
        else "【字数约束】不做字数限制。\n"
    )

    parts.append(
        dedent(
            f"""\
            请按下列 finding 列表,逐条重写【章节正文】中有 AI 痕迹的片段。

            {style_line}{length_line}
            【章节正文】
            {chapter_text}

            【finding 列表(共 {len(findings)} 条)】
            """
        ).rstrip()
    )

    # 每条 finding 给一段上下文(±60 字)
    for i, f in enumerate(findings, 1):
        ctx_start = max(0, f.start - 60)
        ctx_end = min(len(chapter_text), f.end + 60)
        context = chapter_text[ctx_start:ctx_end]
        sev = f.severity.value if hasattr(f.severity, "value") else f.severity
        parts.append(
            f"\n[{i}] 类别={f.category} 等级={sev}\n"
            f"    片段：{f.snippet}\n"
            f"    上下文：…{context}…\n"
            f"    提示：{f.message}"
        )

    parts.append(
        "\n\n请输出 JSON object,字段: rewrites(数组,长度等于 finding 数)、summary(字符串)。"
    )

    return "\n".join(parts)


def format_findings_for_prompt(findings: list["PatternFinding"]) -> str:
    """把 findings 序列化为可读 JSON(供日志/调试)。"""
    return json.dumps([f.to_dict() for f in findings], ensure_ascii=False, indent=2)

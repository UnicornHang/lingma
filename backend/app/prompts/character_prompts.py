"""Character Agent 的 Prompt 模板

SYSTEM：角色设计纪律（JSON / 强 schema / 不 thinking aloud / 不 markdown fence）。
USER：作品上下文 + 已有角色清单 + 用户附加 hint。
"""
from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.character import Character
    from app.models.work import Work

_EMPTY = "（未指定）"


def build_character_system_prompt() -> str:
    return dedent(
        f"""\
        你是资深网文人物设定师。任务：根据给定的作品上下文，**批量设计** N 个互不雷同的角色卡。

        【输出纪律 - 严格遵守】
        1. **只输出 JSON 对象**，禁止任何 markdown fence（``` / ```json / ```JSON）。
        2. **禁止 thinking aloud**：不要输出 "Let me"、"I should"、"Wait"、"好的" 等过渡句。
        3. JSON 顶层结构：{{"cards": [{{...}}, ...]}}，数组长度严格等于请求的 N。
        4. 字段名严格使用以下 schema 中的英文 key，不得增减字段：
           - name (str, 非空)
           - role (str, 必须是 protagonist / antagonist / supporting / narrator 之一)
           - basic_info (str, 1-3 句，外貌/年龄/身份)
           - personality (str, 1-2 句，性格关键词 + 1 句解释)
           - backstory (str, 1-3 句，出身 + 关键经历)
           - relationships (str, 1 句格式"<对方名>:<关系>:<互动动态>"，多条用换行分隔；可空字符串)
           - arc (str, 1-2 句，人物弧开端与结尾状态)
           - voice_samples (str, 1-2 句代表性台词；用引号包裹；可空字符串)
           - raw_text (str, 200-400 字的人设自由描述,包含外形/性格/背景/口癖等)
        5. 不要给字段填 "无"、"N/A"、"待定" 等占位 — 实在没有就省略或留空字符串。
        6. 与已有角色重名时,应换一个名字(避免冲突)。
        7. 角色之间关系网应相互呼应,避免孤立。

        【风格适配】
        - 紧贴作品的类型与风格关键词。
        - 配角应服务主线,避免抢主角戏。
        - 反派动机要合理,避免脸谱化。
        """
    ).strip()


def build_character_user_prompt(
    *,
    work: "Work",
    existing_characters: "list[Character]",
    count: int,
    focus: str,
    extra_hint: str | None = None,
) -> str:
    """构造 Character Agent 的 user prompt。"""
    genre = work.genre.value if hasattr(work.genre, "value") else (work.genre or _EMPTY)
    style_keywords = "、".join(work.style_keywords or []) or _EMPTY
    target_audience = "、".join(work.target_audience or []) or _EMPTY

    existing_lines: list[str] = []
    for c in existing_characters:
        existing_lines.append(f"  - {c.name}（{c.role}）")
    existing_text = "\n".join(existing_lines) if existing_lines else "  （暂无）"

    focus_text = {
        "protagonist": "主角（1-2 人，核心人物，可深挖）",
        "antagonist": "反派/对立面（需有可信动机）",
        "supporting": "配角（围绕主角、推动主线）",
        "all": "混合（包含主角 + 配角 + 反派）",
    }.get(focus, "配角（围绕主角、推动主线）")

    extra_text = f"\n【用户附加要求】\n{extra_hint.strip()}\n" if extra_hint and extra_hint.strip() else ""

    return dedent(
        f"""\
        【作品标题】{work.title}

        【类型】{genre}
        【一句话简介】{work.logline or _EMPTY}
        【风格关键词】{style_keywords}
        【目标读者】{target_audience}
        【备注】{work.notes or _EMPTY}

        【已有角色（请避免重名）】{existing_lines and '' or ''}
{existing_text}

        【本次任务】{extra_text}
        请生成 {count} 个角色，焦点：{focus_text}。

        现在请直接输出 JSON。
        """
    ).strip()

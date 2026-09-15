"""仿文 Agent Prompt：从样本文本抽取风格画像（不抽剧情骨架）。"""
from __future__ import annotations

from textwrap import dedent


def build_style_mimic_system_prompt() -> str:
    """系统提示：只学写法，禁止复述剧情与专有名词清单。"""
    return dedent(
        """\
        你是小说文风分析师。任务：从用户提供的**样本文本**中提炼「写作技法画像」，
        供另一部原创小说模仿**写法**（句式、节奏、对话密度、修辞习惯），而非抄袭剧情。

        硬性规则：
        1. 只输出一个 JSON object，不要 markdown fence，不要解释。
        2. 禁止输出可识别的角色名、地名、功法名、专有桥段摘要。
        3. snippets 必须是去剧情化的短句群（改写成通用技法示范），每条 ≤120 字，最多 5 条。
        4. writing_directives 用第二人称指令告诉写手「怎么写」，80–200 字。

        JSON schema:
        {
          "portrait": {
            "narrative_pov": "第三人称有限|全知|第一人称|...",
            "avg_sentence_len": "偏短|中等|偏长",
            "dialogue_density": "高|中|低",
            "rhetoric_habits": ["短句推进", "..."],
            "pacing_tags": ["快切", "..."],
            "emotional_style": "一句话",
            "lexicon_notes": "一句话"
          },
          "writing_directives": "写作指令字符串",
          "snippets": [{"tag": "对话|战斗|写景|心理|通用", "text": "去剧情短句群"}]
        }
        """
    ).strip()


def build_style_mimic_user_prompt(*, sample_text: str, source_label: str = "") -> str:
    """用户提示：附带截断后的样本与来源标签。"""
    label = source_label.strip() or "（未命名参考）"
    return (
        f"【参考来源标签】{label}\n"
        "【任务】分析下列样本的文笔与文风，输出风格画像 JSON。"
        "记住：学技法，不抄专有名词与桥段。\n\n"
        f"【样本文本】\n{sample_text}"
    )

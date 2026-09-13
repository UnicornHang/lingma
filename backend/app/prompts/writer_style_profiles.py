"""Writer 文风裁决 —— 把 ``work.style_keywords`` 列表展开成具体写作指令。

设计:第一版用硬编码词典。每个关键词对应一段 30-80 字的写作指令,LLM 看到的是
"怎么做"而非"做什么"。未知关键词会触发降级,空列表走默认基调。

后续接入数据库时可把 ``STYLE_KEYWORD_PROFILES`` 提到 ``WriterStyleProfile`` 表,
但接口签名 ``resolve_style(keywords) -> str`` 保持不变。
"""
from __future__ import annotations

from typing import Iterable


# 硬编码文风裁决词典。每个 key 是 work.style_keywords 中可能出现的词;
# value 是注入到 prompt 的具体写作指令,直接告诉 LLM 怎么写。
STYLE_KEYWORD_PROFILES: dict[str, str] = {
    "热血": (
        "节奏紧凑,短句为主,动词驱动,情绪递进而非铺陈。"
        "允许夸张比喻,但每段最多 1 个,避免堆砌。"
    ),
    "悬疑": (
        "信息差驱动,关键线索通过动作/物件暗示而非直说。"
        "每章至少 1 处误导/误导修复,真相推迟到结尾揭示。"
    ),
    "轻松": (
        "对话占比 ≥40%,动作描写少,允许吐槽/反差萌。"
        "避免沉重形容词、悲情渲染。"
    ),
    "虐": (
        "情绪点到为止,留白多于铺陈。身体细节克制,"
        "内心活动以动作外化(攥紧/停顿/移开视线)。"
    ),
    "爽文": (
        "打脸/升级节奏快,每 800 字至少一次小高潮,"
        "章尾必留爽点钩子(承诺兑现或新威胁)。"
    ),
    "细腻": (
        "感官描写(触/嗅/味/听觉)占 20%+,"
        "心理独白用间接自由间接引语而非直白'他想:...'。"
    ),
    "幽默": (
        "反差与错位优先,允许自嘲与人物降智喜剧。"
        "避免谐音梗、网络烂梗、过度解释。"
    ),
    "黑暗": (
        "阴暗面坦然呈现,不做道德说教。"
        "角色代价必须真实,失败有后果,胜利也有代价。"
    ),
    "治愈": (
        "暖色调优先,细节堆叠(食物/天气/小动作)。"
        "伤痛有回应,但不强行和解。"
    ),
    "史诗": (
        "视角跨度大,历史感与厚重感。"
        "避免琐碎日常,聚焦命运转折点与群像戏。"
    ),
}

# 默认基调(空 keywords 时使用)
_DEFAULT_TONE = (
    "基调由作品类型 + 目标读者自定。"
    "避免 AI 模板痕迹:不用'不是 X 而是 Y'、不用'声音不高却'、"
    "不用'这一夜注定/命运的齿轮'式章尾总结、'这一刻他终于明白'式复读。"
    "章尾留悬念或场景而非总结。"
)


def resolve_style(keywords: Iterable[str] | None) -> str:
    """根据风格关键词列表返回拼好的写作指令段。

    输出包含 3 部分:
    - 命中的关键词 → 对应的写作指令(按关键词顺序)
    - 未命中的关键词 → 简短标注"无内置模板"
    - 末尾固定追加 AI 痕迹禁令 + 默认基调
    """
    keywords = [k for k in (keywords or []) if k]
    if not keywords:
        return _DEFAULT_TONE

    hit_lines: list[str] = []
    miss: list[str] = []
    for kw in keywords:
        profile = STYLE_KEYWORD_PROFILES.get(kw)
        if profile:
            hit_lines.append(f"- 【{kw}】{profile}")
        else:
            miss.append(kw)

    parts: list[str] = []
    if hit_lines:
        parts.append("本作文风裁决(命中):\n" + "\n".join(hit_lines))
    if miss:
        miss_str = "、".join(miss)
        parts.append(
            f"其他关键词({miss_str})无内置模板,"
            "请按字面意图写作,不要过度解读。"
        )
    parts.append(_DEFAULT_TONE)
    return "\n\n".join(parts)

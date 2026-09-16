"""Plot 大纲 schema 对 LLM 脏输出的兼容。"""
from app.agents.plot_agent import parse_outline_volumes
from app.prompts.plot_prompts import build_plot_system_prompt
from app.schemas.outline import PlotVolume


def test_plot_volume_accepts_string_beats_and_extra_fields():
    """Prompt 要求 beats 为字符串时，不能整卷丢弃。"""
    vol = PlotVolume.model_validate(
        {
            "vol_no": 1,
            "vol_title": "第一卷 · 枪出如龙",
            "summary": "凡人少年初见仙道",
            "theme": "多余字段应忽略",
            "chapters": [
                {
                    "title": "第1章 沈家枪",
                    "summary": "沈砚十年苦练被仙人看轻。",
                    "target_word_count": 3000,
                    "beats": ["练枪", "遇仙", "不服"],
                    "characters_involved": ["沈砚"],
                    "world_refs": [],
                    "key_events": ["初见修士"],
                    "hook": "多余",
                }
            ],
        }
    )
    assert vol.vol_no == 1
    assert [b.title for b in vol.chapters[0].beats] == ["练枪", "遇仙", "不服"]


def test_plot_volume_accepts_object_beats():
    """对象节拍仍可用。"""
    vol = PlotVolume.model_validate(
        {
            "vol_no": 2,
            "vol_title": "第二卷",
            "chapters": [
                {
                    "title": "第8章",
                    "beats": [{"title": "对决", "summary": "枪破灵光"}],
                }
            ],
        }
    )
    assert vol.chapters[0].beats[0].title == "对决"
    assert vol.chapters[0].beats[0].summary == "枪破灵光"


def test_parse_outline_strips_think_and_salvages_truncated_json():
    """MiniMax 把 JSON 包在 think 后截断时，应回显已经写完的卷。"""
    raw = """<think>
Let me design 5 volumes. First { "draft": true }
Then the real JSON follows.
</think>
{"volumes":[
  {"vol_no":1,"vol_title":"第一卷 · 少年枪鸣","summary":"家破","chapters":[
    {"title":"十年磨枪","summary":"习武","target_word_count":3000,"beats":["练枪","立志","亲授"],"characters_involved":["沈砚"],"world_refs":["武道九境"],"key_events":["枪成"]}
  ]},
  {"vol_no":2,"vol_title":"第二卷 · 血路独行","summary":"寻亲","chapters":[
    {"title":"残垣独醒","summary":"苏醒","target_word_count":3000,"beats":["掩埋","发誓","北上"],"characters_involved":["沈砚"],"world_refs":[],"key_events":["上路"]}
  ]},
  {"vol_no":3,"vol_title":"第三卷 · 凡人之怒","summary":"成名","chapters":[
    {"title":"枪挑灵光","summary":"决战","target_word_count":300
"""
    volumes = parse_outline_volumes(raw)
    assert [v.vol_no for v in volumes] == [1, 2]
    assert volumes[0].vol_title == "第一卷 · 少年枪鸣"
    assert volumes[1].chapters[0].title == "残垣独醒"


def test_plot_system_prompt_forbids_think_tags():
    """系统提示必须禁止 think，避免模型把预算花在英文思考上。"""
    sys_p = build_plot_system_prompt()
    assert "<think>" in sys_p
    assert "只输出 JSON" in sys_p
    assert "本轮只输出" in sys_p
    assert "第一个字符必须是" in sys_p
    assert "约200字" in sys_p
    assert "约60字" in sys_p
    assert "中文数字" in sys_p
    assert "英文双引号" in sys_p


def test_one_volume_prompt_only_keeps_current_volume_hint():
    """全书五卷规划不得整段进入第 2 卷的 user prompt。"""
    from types import SimpleNamespace

    from app.prompts.plot_prompts import build_plot_one_volume_user_prompt, compact_volume_hint

    hint = (
        "主角：沈砚\n"
        "第一卷青山少年1～12章 家族灭门\n"
        "第二卷踏入仙门13～24章 入仙门找妹妹\n"
        "第五卷一枪问仙49～60 打破壁垒\n"
    )
    compact = compact_volume_hint(hint, 2)
    assert "踏入仙门" in compact
    assert "家族灭门" not in compact
    assert "打破壁垒" not in compact

    work = SimpleNamespace(
        title="我有一枪，可问长生",
        genre="fantasy",
        logline="这个世界，凡人习武，修士炼气。" + "长简介" * 40,
        style_keywords=["热血狂飙"],
    )
    user = build_plot_one_volume_user_prompt(
        work=work,
        vol_no=2,
        total_volumes=5,
        chapter_count=12,
        chapter_start=13,
        extra_hint=hint,
    )
    assert "vol_no\":2" in user.replace(" ", "")
    assert "第二卷 · 短标题" in user
    assert "第2卷 · 短标题" not in user
    assert "第一个字符必须是" in user
    assert "约200字" in user
    assert "约60字" in user
    assert "打破壁垒" not in user
    assert "长简介" * 25 not in user


def test_split_chapter_counts_even_for_five_volumes():
    """60 章 5 卷应均分成每卷 12 章。"""
    from app.prompts.plot_prompts import split_chapter_counts

    assert split_chapter_counts(60, 5) == [12, 12, 12, 12, 12]
    assert split_chapter_counts(10, 3) == [4, 3, 3]


def test_parse_outline_salvages_truncated_single_volume_chapters():
    """单卷 12 章写到一半被截断时，应保住已经闭合的章，而不是整卷丢弃。"""
    raw = (
        '{"volumes":[{"vol_no":1,"vol_title":"第一卷 · 青山少年","summary":"家破",'
        '"chapters":['
        '{"title":"第1章 开篇","summary":"练枪","target_word_count":3000},'
        '{"title":"第2章 灭门","summary":"逃出","target_word_count":3000},'
        '{"title":"第3章 北上","summary":"寻仇","target_word_count":30'
    )
    volumes = parse_outline_volumes(raw)
    assert len(volumes) == 1
    assert volumes[0].vol_title == "第一卷 · 青山少年"
    assert [c.title for c in volumes[0].chapters] == ["第1章 开篇", "第2章 灭门"]


def test_parse_outline_drops_invalid_chapter_keeps_volume():
    """某一章缺标题时丢掉该章，整卷仍可用。"""
    raw = (
        '{"volumes":[{"vol_no":1,"vol_title":"第一卷","chapters":['
        '{"title":"第1章","summary":"开篇"},'
        '{"summary":"没有标题应被丢掉"},'
        '{"title":"第3章","summary":"收束"}'
        "]}]}"
    )
    volumes = parse_outline_volumes(raw)
    assert len(volumes) == 1
    assert [c.title for c in volumes[0].chapters] == ["第1章", "第3章"]


def test_parse_outline_accepts_bare_volume_object():
    """单卷调用时模型可能直接吐 volume 对象而不是 volumes 数组。"""
    raw = '{"vol_no":1,"vol_title":"第一卷","chapters":[{"title":"第1章","summary":"开篇"}]}'
    volumes = parse_outline_volumes(raw)
    assert len(volumes) == 1
    assert volumes[0].vol_title == "第一卷"


def test_salvage_volume_summary_keeps_text_after_inner_quotes():
    """简介里的英文引号不得把 summary 截在「却因」或「揭露仙门借」。"""
    inner = '"凡人僭越"'
    raw = (
        '{"volumes":[{"vol_no":3,"vol_title":"第三卷 · 龙渊秘境",'
        '"summary":"本卷写沈砚踏入龙渊秘境。祖上曾以武道斩杀数位化神大能，却因'
        + inner
        + '之罪遭十大仙门联手剿杀。",'
        '"chapters":[{"title":"第25章 龙渊初开","summary":"入秘境","target_word_count":3000},'
        '{"title":"第26章 血狼夜袭","summary":"战狼","target_word_count":3000}]}]}'
    )
    volumes = parse_outline_volumes(raw)
    assert len(volumes) == 1
    assert "凡人僭越" in volumes[0].summary
    assert "十大仙门联手剿杀" in volumes[0].summary
    assert [c.title for c in volumes[0].chapters] == ["第25章 龙渊初开", "第26章 血狼夜袭"]


def test_parse_one_volume_rewrites_arabic_vol_title():
    """第4卷应规范成第四卷。"""
    from app.agents.plot_outline_parse import parse_one_volume

    inner = '"除妖"'
    raw = (
        '{"volumes":[{"vol_no":4,"vol_title":"第4卷 · 人间烽火",'
        '"summary":"本卷写沈砚从仙门弟子蜕变为凡人守护者的转折。修仙界与凡人疆域冲突激化，'
        "多座凡人城池遭仙门征伐。他深入边陲重镇，揭露仙门借"
        + inner
        + '之名行掠夺之实。",'
        '"chapters":[{"title":"第37章 烽烟北起","summary":"下山","target_word_count":3000}]}]}'
    )
    vol = parse_one_volume(raw, 4)
    assert vol is not None
    assert vol.vol_title == "第四卷 · 人间烽火"
    assert "除妖" in vol.summary
    assert "掠夺" in vol.summary


def test_one_volume_prompt_uses_chinese_numeral_for_volume_four():
    """第四卷样例不得写成第4卷。"""
    from types import SimpleNamespace

    from app.prompts.plot_prompts import build_plot_one_volume_user_prompt, chinese_volume_label

    work = SimpleNamespace(
        title="枪",
        genre="fantasy",
        logline="凡人问仙",
        style_keywords=["热血"],
    )
    user = build_plot_one_volume_user_prompt(
        work=work,
        vol_no=4,
        total_volumes=5,
        chapter_count=12,
        chapter_start=37,
    )
    assert chinese_volume_label(4) == "第四卷"
    assert "第四卷 · 短标题" in user
    assert "第4卷 · 短标题" not in user

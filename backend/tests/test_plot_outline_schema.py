"""Plot 大纲 schema 对 LLM 脏输出的兼容。"""
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

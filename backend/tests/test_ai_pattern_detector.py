"""AI 痕迹检测器单测。

覆盖目标:
- 每条规则的命中与不命中
- 阈值与白名单
- severity 分级正确
- 文本过短/为空时返回空
- summarize() 聚合正确
"""
from __future__ import annotations

from app.services.ai_pattern_detector import (
    AIPatternDetector,
    PatternFinding,
    Severity,
    detect_ai_patterns,
    summarize,
)


# ==================== 否定+肯定翻转 ====================


def test_neg_pos_flip_hit():
    text = "他并不是为了报仇,而是为了那笔遗产。"
    findings = AIPatternDetector().detect(text)
    cats = [f.category for f in findings]
    assert "neg-pos-flip" in cats
    flip = next(f for f in findings if f.category == "neg-pos-flip")
    assert flip.severity == Severity.BLOCKING
    assert text[flip.start:flip.end] in text


def test_neg_pos_flip_miss():
    text = "他走向窗边,看着外面的雨。"
    findings = AIPatternDetector().detect(text)
    cats = [f.category for f in findings]
    assert "neg-pos-flip" not in cats


# ==================== 反序对比 ====================


def test_not_is_reverse_hit():
    text = "这是真正的实力,不是运气。"
    findings = AIPatternDetector().detect(text)
    assert any(f.category == "not-is-reverse" for f in findings)


def test_not_is_reverse_miss():
    # 真正不命中的样本:无 "是 X,不是 Y" 结构
    text = "他看了一眼窗外的雨,转身离开。"
    findings = AIPatternDetector().detect(text)
    assert not any(f.category == "not-is-reverse" for f in findings)


# ==================== 否定排比 ====================


def test_negation_parade_hit():
    text = "没有鲜花,没有掌声,没有喝彩,只有无边的寂静。"
    findings = AIPatternDetector().detect(text)
    assert any(f.category == "negation-parade" for f in findings)


# ==================== 音量反差 ====================


def test_voice_contrast_hit():
    text = "她的声音不高,却字字扎进他心里。"
    findings = AIPatternDetector().detect(text)
    assert any(f.category == "voice-contrast" for f in findings)


# ==================== em-dash 密度 ====================


def test_em_dash_density_hit():
    text = "他——她——它——你——我——他——她——它——终于停下来了。"
    findings = AIPatternDetector().detect(text)
    assert any(f.category == "em-dash-density" for f in findings)


def test_em_dash_density_snippet_exists_in_text():
    """密度 finding 的 snippet 必须是正文里能定位到的真实片段,不能是「共 N 处」摘要。"""
    text = "他——她——它——你——我——他——她——它——终于停下来了。"
    findings = AIPatternDetector().detect(text)
    finding = next(f for f in findings if f.category == "em-dash-density")
    assert finding.snippet in text
    assert not finding.snippet.startswith("共 ")
    assert len(finding.hits) >= 6


def test_em_dash_density_miss_under_threshold():
    text = "他说——还有吗?她说没了。"
    findings = AIPatternDetector().detect(text)
    assert not any(f.category == "em-dash-density" for f in findings)


# ==================== 章尾预告式总结 ====================


def test_trailer_ending_hit():
    # 章尾 ~250 字窗口内出现 "才刚开始"
    filler = "无意义的铺垫" * 30
    text = filler + "没人知道这一切才刚刚开始。"
    findings = AIPatternDetector().detect(text)
    assert any(f.category == "trailer-ending" for f in findings)


def test_trailer_summary_hit():
    filler = "夜雨" * 60
    text = filler + "这一夜注定无眠。"
    findings = AIPatternDetector().detect(text)
    assert any(f.category == "trailer-summary" for f in findings)


def test_trailer_summary_miss_in_middle():
    # 不在章尾窗口 → 不应报(用足够长的填充把 trailer 推到中段)
    filler = "正常的章节内容" * 100  # 600 字
    text = "这一夜注定无眠。" + filler + "他合上书。"
    assert len(text) > 600, "filler 不够长,trailer 仍在章尾窗口内"
    findings = AIPatternDetector().detect(text)
    assert not any(f.category == "trailer-summary" for f in findings)


# ==================== 微动作复读 ====================


def test_micro_action_tic_hit():
    # 至少 5 次 "了+下/阵/圈..."
    text = (
        "他看了一眼桌子,点了一下头,挪了一下身子,"
        "皱了一下眉头,抿了一下嘴,转了一下身。"
    )
    findings = AIPatternDetector().detect(text)
    assert any(f.category == "micro-action-tic" for f in findings)


def test_micro_action_tic_snippet_exists_in_text():
    """微动作密度 snippet 必须能在正文中定位,并带上全部命中位置。"""
    text = (
        "他看了一眼桌子,点了一下头,挪了一下身子,"
        "皱了一下眉头,抿了一下嘴,转了一下身。"
    )
    findings = AIPatternDetector().detect(text)
    finding = next(f for f in findings if f.category == "micro-action-tic")
    assert finding.snippet in text
    assert not finding.snippet.startswith("共 ")
    assert len(finding.hits) >= 5


def test_micro_action_tic_miss_under_threshold():
    text = "他看了一下,然后离开了。"
    findings = AIPatternDetector().detect(text)
    assert not any(f.category == "micro-action-tic" for f in findings)


def test_micro_action_tic_skipped_in_quote():
    """引号内(对话)不算微动作复读。"""
    # 真正用全角/半角引号包裹,确保 segmenter 切到对话段
    quote = (
        "“他点了一下头,她皱了一下眉头,我挪了一下,"
        "转了一下,看了一下,听了一下。”她说完了。"
    )
    findings = AIPatternDetector().detect(quote)
    assert not any(f.category == "micro-action-tic" for f in findings)


# ==================== 套式反应细节 ====================


def test_stock_reaction_tic_hit():
    text = (
        "他指尖轻轻一颤,她嘴角微微抿紧,"
        "他拳头攥紧了一下,她眼底悄然移开,他肩膀轻轻一抖。"
    )
    findings = AIPatternDetector().detect(text)
    assert any(f.category == "stock-reaction-tic" for f in findings)


# ==================== 抽象总结复读 ====================


def test_abstract_summary_tic_hit():
    text = (
        "这一刻他终于明白。命运的齿轮开始转动。"
        "如同棋局,所有人都身在其中。"
    )
    findings = AIPatternDetector().detect(text)
    assert any(f.category == "abstract-summary-tic" for f in findings)


# ==================== 边界情况 ====================


def test_empty_text():
    assert AIPatternDetector().detect("") == []
    assert AIPatternDetector().detect("   \n\t  ") == []


def test_clean_text_no_findings():
    text = (
        "沈青河推开包厢门,里面闹成一团。她扫了一眼,"
        "径直走向角落的卡座。灯光昏黄,几个穿西装的男子正在划拳。"
    )
    findings = AIPatternDetector().detect(text)
    # 这些干净文本不应触发任何阻断类
    blocking = [f for f in findings if f.severity == Severity.BLOCKING]
    assert blocking == [], f"clean text triggered blocking: {blocking}"


def test_findings_sorted_by_start():
    text = (
        "他的声音不高,却字字清晰。" + ("中间填充。" * 20) + "不是运气,而是实力。"
    )
    findings = AIPatternDetector().detect(text)
    starts = [f.start for f in findings]
    assert starts == sorted(starts)


# ==================== 便捷函数 & 统计 ====================


def test_detect_ai_patterns_returns_dicts():
    text = "他并不是为了报仇,而是为了那笔遗产。"
    result = detect_ai_patterns(text)
    assert isinstance(result, list)
    assert all(isinstance(f, dict) for f in result)
    if result:
        f = result[0]
        assert "category" in f
        assert "severity" in f
        assert "start" in f
        assert "end" in f
        assert "snippet" in f
        assert "message" in f


def test_summarize_aggregation():
    text = (
        "他的声音不高,却字字清晰。"
        + ("中间。" * 20)
        + "不是运气,而是实力。没有掌声,没有喝彩。"
    )
    findings = AIPatternDetector().detect(text)
    summary = summarize(findings)
    assert summary["total"] == len(findings)
    assert sum(summary["by_severity"].values()) == len(findings)
    assert sum(summary["by_category"].values()) == len(findings)


# ==================== Editor Agent 集成 ====================


def test_editor_agent_analyze():
    from app.agents.editor_agent import EditorAgent

    agent = EditorAgent()
    result = agent.analyze("不是运气,而是实力。")
    assert "findings" in result
    assert "blocking_count" in result
    assert "advisory_count" in result
    assert any(f["category"] == "neg-pos-flip" for f in result["findings"])


def test_editor_agent_analyze_empty():
    from app.agents.editor_agent import EditorAgent

    agent = EditorAgent()
    assert agent.analyze("") == {
        "findings": [],
        "stats": summarize([]),
        "blocking_count": 0,
        "advisory_count": 0,
    }


def test_editor_agent_execute_backward_compat():
    """旧版 orchestrator 调用方式:execute(context) 必须能跑。"""
    import asyncio

    from app.agents.editor_agent import EditorAgent

    agent = EditorAgent()
    result = asyncio.run(agent.execute({"text": "不是运气,而是实力。"}))
    assert result["agent"] == "editor"
    assert "findings" in result
    assert "stats" in result


def test_editor_agent_polish_no_findings():
    """无 finding 时 polish 跳过 LLM,直接返回原文。"""
    import asyncio

    from app.agents.editor_agent import EditorAgent

    agent = EditorAgent()
    text = "沈青河推开包厢门,里面闹成一团。"  # 干净文本
    result = asyncio.run(agent.polish(text, cfg=None))
    assert result.polished_text == text
    assert result.findings == []
    assert result.rewrites == []
    assert "未检测到" in result.summary


def test_editor_agent_skips_placeholder_rewrite():
    """模型把 JSON 样例抄进 rewritten 时不得写入正文。"""
    from app.agents.editor_agent import EditorAgent, PolishRewrite
    from app.services.ai_pattern_detector import PatternFinding, Severity

    text = "不是怕，是压力让他绷紧。"
    finding = PatternFinding(
        category="neg-pos-flip",
        severity=Severity.BLOCKING,
        start=0,
        end=len(text),
        snippet=text,
        message="否定铺垫",
        rule="test",
    )
    leaked = PolishRewrite(
        category="neg-pos-flip",
        original=text,
        rewritten="<改写后片段;若判定无需改写,填原文>",
        reason="x",
    )
    out = EditorAgent._apply_rewrites(text, [finding], [leaked])
    assert "改写后片段" not in out
    assert "压力" in out


def test_expand_density_findings_splits_by_sentence():
    """密度类必须按「含痕迹的整句」展开,否则 LLM 只改第一处,其余破折号仍超阈值。"""
    from app.agents.editor_agent import EditorAgent

    text = "甲——一。乙——二。丙——三。丁——四。戊——五。己——六。"
    findings = AIPatternDetector().detect(text)
    expanded = EditorAgent.expand_findings_for_rewrite(text, findings)
    dash_findings = [f for f in expanded if f.category == "em-dash-density"]
    assert len(dash_findings) == 6
    for f in dash_findings:
        assert f.snippet in text
        assert "——" in f.snippet


def test_apply_rewrites_clears_em_dash_density():
    """逐句替换后,破折号密度必须降到阈值以下。"""
    from app.agents.editor_agent import EditorAgent, PolishRewrite

    text = "甲——一。乙——二。丙——三。丁——四。戊——五。己——六。"
    findings = AIPatternDetector().detect(text)
    expanded = EditorAgent.expand_findings_for_rewrite(text, findings)
    rewrites = [
        PolishRewrite(
            category=f.category,
            original=f.snippet,
            rewritten=f.snippet.replace("——", "，"),
            reason="按功能改写破折号",
        )
        for f in expanded
    ]
    out = EditorAgent._apply_rewrites(text, expanded, rewrites)
    remaining = AIPatternDetector().detect(out)
    assert not any(f.category == "em-dash-density" for f in remaining)
    assert "——" not in out


def test_apply_rewrites_clears_micro_action_tic():
    """微动作复读必须改掉全部命中句,不能只替换第一处。"""
    from app.agents.editor_agent import EditorAgent, PolishRewrite

    text = (
        "他看了一眼桌子。点了一下头。挪了一下身子。"
        "皱了一下眉头。抿了一下嘴。转了一下身。"
    )
    findings = AIPatternDetector().detect(text)
    expanded = EditorAgent.expand_findings_for_rewrite(text, findings)
    rewrites = [
        PolishRewrite(
            category=f.category,
            original=f.snippet,
            rewritten=f.snippet.replace("了一眼", "向").replace("了一下", "了"),
            reason="去掉微动作复读",
        )
        for f in expanded
    ]
    out = EditorAgent._apply_rewrites(text, expanded, rewrites)
    remaining = AIPatternDetector().detect(out)
    assert not any(f.category == "micro-action-tic" for f in remaining)

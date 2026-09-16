import { describe, expect, it } from 'vitest';

import { normalizeNovelParagraphs, plainToTipTapDoc, stripPromptLeaks } from '../plainToTipTap';

describe('plainToTipTap', () => {
  it('剥掉润色 JSON 占位泄漏', () => {
    const raw = '碗口粗的窟窿边缘焦黑<改写后片段;若判定无需改写,填原文>那是枪身高速震荡留下的痕迹。';
    const out = stripPromptLeaks(raw);
    expect(out).not.toContain('改写后片段');
    expect(out).toContain('焦黑');
  });

  it('墙式正文切成多段 TipTap', () => {
    const wall = '第一句结束。第二句也结束。第三句还在继续写动作。'.repeat(3);
    const doc = plainToTipTapDoc(wall);
    expect((doc.content ?? []).length).toBeGreaterThan(1);
    expect(doc.content?.every((n) => n.type === 'paragraph')).toBe(true);
  });

  it('对话与场景切换另起一段', () => {
    const wall = '沈砚收枪而立。「砚哥儿，今晚沈家摆宴。」他点了点头。—— 沈家后院。月光很薄。';
    const out = normalizeNovelParagraphs(wall);
    const paras = out.split('\n\n').filter(Boolean);
    expect(paras.length).toBeGreaterThanOrEqual(3);
  });
});

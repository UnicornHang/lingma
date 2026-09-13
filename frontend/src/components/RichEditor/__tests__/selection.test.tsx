/**
 * 提交 D — RichEditor 句柄(选区/段落级)单测
 *
 * 覆盖:
 * - getSelection: 折叠选区(光标)→ null
 * - replaceRange: 替换后文本变化
 * - getCurrentParagraph: 光标所在自然段
 * - onSelectionChange: 替换后回调附带 from/to/text
 *
 * TipTap 位置规则提醒:doc 起点 0,进入 paragraph 后第一个字符位置为 1
 *  - '<p>你</p>' doc: 0=before, 1=你, 2=end p, 3=end doc
 *  - '<p>你好</p>' doc: 0=before, 1=你, 2=好, 3=end p, 4=end doc
 */
import { describe, it, expect, vi } from 'vitest';
import { render, act } from '@testing-library/react';
import { createRef } from 'react';
import { RichEditor, type RichEditorHandle } from '../index';

describe('RichEditor selection / paragraph handle', () => {
  it('getSelection 返回 null 当选区折叠(仅光标)', () => {
    const ref = createRef<RichEditorHandle>();
    render(
      <RichEditor
        ref={ref}
        content={{ type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'hello world' }] }] }}
        editable
      />
    );
    // 默认无选区 → null
    expect(ref.current).not.toBeNull();
    expect(ref.current?.getSelection()).toBeNull();
  });

  it('replaceRange 替换文本后 getText 反映新内容', () => {
    const ref = createRef<RichEditorHandle>();
    render(
      <RichEditor
        ref={ref}
        content={{ type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: '你好世界' }] }] }}
        editable
      />
    );
    expect(ref.current).not.toBeNull();
    // 段起点=1,字符位置:1=你, 2=好, 3=世, 4=界, 5=end p
    // 替换 '好' (位置 2,3) 为 '棒'
    const ok = ref.current?.replaceRange(2, 3, '棒');
    expect(ok).toBe(true);
    expect(ref.current?.getText()).toBe('你棒世界');
  });

  it('getCurrentParagraph 找到光标所在自然段(默认在段 1)', () => {
    const ref = createRef<RichEditorHandle>();
    render(
      <RichEditor
        ref={ref}
        content={{
          type: 'doc',
          content: [
            { type: 'paragraph', content: [{ type: 'text', text: '第一段' }] },
            { type: 'paragraph', content: [{ type: 'text', text: '第二段文字' }] },
            { type: 'paragraph', content: [{ type: 'text', text: '第三' }] },
          ],
        }}
        editable
      />
    );
    expect(ref.current).not.toBeNull();
    // 默认 selection 在 position 1(doc start)→ 段 1
    const para = ref.current?.getCurrentParagraph();
    expect(para).not.toBeNull();
    expect(para?.text).toBe('第一段');
  });

  it('getCurrentParagraph 跨段时返回正确段落', () => {
    const ref = createRef<RichEditorHandle>();
    render(
      <RichEditor
        ref={ref}
        content={{
          type: 'doc',
          content: [
            { type: 'paragraph', content: [{ type: 'text', text: '第一段' }] },
            { type: 'paragraph', content: [{ type: 'text', text: '第二段文字' }] },
            { type: 'paragraph', content: [{ type: 'text', text: '第三' }] },
          ],
        }}
        editable
      />
    );
    expect(ref.current).not.toBeNull();
    // 段 2 起点=6(段 1 占 5 个位置 0..5: 0=before, 1-4=第一段, 5=end p1)
    // 段 2 内部:'第二段文字' (5 chars) 位置 6-10, 11=end p2
    // 通过 insertContentAt(6,6,'X') 把光标设到 6 附近 → 段 2
    act(() => {
      // 插入 'X' 到段 2 起点之前,触发 selection update,光标到 7
      ref.current?.replaceRange(6, 6, 'X');
    });
    // 段 2 已被扩展为 'X第二段文字'
    const para = ref.current?.getCurrentParagraph();
    expect(para).not.toBeNull();
    expect(para?.text).toBe('X第二段文字');
    expect(para?.from).toBe(6);
  });

  it('onSelectionChange 回调在 replaceRange 后附带 from/to', () => {
    const onSelectionChange = vi.fn();
    const ref = createRef<RichEditorHandle>();
    render(
      <RichEditor
        ref={ref}
        content={{ type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'foo bar' }] }] }}
        editable
        onSelectionChange={onSelectionChange}
      />
    );
    expect(ref.current).not.toBeNull();
    onSelectionChange.mockClear(); // 清掉初始 mount 时的回调
    act(() => {
      // 段起点=1, 字符位置 1-7 = foo bar, 8=end p
      // 替换 ' bar' (位置 4-8) 为 'BAR'
      ref.current?.replaceRange(4, 8, 'BAR');
    });
    // 应被调用至少一次
    expect(onSelectionChange).toHaveBeenCalled();
    // 最近一次 from 应该是 7(=4 + 'BAR'长度)
    const lastCall = onSelectionChange.mock.calls[onSelectionChange.mock.calls.length - 1][0];
    expect(lastCall.from).toBe(7);
    expect(lastCall.to).toBe(7);
    expect(lastCall.text).toBe(''); // 折叠选区 → text 空
  });

  it('onSelectionChange 附带 text 当选区展开', () => {
    const onSelectionChange = vi.fn();
    const ref = createRef<RichEditorHandle>();
    render(
      <RichEditor
        ref={ref}
        content={{ type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'hello world' }] }] }}
        editable
        onSelectionChange={onSelectionChange}
      />
    );
    expect(ref.current).not.toBeNull();
    onSelectionChange.mockClear();
    // 触发编辑,让 TipTap 产生 onSelectionUpdate
    act(() => {
      ref.current?.replaceRange(1, 1, 'X'); // 插入 'X' 到段首
    });
    expect(onSelectionChange).toHaveBeenCalled();
    const lastCall = onSelectionChange.mock.calls[onSelectionChange.mock.calls.length - 1][0];
    // 折叠选区在 position 2(text 之后),text 应为空
    expect(typeof lastCall.text).toBe('string');
    expect(typeof lastCall.from).toBe('number');
    expect(typeof lastCall.to).toBe('number');
  });
});

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { App, Button } from 'antd';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Bot,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Wand2,
  Save,
  Loader2,
  X,
} from 'lucide-react';

import { chaptersApi, type Chapter, type TipTapDoc } from '@/api/chapters';
import { useGenerationStream } from '@/hooks/useGenerationStream';
import { RichEditor } from '@/components/RichEditor';

// 示例大纲树 —— 后端接入后可换成真实 outline tree API
const OUTLINE = [
  {
    volume: '第一卷·少年游',
    chapters: 42,
    expanded: true,
    items: [
      { id: 'c1',  title: '第 1 章 洞天风云',  wordCount: '2.4k', active: false },
      { id: 'c11', title: '第 11 章 意外来客', wordCount: '3.2k', active: true },
      { id: 'c12', title: '第 12 章 山雨欲来', wordCount: '2.8k', active: false },
    ],
  },
  { volume: '第二卷·江湖路', chapters: 38, expanded: false, items: [] },
  { volume: '第三卷·风波起', chapters: 36, expanded: false, items: [] },
];

const TABS = ['分析', '批注', '角色', '一致性', '伏笔'];

/** TipTap 文档转纯文本（用于字数统计；本地简易实现） */
function plainFromDoc(doc: TipTapDoc | null | undefined): string {
  if (!doc?.content) return '';
  const walk = (node: { type: string; text?: string; content?: unknown[] }): string => {
    if (node.type === 'text' && typeof node.text === 'string') return node.text;
    const inner = Array.isArray(node.content) ? (node.content as Array<{ type: string; text?: string; content?: unknown[] }>) : [];
    if (node.type === 'paragraph' || node.type === 'heading') {
      return inner.map(walk).join('') + '\n';
    }
    return inner.map(walk).join('');
  };
  return doc.content.map(walk).join('').trim();
}

/** 把纯文本包装成 TipTap 段落 doc */
function plainToDoc(plain: string): TipTapDoc {
  return {
    type: 'doc',
    content: plain.split(/\n+/).map((line) => ({
      type: 'paragraph',
      content: line ? [{ type: 'text', text: line }] : [],
    })),
  };
}

/** 拼接两个 TipTap doc —— 用于将生成内容追加到现有文档末尾 */
function appendPlain(prev: TipTapDoc | null, more: string): TipTapDoc {
  const baseContent = prev?.content ?? [];
  const extra = plainToDoc(more).content ?? [];
  return { type: 'doc', content: [...baseContent, ...extra] };
}

export default function ChapterEditorPage() {
  const { chapterId } = useParams<{ chapterId?: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();

  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [content, setContent] = useState<TipTapDoc | null>(null);
  const [plainText, setPlainText] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  const saveTimerRef = useRef<number | null>(null);

  // 1) 加载章节
  useEffect(() => {
    if (!chapterId) return;
    let cancelled = false;
    setLoading(true);
    chaptersApi
      .get(chapterId)
      .then((c) => {
        if (cancelled) return;
        setChapter(c);
        const initial = (c.content ?? { type: 'doc', content: [] }) as TipTapDoc;
        setContent(initial);
        setPlainText(c.plain_content || plainFromDoc(initial));
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : '加载章节失败';
        message.error(msg);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [chapterId, message]);

  // 2) 编辑器变更 → 标记 dirty、调度自动保存
  const handleEditorChange = useCallback((json: TipTapDoc, plain: string) => {
    setContent(json);
    setPlainText(plain);
    setDirty(true);
  }, []);

  const persist = useCallback(async () => {
    if (!chapter || !dirty) return;
    setSaving(true);
    try {
      const updated = await chaptersApi.update(chapter.id, {
        content: content ?? undefined,
        plain_content: plainText,
      });
      setChapter(updated);
      setDirty(false);
      setLastSavedAt(new Date());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '保存失败';
      message.error(msg);
    } finally {
      setSaving(false);
    }
  }, [chapter, dirty, content, plainText, message]);

  // 防抖自动保存：800ms 后无操作则保存
  useEffect(() => {
    if (!dirty || !chapter) return;
    if (saveTimerRef.current !== null) {
      window.clearTimeout(saveTimerRef.current);
    }
    saveTimerRef.current = window.setTimeout(() => {
      persist();
    }, 800);
    return () => {
      if (saveTimerRef.current !== null) {
        window.clearTimeout(saveTimerRef.current);
        saveTimerRef.current = null;
      }
    };
  }, [dirty, chapter, persist]);

  // 3) WS 流式生成
  const generation = useGenerationStream(taskId);

  const handleAiContinue = useCallback(async () => {
    if (!chapterId) {
      message.warning('缺少章节 ID，无法续写');
      return;
    }
    if (generation.status === 'streaming' || generation.status === 'connecting') {
      message.info('已有生成任务在进行中');
      return;
    }
    try {
      const resp = await chaptersApi.generate(chapterId, {
        chapter_id: chapterId,
        target_word_count: 800,
      });
      setTaskId(resp.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '创建生成任务失败';
      message.error(msg);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterId, generation.status]);

  // WS 收到 'start' 后才开始送 messages（按协议需在 connected 后才能 send start）
  useEffect(() => {
    if (generation.status !== 'ready') return;
    if (!taskId) return;
    generation.start(
      [
        { role: 'system', content: '你是 LingMa Writer Agent，负责续写中文网文章节，保持原作风与人物声音。' },
        { role: 'user',   content: `请基于以下已有正文续写 800 字左右，开头接续不要重复：\n\n${plainText}` },
      ],
      { model: 'gpt-4o-mini', max_tokens: 1500, temperature: 0.8 }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generation.status, taskId]);

  // 收到 'done' 后把生成内容合并进编辑器并自动保存
  useEffect(() => {
    if (generation.status !== 'done') return;
    const merged = appendPlain(content, generation.content);
    setContent(merged);
    setPlainText(plainFromDoc(merged));
    setDirty(true);
    setTaskId(null);
    message.success(`Writer Agent 已续写 ${generation.content.length} 字`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generation.status, generation.content]);

  // 错误状态
  useEffect(() => {
    if (generation.status === 'error' && generation.error) {
      message.error(`生成失败：${generation.error}`);
      setTaskId(null);
    } else if (generation.status === 'cancelled') {
      message.info('已取消生成');
      setTaskId(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generation.status, generation.error]);

  const handleCancel = useCallback(() => {
    generation.cancel();
    setTaskId(null);
  }, [generation]);

  // 字数显示
  const wordCount = useMemo(() => plainText.length, [plainText]);
  const isStreaming = generation.status === 'streaming' || generation.status === 'connecting' || generation.status === 'ready';

  // ---------- 无 chapterId：占位提示 ----------
  if (!chapterId) {
    return (
      <div className="flex w-full h-full items-center justify-center bg-surface-container-low">
        <div className="text-center flex flex-col items-center gap-3 p-8">
          <FileText size={56} className="text-outline" />
          <h2 className="text-headline-sm font-semibold text-on-surface">请从大纲中选择一个章节</h2>
          <p className="text-body-md text-on-surface-variant">
            在左侧大纲树中点击任意章节即可进入编辑器。
          </p>
          <Button
            type="primary"
            onClick={() => navigate('/works')}
            style={{ marginTop: 8 }}
          >
            返回作品列表
          </Button>
        </div>
      </div>
    );
  }

  // ---------- 主体 ----------
  return (
    <div className="flex w-full h-full bg-surface-container-low">
      {/* Outline tree (left, 300px) */}
      <aside className="w-[300px] flex-shrink-0 h-full bg-surface-container-lowest border-r border-outline-variant/30 overflow-y-auto flex flex-col">
        <div className="p-6 border-b border-outline-variant/30">
          <h3 className="text-headline-sm font-semibold text-on-surface flex items-center justify-between">
            <span>{chapter ? chapter.title : '加载中…'}</span>
            <Button type="text" shape="circle" icon={<Plus size={18} />} aria-label="新建章节" />
          </h3>
          <p className="text-body-sm text-on-surface-variant mt-1">
            {chapter ? `第 ${chapter.id.slice(0, 4)} 章 · v${chapter.version}` : '章节元数据'}
          </p>
        </div>
        <div className="p-4 flex flex-col gap-1">
          {OUTLINE.map((vol) => (
            <div key={vol.volume} className="flex flex-col gap-0.5">
              <Button
                type="text"
                block
                className="!justify-start !text-left"
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 8px' }}
              >
                {vol.expanded ? (
                  <ChevronDown size={16} className="text-outline" />
                ) : (
                  <ChevronRight size={16} className="text-outline" />
                )}
                <span className="text-label-md font-semibold text-on-surface flex-1 ml-1 text-left">
                  {vol.volume}
                </span>
                <span className="font-code-sm text-outline">{vol.chapters} 章</span>
              </Button>
              {vol.expanded && (
                <div className="ml-4 flex flex-col gap-0.5">
                  {vol.items.map((c) => (
                    <a
                      key={c.id}
                      href={`/chapters/${c.id}`}
                      onClick={(e) => { e.preventDefault(); navigate(`/chapters/${c.id}`); }}
                      className={`flex items-center gap-2 px-2 py-1.5 rounded text-body-sm ${
                        c.active
                          ? 'bg-primary-container text-on-primary-container font-semibold'
                          : 'text-on-surface-variant hover:bg-surface-container'
                      }`}
                    >
                      <FileText size={14} />
                      <span className="flex-1">{c.title}</span>
                      <span className="font-code-sm">{c.wordCount}</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* Editor (center) */}
      <section className="flex-1 h-full overflow-y-auto bg-surface-container-low">
        <div className="max-w-[880px] mx-auto px-8 py-8">
          {/* Breadcrumb + title */}
          <div className="flex items-center gap-2 text-on-surface-variant text-label-md mb-2">
            <span>第一卷·少年游</span>
            <span className="text-outline">/</span>
            <span>第 11 章</span>
          </div>
          <h1 className="text-display font-bold text-on-surface">
            {chapter?.title ?? '加载中…'}
          </h1>
          <div className="flex items-center gap-2 mt-2">
            <span className="chip-tertiary">玄幻</span>
            <span className="chip-primary">高潮</span>
            <span className="chip-secondary">POV · 第一人称</span>
            <span className="font-code-sm text-on-surface-variant">
              {wordCount.toLocaleString()} 字
              {chapter ? ` · 目标 ${(chapter.word_count + 800).toLocaleString()}` : ''}
            </span>
          </div>

          {/* Toolbar (TipTap's own toolbar is inside RichEditor; here we keep meta + AI button) */}
          <div className="flex items-center gap-1 p-1 mt-4 bg-surface-container-lowest rounded-lg border border-outline-variant/40 shadow-L1-card">
            <Button
              type="primary"
              ghost
              size="small"
              icon={<Bot size={16} />}
              onClick={handleAiContinue}
              disabled={isStreaming}
              title="AI 续写 800 字"
            >
              续写
            </Button>
            <span className="px-2 py-1 text-body-sm text-on-surface-variant">提示词</span>
            {isStreaming && (
              <Button
                type="text"
                size="small"
                danger
                icon={<X size={16} />}
                onClick={handleCancel}
                title="取消生成"
              >
                取消
              </Button>
            )}
            <span className="ml-auto px-2 py-1 text-body-sm text-on-surface-variant inline-flex items-center gap-1">
              {saving ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> 保存中…
                </>
              ) : dirty ? (
                <>
                  <Save size={14} /> 有未保存的修改
                </>
              ) : lastSavedAt ? (
                <>已自动保存 · {Math.max(1, Math.round((Date.now() - lastSavedAt.getTime()) / 1000))} 秒前</>
              ) : (
                '未修改'
              )}
            </span>
          </div>

          {/* Body — TipTap RichEditor */}
          <div className="mt-4">
            {loading ? (
              <div className="h-[400px] flex items-center justify-center bg-surface-container-lowest rounded-lg border border-outline-variant/30">
                <Loader2 size={28} className="animate-spin text-outline" />
              </div>
            ) : (
              <RichEditor
                content={content}
                editable={!isStreaming}
                onChange={handleEditorChange}
              />
            )}
          </div>

          {/* AI streaming preview card */}
          {(generation.status === 'streaming' || generation.status === 'ready' || generation.status === 'connecting') && (
            <div className="mt-4 p-4 rounded-lg bg-primary-fixed/40 border-l-4 border-primary flex items-start gap-3">
              <Sparkles size={18} className="text-primary animate-pulse" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-label-md text-on-surface font-semibold">Writer Agent 正在续写</span>
                  <span className="font-code-sm text-on-surface-variant">
                    {generation.status === 'streaming'
                      ? `已生成 ${generation.content.length} 字`
                      : generation.status === 'ready'
                        ? '准备开始…'
                        : '连接中…'}
                  </span>
                </div>
                <p className="text-body-sm text-on-surface mt-1 whitespace-pre-wrap min-h-[1.5em]">
                  {generation.content || ' '}
                </p>
              </div>
            </div>
          )}

          {generation.status === 'done' && (
            <div className="mt-4 p-4 rounded-lg bg-tertiary-container/40 border-l-4 border-tertiary flex items-start gap-3">
              <Wand2 size={18} className="text-tertiary" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-label-md text-on-surface font-semibold">续写已完成</span>
                  <span className="font-code-sm text-on-surface-variant">+{generation.content.length} 字</span>
                </div>
                <p className="text-body-sm text-on-surface-variant mt-1">
                  内容已自动合并到正文，800ms 后将自动保存。
                </p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Right Co-pilot panel (460px) */}
      <aside className="w-[460px] flex-shrink-0 h-full bg-surface-container-lowest border-l border-outline-variant/30 overflow-y-auto">
        <div className="px-6 py-3 border-b border-outline-variant/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot size={20} className="text-primary" />
            <span className="text-label-lg font-semibold text-on-surface">协作 Co-pilot</span>
          </div>
          <span className="chip-tertiary">
            {generation.status === 'idle' || generation.status === 'done'
              ? 'READY'
              : generation.status === 'error'
                ? 'ERROR'
                : 'BUSY'}
          </span>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 px-4 py-2 border-b border-outline-variant/30">
          {TABS.map((t, i) => (
            <Button
              key={t}
              type={activeTab === i ? 'primary' : 'text'}
              size="small"
              onClick={() => setActiveTab(i)}
              ghost={activeTab === i}
            >
              {t}
            </Button>
          ))}
        </div>

        {/* Cards */}
        <div className="p-4 flex flex-col gap-4">
          {/* Beat */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-primary">节拍</span>
              <span className="font-code-sm text-outline">第 {chapter?.id.slice(0, 4) ?? '--'} 章 · 段 5</span>
            </div>
            <p className="text-body-md text-on-surface">
              本章核心节拍：<strong>陌生人出现 + 主角审视</strong>
            </p>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 h-1.5 rounded-full bg-surface-container-high">
                <div className="h-full w-3/4 rounded-full bg-primary" />
              </div>
              <span className="font-code-sm text-primary font-semibold">75%</span>
            </div>
          </div>

          {/* Character voice */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-tertiary">角色声音</span>
              <span className="font-code-sm text-outline">3 / 5</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-bold">
                陈
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-label-md text-on-surface">陈平安</span>
                  <span className="font-code-sm text-tertiary">92% 一致</span>
                </div>
                <div className="h-1 mt-1 rounded-full bg-surface-container-high">
                  <div className="h-full w-11/12 rounded-full bg-tertiary" />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-fixed-variant flex items-center justify-center font-bold">
                女
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-label-md text-on-surface">来客 (未命名)</span>
                  <span className="font-code-sm text-outline">尚未建立档案</span>
                </div>
                <Button type="link" size="small" style={{ padding: 0, height: 'auto' }}>+ 创建档案</Button>
              </div>
            </div>
          </div>

          {/* Critic score */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-secondary">质检</span>
              <span className="font-code-sm text-outline">总分 8.4 / 10</span>
            </div>
            <div className="grid grid-cols-4 gap-2 mt-1">
              {[
                { v: '9.1', l: '节奏' },
                { v: '8.6', l: '对话' },
                { v: '8.0', l: '描写' },
                { v: '7.9', l: '钩子' },
              ].map((m) => (
                <div key={m.l} className="flex flex-col items-center p-2 rounded bg-surface-container-lowest">
                  <span className="text-headline-sm font-bold text-primary">{m.v}</span>
                  <span className="font-code-sm text-outline">{m.l}</span>
                </div>
              ))}
            </div>
          </div>

          {/* World bible check */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-tertiary">一致性 ✓</span>
              <span className="font-code-sm text-outline">3 项检查</span>
            </div>
            <ul className="flex flex-col gap-1 mt-1">
              <li className="flex items-center gap-2 text-body-sm">
                <CheckCircle2 size={16} className="text-tertiary" />
                <span className="text-on-surface">"剑来" 招式名 → 功法卷轴存在</span>
              </li>
              <li className="flex items-center gap-2 text-body-sm">
                <CheckCircle2 size={16} className="text-tertiary" />
                <span className="text-on-surface">陈平安右臂旧伤 → 第 8 章已埋伏笔</span>
              </li>
              <li className="flex items-center gap-2 text-body-sm">
                <AlertTriangle size={16} className="text-error" />
                <span className="text-on-surface">来客道袍颜色与第 4 章描述不一致</span>
              </li>
            </ul>
          </div>

          {/* Foreshadowing */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-primary">伏笔</span>
              <span className="font-code-sm text-outline">2 项建议</span>
            </div>
            <div className="p-2 rounded bg-surface-container-lowest">
              <p className="text-body-sm text-on-surface">
                "白驴" → 暂无关联，可在后续卷中关联「骊珠洞天·灵兽」
              </p>
              <Button type="link" size="small" style={{ padding: 0, height: 'auto', marginTop: 4 }}>+ 加入伏笔簿</Button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
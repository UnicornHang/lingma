import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { App, Button, Select, Modal, Spin, Space } from 'antd';
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
  History,
  GitBranch,
} from 'lucide-react';

import {
  chaptersApi,
  type Chapter,
  type ChapterVersion,
  type TipTapDoc,
} from '@/api/chapters';
import { outlineApi, type OutlineTreeNode } from '@/api/outline';
import { useGenerationStream } from '@/hooks/useGenerationStream';
import { RichEditor, type RichEditorHandle } from '@/components/RichEditor';

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

/** 扁平化大纲树为章节节点（含父卷标题） */
function flattenChapters(
  nodes: OutlineTreeNode[],
  volumeTitle?: string,
): Array<OutlineTreeNode & { volumeTitle: string }> {
  const out: Array<OutlineTreeNode & { volumeTitle: string }> = [];
  for (const n of nodes) {
    if (n.type === 'volume') {
      for (const ch of flattenChapters(n.children ?? [], n.title)) out.push(ch);
    } else if (n.type === 'chapter') {
      out.push({ ...n, volumeTitle: volumeTitle ?? '' });
    } else if (n.type === 'beat') {
      // beat 也展示
      out.push({ ...n, volumeTitle: volumeTitle ?? '' });
    }
  }
  return out;
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
  // [P3] 大纲节点状态：从当前章节读,或从大纲树点击切换
  const [outlineNodeId, setOutlineNodeId] = useState<string | null>(null);
  // [P4] 版本历史 UI 状态
  const [versionModalOpen, setVersionModalOpen] = useState(false);
  const [activeVersion, setActiveVersion] = useState<ChapterVersion | null>(null);

  const saveTimerRef = useRef<number | null>(null);
  const editorRef = useRef<RichEditorHandle>(null);

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
        // 同步 outline_node_id(若有)
        setOutlineNodeId(c.outline_node_id ?? null);
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
      // 关键:AI 看到的是 DB 中的 plain_content,若本地有未保存编辑需先落盘,
      // 避免 AI 续写接续在旧版本之后。
      if (dirty) {
        await persist();
      }
      const resp = await chaptersApi.generate(chapterId, {
        chapter_id: chapterId,
        mode: 'continue',
        continue_from_chars: 1500,
        target_word_count: 800,
        outline_node_id: outlineNodeId ?? undefined,
      });
      setTaskId(resp.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '创建生成任务失败';
      message.error(msg);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterId, generation.status, dirty, persist, outlineNodeId]);

  // 注册「待发 start 意图」。useGenerationStream 内部 effect 会在 WS 进入
  // OPEN 时自动发送（StrictMode-safe：即使 WS 被 cleanup，新 WS 进入 OPEN 也会再发一次）
  useEffect(() => {
    if (!taskId) return;
    generation.start(
      [],
      {
        mode: 'continue',
        continue_from_chars: 1500,
        max_tokens: 1500,
        temperature: 0.85,
        onDelta: (chunk) => editorRef.current?.insertContent(chunk),
      }
    );
    // 仅依赖 taskId —— status 变化不应再触发 start(避免重复)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  // 收到 'done' —— 兜底:用后端清洗后的 generation.content 强制覆写编辑器,
  // 防止任何残留的 <think> / thinking aloud 片段留在编辑器中。
  // 然后标记 dirty 让 800ms 自动保存落盘
  useEffect(() => {
    if (generation.status !== 'done') return;
    const cleaned = generation.content;
    if (cleaned && editorRef.current) {
      // 只在编辑器当前内容与 cleaned 不一致时才覆写(避免无谓抖动)
      const currentText = editorRef.current.getText();
      if (currentText.length !== cleaned.length) {
        editorRef.current.setContent(cleaned);
      }
    }
    setDirty(true);
    setTaskId(null);
    // 刷新版本列表
    if (chapterId) versionsQuery.refetch();
    message.success(`Writer Agent 已续写 ${cleaned.length} 字`);
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

  // ==================== [P3] 大纲树数据 ====================
  const outlineQuery = useQuery({
    queryKey: ['outline-tree', chapter?.work_id],
    queryFn: () => outlineApi.tree(chapter!.work_id),
    enabled: !!chapter?.work_id,
  });
  const flatChapters = useMemo(
    () => flattenChapters(outlineQuery.data?.nodes ?? []),
    [outlineQuery.data],
  );
  const [expandedVolumes, setExpandedVolumes] = useState<Set<string>>(new Set());

  // 默认展开首个卷
  useEffect(() => {
    if (outlineQuery.data?.nodes?.length && expandedVolumes.size === 0) {
      const first = outlineQuery.data.nodes[0];
      setExpandedVolumes(new Set([first.id]));
    }
  }, [outlineQuery.data, expandedVolumes.size]);

  const toggleVolume = (id: string) => {
    setExpandedVolumes((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleChapterClick = (chapId: string, outlineId: string) => {
    // 切换到 outline_id 对应的章节(通过 chaptersApi 找或创建)
    // 简化版:直接跳到 /editor/{chapId} 路径,但 chapId 是 outline_node_id 而非 chapter.id
    // 实际生产中需要后端支持 /editor/by-outline/{outline_node_id}
    setOutlineNodeId(outlineId);
    void chapId;
  };

  // ==================== [P4] 版本历史 ====================
  const versionsQuery = useQuery({
    queryKey: ['chapter-versions', chapterId],
    queryFn: () => chaptersApi.listVersions(chapterId!),
    enabled: !!chapterId,
    refetchOnWindowFocus: false,
  });
  const versions = versionsQuery.data?.items ?? [];

  // "当前版本" = 当前 chapter 的 plain_content,版本号 = chapter.version
  // 历史版本从 versionsQuery 拿
  type VersionRow =
    | { kind: 'current'; versionNo: number; length: number; generatedBy: string; note: string; createdAt: string }
    | { kind: 'history'; versionNo: number; length: number; generatedBy: string; note: string; createdAt: string; data: ChapterVersion };
  const versionRows: VersionRow[] = useMemo(() => {
    const rows: VersionRow[] = [];
    if (chapter) {
      rows.push({
        kind: 'current',
        versionNo: chapter.version,
        length: chapter.word_count,
        generatedBy: 'user',
        note: '当前版本',
        createdAt: chapter.updated_at,
      });
    }
    for (const v of versions) {
      rows.push({
        kind: 'history',
        versionNo: v.version_no,
        length: v.plain_content?.length ?? 0,
        generatedBy: v.generated_by,
        note: v.note || `${v.generated_by}`,
        createdAt: v.created_at,
        data: v,
      });
    }
    rows.sort((a, b) => b.versionNo - a.versionNo);
    return rows;
  }, [chapter, versions]);

  const openVersion = (row: VersionRow) => {
    if (row.kind === 'current') {
      message.info('当前版本即编辑区内容,无需预览');
      return;
    }
    setActiveVersion(row.data);
    setVersionModalOpen(true);
  };

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
            <span className="truncate">{chapter ? chapter.title : '加载中…'}</span>
            <Button type="text" shape="circle" icon={<Plus size={18} />} aria-label="新建章节" />
          </h3>
          <p className="text-body-sm text-on-surface-variant mt-1">
            {chapter ? `第 ${chapter.id.slice(0, 4)} 章 · v${chapter.version}` : '章节元数据'}
          </p>
        </div>
        <div className="p-4 flex flex-col gap-1">
          {outlineQuery.isLoading && (
            <div className="flex items-center justify-center py-4">
              <Spin size="small" />
            </div>
          )}
          {outlineQuery.error && (
            <div className="text-body-xs text-error">大纲加载失败</div>
          )}
          {(outlineQuery.data?.nodes ?? []).map((vol) => {
            const expanded = expandedVolumes.has(vol.id);
            const childChapters = (vol.children ?? []).filter((c) => c.type === 'chapter' || c.type === 'beat');
            return (
              <div key={vol.id} className="flex flex-col gap-0.5">
                <Button
                  type="text"
                  block
                  onClick={() => toggleVolume(vol.id)}
                  className="!justify-start !text-left"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 8px' }}
                >
                  {expanded ? <ChevronDown size={16} className="text-outline" /> : <ChevronRight size={16} className="text-outline" />}
                  <span className="text-label-md font-semibold text-on-surface flex-1 ml-1 text-left">
                    {vol.title}
                  </span>
                  <span className="font-code-sm text-outline">{childChapters.length} 章</span>
                </Button>
                {expanded && (
                  <div className="ml-4 flex flex-col gap-0.5">
                    {childChapters.map((c) => {
                      const isActive = outlineNodeId === c.id;
                      return (
                        <a
                          key={c.id}
                          href={`#${c.id}`}
                          onClick={(e) => {
                            e.preventDefault();
                            handleChapterClick(c.id, c.id);
                          }}
                          className={`flex items-center gap-2 px-2 py-1.5 rounded text-body-sm ${
                            isActive
                              ? 'bg-primary-container text-on-primary-container font-semibold'
                              : 'text-on-surface-variant hover:bg-surface-container'
                          }`}
                        >
                          <FileText size={14} />
                          <span className="flex-1 truncate">{c.title}</span>
                          <span className="font-code-sm">{c.target_word_count}</span>
                        </a>
                      );
                    })}
                    {childChapters.length === 0 && (
                      <div className="px-2 py-1 text-body-xs text-outline italic">暂无章节</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {!outlineQuery.isLoading && (outlineQuery.data?.nodes ?? []).length === 0 && (
            <div className="px-2 py-3 text-body-sm text-on-surface-variant italic">
              还没有大纲,新建作品后可使用「AI 推荐大纲」一键生成。
            </div>
          )}
        </div>
      </aside>

      {/* Editor (center) */}
      <section className="flex-1 h-full overflow-y-auto bg-surface-container-low">
        <div className="max-w-[880px] mx-auto px-8 py-8">
          {/* Breadcrumb + title */}
          <div className="flex items-center gap-2 text-on-surface-variant text-label-md mb-2">
            <span>{flatChapters.find((c) => c.id === outlineNodeId)?.volumeTitle || '—'}</span>
            <span className="text-outline">/</span>
            <span>{chapter?.title ?? '加载中…'}</span>
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
          <div className="flex items-center gap-2 p-1 mt-4 bg-surface-container-lowest rounded-lg border border-outline-variant/40 shadow-L1-card flex-wrap">
            <Button
              type="primary"
              ghost
              size="small"
              icon={<Bot size={16} />}
              onClick={handleAiContinue}
              disabled={isStreaming}
              title={outlineNodeId ? `AI 续写 800 字(基于大纲节点 ${outlineNodeId.slice(0, 8)})` : 'AI 续写 800 字'}
            >
              续写
            </Button>
            <span className="px-2 py-1 text-body-sm text-on-surface-variant">提示词</span>

            {/* [P4] 版本下拉 */}
            <span className="px-2 py-1 text-body-sm text-on-surface-variant flex items-center gap-1">
              <History size={14} className="text-outline" />
              版本
            </span>
            <Select
              size="small"
              style={{ minWidth: 200 }}
              value={`v${chapter?.version ?? 1} (当前)`}
              onChange={(value) => {
                const row = versionRows.find((r) => `${r.kind}:${r.versionNo}` === value);
                if (row) openVersion(row);
              }}
              options={versionRows.map((r) => ({
                value: `${r.kind}:${r.versionNo}`,
                label:
                  r.kind === 'current'
                    ? `v${r.versionNo} · 当前版本 · ${r.length} 字`
                    : `v${r.versionNo} · ${r.generatedBy} · ${r.note || `${r.length} 字`}`,
              }))}
              placeholder={versionsQuery.isLoading ? '加载版本中…' : '无历史版本'}
              notFoundContent={versionsQuery.isLoading ? <Spin size="small" /> : '无历史版本'}
            />

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
                ref={editorRef}
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
          {/* [P3] 当前大纲节点信息 */}
          <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="chip-primary">本章大纲</span>
              <span className="font-code-sm text-outline">
                {outlineNodeId ? `node ${outlineNodeId.slice(0, 8)}` : '未关联大纲'}
              </span>
            </div>
            <div className="text-body-sm text-on-surface flex items-start gap-2">
              <GitBranch size={14} className="mt-0.5 text-primary" />
              <div className="flex-1">
                {(() => {
                  const node = flatChapters.find((c) => c.id === outlineNodeId);
                  if (!node) return <span className="text-on-surface-variant italic">点击左侧大纲树节点以关联</span>;
                  return (
                    <>
                      <div className="font-semibold">{node.title}</div>
                      {node.summary && <div className="text-on-surface-variant mt-1">{node.summary}</div>}
                      {node.characters_involved?.length > 0 && (
                        <div className="text-body-xs text-on-surface-variant mt-1">
                          角色:{node.characters_involved.join('、')}
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            </div>
          </div>

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

      {/* [P4] 历史版本预览 Modal */}
      <Modal
        title={
          <Space>
            <History size={18} className="text-primary" />
            {activeVersion ? `查看 v${activeVersion.version_no} 历史版本（只读）` : '版本预览'}
          </Space>
        }
        open={versionModalOpen}
        onCancel={() => setVersionModalOpen(false)}
        footer={null}
        width={820}
        destroyOnClose
      >
        {activeVersion && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 text-body-sm text-on-surface-variant">
              <span className="chip-primary">v{activeVersion.version_no}</span>
              <span>{activeVersion.generated_by}</span>
              <span>·</span>
              <span>{activeVersion.model_used || 'mock'}</span>
              <span>·</span>
              <span>{new Date(activeVersion.created_at).toLocaleString('zh-CN')}</span>
              {activeVersion.note && (
                <>
                  <span>·</span>
                  <span className="text-primary">{activeVersion.note}</span>
                </>
              )}
            </div>
            {activeVersion.prompt_used && (
              <details className="surface-card p-3">
                <summary className="cursor-pointer text-body-sm text-on-surface-variant">
                  查看 Prompt({activeVersion.prompt_used.length} 字)
                </summary>
                <pre className="whitespace-pre-wrap text-body-xs text-on-surface mt-2 max-h-48 overflow-y-auto">
                  {activeVersion.prompt_used.slice(0, 3000)}
                  {activeVersion.prompt_used.length > 3000 ? '\n...(已截断)' : ''}
                </pre>
              </details>
            )}
            <pre className="whitespace-pre-wrap text-body-md text-on-surface max-h-[50vh] overflow-y-auto surface-card p-4">
              {activeVersion.plain_content || '（无内容）'}
            </pre>
            <div className="flex justify-end gap-2 pt-2 border-t border-outline-variant/30">
              <Button onClick={() => setVersionModalOpen(false)}>关闭</Button>
              <Button disabled title="即将在 v2 版本支持">恢复到此版本(即将支持)</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

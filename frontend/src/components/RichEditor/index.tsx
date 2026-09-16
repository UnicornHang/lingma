import { useEditor, EditorContent, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Button } from 'antd';
import { forwardRef, useEffect, useImperativeHandle } from 'react';
import {
  Bold,
  Italic,
  Strikethrough,
  Code as CodeIcon,
  Heading1,
  Heading2,
  Quote,
  List as ListIcon,
  ListOrdered,
  Undo2,
  Redo2,
} from 'lucide-react';

import { plainToTipTapDoc } from '@/utils/plainToTipTap';

/**
 * TipTap JSON 文档的最小类型约定。
 * 真正的 TipTap JSON schema 是开放结构，这里只声明我们关心的部分。
 */
export interface TipTapNode {
  type: string;
  attrs?: Record<string, unknown>;
  content?: TipTapNode[];
  marks?: Array<{ type: string; attrs?: Record<string, unknown> }>;
  text?: string;
}

export interface TipTapDoc {
  type: 'doc';
  content?: TipTapNode[];
}

/**
 * 暴露给父组件的命令式句柄 —— 用于 AI 流式生成时实时插入 chunk
 */
export interface RichEditorHandle {
  /** 在光标位置插入纯文本。换行会拆成新段落，不走 HTML 空白折叠。 */
  insertContent: (text: string) => boolean;
  /** 整体替换为纯文本（自动切段） */
  setContent: (text: string) => boolean;
  /** 当前 TipTap JSON */
  getJSON: () => TipTapDoc | null;
  /** 获取当前纯文本（段间空行） */
  getText: () => string;
  /** 聚焦编辑器 */
  focus: () => void;
  // [提交 D] 选区/段落级操作 —— 用于行内 AI 改写 / 段内润色建议
  /** 当前选区:{from, to, text}。折叠选区(光标)返回 null */
  getSelection: () => { from: number; to: number; text: string } | null;
  /** 把 [from, to) 区间替换为 text(纯文本),触发 onChange */
  replaceRange: (from: number, to: number, text: string) => boolean;
  /** 获取光标所在自然段:{from, to, text}。无段落返回 null */
  getCurrentParagraph: () => { from: number; to: number; text: string } | null;
  /** 光标前后各 radius 字，墙式长段检测时用 */
  getCursorWindow: (radius?: number) => { from: number; to: number; text: string } | null;
  /** 在正文中定位片段并选中 */
  selectSnippet: (snippet: string) => boolean;
}

interface RichEditorProps {
  /** TipTap JSON 内容；传 null 则为空文档 */
  content?: TipTapDoc | null;
  /** 是否可编辑 */
  editable?: boolean;
  /** 内容变更回调（TipTap JSON + 纯文本） */
  onChange?: (json: TipTapDoc, plain: string) => void;
  /** 选区变化回调 —— text 为折叠选区时为 '' */
  onSelectionChange?: (range: { from: number; to: number; text: string }) => void;
  /** 类名 */
  className?: string;
}

/**
 * 基于 TipTap StarterKit 的富文本编辑器
 *
 * - 支持粗体/斜体/删除线/行内代码/标题/引用/列表/撤销
 * - 内容为 TipTap JSON（与后端 Chapter.content 字段一致）
 * - onChange 同时给出纯文本，便于字数统计 / RAG 索引
 * - 通过 ref 暴露 insertContent / getText / focus,支持外部(如 AI 流式)程序化编辑
 */
export const RichEditor = forwardRef<RichEditorHandle, RichEditorProps>(function RichEditor(
  { content, editable = true, onChange, onSelectionChange, className },
  ref
) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        history: { depth: 50 },
      }),
    ],
    content: content ?? '',
    editable,
    onUpdate: ({ editor }) => {
      onChange?.(editor.getJSON() as TipTapDoc, editor.getText());
    },
    onSelectionUpdate: ({ editor }) => {
      const { from, to } = editor.state.selection;
      // [提交 D] 回调里附带选区文本(折叠选区时 text='')
      const text = from === to ? '' : editor.state.doc.textBetween(from, to, '\n', '\n');
      onSelectionChange?.({ from, to, text });
    },
    editorProps: {
      attributes: {
        class: 'prose prose-lg max-w-none focus:outline-none min-h-[400px]',
      },
    },
  });

  // 暴露命令式 API
  useImperativeHandle(
    ref,
    () => ({
      insertContent: (text: string) => {
        if (!editor || !text) return false;
        // 按换行拆段，避免 TipTap 把 \n 当 HTML 空白吃掉
        const parts = text.split('\n');
        parts.forEach((part, i) => {
          if (i > 0) editor.commands.splitBlock();
          if (part) editor.commands.insertContent(part);
        });
        return true;
      },
      setContent: (text: string) => {
        if (!editor) return false;
        editor.commands.setContent(plainToTipTapDoc(text), false);
        return true;
      },
      getJSON: () => (editor ? (editor.getJSON() as TipTapDoc) : null),
      getText: () => editor?.getText({ blockSeparator: '\n\n' }) ?? '',
      focus: () => {
        editor?.commands.focus('end');
      },
      getSelection: () => {
        if (!editor) return null;
        const { from, to } = editor.state.selection;
        if (from === to) return null;
        const text = editor.state.doc.textBetween(from, to, '\n', '\n');
        return { from, to, text };
      },
      replaceRange: (from: number, to: number, text: string) => {
        if (!editor) return false;
        // 无换行时当行内替换，避免把短句包成新段打乱光标
        if (!text.includes('\n')) {
          return editor.chain().focus().insertContentAt({ from, to }, text).run();
        }
        const nodes = plainToTipTapDoc(text).content ?? [];
        return editor.chain().focus().insertContentAt({ from, to }, nodes).run();
      },
      getCurrentParagraph: () => {
        if (!editor) return null;
        const { from } = editor.state.selection;
        const $pos = editor.state.doc.resolve(from);
        for (let depth = $pos.depth; depth > 0; depth--) {
          const node = $pos.node(depth);
          if (node.type.name === 'paragraph' || node.type.name === 'heading') {
            const start = $pos.start(depth);
            const end = $pos.end(depth);
            if (start === end) return null;
            const text = editor.state.doc.textBetween(start, end, '\n', '\n');
            return { from: start, to: end, text };
          }
        }
        return null;
      },
      getCursorWindow: (radius = 220) => {
        if (!editor) return null;
        const { from } = editor.state.selection;
        const size = editor.state.doc.content.size;
        const start = Math.max(1, from - radius);
        const end = Math.min(size, from + radius);
        if (start >= end) return null;
        const text = editor.state.doc.textBetween(start, end, '\n', '\n');
        return { from: start, to: end, text };
      },
      selectSnippet: (snippet: string) => {
        if (!editor || !snippet.trim()) return false;
        const needle = snippet.trim().slice(0, 24);
        let found = false;
        editor.state.doc.descendants((node, pos) => {
          if (found || !node.isText || !node.text) return true;
          const idx = node.text.indexOf(needle);
          if (idx < 0) return true;
          const from = pos + idx;
          const to = Math.min(pos + idx + snippet.trim().length, pos + node.text.length);
          editor.chain().focus().setTextSelection({ from, to }).scrollIntoView().run();
          found = true;
          return false;
        });
        return found;
      },
    }),
    [editor]
  );

  // editable 变化时同步
  useEffect(() => {
    editor?.setEditable(editable);
  }, [editor, editable]);

  // 外部 content 变化时同步（仅当 editor 未聚焦且 content 不同）
  useEffect(() => {
    if (!editor) return;
    if (!content) return;
    const current = JSON.stringify(editor.getJSON());
    const incoming = JSON.stringify(content);
    if (current !== incoming && !editor.isFocused) {
      editor.commands.setContent(content, false);
    }
  }, [editor, content]);

  return (
    <div className={`rich-editor flex flex-col ${className ?? ''}`}>
      {editable && editor && <Toolbar editor={editor} />}
      <div className="flex-1 px-6 py-4 bg-surface-container-lowest rounded-b-lg border border-t-0 border-outline-variant/30">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
});

interface ToolbarProps {
  editor: Editor;
}

function Toolbar({ editor }: ToolbarProps) {
  const Btn = ({
    onClick,
    active,
    disabled,
    children,
    title,
  }: {
    onClick: () => void;
    active?: boolean;
    disabled?: boolean;
    children: React.ReactNode;
    title: string;
  }) => (
    <Button
      type={active ? 'primary' : 'text'}
      size="small"
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{ width: 32, height: 32, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
    >
      {children}
    </Button>
  );

  const Divider = () => <div className="w-px h-5 bg-outline-variant/40 mx-1" />;

  return (
    <div className="flex items-center gap-1 p-1 bg-surface-container-lowest rounded-t-lg border border-outline-variant/30">
      <Btn onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} title="撤销 (Ctrl+Z)">
        <Undo2 size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} title="重做 (Ctrl+Y)">
        <Redo2 size={16} />
      </Btn>
      <Divider />
      <Btn onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="粗体 (Ctrl+B)">
        <Bold size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="斜体 (Ctrl+I)">
        <Italic size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleStrike().run()} active={editor.isActive('strike')} title="删除线">
        <Strikethrough size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleCode().run()} active={editor.isActive('code')} title="行内代码">
        <CodeIcon size={16} />
      </Btn>
      <Divider />
      <Btn onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={editor.isActive('heading', { level: 1 })} title="标题 1">
        <Heading1 size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive('heading', { level: 2 })} title="标题 2">
        <Heading2 size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="引用">
        <Quote size={16} />
      </Btn>
      <Divider />
      <Btn onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="无序列表">
        <ListIcon size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="有序列表">
        <ListOrdered size={16} />
      </Btn>
    </div>
  );
}
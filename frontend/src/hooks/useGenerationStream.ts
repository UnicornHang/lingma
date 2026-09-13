import { useCallback, useEffect, useRef, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import type { AutoPolishReport, AutoRewriteReport, CriticSummary } from '@/api/chapters';

/** 与 docs/API.md 一致的 WS 服务端推送类型 */
export type GenerationServerEvent =
  | { type: 'connected'; task_id: string; message?: string }
  | { type: 'start'; task_id: string; stream_id: string; model: string; mode?: 'continue' | 'generate' }
  | { type: 'delta'; task_id: string; stream_id: string; content: string }
  | {
      type: 'done';
      task_id: string;
      stream_id: string;
      content: string;
      token_usage?: { input_tokens: number; output_tokens: number };
      mode?: 'continue' | 'generate';
      /** [提交 C] 自动去味报告(若开启) */
      auto_polish_report?: AutoPolishReport | null;
      /** [P2] 自动 critic 评审报告(若开启) */
      critic?: CriticSummary | null;
      /** [P3.3] 自动改写循环报告(若触发) */
      auto_rewrite_report?: AutoRewriteReport | null;
    }
  | { type: 'error'; task_id?: string; stream_id?: string; error: string }
  | { type: 'cancelled'; task_id: string }
  | { type: 'pong' };

/** 客户端发送给服务端的 start 消息（messages 可选：缺省时由后端 WriterAgent 加载上下文） */
export interface GenerationClientStartMessage {
  type: 'start';
  messages?: Array<{ role: 'system' | 'user' | 'assistant'; content: string }> | null;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  mode?: 'continue' | 'generate';
  continue_from_chars?: number;
  target_word_count?: number;
  /** [提交 C] 是否启用自动去味(默认 true) */
  auto_polish?: boolean;
  /** [提交 C] blocking 阈值 */
  max_blocking_for_rewrite?: number;
  /** [P2] 是否启用自动 critic 评审(默认 true) */
  auto_critic?: boolean;
}

export type GenerationClientMessage =
  | GenerationClientStartMessage
  | { type: 'ping' }
  | { type: 'cancel' };

export type GenerationStatus = 'idle' | 'connecting' | 'ready' | 'streaming' | 'done' | 'error' | 'cancelled';

export interface GenerationStartOpts {
  model?: string;
  max_tokens?: number;
  temperature?: number;
  /** 续写 vs 全量重写（默认 continue）。会被写入 task.params */
  mode?: 'continue' | 'generate';
  /** 续写模式下取章节末尾 N 字作为 prompt 上下文 */
  continue_from_chars?: number;
  /** 本次生成目标字数（覆盖 outline 默认） */
  target_word_count?: number;
  /** [提交 C] 自动去味开关(默认 true) */
  auto_polish?: boolean;
  /** [提交 C] blocking 阈值 */
  max_blocking_for_rewrite?: number;
  /** [P2] 自动 critic 评审开关(默认 true) */
  auto_critic?: boolean;
  /** 每个 delta 到达时的回调（用于实时插入编辑器） */
  onDelta?: (chunk: string) => void;
}

interface UseGenerationStreamOptions {
  /** 默认模型 */
  defaultModel?: string;
  /** 默认最大 token */
  defaultMaxTokens?: number;
}

interface UseGenerationStreamReturn {
  status: GenerationStatus;
  /** 已接收到的完整正文 */
  content: string;
  /** 错误信息 */
  error: string | null;
  /** 当前模型 */
  model: string | null;
  /** [提交 C] 自动去味报告(done 时填充) */
  autoPolishReport: AutoPolishReport | null;
  /** [P2] 自动 critic 评审报告(done 时填充) */
  criticReport: CriticSummary | null;
  /** [P3.3] 自动改写循环报告(done 时填充,可能 null) */
  autoRewriteReport: AutoRewriteReport | null;
  /**
   * 注册「待发 start 意图」。Hook 内部 effect 会在 WS 进入 OPEN 时自动发送。
   * 多次调用以最新一次为准。StrictMode 双连接场景下安全:
   *  start 只发到当前仍存活的 WS,不会被发到被立刻 cleanup 的 WS#1。
   */
  start: (
    messages?: Array<{ role: 'system' | 'user' | 'assistant'; content: string }> | null,
    opts?: GenerationStartOpts
  ) => void;
  /** 取消 */
  cancel: () => void;
  /** 重置状态 */
  reset: () => void;
}

/**
 * ZhiMeng 流式生成 Hook(StrictMode-safe)
 *
 * 协议：
 *  1. 连入 ws://<host>/ws/generation/{task_id}
 *  2. 收到 {type:'connected'} 后,Hook 内部 effect 自动发送 start(messages, opts)
 *  3. 持续接收 delta；可通过 opts.onDelta 做实时插入（每次 chunk 都会触发）
 *  4. 调用 reset() 或重新 start() 重置内部 buffer
 *
 * 设计要点：
 *  - start 的发送**放在 Hook 内部**而不是组件 effect。这是 React 18 StrictMode 下唯一
 *    安全的位置:StrictMode 会让组件 mount → unmount → mount,导致 useWebSocket 在
 *    第一次 cleanup 时关闭 WS#1,而组件侧的 effect 不会因为 WS#2 建立再次触发,
 *    造成「start 只发给了已断开的 WS,新 WS 永远等不到 start」的 bug
 *  - 组件通过调用 `start(...)` 注册意图;effect 在 WS ready 且 taskId 设置时自动发送
 */
export function useGenerationStream(
  taskId: string | null,
  options: UseGenerationStreamOptions = {}
): UseGenerationStreamReturn {
  // 注意:不要给 model 一个 fallback 默认值(如 'gpt-4o-mini')。
  // 用户的实际 LLM Provider 由后端 APIConfig 决定(model_name 字段),
  // 前端默认模型只会"污染"请求、让不支持该 model 的 provider 报 400。
  // 当 opts.model 也未传时,start 消息中 model 字段省略即可,
  // 后端 LLMService.stream 会自动用 cfg.model。
  const { defaultModel = '', defaultMaxTokens = 2048 } = options;

  const [status, setStatus] = useState<GenerationStatus>('idle');
  const [content, setContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  // [提交 C] 自动去味报告(done 时填充)
  const [autoPolishReport, setAutoPolishReport] = useState<AutoPolishReport | null>(null);
  // [P2] 自动 critic 评审报告(done 时填充)
  const [criticReport, setCriticReport] = useState<CriticSummary | null>(null);
  // [P3.3] 自动改写循环报告(done 时填充,可能 null)
  const [autoRewriteReport, setAutoRewriteReport] = useState<AutoRewriteReport | null>(null);

  // 防止卸载后仍然 setState
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // 待发 start 的「意图」,start() 调用时写入
  const pendingStartRef = useRef<{
    messages: GenerationClientStartMessage['messages'];
    opts: GenerationStartOpts | null;
  } | null>(null);
  // 用于 delta reducer 读取最新的 onDelta(避免 effect 依赖变化频繁重置)
  const optsRef = useRef<GenerationStartOpts | null>(null);

  // 计算 ws URL —— 通过 vite proxy 或 nginx
  const wsBase = (import.meta.env.VITE_WS_BASE as string | undefined) ?? '';
  const wsUrl = taskId ? `${wsBase}/ws/generation/${taskId}` : null;

  const { readyState, lastMessage, send, close } = useWebSocket<GenerationServerEvent>(wsUrl, {
    autoConnect: true,
    reconnect: false, // 生成任务不需要自动重连，断线即结束
  });

  // 派生状态
  useEffect(() => {
    if (readyState === 'CONNECTING') setStatus('connecting');
    else if (readyState === 'OPEN') setStatus('ready');
    else if (readyState === 'CLOSING') {/* keep current */}
    else if (readyState === 'CLOSED' && status !== 'done' && status !== 'error' && status !== 'cancelled') {
      // 仅在尚未有终态时显示 idle
      if (status === 'connecting' || status === 'ready') setStatus('idle');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readyState]);

  // 处理消息
  useEffect(() => {
    if (!lastMessage) return;
    const safe = (fn: () => void) => { if (mountedRef.current) fn(); };

    switch (lastMessage.type) {
      case 'connected':
        safe(() => setStatus('ready'));
        break;
      case 'start':
        safe(() => {
          setStatus('streaming');
          setContent('');
          setError(null);
          setModel(lastMessage.model);
          setAutoPolishReport(null);
          setCriticReport(null);
        });
        break;
      case 'delta':
        safe(() => {
          setContent((prev) => prev + lastMessage.content);
          // 实时插入回调(由调用方决定是否使用)
          optsRef.current?.onDelta?.(lastMessage.content);
        });
        break;
      case 'done':
        safe(() => {
          setContent(lastMessage.content);
          setStatus('done');
          setAutoPolishReport(lastMessage.auto_polish_report ?? null);
          setCriticReport(lastMessage.critic ?? null);
          setAutoRewriteReport(lastMessage.auto_rewrite_report ?? null);
        });
        break;
      case 'error':
        safe(() => {
          setError(lastMessage.error);
          setStatus('error');
        });
        break;
      case 'cancelled':
        safe(() => setStatus('cancelled'));
        break;
      case 'pong':
        break;
    }
  }, [lastMessage]);

  /**
   * 核心 effect:WS 进入 OPEN 且有待发 start 意图时,自动发送。
   *
   * deps 只跟踪 [readyState, taskId]:
   *  - readyState 从 CONNECTING → OPEN 时发送
   *  - taskId 变化时(包括从 null → 值)会重新发送新 task 的 start
   *
   * StrictMode 安全性:即使 WS#1 被 cleanup、WS#2 新建,只要 WS#2 进入 OPEN 且
   * pendingStartRef 仍有待发意图,就会在这里发送一次。组件侧的 effect 在
   * StrictMode 下会因为状态没变而不触发,这是已知 React 行为。
   */
  useEffect(() => {
    if (readyState !== 'OPEN') return;
    if (!taskId) return;
    const pending = pendingStartRef.current;
    if (!pending) return;
    const { messages, opts } = pending;
    const payload: GenerationClientStartMessage = {
      type: 'start',
      messages: messages ?? undefined,
      // 只在显式指定 model 时才带这个字段,让后端用 cfg.model
      ...(opts?.model || defaultModel ? { model: opts?.model || defaultModel } : {}),
      max_tokens: opts?.max_tokens ?? defaultMaxTokens,
      temperature: opts?.temperature ?? 0.8,
      mode: opts?.mode,
      continue_from_chars: opts?.continue_from_chars,
      target_word_count: opts?.target_word_count,
      auto_polish: opts?.auto_polish,
      max_blocking_for_rewrite: opts?.max_blocking_for_rewrite,
      auto_critic: opts?.auto_critic,
    };
    send(payload);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readyState, taskId]);

  const start = useCallback(
    (
      messages?: Array<{ role: 'system' | 'user' | 'assistant'; content: string }> | null,
      opts?: GenerationStartOpts
    ) => {
      if (!taskId) {
        setError('缺少 taskId');
        setStatus('error');
        return;
      }
      // 保存 onDelta 回调给 delta reducer 使用
      optsRef.current = opts ?? null;
      // 注册「待发 start」意图。effect 在 WS ready 时自动发送
      pendingStartRef.current = {
        messages: messages ?? undefined,
        opts: opts ?? null,
      };
      // 如果 WS 已经 OPEN,effect 由于 deps 未变不会自动跑,这里直接发送
      if (readyState === 'OPEN') {
        const payload: GenerationClientStartMessage = {
          type: 'start',
          messages: messages ?? undefined,
          // 只在显式指定 model 时才带这个字段,让后端用 cfg.model
          ...(opts?.model || defaultModel ? { model: opts?.model || defaultModel } : {}),
          max_tokens: opts?.max_tokens ?? defaultMaxTokens,
          temperature: opts?.temperature ?? 0.8,
          mode: opts?.mode,
          continue_from_chars: opts?.continue_from_chars,
          target_word_count: opts?.target_word_count,
          auto_polish: opts?.auto_polish,
          max_blocking_for_rewrite: opts?.max_blocking_for_rewrite,
          auto_critic: opts?.auto_critic,
        };
        send(payload);
      }
    },
    [taskId, readyState, send, defaultModel, defaultMaxTokens]
  );

  const cancel = useCallback(() => {
    pendingStartRef.current = null; // 取消任何待发 start
    send({ type: 'cancel' });
    setStatus('cancelled');
    try { close(1000, 'client cancel'); } catch { /* noop */ }
  }, [send, close]);

  const reset = useCallback(() => {
    pendingStartRef.current = null;
    setStatus('idle');
    setContent('');
    setError(null);
    setModel(null);
    setAutoPolishReport(null);
    setCriticReport(null);
    optsRef.current = null;
  }, []);

  return { status, content, error, model, autoPolishReport, criticReport, autoRewriteReport, start, cancel, reset };
}
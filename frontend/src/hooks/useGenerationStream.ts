import { useCallback, useEffect, useRef, useState } from 'react';
import { useWebSocket } from './useWebSocket';

/** 与 docs/API.md 一致的 WS 服务端推送类型 */
export type GenerationServerEvent =
  | { type: 'connected'; task_id: string; message?: string }
  | { type: 'start'; task_id: string; stream_id: string; model: string }
  | { type: 'delta'; task_id: string; stream_id: string; content: string }
  | { type: 'done'; task_id: string; stream_id: string; content: string }
  | { type: 'error'; task_id?: string; stream_id?: string; error: string }
  | { type: 'cancelled'; task_id: string }
  | { type: 'pong' };

/** 客户端可发送给服务端的控制消息 */
export interface GenerationClientStartMessage {
  type: 'start';
  messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

export type GenerationClientMessage =
  | GenerationClientStartMessage
  | { type: 'ping' }
  | { type: 'cancel' };

export type GenerationStatus = 'idle' | 'connecting' | 'ready' | 'streaming' | 'done' | 'error' | 'cancelled';

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
  /** 流式开始 */
  start: (messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>, opts?: { model?: string; max_tokens?: number; temperature?: number }) => void;
  /** 取消 */
  cancel: () => void;
  /** 重置状态 */
  reset: () => void;
}

/**
 * LingMa 流式生成 Hook
 *
 * 协议：
 *  1. 连入 ws://<host>/ws/generation/{task_id}
 *  2. 收到 {type:'connected'} 后，调用 start(messages) 发送 start 消息
 *  3. 持续接收 delta，调用 reset() 或重新 start() 重置内部 buffer
 */
export function useGenerationStream(
  taskId: string | null,
  options: UseGenerationStreamOptions = {}
): UseGenerationStreamReturn {
  const { defaultModel = 'gpt-4o-mini', defaultMaxTokens = 2048 } = options;

  const [status, setStatus] = useState<GenerationStatus>('idle');
  const [content, setContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);

  // 防止卸载后仍然 setState
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

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
        });
        break;
      case 'delta':
        safe(() => setContent((prev) => prev + lastMessage.content));
        break;
      case 'done':
        safe(() => {
          setContent(lastMessage.content);
          setStatus('done');
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

  const start = useCallback(
    (
      messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>,
      opts?: { model?: string; max_tokens?: number; temperature?: number }
    ) => {
      if (readyState !== 'OPEN') {
        setError('WebSocket 尚未连接');
        setStatus('error');
        return;
      }
      const payload: GenerationClientStartMessage = {
        type: 'start',
        messages,
        model: opts?.model ?? defaultModel,
        max_tokens: opts?.max_tokens ?? defaultMaxTokens,
        temperature: opts?.temperature ?? 0.8,
      };
      send(payload);
    },
    [readyState, send, defaultModel, defaultMaxTokens]
  );

  const cancel = useCallback(() => {
    send({ type: 'cancel' });
    setStatus('cancelled');
    try { close(1000, 'client cancel'); } catch { /* noop */ }
  }, [send, close]);

  const reset = useCallback(() => {
    setStatus('idle');
    setContent('');
    setError(null);
    setModel(null);
  }, []);

  return { status, content, error, model, start, cancel, reset };
}
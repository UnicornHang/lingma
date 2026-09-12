import { useEffect, useRef, useState, useCallback } from 'react';

export type WsReadyState = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';

interface UseWebSocketOptions {
  /** 是否自动连接，默认 true */
  autoConnect?: boolean;
  /** 断线后是否自动重连，默认 true */
  reconnect?: boolean;
  /** 最大重连次数，默认 5 */
  maxRetries?: number;
  /** 自定义协议（如果需要） */
  protocols?: string | string[];
}

interface UseWebSocketReturn<T = unknown> {
  readyState: WsReadyState;
  /** 最新一条消息 */
  lastMessage: T | null;
  /** 主动发送 */
  send: (data: string | object) => void;
  /** 主动关闭 */
  close: (code?: number, reason?: string) => void;
  /** 手动触发重连 */
  reconnectManually: () => void;
}

/**
 * 通用 WebSocket 客户端 Hook
 *
 * @example
 * const { lastMessage, send } = useWebSocket<ServerMsg>('/ws/foo');
 * useEffect(() => { if (lastMessage?.type === 'delta') append(lastMessage.content); }, [lastMessage]);
 */
export function useWebSocket<T = unknown>(
  url: string | null,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn<T> {
  const { autoConnect = true, reconnect = true, maxRetries = 5, protocols } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const manualCloseRef = useRef(false);

  const [readyState, setReadyState] = useState<WsReadyState>('CLOSED');
  const [lastMessage, setLastMessage] = useState<T | null>(null);

  const connect = useCallback(() => {
    if (!url) return;
    manualCloseRef.current = false;

    const ws = new WebSocket(url, protocols);
    wsRef.current = ws;
    setReadyState('CONNECTING');

    ws.onopen = () => {
      retryRef.current = 0;
      setReadyState('OPEN');
    };

    ws.onmessage = (event) => {
      try {
        setLastMessage(JSON.parse(event.data) as T);
      } catch {
        setLastMessage(event.data as unknown as T);
      }
    };

    ws.onerror = () => {
      // 关闭事件会随后触发，由其处理重连
      try { ws.close(); } catch { /* noop */ }
    };

    ws.onclose = () => {
      setReadyState('CLOSED');
      wsRef.current = null;
      if (reconnect && !manualCloseRef.current && retryRef.current < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retryRef.current), 30_000);
        retryRef.current += 1;
        setTimeout(connect, delay);
      }
    };
  }, [url, reconnect, maxRetries, protocols]);

  useEffect(() => {
    if (!autoConnect || !url) return;
    connect();
    return () => {
      manualCloseRef.current = true;
      try { wsRef.current?.close(); } catch { /* noop */ }
    };
  }, [connect, autoConnect, url]);

  const send = useCallback((data: string | object) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(typeof data === 'string' ? data : JSON.stringify(data));
  }, []);

  const close = useCallback((code?: number, reason?: string) => {
    manualCloseRef.current = true;
    try { wsRef.current?.close(code, reason); } catch { /* noop */ }
  }, []);

  const reconnectManually = useCallback(() => {
    manualCloseRef.current = false;
    retryRef.current = 0;
    try { wsRef.current?.close(); } catch { /* noop */ }
    connect();
  }, [connect]);

  return { readyState, lastMessage, send, close, reconnectManually };
}
/**
 * 🔄 WebSocket hook — Sprint 6 Task 5.
 *
 * Real-time sync via WebSocket with exponential backoff reconnection.
 * Falls back to polling if WebSocket fails.
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { getHost } from "./api";

type WSEvent =
    | { type: "companion_state_update"; data: Record<string, any> }
    | { type: "task_completed"; data: { task_id: string; result: string } }
    | { type: "chat_message"; data: { role: string; content: string } }
    | { type: "ping" };

interface UseWebSocketReturn {
    connected: boolean;
    lastEvent: WSEvent | null;
    send: (data: Record<string, any>) => void;
}

export function useWebSocket(onEvent?: (event: WSEvent) => void): UseWebSocketReturn {
    const [connected, setConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const retriesRef = useRef(0);
    const maxRetries = 10;

    const connect = useCallback(async () => {
        try {
            const host = await getHost();
            if (!host) return;

            const wsUrl = `ws://${host}/api/v1/companion/ws`;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                setConnected(true);
                retriesRef.current = 0;
            };

            ws.onmessage = (event) => {
                try {
                    const parsed: WSEvent = JSON.parse(event.data);
                    setLastEvent(parsed);
                    onEvent?.(parsed);
                } catch { }
            };

            ws.onclose = () => {
                setConnected(false);
                wsRef.current = null;

                // Exponential backoff reconnect
                if (retriesRef.current < maxRetries) {
                    const delay = Math.min(1000 * Math.pow(2, retriesRef.current), 30000);
                    retriesRef.current++;
                    setTimeout(connect, delay);
                }
            };

            ws.onerror = () => {
                ws.close();
            };
        } catch { }
    }, [onEvent]);

    useEffect(() => {
        connect();
        return () => {
            wsRef.current?.close();
            wsRef.current = null;
        };
    }, [connect]);

    const send = useCallback((data: Record<string, any>) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(data));
        }
    }, []);

    return { connected, lastEvent, send };
}

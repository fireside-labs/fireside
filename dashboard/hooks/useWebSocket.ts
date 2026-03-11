"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { ValhallaEvent, getEvents, getWebSocketUrl } from "@/lib/api";

interface UseWebSocketReturn {
    events: ValhallaEvent[];
    connected: boolean;
    lastEvent: ValhallaEvent | null;
}

export function useWebSocket(): UseWebSocketReturn {
    const [events, setEvents] = useState<ValhallaEvent[]>([]);
    const [connected, setConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState<ValhallaEvent | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const retryRef = useRef(0);
    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    const startPolling = useCallback(() => {
        if (pollingRef.current) return;
        pollingRef.current = setInterval(async () => {
            try {
                const data = await getEvents();
                setEvents(data);
                if (data.length > 0) setLastEvent(data[0]);
            } catch { /* ignore */ }
        }, 5000);
    }, []);

    const stopPolling = useCallback(() => {
        if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
        }
    }, []);

    const connectWs = useCallback(() => {
        try {
            const ws = new WebSocket(getWebSocketUrl());

            ws.onopen = () => {
                setConnected(true);
                retryRef.current = 0;
                stopPolling();
            };

            ws.onmessage = (msg) => {
                try {
                    const event: ValhallaEvent = JSON.parse(msg.data);
                    setEvents((prev) => [event, ...prev].slice(0, 50));
                    setLastEvent(event);
                } catch { /* ignore bad messages */ }
            };

            ws.onclose = () => {
                setConnected(false);
                wsRef.current = null;
                // Exponential backoff retry
                const delay = Math.min(1000 * Math.pow(2, retryRef.current), 30000);
                retryRef.current++;
                startPolling();
                setTimeout(connectWs, delay);
            };

            ws.onerror = () => {
                ws.close();
            };

            wsRef.current = ws;
        } catch {
            // WebSocket not available — fall back to polling
            startPolling();
        }
    }, [startPolling, stopPolling]);

    useEffect(() => {
        // Load initial events
        getEvents().then((data) => {
            setEvents(data);
            if (data.length > 0) setLastEvent(data[0]);
        }).catch(() => { });

        // Try WebSocket, fall back to polling
        connectWs();

        return () => {
            wsRef.current?.close();
            stopPolling();
        };
    }, [connectWs, stopPolling]);

    return { events, connected, lastEvent };
}

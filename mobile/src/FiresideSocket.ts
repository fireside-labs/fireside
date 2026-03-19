/**
 * 🔌 FiresideSocket — Persistent WebSocket to the home PC.
 *
 * Replaces HTTP polling with a real-time bidirectional channel.
 * Connects to the existing backend WebSocket at /api/v1/companion/ws.
 *
 * Features:
 *   - Auto-reconnect with exponential backoff (1s → 2s → 4s → 8s → 30s cap)
 *   - Ping/pong heartbeat every 15s — detects dead connections fast
 *   - Typed event dispatch for companion updates, tasks, chat, notifications
 *   - Connection state machine: discovering → connecting → connected → reconnecting → offline
 *   - Session ID for cross-device context tracking
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { baseUrl, getActiveHost } from "./api";

const SESSION_KEY = "fireside_session_id";
const PAIR_TOKEN_KEY = "fireside_pair_token";
const HEARTBEAT_MS = 15_000;
const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;
const MAX_RECONNECT_ATTEMPTS = 50; // Give up after ~15 min of trying

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ConnectionPhase =
    | "idle"
    | "discovering"
    | "connecting"
    | "connected"
    | "reconnecting"
    | "offline";

export interface FiresideEvent {
    type: string;
    data: any;
}

export type EventCallback = (event: FiresideEvent) => void;
export type PhaseCallback = (phase: ConnectionPhase) => void;

// ---------------------------------------------------------------------------
// Session ID
// ---------------------------------------------------------------------------

function generateSessionId(): string {
    const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
    let id = "mob_";
    for (let i = 0; i < 12; i++) {
        id += chars[Math.floor(Math.random() * chars.length)];
    }
    return id;
}

export async function getSessionId(): Promise<string> {
    let sid = await AsyncStorage.getItem(SESSION_KEY);
    if (!sid) {
        sid = generateSessionId();
        await AsyncStorage.setItem(SESSION_KEY, sid);
    }
    return sid;
}

/** Store the pairing token for WebSocket auth. */
export async function setPairToken(token: string): Promise<void> {
    await AsyncStorage.setItem(PAIR_TOKEN_KEY, token);
}

/** Get the stored pairing token. */
export async function getPairToken(): Promise<string | null> {
    return AsyncStorage.getItem(PAIR_TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// FiresideSocket
// ---------------------------------------------------------------------------

export class FiresideSocket {
    private ws: WebSocket | null = null;
    private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private reconnectAttempts = 0;
    private intentionalClose = false;
    private _phase: ConnectionPhase = "idle";
    private _sessionId: string | null = null;

    // Callbacks
    private eventListeners: EventCallback[] = [];
    private phaseListeners: PhaseCallback[] = [];

    // ---------------------------------------------------------------------------
    // Public API
    // ---------------------------------------------------------------------------

    /** Current connection phase. */
    get phase(): ConnectionPhase {
        return this._phase;
    }

    /** Whether the socket is connected and ready. */
    get isConnected(): boolean {
        return this._phase === "connected" && this.ws?.readyState === WebSocket.OPEN;
    }

    /** Register an event listener. Returns unsubscribe function. */
    onEvent(cb: EventCallback): () => void {
        this.eventListeners.push(cb);
        return () => {
            this.eventListeners = this.eventListeners.filter((l) => l !== cb);
        };
    }

    /** Register a phase change listener. Returns unsubscribe function. */
    onPhaseChange(cb: PhaseCallback): () => void {
        this.phaseListeners.push(cb);
        return () => {
            this.phaseListeners = this.phaseListeners.filter((l) => l !== cb);
        };
    }

    /** Connect to the home PC. */
    async connect(): Promise<void> {
        if (this.ws?.readyState === WebSocket.OPEN) return;

        this.intentionalClose = false;
        this.setPhase("discovering");

        try {
            const host = await getActiveHost();
            if (!host) {
                this.setPhase("offline");
                return;
            }

            this._sessionId = await getSessionId();
            const token = await getPairToken();

            // Build WebSocket URL from the HTTP host
            const wsHost = host.includes(":") ? host : `${host}:8765`;
            const wsUrl = `ws://${wsHost}/api/v1/companion/ws?token=${token || ""}&session_id=${this._sessionId}`;

            this.setPhase("connecting");
            this.createWebSocket(wsUrl);
        } catch {
            this.setPhase("offline");
            this.scheduleReconnect();
        }
    }

    /** Send a typed message to the desktop. */
    send(type: string, data: any = {}): boolean {
        if (!this.isConnected) return false;
        try {
            this.ws!.send(
                JSON.stringify({ type, data, session_id: this._sessionId })
            );
            return true;
        } catch {
            return false;
        }
    }

    /** Request a full sync from the desktop. */
    requestSync(): boolean {
        return this.send("sync", {});
    }

    /** Send a chat message via WebSocket (for bidirectional sync). */
    sendChat(message: string, role: "user" | "companion" = "user"): boolean {
        return this.send("chat_message", { message, role, timestamp: Date.now() });
    }

    /** Teach the companion a fact via WebSocket. */
    sendTeach(fact: string): boolean {
        return this.send("teach", { fact });
    }

    /** Ping the server (also verifies the connection is alive). */
    ping(): boolean {
        if (!this.isConnected) return false;
        try {
            this.ws!.send("ping");
            return true;
        } catch {
            return false;
        }
    }

    /** Gracefully disconnect. */
    disconnect(): void {
        this.intentionalClose = true;
        this.clearTimers();
        if (this.ws) {
            this.ws.close(1000, "User disconnect");
            this.ws = null;
        }
        this.setPhase("offline");
    }

    /** Destroy the socket entirely (on unmount). */
    destroy(): void {
        this.disconnect();
        this.eventListeners = [];
        this.phaseListeners = [];
    }

    // ---------------------------------------------------------------------------
    // Internal
    // ---------------------------------------------------------------------------

    private createWebSocket(url: string): void {
        try {
            this.ws = new WebSocket(url);
        } catch {
            this.setPhase("offline");
            this.scheduleReconnect();
            return;
        }

        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
            this.setPhase("connected");
            this.startHeartbeat();

            // Request initial sync on connect
            this.send("sync", {});
        };

        this.ws.onmessage = (event) => {
            try {
                // Handle plain-text pong
                if (event.data === "pong" || event.data === '{"type":"pong"}') {
                    return;
                }

                const parsed: FiresideEvent = JSON.parse(event.data);
                this.dispatchEvent(parsed);
            } catch {
                // Non-JSON message, ignore
            }
        };

        this.ws.onerror = () => {
            // Error is always followed by onclose, handle reconnect there
        };

        this.ws.onclose = (event) => {
            this.clearTimers();
            this.ws = null;

            if (this.intentionalClose) {
                this.setPhase("offline");
                return;
            }

            // Unexpected close — reconnect
            this.setPhase("reconnecting");
            this.scheduleReconnect();
        };
    }

    private startHeartbeat(): void {
        this.clearHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            if (!this.ping()) {
                // Ping failed — connection is dead
                this.ws?.close();
            }
        }, HEARTBEAT_MS);
    }

    private clearHeartbeat(): void {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    private scheduleReconnect(): void {
        if (this.intentionalClose) return;
        if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            this.setPhase("offline");
            return;
        }

        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s, 30s, ...
        const delay = Math.min(
            RECONNECT_BASE_MS * Math.pow(2, this.reconnectAttempts),
            RECONNECT_MAX_MS
        );
        this.reconnectAttempts++;

        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, delay);
    }

    private clearTimers(): void {
        this.clearHeartbeat();
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }

    private setPhase(phase: ConnectionPhase): void {
        if (this._phase === phase) return;
        this._phase = phase;
        for (const cb of this.phaseListeners) {
            try {
                cb(phase);
            } catch {
                // Don't let listener errors crash the socket
            }
        }
    }

    private dispatchEvent(event: FiresideEvent): void {
        for (const cb of this.eventListeners) {
            try {
                cb(event);
            } catch {
                // Don't let listener errors crash the socket
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Singleton
// ---------------------------------------------------------------------------

let _instance: FiresideSocket | null = null;

/** Get the shared FiresideSocket instance. */
export function getSocket(): FiresideSocket {
    if (!_instance) {
        _instance = new FiresideSocket();
    }
    return _instance;
}

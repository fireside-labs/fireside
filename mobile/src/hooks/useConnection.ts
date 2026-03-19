/**
 * useConnection — Manages connectivity & power state.
 *
 * Architecture: WebSocket-first with HTTP fallback.
 *
 * Connection Phases:
 *   🔍 discovering   — looking for the home PC (mDNS / subnet scan)
 *   🔗 connecting    — WebSocket handshake in progress
 *   🟢 connected     — live WebSocket, real-time push from desktop
 *   🟡 reconnecting  — connection lost, auto-retrying with backoff
 *   ⚫ offline       — no connection, pocket mode
 *
 * - On mount: connects FiresideSocket to the backend
 * - WebSocket pushes replace the old 30s HTTP polling
 * - Queues offline actions and replays on reconnect
 * - Falls back to HTTP sync if WebSocket is unavailable
 */
import { useState, useEffect, useCallback, useRef } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { companionAPI, testConnection, getHost, getConnectionPref } from "../api";
import {
    getSocket,
    ConnectionPhase,
    FiresideEvent,
} from "../FiresideSocket";
import type { MobileSyncResponse, CompanionState } from "../types";

const CACHE_KEY = "fireside_cache";
const LAST_SEEN_KEY = "fireside_last_seen";
const RECONNECT_FLASH_MS = 3_000;

/** Format a duration in ms to human-readable string. */
function formatDuration(ms: number): string {
    const mins = Math.floor(ms / 60_000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    const remMins = mins % 60;
    if (hours < 24) return remMins > 0 ? `${hours}h ${remMins}m` : `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h`;
}

export type PowerState = "home" | "connected" | "offline" | "reconnected";

export interface OfflineAction {
    type: "feed" | "walk" | "chat" | "play";
    payload?: string;
    timestamp: number;
}

interface ConnectionState {
    isOnline: boolean;
    isConfigured: boolean;
    powerState: PowerState;
    /** Granular connection phase from the WebSocket state machine. */
    connectionPhase: ConnectionPhase;
    companionData: MobileSyncResponse | null;
    offlineActions: OfflineAction[];
    isLoading: boolean;
    /** How long the user has been away from the desktop (human-readable). */
    awayDuration: string | null;
    /** Timestamp of last successful sync. */
    lastSeen: number | null;
}

export function useConnection() {
    const [state, setState] = useState<ConnectionState>({
        isOnline: false,
        isConfigured: false,
        powerState: "offline",
        connectionPhase: "idle",
        companionData: null,
        offlineActions: [],
        isLoading: true,
        awayDuration: null,
        lastSeen: null,
    });

    const wasOfflineRef = useRef(true);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    /** Determine power state from connection type. */
    const determinePowerState = useCallback(async (isOnline: boolean): Promise<PowerState> => {
        if (!isOnline) return "offline";
        const pref = await getConnectionPref();
        return pref === "bridge" ? "connected" : "home";
    }, []);

    /** Flash reconnected state, then settle. */
    const flashReconnected = useCallback(async () => {
        setState((prev) => ({ ...prev, powerState: "reconnected" }));

        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(async () => {
            const settled = await determinePowerState(true);
            setState((prev) => ({ ...prev, powerState: settled }));
        }, RECONNECT_FLASH_MS);
    }, [determinePowerState]);

    /** Save companion data to AsyncStorage for offline access. */
    const cacheData = useCallback(async (data: MobileSyncResponse) => {
        try {
            await AsyncStorage.setItem(CACHE_KEY, JSON.stringify(data));
        } catch { }
    }, []);

    /** Load cached data from AsyncStorage. */
    const loadCache = useCallback(async (): Promise<MobileSyncResponse | null> => {
        try {
            const raw = await AsyncStorage.getItem(CACHE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    }, []);

    /** Replay queued offline actions when connection resumes. */
    const replayOfflineActions = useCallback(
        async (actions: OfflineAction[]) => {
            for (const action of actions) {
                try {
                    switch (action.type) {
                        case "feed":
                            await companionAPI.feed(action.payload || "treat");
                            break;
                        case "walk":
                            await companionAPI.walk();
                            break;
                        case "chat":
                            // Use WebSocket for chat replay (avoids SSE parsing issues)
                            if (action.payload) {
                                const socket = getSocket();
                                if (socket.isConnected) {
                                    socket.sendChat(action.payload, "user");
                                } else {
                                    // Fallback to legacy chat if WS not available
                                    await companionAPI.chat(action.payload);
                                }
                            }
                            break;
                    }
                } catch { }
            }
        },
        []
    );

    /** HTTP fallback sync — used for initial data load and recovery. */
    const sync = useCallback(async () => {
        try {
            const data = await companionAPI.sync();
            await cacheData(data);
            const power = await determinePowerState(true);

            setState((prev) => {
                const justReconnected = !prev.isOnline && wasOfflineRef.current;

                if (justReconnected && prev.offlineActions.length > 0) {
                    replayOfflineActions(prev.offlineActions);
                }

                wasOfflineRef.current = false;

                return {
                    ...prev,
                    isOnline: true,
                    powerState: justReconnected ? "reconnected" : power,
                    companionData: data,
                    offlineActions: justReconnected ? [] : prev.offlineActions,
                    isLoading: false,
                    lastSeen: Date.now(),
                    awayDuration: null,
                };
            });

            if (wasOfflineRef.current === false) {
                setState((prev) => {
                    if (prev.powerState === "reconnected") {
                        flashReconnected();
                    }
                    return prev;
                });
            }

            // Sync phone sensor data (contacts, calendar, device) to PC brain
            try {
                const { syncPhoneContext } = await import("../PhoneContextSync");
                syncPhoneContext(); // Fire-and-forget, rate-limited internally
            } catch { }

            return true;
        } catch {
            const cached = await loadCache();
            wasOfflineRef.current = true;
            const lastSeen = state.lastSeen;
            const awayDuration = lastSeen ? formatDuration(Date.now() - lastSeen) : null;
            setState((prev) => ({
                ...prev,
                isOnline: false,
                powerState: "offline",
                companionData: cached || prev.companionData,
                isLoading: false,
                awayDuration,
            }));
            return false;
        }
    }, [cacheData, loadCache, replayOfflineActions, determinePowerState, flashReconnected]);

    /** Queue an action for when we're back online. */
    const queueAction = useCallback((action: OfflineAction) => {
        setState((prev) => ({
            ...prev,
            offlineActions: [...prev.offlineActions, action],
        }));
    }, []);

    /** Update local companion state optimistically. */
    const updateCompanionLocal = useCallback(
        (updater: (prev: CompanionState) => CompanionState) => {
            setState((prev) => {
                if (!prev.companionData) return prev;
                const updated = {
                    ...prev.companionData,
                    companion: updater(prev.companionData.companion),
                };
                cacheData(updated);
                return { ...prev, companionData: updated };
            });
        },
        [cacheData]
    );

    // ---------------------------------------------------------------------------
    // WebSocket integration
    // ---------------------------------------------------------------------------

    useEffect(() => {
        const socket = getSocket();

        // Listen for connection phase changes
        const unsubPhase = socket.onPhaseChange((phase) => {
            setState((prev) => {
                const isOnline = phase === "connected";
                const powerState: PowerState =
                    phase === "connected"
                        ? prev.powerState === "offline" || prev.powerState === "reconnected"
                            ? "reconnected"
                            : "home"
                        : phase === "reconnecting"
                            ? prev.powerState // keep current while retrying
                            : "offline";

                return {
                    ...prev,
                    connectionPhase: phase,
                    isOnline,
                    powerState,
                };
            });

            // On reconnect: replay offline actions and flash
            if (phase === "connected") {
                setState((prev) => {
                    if (prev.offlineActions.length > 0) {
                        replayOfflineActions(prev.offlineActions);
                    }
                    return {
                        ...prev,
                        offlineActions: [],
                        lastSeen: Date.now(),
                        awayDuration: null,
                        isLoading: false,
                    };
                });

                if (wasOfflineRef.current) {
                    wasOfflineRef.current = false;
                    flashReconnected();
                }
            } else if (phase === "offline" || phase === "reconnecting") {
                wasOfflineRef.current = true;
            }
        });

        // Listen for real-time events from the desktop
        const unsubEvent = socket.onEvent((event: FiresideEvent) => {
            switch (event.type) {
                case "companion_state_update":
                    // Real-time companion state push — no polling needed!
                    setState((prev) => {
                        if (!prev.companionData) return prev;
                        const updated = {
                            ...prev.companionData,
                            companion: {
                                ...prev.companionData.companion,
                                ...event.data.companion,
                            },
                            mood_prefix: event.data.mood_prefix || prev.companionData.mood_prefix,
                        };
                        cacheData(updated);
                        return { ...prev, companionData: updated, lastSeen: Date.now() };
                    });
                    break;

                case "task_completed":
                    // A task in the queue finished — update pending tasks
                    setState((prev) => {
                        if (!prev.companionData) return prev;
                        const pending = prev.companionData.pending_tasks || [];
                        return {
                            ...prev,
                            companionData: {
                                ...prev.companionData,
                                pending_tasks: [...pending, event.data],
                            },
                        };
                    });
                    break;

                case "notification":
                    // Desktop pushed a notification — could trigger a local notification
                    break;

                case "chat_message":
                    // Bidirectional chat sync — message from desktop appears on mobile
                    // This is handled by chat.tsx listening to the same socket
                    break;

                case "full_sync":
                    // Initial sync payload sent on WebSocket connect
                    if (event.data) {
                        const syncData = event.data as MobileSyncResponse;
                        cacheData(syncData);
                        setState((prev) => ({
                            ...prev,
                            companionData: syncData,
                            isOnline: true,
                            isLoading: false,
                            lastSeen: Date.now(),
                        }));
                    }
                    break;
            }
        });

        // Boot: check if configured and connect
        (async () => {
            const host = await getHost();
            setState((prev) => ({ ...prev, isConfigured: !!host }));

            if (host) {
                // Try WebSocket first
                socket.connect();

                // Also do an HTTP sync for initial data (WS might not send full_sync)
                await sync();
            } else {
                setState((prev) => ({ ...prev, isLoading: false }));
            }
        })();

        return () => {
            unsubPhase();
            unsubEvent();
            if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
            // Don't destroy the socket on unmount — it's a singleton that persists
        };
    }, []); // Empty deps — socket is a singleton

    return {
        ...state,
        sync,
        queueAction,
        updateCompanionLocal,
    };
}

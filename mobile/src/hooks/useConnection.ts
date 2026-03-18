/**
 * useConnection — Manages connectivity & power state.
 *
 * Power States:
 *   🔥 home        — connected via LAN to PC
 *   ⚡ connected   — connected via Tailscale bridge
 *   🕯️ offline     — no connection, running on pocket power
 *   🔥 reconnected — just came back online (briefly, then → home/connected)
 *
 * - On mount: attempts /mobile/sync. On fail, loads cached state.
 * - Polls every 30s to detect connection changes.
 * - Queues offline actions and replays on reconnect.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { companionAPI, testConnection, getHost, getConnectionPref } from "../api";
import type { MobileSyncResponse, CompanionState } from "../types";

const CACHE_KEY = "valhalla_cache";
const LAST_SEEN_KEY = "valhalla_last_seen";
const POLL_INTERVAL = 30_000;
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
        companionData: null,
        offlineActions: [],
        isLoading: true,
        awayDuration: null,
        lastSeen: null,
    });

    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
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
                            if (action.payload) await companionAPI.chat(action.payload);
                            break;
                    }
                } catch { }
            }
        },
        []
    );

    /** Attempt to sync with the backend. */
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
                    offlineActions: [],
                    isLoading: false,
                    lastSeen: Date.now(),
                    awayDuration: null,
                };
            });

            // If reconnected, flash then settle
            if (wasOfflineRef.current === false) {
                // Check if we need to flash (state was just set to reconnected above)
                setState((prev) => {
                    if (prev.powerState === "reconnected") {
                        flashReconnected();
                    }
                    return prev;
                });
            }

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

    /** Boot: check if configured and sync. */
    useEffect(() => {
        (async () => {
            const host = await getHost();
            setState((prev) => ({ ...prev, isConfigured: !!host }));
            if (host) {
                await sync();
            } else {
                setState((prev) => ({ ...prev, isLoading: false }));
            }
        })();
    }, [sync]);

    /** Background polling — detects reconnection. */
    useEffect(() => {
        pollRef.current = setInterval(async () => {
            const host = await getHost();
            if (!host) return;
            const online = await testConnection();
            if (online) {
                setState((prev) => {
                    if (!prev.isOnline) sync();
                    return prev;
                });
            } else {
                wasOfflineRef.current = true;
                setState((prev) => ({ ...prev, isOnline: false, powerState: "offline" }));
            }
        }, POLL_INTERVAL);

        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
            if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        };
    }, [sync]);

    return {
        ...state,
        sync,
        queueAction,
        updateCompanionLocal,
    };
}

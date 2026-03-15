/**
 * useConnection — Manages connectivity to the Valhalla backend.
 *
 * - On mount: attempts /mobile/sync. On fail, loads cached state from AsyncStorage.
 * - Polls every 30s to detect connection changes.
 * - Exposes `isOnline`, `companionData`, `sync()` for manual refresh.
 * - Queues offline actions and replays them when connection resumes.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { companionAPI, testConnection, getHost } from "../api";
import type { MobileSyncResponse, CompanionState } from "../types";

const CACHE_KEY = "valhalla_cache";
const POLL_INTERVAL = 30_000; // 30 seconds

export interface OfflineAction {
    type: "feed" | "walk" | "chat";
    payload?: string;
    timestamp: number;
}

interface ConnectionState {
    isOnline: boolean;
    isConfigured: boolean;
    companionData: MobileSyncResponse | null;
    offlineActions: OfflineAction[];
    isLoading: boolean;
}

export function useConnection() {
    const [state, setState] = useState<ConnectionState>({
        isOnline: false,
        isConfigured: false,
        companionData: null,
        offlineActions: [],
        isLoading: true,
    });

    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    /** Save companion data to AsyncStorage for offline access. */
    const cacheData = useCallback(async (data: MobileSyncResponse) => {
        try {
            await AsyncStorage.setItem(CACHE_KEY, JSON.stringify(data));
        } catch {
            // silently fail
        }
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
                } catch {
                    // If replay fails, drop the action — stale actions aren't worth retrying
                }
            }
        },
        []
    );

    /** Attempt to sync with the backend. */
    const sync = useCallback(async () => {
        try {
            const data = await companionAPI.sync();
            await cacheData(data);

            setState((prev) => {
                // If we were offline and had queued actions, replay them
                if (!prev.isOnline && prev.offlineActions.length > 0) {
                    replayOfflineActions(prev.offlineActions);
                }
                return {
                    ...prev,
                    isOnline: true,
                    companionData: data,
                    offlineActions: [],
                    isLoading: false,
                };
            });
            return true;
        } catch {
            // Load cached data if sync fails
            const cached = await loadCache();
            setState((prev) => ({
                ...prev,
                isOnline: false,
                companionData: cached || prev.companionData,
                isLoading: false,
            }));
            return false;
        }
    }, [cacheData, loadCache, replayOfflineActions]);

    /** Queue an action for when we're back online. */
    const queueAction = useCallback((action: OfflineAction) => {
        setState((prev) => ({
            ...prev,
            offlineActions: [...prev.offlineActions, action],
        }));
    }, []);

    /** Update local companion state optimistically (for offline interactions). */
    const updateCompanionLocal = useCallback(
        (updater: (prev: CompanionState) => CompanionState) => {
            setState((prev) => {
                if (!prev.companionData) return prev;
                const updated = {
                    ...prev.companionData,
                    companion: updater(prev.companionData.companion),
                };
                // Cache the optimistic update
                cacheData(updated);
                return { ...prev, companionData: updated };
            });
        },
        [cacheData]
    );

    /** Check if host is configured. */
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

    /** Background polling — detects when connection resumes. */
    useEffect(() => {
        pollRef.current = setInterval(async () => {
            const host = await getHost();
            if (!host) return;
            const online = await testConnection();
            if (online) {
                setState((prev) => {
                    if (!prev.isOnline) {
                        // Connection just resumed — sync
                        sync();
                    }
                    return prev;
                });
            } else {
                setState((prev) => ({ ...prev, isOnline: false }));
            }
        }, POLL_INTERVAL);

        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [sync]);

    return {
        ...state,
        sync,
        queueAction,
        updateCompanionLocal,
    };
}

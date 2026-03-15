/**
 * Valhalla Companion API client.
 *
 * Reads the home PC IP from AsyncStorage ('valhalla_host').
 * Falls back to offline mode when the backend is unreachable.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import type {
    MobileSyncResponse,
    StatusResponse,
    FeedResponse,
    WalkResponse,
    ChatResponse,
    QueueResponse,
} from "./types";

const STORAGE_KEY = "valhalla_host";
const TIMEOUT_MS = 8000;

/** Retrieve the stored host address (e.g. '192.168.1.100:8765'). */
export async function getHost(): Promise<string | null> {
    return AsyncStorage.getItem(STORAGE_KEY);
}

/** Persist the host address. */
export async function setHost(host: string): Promise<void> {
    await AsyncStorage.setItem(STORAGE_KEY, host.replace(/\/+$/, ""));
}

/** Build the full URL for a given path. */
async function baseUrl(): Promise<string> {
    const host = await getHost();
    if (!host) throw new Error("No host configured");
    const h = host.startsWith("http") ? host : `http://${host}`;
    return h.replace(/\/+$/, "");
}

/** Fetch helper with timeout. */
async function apiFetch<T>(
    path: string,
    opts: RequestInit = {}
): Promise<T> {
    const base = await baseUrl();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
        const res = await fetch(`${base}${path}`, {
            ...opts,
            signal: controller.signal,
            headers: {
                "Content-Type": "application/json",
                ...(opts.headers || {}),
            },
        });
        if (!res.ok) {
            throw new Error(`API ${res.status}: ${res.statusText}`);
        }
        return (await res.json()) as T;
    } finally {
        clearTimeout(timer);
    }
}

// ──────────────────────────────────────────────
// Public API methods
// ──────────────────────────────────────────────

export const companionAPI = {
    /** Full sync — call on app launch to get everything in one roundtrip. */
    sync: () => apiFetch<MobileSyncResponse>("/api/v1/companion/mobile/sync", { method: "POST" }),

    /** Health check — confirms we're talking to a Valhalla backend. */
    status: () => apiFetch<StatusResponse>("/api/v1/status"),

    /** Feed the companion. */
    feed: (food: string) =>
        apiFetch<FeedResponse>("/api/v1/companion/feed", {
            method: "POST",
            body: JSON.stringify({ food }),
        }),

    /** Take the companion for a walk. */
    walk: () => apiFetch<WalkResponse>("/api/v1/companion/walk", { method: "POST" }),

    /** Send a chat message. */
    chat: (message: string) =>
        apiFetch<ChatResponse>("/api/v1/chat", {
            method: "POST",
            body: JSON.stringify({ message }),
        }),

    /** Get the task queue. */
    queue: (status?: string) =>
        apiFetch<QueueResponse>(
            `/api/v1/companion/queue${status ? `?status=${status}` : ""}`
        ),

    /** Get companion status. */
    companionStatus: () => apiFetch<{ ok: boolean; companion: Record<string, unknown> }>("/api/v1/companion/status"),

    /** Adopt a new companion (Sprint 2). */
    adopt: (name: string, species: string) =>
        apiFetch<{ ok: boolean }>("/api/v1/companion/adopt", {
            method: "POST",
            body: JSON.stringify({ name, species }),
        }),

    /** Create a new task from mobile (Sprint 2). */
    queueTask: (taskType: string, payload?: Record<string, unknown>) =>
        apiFetch<{ ok: boolean; task: Record<string, unknown> }>("/api/v1/companion/queue", {
            method: "POST",
            body: JSON.stringify({ task_type: taskType, payload }),
        }),

    /** Register push notification token (Sprint 3). */
    registerPush: (token: string) =>
        apiFetch<{ ok: boolean }>("/api/v1/companion/mobile/register-push", {
            method: "POST",
            body: JSON.stringify({ token }),
        }),

    /** Unregister push notification token (Sprint 3). */
    unregisterPush: (token: string) =>
        apiFetch<{ ok: boolean }>("/api/v1/companion/mobile/unregister-push", {
            method: "POST",
            body: JSON.stringify({ token }),
        }),
};

/** Quick connectivity check — returns true if the backend responds. */
export async function testConnection(): Promise<boolean> {
    try {
        const data = await companionAPI.status();
        return data.mobile_ready === true;
    } catch {
        return false;
    }
}

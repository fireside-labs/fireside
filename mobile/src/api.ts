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

    /** Check message through guardian before sending (Sprint 4). */
    guardian: (message: string, timeOfDay?: string) =>
        apiFetch<{ safe: boolean; reason?: string; suggestedRewrite?: string; sentiment?: string }>(
            "/api/v1/companion/guardian",
            { method: "POST", body: JSON.stringify({ message, time_of_day: timeOfDay }) }
        ),

    /** Get daily gift (Sprint 4). */
    dailyGift: () =>
        apiFetch<{ available: boolean; gift?: { text: string; type: string; emoji: string; item?: string; happinessBoost?: number } }>(
            "/api/v1/companion/daily-gift"
        ),

    /** Translate text via NLLB-200 (Sprint 5). */
    translate: (text: string, sourceLang: string, targetLang: string) =>
        apiFetch<{ translation: string; confidence?: number; source_lang?: string }>(
            "/api/v1/companion/translate",
            { method: "POST", body: JSON.stringify({ text, source: sourceLang, target: targetLang }) }
        ),

    /** Teach companion a fact (Sprint 5). */
    teach: (fact: string) =>
        apiFetch<{ ok: boolean; confirmation?: string; fact_count?: number }>(
            "/api/v1/companion/teach",
            { method: "POST", body: JSON.stringify({ fact }) }
        ),

    /** Proactive guardian check-in (Sprint 5). */
    guardianCheckIn: () =>
        apiFetch<{ proactive_warning: boolean; reason?: string }>(
            "/api/v1/companion/guardian/check-in"
        ),

    /** Transcribe audio via Whisper (Sprint 6). */
    voiceTranscribe: (formData: FormData) =>
        apiFetch<{ text: string; language?: string; confidence?: number }>(
            "/api/v1/voice/transcribe",
            { method: "POST", body: formData, headers: {} }
        ),

    /** Speak text via Kokoro TTS (Sprint 6). */
    voiceSpeak: (text: string, voice?: string) =>
        apiFetch<{ audio_url: string; duration?: number }>(
            "/api/v1/voice/speak",
            { method: "POST", body: JSON.stringify({ text, voice }) }
        ),

    /** Search marketplace (Sprint 6). */
    marketplaceSearch: (query: string, category?: string) =>
        apiFetch<{ items: Array<Record<string, any>> }>(
            `/api/v1/marketplace/search?q=${encodeURIComponent(query)}${category ? `&category=${category}` : ""}`
        ),

    /** Install marketplace item (Sprint 6). */
    marketplaceInstall: (itemId: string) =>
        apiFetch<{ ok: boolean }>(
            "/api/v1/marketplace/install",
            { method: "POST", body: JSON.stringify({ item_id: itemId }) }
        ),

    /** Summarize a URL via browse plugin (Sprint 6). */
    browseSummarize: (url: string) =>
        apiFetch<{ title?: string; summary?: string; keyPoints?: string[] }>(
            "/api/v1/browse/summarize",
            { method: "POST", body: JSON.stringify({ url }) }
        ),
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

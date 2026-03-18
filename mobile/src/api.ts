/**
 * Valhalla Companion API client.
 *
 * Reads the home PC IP from AsyncStorage ('valhalla_host').
 * Supports Anywhere Bridge (Tailscale) — routes
 * through tailscale_ip when connection preference is 'bridge'.
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
const BRIDGE_IP_KEY = "valhalla_tailscale_ip";
const CONN_PREF_KEY = "valhalla_conn_pref"; // 'local' | 'bridge'
const TIMEOUT_MS = 8000;

/** Retrieve the stored host address (e.g. '192.168.1.100:8765'). */
export async function getHost(): Promise<string | null> {
    return AsyncStorage.getItem(STORAGE_KEY);
}

/** Persist the host address. */
export async function setHost(host: string): Promise<void> {
    await AsyncStorage.setItem(STORAGE_KEY, host.replace(/\/+$/, ""));
}

/** Store the Tailscale VPN IP. */
export async function setTailscaleIP(ip: string): Promise<void> {
    await AsyncStorage.setItem(BRIDGE_IP_KEY, ip);
}

/** Retrieve the stored Tailscale IP. */
export async function getTailscaleIP(): Promise<string | null> {
    return AsyncStorage.getItem(BRIDGE_IP_KEY);
}

/** Set connection preference: 'local' or 'bridge'. */
export async function setConnectionPref(pref: "local" | "bridge"): Promise<void> {
    await AsyncStorage.setItem(CONN_PREF_KEY, pref);
}

/** Get connection preference. */
export async function getConnectionPref(): Promise<"local" | "bridge"> {
    const p = await AsyncStorage.getItem(CONN_PREF_KEY);
    return (p === "bridge") ? "bridge" : "local";
}

/** Discovered Fireside instance on the local network. */
export interface DiscoveredHost {
    ip: string;
    port: number;
    nodeName: string;
}

/**
 * Scan the local network for a running Fireside backend.
 * Probes common subnet ranges hitting /health endpoint.
 * Returns the first responding host, or null if none found.
 */
export async function discoverFireside(): Promise<DiscoveredHost | null> {
    const PORT = 9099;
    const PROBE_TIMEOUT = 1500; // ms per probe

    // Try to guess the local subnet from a well-known gateway pattern
    const subnets = ["192.168.1", "192.168.0", "192.168.86", "10.0.0", "10.0.1"];
    const candidates: string[] = [];

    for (const subnet of subnets) {
        for (let i = 1; i <= 254; i++) {
            candidates.push(`${subnet}.${i}`);
        }
    }

    // Probe in parallel batches of 50
    const BATCH = 50;
    for (let offset = 0; offset < candidates.length; offset += BATCH) {
        const batch = candidates.slice(offset, offset + BATCH);
        const results = await Promise.allSettled(
            batch.map(async (ip) => {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT);
                try {
                    const res = await fetch(`http://${ip}:${PORT}/health`, {
                        signal: controller.signal,
                    });
                    clearTimeout(timer);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.status === "ok" && data.node) {
                            return { ip: `${ip}:${PORT}`, port: PORT, nodeName: data.node } as DiscoveredHost;
                        }
                    }
                } catch {
                    clearTimeout(timer);
                }
                throw new Error("not found");
            })
        );

        for (const r of results) {
            if (r.status === "fulfilled" && r.value) {
                return r.value;
            }
        }
    }

    return null;
}

/**
 * Get the active host to use for API calls.
 * If preference is 'bridge' and a tailscale_ip exists, use it.
 * Otherwise fall back to local host.
 */
export async function getActiveHost(): Promise<string | null> {
    const pref = await getConnectionPref();
    if (pref === "bridge") {
        const tsIP = await getTailscaleIP();
        if (tsIP) return tsIP;
    }
    return getHost();
}

/** Build the full URL for a given path. */
async function baseUrl(): Promise<string> {
    const host = await getActiveHost();
    if (!host) throw new Error("No host configured");
    // Ensure port is included
    const hostWithPort = host.includes(":") ? host : `${host}:9099`;
    const h = hostWithPort.startsWith("http") ? hostWithPort : `http://${hostWithPort}`;
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

    /** Adopt a new companion. */
    adopt: (name: string, species: string) =>
        apiFetch<{ ok: boolean }>("/api/v1/companion/adopt", {
            method: "POST",
            body: JSON.stringify({ name, species }),
        }),

    /** Create a new task from mobile. */
    queueTask: (taskType: string, payload?: Record<string, unknown>) =>
        apiFetch<{ ok: boolean; task: Record<string, unknown> }>("/api/v1/companion/queue", {
            method: "POST",
            body: JSON.stringify({ task_type: taskType, payload }),
        }),

    /** Register push notification token. */
    registerPush: (token: string) =>
        apiFetch<{ ok: boolean }>("/api/v1/companion/mobile/register-push", {
            method: "POST",
            body: JSON.stringify({ token }),
        }),

    /** Unregister push notification token. */
    unregisterPush: (token: string) =>
        apiFetch<{ ok: boolean }>("/api/v1/companion/mobile/unregister-push", {
            method: "POST",
            body: JSON.stringify({ token }),
        }),

    /** Check message through guardian before sending. */
    guardian: (message: string, timeOfDay?: string) =>
        apiFetch<{ safe: boolean; reason?: string; suggestedRewrite?: string; sentiment?: string }>(
            "/api/v1/companion/guardian",
            { method: "POST", body: JSON.stringify({ message, time_of_day: timeOfDay }) }
        ),

    /** Get daily gift. */
    dailyGift: () =>
        apiFetch<{ available: boolean; gift?: { text: string; type: string; emoji: string; item?: string; happinessBoost?: number } }>(
            "/api/v1/companion/daily-gift"
        ),

    /** Translate text via NLLB-200 (200 languages, offline). */
    translate: (text: string, sourceLang: string, targetLang: string) =>
        apiFetch<{ ok: boolean; translated: string; source_lang?: string; target_lang?: string; confidence?: number; note?: string }>(
            "/api/v1/companion/translate",
            { method: "POST", body: JSON.stringify({ text, source_lang: sourceLang, target_lang: targetLang }) }
        ),

    /** Teach companion a fact. */
    teach: (fact: string) =>
        apiFetch<{ ok: boolean; confirmation?: string; fact_count?: number }>(
            "/api/v1/companion/teach",
            { method: "POST", body: JSON.stringify({ fact }) }
        ),

    /** Proactive guardian check-in. */
    guardianCheckIn: () =>
        apiFetch<{ proactive_warning: boolean; reason?: string }>(
            "/api/v1/companion/guardian/check-in"
        ),

    /** Transcribe audio via Whisper. */
    voiceTranscribe: (formData: FormData) =>
        apiFetch<{ text: string; language?: string; confidence?: number }>(
            "/api/v1/voice/transcribe",
            { method: "POST", body: formData, headers: {} }
        ),

    /** Speak text via Kokoro TTS. */
    voiceSpeak: (text: string, voice?: string) =>
        apiFetch<{ audio_url: string; duration?: number }>(
            "/api/v1/voice/speak",
            { method: "POST", body: JSON.stringify({ text, voice }) }
        ),

    /** Summarize a URL via browse plugin. */
    browseSummarize: (url: string) =>
        apiFetch<{ title?: string; summary?: string; keyPoints?: string[] }>(
            "/api/v1/browse/summarize",
            { method: "POST", body: JSON.stringify({ url }) }
        ),

    /** Check for new achievements. */
    achievementsCheck: () =>
        apiFetch<{ new_achievements?: Array<{ id: string; name: string; description: string; emoji: string }>; all_achievements?: Array<Record<string, any>> }>(
            "/api/v1/companion/achievements/check",
            { method: "POST" }
        ),

    /** Save chat history to backend. */
    chatHistory: (messages: Array<{ role: string; content: string; timestamp?: string }>) =>
        apiFetch<{ ok: boolean; saved: number }>(
            "/api/v1/chat/history",
            { method: "POST", body: JSON.stringify({ messages }) }
        ),

    /** Get working memory health. */
    memoryStatus: () =>
        apiFetch<{ ok: boolean; entries?: number; backend?: string }>(
            "/api/v1/working-memory/status"
        ),

    /** Pair mobile app with backend via token. */
    pair: (token: string) =>
        apiFetch<{ ok: boolean; paired: boolean }>(
            "/mobile/pair",
            { method: "POST", body: JSON.stringify({ token }) }
        ),
    /** Join hosted waitlist. */
    waitlist: (email: string) =>
        apiFetch<{ ok: boolean; message: string }>(
            "/api/v1/waitlist",
            { method: "POST", body: JSON.stringify({ email }) }
        ),

    /** Cross-context search. */
    query: (query: string) =>
        apiFetch<{ results: Array<{ source: string; content: string; relevance: number; date?: string }>; total: number }>(
            "/api/v1/companion/query",
            { method: "POST", body: JSON.stringify({ query }) }
        ),
    /** Agent profile. */
    agentProfile: () =>
        apiFetch<{ name: string; style: string; uptime?: string; companion?: { name: string; species: string } }>(
            "/api/v1/agent/profile"
        ),

    /** Network status — local + Tailscale IPs. */
    networkStatus: () =>
        apiFetch<{ local_ip: string; tailscale_ip: string | null; bridge_active: boolean }>(
            "/api/v1/network/status"
        ),

    /** List available models (verified: GET /api/v1/models). */
    brainModels: () =>
        apiFetch<{ models: Array<{ id: string; name: string; size: string; quantization: string; loaded: boolean; vram_required?: string }>; default?: string }>(
            "/api/v1/models"
        ),

    /** Brain health check (verified: GET /api/v1/brains/status). */
    brainActive: () =>
        apiFetch<{ model: string; backend: string; context_length?: number; gpu_layers?: number; ok?: boolean }>(
            "/api/v1/brains/status"
        ),

    /** Switch the active model on PC. */
    brainSwitch: (modelId: string) =>
        apiFetch<{ ok: boolean; model: string; message?: string }>(
            "/api/v1/brain/switch",
            { method: "POST", body: JSON.stringify({ model_id: modelId }) }
        ),

    /** Get companion skills (RPG toggle cards). */
    skills: () =>
        apiFetch<{ skills: Array<{ id: string; name: string; description: string; emoji: string; enabled: boolean; level: number; xp_cost?: number }> }>(
            "/api/v1/companion/skills"
        ),

    /** Toggle a skill on/off. */
    skillToggle: (skillId: string, enabled: boolean) =>
        apiFetch<{ ok: boolean; skill: { id: string; enabled: boolean } }>(
            "/api/v1/companion/skills/toggle",
            { method: "POST", body: JSON.stringify({ skill_id: skillId, enabled }) }
        ),

    /** Get personality traits (soul file). */
    personality: () =>
        apiFetch<{ traits: Record<string, string>; voice_style?: string; greeting?: string; bio?: string }>(
            "/api/v1/companion/personality"
        ),

    /** Update personality trait. */
    personalityUpdate: (traits: Record<string, string>) =>
        apiFetch<{ ok: boolean; traits: Record<string, string> }>(
            "/api/v1/companion/personality",
            { method: "POST", body: JSON.stringify({ traits }) }
        ),

    /** Get companion pet state (mood/energy/hunger). */
    petState: () =>
        apiFetch<{ mood: number; energy: number; hunger: number; last_interaction?: string }>(
            "/api/v1/companion/pet-state"
        ),

    /** Interact with companion (feed/walk/play). */
    interact: (action: "feed" | "walk" | "play", item?: string) =>
        apiFetch<{ ok: boolean; state: { mood: number; energy: number; hunger: number }; message: string }>(
            "/api/v1/companion/interact",
            { method: "POST", body: JSON.stringify({ action, item }) }
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

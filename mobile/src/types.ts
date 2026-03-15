// Types for the Valhalla Companion mobile app.
// Mirrors patterns from dashboard/components/CompanionSim.tsx, CompanionChat.tsx, etc.

export type PetSpecies = "cat" | "dog" | "penguin" | "fox" | "owl" | "dragon";

export interface CompanionState {
    name: string;
    species: PetSpecies;
    happiness: number; // 0-100
    xp: number;
    level: number;
    streak: number;
    hunger?: number;
    mood?: number;
    energy?: number;
}

export interface WalkEvent {
    text: string;
    happinessBoost: number;
    xpGain: number;
    emoji: string;
}

export interface InventoryItem {
    item: string;
    count: number;
    emoji: string;
    equipped?: boolean;
    consumable?: boolean;
    description?: string;
    rare?: boolean;
}

export interface QueuedTask {
    id: string;
    text: string;
    status: "pending" | "sent" | "completed" | "failed";
    timestamp: string;
    result?: string;
}

export interface Message {
    role: "user" | "pet";
    content: string;
}

export interface MobileSyncResponse {
    ok: boolean;
    companion: CompanionState;
    personality: Record<string, unknown>;
    mood_prefix: string;
    pending_tasks: QueuedTask[];
    synced_at: number;
    inventory?: InventoryItem[];
}

export interface StatusResponse {
    node: string;
    role: string;
    port: number;
    model: string;
    uptime_seconds: number;
    uptime_human: string;
    plugins_loaded: number;
    status: string;
    mobile_ready: boolean;
    gpu: {
        name: string | null;
        vram_total_gb: number | null;
        vram_used_gb: number | null;
    };
}

export interface FeedResponse {
    ok: boolean;
    companion: CompanionState;
    message: string;
}

export interface WalkResponse {
    ok: boolean;
    companion: CompanionState;
    event: WalkEvent;
}

export interface ChatResponse {
    ok: boolean;
    reply: string;
    mood_prefix?: string;
}

export interface QueueResponse {
    tasks: QueuedTask[];
    stats?: { total: number };
}

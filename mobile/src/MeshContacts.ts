/**
 * 🌐 MeshContacts — Cross-companion mesh contact book.
 *
 * Sprint 5: "Net Navis" — enables companions on the same Valhalla Mesh
 * network to discover and communicate with each other.
 *
 * Each companion registers on the mesh with its owner's consent.
 * This module provides:
 *   - Contact discovery via mesh network
 *   - Cross-companion query routing
 *   - Privacy gates for access control
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { companionAPI } from "./api";

export interface MeshContact {
    id: string;
    ownerName: string;
    companionName: string;
    species: string;
    emoji: string;
    lastSeen: string;
    online: boolean;
    /** What this contact is allowed to ask your companion. */
    privacyLevel: PrivacyLevel;
}

export type PrivacyLevel = "full" | "limited" | "blocked";

export interface CrossQuery {
    id: string;
    fromContact: string;
    fromCompanion: string;
    query: string;
    timestamp: string;
    status: "pending" | "approved" | "denied" | "answered";
    answer?: string;
}

const MESH_CONTACTS_KEY = "fireside_mesh_contacts";
const PRIVACY_PREFS_KEY = "fireside_privacy_prefs";
const CROSS_QUERIES_KEY = "fireside_cross_queries";

/**
 * Discover companions on the mesh network.
 */
export async function discoverMeshPeers(): Promise<MeshContact[]> {
    try {
        const res = await companionAPI.query("mesh:discover");
        // Map results to MeshContact format
        return (res.results || []).map((r: any) => ({
            id: r.source || String(Math.random()),
            ownerName: r.content?.split("@")[0] || "Unknown",
            companionName: r.content?.split(":")[0] || "Unknown",
            species: "fox",
            emoji: "🦊",
            lastSeen: r.date || new Date().toISOString(),
            online: r.relevance > 0.5,
            privacyLevel: "limited" as PrivacyLevel,
        }));
    } catch {
        // Return cached contacts
        return getCachedContacts();
    }
}

/**
 * Get cached mesh contacts.
 */
export async function getCachedContacts(): Promise<MeshContact[]> {
    const raw = await AsyncStorage.getItem(MESH_CONTACTS_KEY);
    if (!raw) return [];
    try {
        return JSON.parse(raw) as MeshContact[];
    } catch {
        return [];
    }
}

/**
 * Save contacts to local cache.
 */
export async function cacheContacts(contacts: MeshContact[]): Promise<void> {
    await AsyncStorage.setItem(MESH_CONTACTS_KEY, JSON.stringify(contacts));
}

/**
 * Send a cross-companion query.
 * Requires the target companion's owner to approve (privacy gate).
 */
export async function sendCrossQuery(
    targetId: string,
    query: string
): Promise<{ queued: boolean; message: string }> {
    try {
        const res = await companionAPI.queueTask("cross_query", {
            target_id: targetId,
            query,
        });
        return { queued: true, message: "Query sent! Waiting for approval." };
    } catch {
        return { queued: false, message: "Couldn't reach the mesh. Try again later." };
    }
}

/**
 * Get pending cross-queries for approval.
 */
export async function getPendingQueries(): Promise<CrossQuery[]> {
    const raw = await AsyncStorage.getItem(CROSS_QUERIES_KEY);
    if (!raw) return [];
    try {
        return (JSON.parse(raw) as CrossQuery[]).filter(
            (q) => q.status === "pending"
        );
    } catch {
        return [];
    }
}

/**
 * Approve or deny an incoming cross-query.
 */
export async function respondToQuery(
    queryId: string,
    approved: boolean
): Promise<void> {
    try {
        await companionAPI.queueTask("cross_query_response", {
            query_id: queryId,
            approved,
        });
    } catch { }

    // Update local state
    const raw = await AsyncStorage.getItem(CROSS_QUERIES_KEY);
    if (raw) {
        const queries = JSON.parse(raw) as CrossQuery[];
        const updated = queries.map((q) =>
            q.id === queryId
                ? { ...q, status: approved ? ("approved" as const) : ("denied" as const) }
                : q
        );
        await AsyncStorage.setItem(CROSS_QUERIES_KEY, JSON.stringify(updated));
    }
}

/**
 * Update privacy level for a mesh contact.
 */
export async function setPrivacyLevel(
    contactId: string,
    level: PrivacyLevel
): Promise<void> {
    const raw = await AsyncStorage.getItem(PRIVACY_PREFS_KEY);
    const prefs: Record<string, PrivacyLevel> = raw ? JSON.parse(raw) : {};
    prefs[contactId] = level;
    await AsyncStorage.setItem(PRIVACY_PREFS_KEY, JSON.stringify(prefs));
}

/**
 * Get privacy level for a mesh contact.
 */
export async function getPrivacyLevel(contactId: string): Promise<PrivacyLevel> {
    const raw = await AsyncStorage.getItem(PRIVACY_PREFS_KEY);
    if (!raw) return "limited";
    const prefs: Record<string, PrivacyLevel> = JSON.parse(raw);
    return prefs[contactId] || "limited";
}

/**
 * Privacy level descriptions for the UI.
 */
export const PRIVACY_DESCRIPTIONS: Record<PrivacyLevel, { emoji: string; title: string; desc: string }> = {
    full: {
        emoji: "🟢",
        title: "Full Access",
        desc: "This companion can ask your companion anything. Use for close friends only.",
    },
    limited: {
        emoji: "🟡",
        title: "Limited Access",
        desc: "Basic queries only. Your companion will ask before sharing sensitive info.",
    },
    blocked: {
        emoji: "🔴",
        title: "Blocked",
        desc: "This companion cannot communicate with yours.",
    },
};

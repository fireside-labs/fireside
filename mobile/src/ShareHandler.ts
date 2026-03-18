/**
 * 📋 ShareHandler — iOS Share Sheet integration.
 *
 * When users share text, URLs, or images to Fireside via the iOS share sheet,
 * this module handles the incoming data and routes it to the companion's queue.
 *
 * Usage patterns:
 *   - Share a URL → companion summarizes it
 *   - Share text → companion remembers it as context
 *   - Share a photo → companion processes it (OCR, description)
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { companionAPI } from "./api";

export type ShareType = "text" | "url" | "image";

export interface SharedItem {
    type: ShareType;
    content: string; // text/URL string, or base64 for images
    title?: string;
    timestamp: string;
}

const PENDING_SHARES_KEY = "fireside_pending_shares";

/**
 * Handle an incoming share from the iOS share sheet.
 * Queues it for processing by the companion.
 */
export async function handleIncomingShare(item: SharedItem): Promise<void> {
    // Try to send immediately if online
    try {
        if (item.type === "url") {
            await companionAPI.browseSummarize(item.content);
        } else {
            await companionAPI.queueTask("shared_content", {
                type: item.type,
                content: item.content,
                title: item.title,
            });
        }
    } catch {
        // Offline — save for later
        const pending = await getPendingShares();
        pending.push(item);
        await AsyncStorage.setItem(PENDING_SHARES_KEY, JSON.stringify(pending));
    }
}

/**
 * Get all pending shares that haven't been processed yet.
 */
export async function getPendingShares(): Promise<SharedItem[]> {
    const raw = await AsyncStorage.getItem(PENDING_SHARES_KEY);
    if (!raw) return [];
    try {
        return JSON.parse(raw) as SharedItem[];
    } catch {
        return [];
    }
}

/**
 * Process all pending shares (called on reconnection).
 */
export async function processPendingShares(): Promise<number> {
    const pending = await getPendingShares();
    if (pending.length === 0) return 0;

    let processed = 0;
    for (const item of pending) {
        try {
            await handleIncomingShare(item);
            processed++;
        } catch {
            break; // Stop on first failure (probably offline again)
        }
    }

    // Remove processed items
    const remaining = pending.slice(processed);
    await AsyncStorage.setItem(PENDING_SHARES_KEY, JSON.stringify(remaining));
    return processed;
}

/**
 * Clear all pending shares.
 */
export async function clearPendingShares(): Promise<void> {
    await AsyncStorage.removeItem(PENDING_SHARES_KEY);
}

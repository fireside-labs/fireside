/**
 * 💤 DreamJournal — Morning push notifications with personality.
 *
 * Sprint 4: "Living Companion" — the companion sends you a morning
 * briefing push notification as if it "dreamed" about things overnight.
 *
 * Dream entries are based on:
 *   - What happened yesterday (completed tasks, conversations)
 *   - Companion's personality (species-based dreams)
 *   - Random events (adds unpredictability)
 *
 * On the backend, the orchestrator generates dream content during
 * idle hours and stores it. This module fetches and displays them.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Notifications from "expo-notifications";
import { companionAPI } from "./api";

export interface DreamEntry {
    id: string;
    emoji: string;
    title: string;
    content: string;
    species: string;
    timestamp: string;
    read: boolean;
}

const DREAM_JOURNAL_KEY = "fireside_dream_journal";

/**
 * Fetch the latest dream from the companion.
 */
export async function fetchLatestDream(): Promise<DreamEntry | null> {
    try {
        const res = await companionAPI.heartbeat();
        // The backend returns dream content in the heartbeat during morning hours
        if (res.activity?.includes("dream") || res.activity?.includes("morning")) {
            return {
                id: `dream-${Date.now()}`,
                emoji: res.emoji,
                title: res.activity,
                content: res.detail || "I had the most interesting dream last night...",
                species: "unknown",
                timestamp: new Date().toISOString(),
                read: false,
            };
        }
    } catch { }
    return null;
}

/**
 * Get all saved dream journal entries.
 */
export async function getDreamJournal(): Promise<DreamEntry[]> {
    const raw = await AsyncStorage.getItem(DREAM_JOURNAL_KEY);
    if (!raw) return [];
    try {
        return JSON.parse(raw) as DreamEntry[];
    } catch {
        return [];
    }
}

/**
 * Save a dream entry to the journal.
 */
export async function saveDream(dream: DreamEntry): Promise<void> {
    const journal = await getDreamJournal();
    journal.unshift(dream); // newest first
    // Keep last 30 dreams
    const trimmed = journal.slice(0, 30);
    await AsyncStorage.setItem(DREAM_JOURNAL_KEY, JSON.stringify(trimmed));
}

/**
 * Mark a dream entry as read.
 */
export async function markDreamRead(dreamId: string): Promise<void> {
    const journal = await getDreamJournal();
    const updated = journal.map((d) =>
        d.id === dreamId ? { ...d, read: true } : d
    );
    await AsyncStorage.setItem(DREAM_JOURNAL_KEY, JSON.stringify(updated));
}

/**
 * Species-specific dream templates for offline mode.
 */
export const DREAM_TEMPLATES: Record<string, string[]> = {
    fox: [
        "I dreamed I found a hidden library behind a waterfall. Every book was blank until I touched it.",
        "Last night I dreamed about a market where they traded stories instead of coins.",
        "I had a dream where I was solving a puzzle made entirely of starlight.",
    ],
    cat: [
        "I dreamed of the biggest sunbeam ever. It was warm for approximately 12 hours.",
        "I had a dream about a fish that could fly. I caught it anyway.",
        "Last night I dreamed I was a pharaoh. It was... expected.",
    ],
    dog: [
        "I DREAMED ABOUT THE BIGGEST STICK IN THE WORLD!! It was SO big!!",
        "Last night I dreamed every human was giving me belly rubs at the same time!",
        "I had a dream about a park with INFINITE treats! BEST DREAM EVER!",
    ],
    owl: [
        "I dreamed of a constellation that formed a new theorem. I'm still working on the proof.",
        "Last night I witnessed the birth of a galaxy in my dreams. Quite educational.",
        "I dreamed I was cataloging every grain of sand on a beach. I got to 4,273,891.",
    ],
    penguin: [
        "I dreamed of a perfectly organized iceberg. Every crystal in its rightful place.",
        "Last night I dreamed I was conducting an orchestra of whales. Impeccable timing.",
        "I had a dream about a filing system so elegant it made me cry. Professionally.",
    ],
    dragon: [
        "I DREAMED I WAS THE SIZE OF A MOUNTAIN! I sneezed and created a volcano!",
        "Last night I dreamed about the ultimate hoard — every shiny thing in the universe!",
        "I had a dream where I set the ocean on fire. Physics disagrees but dreams don't care!",
    ],
};

/**
 * Schedule a morning dream notification.
 * Call this during app initialization.
 */
export async function scheduleMorningDream(): Promise<void> {
    // Clear existing dream notifications
    await Notifications.cancelAllScheduledNotificationsAsync();

    // Schedule for 8:00 AM daily
    await Notifications.scheduleNotificationAsync({
        content: {
            title: "💤 Your companion had a dream...",
            body: "Open Fireside to read about it!",
            sound: "default",
        },
        trigger: {
            type: Notifications.SchedulableTriggerInputTypes.DAILY,
            hour: 8,
            minute: 0,
        },
    });
}

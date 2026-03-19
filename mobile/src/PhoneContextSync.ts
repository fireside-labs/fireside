/**
 * 📡 PhoneContextSync — Syncs phone sensor data to the PC brain.
 *
 * The phone is the SENSOR LAYER. The PC is the BRAIN LAYER.
 * This module bridges them: contacts, calendar, location, health → PC working memory.
 *
 * Runs on:
 *   - App foreground (full sync)
 *   - WebSocket reconnect (delta sync)
 *   - Background task (lightweight sync)
 *
 * Privacy: All data goes to YOUR PC only. Never touches any cloud.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { getSocket } from "./FiresideSocket";
import { companionAPI } from "./api";

// ── Types ──

export interface PhoneContext {
    /** Contacts the user has given permission to access */
    contacts?: ContactSnapshot[];
    /** Today's calendar events */
    calendar?: CalendarSnapshot;
    /** Device info */
    device?: DeviceSnapshot;
    /** Last sync timestamp */
    synced_at: number;
}

interface ContactSnapshot {
    name: string;
    phone?: string;
    email?: string;
    nickname?: string;
}

interface CalendarSnapshot {
    today: CalendarEventSnapshot[];
    next_event?: CalendarEventSnapshot;
    event_count: number;
}

interface CalendarEventSnapshot {
    title: string;
    start: string;
    end: string;
    location?: string;
    is_all_day?: boolean;
}

interface DeviceSnapshot {
    platform: "ios" | "android";
    time_zone: string;
    locale: string;
    hour: number;
}

// ── Sync State ──

const LAST_CONTACTS_HASH_KEY = "fireside_contacts_hash";
const LAST_SYNC_KEY = "fireside_context_last_sync";
const MIN_SYNC_INTERVAL_MS = 5 * 60_000; // Don't sync more than every 5 min

// Simple hash for change detection (avoid re-sending unchanged contacts)
function quickHash(data: string): string {
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
        hash = ((hash << 5) - hash + data.charCodeAt(i)) | 0;
    }
    return hash.toString(36);
}

// ── Core Sync ──

/**
 * Full context sync — sends all available phone sensor data to the PC.
 * Called on app foreground and after WebSocket reconnect.
 */
export async function syncPhoneContext(): Promise<void> {
    // Rate limit
    const lastSync = await AsyncStorage.getItem(LAST_SYNC_KEY);
    if (lastSync && Date.now() - parseInt(lastSync) < MIN_SYNC_INTERVAL_MS) {
        return; // Too soon, skip
    }

    const context: PhoneContext = {
        synced_at: Date.now(),
    };

    // ── Contacts ──
    try {
        const { loadContacts } = await import("./native/ContactsBridge");
        const contacts = await loadContacts();
        if (contacts && contacts.length > 0) {
            // Check if contacts changed since last sync
            const snapshot: ContactSnapshot[] = contacts.slice(0, 200).map((c) => ({
                name: c.name,
                phone: c.phone,
                email: c.email,
                nickname: c.nickname,
            }));
            const hash = quickHash(JSON.stringify(snapshot));
            const prevHash = await AsyncStorage.getItem(LAST_CONTACTS_HASH_KEY);
            if (hash !== prevHash) {
                context.contacts = snapshot;
                await AsyncStorage.setItem(LAST_CONTACTS_HASH_KEY, hash);
            }
        }
    } catch { }

    // ── Calendar ──
    try {
        const NativeCalendar = await import("../modules/native-calendar");
        const todayEvents = await NativeCalendar.getTodayEvents();
        const nextEvent = await NativeCalendar.getNextEvent();

        const mapEvent = (e: any): CalendarEventSnapshot => ({
            title: e.title || "Untitled",
            start: e.startDate || e.start || "",
            end: e.endDate || e.end || "",
            location: e.location,
            is_all_day: e.allDay || e.isAllDay,
        });

        context.calendar = {
            today: todayEvents.map(mapEvent),
            next_event: nextEvent ? mapEvent(nextEvent) : undefined,
            event_count: todayEvents.length,
        };
    } catch { }

    // ── Device ──
    try {
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const locale = Intl.DateTimeFormat().resolvedOptions().locale;
        const { Platform } = require("react-native");
        context.device = {
            platform: Platform.OS === "ios" ? "ios" : "android",
            time_zone: tz,
            locale: locale,
            hour: new Date().getHours(),
        };
    } catch { }

    // ── Send to PC ──
    const socket = getSocket();
    if (socket.isConnected) {
        // Prefer WebSocket (instant, no HTTP overhead)
        socket.send("phone_context", context);
    } else {
        // Fallback to HTTP
        try {
            await companionAPI.syncContext(context as any);
        } catch { }
    }

    await AsyncStorage.setItem(LAST_SYNC_KEY, Date.now().toString());
}

/**
 * Lightweight sync — just calendar + device info (no contacts).
 * Used for background task (iOS 30-second limit).
 */
export async function syncCalendarOnly(): Promise<void> {
    const context: Partial<PhoneContext> = { synced_at: Date.now() };

    try {
        const NativeCalendar = await import("../modules/native-calendar");
        const todayEvents = await NativeCalendar.getTodayEvents();
        const nextEvent = await NativeCalendar.getNextEvent();

        const mapEvent = (e: any): CalendarEventSnapshot => ({
            title: e.title || "Untitled",
            start: e.startDate || e.start || "",
            end: e.endDate || e.end || "",
            location: e.location,
        });

        context.calendar = {
            today: todayEvents.map(mapEvent),
            next_event: nextEvent ? mapEvent(nextEvent) : undefined,
            event_count: todayEvents.length,
        };
    } catch { }

    const socket = getSocket();
    if (socket.isConnected) {
        socket.send("phone_context", context);
    }
}

/**
 * Resolve a contact by name and return their info.
 * Used when the AI says "email Jordan" — phone resolves, sends back to PC.
 */
export async function resolveContact(query: string): Promise<ContactSnapshot | null> {
    try {
        const { loadContacts, searchContacts } = await import("./native/ContactsBridge");
        const contacts = await loadContacts();
        if (!contacts) return null;
        const matches = searchContacts(contacts, query);
        if (matches.length === 0) return null;
        return {
            name: matches[0].name,
            phone: matches[0].phone,
            email: matches[0].email,
            nickname: matches[0].nickname,
        };
    } catch {
        return null;
    }
}

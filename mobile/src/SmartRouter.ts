/**
 * 🔀 SmartRouter — Intelligent network routing.
 *
 * Sprint 6: "Trust & Polish" — automatically detects the best
 * connection path and switches seamlessly between:
 *   - LAN (local network, fastest, most private)
 *   - Tailscale (VPN mesh, works from anywhere)
 *   - Offline (pocket mode, queue everything)
 *
 * Also provides the privacy badge info: shows the user
 * WHERE their data is being processed at all times.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { getHost, getTailscaleIP, getConnectionPref, setHost, setConnectionPref } from "./api";
import { testConnection } from "./api";

export type NetworkRoute = "local" | "tailscale" | "offline";

export interface RouteInfo {
    route: NetworkRoute;
    host: string | null;
    latency: number | null;
    /** Human-readable privacy badge text. */
    privacyBadge: string;
    /** Processing location for the privacy badge. */
    processingLocation: "Your PC (LAN)" | "Your PC (VPN)" | "On Device" | "Unknown";
    /** Emoji for the route. */
    emoji: string;
}

const ROUTE_CACHE_KEY = "fireside_route_cache";
const PROBE_TIMEOUT = 2000;

/**
 * Probe a host and measure latency.
 */
async function probeHost(host: string): Promise<number | null> {
    const start = Date.now();
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), PROBE_TIMEOUT);
        await fetch(`http://${host}/health`, { signal: controller.signal });
        clearTimeout(timeout);
        return Date.now() - start;
    } catch {
        return null;
    }
}

/**
 * Determine the best route to the backend.
 * Tries LAN first (faster, more private), then Tailscale.
 */
export async function detectBestRoute(): Promise<RouteInfo> {
    const lanHost = await getHost();
    const tsIP = await getTailscaleIP();

    // Try LAN first (fastest, most private)
    if (lanHost) {
        const latency = await probeHost(lanHost);
        if (latency !== null) {
            return {
                route: "local",
                host: lanHost,
                latency,
                privacyBadge: "🏠 Processing on your PC (LAN)",
                processingLocation: "Your PC (LAN)",
                emoji: "🏠",
            };
        }
    }

    // Try Tailscale (works from anywhere)
    if (tsIP) {
        const latency = await probeHost(`${tsIP}:8000`);
        if (latency !== null) {
            return {
                route: "tailscale",
                host: `${tsIP}:8000`,
                latency,
                privacyBadge: "🔐 Processing on your PC (VPN)",
                processingLocation: "Your PC (VPN)",
                emoji: "🔐",
            };
        }
    }

    // Offline
    return {
        route: "offline",
        host: null,
        latency: null,
        privacyBadge: "📱 Processing on device",
        processingLocation: "On Device",
        emoji: "📱",
    };
}

/**
 * Apply the best route — switches the active host automatically.
 */
export async function applyBestRoute(): Promise<RouteInfo> {
    const route = await detectBestRoute();

    if (route.route === "local" && route.host) {
        await setHost(route.host);
        await setConnectionPref("local");
    } else if (route.route === "tailscale" && route.host) {
        await setHost(route.host);
        await setConnectionPref("bridge");
    }

    // Cache the route for quick reads
    await AsyncStorage.setItem(ROUTE_CACHE_KEY, JSON.stringify(route));
    return route;
}

/**
 * Get the cached route info (for the privacy badge).
 */
export async function getCachedRoute(): Promise<RouteInfo | null> {
    const raw = await AsyncStorage.getItem(ROUTE_CACHE_KEY);
    if (!raw) return null;
    try {
        return JSON.parse(raw) as RouteInfo;
    } catch {
        return null;
    }
}

/**
 * Privacy badge descriptions for the settings screen.
 */
export const ROUTE_DESCRIPTIONS: Record<NetworkRoute, { title: string; desc: string; emoji: string }> = {
    local: {
        title: "LAN Connection",
        desc: "Connected directly to your PC on the same network. Fastest and most private — data never leaves your home.",
        emoji: "🏠",
    },
    tailscale: {
        title: "VPN Connection",
        desc: "Connected to your PC through Tailscale VPN. Encrypted end-to-end, works from anywhere.",
        emoji: "🔐",
    },
    offline: {
        title: "Pocket Mode",
        desc: "Running on-device with Qwen 0.5B. No data sent anywhere. Full privacy, limited power.",
        emoji: "📱",
    },
};

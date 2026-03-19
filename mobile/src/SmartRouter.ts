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
 * Discover the Fireside backend via mDNS/Zeroconf (zero-config).
 * Falls back gracefully if react-native-zeroconf is not installed.
 * Returns host:port or null.
 */
export async function discoverViaMDNS(timeoutMs = 5000): Promise<string | null> {
    try {
        // Dynamic require — won't crash if not installed
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const Zeroconf = require("react-native-zeroconf").default as new () => any;
        const zc = new Zeroconf();

        return new Promise<string | null>((resolve) => {
            const timer = setTimeout(() => {
                zc.stop();
                resolve(null);
            }, timeoutMs);

            zc.on("resolved", (service: any) => {
                if (service.name?.includes("fireside")) {
                    clearTimeout(timer);
                    zc.stop();
                    const host = service.host || service.addresses?.[0];
                    const port = service.port || 8765;
                    if (host) {
                        resolve(`${host}:${port}`);
                    } else {
                        resolve(null);
                    }
                }
            });

            zc.on("error", () => {
                clearTimeout(timer);
                resolve(null);
            });

            // Browse for Fireside TCP service
            zc.scan("fireside", "tcp", "local.");
        });
    } catch {
        // react-native-zeroconf not installed — that's fine
        return null;
    }
}

/**
 * Determine the best route to the backend.
 * Priority: mDNS → LAN probe → Tailscale probe → Offline.
 */
export async function detectBestRoute(): Promise<RouteInfo> {
    // 1. Try mDNS discovery first (instant, zero-config)
    const mdnsHost = await discoverViaMDNS(3000);
    if (mdnsHost) {
        const latency = await probeHost(mdnsHost);
        if (latency !== null) {
            return {
                route: "local",
                host: mdnsHost,
                latency,
                privacyBadge: "🏠 Processing on your PC (LAN)",
                processingLocation: "Your PC (LAN)",
                emoji: "🏠",
            };
        }
    }

    // 2. Try stored LAN host (fast if already known)
    const lanHost = await getHost();
    const tsIP = await getTailscaleIP();

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

    // 3. Try Tailscale (works from anywhere)
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

    // 4. Offline
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

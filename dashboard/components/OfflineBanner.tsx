"use client";

/**
 * ⚠️ Offline Banner — Sprint 14 F9.
 *
 * Shows a visible indicator when the dashboard is using mock/cached data
 * because the backend is unreachable. Prevents user confusion about what's real.
 */
import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";

export default function OfflineBanner() {
    const [offline, setOffline] = useState(false);

    useEffect(() => {
        const check = async () => {
            try {
                // Increased timeout to 10s because local 35B models can cause random CPU lockups
                const res = await fetch(`${API_BASE}/api/v1/status`, { signal: AbortSignal.timeout(10000) });
                setOffline(!res.ok);
            } catch {
                setOffline(true);
            }
        };
        check();
        const interval = setInterval(check, 10000);
        return () => clearInterval(interval);
    }, []);

    if (!offline) return null;

    return (
        <div
            style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                zIndex: 9000,
                background: "rgba(245, 158, 11, 0.12)",
                borderBottom: "1px solid rgba(245, 158, 11, 0.3)",
                padding: "6px 16px",
                textAlign: "center",
                fontSize: "13px",
                fontWeight: 500,
                color: "#F59E0B",
                backdropFilter: "blur(8px)",
            }}
        >
            ⚠️ Offline mode — showing cached data. Start the Fireside backend to see live data.
        </div>
    );
}

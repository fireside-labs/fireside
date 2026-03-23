"use client";

/**
 * ⚠️ Offline Banner — Sprint 14 F9.
 *
 * Shows a visible indicator when the dashboard is using mock/cached data
 * because the backend is unreachable.
 *
 * FIX: Requires 3 consecutive failed health checks before showing.
 * This prevents false "offline" flashes when the AI is busy with heavy
 * tasks (browser tools, long inference) and the backend is slow to respond.
 */
import { useState, useEffect, useRef } from "react";
import { API_BASE } from "@/lib/api";

const FAIL_THRESHOLD = 3; // consecutive failures before showing banner
const CHECK_INTERVAL = 12000; // 12s between checks
const TIMEOUT = 15000; // 15s timeout (generous — heavy models can lock CPU)

export default function OfflineBanner() {
    const [offline, setOffline] = useState(false);
    const failCountRef = useRef(0);

    useEffect(() => {
        const check = async () => {
            try {
                const res = await fetch(`${API_BASE}/health`, {
                    signal: AbortSignal.timeout(TIMEOUT),
                });
                if (res.ok) {
                    failCountRef.current = 0;
                    setOffline(false);
                } else {
                    failCountRef.current++;
                }
            } catch {
                failCountRef.current++;
            }

            // Only show offline after multiple consecutive failures
            if (failCountRef.current >= FAIL_THRESHOLD) {
                setOffline(true);
            }
        };
        check();
        const interval = setInterval(check, CHECK_INTERVAL);
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


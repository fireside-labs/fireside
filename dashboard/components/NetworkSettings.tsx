"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "../lib/api";

interface NetworkStatus {
    local_ip: string;
    tailscale_ip: string | null;
    bridge_active: boolean;
}

export default function NetworkSettings() {
    const [status, setStatus] = useState<NetworkStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/network/status`);
                if (res.ok) {
                    setStatus(await res.json());
                } else {
                    setError("Backend returned an error.");
                }
            } catch {
                setError("Could not reach the backend.");
            }
            setLoading(false);
        })();
    }, []);

    if (loading) {
        return (
            <div className="glass-card p-6">
                <p className="text-[var(--color-rune-dim)]">Loading network status...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="glass-card p-6">
                <p className="text-red-400">{error}</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                🌐 Network / Bridge
            </h3>

            {/* Local IP */}
            <div className="glass-card p-5">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[var(--color-rune-dim)]">Local IP</span>
                    <span className="text-white font-mono text-sm">{status?.local_ip || "Unknown"}</span>
                </div>
                <p className="text-xs text-[var(--color-rune-dim)]">
                    This is your PC's IP on your home Wi-Fi. Mobile devices on the same network can connect here.
                </p>
            </div>

            {/* Anywhere Bridge */}
            <div
                className="glass-card p-5"
                style={{
                    borderColor: status?.bridge_active ? "var(--color-neon)" : "var(--color-glass-border)",
                    borderWidth: 1,
                }}
            >
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[var(--color-rune-dim)]">
                        Anywhere Bridge
                    </span>
                    <span
                        className="text-xs font-semibold px-2 py-0.5 rounded-full"
                        style={{
                            background: status?.bridge_active ? "var(--color-neon-glow)" : "var(--color-glass)",
                            color: status?.bridge_active ? "var(--color-neon)" : "var(--color-rune-dim)",
                        }}
                    >
                        {status?.bridge_active ? "🟢 Active" : "⚫ Inactive"}
                    </span>
                </div>

                {status?.tailscale_ip ? (
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-sm text-[var(--color-rune-dim)]">Tailscale IP</span>
                        <span className="text-white font-mono text-sm">{status.tailscale_ip}</span>
                    </div>
                ) : (
                    <p className="text-sm text-[var(--color-rune-dim)] mb-3">
                        Tailscale is not configured on this machine.
                    </p>
                )}

                <div className="bg-[var(--color-glass)] rounded-lg p-4 mt-2">
                    <p className="text-xs text-[var(--color-rune)] font-medium mb-2">How to enable:</p>
                    <ol className="text-xs text-[var(--color-rune-dim)] space-y-1 list-decimal list-inside">
                        <li>Run <code className="text-[var(--color-neon)]">scripts/setup_bridge.ps1</code> (Windows) or <code className="text-[var(--color-neon)]">scripts/setup_bridge.sh</code> (Mac/Linux)</li>
                        <li>Sign in to Tailscale when prompted</li>
                        <li>Install the Tailscale app on your phone and sign in with the same account</li>
                        <li>Your companion can now reach Atlas from anywhere 🔥</li>
                    </ol>
                </div>
            </div>

            {/* Privacy note */}
            <div className="glass-card p-4 text-center" style={{ borderColor: "var(--color-neon)", borderWidth: 1 }}>
                <p className="text-xs text-[var(--color-rune-dim)]">
                    🔒 The Anywhere Bridge uses Tailscale's peer-to-peer VPN. Your data goes directly between your devices — never through our servers.
                </p>
            </div>
        </div>
    );
}

"use client";

import { useState, useEffect } from "react";

interface SystemStatusProps {
    className?: string;
}

interface StatusData {
    brain: { label: string; tokS: number } | null;
    telegram: boolean;
    inference: "running" | "offline" | "starting";
}

export default function SystemStatus({ className }: SystemStatusProps) {
    const [status, setStatus] = useState<StatusData>({
        brain: null,
        telegram: false,
        inference: "offline",
    });

    // Poll /api/v1/status every 5 seconds (Sprint 14 F7)
    useEffect(() => {
        let mounted = true;
        const poll = async () => {
            try {
                const res = await fetch("http://127.0.0.1:8765/api/v1/status");
                if (res.ok && mounted) {
                    const data = await res.json();
                    setStatus({
                        brain: data.brain || null,
                        telegram: data.telegram ?? false,
                        inference: data.inference || "running",
                    });
                }
            } catch {
                if (mounted) setStatus((prev) => ({ ...prev, inference: "offline" }));
            }
        };
        poll();
        const interval = setInterval(poll, 5000);
        return () => { mounted = false; clearInterval(interval); };
    }, []);

    const handleRestart = async () => {
        setStatus((prev) => ({ ...prev, inference: "starting" }));
        try {
            await fetch("http://127.0.0.1:8765/api/v1/restart", { method: "POST" });
        } catch {
            // Backend will restart — poll will pick up the new state
        }
    };

    return (
        <div className={`space-y-1.5 text-xs ${className || ""}`}>
            {/* Brain */}
            {status.brain && (
                <div className="flex items-center gap-1.5 text-[var(--color-rune-dim)]">
                    <span>🧠</span>
                    <span>{status.brain.label}</span>
                    <span className="text-[var(--color-neon)]">· {status.brain.tokS} letters/sec</span>
                </div>
            )}

            {/* Telegram */}
            {status.telegram && (
                <div className="flex items-center gap-1.5 text-[var(--color-rune-dim)]">
                    <span>💬</span>
                    <span>Connected</span>
                </div>
            )}

            {/* Inference */}
            <div className="flex items-center gap-1.5">
                {status.inference === "running" && (
                    <>
                        <span className="text-[var(--color-neon)]">✅</span>
                        <span className="text-[var(--color-rune-dim)]">Running</span>
                    </>
                )}
                {status.inference === "offline" && (
                    <>
                        <span className="text-[var(--color-danger)]">❌</span>
                        <span className="text-[var(--color-rune-dim)]">Offline</span>
                        <button
                            onClick={handleRestart}
                            className="text-[var(--color-neon)] hover:underline ml-1"
                        >
                            Restart
                        </button>
                    </>
                )}
                {status.inference === "starting" && (
                    <>
                        <span className="text-[var(--color-warning)]">⏳</span>
                        <span className="text-[var(--color-rune-dim)]">Starting...</span>
                    </>
                )}
            </div>
        </div>
    );
}

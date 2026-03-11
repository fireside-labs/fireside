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
        brain: { label: "Smart & Fast", tokS: 45 },
        telegram: false,
        inference: "running",
    });

    // In production, poll /api/v1/system/status
    // useEffect(() => { ... }, []);

    const handleRestart = () => {
        setStatus(prev => ({ ...prev, inference: "starting" }));
        setTimeout(() => {
            setStatus(prev => ({ ...prev, inference: "running" }));
        }, 2000);
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

"use client";

import { useEffect, useState } from "react";

interface DownloadProgressProps {
    /** Brain display name, e.g. "Smart & Fast" */
    brainName: string;
    /** 0 - 100 */
    progress: number;
    /** e.g. "4.2 GB / 6.1 GB" */
    progressLabel?: string;
    /** Current step label, e.g. "Downloading model..." */
    stepLabel?: string;
    /** Download speed, e.g. "12.3 MB/s" */
    speed?: string;
    /** e.g. "~2 min left" */
    eta?: string;
    /** Done state */
    complete?: boolean;
    /** Speed result after install, e.g. "45 letters/sec" */
    tokS?: number;
}

export default function DownloadProgress({
    brainName,
    progress,
    progressLabel,
    stepLabel,
    speed,
    eta,
    complete,
    tokS,
}: DownloadProgressProps) {
    const [dots, setDots] = useState("");

    // Animate dots while downloading
    useEffect(() => {
        if (complete) return;
        const interval = setInterval(() => {
            setDots((d) => (d.length >= 3 ? "" : d + "."));
        }, 500);
        return () => clearInterval(interval);
    }, [complete]);

    if (complete) {
        return (
            <div className="glass-card p-5 text-center">
                <span className="text-3xl block mb-2">✅</span>
                <h3 className="text-white font-semibold mb-1">Brain installed!</h3>
                {tokS && (
                    <p className="text-sm text-[var(--color-neon)]">
                        Speed: {tokS} letters/sec
                    </p>
                )}
                <p className="text-xs text-[var(--color-rune-dim)] mt-2">
                    &quot;{brainName}&quot; is ready to use.
                </p>
            </div>
        );
    }

    return (
        <div className="glass-card p-5">
            <p className="text-sm text-white font-medium mb-3">
                Installing &quot;{brainName}&quot; brain{dots}
            </p>

            {/* Progress bar */}
            <div className="h-3 rounded-full bg-[var(--color-glass)] mb-2 overflow-hidden">
                <div
                    className="h-3 rounded-full transition-all duration-300"
                    style={{
                        width: `${progress}%`,
                        background: "linear-gradient(90deg, var(--color-neon-dim), var(--color-neon))",
                    }}
                />
            </div>

            {/* Stats row */}
            <div className="flex justify-between text-xs text-[var(--color-rune-dim)]">
                <span>{stepLabel || "Preparing..."}</span>
                <span>{Math.round(progress)}%</span>
            </div>

            {/* Details row */}
            {(progressLabel || speed || eta) && (
                <div className="flex justify-between text-xs text-[var(--color-rune-dim)] mt-1">
                    <span>{progressLabel}</span>
                    <span>
                        {speed && <>{speed}</>}
                        {speed && eta && " · "}
                        {eta && <>{eta}</>}
                    </span>
                </div>
            )}
        </div>
    );
}

"use client";

import { useState } from "react";
import DownloadProgress from "@/components/DownloadProgress";

interface BrainInstallerProps {
    brainLabel: string;
    brainId: string;
    onComplete?: (tokS: number) => void;
    onCancel?: () => void;
}

type Phase = "confirm" | "downloading" | "configuring" | "verifying" | "done";

/**
 * One-click brain install orchestrator.
 * Simulates the install flow: confirm → download → configure → verify → done.
 * In production, this would listen to WebSocket `brain.download.progress` events.
 */
export default function BrainInstaller({ brainLabel, brainId, onComplete, onCancel }: BrainInstallerProps) {
    const [phase, setPhase] = useState<Phase>("confirm");
    const [progress, setProgress] = useState(0);
    const [tokS, setTokS] = useState(0);

    const startInstall = () => {
        setPhase("downloading");

        // Simulate download progress
        let p = 0;
        const downloadInterval = setInterval(() => {
            p += Math.random() * 8 + 2;
            if (p >= 100) {
                p = 100;
                clearInterval(downloadInterval);
                setProgress(100);
                setPhase("configuring");

                // Simulate configuring
                setTimeout(() => {
                    setPhase("verifying");
                    // Simulate verify
                    setTimeout(() => {
                        const finalTokS = brainId === "fast" ? 45 : brainId === "deep" ? 18 : 120;
                        setTokS(finalTokS);
                        setPhase("done");
                        onComplete?.(finalTokS);
                    }, 1500);
                }, 2000);
            }
            setProgress(p);
        }, 300);
    };

    if (phase === "confirm") {
        return (
            <div className="glass-card p-6 text-center">
                <span className="text-4xl block mb-3">🧠</span>
                <h3 className="text-white font-semibold mb-1">
                    Install &quot;{brainLabel}&quot;?
                </h3>
                <p className="text-sm text-[var(--color-rune-dim)] mb-4">
                    This will download the AI model and set up the inference server.
                    <br />
                    It may take a few minutes depending on your internet speed.
                </p>
                <div className="flex justify-center gap-3">
                    <button onClick={startInstall} className="btn-neon px-6 py-2.5 text-sm">
                        Install
                    </button>
                    {onCancel && (
                        <button
                            onClick={onCancel}
                            className="px-6 py-2.5 text-sm text-[var(--color-rune-dim)] hover:text-white border border-[var(--color-glass-border)] rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                    )}
                </div>
            </div>
        );
    }

    if (phase === "done") {
        return (
            <DownloadProgress
                brainName={brainLabel}
                progress={100}
                complete
                tokS={tokS}
            />
        );
    }

    const stepLabels: Record<string, string> = {
        downloading: "Downloading model...",
        configuring: "Setting up inference server...",
        verifying: "Running speed test...",
    };

    const sizeEstimates: Record<string, { total: string; current: string }> = {
        fast: { total: "4.6 GB", current: `${(progress / 100 * 4.6).toFixed(1)} GB` },
        deep: { total: "24.1 GB", current: `${(progress / 100 * 24.1).toFixed(1)} GB` },
        cloud: { total: "0 GB", current: "0 GB" },
    };

    const est = sizeEstimates[brainId] || sizeEstimates.fast;

    return (
        <DownloadProgress
            brainName={brainLabel}
            progress={phase === "downloading" ? progress : 100}
            stepLabel={stepLabels[phase]}
            progressLabel={phase === "downloading" ? `${est.current} / ${est.total}` : undefined}
            speed={phase === "downloading" ? "12.3 MB/s" : undefined}
            eta={phase === "downloading" && progress < 90 ? `~${Math.ceil((100 - progress) / 10)} min left` : undefined}
        />
    );
}

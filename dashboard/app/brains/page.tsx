"use client";

import { useState, useEffect } from "react";
import BrainCard from "@/components/BrainCard";
import BrainInstaller from "@/components/BrainInstaller";
import { useToast } from "@/components/Toast";

interface BrainMeta {
    id: string;
    emoji: string;
    label: string;
    description: string;
    size: string;
    speed: string;
    badge: "FREE" | "PAID";
    compatibility: "compatible" | "needs-more-memory" | "cloud";
    compatibilityNote?: string;
}

// Simulated hardware detection + brain registry
const DETECTED_HARDWARE = {
    device: "MacBook Pro",
    chip: "Apple M3 Max",
    aiMemory: "36 GB",
    ram: "36 GB",
};

const BRAINS: BrainMeta[] = [
    {
        id: "fast", emoji: "⚡", label: "Smart & Fast",
        description: "Best for quick questions and everyday chat. Runs entirely on your device.",
        size: "4.6 GB", speed: "45 letters/sec", badge: "FREE", compatibility: "compatible",
    },
    {
        id: "deep", emoji: "🧠", label: "Deep Thinker",
        description: "Best for complex analysis, long documents, and detailed research. Needs powerful hardware.",
        size: "24.1 GB", speed: "18 letters/sec", badge: "FREE", compatibility: "compatible",
    },
    {
        id: "cloud", emoji: "🌙", label: "Cloud Expert (Kimi)",
        description: "128K context window. Great for reading entire codebases and long documents. Requires internet and API key.",
        size: "Cloud", speed: "120 letters/sec", badge: "PAID", compatibility: "cloud",
    },
];

export default function BrainsPage() {
    const [installed, setInstalled] = useState<string[]>(["fast"]);
    const [activeBrain, setActiveBrain] = useState("fast");
    const [installing, setInstalling] = useState<string | null>(null);
    const [showCloudSetup, setShowCloudSetup] = useState(false);
    const [apiKey, setApiKey] = useState("");
    const { toast } = useToast();

    const handleInstall = (brainId: string) => {
        if (brainId === "cloud") {
            setShowCloudSetup(true);
            return;
        }
        setInstalling(brainId);
    };

    const handleInstallComplete = (brainId: string, tokS: number) => {
        setInstalled((prev) => [...prev, brainId]);
        setActiveBrain(brainId);
        setInstalling(null);
        toast(`"${BRAINS.find(b => b.id === brainId)?.label}" installed! Speed: ${tokS} letters/sec`, "success");
    };

    const handleSwitch = (brainId: string) => {
        setActiveBrain(brainId);
        toast(`Switched to "${BRAINS.find(b => b.id === brainId)?.label}"`, "success");
    };

    const handleRemove = (brainId: string) => {
        setInstalled((prev) => prev.filter((id) => id !== brainId));
        if (activeBrain === brainId) {
            setActiveBrain(installed[0] || "");
        }
        toast(`"${BRAINS.find(b => b.id === brainId)?.label}" removed`, "info");
    };

    const handleCloudSave = () => {
        if (!apiKey.trim()) return;
        setInstalled((prev) => [...prev, "cloud"]);
        setShowCloudSetup(false);
        setApiKey("");
        toast("Cloud brain connected!", "success");
    };

    return (
        <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <span>🧠</span> Brains
                </h1>
                <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                    Install and manage the AI brains that power your assistant.
                </p>
            </div>

            {/* Hardware detection banner */}
            <div className="glass-card p-4 mb-6 flex items-center gap-4">
                <span className="text-2xl">💻</span>
                <div>
                    <p className="text-sm text-white font-medium">
                        {DETECTED_HARDWARE.device} · {DETECTED_HARDWARE.chip}
                    </p>
                    <p className="text-xs text-[var(--color-rune-dim)]">
                        {DETECTED_HARDWARE.aiMemory} AI Memory available
                    </p>
                </div>
                <span className="ml-auto text-xs px-3 py-1 rounded-full bg-[var(--color-neon-glow)] text-[var(--color-neon)] font-bold">
                    ✅ Great for AI
                </span>
            </div>

            {/* Installing state */}
            {installing && (
                <div className="mb-6">
                    <BrainInstaller
                        brainLabel={BRAINS.find(b => b.id === installing)?.label || ""}
                        brainId={installing}
                        onComplete={(tokS) => handleInstallComplete(installing, tokS)}
                        onCancel={() => setInstalling(null)}
                    />
                </div>
            )}

            {/* Cloud API key setup */}
            {showCloudSetup && (
                <div className="glass-card p-5 mb-6">
                    <h3 className="text-white font-semibold mb-2">☁️ Set up Cloud Brain</h3>
                    <p className="text-xs text-[var(--color-rune-dim)] mb-3">
                        Get a free API key from NVIDIA to use cloud-powered AI brains.
                    </p>
                    <div className="flex gap-2 mb-3">
                        <input
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder="Paste your API key here..."
                            type="password"
                            className="flex-1 px-4 py-2.5 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)]"
                        />
                        <button onClick={handleCloudSave} className="btn-neon px-5 py-2 text-sm">
                            Verify & Save
                        </button>
                    </div>
                    <div className="flex items-center justify-between">
                        <a
                            href="https://build.nvidia.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-[var(--color-neon)] hover:underline"
                        >
                            Get a free key →
                        </a>
                        <button
                            onClick={() => setShowCloudSetup(false)}
                            className="text-xs text-[var(--color-rune-dim)] hover:text-white transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Brain cards grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {BRAINS.map((brain) => (
                    <BrainCard
                        key={brain.id}
                        id={brain.id}
                        emoji={brain.emoji}
                        name={brain.id}
                        label={brain.label}
                        description={brain.description}
                        size={brain.size}
                        speed={brain.speed}
                        badge={brain.badge}
                        compatibility={brain.compatibility}
                        compatibilityNote={brain.compatibilityNote}
                        installed={installed.includes(brain.id)}
                        active={activeBrain === brain.id}
                        onInstall={() => handleInstall(brain.id)}
                        onSwitch={() => handleSwitch(brain.id)}
                        onRemove={() => handleRemove(brain.id)}
                    />
                ))}
            </div>
        </div>
    );
}

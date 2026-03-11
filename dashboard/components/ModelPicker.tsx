"use client";

import { useState } from "react";
import { switchModel } from "@/lib/api";

const ALIASES = [
    {
        alias: "odin",
        label: "Odin",
        icon: "⚡",
        model: "llama/Qwen3.5-35B-A3B-8bit",
        description: "Local Qwen 35B — fast, private, on-device",
        color: "var(--color-neon)",
    },
    {
        alias: "hugs",
        label: "Hugs",
        icon: "🧠",
        model: "nvidia/z-ai/glm-5",
        description: "NVIDIA GLM-5 — deep reasoning, cloud",
        color: "#44aaff",
    },
    {
        alias: "moon",
        label: "Moon",
        icon: "🌙",
        model: "nvidia/moonshotai/kimi-k2.5",
        description: "Moonshot Kimi K2.5 — creative, long-context",
        color: "#cc88ff",
    },
];

interface ModelPickerProps {
    currentModel?: string;
    onSwitch?: (alias: string) => void;
}

export function ModelPicker({ currentModel, onSwitch }: ModelPickerProps) {
    const [active, setActive] = useState(currentModel || ALIASES[0].model);
    const [switching, setSwitching] = useState<string | null>(null);
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

    async function handleSwitch(alias: typeof ALIASES[number]) {
        if (alias.model === active) return;
        setSwitching(alias.alias);

        try {
            await switchModel(alias.alias);
            setActive(alias.model);
            onSwitch?.(alias.alias);
            showToast(`Switched to ${alias.label} (${alias.model.split("/").pop()})`, "success");
        } catch {
            showToast(`Failed to switch to ${alias.label}`, "error");
        } finally {
            setSwitching(null);
        }
    }

    function showToast(message: string, type: "success" | "error") {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    }

    return (
        <div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {ALIASES.map((alias) => {
                    const isActive = alias.model === active;
                    const isSwitching = switching === alias.alias;

                    return (
                        <button
                            key={alias.alias}
                            onClick={() => handleSwitch(alias)}
                            disabled={isSwitching}
                            className={`
                glass-card p-6 text-left transition-all duration-300 cursor-pointer
                ${isActive
                                    ? "border-[var(--color-neon)] shadow-[0_0_30px_rgba(0,255,136,0.15)]"
                                    : "hover:border-[rgba(255,255,255,0.15)]"
                                }
              `}
                        >
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-3xl">{alias.icon}</span>
                                {isActive && (
                                    <span className="text-xs font-semibold text-[var(--color-neon)] bg-[var(--color-neon-glow)] px-2.5 py-1 rounded-full">
                                        ACTIVE
                                    </span>
                                )}
                            </div>
                            <h3 className="text-white text-xl font-bold mb-1">{alias.label}</h3>
                            <p className="text-sm text-[var(--color-rune-dim)] mb-3">{alias.description}</p>
                            <p className="text-xs font-mono text-[var(--color-rune-dim)] truncate">{alias.model}</p>
                            {isSwitching && (
                                <div className="mt-3 text-xs text-[var(--color-neon)] animate-pulse">
                                    Switching...
                                </div>
                            )}
                        </button>
                    );
                })}
            </div>

            {/* ─── Toast ─── */}
            {toast && (
                <div className={`toast toast-${toast.type}`}>
                    {toast.type === "success" ? "✓" : "✗"} {toast.message}
                </div>
            )}
        </div>
    );
}

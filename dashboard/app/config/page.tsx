"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import SettingsForm from "@/components/SettingsForm";
import VoiceSettings from "@/components/VoiceSettings";
import { useToast } from "@/components/Toast";

// Lazy-load Advanced sub-sections so they don't bloat initial Settings load
const NodesPage = dynamic(() => import("@/app/nodes/page"), { ssr: false });

type SettingsTab = "general" | "advanced";

const TABS: { id: SettingsTab; label: string; icon: string }[] = [
    { id: "general", label: "General", icon: "⚙" },
    { id: "advanced", label: "Advanced", icon: "🔧" },
];

export default function SettingsPage() {
    const { toast } = useToast();
    const [tab, setTab] = useState<SettingsTab>("general");

    const handleSave = (values: { name: string; role: string; brain: string; addons: string[] }) => {
        console.log("Settings saved:", values);
        toast("Settings saved! Changes apply immediately.", "success");
    };

    return (
        <div className="max-w-xl mx-auto">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <span>⚙</span> Settings
                </h1>
                <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                    Configure your AI, choose a brain, and manage add-ons.
                </p>
            </div>

            {/* Tab Strip */}
            <div className="flex gap-1 mb-6 p-1 rounded-xl bg-[var(--color-void)] border border-[var(--color-glass-border)]">
                {TABS.map((t) => (
                    <button
                        key={t.id}
                        onClick={() => setTab(t.id)}
                        className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                            tab === t.id
                                ? "bg-[var(--color-neon)] text-black shadow-md"
                                : "text-[var(--color-rune-dim)] hover:text-white hover:bg-white/5"
                        }`}
                    >
                        <span>{t.icon}</span>
                        {t.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            {tab === "general" && (
                <div className="space-y-6">
                    <SettingsForm onSave={handleSave} />
                    <VoiceSettings />

                    {/* Connect Your Phone */}
                    <div className="glass-card p-6">
                        <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                            <span>📱</span> Connect Your Phone
                        </h2>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-4">
                            Take your AI companion on the go with the Fireside mobile app.
                        </p>
                        <div className="flex items-center gap-4 p-4 rounded-xl bg-[var(--color-void)] border border-[var(--color-glass-border)]">
                            <div className="w-16 h-16 rounded-xl bg-[var(--color-neon-glow)] flex items-center justify-center text-3xl border border-[var(--color-neon)]/20">
                                🔥
                            </div>
                            <div className="flex-1">
                                <p className="text-sm text-white font-medium">Fireside for Mobile</p>
                                <p className="text-xs text-[var(--color-rune-dim)] mt-1">
                                    Available on iOS &amp; Android via Expo Go. Your companion syncs automatically.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {tab === "advanced" && (
                <div className="space-y-8">
                    {/* Connected Devices */}
                    <div>
                        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <span>📱</span> Connected Devices
                        </h2>
                        <NodesPage />
                    </div>

                    {/* Task Builder */}
                    <div className="glass-card p-6">
                        <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                            <span>📋</span> Task Builder
                        </h2>
                        <p className="text-sm text-[var(--color-rune-dim)]">
                            Multi-step task pipeline coming in a future update.
                        </p>
                    </div>

                    {/* Learning Stats */}
                    <div className="glass-card p-6">
                        <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                            <span>📊</span> How It&apos;s Learning
                        </h2>
                        <p className="text-sm text-[var(--color-rune-dim)]">
                            Learning analytics and wisdom viewer coming in a future update.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}

"use client";

import { useState } from "react";
import SettingsForm from "@/components/SettingsForm";
import TelegramSetup from "@/components/TelegramSetup";
import VoiceSettings from "@/components/VoiceSettings";
import { useToast } from "@/components/Toast";

export default function SettingsPage() {
    const { toast } = useToast();
    const [showRaw, setShowRaw] = useState(false);

    const handleSave = (values: { name: string; role: string; brain: string; addons: string[] }) => {
        console.log("Settings saved:", values);
        toast("Settings saved! Changes apply immediately.", "success");
    };

    const agentName = typeof window !== "undefined" ? localStorage.getItem("fireside_agent_name") || "atlas" : "atlas";

    // Mock raw config for Advanced view
    const rawYaml = `# Fireside Configuration
name: ${agentName.toLowerCase()}
role: orchestrator
model: llama-3.1-8b
plugins:
  - model_switch
  - watchdog
  - memory
  - hydra
mesh:
  discovery: mdns
  port: 8444
  tls: true`;

    return (
        <div className="max-w-xl mx-auto">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <span>⚙</span> Settings
                </h1>
                <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                    Configure your AI, choose a brain, and manage add-ons.
                </p>
            </div>

            {!showRaw ? (
                <div className="space-y-6">
                    <SettingsForm onSave={handleSave} />
                    <VoiceSettings />
                    <TelegramSetup />
                </div>
            ) : (
                <div>
                    <div className="glass-card p-5 mb-4">
                        <h3 className="text-white font-semibold mb-3">Raw Configuration (valhalla.yaml)</h3>
                        <textarea
                            defaultValue={rawYaml}
                            rows={16}
                            className="w-full px-4 py-3 rounded-lg bg-[var(--color-void)] border border-[var(--color-glass-border)] text-[var(--color-rune)] text-sm font-mono outline-none focus:border-[var(--color-neon)] transition-colors resize-none"
                        />
                    </div>
                    <button
                        onClick={() => setShowRaw(false)}
                        className="text-sm text-[var(--color-neon)] hover:underline"
                    >
                        ← Back to simple view
                    </button>
                </div>
            )}
        </div>
    );
}

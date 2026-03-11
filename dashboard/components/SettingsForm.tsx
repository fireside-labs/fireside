"use client";

import { useState } from "react";
import BrainPicker from "@/components/BrainPicker";

const ADDON_OPTIONS = [
    { id: "model-switching", label: "Smart Switching", desc: "Automatically switch brains based on the task", default: true },
    { id: "watchdog", label: "Auto-Restart", desc: "Automatically restarts if something breaks", default: true },
    { id: "memory", label: "Long-Term Memory", desc: "Remembers conversations across sessions", default: true },
    { id: "daily-summary", label: "Daily Summary", desc: "Morning summary of what happened overnight", default: false },
    { id: "hydra", label: "Self-Healing", desc: "Automatically recovers from errors", default: true },
    { id: "cache", label: "Smart Cache", desc: "Saves frequent responses for speed", default: false },
];

interface SettingsFormProps {
    onSave: (values: { name: string; role: string; brain: string; addons: string[] }) => void;
}

export default function SettingsForm({ onSave }: SettingsFormProps) {
    const [name, setName] = useState("Odin");
    const [role, setRole] = useState("main");
    const [brain, setBrain] = useState("fast");
    const [addons, setAddons] = useState<string[]>(ADDON_OPTIONS.filter(a => a.default).map(a => a.id));
    const [showAdvanced, setShowAdvanced] = useState(false);

    const toggleAddon = (id: string) => {
        setAddons(prev => prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id]);
    };

    return (
        <div className="space-y-6">
            {/* Your AI */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-4">Your AI</h3>
                <div className="space-y-3">
                    <div>
                        <label htmlFor="settings-name" className="text-xs text-[var(--color-rune-dim)] mb-1 block">Name</label>
                        <input
                            id="settings-name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors"
                        />
                    </div>
                    <div>
                        <label htmlFor="settings-role" className="text-xs text-[var(--color-rune-dim)] mb-1 block">Role</label>
                        <select
                            id="settings-role"
                            value={role}
                            onChange={(e) => setRole(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none"
                        >
                            <option value="main">Main Assistant</option>
                            <option value="helper">Helper</option>
                            <option value="memory">Memory Assistant</option>
                            <option value="security">Security Guard</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* AI Brain */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-1">AI Brain</h3>
                <p className="text-xs text-[var(--color-rune-dim)] mb-4">Choose which brain powers your AI.</p>
                <BrainPicker selected={brain} onSelect={setBrain} />
            </div>

            {/* Add-ons */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-1">Add-ons</h3>
                <p className="text-xs text-[var(--color-rune-dim)] mb-4">Extra features for your AI.</p>
                <div className="space-y-3">
                    {ADDON_OPTIONS.map((addon) => (
                        <div key={addon.id} className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-white">{addon.label}</p>
                                <p className="text-xs text-[var(--color-rune-dim)]">{addon.desc}</p>
                            </div>
                            <button
                                onClick={() => toggleAddon(addon.id)}
                                role="switch"
                                aria-checked={addons.includes(addon.id)}
                                aria-label={addon.label}
                                className="w-12 h-6 rounded-full transition-all relative"
                                style={{
                                    background: addons.includes(addon.id) ? "var(--color-neon)" : "var(--color-glass-border)",
                                }}
                            >
                                <div
                                    className="w-5 h-5 rounded-full bg-white absolute top-0.5 transition-all"
                                    style={{
                                        left: addons.includes(addon.id) ? 26 : 2,
                                    }}
                                />
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Advanced */}
            <div className="glass-card p-5">
                <button
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="text-sm text-[var(--color-rune-dim)] hover:text-[var(--color-rune)] transition-colors"
                >
                    {showAdvanced ? "▾" : "▸"} Edit raw config file (valhalla.yaml)
                </button>
                {showAdvanced && (
                    <p className="text-xs text-[var(--color-rune-dim)] mt-2">
                        For power users — edit the configuration YAML directly.
                        <br />
                        <a href="/config" className="text-[var(--color-neon)] hover:underline mt-1 inline-block">Open raw editor →</a>
                    </p>
                )}
            </div>

            {/* Save */}
            <button
                onClick={() => onSave({ name, role, brain, addons })}
                className="btn-neon px-6 py-3 text-sm w-full"
            >
                Save
            </button>
            <p className="text-xs text-center text-[var(--color-rune-dim)]">Changes apply immediately.</p>
        </div>
    );
}

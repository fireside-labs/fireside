"use client";

import { useState } from "react";

const QUALITY_LABELS = [
    { label: "Speed", desc: "Fewer checks, faster result", iterations: 3 },
    { label: "", desc: "", iterations: 5 },
    { label: "Balanced", desc: "", iterations: 7 },
    { label: "", desc: "", iterations: 10 },
    { label: "Quality", desc: "More checking, better result", iterations: 15 },
];

const NOTIFICATION_OPTIONS = [
    { id: "dashboard", label: "Show a notification in the dashboard", icon: "🔔" },
    { id: "text", label: "Send me a text message", icon: "📱" },
    { id: "retry", label: "Just keep trying", icon: "🔄" },
];

export default function TaskWizard({ onClose, onCreate }: {
    onClose: () => void;
    onCreate: (task: { description: string; quality: number; notification: string }) => void;
}) {
    const [description, setDescription] = useState("");
    const [quality, setQuality] = useState(2); // index into QUALITY_LABELS
    const [notification, setNotification] = useState("dashboard");

    const handleCreate = () => {
        if (!description.trim()) return;
        onCreate({
            description: description.trim(),
            quality: QUALITY_LABELS[quality].iterations,
            notification,
        });
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
            <div className="relative w-full max-w-lg mx-4 glass-card p-8 animate-[fadeIn_0.3s_ease-out]">
                <h2 className="text-xl font-bold text-white mb-2">Create a New Task</h2>
                <p className="text-sm text-[var(--color-rune-dim)] mb-6">
                    Tell your AI what to do. It'll work on it step by step.
                </p>

                {/* Task description */}
                <div className="mb-6">
                    <label className="text-xs text-[var(--color-rune-dim)] mb-2 block">What do you want your AI to do?</label>
                    <textarea
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Write a blog post about our company rebrand..."
                        rows={3}
                        className="w-full px-4 py-3 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)] resize-none"
                    />
                </div>

                {/* Quality slider */}
                <div className="mb-6">
                    <label className="text-xs text-[var(--color-rune-dim)] mb-3 block">How important is quality vs speed?</label>
                    <div className="px-2">
                        <input
                            type="range"
                            min={0}
                            max={4}
                            value={quality}
                            onChange={(e) => setQuality(Number(e.target.value))}
                            className="w-full accent-[var(--color-neon)]"
                        />
                        <div className="flex justify-between mt-1">
                            <span className="text-xs text-[var(--color-rune-dim)]">Speed<br /><span className="text-[10px]">Fewer checks, faster</span></span>
                            <span className="text-xs text-[var(--color-rune-dim)] text-right">Quality<br /><span className="text-[10px]">More checking, better</span></span>
                        </div>
                    </div>
                </div>

                {/* Notification preference */}
                <div className="mb-6">
                    <label className="text-xs text-[var(--color-rune-dim)] mb-2 block">If the AI gets stuck, how should it tell you?</label>
                    <div className="space-y-2">
                        {NOTIFICATION_OPTIONS.map((opt) => (
                            <button
                                key={opt.id}
                                onClick={() => setNotification(opt.id)}
                                className="w-full text-left flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all text-sm"
                                style={{
                                    background: notification === opt.id ? "var(--color-neon-glow)" : "var(--color-glass)",
                                    color: notification === opt.id ? "var(--color-neon)" : "var(--color-rune)",
                                    border: `1px solid ${notification === opt.id ? "var(--color-neon)" : "var(--color-glass-border)"}`,
                                }}
                            >
                                <span>{opt.icon}</span>
                                <span>{opt.label}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Actions */}
                <div className="flex justify-between">
                    <button onClick={onClose} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">
                        Cancel
                    </button>
                    <button
                        onClick={handleCreate}
                        disabled={!description.trim()}
                        className="btn-neon px-6 py-2 text-sm"
                        style={{ opacity: description.trim() ? 1 : 0.4 }}
                    >
                        Start Task →
                    </button>
                </div>
            </div>
        </div>
    );
}

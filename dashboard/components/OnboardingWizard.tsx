"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "../lib/api";

const SPECIES_OPTIONS = [
    { id: "cat", emoji: "🐱", label: "Cat" },
    { id: "dog", emoji: "🐶", label: "Dog" },
    { id: "penguin", emoji: "🐧", label: "Penguin" },
    { id: "fox", emoji: "🦊", label: "Fox" },
    { id: "owl", emoji: "🦉", label: "Owl" },
    { id: "dragon", emoji: "🐉", label: "Dragon" },
];

const STYLE_OPTIONS = [
    { id: "analytical", emoji: "🎯", label: "Analytical", desc: "Data-driven, precise, sees the patterns" },
    { id: "creative", emoji: "🎨", label: "Creative", desc: "Imaginative, lateral thinker, sees possibilities" },
    { id: "direct", emoji: "⚡", label: "Direct", desc: "No-nonsense, efficient, gets to the point" },
    { id: "warm", emoji: "🌿", label: "Warm", desc: "Empathetic, supportive, reads the room" },
];

export default function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
    const [step, setStep] = useState(0);
    const [userName, setUserName] = useState("");

    // The Companion IS the AI — one entity
    const [species, setSpecies] = useState("fox");
    const [name, setName] = useState("Ember");
    const [style, setStyle] = useState("warm");

    const [hardware, setHardware] = useState({ device: "Detecting...", gpu: "Detecting...", vram: "—", ram: "—" });
    const [recommended, setRecommended] = useState({ emoji: "⚡", name: "Smart & Fast", model: "Llama 3.1, 8B" });

    useEffect(() => {
        (async () => {
            try {
                const tauriInvoke = (window as any).__TAURI__?.core?.invoke;
                if (tauriInvoke) {
                    const info = await tauriInvoke("get_system_info");
                    const vram = info.vram_gb || 0;
                    setHardware({ device: `${info.os} (${info.arch})`, gpu: info.gpu || "Unknown", vram: `${vram}GB`, ram: `${info.ram_gb}GB` });
                    if (vram >= 20) setRecommended({ emoji: "🧠", name: "Deep Thinker", model: "35B — Requires 24GB+ VRAM" });
                    else if (vram >= 8) setRecommended({ emoji: "⚡", name: "Smart & Fast", model: "8B — Requires 10GB+ VRAM" });
                    else setRecommended({ emoji: "🌙", name: "Cloud Expert", model: "Cloud — No VRAM required" });
                    return;
                }
            } catch { /* Tauri not available */ }

            try {
                const res = await fetch(`${API_BASE}/api/v1/brains/available`);
                if (res.ok) {
                    const data = await res.json();
                    const vram = data.vram_gb || 0;
                    const runtime = data.detected_runtime || "unknown";
                    const deviceName = runtime === "omlx" ? "Apple Silicon Mac" : runtime === "llamacpp" ? "NVIDIA GPU System" : "PC";
                    const gpuName = runtime === "omlx" ? `Apple Silicon (${vram}GB unified)` : runtime === "llamacpp" ? `NVIDIA GPU (${vram}GB VRAM)` : "Unknown GPU";
                    setHardware({ device: deviceName, gpu: gpuName, vram: `${vram}GB`, ram: `${vram}GB` });
                    if (vram >= 20) setRecommended({ emoji: "🧠", name: "Deep Thinker", model: "35B — Requires 24GB+ VRAM" });
                    else if (vram >= 8) setRecommended({ emoji: "⚡", name: "Smart & Fast", model: "8B — Requires 10GB+ VRAM" });
                    else setRecommended({ emoji: "🌙", name: "Cloud Expert", model: "Cloud — No VRAM required" });
                    return;
                }
            } catch { /* Backend not running */ }

            const plat = navigator?.platform || "";
            const isMac = plat.includes("Mac");
            setHardware({ device: isMac ? "Mac" : "PC", gpu: "Could not detect GPU (backend offline)", vram: "Unknown", ram: "Unknown" });
            setRecommended({ emoji: "⚡", name: "Smart & Fast", model: "8B — Requires 10GB+ VRAM" });
        })();
    }, []);

    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === "Escape" && step > 0) setStep((s) => s - 1);
        };
        window.addEventListener("keydown", handleEscape);
        return () => window.removeEventListener("keydown", handleEscape);
    }, [step]);

    const finish = () => {
        localStorage.setItem("fireside_onboarded", "1");
        if (userName) localStorage.setItem("fireside_user_name", userName);
        const finalName = name || "Ember";
        localStorage.setItem("fireside_companion_species", species);
        localStorage.setItem("fireside_companion_name", finalName);
        localStorage.setItem("fireside_companion", JSON.stringify({ name: finalName, species }));
        localStorage.setItem("fireside_agent_name", finalName);
        localStorage.setItem("fireside_agent_style", style);
        const vramStr = hardware.vram.replace("GB", "").replace("Unknown", "0");
        const vramNum = parseFloat(vramStr) || 0;
        localStorage.setItem("fireside_vram", vramNum.toString());
        const brainId = vramNum >= 20 ? "deep" : "fast";
        localStorage.setItem("fireside_brain", brainId);
        localStorage.setItem("fireside_model", brainId === "deep" ? "qwen-2.5-35b-q4" : "llama-3.1-8b-q6");
        onComplete();
    };

    const displayName = name || "Ember";
    const speciesEmoji = SPECIES_OPTIONS.find((s) => s.id === species)?.emoji || "🦊";

    const screens = [
        /* ── 0: Welcome ── */
        <div key="welcome" className="text-center py-8">
            <div className="text-5xl mb-6">🔥</div>
            <h2 className="text-2xl font-bold text-white mb-3">Welcome to Fireside</h2>
            <p className="text-[var(--color-rune-dim)] mb-1">Your own AI companion that runs on this computer,</p>
            <p className="text-[var(--color-rune-dim)] mb-8">learns from your work, and never forgets.</p>
            <p className="text-sm text-[var(--color-rune-dim)] mb-8">Get ready to adopt. Takes about 2 minutes.</p>
            <button onClick={() => setStep(1)} className="btn-neon px-8 py-3 text-base">Get Started →</button>
        </div>,

        /* ── 1: Adopt Companion (species + name + style) ── */
        <div key="companion" className="py-6">
            <h2 className="text-xl font-bold text-white mb-2">Adopt your Companion</h2>
            <p className="text-sm text-[var(--color-rune-dim)] mb-4">Choose their form and shape their personality.</p>

            <div className="grid grid-cols-3 gap-2 mb-4" role="radiogroup" aria-label="Companion species">
                {SPECIES_OPTIONS.map((opt) => (
                    <button key={opt.id} onClick={() => setSpecies(opt.id)} role="radio" aria-checked={species === opt.id} tabIndex={0}
                        className="glass-card p-2 text-center transition-all"
                        style={{ borderColor: species === opt.id ? "var(--color-neon)" : "var(--color-glass-border)", borderWidth: species === opt.id ? 2 : 1 }}>
                        <div className="text-2xl mb-1">{opt.emoji}</div>
                        <div className="text-[10px] text-white font-medium uppercase tracking-wider">{opt.label}</div>
                    </button>
                ))}
            </div>

            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name your companion... (e.g. Ember)"
                className="w-full px-4 py-3 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)] mb-5" />

            <label className="text-xs text-[var(--color-rune-dim)] block mb-2">What&apos;s {displayName}&apos;s style?</label>
            <div className="grid grid-cols-2 gap-2 mb-6" role="radiogroup" aria-label="Companion style">
                {STYLE_OPTIONS.map((opt) => (
                    <button key={opt.id} onClick={() => setStyle(opt.id)} role="radio" aria-checked={style === opt.id} tabIndex={0}
                        className="glass-card p-3 text-left transition-all"
                        style={{ borderColor: style === opt.id ? "var(--color-neon)" : "var(--color-glass-border)", borderWidth: style === opt.id ? 2 : 1 }}>
                        <div className="text-lg mb-0.5">{opt.emoji}</div>
                        <div className="text-xs text-white font-semibold">{opt.label}</div>
                    </button>
                ))}
            </div>

            <div className="flex justify-between">
                <button onClick={() => setStep(0)} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">← Back</button>
                <button onClick={() => setStep(2)} className="btn-neon px-6 py-2 text-sm">Next →</button>
            </div>
        </div>,

        /* ── 2: Brain (auto-detected) ── */
        <div key="brain" className="py-6">
            <h2 className="text-xl font-bold text-white mb-2">Now give {displayName} a brain</h2>
            <p className="text-sm text-[var(--color-rune-dim)] mb-6">We checked your computer to find the best fit:</p>
            <div className="glass-card p-4 mb-4">
                <div className="flex items-center gap-3 mb-2">
                    <span className="text-lg">💻</span>
                    <span className="text-white font-medium">{hardware.device}</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-lg">🧠</span>
                    <span className="text-[var(--color-rune)]">{hardware.gpu} — {hardware.vram} AI Memory</span>
                </div>
            </div>
            <div className="glass-card p-4 mb-4" style={{ borderColor: "var(--color-neon)", borderWidth: 1 }}>
                <p className="text-xs text-[var(--color-rune-dim)] mb-1">Recommended brain for {displayName}:</p>
                <div className="flex items-center gap-2 mb-1">
                    <span>{recommended.emoji}</span>
                    <span className="text-white font-semibold">{recommended.name}</span>
                    <span className="text-xs text-[var(--color-rune-dim)]">({recommended.model})</span>
                </div>
                <p className="text-sm text-[var(--color-neon)] mt-2">✅ This works great with your computer.</p>
            </div>
            <div className="flex justify-between">
                <button onClick={() => setStep(1)} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">← Back</button>
                <button onClick={() => setStep(3)} className="btn-neon px-6 py-2 text-sm">Use this brain →</button>
            </div>
        </div>,

        /* ── 3: About You ── */
        <div key="about" className="py-6">
            <h2 className="text-xl font-bold text-white mb-2">Tell {displayName} about you</h2>
            <p className="text-sm text-[var(--color-rune-dim)] mb-6">Your companion will use this to personalize their help.</p>
            <label className="text-xs text-[var(--color-rune-dim)] block mb-1">Your name</label>
            <input value={userName} onChange={(e) => setUserName(e.target.value)} placeholder="How should they address you?" autoFocus
                className="w-full px-4 py-3 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)] mb-8" />
            <div className="flex justify-between">
                <button onClick={() => setStep(2)} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">← Back</button>
                <button onClick={() => setStep(4)} className="btn-neon px-6 py-2 text-sm">Next →</button>
            </div>
        </div>,

        /* ── 4: All Set ── */
        <div key="ready" className="text-center py-8">
            <div className="text-5xl mb-4">🔥</div>
            <h2 className="text-2xl font-bold text-white mb-4">You&apos;re all set{userName ? `, ${userName}` : ""}!</h2>
            <div className="glass-card p-5 mb-6 text-left" style={{ borderColor: "var(--color-neon)", borderWidth: 1 }}>
                <div className="flex items-center gap-3 mb-3 pb-3 border-b border-[var(--color-glass-border)]">
                    <span className="text-sm text-[var(--color-rune-dim)]">Companion:</span>
                    <span className="text-white font-semibold">{speciesEmoji} {displayName}</span>
                    <span className="text-xs text-[var(--color-rune-dim)]">({STYLE_OPTIONS.find(s => s.id === style)?.label})</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-sm text-[var(--color-rune-dim)]">Brain:</span>
                    <span className="text-white font-semibold">{recommended.emoji} {recommended.name}</span>
                </div>
            </div>
            <div className="glass-card p-4 mb-6 text-left" style={{ background: "rgba(245,158,11,0.06)" }}>
                <p className="text-xs text-[var(--color-rune-dim)] font-semibold mb-2">Things to try:</p>
                <p className="text-sm text-[var(--color-rune)] mb-1">1. Start a pipeline — ask {displayName} to &quot;Research competitors&quot;</p>
                <p className="text-sm text-[var(--color-rune)] mb-1">2. Chat with {displayName} from the dashboard</p>
                <p className="text-sm text-[var(--color-rune)] mb-1">3. 📱 Download the <strong>Fireside</strong> app — {displayName} goes with you</p>
            </div>
            <p className="text-sm text-[var(--color-rune-dim)] mb-6">One companion, everywhere. Desktop power, pocket convenience. 🔥</p>
            <button onClick={finish} className="btn-neon px-8 py-3 text-base">Open Dashboard →</button>
        </div>,
    ];

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-md" />
            <div className="relative w-full max-w-md mx-4">
                <div className="flex gap-1.5 mb-4 justify-center" role="progressbar" aria-valuenow={step} aria-valuemin={0} aria-valuemax={screens.length - 1} aria-label={`Step ${step + 1} of ${screens.length}`}>
                    {screens.map((_, i) => (
                        <div key={i} className="h-1 rounded-full transition-all"
                            style={{ width: 40, background: i <= step ? "var(--color-neon)" : "var(--color-glass-border)" }} />
                    ))}
                </div>
                <div className="glass-card p-8 animate-[fadeIn_0.3s_ease-out]">
                    {screens[step]}
                </div>
            </div>
        </div>
    );
}

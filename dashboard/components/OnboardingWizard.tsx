"use client";

import { useState, useEffect } from "react";

const PERSONALITY_OPTIONS = [
    { id: "friendly", emoji: "😊", label: "Friendly", desc: "Warm, chatty, uses emoji" },
    { id: "formal", emoji: "💼", label: "Formal", desc: "Polite, proper, no slang" },
    { id: "direct", emoji: "⚡", label: "Direct", desc: "Short, no fluff, gets to the point" },
];

const SPECIES_OPTIONS = [
    { id: "cat", emoji: "🐱", label: "Cat" },
    { id: "dog", emoji: "🐶", label: "Dog" },
    { id: "penguin", emoji: "🐧", label: "Penguin" },
    { id: "fox", emoji: "🦊", label: "Fox" },
    { id: "owl", emoji: "🦉", label: "Owl" },
    { id: "dragon", emoji: "🐉", label: "Dragon" },
];

/** Sprint 10: AI agent style options */
const AI_STYLE_OPTIONS = [
    { id: "analytical", emoji: "🎯", label: "Analytical", desc: "Data-driven, precise, sees the patterns" },
    { id: "creative", emoji: "🎨", label: "Creative", desc: "Imaginative, lateral thinker, sees possibilities" },
    { id: "direct", emoji: "⚡", label: "Direct", desc: "No-nonsense, efficient, gets to the point" },
    { id: "warm", emoji: "🌿", label: "Warm", desc: "Empathetic, supportive, reads the room" },
];

export default function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
    const [step, setStep] = useState(0);
    const [userName, setUserName] = useState("");
    const [personality, setPersonality] = useState("friendly");
    const [companionSpecies, setCompanionSpecies] = useState("fox");
    const [companionName, setCompanionName] = useState("");
    // Sprint 10: AI agent
    const [agentName, setAgentName] = useState("Atlas");
    const [agentStyle, setAgentStyle] = useState("analytical");
    const [hardware, setHardware] = useState({ device: "Detecting...", gpu: "Detecting...", vram: "—", ram: "—" });
    const [recommended, setRecommended] = useState({ emoji: "⚡", name: "Smart & Fast", model: "Llama 3.1, 8B" });

    useEffect(() => {
        // Detect hardware via backend API
        (async () => {
            try {
                const res = await fetch("http://127.0.0.1:8765/api/v1/brains/available");
                if (res.ok) {
                    const data = await res.json();
                    const vram = data.vram_gb || 0;
                    const runtime = data.detected_runtime || "unknown";
                    const deviceName = runtime === "omlx" ? "Apple Silicon Mac" : runtime === "llamacpp" ? "NVIDIA GPU System" : "Cloud Only";
                    const gpuName = runtime === "omlx" ? `Apple Silicon (${vram}GB unified)` : runtime === "llamacpp" ? `NVIDIA GPU (${vram}GB VRAM)` : "No local GPU";
                    setHardware({ device: deviceName, gpu: gpuName, vram: `${vram}GB`, ram: `${vram}GB` });
                    if (vram >= 48) {
                        setRecommended({ emoji: "🧠", name: "Deep Thinker", model: "35B model" });
                    } else if (vram >= 16) {
                        setRecommended({ emoji: "⚡", name: "Smart & Fast", model: "8B model" });
                    } else {
                        setRecommended({ emoji: "💨", name: "Compact", model: "3B model" });
                    }
                }
            } catch {
                const plat = navigator?.platform || "";
                const isMac = plat.includes("Mac");
                const mem = (navigator as unknown as { deviceMemory?: number }).deviceMemory;
                setHardware({
                    device: isMac ? "Mac" : "PC",
                    gpu: isMac ? "Apple Silicon" : "Unknown",
                    vram: mem ? `${mem}GB` : "Unknown",
                    ram: mem ? `${mem}GB` : "Unknown",
                });
            }
        })();
    }, []);

    // Escape key to go back
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
        localStorage.setItem("fireside_personality", personality);
        localStorage.setItem("fireside_companion_species", companionSpecies);
        localStorage.setItem("fireside_companion_name", companionName || "Ember");
        // Sprint 10: Save AI agent info
        localStorage.setItem("fireside_agent_name", agentName || "Atlas");
        localStorage.setItem("fireside_agent_style", agentStyle);
        onComplete();
    };

    const speciesEmoji = SPECIES_OPTIONS.find((s) => s.id === companionSpecies)?.emoji || "🦊";
    const displayCompanionName = companionName || "Ember";
    const displayAgentName = agentName || "Atlas";

    const screens = [
        // 0: Welcome
        <div key="welcome" className="text-center py-8">
            <div className="text-5xl mb-6">🔥</div>
            <h2 className="text-2xl font-bold text-white mb-3">Welcome to Fireside</h2>
            <p className="text-[var(--color-rune-dim)] mb-1">Your own AI that runs on this computer,</p>
            <p className="text-[var(--color-rune-dim)] mb-8">learns from your work, and never forgets.</p>
            <p className="text-sm text-[var(--color-rune-dim)] mb-8">Let&apos;s set it up. Takes about 2 minutes.</p>
            <button onClick={() => setStep(1)} className="btn-neon px-8 py-3 text-base">
                Get Started →
            </button>
        </div>,

        // 1: Your Name
        <div key="name" className="py-6">
            <h2 className="text-xl font-bold text-white mb-2">What&apos;s your name?</h2>
            <p className="text-sm text-[var(--color-rune-dim)] mb-6">Your AI will use this to personalize conversations with you.</p>
            <input
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                placeholder="Your name..."
                autoFocus
                className="w-full px-4 py-3 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-base outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)] mb-8"
            />
            <div className="flex justify-between">
                <button onClick={() => setStep(0)} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">← Back</button>
                <button onClick={() => setStep(2)} className="btn-neon px-6 py-2 text-sm">Next →</button>
            </div>
        </div>,

        // 2: Choose Companion
        <div key="companion" className="py-6">
            <h2 className="text-xl font-bold text-white mb-2">Choose a companion for your journey</h2>
            <p className="text-sm text-[var(--color-rune-dim)] mb-4">Every journey starts with a friend. This one goes with you on your phone.</p>
            <div className="grid grid-cols-3 gap-3 mb-4" role="radiogroup" aria-label="Companion species">
                {SPECIES_OPTIONS.map((opt) => (
                    <button
                        key={opt.id}
                        onClick={() => setCompanionSpecies(opt.id)}
                        role="radio"
                        aria-checked={companionSpecies === opt.id}
                        tabIndex={0}
                        className="glass-card p-3 text-center transition-all"
                        style={{
                            borderColor: companionSpecies === opt.id ? "var(--color-neon)" : "var(--color-glass-border)",
                            borderWidth: companionSpecies === opt.id ? 2 : 1,
                        }}
                    >
                        <div className="text-3xl mb-1">{opt.emoji}</div>
                        <div className="text-xs text-white font-medium">{opt.label}</div>
                    </button>
                ))}
            </div>
            <input
                value={companionName}
                onChange={(e) => setCompanionName(e.target.value)}
                placeholder={`Name your ${SPECIES_OPTIONS.find(s => s.id === companionSpecies)?.label || "companion"}... (default: Ember)`}
                className="w-full px-4 py-3 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)] mb-6"
            />
            <div className="flex justify-between">
                <button onClick={() => setStep(1)} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">← Back</button>
                <button onClick={() => setStep(3)} className="btn-neon px-6 py-2 text-sm">Next →</button>
            </div>
        </div>,

        // 3: AI Brain (auto-detected)
        <div key="brain" className="py-6">
            <h2 className="text-xl font-bold text-white mb-2">We checked your computer</h2>
            <p className="text-sm text-[var(--color-rune-dim)] mb-6">Here&apos;s what we found:</p>
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
                <p className="text-xs text-[var(--color-rune-dim)] mb-1">Recommended brain:</p>
                <div className="flex items-center gap-2 mb-1">
                    <span>{recommended.emoji}</span>
                    <span className="text-white font-semibold">{recommended.name}</span>
                    <span className="text-xs text-[var(--color-rune-dim)]">({recommended.model})</span>
                </div>
                <p className="text-sm text-[var(--color-rune-dim)]">Perfect for everyday questions and tasks.</p>
                <p className="text-sm text-[var(--color-neon)] mt-2">✅ This works great with your computer.</p>
            </div>
            <div className="flex justify-between">
                <button onClick={() => setStep(2)} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">← Back</button>
                <button onClick={() => setStep(4)} className="btn-neon px-6 py-2 text-sm">Use this brain →</button>
            </div>
        </div>,

        // 4: Create Your AI (Sprint 10 — NEW)
        <div key="agent" className="py-6">
            <h2 className="text-xl font-bold text-white mb-2">Now, who&apos;s running the show at home?</h2>
            <p className="text-sm text-[var(--color-rune-dim)] mb-1">Every companion has someone at the fireside.</p>
            <p className="text-sm text-[var(--color-rune-dim)] mb-6">This is the mind behind {displayCompanionName} — your AI.</p>

            <label className="text-xs text-[var(--color-rune-dim)] block mb-1">Give your AI a name:</label>
            <input
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder="Atlas"
                className="w-full px-4 py-3 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-base outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)] mb-6"
            />

            <label className="text-xs text-[var(--color-rune-dim)] block mb-2">What&apos;s their style?</label>
            <div className="grid grid-cols-2 gap-3 mb-6" role="radiogroup" aria-label="AI agent style">
                {AI_STYLE_OPTIONS.map((opt) => (
                    <button
                        key={opt.id}
                        onClick={() => setAgentStyle(opt.id)}
                        role="radio"
                        aria-checked={agentStyle === opt.id}
                        tabIndex={0}
                        className="glass-card p-4 text-left transition-all"
                        style={{
                            borderColor: agentStyle === opt.id ? "var(--color-neon)" : "var(--color-glass-border)",
                            borderWidth: agentStyle === opt.id ? 2 : 1,
                        }}
                    >
                        <div className="text-xl mb-1">{opt.emoji}</div>
                        <div className="text-sm text-white font-semibold mb-0.5">{opt.label}</div>
                        <div className="text-xs text-[var(--color-rune-dim)]">{opt.desc}</div>
                    </button>
                ))}
            </div>

            <div className="flex justify-between">
                <button onClick={() => setStep(3)} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">← Back</button>
                <button onClick={() => setStep(5)} className="btn-neon px-6 py-2 text-sm">Next →</button>
            </div>
        </div>,

        // 5: Confirmation (Sprint 10: shows both characters)
        <div key="ready" className="text-center py-8">
            <div className="text-5xl mb-4">🔥</div>
            <h2 className="text-2xl font-bold text-white mb-4">
                You&apos;re all set{userName ? `, ${userName}` : ""}!
            </h2>

            <div className="glass-card p-5 mb-6 text-left" style={{ borderColor: "var(--color-neon)", borderWidth: 1 }}>
                <div className="flex items-center gap-3 mb-3 pb-3 border-b border-[var(--color-glass-border)]">
                    <span className="text-sm text-[var(--color-rune-dim)]">Owner:</span>
                    <span className="text-white font-semibold">{userName || "You"}</span>
                </div>
                <div className="flex items-center gap-3 mb-3 pb-3 border-b border-[var(--color-glass-border)]">
                    <span className="text-sm text-[var(--color-rune-dim)]">AI:</span>
                    <span className="text-white font-semibold">{displayAgentName}</span>
                    <span className="text-xs text-[var(--color-rune-dim)]">({AI_STYLE_OPTIONS.find(s => s.id === agentStyle)?.emoji} {AI_STYLE_OPTIONS.find(s => s.id === agentStyle)?.label})</span>
                </div>
                <div className="flex items-center gap-3 mb-3 pb-3 border-b border-[var(--color-glass-border)]">
                    <span className="text-sm text-[var(--color-rune-dim)]">Companion:</span>
                    <span className="text-white font-semibold">{speciesEmoji} {displayCompanionName}</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-sm text-[var(--color-rune-dim)]">Brain:</span>
                    <span className="text-white font-semibold">{recommended.emoji} {recommended.name}</span>
                </div>
            </div>

            <p className="text-sm text-[var(--color-rune-dim)] mb-6">
                {displayAgentName} stays home. {displayCompanionName} goes with you. 🔥
            </p>
            <button onClick={finish} className="btn-neon px-8 py-3 text-base">
                {displayAgentName} and {displayCompanionName} are ready →
            </button>
        </div>,
    ];

    // Progress bar
    const totalSteps = screens.length;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-md" />
            <div className="relative w-full max-w-md mx-4">
                {/* Progress */}
                <div className="flex gap-1.5 mb-4 justify-center" role="progressbar" aria-valuenow={step} aria-valuemin={0} aria-valuemax={totalSteps - 1} aria-label={`Step ${step + 1} of ${totalSteps}`}>
                    {screens.map((_, i) => (
                        <div
                            key={i}
                            className="h-1 rounded-full transition-all"
                            style={{
                                width: 40,
                                background: i <= step ? "var(--color-neon)" : "var(--color-glass-border)",
                            }}
                        />
                    ))}
                </div>
                <div className="glass-card p-8 animate-[fadeIn_0.3s_ease-out]">
                    {screens[step]}
                </div>
            </div>
        </div>
    );
}

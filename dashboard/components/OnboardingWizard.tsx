"use client";

import { useState, useEffect } from "react";

const PERSONALITY_OPTIONS = [
    { id: "friendly", emoji: "😊", label: "Friendly", desc: "Warm, chatty, uses emoji" },
    { id: "formal", emoji: "💼", label: "Formal", desc: "Polite, proper, no slang" },
    { id: "direct", emoji: "⚡", label: "Direct", desc: "Short, no fluff, gets to the point" },
];

export default function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
    const [step, setStep] = useState(0);
    const [userName, setUserName] = useState("");
    const [personality, setPersonality] = useState("friendly");
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
                    // Auto-recommend based on VRAM
                    if (vram >= 48) {
                        setRecommended({ emoji: "🧠", name: "Deep Thinker", model: "35B model" });
                    } else if (vram >= 16) {
                        setRecommended({ emoji: "⚡", name: "Smart & Fast", model: "8B model" });
                    } else {
                        setRecommended({ emoji: "💨", name: "Compact", model: "3B model" });
                    }
                }
            } catch {
                // Fallback: detect from browser
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

    // Escape key to close
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
        onComplete();
    };

    const screens = [
        // 0: Welcome
        <div key="welcome" className="text-center py-8">
            <div className="text-5xl mb-6">⚡</div>
            <h2 className="text-2xl font-bold text-white mb-3">Welcome to Fireside</h2>
            <p className="text-[var(--color-rune-dim)] mb-1">Your own AI assistant that runs on this computer,</p>
            <p className="text-[var(--color-rune-dim)] mb-8">learns from your work, and never forgets.</p>
            <p className="text-sm text-[var(--color-rune-dim)] mb-8">Let&apos;s set it up. Takes about 2 minutes.</p>
            <button onClick={() => setStep(1)} className="btn-neon px-8 py-3 text-base">
                Get Started →
            </button>
        </div>,

        // 1: Name
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

        // 2: AI Brain (auto-detected)
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
                <button onClick={() => setStep(1)} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">← Back</button>
                <button onClick={() => setStep(3)} className="btn-neon px-6 py-2 text-sm">Use this brain →</button>
            </div>
        </div>,

        // 3: Personality
        <div key="personality" className="py-6">
            <h2 className="text-xl font-bold text-white mb-2">How should your AI talk to you?</h2>
            <p className="text-sm text-[var(--color-rune-dim)] mb-6">You can change this anytime in Personality.</p>
            <div className="grid grid-cols-3 gap-3 mb-8" role="radiogroup" aria-label="Personality style">
                {PERSONALITY_OPTIONS.map((opt) => (
                    <button
                        key={opt.id}
                        onClick={() => setPersonality(opt.id)}
                        role="radio"
                        aria-checked={personality === opt.id}
                        tabIndex={0}
                        className="glass-card p-4 text-center transition-all"
                        style={{
                            borderColor: personality === opt.id ? "var(--color-neon)" : "var(--color-glass-border)",
                            borderWidth: personality === opt.id ? 2 : 1,
                        }}
                    >
                        <div className="text-3xl mb-2">{opt.emoji}</div>
                        <div className="text-sm text-white font-semibold mb-1">{opt.label}</div>
                        <div className="text-xs text-[var(--color-rune-dim)]">{opt.desc}</div>
                    </button>
                ))}
            </div>
            <div className="flex justify-between">
                <button onClick={() => setStep(2)} className="text-sm text-[var(--color-rune-dim)] hover:text-white transition-colors">← Back</button>
                <button onClick={() => setStep(4)} className="btn-neon px-6 py-2 text-sm">Next →</button>
            </div>
        </div>,

        // 4: Ready
        <div key="ready" className="text-center py-8">
            <div className="text-5xl mb-6">✅</div>
            <h2 className="text-2xl font-bold text-white mb-3">
                You&apos;re all set{userName ? `, ${userName}` : ""}!
            </h2>
            <p className="text-[var(--color-rune-dim)] mb-1">
                Your AI is named <span className="text-white font-semibold">Odin</span>.
                It&apos;s <span className="text-white font-semibold">{PERSONALITY_OPTIONS.find(p => p.id === personality)?.label}</span>,
                runs the <span className="text-white font-semibold">{recommended.name}</span> brain,
            </p>
            <p className="text-[var(--color-rune-dim)] mb-8">and it&apos;s ready to help.</p>
            <p className="text-sm text-[var(--color-rune-dim)] mb-6">It&apos;ll get smarter every day as it learns how you work.</p>
            <button onClick={finish} className="btn-neon px-8 py-3 text-base">
                Start chatting →
            </button>
            <p className="text-xs text-[var(--color-rune-dim)] mt-6">
                💡 Tip: Try asking &quot;What can you help me with?&quot;
            </p>
        </div>,
    ];

    // Progress bar
    const progress = step / 4;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-md" />
            <div className="relative w-full max-w-md mx-4">
                {/* Progress */}
                <div className="flex gap-1.5 mb-4 justify-center" role="progressbar" aria-valuenow={step} aria-valuemin={0} aria-valuemax={4} aria-label={`Step ${step + 1} of 5`}>
                    {[0, 1, 2, 3, 4].map((i) => (
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

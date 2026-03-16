"use client";

/**
 * 🔥 Installer Wizard — Sprint 13.
 *
 * The FIRST thing every user sees. 7 premium steps:
 * Welcome → System Check → Choose Companion → Create AI → Confirm → Installing → Success
 *
 * Calls Thor's Tauri commands for actual system operations.
 * Designed for 1280×800 Tauri window. Fire amber palette.
 */
import { useState, useEffect, useCallback } from "react";

// ---------- Types ----------------------------------------------------------

interface SystemInfo {
    os: string;
    arch: string;
    ram_gb: number;
    gpu: string;
    vram_gb: number;
}

interface InstallerConfig {
    userName: string;
    companionSpecies: string;
    companionName: string;
    agentName: string;
    agentStyle: string;
    brainSize: string;
    brainModel: string;
}

type Step = 0 | 1 | 2 | 3 | 4 | 5 | 6;

const SPECIES = [
    { id: "cat", emoji: "🐱", label: "Cat" },
    { id: "dog", emoji: "🐶", label: "Dog" },
    { id: "penguin", emoji: "🐧", label: "Penguin" },
    { id: "fox", emoji: "🦊", label: "Fox" },
    { id: "owl", emoji: "🦉", label: "Owl" },
    { id: "dragon", emoji: "🐉", label: "Dragon" },
];

const STYLES = [
    { id: "analytical", emoji: "🎯", label: "Analytical", desc: "Data-driven, precise, sees patterns" },
    { id: "creative", emoji: "🎨", label: "Creative", desc: "Imaginative, lateral thinker" },
    { id: "direct", emoji: "⚡", label: "Direct", desc: "No-nonsense, efficient, to the point" },
    { id: "warm", emoji: "🌿", label: "Warm", desc: "Empathetic, supportive, reads the room" },
];

// ---------- Tauri Helpers --------------------------------------------------

async function tauriInvoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    if (w.__TAURI__) {
        const { invoke } = await import("@tauri-apps/api/core");
        return invoke<T>(cmd, args);
    }
    // Browser fallback — mock for development
    console.log(`[mock] invoke(${cmd})`, args);
    await new Promise((r) => setTimeout(r, 800));
    if (cmd === "get_system_info") return { os: "Windows 11", arch: "x86_64", ram_gb: 32, gpu: "NVIDIA RTX 4090", vram_gb: 24 } as T;
    if (cmd === "check_python") return "3.12.2" as T;
    if (cmd === "check_node") return "20.11.0" as T;
    return {} as T;
}

// ---------- Component ------------------------------------------------------

export default function InstallerWizard({ onComplete }: { onComplete: () => void }) {
    const [step, setStep] = useState<Step>(0);
    const [config, setConfig] = useState<InstallerConfig>({
        userName: "",
        companionSpecies: "fox",
        companionName: "Ember",
        agentName: "Atlas",
        agentStyle: "analytical",
        brainSize: "smart",
        brainModel: "7B",
    });
    const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
    const [sysChecks, setSysChecks] = useState<{ label: string; status: "pending" | "ok" | "fail"; value: string }[]>([]);
    const [installSteps, setInstallSteps] = useState<{ label: string; status: "pending" | "running" | "done" | "fail" }[]>([]);
    const [animClass, setAnimClass] = useState("installer-enter");

    const goTo = useCallback((s: Step) => {
        setAnimClass("installer-exit");
        setTimeout(() => {
            setStep(s);
            setAnimClass("installer-enter");
        }, 250);
    }, []);

    // ── Step 1: System Check (auto-run) ──
    useEffect(() => {
        if (step !== 1) return;
        const checks = [
            { label: "Operating System", status: "pending" as const, value: "" },
            { label: "Memory", status: "pending" as const, value: "" },
            { label: "Graphics", status: "pending" as const, value: "" },
        ];
        setSysChecks(checks);

        (async () => {
            const info = await tauriInvoke<SystemInfo>("get_system_info");
            setSysInfo(info);

            const update = (i: number, v: string) => {
                checks[i] = { ...checks[i], status: "ok", value: v };
                setSysChecks([...checks]);
            };
            await new Promise((r) => setTimeout(r, 400));
            update(0, `${info.os} (${info.arch})`);
            await new Promise((r) => setTimeout(r, 400));
            update(1, `${info.ram_gb}GB RAM`);
            await new Promise((r) => setTimeout(r, 400));
            update(2, info.gpu || "No GPU detected");

            // Auto-advance
            setTimeout(() => goTo(2), 1200);
        })();
    }, [step, goTo]);

    // ── Step 5: Installing ──
    useEffect(() => {
        if (step !== 5) return;
        const steps = [
            { label: "Checking Python", status: "pending" as const },
            { label: "Checking Node.js", status: "pending" as const },
            { label: "Setting up Fireside", status: "pending" as const },
            { label: "Installing packages", status: "pending" as const },
            { label: "Saving your preferences", status: "pending" as const },
        ];
        setInstallSteps(steps);

        (async () => {
            const run = async (i: number, fn: () => Promise<void>) => {
                steps[i] = { ...steps[i], status: "running" };
                setInstallSteps([...steps]);
                try {
                    await fn();
                    steps[i] = { ...steps[i], status: "done" };
                } catch {
                    steps[i] = { ...steps[i], status: "fail" };
                }
                setInstallSteps([...steps]);
            };

            await run(0, async () => {
                const py = await tauriInvoke<string | null>("check_python");
                if (!py) await tauriInvoke("install_python");
            });
            await run(1, async () => {
                const nd = await tauriInvoke<string | null>("check_node");
                if (!nd) await tauriInvoke("install_node");
            });
            await run(2, async () => {
                await tauriInvoke("clone_repo", { firesideDir: "~/.fireside" });
            });
            await run(3, async () => {
                await tauriInvoke("install_deps", { firesideDir: "~/.fireside" });
            });
            await run(4, async () => {
                await tauriInvoke("write_config", {
                    config: {
                        user_name: config.userName || "User",
                        agent_name: config.agentName,
                        agent_style: config.agentStyle,
                        companion_species: config.companionSpecies,
                        companion_name: config.companionName,
                    },
                });
            });

            setTimeout(() => goTo(6), 800);
        })();
    }, [step, config, goTo]);

    const speciesEmoji = SPECIES.find((s) => s.id === config.companionSpecies)?.emoji || "🦊";

    // ── Shared progress bar ──
    const progress = ((step / 6) * 100);

    return (
        <div className="installer-root">
            <style>{installerCSS}</style>

            {/* Progress */}
            <div className="installer-progress">
                <div className="installer-progress-fill" style={{ width: `${progress}%` }} />
            </div>

            <div className={`installer-content ${animClass}`}>
                {/* Step 0: Welcome */}
                {step === 0 && (
                    <div className="installer-center">
                        <div className="installer-fire">🔥</div>
                        <h1 className="installer-brand">FIRESIDE</h1>
                        <p className="installer-tagline">The AI companion that learns while you sleep.</p>
                        <div className="installer-spacer" />
                        <button className="installer-btn-primary" onClick={() => goTo(1)}>
                            Get Started →
                        </button>
                    </div>
                )}

                {/* Step 1: System Check */}
                {step === 1 && (
                    <div className="installer-center">
                        <h2 className="installer-title">Checking your system...</h2>
                        <div className="installer-checks">
                            {sysChecks.map((c, i) => (
                                <div key={i} className="installer-check-row">
                                    <span className="installer-check-icon">
                                        {c.status === "pending" ? "⏳" : c.status === "ok" ? "✔" : "❌"}
                                    </span>
                                    <span className="installer-check-label">{c.label}</span>
                                    {c.value && <span className="installer-check-value">{c.value}</span>}
                                </div>
                            ))}
                        </div>
                        {sysInfo && (
                            <div className="installer-recommended">
                                <span>Recommended brain: </span>
                                <strong>
                                    {(sysInfo.vram_gb || 0) >= 48
                                        ? "🧠 Deep Thinker (35B)"
                                        : (sysInfo.vram_gb || 0) >= 16
                                            ? "⚡ Smart & Fast (7B)"
                                            : "💨 Compact (3B)"}
                                </strong>
                            </div>
                        )}
                    </div>
                )}

                {/* Step 2: Choose Companion */}
                {step === 2 && (
                    <div className="installer-center">
                        <h2 className="installer-title">Choose a companion for your journey</h2>
                        <p className="installer-subtitle">Every journey starts with a friend.</p>
                        <div className="installer-species-grid">
                            {SPECIES.map((s) => (
                                <button
                                    key={s.id}
                                    className={`installer-species-card ${config.companionSpecies === s.id ? "selected" : ""}`}
                                    onClick={() => setConfig((c) => ({ ...c, companionSpecies: s.id }))}
                                >
                                    <span className="installer-species-emoji">{s.emoji}</span>
                                    <span className="installer-species-label">{s.label}</span>
                                </button>
                            ))}
                        </div>
                        <input
                            className="installer-input"
                            value={config.companionName}
                            onChange={(e) => setConfig((c) => ({ ...c, companionName: e.target.value }))}
                            placeholder="Name your companion..."
                        />
                        <div className="installer-nav">
                            <button className="installer-btn-back" onClick={() => goTo(1)}>← Back</button>
                            <button className="installer-btn-primary" onClick={() => goTo(3)}>Next →</button>
                        </div>
                    </div>
                )}

                {/* Step 3: Create AI */}
                {step === 3 && (
                    <div className="installer-center">
                        <h2 className="installer-title">Every companion has someone at the fireside.</h2>
                        <p className="installer-subtitle">
                            This is the mind behind {config.companionName || "Ember"} — your AI.
                        </p>
                        <label className="installer-label">What should we call you?</label>
                        <input
                            className="installer-input"
                            value={config.userName}
                            onChange={(e) => setConfig((c) => ({ ...c, userName: e.target.value }))}
                            placeholder="Your name..."
                        />
                        <label className="installer-label">Give your AI a name:</label>
                        <input
                            className="installer-input"
                            value={config.agentName}
                            onChange={(e) => setConfig((c) => ({ ...c, agentName: e.target.value }))}
                            placeholder="Atlas"
                        />
                        <label className="installer-label">What&apos;s {config.agentName || "Atlas"}&apos;s style?</label>
                        <div className="installer-style-grid">
                            {STYLES.map((s) => (
                                <button
                                    key={s.id}
                                    className={`installer-style-card ${config.agentStyle === s.id ? "selected" : ""}`}
                                    onClick={() => setConfig((c) => ({ ...c, agentStyle: s.id }))}
                                >
                                    <span className="installer-style-emoji">{s.emoji}</span>
                                    <span className="installer-style-label">{s.label}</span>
                                    <span className="installer-style-desc">{s.desc}</span>
                                </button>
                            ))}
                        </div>
                        <div className="installer-nav">
                            <button className="installer-btn-back" onClick={() => goTo(2)}>← Back</button>
                            <button className="installer-btn-primary" onClick={() => goTo(4)}>Next →</button>
                        </div>
                    </div>
                )}

                {/* Step 4: Confirmation */}
                {step === 4 && (
                    <div className="installer-center">
                        <h2 className="installer-title">Ready to install.</h2>
                        <div className="installer-confirm-card">
                            <div className="installer-confirm-row">
                                <span className="installer-confirm-label">Owner</span>
                                <span className="installer-confirm-value">{config.userName || "You"}</span>
                            </div>
                            <div className="installer-confirm-divider" />
                            <div className="installer-confirm-row">
                                <span className="installer-confirm-label">AI</span>
                                <span className="installer-confirm-value">
                                    {config.agentName || "Atlas"} ({STYLES.find((s) => s.id === config.agentStyle)?.emoji})
                                </span>
                            </div>
                            <div className="installer-confirm-divider" />
                            <div className="installer-confirm-row">
                                <span className="installer-confirm-label">Companion</span>
                                <span className="installer-confirm-value">
                                    {speciesEmoji} {config.companionName || "Ember"}
                                </span>
                            </div>
                            <div className="installer-confirm-divider" />
                            <div className="installer-confirm-row">
                                <span className="installer-confirm-label">Brain</span>
                                <span className="installer-confirm-value">
                                    {sysInfo && (sysInfo.vram_gb || 0) >= 48
                                        ? "🧠 Deep Thinker (35B)"
                                        : sysInfo && (sysInfo.vram_gb || 0) >= 16
                                            ? "⚡ Smart & Fast (7B)"
                                            : "💨 Compact (3B)"}
                                </span>
                            </div>
                        </div>
                        <div className="installer-nav">
                            <button className="installer-btn-back" onClick={() => goTo(3)}>← Back</button>
                            <button className="installer-btn-install" onClick={() => goTo(5)}>
                                Install Fireside →
                            </button>
                        </div>
                    </div>
                )}

                {/* Step 5: Installing */}
                {step === 5 && (
                    <div className="installer-center">
                        <h2 className="installer-title">
                            {config.agentName || "Atlas"} and {config.companionName || "Ember"} are getting ready...
                        </h2>
                        <div className="installer-install-steps">
                            {installSteps.map((s, i) => (
                                <div key={i} className={`installer-install-row ${s.status}`}>
                                    <span className="installer-install-icon">
                                        {s.status === "pending" ? "○" : s.status === "running" ? "⏳" : s.status === "done" ? "✔" : "❌"}
                                    </span>
                                    <span className="installer-install-label">{s.label}</span>
                                </div>
                            ))}
                        </div>
                        <div className="installer-install-companion">
                            {speciesEmoji}
                        </div>
                    </div>
                )}

                {/* Step 6: Success */}
                {step === 6 && (
                    <div className="installer-center">
                        <div className="installer-success-fire">🔥</div>
                        <h2 className="installer-success-title">Fireside is live.</h2>
                        <p className="installer-success-subtitle">
                            {config.agentName || "Atlas"} is at the fireside.{"\n"}
                            {config.companionName || "Ember"} is by their side.
                        </p>
                        <div className="installer-success-scene">
                            <span className="installer-success-fire-emoji">🔥</span>
                            <span className="installer-success-companion">{speciesEmoji}</span>
                        </div>
                        <div className="installer-success-tips">
                            <p className="installer-success-tip-title">Things to try:</p>
                            <p className="installer-success-tip">1. Say &quot;Hello {config.companionName || "Ember"}!&quot;</p>
                            <p className="installer-success-tip">2. Ask &quot;Take me for a walk&quot;</p>
                            <p className="installer-success-tip">3. Say &quot;Remember: I like coffee black&quot;</p>
                        </div>
                        <button
                            className="installer-btn-primary"
                            onClick={() => {
                                localStorage.setItem("fireside_onboarded", "1");
                                if (config.userName) localStorage.setItem("fireside_user_name", config.userName);
                                localStorage.setItem("fireside_agent_name", config.agentName || "Atlas");
                                localStorage.setItem("fireside_agent_style", config.agentStyle);
                                localStorage.setItem("fireside_companion_species", config.companionSpecies);
                                localStorage.setItem("fireside_companion_name", config.companionName || "Ember");
                                onComplete();
                            }}
                        >
                            Open Dashboard →
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

// ---------- Embedded CSS (scoped to installer) ----------------------------

const installerCSS = `
  .installer-root {
    position: fixed; inset: 0; z-index: 9999;
    background: #0F0F0F;
    font-family: 'Inter', 'Outfit', -apple-system, sans-serif;
    color: #F0DCC8;
    display: flex; flex-direction: column;
    overflow: hidden;
  }

  /* Progress bar */
  .installer-progress { height: 3px; background: #1A1A1A; }
  .installer-progress-fill { height: 100%; background: linear-gradient(90deg, #D97706, #F59E0B); transition: width 0.4s ease; border-radius: 2px; }

  /* Animation */
  .installer-enter { animation: installerFadeIn 0.3s ease-out forwards; }
  .installer-exit { animation: installerFadeOut 0.2s ease-in forwards; }
  @keyframes installerFadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes installerFadeOut { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(-12px); } }

  /* Content */
  .installer-content { flex: 1; display: flex; align-items: center; justify-content: center; padding: 40px; }
  .installer-center { display: flex; flex-direction: column; align-items: center; max-width: 560px; width: 100%; }
  .installer-spacer { height: 40px; }

  /* Welcome */
  .installer-fire { font-size: 80px; margin-bottom: 16px; animation: fireGlow 2s ease-in-out infinite alternate; }
  @keyframes fireGlow { from { filter: brightness(0.9); } to { filter: brightness(1.2) drop-shadow(0 0 30px rgba(245,166,35,0.4)); } }
  .installer-brand { font-size: 48px; font-weight: 800; letter-spacing: 6px; background: linear-gradient(135deg, #F59E0B, #D97706, #92400E); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }
  .installer-tagline { font-size: 16px; color: #A08264; margin-bottom: 0; }

  /* Typography */
  .installer-title { font-size: 24px; font-weight: 700; color: #F0DCC8; text-align: center; margin-bottom: 8px; }
  .installer-subtitle { font-size: 14px; color: #A08264; text-align: center; margin-bottom: 24px; }
  .installer-label { font-size: 12px; color: #A08264; align-self: flex-start; margin-bottom: 6px; margin-top: 16px; }

  /* Inputs */
  .installer-input {
    width: 100%; padding: 12px 16px; border-radius: 10px;
    background: #1A1A1A; border: 1px solid #2A2A2A; color: #F0DCC8;
    font-size: 15px; outline: none; transition: border-color 0.2s;
  }
  .installer-input:focus { border-color: #D97706; }
  .installer-input::placeholder { color: #5A4A3A; }

  /* Buttons */
  .installer-btn-primary {
    padding: 14px 40px; border-radius: 12px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B); color: #0F0F0F;
    font-size: 16px; font-weight: 700; letter-spacing: 0.5px;
    box-shadow: 0 4px 20px rgba(245,158,11,0.3);
    transition: all 0.2s; margin-top: 24px;
  }
  .installer-btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 24px rgba(245,158,11,0.5); }
  .installer-btn-back { background: none; border: none; color: #A08264; font-size: 14px; cursor: pointer; padding: 10px 16px; }
  .installer-btn-back:hover { color: #F0DCC8; }
  .installer-btn-install {
    padding: 16px 48px; border-radius: 12px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B); color: #0F0F0F;
    font-size: 18px; font-weight: 800; letter-spacing: 0.5px;
    box-shadow: 0 4px 24px rgba(245,158,11,0.4);
    transition: all 0.2s; animation: installPulse 2s ease-in-out infinite;
  }
  @keyframes installPulse { 0%,100% { box-shadow: 0 4px 24px rgba(245,158,11,0.4); } 50% { box-shadow: 0 4px 36px rgba(245,158,11,0.7); } }
  .installer-btn-install:hover { transform: translateY(-2px); }
  .installer-nav { display: flex; justify-content: space-between; width: 100%; margin-top: 32px; align-items: center; }

  /* Species grid */
  .installer-species-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; width: 100%; margin-bottom: 20px; }
  .installer-species-card {
    display: flex; flex-direction: column; align-items: center; padding: 20px 12px;
    border-radius: 12px; border: 2px solid #2A2A2A; background: #1A1A1A;
    cursor: pointer; transition: all 0.2s;
  }
  .installer-species-card:hover { border-color: #5A4A3A; transform: translateY(-2px); }
  .installer-species-card.selected { border-color: #D97706; background: rgba(217,119,6,0.08); box-shadow: 0 0 20px rgba(217,119,6,0.2); }
  .installer-species-emoji { font-size: 36px; margin-bottom: 6px; }
  .installer-species-label { font-size: 13px; color: #F0DCC8; font-weight: 500; }

  /* Style grid */
  .installer-style-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; width: 100%; }
  .installer-style-card {
    display: flex; flex-direction: column; padding: 16px;
    border-radius: 12px; border: 2px solid #2A2A2A; background: #1A1A1A;
    cursor: pointer; transition: all 0.2s; text-align: left;
  }
  .installer-style-card:hover { border-color: #5A4A3A; }
  .installer-style-card.selected { border-color: #D97706; background: rgba(217,119,6,0.08); box-shadow: 0 0 20px rgba(217,119,6,0.2); }
  .installer-style-emoji { font-size: 24px; margin-bottom: 4px; }
  .installer-style-label { font-size: 14px; color: #F0DCC8; font-weight: 600; margin-bottom: 2px; }
  .installer-style-desc { font-size: 12px; color: #A08264; }

  /* System checks */
  .installer-checks { width: 100%; margin-top: 24px; }
  .installer-check-row { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid #1A1A1A; animation: checkSlide 0.4s ease-out; }
  @keyframes checkSlide { from { opacity: 0; transform: translateX(-10px); } to { opacity: 1; transform: translateX(0); } }
  .installer-check-icon { font-size: 18px; width: 24px; text-align: center; }
  .installer-check-label { font-size: 14px; color: #A08264; }
  .installer-check-value { margin-left: auto; font-size: 14px; color: #F0DCC8; font-weight: 500; }
  .installer-recommended { margin-top: 24px; padding: 16px; border-radius: 10px; background: rgba(217,119,6,0.1); border: 1px solid #D97706; text-align: center; font-size: 14px; color: #A08264; }
  .installer-recommended strong { color: #F59E0B; }

  /* Confirm card */
  .installer-confirm-card { width: 100%; background: #1A1A1A; border-radius: 14px; border: 1px solid #D97706; padding: 24px; margin-top: 20px; }
  .installer-confirm-row { display: flex; justify-content: space-between; padding: 10px 0; }
  .installer-confirm-label { font-size: 14px; color: #A08264; }
  .installer-confirm-value { font-size: 14px; color: #F0DCC8; font-weight: 600; }
  .installer-confirm-divider { height: 1px; background: #2A2A2A; }

  /* Install progress */
  .installer-install-steps { width: 100%; margin-top: 28px; }
  .installer-install-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; transition: all 0.3s; }
  .installer-install-row.done .installer-install-icon { color: #22C55E; }
  .installer-install-row.running .installer-install-label { color: #F59E0B; }
  .installer-install-row.fail .installer-install-icon { color: #EF4444; }
  .installer-install-icon { font-size: 16px; width: 22px; text-align: center; }
  .installer-install-label { font-size: 14px; color: #A08264; }
  .installer-install-companion { font-size: 48px; margin-top: 32px; animation: companionBounce 1.5s ease-in-out infinite; }
  @keyframes companionBounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }

  /* Success */
  .installer-success-fire { font-size: 64px; animation: fireGlow 2s ease-in-out infinite alternate; }
  .installer-success-title { font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #F59E0B, #D97706); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-top: 8px; margin-bottom: 4px; }
  .installer-success-subtitle { font-size: 15px; color: #A08264; text-align: center; white-space: pre-line; margin-bottom: 20px; }
  .installer-success-scene { display: flex; gap: 24px; align-items: flex-end; margin-bottom: 28px; }
  .installer-success-fire-emoji { font-size: 48px; }
  .installer-success-companion { font-size: 36px; animation: companionBounce 1.5s ease-in-out infinite; }
  .installer-success-tips { text-align: left; background: #1A1A1A; border-radius: 12px; padding: 20px; margin-bottom: 20px; width: 100%; }
  .installer-success-tip-title { font-size: 14px; color: #D97706; font-weight: 600; margin-bottom: 10px; }
  .installer-success-tip { font-size: 13px; color: #A08264; margin-bottom: 4px; }
`;

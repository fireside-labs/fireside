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
import { useState, useEffect, useCallback, useRef } from "react";
import EmberParticles from "@/components/EmberParticles";
import BrainSelectScreen from "@/components/BrainSelectScreen";
import { playWhoosh, playPing, playTick, startFireLoop, playCrackle } from "@/components/FiresideSounds";

// ---------- Types ----------------------------------------------------------

type CheckStatus = "pending" | "ok" | "fail";
type InstallStatus = "pending" | "running" | "done" | "fail";
interface SysCheck { label: string; status: CheckStatus; value: string; }
interface InstallStep { label: string; status: InstallStatus; }

interface SystemInfo {
  os: string;
  arch: string;
  ram_gb: number;
  gpu: string;
  vram_gb: number;
}

interface InstallerConfig {
  userName: string;
  userRole: string;
  userContext: string;
  companionSpecies: string;
  companionName: string;
  agentName: string;
  agentStyle: string;
  brainSize: string;
  brainModel: string;
  actualModel: string;
  brainLabel: string;
  brainDisplaySize: string;
}

type Step = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;

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

const MODEL_LABELS: Record<string, string> = {
    "llama-3.1-8b-q6": "⚡ Llama 3.1 8B (Q6_K)",
    "mistral-v0.3-7b": "⚡ Mistral v0.3 7B",
    "qwen-2.5-7b": "⚡ Qwen 2.5 7B",
    "qwen-2.5-35b-q4": "🧠 Qwen 2.5 35B (Q4_K)",
    "command-r-35b": "🧠 Command R (v01)",
};

// ---------- Tauri Helpers --------------------------------------------------

async function tauriInvoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const w = window as any;
  if (w.__TAURI__?.core?.invoke) {
    return w.__TAURI__.core.invoke(cmd, args) as Promise<T>;
  }
  // Browser fallback — mock for development (slower so you feel the fire build)
  console.log(`[mock] invoke(${cmd})`, args);
  const delay = (cmd === "check_python" || cmd === "check_node" || cmd === "clone_repo" || cmd === "install_deps" || cmd === "write_config")
    ? 1500 + Math.random() * 1000  // Install steps: 1.5-2.5s each
    : 800;
  await new Promise((r) => setTimeout(r, delay));
  if (cmd === "get_system_info") return { os: "Windows 11", arch: "x86_64", ram_gb: 32, gpu: "NVIDIA RTX 4090", vram_gb: 24 } as T;
  if (cmd === "check_python") return "3.12.2" as T;
  if (cmd === "check_node") return "20.11.0" as T;
  if (cmd === "download_brain") return { success: true } as T;
  if (cmd === "test_connection") return { success: true, message: "Atlas is ready to chat!" } as T;
  return {} as T;
}

// ---------- Component ------------------------------------------------------

export default function InstallerWizard({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState<Step>(0);
  const [config, setConfig] = useState<InstallerConfig>({
    userName: "",
    userRole: "",
    userContext: "",
    companionSpecies: "fox",
    companionName: "Ember",
    agentName: "Atlas",
    agentStyle: "analytical",
    brainSize: "smart",
    brainModel: "7B",
    actualModel: "llama-3.1-8b-q6",
    brainLabel: "Llama 3.1 8B",
    brainDisplaySize: "~4.9 GB",
  });
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const [sysChecks, setSysChecks] = useState<SysCheck[]>([]);
  const [installSteps, setInstallSteps] = useState<InstallStep[]>([]);
  const [animClass, setAnimClass] = useState("installer-enter");
  const [brainProgress, setBrainProgress] = useState(0);
  const [brainDownloading, setBrainDownloading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"pending" | "testing" | "success" | "fail">("pending");
  const [installIntensity, setInstallIntensity] = useState(0);
  const [sparkBurst, setSparkBurst] = useState(false);

  const fireLoopRef = useRef<(() => void) | null>(null);

  const goTo = useCallback((s: Step) => {
    playWhoosh();
    setAnimClass("installer-exit");
    setTimeout(() => {
      setStep(s);
      setAnimClass("installer-enter");
    }, 250);
  }, []);

  // Fire crackling runs throughout the entire installer
  useEffect(() => {
    fireLoopRef.current = startFireLoop(step === 6 ? 0.7 : 0.2);
    return () => { fireLoopRef.current?.(); };
  }, [step]);

  // ── Step 1: System Check (auto-run) ──
  useEffect(() => {
    if (step !== 1) return;
    const checks: SysCheck[] = [
      { label: "Operating System", status: "pending", value: "" },
      { label: "Memory", status: "pending", value: "" },
      { label: "Graphics", status: "pending", value: "" },
      { label: "VRAM", status: "pending", value: "" },
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
      update(0, `${info.os} (${info.arch})`); playPing();
      await new Promise((r) => setTimeout(r, 400));
      update(1, `${info.ram_gb}GB RAM`); playPing();
      await new Promise((r) => setTimeout(r, 400));
      update(2, info.gpu || "No GPU detected"); playPing();
      await new Promise((r) => setTimeout(r, 400));
      update(3, info.vram_gb ? `${info.vram_gb}GB VRAM` : "Not detected"); playPing();
      // Auto-advance to brain selection after a brief pause
      await new Promise((r) => setTimeout(r, 800));
    })();
  }, [step, goTo]);

  // ── Step 6: Installing ──
  useEffect(() => {
    if (step !== 6) return;
    const steps: InstallStep[] = [
      { label: "Checking Python", status: "pending" },
      { label: "Checking Node.js", status: "pending" },
      { label: "Setting up Fireside", status: "pending" },
      { label: "Installing packages", status: "pending" },
      { label: "Saving your preferences", status: "pending" },
    ];
    setInstallSteps(steps);

    (async () => {
      const totalSteps = steps.length;
      const run = async (i: number, fn: () => Promise<void>) => {
        steps[i] = { ...steps[i], status: "running" };
        setInstallSteps([...steps]);
        // Ramp intensity as we progress through steps
        setInstallIntensity(Math.round(((i + 0.5) / totalSteps) * 80));
        try {
          await fn();
          steps[i] = { ...steps[i], status: "done" };
        } catch {
          steps[i] = { ...steps[i], status: "fail" };
        }
        setInstallSteps([...steps]);
        // Spark burst on step completion!
        setSparkBurst(true);
        setTimeout(() => setSparkBurst(false), 150);
        setInstallIntensity(Math.round(((i + 1) / totalSteps) * 80));
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
            brain: (sysInfo?.vram_gb || 0) >= 20 ? "deep" : "fast",
            model: (sysInfo?.vram_gb || 0) >= 20 ? "qwen-2.5-35b-q4" : "llama-3.1-8b-q6",
          },
        });
      });

      // Final ignition — max intensity
      setInstallIntensity(100);
      setSparkBurst(true);
      setTimeout(() => setSparkBurst(false), 200);

      // Check results: config write (step 4) is critical, others are non-critical
      const hasCriticalFail = steps[4].status === "fail";
      const hasWarnings = steps.some((s, i) => i < 4 && s.status === "fail");

      if (hasCriticalFail) {
        setInstallIntensity(10);
        return;
      }

      if (hasWarnings) {
        steps.forEach((s, i) => {
          if (i < 4 && s.status === "fail") {
            steps[i] = { ...s, status: "done", label: `${s.label} (skipped — already set up)` };
          }
        });
        setInstallSteps([...steps]);
      }

      setTimeout(() => goTo(7), 800);
    })();
  }, [step, config, goTo, sysInfo]);

  // ── Step 7: Brain Download ──
  useEffect(() => {
    if (step !== 7 || brainDownloading) return;
    // Don't auto-start — user chooses to download or skip
  }, [step, brainDownloading]);

  const startBrainDownload = useCallback(async () => {
    setBrainDownloading(true);
    setBrainProgress(0);
    const model = config.actualModel || "llama-3.1-8b-q6";
    try {
      // Simulate progress for development (Tauri will send real progress events)
      const progressInterval = setInterval(() => {
        setBrainProgress(prev => {
          if (prev >= 95) { clearInterval(progressInterval); return prev; }
          return prev + Math.random() * 3 + 1;
        });
      }, 300);

      await tauriInvoke("download_brain", { model, dest: "~/.fireside/models/" });
      clearInterval(progressInterval);
      setBrainProgress(100);
      localStorage.setItem("fireside_model", model);
      setTimeout(() => goTo(8), 600);
    } catch {
      setBrainDownloading(false);
      setBrainProgress(0);
    }
  }, [config.actualModel, goTo]);

  // ── Step 8: Connection Test ──
  useEffect(() => {
    if (step !== 8) return;
    setConnectionStatus("testing");
    (async () => {
      try {
        await tauriInvoke("test_connection");
        setConnectionStatus("success");
        setTimeout(() => goTo(9), 1500);
      } catch {
        setConnectionStatus("fail");
      }
    })();
  }, [step, goTo]);

  const speciesEmoji = SPECIES.find((s) => s.id === config.companionSpecies)?.emoji || "🦊";
  const brainLabel = config.brainLabel || "Llama 3.1 8B";
  const brainSize = config.brainDisplaySize || "~4.9 GB";

  // ── Shared progress bar ──
  const progress = ((step / 9) * 100);

  return (
    <div className="installer-root">
      <style>{installerCSS}</style>

      {/* Progress */}
      <div className="installer-progress">
        <div className="installer-progress-fill" style={{ width: `${progress}%` }} />
      </div>

      {/* Persistent ember background — the whole installer is fireside */}
      <EmberParticles
        intensity={step === 6 ? installIntensity : 12}
        burst={step === 6 && sparkBurst}
        style={{ position: 'fixed', inset: 0, zIndex: 1 }}
      />

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

        {/* Step 1: System Check — clean, auto-advances to brain select */}
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
              <>
                <div className="installer-recommended">
                  <span>System ready</span>
                  <p style={{ fontSize: 12, color: '#7A6A5A', marginTop: 4 }}>
                    {sysInfo.gpu || 'CPU'} · {sysInfo.vram_gb ? `${sysInfo.vram_gb}GB VRAM` : `${sysInfo.ram_gb}GB RAM`}
                  </p>
                </div>
                <div className="installer-spacer" />
                <button className="installer-btn-primary" onClick={() => goTo(2)}>
                  Choose Your Brain →
                </button>
              </>
            )}
          </div>
        )}

        {/* Step 2: Brain Selection — two-screen RPG picker */}
        {step === 2 && (
          <BrainSelectScreen
            onSelect={(modelId, label, size, quant) => {
              setConfig(c => ({
                ...c,
                brainSize: modelId,
                actualModel: modelId,
                brainLabel: label,
                brainDisplaySize: size,
                brainModel: quant,
              }));
              goTo(3);
            }}
            detectedVram={sysInfo?.vram_gb || 0}
            onBack={() => goTo(1)}
            fullscreen
          />
        )}

        {/* Step 3: Choose Companion */}
        {step === 3 && (
          <div className="installer-center">
            <h2 className="installer-title">Choose a companion for your journey</h2>
            <p className="installer-subtitle">Every journey starts with a friend.</p>
            <div className="installer-species-grid">
              {SPECIES.map((s) => (
                <button
                  key={s.id}
                  className={`installer-species-card ${config.companionSpecies === s.id ? "selected" : ""}`}
                  onClick={() => { playTick(); setConfig((c) => ({ ...c, companionSpecies: s.id })); }}
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
              <button className="installer-btn-back" onClick={() => goTo(2)}>← Back</button>
              <button className="installer-btn-primary" onClick={() => goTo(4)}>Next →</button>
            </div>
          </div>
        )}

        {/* Step 4: Create AI + About You */}
        {step === 4 && (
          <div className="installer-center" style={{ maxWidth: 520 }}>
            <h2 className="installer-title">Let&apos;s set up the fireside.</h2>
            <p className="installer-subtitle">
              Tell {config.companionName || "Ember"} who you are so your AI can be useful from day one.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, width: '100%', marginBottom: 8 }}>
              <div>
                <label className="installer-label">Your name</label>
                <input className="installer-input" value={config.userName}
                  onChange={(e) => setConfig((c) => ({ ...c, userName: e.target.value }))}
                  placeholder="Jordan" />
              </div>
              <div>
                <label className="installer-label">Your AI&apos;s name</label>
                <input className="installer-input" value={config.agentName}
                  onChange={(e) => setConfig((c) => ({ ...c, agentName: e.target.value }))}
                  placeholder="Atlas" />
              </div>
            </div>

            <label className="installer-label">What do you do?</label>
            <div className="installer-role-grid">
              {[
                { id: "work", emoji: "💼", label: "Work" },
                { id: "student", emoji: "📚", label: "Student" },
                { id: "creative", emoji: "🎨", label: "Creative" },
                { id: "founder", emoji: "🚀", label: "Founder" },
                { id: "developer", emoji: "💻", label: "Developer" },
                { id: "other", emoji: "✨", label: "Other" },
              ].map((r) => (
                <button key={r.id}
                  className={`installer-role-chip ${config.userRole === r.id ? "selected" : ""}`}
                  onClick={() => { playTick(); setConfig((c) => ({ ...c, userRole: r.id })); }}
                >
                  <span>{r.emoji}</span> {r.label}
                </button>
              ))}
            </div>

            <label className="installer-label">Anything {config.agentName || "Atlas"} should know about you?</label>
            <textarea
              className="installer-textarea"
              value={config.userContext}
              onChange={(e) => setConfig((c) => ({ ...c, userContext: e.target.value }))}
              placeholder="e.g. I'm a startup founder in healthcare, I like concise answers, I work late at night..."
              rows={3}
            />

            <label className="installer-label" style={{ marginTop: 8 }}>What&apos;s {config.agentName || "Atlas"}&apos;s style?</label>
            <div className="installer-style-grid">
              {STYLES.map((s) => (
                <button key={s.id}
                  className={`installer-style-card ${config.agentStyle === s.id ? "selected" : ""}`}
                  onClick={() => { playTick(); setConfig((c) => ({ ...c, agentStyle: s.id })); }}
                >
                  <span className="installer-style-emoji">{s.emoji}</span>
                  <span className="installer-style-label">{s.label}</span>
                  <span className="installer-style-desc">{s.desc}</span>
                </button>
              ))}
            </div>
            <div className="installer-nav">
              <button className="installer-btn-back" onClick={() => goTo(3)}>← Back</button>
              <button className="installer-btn-primary" onClick={() => goTo(5)}>Next →</button>
            </div>
          </div>
        )}

        {/* Step 5: Confirmation */}
        {step === 5 && (
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
                  {config.brainLabel || config.actualModel}
                </span>
              </div>
            </div>
            <div className="installer-nav">
              <button className="installer-btn-back" onClick={() => goTo(4)}>← Back</button>
              <button className="installer-btn-install" onClick={() => goTo(6)}>
                Install Fireside →
              </button>
            </div>
          </div>
        )}

        {/* Step 6: Installing — with ember fire crackling */}
        {step === 6 && (
          <div className="installer-center" style={{ position: 'relative' }}>
            {/* Ember particle system — intensifies with install progress */}
            <EmberParticles
              intensity={installIntensity}
              burst={sparkBurst}
              style={{ position: 'fixed', inset: 0, zIndex: 0 }}
            />

            <div style={{ position: 'relative', zIndex: 2 }}>
              <h2 className="installer-title">
                {config.agentName || "Atlas"} and {config.companionName || "Ember"} are getting ready...
              </h2>

              {/* Fire-intensity bar */}
              <div className="installer-fire-bar">
                <div
                  className="installer-fire-bar-fill"
                  style={{ width: `${installIntensity}%` }}
                />
              </div>

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
              <div className={`installer-install-companion ${installIntensity > 60 ? 'installer-companion-hot' : ''}`}>
                {speciesEmoji}
              </div>
            </div>
          </div>
        )}

        {/* Step 7: Brain Download — with ambient embers */}
        {step === 7 && (
          <div className="installer-center" style={{ position: 'relative' }}>
            <EmberParticles
              intensity={brainDownloading ? Math.min(brainProgress * 0.8, 80) : 20}
              burst={brainProgress >= 100}
              style={{ position: 'fixed', inset: 0, zIndex: 0 }}
            />
            <div style={{ position: 'relative', zIndex: 2 }}>
              <span style={{ fontSize: 48, display: 'block', marginBottom: 16, animation: 'float 3s ease-in-out infinite' }}>🧠</span>
              <h2 className="installer-title">Download your AI brain</h2>
              <p className="installer-subtitle" style={{ marginBottom: 24 }}>
                {brainLabel} — {brainSize}
              </p>

              {!brainDownloading ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' }}>
                  <button className="installer-btn-primary" onClick={startBrainDownload}>
                    Download Brain →
                  </button>
                  <button
                    className="installer-btn-secondary"
                    onClick={() => goTo(9)}
                    style={{ opacity: 0.6, fontSize: 13 }}
                  >
                    Download Later (power users)
                  </button>
                </div>
              ) : (
                <div style={{ width: '100%', maxWidth: 400 }}>
                  {/* Fire-trail progress bar */}
                  <div className="installer-fire-bar" style={{ marginBottom: 12 }}>
                    <div
                      className="installer-fire-bar-fill"
                      style={{ width: `${Math.min(brainProgress, 100)}%` }}
                    />
                  </div>
                  <p style={{ textAlign: 'center', fontSize: 13, color: 'rgba(255,255,255,0.5)' }}>
                    {brainProgress < 100 ? `Downloading... ${Math.round(brainProgress)}%` : '✔ Download complete!'}
                  </p>
                </div>
              )}

              <div className="installer-install-companion" style={{ marginTop: 32 }}>
                {speciesEmoji}
              </div>
            </div>
          </div>
        )}

        {/* Step 8: Connection Test */}
        {step === 8 && (
          <div className="installer-center">
            <span style={{ fontSize: 48, display: 'block', marginBottom: 16, animation: connectionStatus === 'testing' ? 'pulse 1.5s ease-in-out infinite' : 'none' }}>
              {connectionStatus === 'success' ? '✅' : connectionStatus === 'fail' ? '❌' : '⚡'}
            </span>
            <h2 className="installer-title">
              {connectionStatus === 'testing' && 'Starting your AI...'}
              {connectionStatus === 'success' && `${config.agentName || 'Atlas'} is ready!`}
              {connectionStatus === 'fail' && 'Connection failed'}
            </h2>
            <p className="installer-subtitle">
              {connectionStatus === 'testing' && 'Testing connection to your AI brain...'}
              {connectionStatus === 'success' && `${config.companionName || 'Ember'} is by their side. Let\'s go!`}
              {connectionStatus === 'fail' && 'Don\'t worry — you can configure this in Settings.'}
            </p>
            {connectionStatus === 'fail' && (
              <button className="installer-btn-primary" style={{ marginTop: 16 }} onClick={() => goTo(9)}>
                Continue Anyway →
              </button>
            )}
            {connectionStatus === 'testing' && (
              <button
                className="installer-btn-secondary"
                style={{ marginTop: 16, opacity: 0.6, fontSize: 13 }}
                onClick={() => goTo(9)}
              >
                Skip →
              </button>
            )}
          </div>
        )}

        {/* Step 9: Success */}
        {step === 9 && (
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
                if (config.userRole) localStorage.setItem("fireside_user_role", config.userRole);
                if (config.userContext) localStorage.setItem("fireside_user_context", config.userContext);
                localStorage.setItem("fireside_agent_name", config.agentName || "Atlas");
                localStorage.setItem("fireside_agent_style", config.agentStyle);
                localStorage.setItem("fireside_companion_species", config.companionSpecies);
                localStorage.setItem("fireside_companion_name", config.companionName || "Ember");
                localStorage.setItem("fireside_companion", JSON.stringify({
                  name: config.companionName || "Ember",
                  species: config.companionSpecies,
                }));
                localStorage.setItem("fireside_vram", sysInfo?.vram_gb.toString() || "0");
                const brainId = (sysInfo?.vram_gb || 0) >= 20 ? "deep" : "fast";
                localStorage.setItem("fireside_brain", brainId);
                // fireside_model is set only when brain actually downloads (line 235)
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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

  .installer-root {
    position: fixed; inset: 0; z-index: 9999;
    background: var(--color-void);
    font-family: var(--font-family-body);
    color: var(--color-rune);
    display: flex; flex-direction: column;
    overflow: hidden;
  }

  /* ── Ambient background glow ── */
  .installer-root::before {
    content: ''; position: absolute; inset: 0; pointer-events: none;
    background:
      radial-gradient(ellipse 600px 400px at 50% 80%, rgba(217,119,6,0.12) 0%, transparent 70%),
      radial-gradient(ellipse 300px 300px at 30% 20%, rgba(245,158,11,0.06) 0%, transparent 60%),
      radial-gradient(ellipse 200px 200px at 75% 30%, rgba(146,64,14,0.08) 0%, transparent 60%);
    animation: ambientShift 8s ease-in-out infinite alternate;
  }
  @keyframes ambientShift {
    0% { opacity: 0.7; transform: scale(1); }
    100% { opacity: 1; transform: scale(1.05); }
  }

  /* ── Vignette overlay ── */
  .installer-root::after {
    content: ''; position: absolute; inset: 0; pointer-events: none;
    background: radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.6) 100%);
  }

  /* ── Fire particle system (CSS only) ── */
  .installer-root .installer-content::before {
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 300px;
    background:
      radial-gradient(2px 2px at 20% 90%, var(--color-neon), transparent),
      radial-gradient(2px 2px at 40% 85%, var(--color-neon-dim), transparent),
      radial-gradient(2px 2px at 60% 92%, var(--color-neon), transparent),
      radial-gradient(2px 2px at 80% 88%, var(--color-neon-dim), transparent),
      radial-gradient(3px 3px at 10% 95%, var(--color-neon), transparent),
      radial-gradient(3px 3px at 50% 80%, #92400E, transparent),
      radial-gradient(2px 2px at 70% 93%, var(--color-neon), transparent),
      radial-gradient(2px 2px at 90% 87%, var(--color-neon-dim), transparent),
      radial-gradient(1px 1px at 25% 75%, var(--color-neon), transparent),
      radial-gradient(1px 1px at 55% 70%, var(--color-neon-dim), transparent),
      radial-gradient(1px 1px at 85% 78%, var(--color-neon), transparent),
      radial-gradient(1px 1px at 15% 82%, var(--color-neon-dim), transparent);
    background-size: 100% 100%;
    animation: particleRise 4s ease-in-out infinite;
    pointer-events: none; opacity: 0.4;
  }
  @keyframes particleRise {
    0% { transform: translateY(0) scaleY(1); opacity: 0.4; }
    50% { transform: translateY(-30px) scaleY(1.1); opacity: 0.6; }
    100% { transform: translateY(0) scaleY(1); opacity: 0.4; }
  }

  /* Progress bar */
  .installer-progress { height: 2px; background: #111; position: relative; z-index: 10; }
  .installer-progress-fill {
    height: 100%; border-radius: 2px;
    background: linear-gradient(90deg, #92400E, var(--color-neon-dim), var(--color-neon));
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 0 12px var(--color-neon-glow-strong);
  }

  /* ── Cinematic transitions ── */
  .installer-enter { animation: cineFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
  .installer-exit { animation: cineFadeOut 0.3s cubic-bezier(0.7, 0, 0.84, 0) forwards; }
  @keyframes cineFadeIn {
    from { opacity: 0; transform: translateY(20px) scale(0.98); filter: blur(4px); }
    to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
  }
  @keyframes cineFadeOut {
    from { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
    to { opacity: 0; transform: translateY(-20px) scale(1.02); filter: blur(4px); }
  }

  /* Content */
  .installer-content {
    flex: 1; display: flex; align-items: center; justify-content: center;
    padding: 48px; position: relative; z-index: 5;
  }
  .installer-center {
    display: flex; flex-direction: column; align-items: center;
    max-width: 560px; width: 100%;
  }
  .installer-spacer { height: 48px; }

  /* ── Welcome ── */
  .installer-fire {
    font-size: 100px; margin-bottom: 20px;
    animation: fireFloat 3s ease-in-out infinite;
    filter: drop-shadow(0 0 40px rgba(245,158,11,0.5));
  }
  @keyframes fireFloat {
    0%, 100% { transform: translateY(0) scale(1); filter: drop-shadow(0 0 40px rgba(245,158,11,0.5)); }
    50% { transform: translateY(-10px) scale(1.05); filter: drop-shadow(0 0 60px rgba(245,158,11,0.7)); }
  }
  .installer-brand {
    font-size: 56px; font-weight: 900; letter-spacing: 10px;
    background: linear-gradient(135deg, var(--color-neon) 0%, var(--color-neon-dim) 40%, #92400E 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
    text-shadow: none;
    filter: drop-shadow(0 2px 8px rgba(217,119,6,0.3));
  }
  .installer-tagline {
    font-size: 16px; color: rgba(160,130,100,0.8); margin-bottom: 0;
    letter-spacing: 2px; text-transform: uppercase; font-weight: 500;
  }

  /* Typography */
  .installer-title {
    font-size: 26px; font-weight: 700; color: #F0DCC8;
    text-align: center; margin-bottom: 8px;
    text-shadow: 0 2px 12px rgba(245,158,11,0.15);
  }
  .installer-subtitle { font-size: 14px; color: #7A6A5A; text-align: center; margin-bottom: 28px; }
  .installer-label { font-size: 11px; color: #7A6A5A; align-self: flex-start; margin-bottom: 6px; margin-top: 18px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; }

  /* Inputs */
  .installer-input {
    width: 100%; padding: 14px 18px; border-radius: 12px;
    background: rgba(26,26,26,0.8); border: 1px solid rgba(255,255,255,0.06);
    color: #F0DCC8; font-size: 15px; outline: none;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(8px);
  }
  .installer-input:focus {
    border-color: var(--color-neon-dim);
    box-shadow: 0 0 20px var(--color-neon-glow), inset 0 0 20px rgba(217,119,6,0.05);
  }
  .installer-input::placeholder { color: #3A3028; }

  /* Role chips */
  .installer-role-grid {
    display: flex; flex-wrap: wrap; gap: 8px; width: 100%; margin-bottom: 8px;
  }
  .installer-role-chip {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06);
    background: rgba(26,26,26,0.6); color: #7A6A5A; font-size: 13px; font-weight: 600;
    cursor: pointer; transition: all 0.25s; font-family: 'Outfit', system-ui;
  }
  .installer-role-chip:hover { border-color: rgba(245,158,11,0.2); color: #C4A882; }
  .installer-role-chip.selected {
    border-color: rgba(245,158,11,0.4); color: #F59E0B;
    background: rgba(245,158,11,0.08);
    box-shadow: 0 0 12px rgba(245,158,11,0.1);
  }

  /* Textarea */
  .installer-textarea {
    width: 100%; padding: 14px 18px; border-radius: 12px; resize: vertical;
    background: rgba(26,26,26,0.8); border: 1px solid rgba(255,255,255,0.06);
    color: #F0DCC8; font-size: 13px; line-height: 1.6; outline: none;
    font-family: 'Outfit', system-ui; transition: all 0.3s;
    backdrop-filter: blur(8px); min-height: 70px;
  }
  .installer-textarea:focus {
    border-color: var(--color-neon-dim);
    box-shadow: 0 0 20px var(--color-neon-glow), inset 0 0 20px rgba(217,119,6,0.05);
  }
  .installer-textarea::placeholder { color: #3A3028; }

  /* ── Buttons — game menu feel ── */
  .installer-btn-primary {
    padding: 16px 48px; border-radius: 14px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 16px; font-weight: 800; letter-spacing: 1px;
    text-transform: uppercase;
    box-shadow: 0 4px 24px rgba(245,158,11,0.3), inset 0 1px 0 rgba(255,255,255,0.2);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); margin-top: 28px;
    position: relative; overflow: hidden;
  }
  .installer-btn-primary::before {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    transform: translateX(-100%);
    transition: transform 0.6s ease;
  }
  .installer-btn-primary:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 8px 32px var(--color-neon-glow-strong), inset 0 1px 0 rgba(255,255,255,0.3);
  }
  .installer-btn-primary:hover::before { transform: translateX(100%); }

  .installer-btn-back {
    background: none; border: 1px solid rgba(255,255,255,0.06);
    color: #7A6A5A; font-size: 13px; cursor: pointer;
    padding: 10px 20px; border-radius: 10px;
    transition: all 0.2s;
  }
  .installer-btn-back:hover { color: #F0DCC8; border-color: rgba(255,255,255,0.15); }

  .installer-btn-install {
    padding: 18px 56px; border-radius: 14px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 18px; font-weight: 900; letter-spacing: 1.5px;
    text-transform: uppercase;
    box-shadow: 0 4px 30px rgba(245,158,11,0.4);
    transition: all 0.3s; animation: installPulse 2.5s ease-in-out infinite;
    position: relative; overflow: hidden;
  }
  @keyframes installPulse {
    0%, 100% { box-shadow: 0 4px 30px rgba(245,158,11,0.4); }
    50% { box-shadow: 0 4px 50px rgba(245,158,11,0.7), 0 0 80px rgba(245,158,11,0.2); }
  }
  .installer-btn-install:hover { transform: translateY(-3px) scale(1.03); }
  .installer-nav { display: flex; justify-content: space-between; width: 100%; margin-top: 36px; align-items: center; }

  /* ── Species grid — glassmorphism cards ── */
  .installer-species-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; width: 100%; margin-bottom: 24px; }
  .installer-species-card {
    display: flex; flex-direction: column; align-items: center;
    padding: 24px 14px; border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.06);
    background: rgba(26,26,26,0.6);
    backdrop-filter: blur(12px);
    cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .installer-species-card:hover {
    border-color: rgba(217,119,6,0.3); transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0,0,0,0.3);
  }
  .installer-species-card.selected {
    border-color: var(--color-neon-dim);
    background: var(--color-neon-glow);
    box-shadow: 0 0 30px var(--color-neon-glow-strong), inset 0 0 30px rgba(217,119,6,0.05);
    transform: translateY(-4px) scale(1.02);
  }
  .installer-species-emoji { font-size: 40px; margin-bottom: 8px; transition: transform 0.3s; }
  .installer-species-card:hover .installer-species-emoji { transform: scale(1.15); }
  .installer-species-card.selected .installer-species-emoji { transform: scale(1.2); animation: selectedBounce 1s ease-in-out infinite; }
  @keyframes selectedBounce { 0%,100% { transform: scale(1.2) translateY(0); } 50% { transform: scale(1.2) translateY(-4px); } }
  .installer-species-label { font-size: 13px; color: #A08264; font-weight: 600; letter-spacing: 0.5px; }

  /* Style grid */
  .installer-style-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; width: 100%; }
  .installer-style-card {
    display: flex; flex-direction: column; padding: 18px;
    border-radius: 14px; border: 1px solid rgba(255,255,255,0.06);
    background: rgba(26,26,26,0.6); backdrop-filter: blur(12px);
    cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); text-align: left;
  }
  .installer-style-card:hover { border-color: rgba(217,119,6,0.3); transform: translateY(-2px); }
  .installer-style-card.selected {
    border-color: #D97706; background: rgba(217,119,6,0.1);
    box-shadow: 0 0 30px rgba(217,119,6,0.2), inset 0 0 20px rgba(217,119,6,0.05);
  }
  .installer-style-emoji { font-size: 28px; margin-bottom: 6px; }
  .installer-style-label { font-size: 14px; color: #F0DCC8; font-weight: 700; margin-bottom: 3px; }
  .installer-style-desc { font-size: 12px; color: #7A6A5A; }

  /* System checks */
  .installer-checks { width: 100%; margin-top: 28px; }
  .installer-check-row {
    display: flex; align-items: center; gap: 14px; padding: 14px 0;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    animation: checkReveal 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  @keyframes checkReveal {
    from { opacity: 0; transform: translateX(-16px) scale(0.95); }
    to { opacity: 1; transform: translateX(0) scale(1); }
  }
  .installer-check-icon { font-size: 18px; width: 24px; text-align: center; filter: drop-shadow(0 0 4px rgba(34,197,94,0.3)); }
  .installer-check-label { font-size: 14px; color: #7A6A5A; }
  .installer-check-value { margin-left: auto; font-size: 14px; color: #F0DCC8; font-weight: 600; }
  .installer-recommended {
    margin-top: 28px; padding: 18px; border-radius: 12px;
    background: rgba(217,119,6,0.08); border: 1px solid rgba(217,119,6,0.3);
    text-align: center; font-size: 14px; color: #7A6A5A;
    backdrop-filter: blur(8px);
  }
  .installer-recommended strong { color: #F59E0B; }

  /* Confirm card */
  .installer-confirm-card {
    width: 100%; border-radius: 16px; padding: 28px;
    margin-top: 24px;
    background: rgba(26,26,26,0.7); backdrop-filter: blur(16px);
    border: 1px solid rgba(217,119,6,0.3);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 0 40px rgba(217,119,6,0.03);
  }
  .installer-confirm-row { display: flex; justify-content: space-between; padding: 12px 0; }
  .installer-confirm-label { font-size: 13px; color: #7A6A5A; text-transform: uppercase; letter-spacing: 1px; }
  .installer-confirm-value { font-size: 14px; color: #F0DCC8; font-weight: 700; }
  .installer-confirm-divider { height: 1px; background: rgba(255,255,255,0.04); }

  /* Install progress */
  .installer-install-steps { width: 100%; margin-top: 32px; }
  .installer-install-row {
    display: flex; align-items: center; gap: 14px; padding: 12px 0;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .installer-install-row.done .installer-install-icon { color: #22C55E; filter: drop-shadow(0 0 6px rgba(34,197,94,0.4)); }
  .installer-install-row.running .installer-install-label { color: #F59E0B; text-shadow: 0 0 8px rgba(245,158,11,0.3); }
  .installer-install-row.running .installer-install-icon { animation: spinGlow 1s linear infinite; }
  @keyframes spinGlow { 0% { filter: brightness(0.8); } 50% { filter: brightness(1.3) drop-shadow(0 0 6px rgba(245,158,11,0.5)); } 100% { filter: brightness(0.8); } }
  .installer-install-row.fail .installer-install-icon { color: #EF4444; }
  .installer-install-icon { font-size: 16px; width: 22px; text-align: center; }
  .installer-install-label { font-size: 14px; color: #7A6A5A; }
  .installer-install-companion {
    font-size: 56px; margin-top: 36px;
    animation: companionFloat 3s ease-in-out infinite;
    filter: drop-shadow(0 8px 24px rgba(0,0,0,0.4));
  }
  @keyframes companionFloat {
    0%, 100% { transform: translateY(0) rotate(-2deg); }
    33% { transform: translateY(-12px) rotate(1deg); }
    66% { transform: translateY(-6px) rotate(-1deg); }
  }

  /* ── Fire-trail progress bar ── */
  .installer-fire-bar {
    width: 100%; height: 6px; border-radius: 3px;
    background: rgba(255,255,255,0.06); overflow: hidden;
    margin: 16px 0 24px;
    position: relative;
  }
  .installer-fire-bar-fill {
    height: 100%; border-radius: 3px;
    background: linear-gradient(90deg, #92400E, #D97706, #F59E0B, #FBBF24);
    box-shadow: 0 0 16px rgba(245,158,11,0.5), 0 0 40px rgba(245,158,11,0.2);
    transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
  }
  .installer-fire-bar-fill::after {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%);
    animation: fireBarShimmer 1.5s ease-in-out infinite;
  }
  @keyframes fireBarShimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(200%); }
  }

  /* Companion glows hot when install progresses past 60% */
  .installer-companion-hot {
    filter: drop-shadow(0 0 30px rgba(245,158,11,0.6)) drop-shadow(0 8px 24px rgba(0,0,0,0.4));
    animation: companionHotFloat 2s ease-in-out infinite;
  }
  @keyframes companionHotFloat {
    0%, 100% { transform: translateY(0) rotate(-2deg) scale(1); }
    33% { transform: translateY(-14px) rotate(2deg) scale(1.05); }
    66% { transform: translateY(-8px) rotate(-1deg) scale(1.02); }
  }

  /* ── Success — celebration ── */
  .installer-success-fire {
    font-size: 80px;
    animation: fireFloat 3s ease-in-out infinite;
    filter: drop-shadow(0 0 50px rgba(245,158,11,0.6));
  }
  .installer-success-title {
    font-size: 32px; font-weight: 900;
    background: linear-gradient(135deg, #F59E0B, #D97706);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-top: 12px; margin-bottom: 4px;
    filter: drop-shadow(0 2px 8px rgba(217,119,6,0.3));
  }
  .installer-success-subtitle {
    font-size: 15px; color: #7A6A5A; text-align: center;
    white-space: pre-line; margin-bottom: 24px;
  }
  .installer-success-scene {
    display: flex; gap: 32px; align-items: flex-end; margin-bottom: 32px;
  }
  .installer-success-fire-emoji {
    font-size: 56px;
    filter: drop-shadow(0 0 20px rgba(245,158,11,0.5));
  }
  .installer-success-companion {
    font-size: 42px;
    animation: companionFloat 3s ease-in-out infinite;
    filter: drop-shadow(0 4px 16px rgba(0,0,0,0.4));
  }
  .installer-success-tips {
    text-align: left; border-radius: 14px; padding: 22px;
    margin-bottom: 24px; width: 100%;
    background: rgba(26,26,26,0.7); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.04);
  }
  .installer-success-tip-title { font-size: 13px; color: #D97706; font-weight: 700; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }
  .installer-success-tip { font-size: 13px; color: #7A6A5A; margin-bottom: 6px; }
`;

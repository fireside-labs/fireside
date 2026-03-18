"use client";

import { useState, useEffect, useMemo } from "react";
import { API_BASE } from "../../lib/api";
import EmberParticles from "@/components/EmberParticles";

/* ═══════════════════════════════════════════════════════════════════
   Pipeline — The Forge
   Watch your AI smith tasks through ember stages.
   Companion reacts. Socratic debate for reviews.
   ═══════════════════════════════════════════════════════════════════ */

interface Stage {
  name: string;
  status: "done" | "active" | "pending" | "failed";
  role: string;
  output?: string;
  on_fail?: string;
}

interface Pipeline {
  id: string;
  title: string;
  template: string;
  templateIcon: string;
  status: "running" | "complete" | "failed" | "escalated";
  iteration: number;
  maxIterations: number;
  stages: Stage[];
  startedAt: Date;
  eta?: string;
  mode: "local" | "mesh";
  lessons?: string[];
  debate?: DebateRound[];
}

interface DebateRound {
  persona: string;
  color: string;
  icon: string;
  message: string;
}

// ── Mock data (replaced by API in production) ──
const MOCK_PIPELINES: Pipeline[] = [
  {
    id: "p1",
    title: "Add user authentication to the API",
    template: "Coding",
    templateIcon: "⚡",
    status: "running",
    iteration: 3,
    maxIterations: 10,
    stages: [
      { name: "Spec", status: "done", role: "planner" },
      { name: "Build", status: "done", role: "backend" },
      { name: "Test", status: "active", role: "tester", output: "Running tests... 12/18 passing" },
      { name: "Review", status: "pending", role: "reviewer" },
    ],
    startedAt: new Date(Date.now() - 14 * 60 * 1000),
    eta: "~8 min",
    mode: "local",
    debate: [
      { persona: "Planner", color: "#60A5FA", icon: "🏛️", message: "The auth middleware is solid but the token refresh flow has a race condition when two requests hit simultaneously." },
      { persona: "Tester", color: "#F87171", icon: "😈", message: "What happens in 6 months when you have 50 endpoints? This middleware requires manual annotation on every route." },
      { persona: "Reviewer", color: "#A78BFA", icon: "👤", message: "The error messages are too cryptic. 'Invalid JWT' tells the frontend developer nothing about what went wrong." },
    ],
  },
  {
    id: "p2",
    title: "Research competitor pricing strategies",
    template: "Research",
    templateIcon: "🔍",
    status: "complete",
    iteration: 2,
    maxIterations: 5,
    stages: [
      { name: "Gather", status: "done", role: "researcher" },
      { name: "Analyze", status: "done", role: "analyst" },
      { name: "Write", status: "done", role: "writer" },
    ],
    startedAt: new Date(Date.now() - 34 * 60 * 1000),
    mode: "local",
    lessons: [
      "Premium tier pricing clusters around $20-30/mo for AI products",
      "Free tier with local-only is a strong differentiator",
      "Enterprise pricing should be per-seat, not flat rate",
    ],
  },
];

// ── Templates ──
const TEMPLATES = [
  { id: "coding", name: "Coding", icon: "⚡", stages: "Spec → Build ═ → Test → Review", color: "#F59E0B" },
  { id: "research", name: "Research", icon: "🔍", stages: "Gather → Analyze → Write", color: "#60A5FA" },
  { id: "drafting", name: "Drafting", icon: "✉️", stages: "Context → Draft → Review", color: "#A78BFA" },
  { id: "presentation", name: "Presentation", icon: "📊", stages: "Outline → Content → Design → Review", color: "#FB923C" },
  { id: "analysis", name: "Analysis", icon: "📈", stages: "Gather → Analyze → Insights → Report", color: "#34D399" },
  { id: "general", name: "General", icon: "📋", stages: "Plan → Execute → Review", color: "#F0DCC8" },
];

export default function PipelinePage() {
  const [species, setSpecies] = useState("fox");
  const [pipelines, setPipelines] = useState<Pipeline[]>(MOCK_PIPELINES);
  const [activePipeline, setActivePipeline] = useState<string | null>("p1");
  const [showWizard, setShowWizard] = useState(false);
  const [wizardInput, setWizardInput] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [showDebate, setShowDebate] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("fireside_companion");
      if (stored) {
        const c = JSON.parse(stored);
        setSpecies(c.species || "fox");
      }
    } catch { /* default fox */ }
  }, []);

  const current = useMemo(() => pipelines.find(p => p.id === activePipeline), [pipelines, activePipeline]);
  const progress = current ? Math.round((current.stages.filter(s => s.status === "done").length / current.stages.length) * 100) : 0;

  // Auto-detect template from input
  useEffect(() => {
    if (!wizardInput.trim()) { setSelectedTemplate(null); return; }
    const lower = wizardInput.toLowerCase();
    if (["api", "backend", "frontend", "build", "code", "deploy"].some(k => lower.includes(k))) setSelectedTemplate("coding");
    else if (["research", "investigate", "find out", "look into"].some(k => lower.includes(k))) setSelectedTemplate("research");
    else if (["draft", "letter", "email", "write"].some(k => lower.includes(k))) setSelectedTemplate("drafting");
    else if (["presentation", "slides", "deck"].some(k => lower.includes(k))) setSelectedTemplate("presentation");
    else if (["analyze", "data", "trends", "metrics"].some(k => lower.includes(k))) setSelectedTemplate("analysis");
    else setSelectedTemplate("general");
  }, [wizardInput]);

  // Companion reaction based on pipeline state
  const companionMood = useMemo(() => {
    if (!current) return { expression: "idle", speech: "No forges running. Start one?" };
    if (current.status === "complete") return { expression: "happy", speech: "The forge is done! Look what we made! ✨" };
    if (current.status === "failed" || current.status === "escalated") return { expression: "worried", speech: "Something went wrong... need your help!" };
    const active = current.stages.find(s => s.status === "active");
    if (active?.name === "Test") return { expression: "curious", speech: `Testing... 🔍 ${active.output || ""}` };
    if (active?.name === "Review") return { expression: "thinking", speech: "Reviewing the work..." };
    return { expression: "watching", speech: `Forging: ${active?.name || "..."}` };
  }, [current]);

  return (
    <div className="fp-root">
      <style>{pageCSS}</style>
      <EmberParticles intensity={current?.status === "running" ? 30 : 15} className="fp-embers" />

      <div className="fp-layout">
        {/* ── Left: Pipeline List ── */}
        <div className="fp-sidebar">
          <div className="fp-sidebar-header">
            <h2 className="fp-sidebar-title">🔥 The Forge</h2>
            <button className="fp-new-btn" onClick={() => setShowWizard(true)}>+ New</button>
          </div>

          <div className="fp-pipeline-list">
            {pipelines.map((p) => (
              <button
                key={p.id}
                className={`fp-pipeline-card ${activePipeline === p.id ? "active" : ""} ${p.status}`}
                onClick={() => { setActivePipeline(p.id); setShowDebate(false); }}
              >
                <div className="fp-pc-header">
                  <span className="fp-pc-icon">{p.templateIcon}</span>
                  <span className="fp-pc-template">{p.template}</span>
                  {p.status === "running" && <span className="fp-pc-live">LIVE</span>}
                  {p.status === "complete" && <span className="fp-pc-done">✔</span>}
                </div>
                <div className="fp-pc-title">{p.title}</div>
                <div className="fp-pc-stages">
                  {p.stages.map((s, i) => (
                    <span key={i} className={`fp-pc-dot ${s.status}`} title={s.name} />
                  ))}
                </div>
                {p.status === "running" && (
                  <div className="fp-pc-meta">Iteration {p.iteration} · {p.eta || "..."}</div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* ── Right: Detail View ── */}
        <div className="fp-main">
          {!current && !showWizard && (
            <div className="fp-empty">
              <img src={`/hub/mascot_${species}.png`} alt="" className="fp-empty-mascot" />
              <p className="fp-empty-text">No forge selected</p>
              <p className="fp-empty-sub">Select a pipeline or start a new one</p>
              <button className="fp-start-btn" onClick={() => setShowWizard(true)}>⚡ Start a Forge</button>
            </div>
          )}

          {/* ═══ WIZARD ═══ */}
          {showWizard && (
            <div className="fp-wizard">
              <div className="fp-wizard-panel">
                <div className="fp-wiz-header">
                  <h2>⚡ New Pipeline</h2>
                  <button className="fp-wiz-close" onClick={() => setShowWizard(false)}>×</button>
                </div>

                <label className="fp-wiz-label">What should we forge?</label>
                <input
                  className="fp-wiz-input"
                  value={wizardInput}
                  onChange={(e) => setWizardInput(e.target.value)}
                  placeholder="Build a real-time chat app with auth..."
                  autoFocus
                />

                <div className="fp-wiz-templates">
                  {TEMPLATES.map((t) => (
                    <button
                      key={t.id}
                      className={`fp-wiz-tcard ${selectedTemplate === t.id ? "selected" : ""}`}
                      style={{ "--tc": t.color } as React.CSSProperties}
                      onClick={() => setSelectedTemplate(t.id)}
                    >
                      <div className="fp-wiz-ticon">{t.icon}</div>
                      <div className="fp-wiz-tname">{t.name}</div>
                      <div className="fp-wiz-tstages">{t.stages}</div>
                    </button>
                  ))}
                </div>

                {selectedTemplate && (
                  <div className="fp-wiz-preview">
                    <div className="fp-wiz-preview-label">Stage Preview</div>
                    <div className="fp-wiz-preview-stages">
                      {(TEMPLATES.find(t => t.id === selectedTemplate)?.stages || "").split(" → ").map((s, i) => (
                        <div key={i} className="fp-wiz-stage-node" style={{ animationDelay: `${i * 0.1}s` }}>
                          <div className="fp-wiz-ember" />
                          <span>{s.replace("═ ", "")}</span>
                          {i < (TEMPLATES.find(t => t.id === selectedTemplate)?.stages || "").split(" → ").length - 1 && (
                            <div className="fp-wiz-trail" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="fp-wiz-actions">
                  <button className="fp-wiz-cancel" onClick={() => setShowWizard(false)}>Cancel</button>
                  <button
                    className="fp-wiz-create"
                    disabled={!wizardInput.trim() || !selectedTemplate}
                    onClick={() => { setShowWizard(false); /* TODO: POST /api/v1/orchestrate */ }}
                  >
                    ⚡ Create Pipeline
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ═══ PIPELINE DETAIL ═══ */}
          {current && !showWizard && (
            <div className="fp-detail">
              {/* Header */}
              <div className="fp-detail-header">
                <div>
                  <h1 className="fp-detail-title">{current.templateIcon} {current.title}</h1>
                  <div className="fp-detail-meta">
                    <span className={`fp-status-badge ${current.status}`}>
                      {current.status === "running" ? "🔄 Running" : current.status === "complete" ? "✅ Complete" : "⚠️ " + current.status}
                    </span>
                    <span>Iteration {current.iteration}/{current.maxIterations}</span>
                    <span>{current.template}</span>
                    <span>{current.mode === "mesh" ? "🔗 Mesh" : "🖥️ Local"}</span>
                  </div>
                </div>
                <img src={`/hub/mascot_${species}.png`} alt="" className="fp-detail-mascot" />
              </div>

              {/* Companion speech */}
              <div className="fp-companion-speech">
                <p>{companionMood.speech}</p>
              </div>

              {/* ── FORGE: Stage Timeline ── */}
              <div className="fp-forge">
                <div className="fp-forge-glow" />
                <div className="fp-stages">
                  {current.stages.map((stage, i) => (
                    <div key={i} className={`fp-stage ${stage.status}`} style={{ animationDelay: `${i * 0.15}s` }}>
                      <div className={`fp-ember-stone ${stage.status}`}>
                        {stage.status === "done" && <span className="fp-ember-check">✔</span>}
                        {stage.status === "active" && <div className="fp-ember-flames" />}
                        {stage.status === "failed" && <span className="fp-ember-x">✕</span>}
                      </div>
                      <div className="fp-stage-label">{stage.name}</div>
                      <div className="fp-stage-role">{stage.role}</div>
                      {i < current.stages.length - 1 && (
                        <div className={`fp-fire-trail ${stage.status === "done" ? "lit" : ""}`} />
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Progress bar */}
              <div className="fp-progress-wrap">
                <div className="fp-progress-bar">
                  <div className="fp-progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <span className="fp-progress-text">{progress}% · {current.eta || "Complete"}</span>
              </div>

              {/* ── Active stage output ── */}
              {current.stages.find(s => s.status === "active")?.output && (
                <div className="fp-stage-output">
                  <div className="fp-so-label">Current Output</div>
                  <pre className="fp-so-content">{current.stages.find(s => s.status === "active")?.output}</pre>
                </div>
              )}

              {/* ── Socratic Debate ── */}
              {current.debate && current.debate.length > 0 && (
                <div className="fp-debate-section">
                  <button className="fp-debate-toggle" onClick={() => setShowDebate(!showDebate)}>
                    🗣️ Socratic Review {showDebate ? "▼" : "▶"}
                  </button>
                  {showDebate && (
                    <div className="fp-debate">
                      <div className="fp-debate-bar-wrap">
                        <div className="fp-debate-bar-label">Consensus</div>
                        <div className="fp-debate-bar">
                          <div className="fp-debate-bar-fill" style={{ width: "45%" }} />
                        </div>
                        <span className="fp-debate-pct">45%</span>
                      </div>
                      {current.debate.map((d, i) => (
                        <div key={i} className="fp-debate-msg" style={{ "--dc": d.color, animationDelay: `${i * 0.1}s` } as React.CSSProperties}>
                          <div className="fp-debate-icon">{d.icon}</div>
                          <div className="fp-debate-content">
                            <div className="fp-debate-persona" style={{ color: d.color }}>{d.persona}</div>
                            <p className="fp-debate-text">{d.message}</p>
                          </div>
                        </div>
                      ))}
                      <button className="fp-intervene-btn">🖐️ Intervene — Add Your Take</button>
                    </div>
                  )}
                </div>
              )}

              {/* ── Lessons (complete pipelines) ── */}
              {current.lessons && current.lessons.length > 0 && (
                <div className="fp-lessons">
                  <h3 className="fp-lessons-title">📜 Lessons Learned</h3>
                  {current.lessons.map((l, i) => (
                    <div key={i} className="fp-lesson-item">• {l}</div>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div className="fp-actions">
                {current.status === "running" && (
                  <>
                    <button className="fp-action-btn cancel">Cancel Pipeline</button>
                    <button className="fp-action-btn advance">Force Advance ▶</button>
                  </>
                )}
                {current.status === "complete" && (
                  <button className="fp-action-btn new" onClick={() => setShowWizard(true)}>⚡ New Pipeline</button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
// CSS — Pipeline Forge
// ════════════════════════════════════════════════════════════════════

const pageCSS = `
  .fp-root {
    min-height: 100vh; width: 100%;
    background: #060609;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    color: #F0DCC8;
    position: relative;
  }
  .fp-embers { position: fixed !important; inset: 0 !important; z-index: 1 !important; }

  .fp-layout {
    display: flex; min-height: 100vh;
    position: relative; z-index: 5;
  }

  /* ── Sidebar ── */
  .fp-sidebar {
    width: 300px; flex-shrink: 0;
    background: rgba(8,8,14,0.92); backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.04);
    display: flex; flex-direction: column;
    padding: 20px 16px;
  }
  .fp-sidebar-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 20px;
  }
  .fp-sidebar-title {
    font-size: 20px; font-weight: 900;
    background: linear-gradient(135deg, #F0DCC8, #F59E0B);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
  }
  .fp-new-btn {
    padding: 6px 16px; border-radius: 10px;
    background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.15);
    color: #F59E0B; font-size: 12px; font-weight: 800;
    cursor: pointer; transition: all 0.2s; font-family: 'Outfit';
  }
  .fp-new-btn:hover { background: rgba(245,158,11,0.15); transform: scale(1.05); }

  /* Pipeline cards */
  .fp-pipeline-list { display: flex; flex-direction: column; gap: 10px; }
  .fp-pipeline-card {
    padding: 14px 16px; border-radius: 14px; cursor: pointer;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);
    text-align: left; transition: all 0.25s; font-family: 'Outfit';
    animation: fpCardIn 0.4s ease both;
  }
  @keyframes fpCardIn { from { opacity: 0; transform: translateX(-10px); } to { opacity: 1; transform: translateX(0); } }
  .fp-pipeline-card:hover {
    background: rgba(245,158,11,0.04); border-color: rgba(245,158,11,0.1);
  }
  .fp-pipeline-card.active {
    background: rgba(245,158,11,0.06); border-color: rgba(245,158,11,0.2);
    box-shadow: 0 0 20px rgba(245,158,11,0.05);
  }
  .fp-pc-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
  .fp-pc-icon { font-size: 14px; }
  .fp-pc-template { font-size: 10px; font-weight: 800; color: #6A5A4A; text-transform: uppercase; letter-spacing: 1px; }
  .fp-pc-live {
    margin-left: auto; font-size: 8px; font-weight: 800; color: #34D399;
    padding: 2px 6px; border-radius: 4px;
    background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.2);
    animation: fpPulse 2s ease-in-out infinite;
  }
  @keyframes fpPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
  .fp-pc-done { margin-left: auto; color: #34D399; font-size: 12px; }
  .fp-pc-title { font-size: 13px; font-weight: 700; color: #C4A882; margin-bottom: 8px; line-height: 1.3; }
  .fp-pc-stages { display: flex; gap: 4px; margin-bottom: 6px; }
  .fp-pc-dot {
    width: 8px; height: 8px; border-radius: 50%;
    transition: all 0.3s;
  }
  .fp-pc-dot.done { background: #F59E0B; box-shadow: 0 0 6px rgba(245,158,11,0.4); }
  .fp-pc-dot.active { background: #F59E0B; animation: fpDotPulse 1.5s ease-in-out infinite; }
  @keyframes fpDotPulse {
    0%, 100% { box-shadow: 0 0 4px rgba(245,158,11,0.3); transform: scale(1); }
    50% { box-shadow: 0 0 12px rgba(245,158,11,0.6); transform: scale(1.3); }
  }
  .fp-pc-dot.pending { background: rgba(255,255,255,0.08); }
  .fp-pc-dot.failed { background: #EF4444; }
  .fp-pc-meta { font-size: 10px; color: #4A3D30; }

  /* ── Main area ── */
  .fp-main { flex: 1; overflow-y: auto; position: relative; }

  /* Empty state */
  .fp-empty {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    height: 100%; gap: 12px;
  }
  .fp-empty-mascot {
    width: 100px; height: 100px; object-fit: contain;
    mix-blend-mode: screen; filter: drop-shadow(0 0 20px rgba(245,158,11,0.2));
    animation: fpBob 4s ease-in-out infinite;
  }
  @keyframes fpBob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
  .fp-empty-text { font-size: 18px; font-weight: 700; color: #6A5A4A; }
  .fp-empty-sub { font-size: 12px; color: #3A3530; }
  .fp-start-btn {
    padding: 12px 28px; border-radius: 12px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 14px; font-weight: 800;
    font-family: 'Outfit'; transition: all 0.2s;
    box-shadow: 0 4px 20px rgba(245,158,11,0.25);
  }
  .fp-start-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(245,158,11,0.35); }

  /* ═══ WIZARD ═══ */
  .fp-wizard {
    display: flex; align-items: center; justify-content: center;
    height: 100%; padding: 40px;
  }
  .fp-wizard-panel {
    width: 100%; max-width: 600px;
    background: rgba(15,13,22,0.85); backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px; padding: 28px; box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }
  .fp-wiz-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
  .fp-wiz-header h2 { margin: 0; font-size: 20px; font-weight: 900; color: #F59E0B; }
  .fp-wiz-close {
    width: 32px; height: 32px; border-radius: 8px;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06);
    color: #4A3D30; font-size: 18px; cursor: pointer; transition: all 0.2s;
  }
  .fp-wiz-close:hover { color: #F0DCC8; }

  .fp-wiz-label { font-size: 12px; font-weight: 700; color: #6A5A4A; margin-bottom: 8px; display: block; }
  .fp-wiz-input {
    width: 100%; padding: 14px 18px; border-radius: 12px;
    background: rgba(18,16,26,0.7); border: 1.5px solid rgba(255,255,255,0.06);
    color: #F0DCC8; font-size: 14px; outline: none;
    font-family: 'Outfit'; transition: all 0.3s; margin-bottom: 20px;
  }
  .fp-wiz-input:focus { border-color: rgba(245,158,11,0.3); box-shadow: 0 0 20px rgba(245,158,11,0.06); }
  .fp-wiz-input::placeholder { color: rgba(240,220,200,0.2); }

  .fp-wiz-templates { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; }
  .fp-wiz-tcard {
    padding: 14px; border-radius: 12px; cursor: pointer;
    background: rgba(255,255,255,0.02); border: 1.5px solid rgba(255,255,255,0.05);
    text-align: center; transition: all 0.3s; font-family: 'Outfit';
  }
  .fp-wiz-tcard:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.1); }
  .fp-wiz-tcard.selected {
    border-color: var(--tc); box-shadow: 0 0 20px color-mix(in srgb, var(--tc) 15%, transparent);
    background: color-mix(in srgb, var(--tc) 4%, transparent);
  }
  .fp-wiz-ticon { font-size: 22px; margin-bottom: 4px; }
  .fp-wiz-tname { font-size: 12px; font-weight: 800; color: #C4A882; }
  .fp-wiz-tstages { font-size: 9px; color: #4A3D30; margin-top: 4px; }

  .fp-wiz-preview {
    padding: 16px; border-radius: 12px;
    background: rgba(245,158,11,0.03); border: 1px solid rgba(245,158,11,0.08);
    margin-bottom: 20px;
  }
  .fp-wiz-preview-label { font-size: 10px; font-weight: 800; color: #6A5A4A; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
  .fp-wiz-preview-stages { display: flex; align-items: center; gap: 0; justify-content: center; }
  .fp-wiz-stage-node {
    display: flex; align-items: center; gap: 0;
    animation: fpStageIn 0.3s ease both;
  }
  @keyframes fpStageIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }
  .fp-wiz-ember {
    width: 12px; height: 12px; border-radius: 50%;
    background: #F59E0B; box-shadow: 0 0 10px rgba(245,158,11,0.4);
    margin-right: 6px;
  }
  .fp-wiz-stage-node span { font-size: 11px; font-weight: 700; color: #C4A882; margin-right: 6px; }
  .fp-wiz-trail {
    width: 30px; height: 2px;
    background: linear-gradient(90deg, rgba(245,158,11,0.4), rgba(245,158,11,0.1));
    margin-right: 6px;
  }

  .fp-wiz-actions { display: flex; justify-content: flex-end; gap: 12px; }
  .fp-wiz-cancel {
    padding: 10px 22px; border-radius: 10px;
    background: transparent; border: 1px solid rgba(255,255,255,0.08);
    color: #6A5A4A; font-size: 13px; font-weight: 700; cursor: pointer;
    font-family: 'Outfit'; transition: all 0.2s;
  }
  .fp-wiz-cancel:hover { border-color: rgba(255,255,255,0.15); color: #C4A882; }
  .fp-wiz-create {
    padding: 10px 22px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 13px; font-weight: 800; cursor: pointer;
    font-family: 'Outfit'; transition: all 0.2s;
    box-shadow: 0 4px 16px rgba(245,158,11,0.2);
  }
  .fp-wiz-create:hover { transform: translateY(-1px); box-shadow: 0 6px 24px rgba(245,158,11,0.3); }
  .fp-wiz-create:disabled { opacity: 0.3; cursor: default; transform: none; }

  /* ═══ PIPELINE DETAIL ═══ */
  .fp-detail { padding: 28px 36px; animation: fsFadeUp 0.5s ease; }
  @keyframes fsFadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

  .fp-detail-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 8px; }
  .fp-detail-title { font-size: 22px; font-weight: 900; color: #F0DCC8; margin: 0 0 8px; }
  .fp-detail-meta { display: flex; gap: 12px; flex-wrap: wrap; }
  .fp-detail-meta span {
    font-size: 11px; color: #4A3D30; padding: 3px 10px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);
    border-radius: 8px; font-weight: 600;
  }
  .fp-status-badge.running { color: #34D399; border-color: rgba(52,211,153,0.15); background: rgba(52,211,153,0.06); }
  .fp-status-badge.complete { color: #F59E0B; border-color: rgba(245,158,11,0.15); background: rgba(245,158,11,0.06); }
  .fp-status-badge.failed { color: #EF4444; border-color: rgba(239,68,68,0.15); background: rgba(239,68,68,0.06); }

  .fp-detail-mascot {
    width: 64px; height: 64px; object-fit: contain;
    mix-blend-mode: screen; filter: drop-shadow(0 0 15px rgba(245,158,11,0.25));
    animation: fpBob 4s ease-in-out infinite;
  }

  .fp-companion-speech {
    padding: 10px 16px; border-radius: 12px 12px 12px 4px;
    background: rgba(15,13,22,0.7); border: 1px solid rgba(245,158,11,0.08);
    font-size: 12px; color: #C4A882; margin-bottom: 24px;
    max-width: 400px;
  }

  /* ── FORGE ── */
  .fp-forge {
    position: relative; padding: 50px 20px;
    margin-bottom: 20px; border-radius: 16px;
    background: url('/hub/forge_background.png') center/cover no-repeat;
    border: 1px solid rgba(245,158,11,0.1);
    overflow: hidden;
    min-height: 200px;
  }
  .fp-forge-glow {
    position: absolute; bottom: 0; left: 0; right: 0; height: 70%;
    background: radial-gradient(ellipse 80% 100% at 50% 100%, rgba(245,158,11,0.1), transparent);
    pointer-events: none;
  }
  .fp-stages { display: flex; align-items: center; justify-content: center; gap: 10px; position: relative; z-index: 2; }

  .fp-stage {
    display: flex; flex-direction: column; align-items: center; gap: 8px;
    position: relative; min-width: 100px;
    animation: fpStageIn 0.4s ease both;
  }

  .fp-ember-stone {
    width: 72px; height: 72px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    position: relative; transition: all 0.4s;
    background-size: contain; background-repeat: no-repeat; background-position: center;
  }
  .fp-ember-stone.done {
    background-image: url('/hub/ember_stone_done.png');
    filter: drop-shadow(0 0 15px rgba(245,158,11,0.4));
  }
  .fp-ember-stone.active {
    background-image: url('/hub/ember_stone_active.png');
    filter: drop-shadow(0 0 25px rgba(245,158,11,0.6));
    animation: fpEmberPulse 2s ease-in-out infinite;
  }
  @keyframes fpEmberPulse {
    0%, 100% { filter: drop-shadow(0 0 20px rgba(245,158,11,0.4)); transform: scale(1); }
    50% { filter: drop-shadow(0 0 35px rgba(245,158,11,0.7)); transform: scale(1.08); }
  }
  .fp-ember-stone.pending {
    background-image: url('/hub/ember_stone_pending.png');
    filter: drop-shadow(0 0 5px rgba(255,255,255,0.05));
    opacity: 0.7;
  }
  .fp-ember-stone.failed {
    background-image: url('/hub/ember_stone_active.png');
    filter: drop-shadow(0 0 15px rgba(239,68,68,0.5)) hue-rotate(-40deg);
  }
  .fp-ember-check { color: #FEF3C7; font-size: 18px; font-weight: 900; text-shadow: 0 0 8px rgba(245,158,11,0.8); }
  .fp-ember-x { color: #fff; font-size: 18px; font-weight: 900; text-shadow: 0 0 6px rgba(239,68,68,0.8); }
  .fp-ember-flames {
    position: absolute; top: -16px; left: 50%; transform: translateX(-50%);
    width: 30px; height: 30px;
    background: radial-gradient(circle, rgba(255,200,50,0.9), rgba(245,158,11,0.4) 50%, transparent 70%);
    border-radius: 50%; filter: blur(4px);
    animation: fpFlame 0.8s ease-in-out infinite alternate;
  }
  @keyframes fpFlame {
    0% { transform: translateX(-50%) translateY(0) scale(1); opacity: 0.6; }
    100% { transform: translateX(-50%) translateY(-8px) scale(1.4); opacity: 1; }
  }

  .fp-stage-label { font-size: 13px; font-weight: 800; color: #F0DCC8; text-shadow: 0 1px 4px rgba(0,0,0,0.6); }
  .fp-stage-role { font-size: 9px; color: #8A7A6A; text-transform: uppercase; letter-spacing: 0.5px; }

  .fp-fire-trail {
    position: absolute; top: 28px; left: calc(50% + 36px);
    width: 28px; height: 20px;
    background: url('/hub/fire_trail.png') center/cover no-repeat;
    opacity: 0.15;
    transition: all 0.5s;
  }
  .fp-fire-trail.lit {
    opacity: 0.7;
    filter: drop-shadow(0 0 8px rgba(245,158,11,0.3));
  }

  /* Progress */
  .fp-progress-wrap { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
  .fp-progress-bar {
    flex: 1; height: 4px; border-radius: 2px;
    background: rgba(255,255,255,0.05); overflow: hidden;
  }
  .fp-progress-fill {
    height: 100%; border-radius: 2px;
    background: linear-gradient(90deg, #D97706, #F59E0B);
    box-shadow: 0 0 8px rgba(245,158,11,0.3);
    transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .fp-progress-text { font-size: 11px; color: #4A3D30; font-weight: 600; white-space: nowrap; }

  /* Stage output */
  .fp-stage-output {
    padding: 14px; border-radius: 12px;
    background: rgba(15,13,22,0.6); border: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 20px;
  }
  .fp-so-label { font-size: 10px; font-weight: 800; color: #6A5A4A; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .fp-so-content {
    font-size: 12px; color: #C4A882; font-family: 'JetBrains Mono', monospace;
    white-space: pre-wrap; margin: 0; line-height: 1.6;
  }

  /* ── Debate ── */
  .fp-debate-section { margin-bottom: 20px; }
  .fp-debate-toggle {
    padding: 10px 16px; border-radius: 10px;
    background: rgba(167,139,250,0.04); border: 1px solid rgba(167,139,250,0.1);
    color: #A78BFA; font-size: 13px; font-weight: 700; cursor: pointer;
    font-family: 'Outfit'; transition: all 0.2s; width: 100%; text-align: left;
  }
  .fp-debate-toggle:hover { background: rgba(167,139,250,0.08); }

  .fp-debate { padding: 16px 0; display: flex; flex-direction: column; gap: 12px; }
  .fp-debate-bar-wrap { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .fp-debate-bar-label { font-size: 10px; font-weight: 800; color: #6A5A4A; }
  .fp-debate-bar { flex: 1; height: 4px; border-radius: 2px; background: rgba(255,255,255,0.05); }
  .fp-debate-bar-fill { height: 100%; border-radius: 2px; background: linear-gradient(90deg, #A78BFA, #8B5CF6); }
  .fp-debate-pct { font-size: 11px; color: #A78BFA; font-weight: 700; }

  .fp-debate-msg {
    display: flex; gap: 12px; padding: 12px;
    border-radius: 12px; background: rgba(255,255,255,0.02);
    border: 1px solid color-mix(in srgb, var(--dc) 12%, transparent);
    animation: fpStageIn 0.3s ease both;
  }
  .fp-debate-icon { font-size: 20px; flex-shrink: 0; margin-top: 2px; }
  .fp-debate-persona { font-size: 11px; font-weight: 800; margin-bottom: 3px; }
  .fp-debate-text { font-size: 12px; color: #C4A882; line-height: 1.5; margin: 0; }

  .fp-intervene-btn {
    padding: 10px 20px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, rgba(167,139,250,0.1), rgba(167,139,250,0.05));
    border: 1px solid rgba(167,139,250,0.15);
    color: #A78BFA; font-size: 12px; font-weight: 800;
    cursor: pointer; font-family: 'Outfit'; transition: all 0.2s;
    align-self: center;
  }
  .fp-intervene-btn:hover { background: rgba(167,139,250,0.15); transform: translateY(-1px); }

  /* ── Lessons ── */
  .fp-lessons {
    padding: 16px; border-radius: 12px;
    background: rgba(245,158,11,0.03); border: 1px solid rgba(245,158,11,0.08);
    margin-bottom: 20px;
  }
  .fp-lessons-title { font-size: 14px; font-weight: 800; color: #F59E0B; margin: 0 0 10px; }
  .fp-lesson-item { font-size: 12px; color: #C4A882; line-height: 1.6; margin-bottom: 4px; }

  /* Actions */
  .fp-actions { display: flex; gap: 12px; }
  .fp-action-btn {
    padding: 10px 22px; border-radius: 10px; font-size: 12px;
    font-weight: 700; cursor: pointer; font-family: 'Outfit'; transition: all 0.2s;
  }
  .fp-action-btn.cancel {
    background: transparent; border: 1px solid rgba(239,68,68,0.15);
    color: #EF4444;
  }
  .fp-action-btn.cancel:hover { background: rgba(239,68,68,0.08); }
  .fp-action-btn.advance {
    background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.15);
    color: #F59E0B;
  }
  .fp-action-btn.advance:hover { background: rgba(245,158,11,0.15); }
  .fp-action-btn.new {
    background: linear-gradient(135deg, #D97706, #F59E0B);
    border: none; color: #0A0A0A; font-weight: 800;
  }
  .fp-action-btn.new:hover { transform: translateY(-1px); }
`;

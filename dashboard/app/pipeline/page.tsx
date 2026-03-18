"use client";

import { useState, useEffect, useMemo } from "react";
import { API_BASE } from "../../lib/api";

/* ═══════════════════════════════════════════════════════════════════
   Pipeline — The Forge
   Companion-guided task orchestration.
   The mascot narrates, guides, and reacts.
   ═══════════════════════════════════════════════════════════════════ */

interface Stage {
  name: string;
  emoji: string;
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

// ── Stage emoji mapping ──
const STAGE_EMOJI: Record<string, string> = {
  Spec: "📜", Plan: "📜", Outline: "📜", Context: "📜", Gather: "🔎",
  Build: "🔨", Content: "🔨", Draft: "✍️", Design: "🎨",
  Test: "🔍", Analyze: "📊", Insights: "💡",
  Review: "👤", Write: "✍️", Report: "📋", Execute: "⚡",
};

// ── Mascot pose mapping per stage ──
function getMascotPose(species: string, status?: string, stageName?: string): string {
  const base = `/hub/mascot_${species}`;
  if (!status || status === "idle") return `${base}_reading.png`;
  if (status === "complete") return `${base}_celebrating.png`;
  if (status === "failed" || status === "escalated") return `${base}_surprised.png`;
  if (stageName === "Test" || stageName === "Analyze") return `${base}_thinking.png`;
  if (stageName === "Review" || stageName === "Write") return `${base}_thinking.png`;
  if (stageName === "Build" || stageName === "Execute" || stageName === "Draft" || stageName === "Content") return `${base}_building.png`;
  if (stageName === "Spec" || stageName === "Plan" || stageName === "Gather") return `${base}_reading.png`;
  return `${base}_building.png`;
}

// ── Mock data ──
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
      { name: "Spec", emoji: "📜", status: "done", role: "planner" },
      { name: "Build", emoji: "🔨", status: "done", role: "engineer" },
      { name: "Test", emoji: "🔍", status: "active", role: "tester", output: "Running tests... 12/18 passing" },
      { name: "Review", emoji: "👤", status: "pending", role: "reviewer" },
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
      { name: "Gather", emoji: "🔎", status: "done", role: "researcher" },
      { name: "Analyze", emoji: "📊", status: "done", role: "analyst" },
      { name: "Write", emoji: "✍️", status: "done", role: "writer" },
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

// ── Template auto-detection ──
function detectTemplate(input: string): { name: string; icon: string; stages: string[] } {
  const lower = input.toLowerCase();
  if (["api", "backend", "frontend", "build", "code", "deploy", "app", "function"].some(k => lower.includes(k)))
    return { name: "Coding", icon: "⚡", stages: ["📜 Plan", "🔨 Build", "🔍 Test", "👤 Review"] };
  if (["research", "investigate", "find out", "look into", "compare"].some(k => lower.includes(k)))
    return { name: "Research", icon: "🔍", stages: ["🔎 Gather", "📊 Analyze", "✍️ Write"] };
  if (["draft", "letter", "email", "write a"].some(k => lower.includes(k)))
    return { name: "Drafting", icon: "✉️", stages: ["📜 Context", "✍️ Draft", "👤 Review"] };
  if (["presentation", "slides", "deck"].some(k => lower.includes(k)))
    return { name: "Presentation", icon: "📊", stages: ["📜 Outline", "🔨 Content", "🎨 Design", "👤 Review"] };
  if (["analyze", "data", "trends", "metrics", "numbers"].some(k => lower.includes(k)))
    return { name: "Analysis", icon: "📈", stages: ["🔎 Gather", "📊 Analyze", "💡 Insights", "📋 Report"] };
  return { name: "General", icon: "📋", stages: ["📜 Plan", "⚡ Execute", "👤 Review"] };
}


export default function PipelinePage() {
  const [species, setSpecies] = useState("fox");
  const [pipelines, setPipelines] = useState<Pipeline[]>(MOCK_PIPELINES);
  const [activePipeline, setActivePipeline] = useState<string | null>(null);
  const [taskInput, setTaskInput] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
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
  const activeStage = current?.stages.find(s => s.status === "active");
  const progress = current ? Math.round((current.stages.filter(s => s.status === "done").length / current.stages.length) * 100) : 0;
  const detected = taskInput.trim() ? detectTemplate(taskInput) : null;

  // Companion speech & pose
  const companion = useMemo(() => {
    if (activePipeline && current) {
      if (current.status === "complete") return {
        pose: getMascotPose(species, "complete"),
        speech: "We did it! Here's what I learned along the way. 🎉",
      };
      if (current.status === "failed" || current.status === "escalated") return {
        pose: getMascotPose(species, "failed"),
        speech: "Something went wrong... I need your help to figure this out!",
      };
      return {
        pose: getMascotPose(species, "running", activeStage?.name),
        speech: activeStage?.name === "Test"
          ? `Testing... ${activeStage?.output || "running checks"}`
          : activeStage?.name === "Build"
          ? "Forging the pieces together... 🔨"
          : activeStage?.name === "Review"
          ? "Reviewing the work for quality..."
          : activeStage?.name === "Spec" || activeStage?.name === "Plan"
          ? "Planning the approach... 📜"
          : `Working on ${activeStage?.name || "it"}...`,
      };
    }
    return {
      pose: getMascotPose(species, "idle"),
      speech: "I can break big tasks into steps and work through them. What should I work on?",
    };
  }, [species, activePipeline, current, activeStage]);

  // Active stage index for mascot positioning
  const activeIdx = current?.stages.findIndex(s => s.status === "active") ?? -1;
  const stageCount = current?.stages.length ?? 1;

  return (
    <div className="fp-root">
      <style>{pageCSS}</style>

      <div className="fp-layout">
        {/* ── Sidebar ── */}
        <div className="fp-sidebar">
          <div className="fp-sidebar-header">
            <h2 className="fp-sidebar-title">🔥 The Forge</h2>
          </div>

          <button
            className={`fp-pipeline-card new-task ${!activePipeline ? "active" : ""}`}
            onClick={() => { setActivePipeline(null); setShowDebate(false); }}
          >
            <span className="fp-pc-icon">⚡</span>
            <span className="fp-pc-title" style={{ color: "#F59E0B" }}>New Task</span>
          </button>

          <div className="fp-pipeline-list">
            {pipelines.map((p) => (
              <button
                key={p.id}
                className={`fp-pipeline-card ${activePipeline === p.id ? "active" : ""}`}
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

        {/* ── Main Area ── */}
        <div className="fp-main">

          {/* ═══════════════════════════════════════════════
              CREATION FLOW — conversational, mascot-driven
              ═══════════════════════════════════════════════ */}
          {!activePipeline && (
            <div className="fp-create">
              {/* Mascot — large, centered */}
              <div className="fp-mascot-area">
                <img
                  src={companion.pose}
                  alt=""
                  className="fp-mascot-large"
                  onError={(e) => { (e.target as HTMLImageElement).src = `/hub/mascot_${species}.png`; }}
                />
                <div className="fp-speech-bubble">
                  <p>{companion.speech}</p>
                </div>
              </div>

              {/* Input */}
              <div className="fp-create-input-wrap">
                <input
                  className="fp-create-input"
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  placeholder="Build a REST API with user auth..."
                  onKeyDown={(e) => { if (e.key === "Enter" && detected) { /* TODO: submit */ } }}
                />
              </div>

              {/* Auto-detected approach */}
              {detected && (
                <div className="fp-detected">
                  <div className="fp-detected-label">
                    I&apos;ll use the {detected.icon} <strong>{detected.name}</strong> approach:
                  </div>
                  <div className="fp-detected-stages">
                    {detected.stages.map((s, i) => (
                      <span key={i} className="fp-detected-stage" style={{ animationDelay: `${i * 0.08}s` }}>
                        {s}
                        {i < detected.stages.length - 1 && <span className="fp-detected-arrow">→</span>}
                      </span>
                    ))}
                  </div>

                  <button className="fp-start-btn">⚡ Start</button>

                  <button className="fp-customize-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
                    {showAdvanced ? "Hide options ▾" : "Want to customize? ▸"}
                  </button>

                  {showAdvanced && (
                    <div className="fp-advanced">
                      <div className="fp-adv-label">Stages <span>(drag to reorder, click to toggle)</span></div>
                      {detected.stages.map((s, i) => (
                        <div key={i} className="fp-adv-stage">
                          <input type="checkbox" defaultChecked className="fp-adv-check" />
                          <span className="fp-adv-name">{s}</span>
                        </div>
                      ))}
                      <div className="fp-adv-row">
                        <span>If test fails:</span>
                        <select className="fp-adv-select"><option>Rebuild</option><option>Retry</option><option>Stop</option></select>
                      </div>
                      <div className="fp-adv-row">
                        <span>Max attempts:</span>
                        <select className="fp-adv-select"><option>3</option><option>5</option><option>10</option></select>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Example prompts when empty */}
              {!taskInput.trim() && (
                <div className="fp-examples">
                  <div className="fp-examples-label">Try something like:</div>
                  {[
                    "Build a REST API with authentication",
                    "Research our competitors and write a report",
                    "Draft an investor update email",
                  ].map((ex, i) => (
                    <button key={i} className="fp-example-btn" onClick={() => setTaskInput(ex)}>
                      {ex}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════════════════
              PIPELINE DETAIL — running/complete view
              ═══════════════════════════════════════════════ */}
          {current && (
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
                    <span>{current.mode === "mesh" ? "🔗 Mesh" : "🖥️ Local"}</span>
                  </div>
                </div>
              </div>

              {/* ── FORGE with mascot ── */}
              <div className="fp-forge">
                <div className="fp-forge-glow" />

                {/* Stage timeline */}
                <div className="fp-stages">
                  {current.stages.map((stage, i) => (
                    <div key={i} className={`fp-stage ${stage.status}`} style={{ animationDelay: `${i * 0.12}s` }}>
                      <div className={`fp-ember-stone ${stage.status}`}>
                        {stage.status === "done" && <span className="fp-ember-check">✔</span>}
                        {stage.status === "active" && <div className="fp-ember-flames" />}
                        {stage.status === "failed" && <span className="fp-ember-x">✕</span>}
                      </div>
                      <div className="fp-stage-label">{stage.emoji || STAGE_EMOJI[stage.name] || "⚡"} {stage.name}</div>
                      <div className="fp-stage-role">{stage.role}</div>
                      {i < current.stages.length - 1 && (
                        <div className={`fp-fire-trail ${stage.status === "done" ? "lit" : ""}`} />
                      )}
                    </div>
                  ))}
                </div>

                {/* Mascot positioned near active stage */}
                <div
                  className="fp-forge-mascot"
                  style={{
                    left: activeIdx >= 0
                      ? `calc(${((activeIdx + 0.5) / stageCount) * 100}% - 50px)`
                      : current.status === "complete" ? "calc(100% - 120px)" : "20px"
                  }}
                >
                  <img
                    src={companion.pose}
                    alt=""
                    className="fp-forge-mascot-img"
                    onError={(e) => { (e.target as HTMLImageElement).src = `/hub/mascot_${species}.png`; }}
                  />
                </div>
              </div>

              {/* Companion speech */}
              <div className="fp-companion-strip">
                <p>{companion.speech}</p>
              </div>

              {/* Progress */}
              <div className="fp-progress-wrap">
                <div className="fp-progress-bar">
                  <div className="fp-progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <span className="fp-progress-text">{progress}% · {current.eta || "Complete"}</span>
              </div>

              {/* Active stage output */}
              {activeStage?.output && (
                <div className="fp-stage-output">
                  <div className="fp-so-label">Current Output</div>
                  <pre className="fp-so-content">{activeStage.output}</pre>
                </div>
              )}

              {/* Socratic Debate */}
              {current.debate && current.debate.length > 0 && (
                <div className="fp-debate-section">
                  <button className="fp-debate-toggle" onClick={() => setShowDebate(!showDebate)}>
                    🗣️ Socratic Review — the team is debating {showDebate ? "▼" : "▶"}
                  </button>
                  {showDebate && (
                    <div className="fp-debate">
                      <div className="fp-debate-bar-wrap">
                        <span className="fp-debate-bar-label">Consensus</span>
                        <div className="fp-debate-bar"><div className="fp-debate-bar-fill" style={{ width: "45%" }} /></div>
                        <span className="fp-debate-pct">45%</span>
                      </div>
                      {current.debate.map((d, i) => (
                        <div key={i} className="fp-debate-msg" style={{ "--dc": d.color, animationDelay: `${i * 0.1}s` } as React.CSSProperties}>
                          <div className="fp-debate-icon">{d.icon}</div>
                          <div>
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

              {/* Lessons */}
              {current.lessons && current.lessons.length > 0 && (
                <div className="fp-lessons">
                  <h3 className="fp-lessons-title">📜 Lessons Learned</h3>
                  {current.lessons.map((l, i) => <div key={i} className="fp-lesson-item">• {l}</div>)}
                </div>
              )}

              {/* Actions */}
              <div className="fp-actions">
                {current.status === "running" && (
                  <>
                    <button className="fp-action-btn cancel">Cancel</button>
                    <button className="fp-action-btn advance">Force Advance ▶</button>
                  </>
                )}
                {current.status === "complete" && (
                  <button className="fp-action-btn new" onClick={() => setActivePipeline(null)}>⚡ Start New Task</button>
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
const pageCSS = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&display=swap');

  .fp-root {
    min-height: 100vh; width: 100%;
    background: #060609;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    color: #F0DCC8;
  }
  .fp-layout { display: flex; min-height: 100vh; }

  /* ── Sidebar ── */
  .fp-sidebar {
    width: 280px; flex-shrink: 0;
    background: rgba(8,8,14,0.95); backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.04);
    padding: 20px 14px; display: flex; flex-direction: column; gap: 8px;
  }
  .fp-sidebar-header { margin-bottom: 12px; }
  .fp-sidebar-title {
    font-size: 18px; font-weight: 900; margin: 0;
    background: linear-gradient(135deg, #F0DCC8, #F59E0B);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .fp-pipeline-card {
    padding: 12px 14px; border-radius: 12px; cursor: pointer;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    text-align: left; transition: all 0.2s; font-family: 'Outfit'; display: flex; flex-direction: column; gap: 4px;
  }
  .fp-pipeline-card.new-task {
    flex-direction: row; align-items: center; gap: 8px;
    border: 1px dashed rgba(245,158,11,0.15);
  }
  .fp-pipeline-card:hover { background: rgba(245,158,11,0.04); border-color: rgba(245,158,11,0.1); }
  .fp-pipeline-card.active { background: rgba(245,158,11,0.06); border-color: rgba(245,158,11,0.2); box-shadow: 0 0 16px rgba(245,158,11,0.04); }

  .fp-pipeline-list { display: flex; flex-direction: column; gap: 6px; }
  .fp-pc-header { display: flex; align-items: center; gap: 6px; }
  .fp-pc-icon { font-size: 13px; }
  .fp-pc-template { font-size: 9px; font-weight: 800; color: #6A5A4A; text-transform: uppercase; letter-spacing: 1px; }
  .fp-pc-live { margin-left: auto; font-size: 7px; font-weight: 800; color: #34D399; padding: 2px 6px; border-radius: 4px; background: rgba(52,211,153,0.08); animation: fpPulse 2s ease infinite; }
  @keyframes fpPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  .fp-pc-done { margin-left: auto; color: #34D399; font-size: 11px; }
  .fp-pc-title { font-size: 12px; font-weight: 700; color: #C4A882; line-height: 1.3; }
  .fp-pc-stages { display: flex; gap: 3px; }
  .fp-pc-dot { width: 6px; height: 6px; border-radius: 50%; }
  .fp-pc-dot.done { background: #F59E0B; box-shadow: 0 0 4px rgba(245,158,11,0.4); }
  .fp-pc-dot.active { background: #F59E0B; animation: fpDotPulse 1.5s ease infinite; }
  @keyframes fpDotPulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.4); box-shadow: 0 0 8px rgba(245,158,11,0.5); } }
  .fp-pc-dot.pending { background: rgba(255,255,255,0.06); }
  .fp-pc-dot.failed { background: #EF4444; }
  .fp-pc-meta { font-size: 9px; color: #4A3D30; }

  /* ── Main ── */
  .fp-main { flex: 1; overflow-y: auto; }

  /* ═══ CREATION FLOW ═══ */
  .fp-create {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 100vh; padding: 40px;
    gap: 0;
  }

  .fp-mascot-area {
    display: flex; flex-direction: column; align-items: center; gap: 16px;
    margin-bottom: 24px;
  }
  .fp-mascot-large {
    width: 140px; height: 140px; object-fit: contain;
    filter: drop-shadow(0 0 30px rgba(245,158,11,0.25));
    animation: fpBob 4s ease-in-out infinite;
    transition: opacity 0.5s;
    mix-blend-mode: lighten;
  }
  @keyframes fpBob { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }

  .fp-speech-bubble {
    padding: 12px 20px; border-radius: 16px 16px 16px 6px;
    background: rgba(15,13,22,0.75); backdrop-filter: blur(10px);
    border: 1px solid rgba(245,158,11,0.1);
    max-width: 420px; text-align: center;
  }
  .fp-speech-bubble p { margin: 0; font-size: 14px; color: #C4A882; line-height: 1.5; }

  .fp-create-input-wrap { width: 100%; max-width: 500px; margin-bottom: 16px; }
  .fp-create-input {
    width: 100%; padding: 16px 20px; border-radius: 14px;
    background: rgba(15,13,22,0.6); border: 1.5px solid rgba(255,255,255,0.06);
    color: #F0DCC8; font-size: 15px; font-weight: 500;
    font-family: 'Outfit'; outline: none; transition: all 0.3s;
  }
  .fp-create-input:focus { border-color: rgba(245,158,11,0.3); box-shadow: 0 0 24px rgba(245,158,11,0.06); }
  .fp-create-input::placeholder { color: rgba(240,220,200,0.2); }

  /* Detected approach */
  .fp-detected {
    display: flex; flex-direction: column; align-items: center; gap: 14px;
    animation: fsFadeUp 0.35s ease;
  }
  @keyframes fsFadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  .fp-detected-label { font-size: 13px; color: #6A5A4A; }
  .fp-detected-label strong { color: #F59E0B; }
  .fp-detected-stages { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; justify-content: center; }
  .fp-detected-stage {
    font-size: 14px; font-weight: 700; color: #C4A882;
    display: flex; align-items: center; gap: 4px;
    animation: fsFadeUp 0.3s ease both;
  }
  .fp-detected-arrow { color: #4A3D30; margin: 0 2px; }

  .fp-start-btn {
    padding: 14px 40px; border-radius: 14px; border: none;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 16px; font-weight: 900;
    font-family: 'Outfit'; cursor: pointer; transition: all 0.2s;
    box-shadow: 0 6px 24px rgba(245,158,11,0.25);
  }
  .fp-start-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 36px rgba(245,158,11,0.35); }

  .fp-customize-toggle {
    background: none; border: none; color: #4A3D30; font-size: 12px;
    cursor: pointer; font-family: 'Outfit'; transition: color 0.2s;
  }
  .fp-customize-toggle:hover { color: #C4A882; }

  .fp-advanced {
    padding: 16px; border-radius: 12px; width: 100%; max-width: 400px;
    background: rgba(15,13,22,0.5); border: 1px solid rgba(255,255,255,0.05);
    animation: fsFadeUp 0.3s ease;
  }
  .fp-adv-label { font-size: 10px; font-weight: 800; color: #6A5A4A; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
  .fp-adv-label span { font-weight: 500; text-transform: none; letter-spacing: 0; }
  .fp-adv-stage { display: flex; align-items: center; gap: 8px; padding: 6px 0; }
  .fp-adv-check { accent-color: #F59E0B; }
  .fp-adv-name { font-size: 13px; color: #C4A882; }
  .fp-adv-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-top: 1px solid rgba(255,255,255,0.04); margin-top: 4px; }
  .fp-adv-row span { font-size: 12px; color: #6A5A4A; }
  .fp-adv-select {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    color: #C4A882; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-family: 'Outfit';
  }

  /* Example prompts */
  .fp-examples { display: flex; flex-direction: column; align-items: center; gap: 8px; margin-top: 4px; }
  .fp-examples-label { font-size: 11px; color: #3A3530; }
  .fp-example-btn {
    padding: 8px 16px; border-radius: 10px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    color: #6A5A4A; font-size: 12px; cursor: pointer;
    font-family: 'Outfit'; transition: all 0.2s;
  }
  .fp-example-btn:hover { color: #C4A882; border-color: rgba(245,158,11,0.1); background: rgba(245,158,11,0.03); }

  /* ═══ DETAIL VIEW ═══ */
  .fp-detail { padding: 28px 32px; animation: fsFadeUp 0.4s ease; }
  .fp-detail-header { margin-bottom: 16px; }
  .fp-detail-title { font-size: 20px; font-weight: 900; color: #F0DCC8; margin: 0 0 8px; }
  .fp-detail-meta { display: flex; gap: 8px; flex-wrap: wrap; }
  .fp-detail-meta span { font-size: 10px; color: #4A3D30; padding: 3px 8px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; font-weight: 600; }
  .fp-status-badge.running { color: #34D399; border-color: rgba(52,211,153,0.15); background: rgba(52,211,153,0.06); }
  .fp-status-badge.complete { color: #F59E0B; border-color: rgba(245,158,11,0.15); background: rgba(245,158,11,0.06); }

  /* ── FORGE ── */
  .fp-forge {
    position: relative; padding: 50px 20px 80px;
    margin-bottom: 8px; border-radius: 16px;
    background: url('/hub/forge_background.png') center/cover no-repeat;
    border: 1px solid rgba(245,158,11,0.1);
    overflow: hidden; min-height: 220px;
  }
  .fp-forge-glow {
    position: absolute; bottom: 0; left: 0; right: 0; height: 70%;
    background: radial-gradient(ellipse 80% 100% at 50% 100%, rgba(245,158,11,0.1), transparent);
    pointer-events: none;
  }
  .fp-stages { display: flex; align-items: center; justify-content: center; gap: 10px; position: relative; z-index: 2; }
  .fp-stage {
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    position: relative; min-width: 100px;
    animation: fpStageIn 0.4s ease both;
  }
  @keyframes fpStageIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }

  .fp-ember-stone {
    width: 72px; height: 72px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    position: relative; transition: all 0.4s;
    background-size: contain; background-repeat: no-repeat; background-position: center;
    mix-blend-mode: lighten;
  }
  .fp-ember-stone.done { background-image: url('/hub/ember_stone_done.png'); filter: drop-shadow(0 0 15px rgba(245,158,11,0.4)); }
  .fp-ember-stone.active { background-image: url('/hub/ember_stone_active.png'); filter: drop-shadow(0 0 25px rgba(245,158,11,0.6)); animation: fpEmberPulse 2s ease infinite; }
  @keyframes fpEmberPulse { 0%,100% { filter: drop-shadow(0 0 20px rgba(245,158,11,0.4)); transform: scale(1); } 50% { filter: drop-shadow(0 0 35px rgba(245,158,11,0.7)); transform: scale(1.06); } }
  .fp-ember-stone.pending { background-image: url('/hub/ember_stone_pending.png'); opacity: 0.6; }
  .fp-ember-stone.failed { background-image: url('/hub/ember_stone_active.png'); filter: drop-shadow(0 0 15px rgba(239,68,68,0.5)) hue-rotate(-40deg); }
  .fp-ember-check { color: #FEF3C7; font-size: 18px; font-weight: 900; text-shadow: 0 0 8px rgba(245,158,11,0.8); }
  .fp-ember-x { color: #fff; font-size: 18px; font-weight: 900; }
  .fp-ember-flames {
    position: absolute; top: -14px; left: 50%; transform: translateX(-50%);
    width: 28px; height: 28px;
    background: radial-gradient(circle, rgba(255,200,50,0.9), transparent 70%);
    border-radius: 50%; filter: blur(4px);
    animation: fpFlame 0.8s ease infinite alternate;
  }
  @keyframes fpFlame { 0% { transform: translateX(-50%) scale(1); opacity: 0.5; } 100% { transform: translateX(-50%) translateY(-6px) scale(1.3); opacity: 1; } }

  .fp-stage-label { font-size: 12px; font-weight: 800; color: #F0DCC8; text-shadow: 0 1px 4px rgba(0,0,0,0.6); }
  .fp-stage-role { font-size: 8px; color: #8A7A6A; text-transform: uppercase; letter-spacing: 0.5px; }

  .fp-fire-trail {
    position: absolute; top: 28px; left: calc(50% + 36px);
    width: 28px; height: 18px;
    background: url('/hub/fire_trail.png') center/cover no-repeat;
    opacity: 0.12; transition: all 0.5s;
    mix-blend-mode: lighten;
  }
  .fp-fire-trail.lit { opacity: 0.65; filter: drop-shadow(0 0 6px rgba(245,158,11,0.3)); }

  /* Mascot in forge — slides to active stage */
  .fp-forge-mascot {
    position: absolute; bottom: 8px; z-index: 10;
    transition: left 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .fp-forge-mascot-img {
    width: 100px; height: 100px; object-fit: contain;
    filter: drop-shadow(0 0 20px rgba(245,158,11,0.3));
    animation: fpBob 3.5s ease-in-out infinite;
    mix-blend-mode: lighten;
  }

  /* Companion speech strip */
  .fp-companion-strip {
    padding: 8px 16px; border-radius: 10px;
    background: rgba(15,13,22,0.5); border: 1px solid rgba(245,158,11,0.06);
    margin-bottom: 16px;
  }
  .fp-companion-strip p { margin: 0; font-size: 12px; color: #C4A882; font-style: italic; }

  /* Progress */
  .fp-progress-wrap { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
  .fp-progress-bar { flex: 1; height: 3px; border-radius: 2px; background: rgba(255,255,255,0.04); overflow: hidden; }
  .fp-progress-fill { height: 100%; border-radius: 2px; background: linear-gradient(90deg, #D97706, #F59E0B); box-shadow: 0 0 6px rgba(245,158,11,0.3); transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
  .fp-progress-text { font-size: 10px; color: #4A3D30; font-weight: 600; }

  .fp-stage-output { padding: 12px; border-radius: 10px; background: rgba(15,13,22,0.5); border: 1px solid rgba(255,255,255,0.04); margin-bottom: 16px; }
  .fp-so-label { font-size: 9px; font-weight: 800; color: #6A5A4A; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
  .fp-so-content { font-size: 12px; color: #C4A882; font-family: 'JetBrains Mono', monospace; white-space: pre-wrap; margin: 0; }

  /* Debate */
  .fp-debate-section { margin-bottom: 16px; }
  .fp-debate-toggle { padding: 10px 14px; border-radius: 10px; background: rgba(167,139,250,0.04); border: 1px solid rgba(167,139,250,0.08); color: #A78BFA; font-size: 12px; font-weight: 700; cursor: pointer; font-family: 'Outfit'; width: 100%; text-align: left; transition: all 0.2s; }
  .fp-debate-toggle:hover { background: rgba(167,139,250,0.08); }
  .fp-debate { padding: 14px 0; display: flex; flex-direction: column; gap: 10px; }
  .fp-debate-bar-wrap { display: flex; align-items: center; gap: 8px; }
  .fp-debate-bar-label { font-size: 9px; font-weight: 800; color: #6A5A4A; }
  .fp-debate-bar { flex: 1; height: 3px; border-radius: 2px; background: rgba(255,255,255,0.04); }
  .fp-debate-bar-fill { height: 100%; border-radius: 2px; background: linear-gradient(90deg, #A78BFA, #8B5CF6); }
  .fp-debate-pct { font-size: 10px; color: #A78BFA; font-weight: 700; }
  .fp-debate-msg { display: flex; gap: 10px; padding: 10px; border-radius: 10px; background: rgba(255,255,255,0.02); border: 1px solid color-mix(in srgb, var(--dc) 10%, transparent); animation: fsFadeUp 0.3s ease both; }
  .fp-debate-icon { font-size: 18px; flex-shrink: 0; }
  .fp-debate-persona { font-size: 10px; font-weight: 800; margin-bottom: 2px; }
  .fp-debate-text { font-size: 12px; color: #C4A882; line-height: 1.5; margin: 0; }
  .fp-intervene-btn { padding: 8px 16px; border-radius: 10px; border: 1px solid rgba(167,139,250,0.12); background: rgba(167,139,250,0.05); color: #A78BFA; font-size: 11px; font-weight: 800; cursor: pointer; font-family: 'Outfit'; align-self: center; transition: all 0.2s; }
  .fp-intervene-btn:hover { background: rgba(167,139,250,0.12); }

  /* Lessons */
  .fp-lessons { padding: 14px; border-radius: 10px; background: rgba(245,158,11,0.03); border: 1px solid rgba(245,158,11,0.06); margin-bottom: 16px; }
  .fp-lessons-title { font-size: 13px; font-weight: 800; color: #F59E0B; margin: 0 0 8px; }
  .fp-lesson-item { font-size: 12px; color: #C4A882; line-height: 1.5; margin-bottom: 2px; }

  /* Actions */
  .fp-actions { display: flex; gap: 10px; }
  .fp-action-btn { padding: 8px 18px; border-radius: 10px; font-size: 12px; font-weight: 700; cursor: pointer; font-family: 'Outfit'; transition: all 0.2s; }
  .fp-action-btn.cancel { background: transparent; border: 1px solid rgba(239,68,68,0.12); color: #EF4444; }
  .fp-action-btn.cancel:hover { background: rgba(239,68,68,0.06); }
  .fp-action-btn.advance { background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.12); color: #F59E0B; }
  .fp-action-btn.advance:hover { background: rgba(245,158,11,0.12); }
  .fp-action-btn.new { background: linear-gradient(135deg, #D97706, #F59E0B); border: none; color: #0A0A0A; font-weight: 800; }
  .fp-action-btn.new:hover { transform: translateY(-1px); }
`;

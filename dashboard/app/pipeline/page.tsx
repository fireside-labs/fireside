"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import Link from "next/link";
import { API_BASE, getWebSocketUrl, intervenePipeline, approvePipeline, rejectPipeline } from "../../lib/api";
import { DiscoveryCard } from "@/components/GuidedTour";
import WorkflowBuilder from "@/components/WorkflowBuilder";

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
  status: "running" | "complete" | "failed" | "escalated" | "waiting_approval";
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

interface AgentMessage {
  id: string;
  role: string;
  icon: string;
  color: string;
  message: string;
  ts: number;
  type: "normal" | "verdict_pass" | "verdict_fail" | "feedback" | "debate_start" | "debate_end" | "debate" | "escalation" | "lesson" | "iteration" | "typing";
}

const ROLE_COLORS: Record<string, string> = {
  planner: "#60A5FA",
  coder: "#22D3EE",
  backend: "#22D3EE",
  frontend: "#22D3EE",
  tester: "#FB923C",
  reviewer: "#A78BFA",
  architect: "#A78BFA",
  devil_advocate: "#F87171",
  end_user: "#60A5FA",
  distiller: "#FBBF24",
  system: "#6B7280",
};

const ROLE_ICONS: Record<string, string> = {
  planner: "🧠",
  coder: "⚡",
  backend: "⚡",
  frontend: "🎨",
  tester: "🔍",
  reviewer: "👤",
  architect: "🏛️",
  devil_advocate: "😈",
  end_user: "👤",
  distiller: "📜",
  system: "⚙️",
};

// ── Stage emoji mapping ──
const STAGE_EMOJI: Record<string, string> = {
  Spec: "📜", Plan: "📜", Outline: "📜", Context: "📜", Gather: "🔎",
  Build: "🔨", Content: "🔨", Draft: "✍️", Design: "🎨",
  Test: "🔍", Analyze: "📊", Insights: "💡",
  Review: "👤", Write: "✍️", Report: "📋", Execute: "⚡",
};

// Pipelines are loaded from the backend — start empty
const INITIAL_PIPELINES: Pipeline[] = [];


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


// Agent feed starts empty — populated from WebSocket events
const INITIAL_AGENT_FEED: AgentMessage[] = [];


export default function PipelinePage() {

  const [pipelines, setPipelines] = useState<Pipeline[]>(INITIAL_PIPELINES);
  const [activePipeline, setActivePipeline] = useState<string | null>(null);
  const [taskInput, setTaskInput] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showDebate, setShowDebate] = useState(false);
  const [agentFeed, setAgentFeed] = useState<AgentMessage[]>(INITIAL_AGENT_FEED);
  const [showFeed, setShowFeed] = useState(true);
  const [interveneText, setInterveneText] = useState("");
  const [showIntervene, setShowIntervene] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [fileToast, setFileToast] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [creationMode, setCreationMode] = useState<"text" | "visual">("text");
  const feedEndRef = useRef<HTMLDivElement>(null);

  // ── WebSocket: live pipeline events → agent feed ──
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      try {
        ws = new WebSocket(getWebSocketUrl());
        ws.onopen = () => setWsConnected(true);
        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimer = setTimeout(connect, 3000);
        };
        ws.onmessage = (e) => {
          try {
            const event = JSON.parse(e.data);
            const topic: string = event.topic || "";
            const payload = event.payload || {};

            // Convert pipeline events into AgentMessage format
            if (topic.startsWith("pipeline.")) {
              const msg = pipelineEventToMessage(topic, payload);
              if (msg) {
                setAgentFeed(prev => [...prev, msg]);
                // Auto-scroll feed
                setTimeout(() => feedEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
              }

              // File created toast
              if (topic === "pipeline.file_created") {
                const fname = (payload.path || "").split("/").pop() || (payload.path || "").split("\\").pop() || "file";
                setFileToast(`📄 Created: ${fname}`);
                setTimeout(() => setFileToast(null), 5000);
              }

              // Update pipeline status from events
              if (topic === "pipeline.stage_complete" || topic === "pipeline.shipped" || topic === "pipeline.escalated") {
                updatePipelineFromEvent(topic, payload);
              }
            }
          } catch {
            // ignore parse errors
          }
        };
      } catch {
        reconnectTimer = setTimeout(connect, 3000);
      }
    }

    connect();
    return () => {
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  // Convert WebSocket pipeline events to agent feed messages
  const pipelineEventToMessage = useCallback((topic: string, payload: Record<string, unknown>): AgentMessage | null => {
    const ts = Date.now();
    const id = `ws_${ts}_${Math.random().toString(36).slice(2, 6)}`;
    const stage = (payload.stage as string) || "";

    switch (topic) {
      case "pipeline.stage_started":
        return { id, role: "system", icon: "▶", color: "#60A5FA", message: `Stage started: ${stage} (${payload.stage_index as number + 1}/${payload.total_stages})`, ts, type: "normal" };
      case "pipeline.stage_complete": {
        const verdict = payload.verdict as string;
        const duration = payload.duration_s as number;
        const eta = payload.eta_seconds as number;
        const type: AgentMessage["type"] = verdict === "pass" || verdict === "ship" ? "verdict_pass" : verdict === "fail" ? "verdict_fail" : "normal";
        return { id, role: stage || "system", icon: verdict === "pass" ? "✔" : verdict === "fail" ? "✕" : "→", color: verdict === "pass" ? "#34D399" : verdict === "fail" ? "#F87171" : "#F59E0B", message: `Stage ${stage}: ${verdict.toUpperCase()}${duration ? ` (${duration}s)` : ""}${eta ? ` · ETA ~${Math.round(eta / 60)}min` : ""}`, ts, type };
      }
      case "pipeline.file_created":
        return { id, role: "system", icon: "📄", color: "#A78BFA", message: `File created: ${payload.path}`, ts, type: "normal" };
      case "pipeline.shipped": {
        const dur = payload.duration_s as number;
        const tokens = payload.tokens as { prompt?: number; completion?: number } | undefined;
        const totalTokens = tokens ? (tokens.prompt || 0) + (tokens.completion || 0) : 0;
        return { id, role: "system", icon: "🚀", color: "#F59E0B", message: `Pipeline complete! ${dur ? `${Math.round(dur / 60)}min` : ""}${totalTokens ? ` · ${(totalTokens / 1000).toFixed(1)}K tokens` : ""}`, ts, type: "verdict_pass" };
      }
      case "pipeline.escalated":
        return { id, role: "system", icon: "🖐", color: "#F87171", message: `Escalated: ${payload.reason || "Max iterations reached"}`, ts, type: "escalation" };
      case "pipeline.human_intervention":
        return { id, role: "you", icon: "💬", color: "#22D3EE", message: `Guidance: ${payload.guidance}`, ts, type: "normal" };
      case "pipeline.iteration":
        return { id, role: "system", icon: "🔄", color: "#4A3D30", message: `Iteration ${payload.iteration} — ${payload.stage} ${payload.verdict}`, ts, type: "iteration" };
      case "pipeline.gate_waiting":
        return { id, role: "system", icon: "⏸", color: "#FBBF24", message: `✉️ Approval required: ${payload.prompt || "Continue?"}`, ts, type: "normal" };
      case "pipeline.gate_approved":
        return { id, role: "you", icon: "✅", color: "#34D399", message: `Gate approved — pipeline continuing`, ts, type: "verdict_pass" };
      case "pipeline.gate_rejected":
        return { id, role: "you", icon: "❌", color: "#F87171", message: `Gate rejected — ${payload.stage || "stage"} declined`, ts, type: "verdict_fail" };
      default:
        return null;
    }
  }, []);

  // Update pipeline state from incoming events
  const updatePipelineFromEvent = useCallback((topic: string, payload: Record<string, unknown>) => {
    const pipelineId = payload.pipeline_id as string;
    if (!pipelineId) return;

    setPipelines(prev => prev.map(p => {
      if (p.id !== pipelineId) return p;
      if (topic === "pipeline.shipped") {
        return { ...p, status: "complete" as const, stages: p.stages.map(s => ({ ...s, status: "done" as const })) };
      }
      if (topic === "pipeline.escalated") {
        return { ...p, status: "escalated" as const };
      }
      if (topic === "pipeline.stage_complete") {
        const stageIdx = payload.stage_index as number;
        const verdict = payload.verdict as string;
        if (typeof stageIdx === "number") {
          return {
            ...p,
            eta: payload.eta_seconds ? `~${Math.round((payload.eta_seconds as number) / 60)}min` : p.eta,
            stages: p.stages.map((s, i) => {
              if (i === stageIdx) return { ...s, status: (verdict === "pass" || verdict === "ship" ? "done" : "failed") as Stage["status"] };
              if (i === stageIdx + 1 && (verdict === "pass" || verdict === "ship")) return { ...s, status: "active" as Stage["status"] };
              return s;
            }),
          };
        }
      }
      if (topic === "pipeline.gate_waiting") {
        return { ...p, status: "waiting_approval" as const };
      }
      if (topic === "pipeline.gate_approved") {
        return { ...p, status: "running" as const };
      }
      return p;
    }));
  }, []);

  // Wire intervene to real API
  const handleIntervene = useCallback(async () => {
    if (!interveneText.trim() || !activePipeline) return;
    try {
      await intervenePipeline(activePipeline, interveneText.trim());
      setAgentFeed(prev => [...prev, {
        id: `int_${Date.now()}`,
        role: "you",
        icon: "💬",
        color: "#22D3EE",
        message: interveneText.trim(),
        ts: Date.now(),
        type: "normal" as const,
      }]);
    } catch (e) {
      console.error("Intervention failed:", e);
    }
    setShowIntervene(false);
    setInterveneText("");
  }, [interveneText, activePipeline]);

  const submitTask = async () => {
    if (!taskInput.trim() || !detected || submitting) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/pipeline/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: taskInput.trim(), mode: "auto" }),
      });
      const data = await res.json();
      if (data.pipeline_id || data.ok) {
        const newId = data.pipeline_id || `p${Date.now()}`;
        const newPipeline: Pipeline = {
          id: newId,
          title: taskInput.trim(),
          template: detected.name,
          templateIcon: detected.icon,
          status: "running",
          iteration: 1,
          maxIterations: 10,
          stages: detected.stages.map((s, i) => ({
            name: s.replace(/^.\s/, ""),
            emoji: s.charAt(0),
            status: i === 0 ? "active" : "pending",
            role: "system",
          })),
          startedAt: new Date(),
          eta: "estimating...",
          mode: "local",
        };
        setPipelines(prev => [newPipeline, ...prev]);
        setActivePipeline(newId);
        setTaskInput("");
      }
    } catch (e) {
      console.error("Pipeline start failed:", e);
    } finally {
      setSubmitting(false);
    }
  };



  const current = useMemo(() => pipelines.find(p => p.id === activePipeline), [pipelines, activePipeline]);
  const progress = current ? Math.round((current.stages.filter(s => s.status === "done").length / current.stages.length) * 100) : 0;
  const detected = taskInput.trim() ? detectTemplate(taskInput) : null;



  return (
    <div className="fp-root">
      <style>{pageCSS}</style>

      <DiscoveryCard pageKey="/pipeline" />

      <div className="fp-layout">
        {/* ── Sidebar ── */}
        <div className="fp-sidebar">
          <div className="fp-sidebar-header">
            <Link href="/" className="fp-back-hub">🔥 Hub</Link>
            <h2 className="fp-sidebar-title">Tasks</h2>
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
              CREATION FLOW — text or visual
              ═══════════════════════════════════════════════ */}
          {!activePipeline && creationMode === "visual" && (
            <div className="fp-builder-container">
              <WorkflowBuilder
                onRun={() => setCreationMode("text")}
                onClose={() => setCreationMode("text")}
              />
            </div>
          )}

          {!activePipeline && creationMode === "text" && (
            <div className="fp-create">

              {/* Mode toggle */}
              <div className="fp-mode-toggle">
                <button
                  className="fp-mode-btn active"
                  onClick={() => setCreationMode("text")}
                >✏️ Text</button>
                <button
                  className="fp-mode-btn"
                  onClick={() => setCreationMode("visual")}
                >🔧 Visual Builder</button>
              </div>

              {/* Input */}
              <div className="fp-create-input-wrap">
                <input
                  className="fp-create-input"
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  placeholder="Build a REST API with user auth..."
                  onKeyDown={(e) => { if (e.key === "Enter" && detected) submitTask(); }}
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

                  <button className="fp-start-btn" onClick={submitTask} disabled={submitting}>
                    {submitting ? "⏳ Starting..." : "⚡ Start"}
                  </button>

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
                      {current.status === "running" ? "🔄 Running" : current.status === "complete" ? "✅ Complete" : current.status === "waiting_approval" ? "⏸ Approval Gate" : "⚠️ " + current.status}
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

              </div>

              {/* Progress */}
              <div className="fp-progress-wrap">
                <div className="fp-progress-bar">
                  <div className="fp-progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <span className="fp-progress-text">{progress}% · {current.eta || "Complete"}</span>
              </div>

              {/* ═══ AGENT FEED ═══ */}
              {current.status === "running" && (
                <div className="fp-feed-section">
                  <button
                    className="fp-feed-toggle"
                    onClick={() => setShowFeed(!showFeed)}
                  >
                    <span className="fp-feed-toggle-dot" />
                    Agent Feed — {agentFeed.length} messages
                    <span className="fp-feed-toggle-arrow">{showFeed ? "▼" : "▶"}</span>
                  </button>

                  {showFeed && (
                    <div className="fp-feed-wrap">
                      <div className="fp-feed">
                        {agentFeed.map((msg, i) => {
                          // Iteration markers
                          if (msg.type === "iteration") {
                            return (
                              <div key={msg.id} className="fp-feed-iter" style={{ animationDelay: `${i * 0.03}s` }}>
                                <div className="fp-feed-iter-line" />
                                <span className="fp-feed-iter-label">{msg.message}</span>
                                <div className="fp-feed-iter-line" />
                              </div>
                            );
                          }

                          // Typing indicator
                          if (msg.type === "typing") {
                            return (
                              <div key={msg.id} className="fp-feed-typing">
                                <div className="fp-feed-accent" style={{ background: msg.color } as React.CSSProperties} />
                                <div className="fp-feed-icon">{msg.icon}</div>
                                <div className="fp-feed-body">
                                  <span className="fp-feed-role" style={{ color: msg.color }}>{msg.role}</span>
                                  <span className="fp-feed-typing-dots">
                                    <span className="fp-dot" /><span className="fp-dot" /><span className="fp-dot" />
                                  </span>
                                  <span className="fp-feed-typing-text">{msg.message}</span>
                                </div>
                              </div>
                            );
                          }

                          // Debate messages — grouped with indent
                          const isDebate = msg.type === "debate" || msg.type === "debate_start";

                          return (
                            <div
                              key={msg.id}
                              className={`fp-feed-msg ${msg.type}${isDebate ? " fp-debate-indent" : ""}`}
                              style={{
                                "--agent-color": msg.color,
                                animationDelay: `${i * 0.03}s`,
                              } as React.CSSProperties}
                            >
                              <div className="fp-feed-accent" />
                              <div className="fp-feed-icon">{msg.icon}</div>
                              <div className="fp-feed-body">
                                <div className="fp-feed-header">
                                  <span className="fp-feed-role" style={{ color: msg.color }}>
                                    {msg.role}
                                  </span>
                                  {isDebate && <span className="fp-feed-debate-tag">DEBATE</span>}
                                  <span className="fp-feed-ts">
                                    {new Date(msg.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                  </span>
                                </div>
                                <p className="fp-feed-text">{msg.message}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Sticky intervene bar — always visible */}
                      <div className="fp-feed-intervene-sticky">
                        {!showIntervene ? (
                          <button
                            className="fp-feed-intervene-btn"
                            onClick={() => setShowIntervene(true)}
                          >
                            🖐️ Intervene — Jump In
                          </button>
                        ) : (
                          <div className="fp-feed-intervene-input-wrap">
                            <input
                              className="fp-feed-intervene-input"
                              value={interveneText}
                              onChange={(e) => setInterveneText(e.target.value)}
                              placeholder="Tell the agents what to do differently..."
                              onKeyDown={(e) => {
                                if (e.key === "Enter" && interveneText.trim()) {
                                  handleIntervene();
                                }
                              }}
                              autoFocus
                            />
                            <button
                              className="fp-feed-send-btn"
                              onClick={handleIntervene}
                            >
                              Send ⚡
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
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
                    <button className="fp-action-btn cancel" onClick={() => {
                      setPipelines(prev => prev.map(p =>
                        p.id === current.id ? { ...p, status: "failed" as const } : p
                      ));
                      // Also try to cancel via API
                      fetch(`${API_BASE}/api/v1/pipeline/${current.id}`, { method: "DELETE" }).catch(() => {});
                    }}>Cancel</button>
                    <button className="fp-action-btn advance" onClick={() => {
                      fetch(`${API_BASE}/api/v1/pipeline/${current.id}/advance`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ action: "advance" }),
                      }).catch(() => {});
                      setPipelines(prev => prev.map(p => {
                        if (p.id !== current.id) return p;
                        const newStages = p.stages.map((s, i) => {
                          if (s.status === "active") return { ...s, status: "done" as const };
                          const prevDone = i > 0 && p.stages[i - 1].status === "active";
                          if (s.status === "pending" && prevDone) return { ...s, status: "active" as const };
                          return s;
                        });
                        const allDone = newStages.every(s => s.status === "done");
                        return { ...p, stages: newStages, status: allDone ? "complete" as const : "running" as const };
                      }));
                    }}>Force Advance ▶</button>
                  </>
                )}
                {current.status === "complete" && (
                  <button className="fp-action-btn new" onClick={() => setActivePipeline(null)}>⚡ Start New Task</button>
                )}
                {current.status === "escalated" && (
                  <button className="fp-action-btn advance" onClick={() => setShowIntervene(true)}>💬 Give Guidance</button>
                )}
                {current.status === "waiting_approval" && (
                  <div className="fp-gate-ui">
                    <div className="fp-gate-prompt">
                      <span className="fp-gate-icon">⏸</span>
                      <span className="fp-gate-text">Approval required to continue</span>
                    </div>
                    <div className="fp-gate-actions">
                      <button className="fp-action-btn fp-gate-approve" onClick={async () => {
                        await approvePipeline(current.id);
                        setPipelines(prev => prev.map(p => p.id === current.id ? { ...p, status: "running" as const } : p));
                      }}>✅ Approve</button>
                      <button className="fp-action-btn fp-gate-reject" onClick={async () => {
                        await rejectPipeline(current.id);
                        setPipelines(prev => prev.map(p => p.id === current.id ? { ...p, status: "escalated" as const } : p));
                      }}>❌ Reject</button>
                    </div>
                  </div>
                )}
              </div>

              {/* ═══ OUTPUT VIEWER — files + tokens ═══ */}
              {current.status === "complete" && (
                <div className="fp-output-section">
                  <h3 className="fp-output-title">📦 Pipeline Output</h3>

                  {/* Token usage */}
                  <div className="fp-output-tokens">
                    <div className="fp-token-stat">
                      <span className="fp-token-label">⏱ Duration</span>
                      <span className="fp-token-value">{current.eta || "—"}</span>
                    </div>
                    <div className="fp-token-stat">
                      <span className="fp-token-label">🔄 Iterations</span>
                      <span className="fp-token-value">{current.iteration}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* File created toast */}
              {fileToast && (
                <div className="fp-file-toast">
                  {fileToast}
                </div>
              )}

              {/* WebSocket status */}
              <div className="fp-ws-status">
                <span className={wsConnected ? "fp-ws-dot connected" : "fp-ws-dot"} />
                {wsConnected ? "Live" : "Reconnecting..."}
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
  .fp-sidebar-header { margin-bottom: 12px; display: flex; align-items: center; gap: 12px; }
  .fp-back-hub {
    padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 800;
    background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.12);
    color: #C4A882; text-decoration: none; transition: all 0.2s; font-family: 'Outfit';
  }
  .fp-back-hub:hover { background: rgba(245,158,11,0.12); color: #F59E0B; border-color: rgba(245,158,11,0.25); }
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
    animation: fpBob 4s ease-in-out infinite;
    transition: opacity 0.5s;
    mix-blend-mode: screen;
    mask-image: radial-gradient(ellipse 70% 70% at center, black 40%, transparent 72%);
    -webkit-mask-image: radial-gradient(ellipse 70% 70% at center, black 40%, transparent 72%);
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

  /* ── Mode toggle ── */
  .fp-mode-toggle {
    display: flex; gap: 4px; margin-bottom: 24px;
    padding: 3px; border-radius: 10px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
  }
  .fp-mode-btn {
    padding: 6px 16px; border-radius: 8px; border: none;
    background: transparent; color: #4A3D30; font-size: 12px; font-weight: 700;
    cursor: pointer; font-family: 'Outfit'; transition: all 0.2s;
  }
  .fp-mode-btn.active { background: rgba(245,158,11,0.08); color: #F59E0B; }
  .fp-mode-btn:hover:not(.active) { color: #C4A882; }
  .fp-builder-container { flex: 1; display: flex; flex-direction: column; min-height: 0; }
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
  .fp-status-badge.waiting_approval { color: #FBBF24; border-color: rgba(251,191,36,0.2); background: rgba(251,191,36,0.08); animation: fpPulse 2s ease infinite; }
  .fp-status-badge.escalated { color: #F87171; border-color: rgba(248,113,113,0.15); background: rgba(248,113,113,0.06); }

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
    animation: fpBob 3.5s ease-in-out infinite;
    mix-blend-mode: screen;
    mask-image: radial-gradient(ellipse 70% 70% at center, black 40%, transparent 72%);
    -webkit-mask-image: radial-gradient(ellipse 70% 70% at center, black 40%, transparent 72%);
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

  /* ═══ AGENT FEED ═══ */
  .fp-feed-section { margin-bottom: 16px; }
  .fp-feed-toggle {
    padding: 10px 16px; border-radius: 12px; width: 100%; text-align: left;
    background: rgba(34,211,238,0.04); border: 1px solid rgba(34,211,238,0.08);
    color: #22D3EE; font-size: 12px; font-weight: 700; cursor: pointer;
    font-family: 'Outfit'; transition: all 0.2s;
    display: flex; align-items: center; gap: 8px;
  }
  .fp-feed-toggle:hover { background: rgba(34,211,238,0.08); }
  .fp-feed-toggle-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #22D3EE;
    animation: fpPulse 2s ease infinite; box-shadow: 0 0 8px rgba(34,211,238,0.5);
  }
  .fp-feed-toggle-arrow { margin-left: auto; font-size: 10px; opacity: 0.5; }

  .fp-feed {
    margin-top: 8px; border-radius: 12px;
    background: rgba(6,6,12,0.8); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.04);
    padding: 8px; max-height: 500px; overflow-y: auto;
    display: flex; flex-direction: column; gap: 4px;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.06) transparent;
  }
  .fp-feed::-webkit-scrollbar { width: 4px; }
  .fp-feed::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }

  .fp-feed-msg {
    display: flex; gap: 8px; padding: 8px 10px;
    border-radius: 10px; position: relative;
    background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.02);
    animation: fpFeedIn 0.3s ease both; transition: all 0.2s;
  }
  .fp-feed-msg:hover { background: rgba(255,255,255,0.03); }
  @keyframes fpFeedIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

  .fp-feed-accent {
    position: absolute; left: 0; top: 6px; bottom: 6px; width: 3px;
    border-radius: 2px; background: var(--agent-color); opacity: 0.6;
  }
  .fp-feed-msg.verdict_pass { background: rgba(52,211,153,0.04); border-color: rgba(52,211,153,0.1); }
  .fp-feed-msg.verdict_pass .fp-feed-accent { background: #34D399; opacity: 1; }
  .fp-feed-msg.verdict_fail { background: rgba(239,68,68,0.04); border-color: rgba(239,68,68,0.1); }
  .fp-feed-msg.verdict_fail .fp-feed-accent { background: #EF4444; opacity: 1; }
  .fp-feed-msg.feedback { background: rgba(251,191,36,0.03); border-color: rgba(251,191,36,0.08); border-style: dashed; }
  .fp-feed-msg.feedback .fp-feed-accent { background: #FBBF24; opacity: 0.8; }
  .fp-feed-msg.debate_start { background: rgba(167,139,250,0.04); border-color: rgba(167,139,250,0.1); }
  .fp-feed-msg.debate_start .fp-feed-accent { background: #A78BFA; opacity: 1; }
  .fp-feed-msg.debate_end .fp-feed-accent { background: #34D399; opacity: 1; }
  .fp-feed-msg.escalation { background: rgba(239,68,68,0.06); border-color: rgba(239,68,68,0.15); animation: fpEscalationPulse 2s ease infinite; }
  @keyframes fpEscalationPulse { 0%,100% { box-shadow: none; } 50% { box-shadow: 0 0 16px rgba(239,68,68,0.1); } }
  .fp-feed-msg.escalation .fp-feed-accent { background: #EF4444; opacity: 1; width: 4px; }
  .fp-feed-msg.lesson { background: rgba(245,158,11,0.03); border-color: rgba(245,158,11,0.08); }
  .fp-feed-msg.lesson .fp-feed-accent { background: #F59E0B; opacity: 0.8; }

  .fp-feed-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
  .fp-feed-body { flex: 1; min-width: 0; }
  .fp-feed-header { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
  .fp-feed-role { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }
  .fp-feed-ts { margin-left: auto; font-size: 9px; color: #3A3530; font-weight: 500; }
  .fp-feed-text { font-size: 12px; color: #C4A882; line-height: 1.5; margin: 0; word-break: break-word; }
  .fp-feed-msg.verdict_pass .fp-feed-text { color: #6EE7B7; }
  .fp-feed-msg.verdict_fail .fp-feed-text { color: #FCA5A5; }

  /* #2: PASS glow — the victory moment */
  .fp-feed-msg.verdict_pass {
    animation: fpFeedIn 0.3s ease both, fpPassGlow 2s ease 0.3s;
  }
  @keyframes fpPassGlow {
    0% { box-shadow: none; }
    30% { box-shadow: 0 0 24px rgba(52,211,153,0.2), inset 0 0 8px rgba(52,211,153,0.05); }
    100% { box-shadow: 0 0 8px rgba(52,211,153,0.06); }
  }

  /* #1: Iteration markers */
  .fp-feed-iter {
    display: flex; align-items: center; gap: 10px;
    padding: 4px 8px; animation: fpFeedIn 0.3s ease both;
  }
  .fp-feed-iter-line {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
  }
  .fp-feed-iter-label {
    font-size: 9px; font-weight: 800; color: #3A3530;
    text-transform: uppercase; letter-spacing: 1px;
    white-space: nowrap;
  }

  /* #3: Debate messages — indent + purple border */
  .fp-debate-indent {
    margin-left: 16px;
    border-left: 2px solid rgba(167,139,250,0.15);
    border-radius: 0 10px 10px 0;
  }
  .fp-debate-indent .fp-feed-accent { display: none; }
  .fp-feed-debate-tag {
    font-size: 7px; font-weight: 900; color: #A78BFA;
    background: rgba(167,139,250,0.08); padding: 1px 5px;
    border-radius: 3px; letter-spacing: 0.5px;
  }
  .fp-feed-msg.debate {
    background: rgba(167,139,250,0.02);
    border-color: rgba(167,139,250,0.06);
  }

  /* #4: Typing indicator */
  .fp-feed-typing {
    display: flex; gap: 8px; padding: 8px 10px;
    border-radius: 10px; position: relative;
    background: rgba(255,255,255,0.01);
    border: 1px solid rgba(255,255,255,0.02);
    animation: fpFeedIn 0.3s ease both;
  }
  .fp-feed-typing .fp-feed-body {
    display: flex; align-items: center; gap: 8px;
  }
  .fp-feed-typing-dots {
    display: flex; gap: 3px; align-items: center;
  }
  .fp-dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: #A78BFA; opacity: 0.4;
    animation: fpDotBounce 1.4s ease-in-out infinite;
  }
  .fp-dot:nth-child(2) { animation-delay: 0.2s; }
  .fp-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes fpDotBounce {
    0%, 80%, 100% { opacity: 0.3; transform: scale(1); }
    40% { opacity: 1; transform: scale(1.3); }
  }
  .fp-feed-typing-text {
    font-size: 11px; color: #4A3D30; font-style: italic;
  }

  /* #5: Feed wrapper + sticky intervene */
  .fp-feed-wrap {
    margin-top: 8px; border-radius: 12px;
    background: rgba(6,6,12,0.8); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.04);
    display: flex; flex-direction: column;
    overflow: hidden;
  }
  .fp-feed {
    margin-top: 0; border-radius: 0; background: none;
    backdrop-filter: none; border: none;
    padding: 8px; max-height: 460px; overflow-y: auto;
    display: flex; flex-direction: column; gap: 4px;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.06) transparent;
  }
  .fp-feed-intervene-sticky {
    padding: 8px 12px;
    border-top: 1px solid rgba(255,255,255,0.04);
    background: rgba(6,6,12,0.95);
    display: flex; justify-content: center;
  }
  .fp-feed-intervene-btn {
    padding: 8px 20px; border-radius: 10px;
    border: 1px solid rgba(245,158,11,0.12); background: rgba(245,158,11,0.04);
    color: #F59E0B; font-size: 11px; font-weight: 800;
    cursor: pointer; font-family: 'Outfit'; transition: all 0.2s;
  }
  .fp-feed-intervene-btn:hover { background: rgba(245,158,11,0.1); box-shadow: 0 0 16px rgba(245,158,11,0.08); }
  .fp-feed-intervene-input-wrap { display: flex; gap: 6px; width: 100%; }
  .fp-feed-intervene-input {
    flex: 1; padding: 8px 14px; border-radius: 10px;
    background: rgba(15,13,22,0.6); border: 1px solid rgba(245,158,11,0.15);
    color: #F0DCC8; font-size: 12px; font-family: 'Outfit'; outline: none; transition: all 0.2s;
  }
  .fp-feed-intervene-input:focus { border-color: rgba(245,158,11,0.3); box-shadow: 0 0 12px rgba(245,158,11,0.06); }
  .fp-feed-intervene-input::placeholder { color: rgba(240,220,200,0.2); }
  .fp-feed-send-btn {
    padding: 8px 16px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 11px; font-weight: 800;
    cursor: pointer; font-family: 'Outfit'; transition: all 0.2s;
  }
  .fp-feed-send-btn:hover { transform: translateY(-1px); }

  /* ═══ OUTPUT VIEWER ═══ */
  .fp-output-section {
    margin-top: 20px; padding: 16px; border-radius: 12px;
    background: rgba(245,158,11,0.03); border: 1px solid rgba(245,158,11,0.08);
  }
  .fp-output-title { font-size: 14px; font-weight: 800; color: #F59E0B; margin: 0 0 12px; }
  .fp-output-tokens { display: flex; gap: 12px; flex-wrap: wrap; }
  .fp-token-stat {
    flex: 1; min-width: 100px; padding: 10px 14px; border-radius: 10px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    display: flex; flex-direction: column; gap: 2px;
  }
  .fp-token-label { font-size: 9px; font-weight: 800; color: #6A5A4A; text-transform: uppercase; letter-spacing: 0.5px; }
  .fp-token-value { font-size: 16px; font-weight: 900; color: #F0DCC8; }
  .fp-output-files { margin-top: 12px; }
  .fp-output-files-title { font-size: 10px; font-weight: 800; color: #6A5A4A; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
  .fp-file-item {
    display: flex; align-items: center; gap: 8px; padding: 6px 10px;
    border-radius: 8px; background: rgba(167,139,250,0.04); border: 1px solid rgba(167,139,250,0.08);
    margin-bottom: 4px; font-size: 11px; color: #C4A882; cursor: pointer; transition: all 0.2s;
  }
  .fp-file-item:hover { background: rgba(167,139,250,0.08); color: #F0DCC8; }

  /* ═══ FILE TOAST ═══ */
  .fp-file-toast {
    position: fixed; bottom: 24px; right: 24px; z-index: 1000;
    padding: 12px 20px; border-radius: 12px;
    background: rgba(167,139,250,0.15); backdrop-filter: blur(16px);
    border: 1px solid rgba(167,139,250,0.25);
    color: #E0D4FF; font-size: 13px; font-weight: 700;
    box-shadow: 0 8px 32px rgba(167,139,250,0.15);
    animation: fpToastIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes fpToastIn { from { opacity: 0; transform: translateY(16px) scale(0.95); } to { opacity: 1; transform: translateY(0) scale(1); } }

  /* ═══ WEBSOCKET STATUS ═══ */
  .fp-ws-status {
    display: flex; align-items: center; gap: 6px;
    font-size: 9px; color: #3A3530; margin-top: 12px;
  }
  .fp-ws-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #4A3D30;
  }
  .fp-ws-dot.connected {
    background: #34D399;
    box-shadow: 0 0 6px rgba(52,211,153,0.4);
    animation: fpPulse 2s ease infinite;
  }

  /* ═══ APPROVAL GATE ═══ */
  .fp-gate-ui {
    margin-top: 12px; padding: 16px; border-radius: 14px;
    background: rgba(251,191,36,0.04); border: 1.5px solid rgba(251,191,36,0.15);
    animation: fsFadeUp 0.4s ease, fpGatePulse 3s ease infinite;
  }
  @keyframes fpGatePulse {
    0%,100% { border-color: rgba(251,191,36,0.15); box-shadow: 0 0 0 rgba(251,191,36,0); }
    50% { border-color: rgba(251,191,36,0.3); box-shadow: 0 0 20px rgba(251,191,36,0.06); }
  }
  .fp-gate-prompt { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
  .fp-gate-icon { font-size: 20px; }
  .fp-gate-text { font-size: 14px; font-weight: 700; color: #FBBF24; }
  .fp-gate-actions { display: flex; gap: 10px; }
  .fp-gate-approve {
    background: rgba(52,211,153,0.08) !important; border: 1px solid rgba(52,211,153,0.2) !important;
    color: #34D399 !important; font-weight: 800 !important; padding: 10px 24px !important;
  }
  .fp-gate-approve:hover { background: rgba(52,211,153,0.15) !important; box-shadow: 0 0 16px rgba(52,211,153,0.1); transform: translateY(-1px); }
  .fp-gate-reject {
    background: rgba(248,113,113,0.06) !important; border: 1px solid rgba(248,113,113,0.15) !important;
    color: #F87171 !important;
  }
  .fp-gate-reject:hover { background: rgba(248,113,113,0.12) !important; }
`;

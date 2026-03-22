"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import Link from "next/link";
import { API_BASE, getWebSocketUrl, intervenePipeline, approvePipeline, rejectPipeline } from "../../lib/api";
import { DiscoveryCard } from "@/components/GuidedTour";
import WorkflowBuilder from "@/components/WorkflowBuilder";

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   Pipeline â€” The Forge
   Companion-guided task orchestration.
   The mascot narrates, guides, and reacts.
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */

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
  planner: "ðŸ§ ",
  coder: "âš¡",
  backend: "âš¡",
  frontend: "ðŸŽ¨",
  tester: "ðŸ”",
  reviewer: "ðŸ‘¤",
  architect: "ðŸ›ï¸",
  devil_advocate: "ðŸ˜ˆ",
  end_user: "ðŸ‘¤",
  distiller: "ðŸ“œ",
  system: "âš™ï¸",
};

// â”€â”€ Stage emoji mapping â”€â”€
const STAGE_EMOJI: Record<string, string> = {
  Spec: "ðŸ“œ", Plan: "ðŸ“œ", Outline: "ðŸ“œ", Context: "ðŸ“œ", Gather: "ðŸ”Ž",
  Build: "ðŸ”¨", Content: "ðŸ”¨", Draft: "âœï¸", Design: "ðŸŽ¨",
  Test: "ðŸ”", Analyze: "ðŸ“Š", Insights: "ðŸ’¡",
  Review: "ðŸ‘¤", Write: "âœï¸", Report: "ðŸ“‹", Execute: "âš¡",
};

// Pipelines are loaded from the backend â€” start empty
const INITIAL_PIPELINES: Pipeline[] = [];


// â”€â”€ Template auto-detection â”€â”€
function detectTemplate(input: string): { name: string; icon: string; stages: string[] } {
  const lower = input.toLowerCase();
  if (["api", "backend", "frontend", "build", "code", "deploy", "app", "function"].some(k => lower.includes(k)))
    return { name: "Coding", icon: "âš¡", stages: ["ðŸ“œ Plan", "ðŸ”¨ Build", "ðŸ” Test", "ðŸ‘¤ Review"] };
  if (["research", "investigate", "find out", "look into", "compare"].some(k => lower.includes(k)))
    return { name: "Research", icon: "ðŸ”", stages: ["ðŸ”Ž Gather", "ðŸ“Š Analyze", "âœï¸ Write"] };
  if (["draft", "letter", "email", "write a"].some(k => lower.includes(k)))
    return { name: "Drafting", icon: "âœ‰ï¸", stages: ["ðŸ“œ Context", "âœï¸ Draft", "ðŸ‘¤ Review"] };
  if (["presentation", "slides", "deck"].some(k => lower.includes(k)))
    return { name: "Presentation", icon: "ðŸ“Š", stages: ["ðŸ“œ Outline", "ðŸ”¨ Content", "ðŸŽ¨ Design", "ðŸ‘¤ Review"] };
  if (["analyze", "data", "trends", "metrics", "numbers"].some(k => lower.includes(k)))
    return { name: "Analysis", icon: "ðŸ“ˆ", stages: ["ðŸ”Ž Gather", "ðŸ“Š Analyze", "ðŸ’¡ Insights", "ðŸ“‹ Report"] };
  return { name: "General", icon: "ðŸ“‹", stages: ["ðŸ“œ Plan", "âš¡ Execute", "ðŸ‘¤ Review"] };
}


// Agent feed starts empty â€” populated from WebSocket events
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

  // â”€â”€ WebSocket: live pipeline events â†’ agent feed â”€â”€
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
                setFileToast(`ðŸ“„ Created: ${fname}`);
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
        return { id, role: "system", icon: "â–¶", color: "#60A5FA", message: `Stage started: ${stage} (${payload.stage_index as number + 1}/${payload.total_stages})`, ts, type: "normal" };
      case "pipeline.stage_complete": {
        const verdict = payload.verdict as string;
        const duration = payload.duration_s as number;
        const eta = payload.eta_seconds as number;
        const type: AgentMessage["type"] = verdict === "pass" || verdict === "ship" ? "verdict_pass" : verdict === "fail" ? "verdict_fail" : "normal";
        return { id, role: stage || "system", icon: verdict === "pass" ? "âœ”" : verdict === "fail" ? "âœ•" : "â†’", color: verdict === "pass" ? "#34D399" : verdict === "fail" ? "#F87171" : "#F59E0B", message: `Stage ${stage}: ${verdict.toUpperCase()}${duration ? ` (${duration}s)` : ""}${eta ? ` Â· ETA ~${Math.round(eta / 60)}min` : ""}`, ts, type };
      }
      case "pipeline.file_created":
        return { id, role: "system", icon: "ðŸ“„", color: "#A78BFA", message: `File created: ${payload.path}`, ts, type: "normal" };
      case "pipeline.shipped": {
        const dur = payload.duration_s as number;
        const tokens = payload.tokens as { prompt?: number; completion?: number } | undefined;
        const totalTokens = tokens ? (tokens.prompt || 0) + (tokens.completion || 0) : 0;
        return { id, role: "system", icon: "ðŸš€", color: "#F59E0B", message: `Pipeline complete! ${dur ? `${Math.round(dur / 60)}min` : ""}${totalTokens ? ` Â· ${(totalTokens / 1000).toFixed(1)}K tokens` : ""}`, ts, type: "verdict_pass" };
      }
      case "pipeline.escalated":
        return { id, role: "system", icon: "ðŸ–", color: "#F87171", message: `Escalated: ${payload.reason || "Max iterations reached"}`, ts, type: "escalation" };
      case "pipeline.human_intervention":
        return { id, role: "you", icon: "ðŸ’¬", color: "#22D3EE", message: `Guidance: ${payload.guidance}`, ts, type: "normal" };
      case "pipeline.iteration":
        return { id, role: "system", icon: "ðŸ”„", color: "#4A3D30", message: `Iteration ${payload.iteration} â€” ${payload.stage} ${payload.verdict}`, ts, type: "iteration" };
      case "pipeline.gate_waiting":
        return { id, role: "system", icon: "â¸", color: "#FBBF24", message: `âœ‰ï¸ Approval required: ${payload.prompt || "Continue?"}`, ts, type: "normal" };
      case "pipeline.gate_approved":
        return { id, role: "you", icon: "âœ…", color: "#34D399", message: `Gate approved â€” pipeline continuing`, ts, type: "verdict_pass" };
      case "pipeline.gate_rejected":
        return { id, role: "you", icon: "âŒ", color: "#F87171", message: `Gate rejected â€” ${payload.stage || "stage"} declined`, ts, type: "verdict_fail" };
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
        icon: "ðŸ’¬",
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
      {/* CSS migrated to globals.css for Tauri CSP compatibility */}

      <DiscoveryCard pageKey="/pipeline" />

      <div className="fp-layout">
        {/* â”€â”€ Sidebar â”€â”€ */}
        <div className="fp-sidebar">
          <div className="fp-sidebar-header">
            <Link href="/" className="fp-back-hub">ðŸ”¥ Hub</Link>
            <h2 className="fp-sidebar-title">Tasks</h2>
          </div>

          <button
            className={`fp-pipeline-card new-task ${!activePipeline ? "active" : ""}`}
            onClick={() => { setActivePipeline(null); setShowDebate(false); }}
          >
            <span className="fp-pc-icon">âš¡</span>
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
                  {p.status === "complete" && <span className="fp-pc-done">âœ”</span>}
                </div>
                <div className="fp-pc-title">{p.title}</div>
                <div className="fp-pc-stages">
                  {p.stages.map((s, i) => (
                    <span key={i} className={`fp-pc-dot ${s.status}`} title={s.name} />
                  ))}
                </div>
                {p.status === "running" && (
                  <div className="fp-pc-meta">Iteration {p.iteration} Â· {p.eta || "..."}</div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* â”€â”€ Main Area â”€â”€ */}
        <div className="fp-main">

          {/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
              CREATION FLOW â€” text or visual
              â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
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
                >âœï¸ Text</button>
                <button
                  className="fp-mode-btn"
                  onClick={() => setCreationMode("visual")}
                >ðŸ”§ Visual Builder</button>
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
                        {i < detected.stages.length - 1 && <span className="fp-detected-arrow">â†’</span>}
                      </span>
                    ))}
                  </div>

                  <button className="fp-start-btn" onClick={submitTask} disabled={submitting}>
                    {submitting ? "â³ Starting..." : "âš¡ Start"}
                  </button>

                  <button className="fp-customize-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
                    {showAdvanced ? "Hide options â–¾" : "Want to customize? â–¸"}
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

          {/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
              PIPELINE DETAIL â€” running/complete view
              â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
          {current && (
            <div className="fp-detail">
              {/* Header */}
              <div className="fp-detail-header">
                <div>
                  <h1 className="fp-detail-title">{current.templateIcon} {current.title}</h1>
                  <div className="fp-detail-meta">
                    <span className={`fp-status-badge ${current.status}`}>
                      {current.status === "running" ? "ðŸ”„ Running" : current.status === "complete" ? "âœ… Complete" : current.status === "waiting_approval" ? "â¸ Approval Gate" : "âš ï¸ " + current.status}
                    </span>
                    <span>Iteration {current.iteration}/{current.maxIterations}</span>
                    <span>{current.mode === "mesh" ? "ðŸ”— Mesh" : "ðŸ–¥ï¸ Local"}</span>
                  </div>
                </div>
              </div>

              {/* â”€â”€ FORGE with mascot â”€â”€ */}
              <div className="fp-forge">
                <div className="fp-forge-glow" />

                {/* Stage timeline */}
                <div className="fp-stages">
                  {current.stages.map((stage, i) => (
                    <div key={i} className={`fp-stage ${stage.status}`} style={{ animationDelay: `${i * 0.12}s` }}>
                      <div className={`fp-ember-stone ${stage.status}`}>
                        {stage.status === "done" && <span className="fp-ember-check">âœ”</span>}
                        {stage.status === "active" && <div className="fp-ember-flames" />}
                        {stage.status === "failed" && <span className="fp-ember-x">âœ•</span>}
                      </div>
                      <div className="fp-stage-label">{stage.emoji || STAGE_EMOJI[stage.name] || "âš¡"} {stage.name}</div>
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
                <span className="fp-progress-text">{progress}% Â· {current.eta || "Complete"}</span>
              </div>

              {/* â•â•â• AGENT FEED â•â•â• */}
              {current.status === "running" && (
                <div className="fp-feed-section">
                  <button
                    className="fp-feed-toggle"
                    onClick={() => setShowFeed(!showFeed)}
                  >
                    <span className="fp-feed-toggle-dot" />
                    Agent Feed â€” {agentFeed.length} messages
                    <span className="fp-feed-toggle-arrow">{showFeed ? "â–¼" : "â–¶"}</span>
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

                          // Debate messages â€” grouped with indent
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

                      {/* Sticky intervene bar â€” always visible */}
                      <div className="fp-feed-intervene-sticky">
                        {!showIntervene ? (
                          <button
                            className="fp-feed-intervene-btn"
                            onClick={() => setShowIntervene(true)}
                          >
                            ðŸ–ï¸ Intervene â€” Jump In
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
                              Send âš¡
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
                    ðŸ—£ï¸ Socratic Review â€” the team is debating {showDebate ? "â–¼" : "â–¶"}
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
                      <button className="fp-intervene-btn">ðŸ–ï¸ Intervene â€” Add Your Take</button>
                    </div>
                  )}
                </div>
              )}

              {/* Lessons */}
              {current.lessons && current.lessons.length > 0 && (
                <div className="fp-lessons">
                  <h3 className="fp-lessons-title">ðŸ“œ Lessons Learned</h3>
                  {current.lessons.map((l, i) => <div key={i} className="fp-lesson-item">â€¢ {l}</div>)}
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
                    }}>Force Advance â–¶</button>
                  </>
                )}
                {current.status === "complete" && (
                  <button className="fp-action-btn new" onClick={() => setActivePipeline(null)}>âš¡ Start New Task</button>
                )}
                {current.status === "escalated" && (
                  <button className="fp-action-btn advance" onClick={() => setShowIntervene(true)}>ðŸ’¬ Give Guidance</button>
                )}
                {current.status === "waiting_approval" && (
                  <div className="fp-gate-ui">
                    <div className="fp-gate-prompt">
                      <span className="fp-gate-icon">â¸</span>
                      <span className="fp-gate-text">Approval required to continue</span>
                    </div>
                    <div className="fp-gate-actions">
                      <button className="fp-action-btn fp-gate-approve" onClick={async () => {
                        await approvePipeline(current.id);
                        setPipelines(prev => prev.map(p => p.id === current.id ? { ...p, status: "running" as const } : p));
                      }}>âœ… Approve</button>
                      <button className="fp-action-btn fp-gate-reject" onClick={async () => {
                        await rejectPipeline(current.id);
                        setPipelines(prev => prev.map(p => p.id === current.id ? { ...p, status: "escalated" as const } : p));
                      }}>âŒ Reject</button>
                    </div>
                  </div>
                )}
              </div>

              {/* â•â•â• OUTPUT VIEWER â€” files + tokens â•â•â• */}
              {current.status === "complete" && (
                <div className="fp-output-section">
                  <h3 className="fp-output-title">ðŸ“¦ Pipeline Output</h3>

                  {/* Token usage */}
                  <div className="fp-output-tokens">
                    <div className="fp-token-stat">
                      <span className="fp-token-label">â± Duration</span>
                      <span className="fp-token-value">{current.eta || "â€”"}</span>
                    </div>
                    <div className="fp-token-stat">
                      <span className="fp-token-label">ðŸ”„ Iterations</span>
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


// Pipeline CSS now lives in globals.css (migrated for Tauri CSP compat)


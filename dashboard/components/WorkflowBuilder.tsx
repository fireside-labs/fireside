"use client";

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { API_BASE } from "@/lib/api";

/* ═══════════════════════════════════════════════════════════════════
   WorkflowBuilder — Visual drag-and-drop pipeline creator
   No external dependencies — pure React + CSS + SVG connections
   ═══════════════════════════════════════════════════════════════════ */

// ── Types ──

interface WorkflowNode {
  id: string;
  type: "task" | "gate" | "review";
  name: string;
  role: string;
  prompt: string;
  x: number;
  y: number;
  onFail: "retry" | "escalate" | string; // string for "goto:nodeName"
}

interface Connection {
  from: string;
  to: string;
}

// ── Constants ──

const ROLES = [
  { value: "planner", label: "🧠 Planner", color: "#60A5FA" },
  { value: "writer", label: "✍️ Writer", color: "#A78BFA" },
  { value: "researcher", label: "🔍 Researcher", color: "#22D3EE" },
  { value: "analyst", label: "📊 Analyst", color: "#FBBF24" },
  { value: "executor", label: "⚡ Executor", color: "#34D399" },
  { value: "reviewer", label: "👤 Reviewer", color: "#F87171" },
  { value: "presenter", label: "📊 Presenter", color: "#F59E0B" },
  { value: "drafter", label: "✉️ Drafter", color: "#E879F9" },
];

const NODE_TYPES = [
  { type: "task" as const, icon: "⚡", label: "Task", desc: "AI executes a prompt", color: "#F59E0B" },
  { type: "gate" as const, icon: "⏸", label: "Approval Gate", desc: "Pauses for human OK", color: "#FBBF24" },
  { type: "review" as const, icon: "🗣️", label: "Review", desc: "Socratic debate review", color: "#A78BFA" },
];

const TEMPLATES = [
  {
    name: "📋 Report Pipeline",
    nodes: [
      { type: "task" as const, name: "Research", role: "researcher", prompt: "Research the topic thoroughly" },
      { type: "task" as const, name: "Analyze", role: "analyst", prompt: "Analyze findings and identify key insights" },
      { type: "gate" as const, name: "Approve", role: "reviewer", prompt: "Review analysis before writing" },
      { type: "task" as const, name: "Write", role: "writer", prompt: "Write a comprehensive report" },
    ],
  },
  {
    name: "⚡ Build & Ship",
    nodes: [
      { type: "task" as const, name: "Plan", role: "planner", prompt: "Create a detailed implementation plan" },
      { type: "task" as const, name: "Build", role: "executor", prompt: "Implement the plan" },
      { type: "task" as const, name: "Test", role: "reviewer", prompt: "Test thoroughly and report issues" },
      { type: "review" as const, name: "Review", role: "reviewer", prompt: "Socratic review of the implementation" },
    ],
  },
  {
    name: "📊 Data Analysis",
    nodes: [
      { type: "task" as const, name: "Gather", role: "researcher", prompt: "Gather all relevant data" },
      { type: "task" as const, name: "Clean", role: "analyst", prompt: "Clean and normalize the data" },
      { type: "task" as const, name: "Analyze", role: "analyst", prompt: "Run analysis and find patterns" },
      { type: "gate" as const, name: "Approve", role: "reviewer", prompt: "Approve findings before presentation" },
      { type: "task" as const, name: "Present", role: "presenter", prompt: "Create a presentation of findings" },
    ],
  },
  {
    name: "✉️ Draft & Review",
    nodes: [
      { type: "task" as const, name: "Context", role: "researcher", prompt: "Gather context and requirements" },
      { type: "task" as const, name: "Draft", role: "drafter", prompt: "Write the first draft" },
      { type: "review" as const, name: "Review", role: "reviewer", prompt: "Review for tone, accuracy, and completeness" },
      { type: "gate" as const, name: "Send", role: "reviewer", prompt: "Approve final version for sending" },
    ],
  },
];

function generateId() {
  return `n_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
}

function getRoleColor(role: string): string {
  return ROLES.find(r => r.value === role)?.color || "#F59E0B";
}

function getTypeVisual(type: string) {
  return NODE_TYPES.find(t => t.type === type) || NODE_TYPES[0];
}

// ── Component ──

interface Props {
  onRun: (stages: Record<string, unknown>[]) => void;
  onClose: () => void;
}

export default function WorkflowBuilder({ onRun, onClose }: Props) {
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [dragging, setDragging] = useState<{ nodeId: string; offsetX: number; offsetY: number } | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [workflowTitle, setWorkflowTitle] = useState("");
  const [validationMsg, setValidationMsg] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  // Undo stack: stores snapshots of {nodes, connections} before destructive actions
  const undoStack = useRef<{ nodes: WorkflowNode[]; connections: Connection[] }[]>([]);

  // ── Drag from toolbox to canvas ──
  const handleToolboxDrag = useCallback((type: "task" | "gate" | "review", e: React.DragEvent) => {
    e.dataTransfer.setData("nodeType", type);
  }, []);

  const handleCanvasDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const type = e.dataTransfer.getData("nodeType") as "task" | "gate" | "review";
    if (!type) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const visual = getTypeVisual(type);

    const newNode: WorkflowNode = {
      id: generateId(),
      type,
      name: visual.label,
      role: type === "gate" ? "reviewer" : type === "review" ? "reviewer" : "executor",
      prompt: "",
      x: Math.max(20, x - 75),
      y: Math.max(20, y - 30),
      onFail: "retry",
    };

    setNodes(prev => [...prev, newNode]);

    // Auto-connect to the last node
    if (nodes.length > 0) {
      const lastNode = nodes[nodes.length - 1];
      setConnections(prev => [...prev, { from: lastNode.id, to: newNode.id }]);
    }

    setSelectedNode(newNode.id);
  }, [nodes]);

  // ── Drag nodes on canvas ──
  const handleNodeMouseDown = useCallback((nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const rect = (e.target as HTMLElement).closest(".wb-node")?.getBoundingClientRect();
    if (!rect) return;
    setDragging({
      nodeId,
      offsetX: e.clientX - rect.left,
      offsetY: e.clientY - rect.top,
    });
    setSelectedNode(nodeId);
  }, []);

  const handleCanvasMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - dragging.offsetX;
    const y = e.clientY - rect.top - dragging.offsetY;
    setNodes(prev => prev.map(n =>
      n.id === dragging.nodeId ? { ...n, x: Math.max(0, x), y: Math.max(0, y) } : n
    ));
  }, [dragging]);

  const handleCanvasMouseUp = useCallback(() => {
    setDragging(null);
  }, []);

  // ── Connection drawing ──
  const startConnection = useCallback((nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConnecting(nodeId);
  }, []);

  const finishConnection = useCallback((nodeId: string) => {
    if (connecting && connecting !== nodeId) {
      // Don't add duplicate connections
      const exists = connections.some(c => c.from === connecting && c.to === nodeId);
      if (!exists) {
        setConnections(prev => [...prev, { from: connecting, to: nodeId }]);
      }
    }
    setConnecting(null);
  }, [connecting, connections]);

  // ── Delete node (with undo snapshot) ──
  const deleteNode = useCallback((nodeId: string) => {
    // Save undo snapshot
    undoStack.current.push({ nodes: [...nodes], connections: [...connections] });
    setNodes(prev => prev.filter(n => n.id !== nodeId));
    setConnections(prev => prev.filter(c => c.from !== nodeId && c.to !== nodeId));
    if (selectedNode === nodeId) setSelectedNode(null);
  }, [selectedNode, nodes, connections]);

  // ── Delete connection ──
  const deleteConnection = useCallback((index: number) => {
    undoStack.current.push({ nodes: [...nodes], connections: [...connections] });
    setConnections(prev => prev.filter((_, i) => i !== index));
  }, [nodes, connections]);

  // ── Undo (ctrl+Z) ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z") {
        e.preventDefault();
        const snapshot = undoStack.current.pop();
        if (snapshot) {
          setNodes(snapshot.nodes);
          setConnections(snapshot.connections);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // ── Update node ──
  const updateNode = useCallback((nodeId: string, updates: Partial<WorkflowNode>) => {
    setNodes(prev => prev.map(n => n.id === nodeId ? { ...n, ...updates } : n));
  }, []);

  // ── Load template ──
  const loadTemplate = useCallback((template: typeof TEMPLATES[0]) => {
    const spacing = 180;
    const startX = 60;
    const startY = 80;
    const newNodes: WorkflowNode[] = template.nodes.map((n, i) => ({
      id: generateId(),
      type: n.type,
      name: n.name,
      role: n.role,
      prompt: n.prompt,
      x: startX + i * spacing,
      y: startY + (i % 2 === 0 ? 0 : 40), // slight wave pattern
      onFail: "retry",
    }));
    const newConnections: Connection[] = newNodes.slice(0, -1).map((n, i) => ({
      from: n.id,
      to: newNodes[i + 1].id,
    }));
    setNodes(newNodes);
    setConnections(newConnections);
    setSelectedNode(newNodes[0]?.id || null);
    setWorkflowTitle(template.name.replace(/^.\s/, ""));
  }, []);

  // ── Export to pipeline stages JSON ──
  const exportStages = useCallback((): Record<string, unknown>[] => {
    // Follow connections to determine order
    const ordered: WorkflowNode[] = [];
    const visited = new Set<string>();
    
    // Find the root (node with no incoming connection)
    const hasIncoming = new Set(connections.map(c => c.to));
    let current = nodes.find(n => !hasIncoming.has(n.id));
    if (!current && nodes.length > 0) current = nodes[0]; // fallback

    while (current && !visited.has(current.id)) {
      visited.add(current.id);
      ordered.push(current);
      const next = connections.find(c => c.from === current!.id);
      if (next) current = nodes.find(n => n.id === next.to);
      else current = undefined;
    }

    // Add any unvisited nodes at the end
    nodes.forEach(n => { if (!visited.has(n.id)) ordered.push(n); });

    return ordered.map(n => ({
      name: n.name,
      type: n.type === "gate" ? "gate" : undefined,
      agent: "local",
      task_type: n.type === "review" ? "review" : "build",
      role: n.role,
      prompt: n.prompt || `Execute ${n.name} stage`,
      system_prompt: `You are a ${n.role} executing the '${n.name}' stage of a pipeline.`,
      on_fail: n.onFail,
    }));
  }, [nodes, connections]);

  // ── Run workflow (with validation) ──
  const handleRun = useCallback(async () => {
    if (nodes.length === 0) return;
    // Validate: check for empty prompts
    const emptyPrompts = nodes.filter(n => !n.prompt.trim() && n.type !== "gate");
    if (emptyPrompts.length > 0) {
      setValidationMsg(`⚠️ ${emptyPrompts.length} stage${emptyPrompts.length > 1 ? "s have" : " has"} empty prompts: ${emptyPrompts.map(n => n.name).join(", ")}`);
      // Auto-dismiss after 5s
      setTimeout(() => setValidationMsg(null), 5000);
      return;
    }
    setRunning(true);
    try {
      const stages = exportStages();
      const title = workflowTitle || `Workflow (${nodes.length} stages)`;
      
      const res = await fetch(`${API_BASE}/api/v1/pipeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description: `Visual workflow: ${nodes.map(n => n.name).join(" → ")}`,
          stages,
          max_iterations: 5,
        }),
      });
      const data = await res.json();
      onRun(stages);
    } catch (e) {
      console.error("Pipeline start failed:", e);
    } finally {
      setRunning(false);
    }
  }, [nodes, workflowTitle, exportStages, onRun]);

  // ── Back with confirmation ──
  const handleBack = useCallback(() => {
    if (nodes.length > 0) {
      if (!window.confirm(`You have ${nodes.length} unsaved stages. Discard and go back?`)) return;
    }
    onClose();
  }, [nodes, onClose]);

  // Selected node data
  const selected = useMemo(() => nodes.find(n => n.id === selectedNode), [nodes, selectedNode]);

  // ── Render ──
  return (
    <div className="wb-root">
      <style>{builderCSS}</style>

      {/* ── Header ── */}
      <div className="wb-header">
        <div className="wb-header-left">
          <button className="wb-back" onClick={handleBack}>← Back</button>
          <input
            className="wb-title-input"
            value={workflowTitle}
            onChange={e => setWorkflowTitle(e.target.value)}
            placeholder="Workflow name..."
          />
        </div>
        <div className="wb-header-right">
          <span className="wb-node-count">{nodes.length} stages</span>
          <button
            className="wb-run-btn"
            onClick={handleRun}
            disabled={nodes.length === 0 || running}
          >
            {running ? "⏳ Starting..." : "▶ Run Workflow"}
          </button>
        </div>
      </div>

      <div className="wb-layout">
        {/* ── Toolbox (Left sidebar) ── */}
        <div className="wb-toolbox">
          <div className="wb-toolbox-section">
            <h4 className="wb-toolbox-title">Drag to Canvas</h4>
            {NODE_TYPES.map(nt => (
              <div
                key={nt.type}
                className="wb-toolbox-item"
                draggable
                onDragStart={e => handleToolboxDrag(nt.type, e)}
                style={{ "--item-color": nt.color } as React.CSSProperties}
              >
                <span className="wb-toolbox-icon">{nt.icon}</span>
                <div>
                  <div className="wb-toolbox-label">{nt.label}</div>
                  <div className="wb-toolbox-desc">{nt.desc}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="wb-toolbox-section">
            <h4 className="wb-toolbox-title">Templates</h4>
            {TEMPLATES.map((t, i) => (
              <button
                key={i}
                className="wb-template-btn"
                onClick={() => loadTemplate(t)}
              >
                {t.name}
                <span className="wb-template-count">{t.nodes.length} stages</span>
              </button>
            ))}
          </div>
        </div>

        {/* ── Canvas ── */}
        <div
          ref={canvasRef}
          className="wb-canvas"
          onDragOver={e => e.preventDefault()}
          onDrop={handleCanvasDrop}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onClick={() => { setSelectedNode(null); setConnecting(null); }}
        >
          {/* SVG connections */}
          <svg className="wb-connections">
            {connections.map((conn, i) => {
              const fromNode = nodes.find(n => n.id === conn.from);
              const toNode = nodes.find(n => n.id === conn.to);
              if (!fromNode || !toNode) return null;
              const x1 = fromNode.x + 75;
              const y1 = fromNode.y + 30;
              const x2 = toNode.x + 75;
              const y2 = toNode.y + 30;
              const midX = (x1 + x2) / 2;
              return (
                <g key={i}>
                  {/* Invisible fat hit area for clicking */}
                  <path
                    d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                    className="wb-connection-hit"
                    onClick={(e) => { e.stopPropagation(); deleteConnection(i); }}
                    style={{ pointerEvents: "stroke" }}
                  />
                  <path
                    d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                    className="wb-connection-line"
                  />
                  <circle cx={x2 - 8} cy={y2} r="3" fill="#F59E0B" opacity="0.6" />
                </g>
              );
            })}
          </svg>

          {/* Nodes */}
          {nodes.map(node => {
            const visual = getTypeVisual(node.type);
            const roleColor = getRoleColor(node.role);
            const isSelected = selectedNode === node.id;
            return (
              <div
                key={node.id}
                className={`wb-node ${node.type} ${isSelected ? "selected" : ""} ${connecting ? "connectable" : ""}`}
                style={{
                  left: node.x,
                  top: node.y,
                  "--node-color": roleColor,
                  "--type-color": visual.color,
                } as React.CSSProperties}
                onMouseDown={e => handleNodeMouseDown(node.id, e)}
                onClick={e => { e.stopPropagation(); setSelectedNode(node.id); if (connecting) finishConnection(node.id); }}
              >
                <div className="wb-node-header">
                  <span className="wb-node-type-icon">{visual.icon}</span>
                  <span className="wb-node-name">{node.name}</span>
                </div>
                <div className="wb-node-role" style={{ color: roleColor }}>{node.role}</div>

                {/* Connection handle (right side) */}
                <div
                  className="wb-node-handle out"
                  onMouseDown={e => { e.stopPropagation(); startConnection(node.id, e); }}
                  title="Drag to connect"
                />
                {/* Connection target (left side) */}
                <div
                  className="wb-node-handle in"
                  onClick={e => { e.stopPropagation(); if (connecting) finishConnection(node.id); }}
                />
              </div>
            );
          })}

          {/* Empty state */}
          {nodes.length === 0 && (
            <div className="wb-empty">
              <div className="wb-empty-icon">⚡</div>
              <p>Drag stages from the toolbox</p>
              <p className="wb-empty-sub">or pick a template to start</p>
            </div>
          )}

          {/* Validation message */}
          {validationMsg && (
            <div className="wb-validation-msg">
              {validationMsg}
            </div>
          )}
        </div>

        {/* ── Settings Panel (Right) ── */}
        {selected && (
          <div className="wb-settings">
            <h4 className="wb-settings-title">Stage Settings</h4>

            <label className="wb-field-label">Name</label>
            <input
              className="wb-field-input"
              value={selected.name}
              onChange={e => updateNode(selected.id, { name: e.target.value })}
            />

            <label className="wb-field-label">Type</label>
            <div className="wb-type-group">
              {NODE_TYPES.map(nt => (
                <button
                  key={nt.type}
                  className={`wb-type-btn ${selected.type === nt.type ? "active" : ""}`}
                  onClick={() => updateNode(selected.id, { type: nt.type })}
                >
                  {nt.icon} {nt.label}
                </button>
              ))}
            </div>

            <label className="wb-field-label">Role</label>
            <select
              className="wb-field-select"
              value={selected.role}
              onChange={e => updateNode(selected.id, { role: e.target.value })}
            >
              {ROLES.map(r => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>

            <label className="wb-field-label">Prompt</label>
            <textarea
              className="wb-field-textarea"
              value={selected.prompt}
              onChange={e => updateNode(selected.id, { prompt: e.target.value })}
              placeholder="Describe what this stage should do..."
              rows={4}
            />

            <label className="wb-field-label">On Failure</label>
            <select
              className="wb-field-select"
              value={selected.onFail}
              onChange={e => updateNode(selected.id, { onFail: e.target.value })}
            >
              <option value="retry">🔄 Retry</option>
              <option value="escalate">🖐 Escalate to human</option>
              {nodes.filter(n => n.id !== selected.id).map(n => (
                <option key={n.id} value={`goto:${n.name}`}>↩ Go to: {n.name}</option>
              ))}
            </select>

            <button
              className="wb-delete-btn"
              onClick={() => deleteNode(selected.id)}
            >
              🗑️ Delete Stage
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
const builderCSS = `
  .wb-root {
    display: flex; flex-direction: column; height: 100%;
    background: #060609; font-family: 'Outfit', 'Inter', system-ui, sans-serif; color: #F0DCC8;
  }

  /* ── Header ── */
  .wb-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 20px; border-bottom: 1px solid rgba(255,255,255,0.04);
    background: rgba(8,8,14,0.95); backdrop-filter: blur(12px);
  }
  .wb-header-left { display: flex; align-items: center; gap: 16px; }
  .wb-header-right { display: flex; align-items: center; gap: 12px; }
  .wb-back {
    padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.02); color: #C4A882; font-size: 12px; font-weight: 700;
    cursor: pointer; font-family: 'Outfit'; transition: all 0.2s;
  }
  .wb-back:hover { background: rgba(255,255,255,0.04); color: #F0DCC8; }
  .wb-title-input {
    padding: 6px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.02); color: #F0DCC8; font-size: 16px; font-weight: 800;
    font-family: 'Outfit'; outline: none; width: 280px; transition: all 0.2s;
  }
  .wb-title-input:focus { border-color: rgba(245,158,11,0.2); }
  .wb-title-input::placeholder { color: rgba(240,220,200,0.2); }
  .wb-node-count { font-size: 11px; color: #4A3D30; font-weight: 700; }
  .wb-run-btn {
    padding: 8px 20px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #D97706, #F59E0B); color: #0A0A0A;
    font-size: 13px; font-weight: 900; cursor: pointer; font-family: 'Outfit';
    transition: all 0.2s; box-shadow: 0 4px 16px rgba(245,158,11,0.2);
  }
  .wb-run-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 24px rgba(245,158,11,0.3); }
  .wb-run-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  /* ── Layout ── */
  .wb-layout { display: flex; flex: 1; overflow: hidden; }

  /* ── Toolbox ── */
  .wb-toolbox {
    width: 220px; flex-shrink: 0; padding: 16px;
    background: rgba(8,8,14,0.95); border-right: 1px solid rgba(255,255,255,0.04);
    overflow-y: auto; display: flex; flex-direction: column; gap: 20px;
  }
  .wb-toolbox-section { display: flex; flex-direction: column; gap: 6px; }
  .wb-toolbox-title {
    font-size: 9px; font-weight: 800; color: #6A5A4A; text-transform: uppercase;
    letter-spacing: 1px; margin: 0 0 4px;
  }
  .wb-toolbox-item {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px;
    border-radius: 10px; cursor: grab; transition: all 0.2s;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
  }
  .wb-toolbox-item:hover { background: color-mix(in srgb, var(--item-color) 6%, transparent); border-color: color-mix(in srgb, var(--item-color) 15%, transparent); }
  .wb-toolbox-item:active { cursor: grabbing; }
  .wb-toolbox-icon { font-size: 18px; }
  .wb-toolbox-label { font-size: 12px; font-weight: 700; color: #C4A882; }
  .wb-toolbox-desc { font-size: 9px; color: #4A3D30; }

  .wb-template-btn {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; border-radius: 10px; cursor: pointer; transition: all 0.2s;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    color: #C4A882; font-size: 11px; font-weight: 700; font-family: 'Outfit';
  }
  .wb-template-btn:hover { background: rgba(245,158,11,0.04); border-color: rgba(245,158,11,0.1); }
  .wb-template-count { font-size: 9px; color: #4A3D30; font-weight: 600; }

  /* ── Canvas ── */
  .wb-canvas {
    flex: 1; position: relative; overflow: auto;
    background:
      radial-gradient(circle at 50% 50%, rgba(245,158,11,0.015) 0%, transparent 70%),
      repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(255,255,255,0.015) 39px, rgba(255,255,255,0.015) 40px),
      repeating-linear-gradient(90deg, transparent, transparent 39px, rgba(255,255,255,0.015) 39px, rgba(255,255,255,0.015) 40px);
    min-height: 500px;
  }

  .wb-connections {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none; z-index: 1;
  }
  .wb-connection-hit {
    fill: none; stroke: transparent; stroke-width: 12; cursor: pointer;
    pointer-events: stroke;
  }
  .wb-connection-hit:hover + .wb-connection-line { stroke: #F87171; opacity: 0.6; }
  .wb-connection-line {
    fill: none; stroke: #F59E0B; stroke-width: 2; opacity: 0.35;
    stroke-dasharray: 6 4; pointer-events: none;
  }

  /* ── Nodes ── */
  .wb-node {
    position: absolute; z-index: 2; width: 150px;
    padding: 10px 14px; border-radius: 12px; cursor: move;
    background: rgba(15,13,22,0.85); backdrop-filter: blur(8px);
    border: 1.5px solid color-mix(in srgb, var(--node-color) 20%, transparent);
    transition: box-shadow 0.2s, border-color 0.2s;
    user-select: none;
  }
  .wb-node:hover { border-color: color-mix(in srgb, var(--node-color) 40%, transparent); }
  .wb-node.selected {
    border-color: var(--node-color);
    box-shadow: 0 0 20px color-mix(in srgb, var(--node-color) 15%, transparent);
  }
  .wb-node.gate { border-style: dashed; }
  .wb-node.connectable { cursor: crosshair; }
  .wb-node-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
  .wb-node-type-icon { font-size: 14px; }
  .wb-node-name { font-size: 12px; font-weight: 800; color: #F0DCC8; }
  .wb-node-role { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }

  /* Connection handles — 16px targets */
  .wb-node-handle {
    position: absolute; width: 16px; height: 16px; border-radius: 50%;
    background: rgba(245,158,11,0.3); border: 1.5px solid #F59E0B;
    cursor: crosshair; transition: all 0.2s; z-index: 5;
  }
  .wb-node-handle:hover { transform: scale(1.3); background: rgba(245,158,11,0.6); }
  .wb-node-handle.out { right: -8px; top: 50%; transform: translateY(-50%); }
  .wb-node-handle.out:hover { transform: translateY(-50%) scale(1.3); }
  .wb-node-handle.in { left: -8px; top: 50%; transform: translateY(-50%); }
  .wb-node-handle.in:hover { transform: translateY(-50%) scale(1.3); }

  /* ── Empty state ── */
  .wb-empty {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    text-align: center; color: #3A3530;
  }
  .wb-empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.3; }
  .wb-empty p { margin: 0; font-size: 14px; font-weight: 700; }
  .wb-empty-sub { font-size: 11px; color: #2A2520; margin-top: 4px !important; }

  /* ── Settings Panel ── */
  .wb-settings {
    width: 260px; flex-shrink: 0; padding: 16px;
    background: rgba(8,8,14,0.95); border-left: 1px solid rgba(255,255,255,0.04);
    overflow-y: auto; display: flex; flex-direction: column; gap: 10px;
    animation: wbSlideIn 0.25s ease;
  }
  @keyframes wbSlideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
  .wb-settings-title { font-size: 13px; font-weight: 800; color: #F59E0B; margin: 0 0 4px; }

  .wb-field-label { font-size: 9px; font-weight: 800; color: #6A5A4A; text-transform: uppercase; letter-spacing: 0.5px; }
  .wb-field-input, .wb-field-select, .wb-field-textarea {
    width: 100%; padding: 8px 10px; border-radius: 8px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    color: #F0DCC8; font-size: 12px; font-family: 'Outfit'; outline: none;
    transition: border-color 0.2s;
  }
  .wb-field-input:focus, .wb-field-select:focus, .wb-field-textarea:focus {
    border-color: rgba(245,158,11,0.2);
  }
  .wb-field-select { cursor: pointer; }
  .wb-field-textarea { resize: vertical; min-height: 60px; }

  .wb-type-group { display: flex; gap: 4px; flex-wrap: wrap; }
  .wb-type-btn {
    padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 700;
    cursor: pointer; font-family: 'Outfit'; transition: all 0.2s;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); color: #6A5A4A;
  }
  .wb-type-btn.active { background: rgba(245,158,11,0.08); border-color: rgba(245,158,11,0.2); color: #F59E0B; }
  .wb-type-btn:hover { background: rgba(245,158,11,0.04); color: #C4A882; }

  .wb-delete-btn {
    margin-top: 8px; padding: 8px 12px; border-radius: 8px;
    background: rgba(239,68,68,0.04); border: 1px solid rgba(239,68,68,0.1);
    color: #F87171; font-size: 11px; font-weight: 700; cursor: pointer;
    font-family: 'Outfit'; transition: all 0.2s;
  }
  .wb-delete-btn:hover { background: rgba(239,68,68,0.1); }

  /* ── Validation ── */
  .wb-validation-msg {
    position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
    padding: 10px 20px; border-radius: 10px; z-index: 10;
    background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.25);
    color: #F87171; font-size: 12px; font-weight: 700;
    animation: wbSlideIn 0.3s ease;
    backdrop-filter: blur(8px);
  }
`;

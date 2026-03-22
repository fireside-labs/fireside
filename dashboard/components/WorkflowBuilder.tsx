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
  const [showConfirmBack, setShowConfirmBack] = useState(false);
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
      setShowConfirmBack(true);
      return;
    }
    onClose();
  }, [nodes, onClose]);

  // Selected node data
  const selected = useMemo(() => nodes.find(n => n.id === selectedNode), [nodes, selectedNode]);

  // ── Render ──
  return (
    <div className="wb-root">
      {/* CSS in globals.css */}

      {/* ── Confirm discard modal ── */}
      {showConfirmBack && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
        }}>
          <div style={{
            background: '#141418', borderRadius: 16,
            border: '1px solid rgba(245,158,11,0.15)',
            padding: '28px 32px', maxWidth: 380, width: '90%',
            boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
            fontFamily: "'Outfit', system-ui",
          }}>
            <p style={{ color: '#F0DCC8', fontSize: 15, fontWeight: 700, marginBottom: 8 }}>
              Discard workflow?
            </p>
            <p style={{ color: '#5A4D40', fontSize: 13, marginBottom: 20, lineHeight: 1.5 }}>
              You have {nodes.length} unsaved stage{nodes.length !== 1 ? 's' : ''}. This can't be undone.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowConfirmBack(false)}
                style={{
                  padding: '8px 20px', borderRadius: 10, fontSize: 13, fontWeight: 700,
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
                  color: '#C4A882', cursor: 'pointer', fontFamily: "'Outfit', system-ui",
                }}
              >Keep editing</button>
              <button
                onClick={() => { setShowConfirmBack(false); onClose(); }}
                style={{
                  padding: '8px 20px', borderRadius: 10, fontSize: 13, fontWeight: 700,
                  background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.2)',
                  color: '#F87171', cursor: 'pointer', fontFamily: "'Outfit', system-ui",
                }}
              >Discard</button>
            </div>
          </div>
        </div>
      )}

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
// CSS migrated to globals.css
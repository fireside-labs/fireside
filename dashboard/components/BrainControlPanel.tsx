"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { API_BASE } from "@/lib/api";

/* ═══════════════════════════════════════════════════════════════════
   Brain Control Panel — RPG Equipment HUD
   Shows active brain status, VRAM usage, and Stop/Restart controls.
   Styled like an RPG character equipment panel with glow effects.
   ═══════════════════════════════════════════════════════════════════ */

interface BrainStatus {
  running: boolean;
  model: string | null;
  model_path: string | null;
  pid: number | null;
  port: number;
  started_at: string | null;
  error: string | null;
  gpu_layers: number;
}

interface GpuInfo {
  name: string;
  vram_total_gb: number;
  vram_used_gb: number;
}

export default function BrainControlPanel() {
  const [status, setStatus] = useState<BrainStatus | null>(null);
  const [gpu, setGpu] = useState<GpuInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionPending, setActionPending] = useState<string | null>(null);
  const [showStats, setShowStats] = useState(false);

  // Brain config (user-friendly)
  const [memorySize, setMemorySize] = useState("normal"); // short|normal|deep|max
  const [thinkingEnabled, setThinkingEnabled] = useState(true);
  const [responseLength, setResponseLength] = useState("normal"); // short|normal|long|unlimited

  const pollDelay = useRef(4000);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const [brainRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/brains/status`),
        fetch(`${API_BASE}/api/v1/status`),
      ]);
      const brain = await brainRes.json();
      const sys = await statusRes.json();
      setStatus(brain);
      setGpu(sys.gpu || null);
      // Reset to fast polling when brain is reachable
      pollDelay.current = 4000;
    } catch (e) {
      console.warn("[BrainControlPanel] fetch failed:", e);
      // Exponential backoff: 4s → 8s → 16s → 30s max
      pollDelay.current = Math.min(pollDelay.current * 2, 30000);
    } finally {
      setLoading(false);
    }
  }, []);

  // Adaptive polling with exponential backoff
  useEffect(() => {
    let cancelled = false;
    const schedule = async () => {
      await fetchStatus();
      if (!cancelled) {
        pollTimer.current = setTimeout(schedule, pollDelay.current);
      }
    };
    schedule();
    return () => {
      cancelled = true;
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, [fetchStatus]);

  // Load saved brain config from localStorage
  useEffect(() => {
    const mem = localStorage.getItem("fireside_memory_size");
    if (mem) setMemorySize(mem);
    const think = localStorage.getItem("fireside_thinking_enabled");
    if (think !== null) setThinkingEnabled(think === "true");
    const resp = localStorage.getItem("fireside_response_length");
    if (resp) setResponseLength(resp);
  }, []);

  // Memory presets → actual context sizes
  const memoryPresets: Record<string, { tokens: number; label: string; desc: string }> = {
    short:  { tokens: 4096,  label: "Short",  desc: "Quick chats, saves resources" },
    normal: { tokens: 8192,  label: "Normal", desc: "Good for most conversations" },
    deep:   { tokens: 16384, label: "Deep",   desc: "Long discussions, more memory" },
    max:    { tokens: 32768, label: "Max",    desc: "Full memory, uses more VRAM" },
  };

  const responseLengthPresets: Record<string, { label: string; desc: string }> = {
    short:     { label: "Short",     desc: "Brief answers" },
    normal:    { label: "Normal",    desc: "Balanced responses" },
    long:      { label: "Long",      desc: "Detailed explanations" },
    unlimited: { label: "Unlimited", desc: "No limit (model decides)" },
  };

  const handleStop = async () => {
    setActionPending("stop");
    try {
      // Actually stop the brain, not restart it
      await fetch(`${API_BASE}/api/v1/brains/stop`, { method: "POST" });
      await fetchStatus();
    } finally {
      setActionPending(null);
    }
  };

  const handleRestart = async () => {
    setActionPending("restart");
    try {
      await fetch(`${API_BASE}/api/v1/brains/restart`, { method: "POST" });
      setTimeout(fetchStatus, 2000);
    } finally {
      setActionPending(null);
    }
  };

  const saveStat = (key: string, value: string) => {
    localStorage.setItem(key, value);
  };

  if (loading) {
    return (
      <div style={styles.root}>
        <div style={styles.loadingPulse}>
          <span style={styles.loadingDot}>◆</span>
          <span style={styles.loadingText}>Scanning brain...</span>
        </div>
      </div>
    );
  }

  const isOnline = status?.running;
  const modelName = status?.model || "No Brain Equipped";
  const vramUsed = gpu?.vram_used_gb || 0;
  const vramTotal = gpu?.vram_total_gb || 0;
  const vramPct = vramTotal > 0 ? Math.round((vramUsed / vramTotal) * 100) : 0;
  const gpuName = gpu?.name || "Unknown GPU";

  return (
    <div style={styles.root}>
      {/* CSS in globals.css */}

      {/* ─── Status Header ─── */}
      <div className="bcp-header">
        <div className="bcp-status-group">
          {/* Pulsing status dot */}
          <div className={`bcp-dot ${isOnline ? "bcp-dot-online" : "bcp-dot-offline"}`} />

          {/* Model name — CLICK TO OPEN STATS */}
          <div className="bcp-model-info" onClick={() => setShowStats(v => !v)} style={{ cursor: "pointer" }}>
            <div className="bcp-label">ACTIVE BRAIN <span style={{ opacity: 0.4, fontSize: 8 }}>{showStats ? "▼" : "▶"} STATS</span></div>
            <div className={`bcp-model-name ${isOnline ? "bcp-name-glow" : ""}`}>
              {isOnline ? `⚡ ${modelName}` : `☠ ${modelName}`}
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div className="bcp-stats">
          {isOnline && status?.pid && (
            <div className="bcp-stat">
              <span className="bcp-stat-label">PID</span>
              <span className="bcp-stat-value">{status.pid}</span>
            </div>
          )}
          {isOnline && (
            <div className="bcp-stat">
              <span className="bcp-stat-label">PORT</span>
              <span className="bcp-stat-value">{status?.port || 8080}</span>
            </div>
          )}
          {status?.gpu_layers && (
            <div className="bcp-stat">
              <span className="bcp-stat-label">GPU</span>
              <span className="bcp-stat-value">{status.gpu_layers} layers</span>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="bcp-actions">
          {isOnline ? (
            <>
              <button
                className="bcp-btn bcp-btn-stop"
                onClick={handleStop}
                disabled={actionPending !== null}
                title="Stop Brain"
              >
                {actionPending === "stop" ? "⏳" : "■"} STOP
              </button>
              <button
                className="bcp-btn bcp-btn-restart"
                onClick={handleRestart}
                disabled={actionPending !== null}
                title="Restart Brain"
              >
                {actionPending === "restart" ? "⏳" : "↻"} RESTART
              </button>
            </>
          ) : (
            <button
              className="bcp-btn bcp-btn-start"
              onClick={async () => {
                setActionPending("start");
                try {
                  await fetch(`${API_BASE}/api/v1/brains/restart`, { method: "POST" });
                  setTimeout(fetchStatus, 2000);
                } finally { setActionPending(null); }
              }}
              disabled={actionPending !== null}
              title="Start Brain"
            >
              {actionPending === "start" ? "⏳" : "▶"} START
            </button>
          )}
        </div>
      </div>

      {/* ─── VRAM Bar ─── */}
      {vramTotal > 0 && (
        <div className="bcp-vram">
          <div className="bcp-vram-header">
            <span className="bcp-vram-label">🖥 {gpuName}</span>
            <span className="bcp-vram-usage">
              {vramUsed.toFixed(1)} / {vramTotal.toFixed(1)} GB
            </span>
          </div>
          <div className="bcp-vram-bar">
            <div
              className={`bcp-vram-fill ${vramPct > 85 ? "bcp-vram-danger" : vramPct > 60 ? "bcp-vram-warn" : ""}`}
              style={{ width: `${vramPct}%` }}
            />
          </div>
        </div>
      )}

      {/* ─── Error display ─── */}
      {status?.error && !isOnline && (
        <div className="bcp-error">
          <span>⚠</span> {status.error}
        </div>
      )}

      {/* ─── JRPG STAT SHEET ─── */}
      {showStats && (
        <div className="bcp-stats-sheet">
          <div className="bcp-sheet-title">⚔ BRAIN CONFIGURATION</div>

          {/* Memory (Context Window) */}
          <div className="bcp-stat-row">
            <div className="bcp-stat-header">
              <span className="bcp-stat-name">📜 Memory</span>
              <span className="bcp-stat-val">{memoryPresets[memorySize]?.label}</span>
            </div>
            <div className="bcp-stat-desc">{memoryPresets[memorySize]?.desc}</div>
            <div className="bcp-preset-row">
              {Object.entries(memoryPresets).map(([key, preset]) => (
                <button key={key}
                  className={`bcp-preset-btn ${memorySize === key ? "bcp-preset-active" : ""}`}
                  onClick={() => {
                    setMemorySize(key);
                    saveStat("fireside_memory_size", key);
                    saveStat("fireside_ctx_size", String(preset.tokens));
                  }}
                >{preset.label}</button>
              ))}
            </div>
          </div>

          {/* Response Length */}
          <div className="bcp-stat-row">
            <div className="bcp-stat-header">
              <span className="bcp-stat-name">💬 Max Response</span>
              <span className="bcp-stat-val">{responseLengthPresets[responseLength]?.label}</span>
            </div>
            <div className="bcp-stat-desc">{responseLengthPresets[responseLength]?.desc}</div>
            <div className="bcp-preset-row">
              {Object.entries(responseLengthPresets).map(([key, preset]) => (
                <button key={key}
                  className={`bcp-preset-btn ${responseLength === key ? "bcp-preset-active" : ""}`}
                  onClick={() => { setResponseLength(key); saveStat("fireside_response_length", key); }}
                >{preset.label}</button>
              ))}
            </div>
          </div>

          {/* Thinking Mode Toggle */}
          <div className="bcp-stat-row bcp-toggle-row">
            <div>
              <span className="bcp-stat-name">🧠 Thinking Mode</span>
              <div className="bcp-stat-desc" style={{ marginTop: 2 }}>
                {thinkingEnabled ? "AI reasons step-by-step before answering" : "Direct answers, faster responses"}
              </div>
            </div>
            <button
              className={`bcp-toggle ${thinkingEnabled ? "bcp-toggle-on" : ""}`}
              onClick={() => { const next = !thinkingEnabled; setThinkingEnabled(next); saveStat("fireside_thinking_enabled", String(next)); }}
            >
              {thinkingEnabled ? "ON" : "OFF"}
            </button>
          </div>

          <div className="bcp-sheet-hint">
            ⚠ Memory changes take effect after restart
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// Styles
// ═══════════════════════════════════════════════════════════════════

const styles: Record<string, React.CSSProperties> = {
  root: {
    padding: "0 24px",
    marginBottom: 0,
  },
  loadingPulse: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "16px 0",
  },
  loadingDot: {
    color: "#F59E0B",
    fontSize: 14,
    animation: "bcpPulse 1.5s ease-in-out infinite",
  },
  loadingText: {
    color: "#4A3D30",
    fontSize: 12,
    fontWeight: 600,
    letterSpacing: 1,
    textTransform: "uppercase" as const,
  },
};

// CSS migrated to globals.css
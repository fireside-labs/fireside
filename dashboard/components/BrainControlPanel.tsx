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
      <style>{panelCSS}</style>

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

const panelCSS = `
  @keyframes bcpPulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }
  @keyframes bcpDotPulse {
    0%, 100% { box-shadow: 0 0 4px currentColor; }
    50% { box-shadow: 0 0 12px currentColor, 0 0 24px currentColor; }
  }
  @keyframes bcpGlow {
    0%, 100% { text-shadow: 0 0 8px rgba(245,158,11,0.3); }
    50% { text-shadow: 0 0 16px rgba(245,158,11,0.6), 0 0 32px rgba(245,158,11,0.2); }
  }
  @keyframes bcpBarShine {
    0% { left: -100%; }
    50%, 100% { left: 200%; }
  }

  .bcp-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 20px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(245,158,11,0.04), rgba(139,92,246,0.02));
    border: 1.5px solid rgba(245,158,11,0.12);
    backdrop-filter: blur(10px);
    margin-bottom: 8px;
  }

  .bcp-status-group {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  .bcp-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .bcp-dot-online {
    background: #10B981;
    color: #10B981;
    animation: bcpDotPulse 2s ease-in-out infinite;
  }
  .bcp-dot-offline {
    background: #EF4444;
    color: #EF4444;
    animation: bcpDotPulse 3s ease-in-out infinite;
  }

  .bcp-model-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .bcp-label {
    font-size: 9px;
    font-weight: 800;
    color: #4A3D30;
    letter-spacing: 2px;
    text-transform: uppercase;
  }
  .bcp-model-name {
    font-size: 16px;
    font-weight: 800;
    color: #F0DCC8;
    white-space: nowrap;
  }
  .bcp-name-glow {
    animation: bcpGlow 3s ease-in-out infinite;
  }

  .bcp-stats {
    display: flex;
    gap: 16px;
    margin-left: auto;
    margin-right: 8px;
  }
  .bcp-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  .bcp-stat-label {
    font-size: 8px;
    font-weight: 700;
    color: #3A3530;
    letter-spacing: 1px;
  }
  .bcp-stat-value {
    font-size: 12px;
    font-weight: 700;
    color: #6A5A4A;
    font-variant-numeric: tabular-nums;
  }

  .bcp-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }
  .bcp-btn {
    padding: 8px 14px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 800;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.3s;
    border: 1.5px solid;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .bcp-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .bcp-btn-stop {
    background: rgba(239,68,68,0.08);
    border-color: rgba(239,68,68,0.25);
    color: #EF4444;
  }
  .bcp-btn-stop:hover:not(:disabled) {
    background: rgba(239,68,68,0.15);
    border-color: rgba(239,68,68,0.5);
    box-shadow: 0 0 16px rgba(239,68,68,0.15);
  }
  .bcp-btn-restart {
    background: rgba(59,130,246,0.08);
    border-color: rgba(59,130,246,0.25);
    color: #3B82F6;
  }
  .bcp-btn-restart:hover:not(:disabled) {
    background: rgba(59,130,246,0.15);
    border-color: rgba(59,130,246,0.5);
    box-shadow: 0 0 16px rgba(59,130,246,0.15);
  }
  .bcp-btn-start {
    background: rgba(16,185,129,0.08);
    border-color: rgba(16,185,129,0.25);
    color: #10B981;
  }
  .bcp-btn-start:hover:not(:disabled) {
    background: rgba(16,185,129,0.15);
    border-color: rgba(16,185,129,0.5);
    box-shadow: 0 0 16px rgba(16,185,129,0.15);
  }

  /* ─── VRAM Bar ─── */
  .bcp-vram {
    padding: 10px 20px 14px;
    border-radius: 0 0 16px 16px;
    background: rgba(255,255,255,0.015);
    border: 1px solid rgba(255,255,255,0.04);
    border-top: none;
    margin-top: -8px;
  }
  .bcp-vram-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .bcp-vram-label {
    font-size: 10px;
    font-weight: 700;
    color: #4A3D30;
    letter-spacing: 0.5px;
  }
  .bcp-vram-usage {
    font-size: 11px;
    font-weight: 700;
    color: #6A5A4A;
    font-variant-numeric: tabular-nums;
  }
  .bcp-vram-bar {
    height: 8px;
    border-radius: 4px;
    background: rgba(255,255,255,0.04);
    overflow: hidden;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.4);
  }
  .bcp-vram-fill {
    height: 100%;
    border-radius: 4px;
    background: linear-gradient(90deg, #047857, #10B981, #34D399);
    box-shadow: 0 0 8px rgba(16,185,129,0.3);
    transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
  }
  .bcp-vram-fill::after {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    animation: bcpBarShine 3s ease-in-out infinite;
  }
  .bcp-vram-warn {
    background: linear-gradient(90deg, #D97706, #F59E0B, #FBBF24) !important;
    box-shadow: 0 0 8px rgba(245,158,11,0.3) !important;
  }
  .bcp-vram-danger {
    background: linear-gradient(90deg, #DC2626, #EF4444, #F87171) !important;
    box-shadow: 0 0 8px rgba(239,68,68,0.3) !important;
  }

  /* ─── Error ─── */
  .bcp-error {
    margin-top: 8px;
    padding: 10px 16px;
    border-radius: 10px;
    background: rgba(239,68,68,0.06);
    border: 1px solid rgba(239,68,68,0.15);
    font-size: 12px;
    color: #EF4444;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* ─── Responsive ─── */
  @media (max-width: 700px) {
    .bcp-header {
      flex-wrap: wrap;
      gap: 12px;
    }
    .bcp-stats {
      margin-left: 24px;
    }
    .bcp-actions {
      width: 100%;
      justify-content: flex-end;
    }
  }

  /* ═══ JRPG STAT SHEET ═══ */
  .bcp-stats-sheet {
    margin-top: 8px;
    padding: 16px 20px;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(245,158,11,0.03), rgba(139,92,246,0.02));
    border: 1.5px solid rgba(245,158,11,0.12);
    backdrop-filter: blur(10px);
    animation: bcpSheetIn 0.3s ease-out;
  }
  @keyframes bcpSheetIn {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .bcp-sheet-title {
    font-size: 10px;
    font-weight: 800;
    color: #F59E0B;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(245,158,11,0.1);
  }

  .bcp-stat-row {
    margin-bottom: 14px;
  }
  .bcp-stat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .bcp-stat-name {
    font-size: 12px;
    font-weight: 700;
    color: #9A8A7A;
  }
  .bcp-stat-val {
    font-size: 13px;
    font-weight: 800;
    color: #F59E0B;
    font-variant-numeric: tabular-nums;
  }
  .bcp-stat-desc {
    font-size: 10px;
    color: #5A4D40;
    font-weight: 600;
    margin-bottom: 8px;
  }
  .bcp-stat-range {
    display: flex;
    justify-content: space-between;
    font-size: 9px;
    color: #4A3D30;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-top: 2px;
  }

  /* Preset buttons (JRPG style) */
  .bcp-preset-row {
    display: flex;
    gap: 6px;
  }
  .bcp-preset-btn {
    flex: 1;
    padding: 8px 4px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    cursor: pointer;
    transition: all 0.3s;
    background: rgba(255,255,255,0.03);
    border: 1.5px solid rgba(255,255,255,0.06);
    color: #5A4D40;
    text-align: center;
  }
  .bcp-preset-btn:hover {
    background: rgba(245,158,11,0.06);
    border-color: rgba(245,158,11,0.2);
    color: #9A8A7A;
  }
  .bcp-preset-active {
    background: rgba(245,158,11,0.1) !important;
    border-color: rgba(245,158,11,0.35) !important;
    color: #F59E0B !important;
    box-shadow: 0 0 10px rgba(245,158,11,0.12);
  }

  /* Thinking mode toggle */
  .bcp-toggle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .bcp-toggle {
    padding: 6px 16px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.3s;
    background: rgba(255,255,255,0.04);
    border: 1.5px solid rgba(255,255,255,0.08);
    color: #4A3D30;
    flex-shrink: 0;
  }
  .bcp-toggle-on {
    background: rgba(245,158,11,0.1);
    border-color: rgba(245,158,11,0.3);
    color: #F59E0B;
    box-shadow: 0 0 12px rgba(245,158,11,0.15);
  }
  .bcp-toggle:hover {
    border-color: rgba(245,158,11,0.4);
  }

  .bcp-sheet-hint {
    font-size: 10px;
    color: #4A3D30;
    font-weight: 600;
    text-align: center;
    padding-top: 8px;
    border-top: 1px solid rgba(255,255,255,0.04);
  }
`;

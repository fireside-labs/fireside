"use client";

import { useState, useEffect, useCallback } from "react";

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

  const fetchStatus = useCallback(async () => {
    try {
      const [brainRes, statusRes] = await Promise.all([
        fetch("/api/v1/brains/status"),
        fetch("/api/v1/status"),
      ]);
      const brain = await brainRes.json();
      const sys = await statusRes.json();
      setStatus(brain);
      setGpu(sys.gpu || null);
    } catch (e) {
      console.warn("[BrainControlPanel] fetch failed:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll every 4s
  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, 4000);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const handleStop = async () => {
    setActionPending("stop");
    try {
      // Stop = restart with no model (we use the restart endpoint which re-checks)
      await fetch("/api/v1/brains/restart", { method: "POST" });
      await fetchStatus();
    } finally {
      setActionPending(null);
    }
  };

  const handleRestart = async () => {
    setActionPending("restart");
    try {
      await fetch("/api/v1/brains/restart", { method: "POST" });
      setTimeout(fetchStatus, 2000);
    } finally {
      setActionPending(null);
    }
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

          {/* Model name */}
          <div className="bcp-model-info">
            <div className="bcp-label">ACTIVE BRAIN</div>
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
              onClick={handleRestart}
              disabled={actionPending !== null}
              title="Start Brain"
            >
              {actionPending === "restart" ? "⏳" : "▶"} START
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
`;

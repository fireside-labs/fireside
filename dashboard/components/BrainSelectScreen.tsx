"use client";

import { useState, useEffect, useCallback } from "react";
import EmberParticles from "@/components/EmberParticles";
import { playTick, playConfirm, playWhoosh } from "@/components/FiresideSounds";

/**
 * 🧠 BrainSelectScreen — RPG-style brain selection.
 *
 * Default: "Use Recommended" auto-picks based on VRAM.
 * Manual: Two-panel layout — archetypes left, models+quant right.
 */

// ── Data ────────────────────────────────────────────────────────────

interface ModelEntry {
  id: string;
  label: string;
  family: string;
  params: string;
  quants: string[];
  defaultQuant: string;
  sizes: Record<string, string>;   // quant → filesize
  vrams: Record<string, number>;   // quant → VRAM needed
  speed: string;
}

interface Archetype {
  id: string;
  emoji: string;
  label: string;
  tagline: string;
  desc: string;
  badge: "FREE" | "PAID";
  models: ModelEntry[];
}

const ARCHETYPES: Archetype[] = [
  {
    id: "fast",
    emoji: "⚡",
    label: "Fast",
    tagline: "Quick & capable",
    desc: "Runs on most hardware. Great for everyday use.",
    badge: "FREE",
    models: [
      {
        id: "llama-3.1-8b", label: "Llama 3.1 8B", family: "Meta", params: "8B",
        quants: ["Q4_K_M", "Q6_K", "Q8_0", "FP16"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "4.9 GB", "Q6_K": "6.6 GB", "Q8_0": "8.5 GB", "FP16": "16.1 GB" },
        vrams: { "Q4_K_M": 8, "Q6_K": 10, "Q8_0": 12, "FP16": 20 },
        speed: "~45 tok/s",
      },
      {
        id: "qwen-2.5-7b", label: "Qwen 2.5 7B", family: "Alibaba", params: "7B",
        quants: ["Q4_K_M", "Q6_K", "FP16"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "4.7 GB", "Q6_K": "6.3 GB", "FP16": "14.2 GB" },
        vrams: { "Q4_K_M": 8, "Q6_K": 10, "FP16": 18 },
        speed: "~42 tok/s",
      },
      {
        id: "mistral-7b", label: "Mistral v0.3 7B", family: "Mistral", params: "7B",
        quants: ["Q4_K_M", "Q6_K", "Q8_0", "FP16"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "4.4 GB", "Q6_K": "5.9 GB", "Q8_0": "7.7 GB", "FP16": "14.5 GB" },
        vrams: { "Q4_K_M": 8, "Q6_K": 10, "Q8_0": 12, "FP16": 18 },
        speed: "~40 tok/s",
      },
      {
        id: "gemma-2-9b", label: "Gemma 2 9B", family: "Google", params: "9B",
        quants: ["Q4_K_M", "Q6_K"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "5.8 GB", "Q6_K": "7.8 GB" },
        vrams: { "Q4_K_M": 8, "Q6_K": 10 },
        speed: "~38 tok/s",
      },
      {
        id: "phi-3-mini", label: "Phi-3 Mini 3.8B", family: "Microsoft", params: "3.8B",
        quants: ["Q4_K_M", "Q6_K"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "2.4 GB", "Q6_K": "3.1 GB" },
        vrams: { "Q4_K_M": 4, "Q6_K": 6 },
        speed: "~55 tok/s",
      },
      {
        id: "gemma-2-2b", label: "Gemma 2 2B", family: "Google", params: "2B",
        quants: ["Q6_K"], defaultQuant: "Q6_K",
        sizes: { "Q6_K": "2.1 GB" },
        vrams: { "Q6_K": 4 },
        speed: "~65 tok/s",
      },
    ],
  },
  {
    id: "deep",
    emoji: "🧠",
    label: "Deep",
    tagline: "Powerful reasoning",
    desc: "Advanced analysis. Needs more GPU power.",
    badge: "FREE",
    models: [
      {
        id: "qwen-2.5-14b", label: "Qwen 2.5 14B", family: "Alibaba", params: "14B",
        quants: ["Q4_K_M", "Q6_K"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "9.0 GB", "Q6_K": "12.1 GB" },
        vrams: { "Q4_K_M": 12, "Q6_K": 16 },
        speed: "~25 tok/s",
      },
      {
        id: "mistral-small-22b", label: "Mistral Small 22B", family: "Mistral", params: "22B",
        quants: ["Q4_K_M"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "14 GB" },
        vrams: { "Q4_K_M": 18 },
        speed: "~18 tok/s",
      },
      {
        id: "gemma-2-27b", label: "Gemma 2 27B", family: "Google", params: "27B",
        quants: ["Q4_K_M"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "17 GB" },
        vrams: { "Q4_K_M": 20 },
        speed: "~15 tok/s",
      },
      {
        id: "qwen-2.5-32b", label: "Qwen 2.5 32B", family: "Alibaba", params: "32B",
        quants: ["Q4_K_M"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "20 GB" },
        vrams: { "Q4_K_M": 24 },
        speed: "~12 tok/s",
      },
      {
        id: "qwen-2.5-72b", label: "Qwen 2.5 72B", family: "Alibaba", params: "72B",
        quants: ["Q4_K_M"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "44 GB" },
        vrams: { "Q4_K_M": 48 },
        speed: "~6 tok/s",
      },
      {
        id: "llama-3.1-70b", label: "Llama 3.1 70B", family: "Meta", params: "70B",
        quants: ["Q4_K_M"], defaultQuant: "Q4_K_M",
        sizes: { "Q4_K_M": "42 GB" },
        vrams: { "Q4_K_M": 48 },
        speed: "~5 tok/s",
      },
    ],
  },
  {
    id: "cloud",
    emoji: "☁️",
    label: "Cloud",
    tagline: "Unlimited power",
    desc: "No hardware needed. Requires API key.",
    badge: "PAID",
    models: [
      {
        id: "kimi-k2", label: "Kimi K2", family: "Moonshot", params: "MoE",
        quants: ["API"], defaultQuant: "API",
        sizes: { "API": "Cloud" }, vrams: { "API": 0 },
        speed: "~120 tok/s",
      },
      {
        id: "gpt-4o", label: "GPT-4o", family: "OpenAI", params: "—",
        quants: ["API"], defaultQuant: "API",
        sizes: { "API": "Cloud" }, vrams: { "API": 0 },
        speed: "~90 tok/s",
      },
      {
        id: "claude-3.5-sonnet", label: "Claude 3.5 Sonnet", family: "Anthropic", params: "—",
        quants: ["API"], defaultQuant: "API",
        sizes: { "API": "Cloud" }, vrams: { "API": 0 },
        speed: "~80 tok/s",
      },
      {
        id: "gemini-2-flash", label: "Gemini 2.0 Flash", family: "Google", params: "—",
        quants: ["API"], defaultQuant: "API",
        sizes: { "API": "Cloud" }, vrams: { "API": 0 },
        speed: "~100 tok/s",
      },
    ],
  },
];

// Friendly quality labels for quant levels
const QUANT_LABELS: Record<string, { name: string; desc: string }> = {
  "Q4_K_M": { name: "Low", desc: "Smallest · fastest" },
  "Q6_K":   { name: "Medium", desc: "Balanced" },
  "Q8_0":   { name: "High", desc: "Near-lossless" },
  "FP16":   { name: "Ultra", desc: "Full precision · largest" },
  "API":    { name: "Cloud", desc: "No download" },
};

// Intelligence presets — like game difficulty settings
interface Preset {
  id: string;
  emoji: string;
  label: string;
  desc: string;
  model: ModelEntry;
  archetype: string;
  quant: string;
  compatible: boolean;
}

function getPresets(vram: number): { presets: Preset[]; recommendedId: string } {
  const low: Preset = {
    id: "low", emoji: "🟢", label: "Low",
    desc: "Fast & lightweight. Runs on anything.",
    model: ARCHETYPES[0].models[4], // Phi-3 Mini 3.8B
    archetype: "fast", quant: "Q4_K_M",
    compatible: vram >= 4 || vram === 0,
  };
  const med: Preset = {
    id: "medium", emoji: "🟡", label: "Medium",
    desc: "Balanced smarts and speed. Great all-rounder.",
    model: ARCHETYPES[0].models[0], // Llama 3.1 8B
    archetype: "fast", quant: "Q4_K_M",
    compatible: vram >= 8 || vram === 0,
  };
  const high: Preset = {
    id: "high", emoji: "🔴", label: "High",
    desc: "Maximum intelligence. Needs strong GPU.",
    model: vram >= 24 ? ARCHETYPES[1].models[3] : ARCHETYPES[1].models[0], // 32B or 14B
    archetype: "deep", quant: "Q4_K_M",
    compatible: vram >= 12,
  };

  const presets = [low, med, high];
  const recommendedId = vram >= 24 ? "high" : vram >= 12 ? "high" : vram >= 8 ? "medium" : vram >= 4 ? "low" : "medium";
  return { presets, recommendedId };
}

// ── Exported types for backward compat ──

export interface BrainOption {
  id: string; emoji: string; label: string; model: string;
  headline: string; features: string[]; sizeLabel: string;
  speedLabel: string; badge: "FREE" | "PAID"; vramNeeded: number;
}

export const BRAIN_OPTIONS: BrainOption[] = ARCHETYPES.map(a => ({
  id: a.id, emoji: a.emoji, label: a.label,
  model: a.models[0]?.label || "Cloud",
  headline: a.desc,
  features: a.models.slice(0, 3).map(m => m.label),
  sizeLabel: a.models[0]?.sizes[a.models[0].defaultQuant] || "Cloud",
  speedLabel: a.models[0]?.speed || "—",
  badge: a.badge,
  vramNeeded: a.models[0]?.vrams[a.models[0].defaultQuant] || 0,
}));

// ── Component ───────────────────────────────────────────────────────

interface BrainSelectScreenProps {
  selected?: string;
  onSelect: (brainId: string) => void;
  detectedVram?: number;
  onBack?: () => void;
  fullscreen?: boolean;
  installed?: string[];
  activeBrain?: string;
  onInstall?: (brainId: string) => void;
  onSwitch?: (brainId: string) => void;
}

export default function BrainSelectScreen({
  selected: initialSelected,
  onSelect,
  detectedVram = 0,
  onBack,
  fullscreen = true,
}: BrainSelectScreenProps) {
  const { presets, recommendedId } = getPresets(detectedVram);
  const rec = presets.find(p => p.id === recommendedId)!;

  const [mode, setMode] = useState<"recommended" | "manual">("recommended");
  const [selectedPreset, setSelectedPreset] = useState(recommendedId);
  const [selectedArchetype, setSelectedArchetype] = useState(rec.archetype);
  const [selectedModel, setSelectedModel] = useState<string>(rec.model.id);
  const [selectedQuant, setSelectedQuant] = useState<string>(rec.quant);
  const [confirming, setConfirming] = useState(false);
  const [flashClass, setFlashClass] = useState("");

  const archetype = ARCHETYPES.find(a => a.id === selectedArchetype)!;
  const model = archetype.models.find(m => m.id === selectedModel) || archetype.models[0];

  const handleConfirm = () => {
    if (confirming) return;
    setConfirming(true);
    playConfirm();
    setFlashClass("bss-flash");
    setTimeout(() => {
      onSelect(selectedArchetype);
      setConfirming(false);
      setFlashClass("");
    }, 600);
  };

  const selectArchetype = (id: string) => {
    playTick();
    setSelectedArchetype(id);
    const arch = ARCHETYPES.find(a => a.id === id)!;
    setSelectedModel(arch.models[0].id);
    setSelectedQuant(arch.models[0].defaultQuant);
  };

  const selectModel = (m: ModelEntry) => {
    playTick();
    setSelectedModel(m.id);
    setSelectedQuant(m.defaultQuant);
  };

  const selectQuant = (q: string) => {
    playTick();
    setSelectedQuant(q);
  };

  const currentSize = model.sizes[selectedQuant] || "—";
  const currentVram = model.vrams[selectedQuant] || 0;
  const compatible = currentVram === 0 || detectedVram >= currentVram;

  const rootClass = fullscreen ? "bss-root bss-fullscreen" : "bss-root bss-inline";

  return (
    <div className={rootClass}>
      <style>{brainSelectCSS}</style>
      {flashClass && <div className={flashClass} />}
      <EmberParticles intensity={15} className="bss-embers" />

      <div className="bss-container">
        {/* Header */}
        <div className="bss-header">
          <p className="bss-eyebrow">Choose your brain</p>
          <h2 className="bss-title">How powerful should your AI be?</h2>
        </div>

        {/* ══ RECOMMENDED — 3 presets ══ */}
        {mode === "recommended" && (
          <div className="bss-rec-area">
            <p className="bss-rec-subtitle">
              {detectedVram > 0 ? `Detected ${detectedVram}GB VRAM` : "Select your AI intelligence level"}
            </p>

            <div className="bss-presets">
              {presets.map((p) => {
                const isSelected = p.id === selectedPreset;
                const isRec = p.id === recommendedId;
                return (
                  <button
                    key={p.id}
                    className={`bss-preset ${isSelected ? 'bss-preset-active' : ''} ${!p.compatible ? 'bss-preset-dim' : ''}`}
                    onClick={() => {
                      playTick();
                      setSelectedPreset(p.id);
                      setSelectedArchetype(p.archetype);
                      setSelectedModel(p.model.id);
                      setSelectedQuant(p.quant);
                    }}
                  >
                    {isRec && <div className="bss-preset-rec">✨ Best for you</div>}
                    <span className="bss-preset-emoji">{p.emoji}</span>
                    <span className="bss-preset-label">{p.label}</span>
                    <span className="bss-preset-desc">{p.desc}</span>
                    <div className="bss-preset-model">
                      <span>{p.model.label}</span>
                      <span className="bss-preset-size">{p.model.sizes[p.quant]}</span>
                    </div>
                    {!p.compatible && <span className="bss-preset-warn">⚠ Not enough VRAM</span>}
                    <div className={`bss-radio ${isSelected ? 'bss-radio-on' : ''}`}>
                      {isSelected && <div className="bss-radio-dot" />}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="bss-rec-actions">
              <button
                className={`bss-btn-confirm ${confirming ? "bss-btn-pulse" : ""}`}
                onClick={handleConfirm}
                disabled={confirming}
              >
                {confirming ? "Setting up..." : `Continue with ${presets.find(p => p.id === selectedPreset)!.label} →`}
              </button>
              <button className="bss-btn-manual" onClick={() => { playTick(); setMode("manual"); }}>
                I know what I want — choose model &amp; bits
              </button>
            </div>
          </div>
        )}

        {/* ══ MANUAL — Two Panel ══ */}
        {mode === "manual" && (
          <div className="bss-manual">
            {/* Left: Archetypes */}
            <div className="bss-archetypes">
              {ARCHETYPES.map((a) => (
                <button
                  key={a.id}
                  className={`bss-arch-card ${a.id === selectedArchetype ? "bss-arch-active" : ""}`}
                  onClick={() => selectArchetype(a.id)}
                >
                  <span className="bss-arch-emoji">{a.emoji}</span>
                  <div className="bss-arch-text">
                    <span className="bss-arch-label">{a.label}</span>
                    <span className="bss-arch-tag">{a.tagline}</span>
                  </div>
                  <span className={`bss-arch-badge bss-arch-badge-${a.badge.toLowerCase()}`}>{a.badge}</span>
                </button>
              ))}
              <button className="bss-btn-rec-back" onClick={() => { playTick(); setMode("recommended"); }}>
                ← Use Recommended
              </button>
            </div>

            {/* Right: Models for selected archetype */}
            <div className="bss-models-panel">
              <h4 className="bss-models-title">{archetype.emoji} {archetype.label} Models</h4>

              <div className="bss-models-list">
                {archetype.models.map((m) => {
                  const isActive = m.id === selectedModel;
                  const mVram = m.vrams[m.defaultQuant];
                  const mCompat = mVram === 0 || detectedVram >= mVram;
                  return (
                    <button
                      key={m.id}
                      className={`bss-model-card ${isActive ? "bss-model-card-active" : ""} ${!mCompat ? "bss-model-card-dim" : ""}`}
                      onClick={() => selectModel(m)}
                    >
                      <div className="bss-model-top">
                        <span className="bss-model-name">{m.label}</span>
                        <span className="bss-model-family">{m.family}</span>
                      </div>
                      <div className="bss-model-bottom">
                        <span className="bss-model-params">{m.params}</span>
                        <span className="bss-model-speed">{m.speed}</span>
                        <span className="bss-model-size">{m.sizes[m.defaultQuant]}</span>
                        {!mCompat && <span className="bss-model-warn">⚠ {mVram}GB</span>}
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Quant selector */}
              {model.quants.length > 1 && (
                <div className="bss-quant-area">
                  <span className="bss-quant-label">Quality</span>
                  <div className="bss-quant-pills">
                    {model.quants.map(q => {
                      const ql = QUANT_LABELS[q] || { name: q, desc: "" };
                      return (
                        <button
                          key={q}
                          className={`bss-quant-pill ${q === selectedQuant ? "bss-quant-active" : ""}`}
                          onClick={() => selectQuant(q)}
                        >
                          <span className="bss-quant-name">{ql.name}</span>
                          <span className="bss-quant-tech">{q}</span>
                          <span className="bss-quant-size">{model.sizes[q]}</span>
                        </button>
                      );
                    })}
                  </div>
                  {!compatible && (
                    <p className="bss-quant-warn">⚠ This config needs {currentVram}GB VRAM (you have {detectedVram}GB)</p>
                  )}
                </div>
              )}

              {/* RPG Stat Bars */}
              <div className="bss-stats">
                {(() => {
                  // Calculate stats from model + quant
                  const paramNum = parseFloat(model.params) || 0;
                  const intell = Math.min(100, Math.round((paramNum / 72) * 100));
                  const speedNum = parseFloat(model.speed.replace(/[^0-9.]/g, '')) || 0;
                  const spd = Math.min(100, Math.round((speedNum / 120) * 100));
                  const sizeStr = currentSize.replace(/[^0-9.]/g, '');
                  const sizeNum = parseFloat(sizeStr) || 0;
                  const siz = Math.min(100, Math.round((sizeNum / 50) * 100));
                  const qualIdx = ["Q4_K_M", "Q6_K", "Q8_0", "FP16", "API"].indexOf(selectedQuant);
                  const qual = selectedQuant === "API" ? 95 : Math.round(((qualIdx + 1) / 4) * 100);

                  return (
                    <>
                      <div className="bss-stat-row">
                        <span className="bss-stat-icon">🧠</span>
                        <span className="bss-stat-name">Intelligence</span>
                        <div className="bss-stat-bar">
                          <div className="bss-stat-fill bss-stat-intel" style={{ width: `${intell}%` }} />
                        </div>
                        <span className="bss-stat-val">{model.params}</span>
                      </div>
                      <div className="bss-stat-row">
                        <span className="bss-stat-icon">⚡</span>
                        <span className="bss-stat-name">Speed</span>
                        <div className="bss-stat-bar">
                          <div className="bss-stat-fill bss-stat-speed" style={{ width: `${spd}%` }} />
                        </div>
                        <span className="bss-stat-val">{model.speed}</span>
                      </div>
                      <div className="bss-stat-row">
                        <span className="bss-stat-icon">💎</span>
                        <span className="bss-stat-name">Quality</span>
                        <div className="bss-stat-bar">
                          <div className="bss-stat-fill bss-stat-qual" style={{ width: `${qual}%` }} />
                        </div>
                        <span className="bss-stat-val">{selectedQuant}</span>
                      </div>
                      <div className="bss-stat-row">
                        <span className="bss-stat-icon">💾</span>
                        <span className="bss-stat-name">Download</span>
                        <div className="bss-stat-bar">
                          <div className="bss-stat-fill bss-stat-size" style={{ width: `${siz}%` }} />
                        </div>
                        <span className="bss-stat-val">{currentSize}</span>
                      </div>
                    </>
                  );
                })()}
              </div>
            </div>
          </div>
        )}

        {/* Action bar (manual mode) */}
        {mode === "manual" && (
          <div className="bss-actions">
            {onBack && (
              <button className="bss-btn-back" onClick={() => { playWhoosh(); onBack(); }}>← Back</button>
            )}
            <button
              className={`bss-btn-confirm ${confirming ? "bss-btn-pulse" : ""}`}
              onClick={handleConfirm}
              disabled={confirming}
            >
              {confirming ? "Setting up..." : `Continue with ${model.label} →`}
            </button>
          </div>
        )}

        {/* Back button (recommended mode) */}
        {mode === "recommended" && onBack && (
          <div className="bss-actions" style={{ marginTop: 8 }}>
            <button className="bss-btn-back" onClick={() => { playWhoosh(); onBack(); }}>← Back</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
// CSS
// ════════════════════════════════════════════════════════════════════

const brainSelectCSS = `
  .bss-root {
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    color: #F0DCC8;
    position: relative; overflow: hidden;
  }
  .bss-fullscreen {
    position: fixed; inset: 0; z-index: 9998;
    background: #0a0a0f;
    display: flex; align-items: center; justify-content: center;
  }
  .bss-inline {
    width: 100%; min-height: 480px;
    display: flex; align-items: center; justify-content: center;
  }
  .bss-embers { position: fixed !important; inset: 0 !important; z-index: 0 !important; }

  .bss-root::before {
    content: ''; position: absolute; inset: 0; pointer-events: none;
    background:
      radial-gradient(ellipse 700px 400px at 50% 90%, rgba(217,119,6,0.06) 0%, transparent 70%),
      radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.6) 100%);
    z-index: 1;
  }

  .bss-container {
    position: relative; z-index: 5;
    max-width: 960px; width: 100%; padding: 32px 24px;
    display: flex; flex-direction: column; align-items: center;
    animation: bssEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  @keyframes bssEnter {
    from { opacity: 0; transform: translateY(24px); filter: blur(4px); }
    to { opacity: 1; transform: translateY(0); filter: blur(0); }
  }

  .bss-header { text-align: center; margin-bottom: 28px; }
  .bss-eyebrow {
    font-size: 11px; font-weight: 700; color: var(--color-neon, #FBBF24);
    letter-spacing: 3px; text-transform: uppercase; margin-bottom: 8px;
  }
  .bss-title {
    font-size: 30px; font-weight: 800; color: #FFFFFF;
    letter-spacing: -0.5px; margin-bottom: 4px;
  }

  /* ═══ RECOMMENDED MODE ═══ */
  .bss-rec-area {
    display: flex; flex-direction: column; align-items: center;
    width: 100%; max-width: 640px;
    animation: bssEnter 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
  }
  .bss-rec-subtitle {
    font-size: 12px; color: #5A4D40; margin: 0 0 20px;
    letter-spacing: 1px; text-transform: uppercase; font-weight: 600;
  }

  .bss-presets {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 12px; width: 100%; margin-bottom: 24px;
  }
  .bss-preset {
    position: relative; padding: 28px 18px 20px;
    border-radius: 18px;
    background: rgba(18,18,26,0.75);
    backdrop-filter: blur(16px);
    border: 1.5px solid rgba(255,255,255,0.05);
    cursor: pointer; text-align: center;
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    animation: bssEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
  }
  .bss-preset:hover {
    border-color: rgba(217,119,6,0.25);
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.4);
  }
  .bss-preset-active {
    border-color: var(--color-neon, #FBBF24) !important;
    box-shadow: 0 0 0 1px var(--color-neon, #FBBF24), 0 8px 40px rgba(251,191,36,0.12) !important;
    transform: translateY(-4px) !important;
  }
  .bss-preset-dim { opacity: 0.35; }

  .bss-preset-rec {
    position: absolute; top: -1px; left: 50%; transform: translateX(-50%);
    font-size: 9px; font-weight: 800; color: #0A0A0A;
    background: linear-gradient(135deg, #FBBF24, #F59E0B);
    padding: 4px 14px; border-radius: 0 0 10px 10px;
    z-index: 5; letter-spacing: 0.3px; white-space: nowrap;
  }
  .bss-preset-emoji { font-size: 36px; margin-top: 4px; }
  .bss-preset-label { font-size: 18px; font-weight: 800; color: #F0DCC8; }
  .bss-preset-desc { font-size: 11px; color: #7A6A5A; line-height: 1.4; min-height: 30px; }
  .bss-preset-model {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.04);
    width: 100%; font-size: 11px; color: #5A4D40;
    font-family: 'SF Mono', 'JetBrains Mono', monospace;
  }
  .bss-preset-size { font-size: 10px; color: #7A6A5A; }
  .bss-preset-warn { font-size: 9px; color: #F59E0B; font-weight: 600; margin-top: 4px; }

  /* Radio indicator */
  .bss-radio {
    position: absolute; top: 12px; right: 12px;
    width: 18px; height: 18px; border-radius: 50%;
    border: 2px solid rgba(255,255,255,0.08);
    display: flex; align-items: center; justify-content: center;
    transition: all 0.25s ease; z-index: 5;
  }
  .bss-radio-on { border-color: var(--color-neon, #FBBF24); }
  .bss-radio-dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--color-neon, #FBBF24);
    box-shadow: 0 0 8px rgba(251,191,36,0.5);
    animation: radioPop 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes radioPop { from { transform: scale(0); } to { transform: scale(1); } }

  .bss-rec-desc { font-size: 13px; color: #A09080; margin: 0; line-height: 1.4; }

  .bss-rec-actions {
    display: flex; flex-direction: column; align-items: center; gap: 10px;
  }
  .bss-btn-manual {
    background: none; border: none; cursor: pointer;
    color: #5A4D40; font-size: 12px; font-weight: 600;
    letter-spacing: 1px; text-transform: uppercase;
    padding: 6px 0; transition: color 0.2s;
  }
  .bss-btn-manual:hover { color: var(--color-neon, #FBBF24); }

  /* ═══ MANUAL MODE — Two Panel ═══ */
  .bss-manual {
    display: grid; grid-template-columns: 200px 1fr;
    gap: 16px; width: 100%;
    animation: bssEnter 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
    margin-bottom: 20px;
  }

  /* Left: Archetypes */
  .bss-archetypes {
    display: flex; flex-direction: column; gap: 6px;
  }
  .bss-arch-card {
    display: flex; align-items: center; gap: 10px;
    padding: 14px 12px; border-radius: 12px;
    background: rgba(18,18,26,0.6);
    border: 1.5px solid rgba(255,255,255,0.04);
    cursor: pointer; transition: all 0.25s ease;
    text-align: left;
  }
  .bss-arch-card:hover {
    border-color: rgba(217,119,6,0.2);
    background: rgba(26,26,36,0.7);
  }
  .bss-arch-active {
    border-color: var(--color-neon, #FBBF24) !important;
    background: rgba(251,191,36,0.06) !important;
    box-shadow: 0 0 20px rgba(251,191,36,0.08);
  }
  .bss-arch-emoji { font-size: 24px; flex-shrink: 0; }
  .bss-arch-text { flex: 1; display: flex; flex-direction: column; }
  .bss-arch-label { font-size: 14px; font-weight: 700; color: #F0DCC8; }
  .bss-arch-tag { font-size: 10px; color: #5A4D40; }
  .bss-arch-badge {
    font-size: 8px; font-weight: 800; letter-spacing: 0.8px;
    padding: 2px 8px; border-radius: 10px;
  }
  .bss-arch-badge-free { background: rgba(52,211,153,0.12); color: #34D399; }
  .bss-arch-badge-paid { background: rgba(168,85,247,0.12); color: #A78BFA; }
  .bss-btn-rec-back {
    background: none; border: none; cursor: pointer;
    color: #5A4D40; font-size: 11px; font-weight: 600;
    text-align: left; padding: 8px 12px;
    transition: color 0.2s; margin-top: 4px;
  }
  .bss-btn-rec-back:hover { color: var(--color-neon, #FBBF24); }

  /* Right: Models panel */
  .bss-models-panel {
    background: rgba(12,12,20,0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 16px; padding: 18px;
    display: flex; flex-direction: column; gap: 12px;
  }
  .bss-models-title {
    font-size: 13px; font-weight: 700; color: #F0DCC8;
    margin: 0; letter-spacing: 0.5px;
  }

  .bss-models-list {
    display: flex; flex-direction: column; gap: 4px;
    max-height: 260px; overflow-y: auto;
  }
  .bss-models-list::-webkit-scrollbar { width: 3px; }
  .bss-models-list::-webkit-scrollbar-thumb { background: rgba(251,191,36,0.15); border-radius: 2px; }

  .bss-model-card {
    display: flex; flex-direction: column; gap: 3px;
    padding: 10px 12px; border-radius: 10px;
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer; transition: all 0.2s ease;
    text-align: left;
  }
  .bss-model-card:hover {
    background: rgba(251,191,36,0.03);
    border-color: rgba(251,191,36,0.12);
  }
  .bss-model-card-active {
    background: rgba(251,191,36,0.06) !important;
    border-color: var(--color-neon, #FBBF24) !important;
  }
  .bss-model-card-dim { opacity: 0.4; }

  .bss-model-top { display: flex; align-items: baseline; gap: 8px; }
  .bss-model-name { font-size: 13px; font-weight: 600; color: #F0DCC8; }
  .bss-model-family { font-size: 10px; color: #5A4D40; font-weight: 500; }

  .bss-model-bottom {
    display: flex; gap: 10px; align-items: center;
    font-size: 10px; color: #7A6A5A;
    font-family: 'SF Mono', 'JetBrains Mono', monospace;
  }
  .bss-model-warn { color: #F59E0B; font-weight: 600; }

  /* Quant pills */
  .bss-quant-area {
    display: flex; flex-direction: column; gap: 6px;
    padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.04);
  }
  .bss-quant-label {
    font-size: 10px; font-weight: 700; color: #5A4D40;
    text-transform: uppercase; letter-spacing: 1.5px;
  }
  .bss-quant-pills { display: flex; gap: 6px; }
  .bss-quant-pill {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    padding: 8px 14px; border-radius: 10px;
    background: rgba(18,18,26,0.6);
    border: 1px solid rgba(255,255,255,0.04);
    cursor: pointer; transition: all 0.2s;
    font-size: 12px; font-weight: 600; color: #7A6A5A;
    font-family: 'SF Mono', 'JetBrains Mono', monospace;
  }
  .bss-quant-pill:hover { border-color: rgba(217,119,6,0.2); color: #F0DCC8; }
  .bss-quant-active {
    border-color: var(--color-neon, #FBBF24) !important;
    background: rgba(251,191,36,0.06) !important;
    color: #FBBF24 !important;
  }
  .bss-quant-size { font-size: 9px; color: #5A4D40; font-weight: 400; }
  .bss-quant-name { font-size: 13px; font-weight: 700; color: inherit; }
  .bss-quant-tech { font-size: 8px; color: #5A4D40; font-family: 'SF Mono', monospace; letter-spacing: 0.5px; }
  .bss-quant-warn {
    font-size: 10px; color: #F59E0B; font-weight: 600; margin: 0;
  }

  /* RPG Stat Bars */
  .bss-stats {
    display: flex; flex-direction: column; gap: 6px;
    padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.04);
  }
  .bss-stat-row {
    display: flex; align-items: center; gap: 8px;
  }
  .bss-stat-icon { font-size: 12px; width: 16px; text-align: center; }
  .bss-stat-name {
    font-size: 10px; font-weight: 600; color: #5A4D40;
    width: 75px; flex-shrink: 0; text-transform: uppercase; letter-spacing: 0.5px;
  }
  .bss-stat-bar {
    flex: 1; height: 8px; border-radius: 4px;
    background: rgba(255,255,255,0.04); overflow: hidden;
    position: relative;
  }
  .bss-stat-fill {
    height: 100%; border-radius: 4px;
    transition: width 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
  }
  .bss-stat-fill::after {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15));
    border-radius: inherit;
  }
  .bss-stat-intel { background: linear-gradient(90deg, #92400E, #FBBF24); }
  .bss-stat-speed { background: linear-gradient(90deg, #065F46, #34D399); }
  .bss-stat-qual  { background: linear-gradient(90deg, #5B21B6, #A78BFA); }
  .bss-stat-size  { background: linear-gradient(90deg, #1E3A5F, #60A5FA); }
  .bss-stat-val {
    font-size: 10px; font-weight: 600; color: #7A6A5A;
    width: 55px; text-align: right; flex-shrink: 0;
    font-family: 'SF Mono', 'JetBrains Mono', monospace;
  }

  /* ═══ SHARED ═══ */
  .bss-actions {
    display: flex; align-items: center; justify-content: center;
    gap: 16px; width: 100%;
  }
  .bss-btn-back {
    background: none; border: 1px solid rgba(255,255,255,0.06);
    color: #7A6A5A; font-size: 14px; cursor: pointer;
    padding: 14px 28px; border-radius: 12px;
    transition: all 0.2s; font-weight: 600;
  }
  .bss-btn-back:hover { color: #F0DCC8; border-color: rgba(255,255,255,0.15); }

  .bss-btn-confirm {
    padding: 16px 48px; border-radius: 14px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 15px; font-weight: 800; letter-spacing: 0.5px;
    box-shadow: 0 4px 24px rgba(245,158,11,0.3), inset 0 1px 0 rgba(255,255,255,0.2);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative; overflow: hidden;
  }
  .bss-btn-confirm::before {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    transform: translateX(-100%); transition: transform 0.6s ease;
  }
  .bss-btn-confirm:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 8px 32px rgba(245,158,11,0.5);
  }
  .bss-btn-confirm:hover::before { transform: translateX(100%); }
  .bss-btn-pulse { animation: bssPulse 0.4s ease-in-out; }
  @keyframes bssPulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.04); box-shadow: 0 0 50px rgba(245,158,11,0.5); }
    100% { transform: scale(1); }
  }

  .bss-flash {
    position: fixed; inset: 0; z-index: 9999;
    background: rgba(251,191,36,0.2);
    animation: bssFlash 0.6s ease-out forwards;
    pointer-events: none;
  }
  @keyframes bssFlash {
    0% { opacity: 0; } 15% { opacity: 1; } 100% { opacity: 0; }
  }

  @media (max-width: 768px) {
    .bss-manual { grid-template-columns: 1fr; }
    .bss-archetypes { flex-direction: row; overflow-x: auto; }
    .bss-arch-card { min-width: 140px; }
    .bss-title { font-size: 24px; }
  }
`;

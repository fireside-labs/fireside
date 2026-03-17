"use client";

import { useState, useMemo } from "react";

/* ═══════════════════════════════════════════════════════════════════
   Brain Select — Two-Screen RPG Flow
   Screen 1: Three category boxes (Speed / Power / Specialist)
   Screen 2: Filterable model list + expandable cards + inline quant + stat bars
   ═══════════════════════════════════════════════════════════════════ */

// ── Data ──

interface ModelDef {
  id: string;
  label: string;
  family: string;
  params: string;
  paramNum: number;
  speed: string;
  speedNum: number;
  category: "speed" | "power" | "specialist";
  tags: string[];
  quants: string[];
  sizes: Record<string, string>;
  vrams: Record<string, number>;
}

const QUANT_META: Record<string, { label: string; bits: string; quality: number }> = {
  Q2_K:   { label: "Tiny",   bits: "2-bit", quality: 15 },
  Q4_K_M: { label: "Low",    bits: "4-bit", quality: 35 },
  Q6_K:   { label: "Medium", bits: "6-bit", quality: 60 },
  Q8_0:   { label: "High",   bits: "8-bit", quality: 80 },
  FP16:   { label: "Ultra",  bits: "16-bit", quality: 100 },
  API:    { label: "Cloud",  bits: "API",   quality: 95 },
};

const MODELS: ModelDef[] = [
  // ── Speed ──
  {
    id: "phi-3-mini", label: "Phi-3 Mini", family: "Microsoft",
    params: "3.8B", paramNum: 3.8, speed: "~80 tok/s", speedNum: 80,
    category: "speed", tags: ["compact", "efficient"],
    quants: ["Q4_K_M", "Q6_K", "Q8_0"],
    sizes: { Q4_K_M: "2.2 GB", Q6_K: "2.9 GB", Q8_0: "3.8 GB" },
    vrams: { Q4_K_M: 4, Q6_K: 5, Q8_0: 6 },
  },
  {
    id: "llama-3.1-8b", label: "Llama 3.1 8B", family: "Meta",
    params: "8B", paramNum: 8, speed: "~45 tok/s", speedNum: 45,
    category: "speed", tags: ["general", "reliable"],
    quants: ["Q4_K_M", "Q6_K", "Q8_0", "FP16"],
    sizes: { Q4_K_M: "4.9 GB", Q6_K: "6.6 GB", Q8_0: "8.5 GB", FP16: "16 GB" },
    vrams: { Q4_K_M: 7, Q6_K: 9, Q8_0: 11, FP16: 18 },
  },
  {
    id: "qwen-3.5-7b", label: "Qwen 3.5 7B", family: "Alibaba",
    params: "7B", paramNum: 7, speed: "~50 tok/s", speedNum: 50,
    category: "speed", tags: ["general", "multilingual"],
    quants: ["Q4_K_M", "Q6_K", "Q8_0", "FP16"],
    sizes: { Q4_K_M: "4.4 GB", Q6_K: "5.9 GB", Q8_0: "7.6 GB", FP16: "14 GB" },
    vrams: { Q4_K_M: 6, Q6_K: 8, Q8_0: 10, FP16: 16 },
  },
  {
    id: "mistral-7b", label: "Mistral 7B", family: "Mistral AI",
    params: "7B", paramNum: 7, speed: "~50 tok/s", speedNum: 50,
    category: "speed", tags: ["general", "creative"],
    quants: ["Q4_K_M", "Q6_K", "Q8_0", "FP16"],
    sizes: { Q4_K_M: "4.4 GB", Q6_K: "5.9 GB", Q8_0: "7.6 GB", FP16: "14.5 GB" },
    vrams: { Q4_K_M: 6, Q6_K: 8, Q8_0: 10, FP16: 17 },
  },
  // ── Power ──
  {
    id: "qwen-2.5-14b", label: "Qwen 2.5 14B", family: "Alibaba",
    params: "14B", paramNum: 14, speed: "~25 tok/s", speedNum: 25,
    category: "power", tags: ["deep", "reasoning"],
    quants: ["Q4_K_M", "Q6_K", "Q8_0", "FP16"],
    sizes: { Q4_K_M: "9.0 GB", Q6_K: "12 GB", Q8_0: "15 GB", FP16: "28 GB" },
    vrams: { Q4_K_M: 12, Q6_K: 14, Q8_0: 18, FP16: 30 },
  },
  {
    id: "llama-3.1-70b", label: "Llama 3.1 70B", family: "Meta",
    params: "70B", paramNum: 70, speed: "~8 tok/s", speedNum: 8,
    category: "power", tags: ["flagship", "deep"],
    quants: ["Q2_K", "Q4_K_M", "Q6_K"],
    sizes: { Q2_K: "26 GB", Q4_K_M: "40 GB", Q6_K: "54 GB" },
    vrams: { Q2_K: 28, Q4_K_M: 44, Q6_K: 58 },
  },
  {
    id: "command-r-35b", label: "Command R 35B", family: "Cohere",
    params: "35B", paramNum: 35, speed: "~15 tok/s", speedNum: 15,
    category: "power", tags: ["agents", "tools"],
    quants: ["Q4_K_M", "Q6_K"],
    sizes: { Q4_K_M: "20 GB", Q6_K: "27 GB" },
    vrams: { Q4_K_M: 22, Q6_K: 30 },
  },
  // ── Specialist ──
  {
    id: "qwen-2.5-coder-7b", label: "Qwen 2.5 Coder 7B", family: "Alibaba",
    params: "7B", paramNum: 7, speed: "~50 tok/s", speedNum: 50,
    category: "specialist", tags: ["code", "programming"],
    quants: ["Q4_K_M", "Q6_K", "Q8_0", "FP16"],
    sizes: { Q4_K_M: "4.4 GB", Q6_K: "5.9 GB", Q8_0: "7.6 GB", FP16: "14 GB" },
    vrams: { Q4_K_M: 6, Q6_K: 8, Q8_0: 10, FP16: 16 },
  },
  {
    id: "deepseek-coder-v2", label: "DeepSeek Coder V2", family: "DeepSeek",
    params: "16B", paramNum: 16, speed: "~22 tok/s", speedNum: 22,
    category: "specialist", tags: ["code", "math"],
    quants: ["Q4_K_M", "Q6_K", "Q8_0"],
    sizes: { Q4_K_M: "9.5 GB", Q6_K: "12.8 GB", Q8_0: "16.5 GB" },
    vrams: { Q4_K_M: 12, Q6_K: 15, Q8_0: 19 },
  },
  // ── Cloud ──
  {
    id: "cloud-gpt4", label: "GPT-4o (Cloud)", family: "OpenAI",
    params: "~200B+", paramNum: 200, speed: "~60 tok/s", speedNum: 60,
    category: "power", tags: ["cloud", "api"],
    quants: ["API"],
    sizes: { API: "0 GB" },
    vrams: { API: 0 },
  },
];

const CATEGORIES = [
  { id: "speed" as const, icon: "⚡", img: "/hub/card_speed.png", label: "Speed", color: "#F59E0B", subtitle: "Fast responses, lighter models", bg: "rgba(245,158,11,0.06)" },
  { id: "power" as const, icon: "🧠", img: "/hub/card_power.png", label: "Power", color: "#A78BFA", subtitle: "Deep intelligence, larger models", bg: "rgba(167,139,250,0.06)" },
  { id: "specialist" as const, icon: "🔧", img: "/hub/card_specialist.png", label: "Specialist", color: "#34D399", subtitle: "Code, math, creative", bg: "rgba(52,211,153,0.06)" },
];

// ── Component ──

interface Props {
  selected?: string;
  onSelect: (modelId: string, label: string, size: string, quant: string) => void;
  detectedVram?: number;
  onBack?: () => void;
  fullscreen?: boolean;
}

export default function BrainSelectScreen({ onSelect, detectedVram = 0, onBack, fullscreen }: Props) {
  const [screen, setScreen] = useState<"categories" | "models">("categories");
  const [category, setCategory] = useState<"speed" | "power" | "specialist">("speed");
  const [expandedModel, setExpandedModel] = useState<string | null>(null);
  const [selectedQuants, setSelectedQuants] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");

  const pickCategory = (cat: typeof category) => {
    setCategory(cat);
    setScreen("models");
    setExpandedModel(null);
    setSearch("");
  };

  const getQuant = (modelId: string, model: ModelDef) =>
    selectedQuants[modelId] || model.quants[0];

  const filteredModels = useMemo(() => {
    let list = MODELS.filter(m => m.category === category);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(m =>
        m.label.toLowerCase().includes(q) ||
        m.family.toLowerCase().includes(q) ||
        m.tags.some(t => t.includes(q))
      );
    }
    return list;
  }, [category, search]);

  const confirmModel = (model: ModelDef) => {
    const q = getQuant(model.id, model);
    const size = model.sizes[q] || "?";
    const qm = QUANT_META[q];
    const label = `${model.label} (${qm?.bits || q})`;
    onSelect(model.id, label, size, q);
  };

  const catColor = CATEGORIES.find(c => c.id === category)?.color || "#F59E0B";

  return (
    <div className={`bss2-root ${fullscreen ? "bss2-fullscreen" : ""}`}>
      <style>{css}</style>

      {/* ═══ SCREEN 1: CATEGORIES ═══ */}
      {screen === "categories" && (
        <div className="bss2-categories">
          <h2 className="bss2-title">Choose your path</h2>
          <p className="bss2-sub">What matters most to you?</p>
          <div className="bss2-cat-grid">
            {CATEGORIES.map((cat, i) => (
              <button
                key={cat.id}
                className="bss2-cat-card"
                onClick={() => pickCategory(cat.id)}
                style={{
                  "--cat-color": cat.color,
                  "--cat-bg": cat.bg,
                  animationDelay: `${i * 0.1}s`,
                } as React.CSSProperties}
              >
                <div className="bss2-cat-glow" />
                <div className="bss2-cat-shimmer" />
                <span className="bss2-cat-icon">{cat.icon}</span>
                <span className="bss2-cat-label">{cat.label}</span>
                <span className="bss2-cat-sub">{cat.subtitle}</span>
                <span className="bss2-cat-count">
                  {MODELS.filter(m => m.category === cat.id).length} models
                </span>
              </button>
            ))}
          </div>
          {onBack && (
            <button className="bss2-back-link" onClick={onBack}>
              ← Back to recommended
            </button>
          )}
        </div>
      )}

      {/* ═══ SCREEN 2: MODEL LIST ═══ */}
      {screen === "models" && (
        <div className="bss2-models">
          {/* Header */}
          <div className="bss2-models-header">
            <button className="bss2-back-btn" onClick={() => setScreen("categories")}>
              ← Back
            </button>
            <div className="bss2-models-title-area">
              <span className="bss2-cat-badge" style={{ background: catColor }}>
                {CATEGORIES.find(c => c.id === category)?.icon} {CATEGORIES.find(c => c.id === category)?.label}
              </span>
              {detectedVram > 0 && (
                <span className="bss2-vram-badge">💾 {detectedVram} GB VRAM</span>
              )}
            </div>
          </div>

          {/* Search */}
          <div className="bss2-search-wrap">
            <span className="bss2-search-icon">🔍</span>
            <input
              className="bss2-search"
              placeholder="Search models..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          {/* Model list */}
          <div className="bss2-model-list">
            {filteredModels.length === 0 && (
              <p className="bss2-empty">No models found. Try a different search.</p>
            )}
            {filteredModels.map(model => {
              const isExpanded = expandedModel === model.id;
              const q = getQuant(model.id, model);
              const qm = QUANT_META[q] || { label: q, bits: q, quality: 50 };
              const compatible = detectedVram >= (model.vrams[q] || 0);
              const intel = Math.min(100, Math.round((model.paramNum / 72) * 100));
              const spd = Math.min(100, Math.round((model.speedNum / 100) * 100));
              const sizeNum = parseFloat((model.sizes[q] || "0").replace(/[^0-9.]/g, ""));
              const siz = Math.min(100, Math.round((sizeNum / 60) * 100));

              return (
                <div
                  key={model.id}
                  className={`bss2-model-card ${isExpanded ? "bss2-expanded" : ""} ${!compatible && detectedVram > 0 ? "bss2-dim" : ""}`}
                  style={{ "--cat-color": catColor } as React.CSSProperties}
                >
                  {/* Collapsed header */}
                  <button
                    className="bss2-model-header"
                    onClick={() => setExpandedModel(isExpanded ? null : model.id)}
                  >
                    <div className="bss2-model-info">
                      <span className="bss2-model-name">{model.label}</span>
                      <span className="bss2-model-family">{model.family}</span>
                    </div>
                    <div className="bss2-model-badges">
                      <span className="bss2-param-badge">{model.params}</span>
                      <span className="bss2-speed-badge">{model.speed}</span>
                    </div>
                    <span className="bss2-chevron">{isExpanded ? "▾" : "▸"}</span>
                  </button>

                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="bss2-model-body">
                      {/* Tags */}
                      <div className="bss2-tags">
                        {model.tags.map(t => (
                          <span key={t} className="bss2-tag">{t}</span>
                        ))}
                      </div>

                      {/* Quant pills */}
                      <div className="bss2-quant-area">
                        <span className="bss2-quant-label">Quality</span>
                        <div className="bss2-quant-pills">
                          {model.quants.map(qOpt => {
                            const qInfo = QUANT_META[qOpt] || { label: qOpt, bits: qOpt };
                            return (
                              <button
                                key={qOpt}
                                className={`bss2-qpill ${qOpt === q ? "bss2-qpill-active" : ""}`}
                                onClick={() =>
                                  setSelectedQuants(prev => ({ ...prev, [model.id]: qOpt }))
                                }
                              >
                                <span className="bss2-qpill-name">{qInfo.label}</span>
                                <span className="bss2-qpill-bits">{qInfo.bits}</span>
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Stat bars */}
                      <div className="bss2-stats">
                        <div className="bss2-stat">
                          <span className="bss2-stat-icon">🧠</span>
                          <span className="bss2-stat-name">Intelligence</span>
                          <div className="bss2-stat-bar">
                            <div className="bss2-stat-fill bss2-fill-intel" style={{ width: `${intel}%` }} />
                          </div>
                          <span className="bss2-stat-val">{model.params}</span>
                        </div>
                        <div className="bss2-stat">
                          <span className="bss2-stat-icon">⚡</span>
                          <span className="bss2-stat-name">Speed</span>
                          <div className="bss2-stat-bar">
                            <div className="bss2-stat-fill bss2-fill-speed" style={{ width: `${spd}%` }} />
                          </div>
                          <span className="bss2-stat-val">{model.speed}</span>
                        </div>
                        <div className="bss2-stat">
                          <span className="bss2-stat-icon">💎</span>
                          <span className="bss2-stat-name">Quality</span>
                          <div className="bss2-stat-bar">
                            <div className="bss2-stat-fill bss2-fill-qual" style={{ width: `${qm.quality}%` }} />
                          </div>
                          <span className="bss2-stat-val">{qm.bits}</span>
                        </div>
                        <div className="bss2-stat">
                          <span className="bss2-stat-icon">💾</span>
                          <span className="bss2-stat-name">Download</span>
                          <div className="bss2-stat-bar">
                            <div className="bss2-stat-fill bss2-fill-size" style={{ width: `${siz}%` }} />
                          </div>
                          <span className="bss2-stat-val">{model.sizes[q]}</span>
                        </div>
                      </div>

                      {/* VRAM warning */}
                      {!compatible && detectedVram > 0 && (
                        <p className="bss2-vram-warn">
                          ⚠ Needs ~{model.vrams[q]} GB VRAM (you have {detectedVram} GB)
                        </p>
                      )}

                      {/* Confirm */}
                      <button className="bss2-confirm" onClick={() => confirmModel(model)}>
                        Select {model.label} ({qm.bits}) →
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
// CSS
// ════════════════════════════════════════════════════════════════════

const css = `
  .bss2-root {
    width: 100%; min-height: 100%;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    color: #F0DCC8;
    background: #080810;
  }
  .bss2-fullscreen {
    position: fixed; inset: 0; z-index: 100;
    background: #080810;
    overflow-y: auto;
  }

  /* ═══ SCREEN 1: CATEGORIES ═══ */
  .bss2-categories {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 40px 24px; min-height: 100vh; width: 100%;
    animation: fadeUp 0.5s ease forwards;
  }
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .bss2-title {
    font-size: 28px; font-weight: 800; margin: 0 0 8px;
    background: linear-gradient(135deg, #F0DCC8, #FBBF24);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .bss2-sub {
    font-size: 14px; color: #5A4D40; margin: 0 0 40px;
  }
  .bss2-cat-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 24px; max-width: 760px; width: 100%;
  }
  .bss2-cat-card {
    position: relative;
    display: flex; flex-direction: column;
    align-items: center; gap: 14px;
    padding: 48px 28px 36px;
    border-radius: 24px;
    aspect-ratio: 3 / 4;
    justify-content: center;
    background: radial-gradient(ellipse at 50% 30%,
      color-mix(in srgb, var(--cat-color) 10%, transparent) 0%,
      rgba(10,10,16,0.97) 60%);
    border: 1.5px solid color-mix(in srgb, var(--cat-color) 15%, transparent);
    cursor: pointer;
    transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    animation: cardPop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }
  @keyframes cardPop {
    from { opacity: 0; transform: translateY(40px) scale(0.85); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  /* Radial glow that BLEEDS outside the card */
  .bss2-cat-glow {
    position: absolute; top: -20px; left: 50%; transform: translateX(-50%);
    width: 200px; height: 200px; border-radius: 50%;
    background: radial-gradient(circle,
      color-mix(in srgb, var(--cat-color) 20%, transparent) 0%,
      color-mix(in srgb, var(--cat-color) 8%, transparent) 40%,
      transparent 70%);
    pointer-events: none;
    animation: glowPulse 3s ease-in-out infinite alternate;
    z-index: 0;
  }
  @keyframes glowPulse { 0% { opacity: 0.4; transform: translateX(-50%) scale(0.9); } 100% { opacity: 1; transform: translateX(-50%) scale(1.1); } }
  /* Diagonal shimmer sweep */
  .bss2-cat-shimmer {
    position: absolute; inset: 0;
    border-radius: 24px;
    overflow: hidden;
    pointer-events: none;
  }
  .bss2-cat-shimmer::after {
    content: ''; position: absolute; inset: -50% -50%;
    background: linear-gradient(
      105deg,
      transparent 30%,
      color-mix(in srgb, var(--cat-color) 5%, transparent) 45%,
      transparent 55%
    );
    animation: shimmerSweep 5s ease-in-out infinite;
  }
  @keyframes shimmerSweep {
    0% { transform: translateX(-150%); }
    40%, 100% { transform: translateX(250%); }
  }
  .bss2-cat-card:hover {
    transform: translateY(-10px) scale(1.05);
    border-color: color-mix(in srgb, var(--cat-color) 60%, transparent);
    box-shadow:
      0 24px 60px color-mix(in srgb, var(--cat-color) 20%, transparent),
      0 0 100px color-mix(in srgb, var(--cat-color) 10%, transparent);
  }
  .bss2-cat-card:hover .bss2-cat-glow {
    opacity: 1.3;
    width: 240px; height: 240px;
  }
  .bss2-cat-icon {
    font-size: 64px; position: relative; z-index: 2;
    filter: drop-shadow(0 0 25px color-mix(in srgb, var(--cat-color) 50%, transparent));
    animation: iconFloat 5s ease-in-out infinite;
  }
  @keyframes iconFloat {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
  }
  .bss2-cat-label {
    font-size: 20px; font-weight: 800; color: var(--cat-color);
    text-transform: uppercase; letter-spacing: 3px;
    position: relative; z-index: 2;
    text-shadow: 0 0 25px color-mix(in srgb, var(--cat-color) 35%, transparent);
  }
  .bss2-cat-sub {
    font-size: 12px; color: #5A4D40; text-align: center; line-height: 1.4;
    position: relative; z-index: 2;
  }
  .bss2-cat-count {
    font-size: 10px; color: #3A3530; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1px;
  }
  .bss2-back-link {
    margin-top: 32px;
    background: none; border: none; cursor: pointer;
    color: #5A4D40; font-size: 12px;
    transition: color 0.2s;
  }
  .bss2-back-link:hover { color: #F0DCC8; }

  /* ═══ SCREEN 2: MODELS ═══ */
  .bss2-models {
    width: 100%; max-width: 640px;
    min-height: 100vh;
    padding: 24px;
    margin: 0 auto;
    background: #080810;
    animation: fadeUp 0.4s ease forwards;
  }
  .bss2-models-header {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 16px;
  }
  .bss2-back-btn {
    background: none; border: 1px solid rgba(255,255,255,0.06);
    color: #7A6A5A; font-size: 12px; font-weight: 600; cursor: pointer;
    padding: 6px 14px; border-radius: 8px; transition: all 0.2s;
    flex-shrink: 0;
  }
  .bss2-back-btn:hover { color: #F0DCC8; border-color: rgba(217,119,6,0.3); }
  .bss2-models-title-area {
    display: flex; align-items: center; gap: 10px; flex: 1;
  }
  .bss2-cat-badge {
    font-size: 11px; font-weight: 700; color: #0A0A0A;
    padding: 4px 12px; border-radius: 6px;
    text-transform: uppercase; letter-spacing: 1px;
  }
  .bss2-vram-badge {
    font-size: 10px; color: #5A4D40; font-weight: 600;
    padding: 4px 10px; border-radius: 6px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.04);
  }

  /* Search */
  .bss2-search-wrap {
    position: relative; margin-bottom: 16px;
  }
  .bss2-search-icon {
    position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
    font-size: 14px; pointer-events: none;
  }
  .bss2-search {
    width: 100%; padding: 12px 14px 12px 40px;
    border-radius: 12px;
    background: rgba(18,18,26,0.6);
    border: 1px solid rgba(255,255,255,0.06);
    color: #F0DCC8; font-size: 13px; outline: none;
    transition: all 0.3s;
  }
  .bss2-search:focus {
    border-color: rgba(217,119,6,0.3);
    box-shadow: 0 0 20px rgba(245,158,11,0.06);
  }
  .bss2-search::placeholder { color: rgba(240,220,200,0.2); }

  /* Model list */
  .bss2-model-list {
    display: flex; flex-direction: column; gap: 8px;
    max-height: calc(100vh - 200px);
    overflow-y: auto;
    padding-right: 4px;
  }
  .bss2-model-list::-webkit-scrollbar { width: 3px; }
  .bss2-model-list::-webkit-scrollbar-thumb { background: rgba(245,158,11,0.15); border-radius: 2px; }

  .bss2-empty { color: #3A3530; text-align: center; font-size: 13px; padding: 40px 0; }

  /* Model card */
  .bss2-model-card {
    border-radius: 14px;
    background: rgba(18,18,26,0.4);
    border: 1px solid rgba(255,255,255,0.04);
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .bss2-model-card:hover {
    border-color: rgba(255,255,255,0.08);
  }
  .bss2-expanded {
    border-color: color-mix(in srgb, var(--cat-color) 25%, transparent);
    box-shadow: 0 8px 32px color-mix(in srgb, var(--cat-color) 8%, transparent);
  }
  .bss2-dim { opacity: 0.35; }

  .bss2-model-header {
    width: 100%; padding: 14px 16px;
    display: flex; align-items: center; gap: 12px;
    background: none; border: none; cursor: pointer;
    color: #F0DCC8; text-align: left;
  }
  .bss2-model-info { flex: 1; }
  .bss2-model-name { font-size: 14px; font-weight: 700; display: block; }
  .bss2-model-family { font-size: 10px; color: #5A4D40; }
  .bss2-model-badges { display: flex; gap: 6px; }
  .bss2-param-badge, .bss2-speed-badge {
    font-size: 10px; font-weight: 600; padding: 2px 8px;
    border-radius: 4px; background: rgba(255,255,255,0.04);
    color: #7A6A5A;
    font-family: 'SF Mono', 'JetBrains Mono', monospace;
  }
  .bss2-chevron { font-size: 12px; color: #3A3530; flex-shrink: 0; }

  /* Expanded body */
  .bss2-model-body {
    padding: 0 16px 16px;
    animation: bodyIn 0.3s ease forwards;
  }
  @keyframes bodyIn { from { opacity: 0; } to { opacity: 1; } }

  /* Tags */
  .bss2-tags { display: flex; gap: 6px; margin-bottom: 12px; }
  .bss2-tag {
    font-size: 9px; font-weight: 600; color: #5A4D40;
    padding: 2px 8px; border-radius: 4px;
    background: rgba(255,255,255,0.03);
    text-transform: uppercase; letter-spacing: 0.5px;
  }

  /* Quant pills */
  .bss2-quant-area { margin-bottom: 12px; }
  .bss2-quant-label {
    font-size: 10px; font-weight: 600; color: #3A3530;
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 6px; display: block;
  }
  .bss2-quant-pills { display: flex; gap: 6px; flex-wrap: wrap; }
  .bss2-qpill {
    display: flex; flex-direction: column; align-items: center;
    padding: 6px 14px; border-radius: 8px; cursor: pointer;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.04);
    transition: all 0.2s;
  }
  .bss2-qpill:hover { border-color: rgba(255,255,255,0.1); }
  .bss2-qpill-active {
    background: rgba(245,158,11,0.1);
    border-color: rgba(245,158,11,0.3);
  }
  .bss2-qpill-name { font-size: 11px; font-weight: 700; color: #F0DCC8; }
  .bss2-qpill-bits { font-size: 9px; color: #5A4D40; }

  /* Stat bars */
  .bss2-stats {
    display: flex; flex-direction: column; gap: 5px;
    margin-bottom: 12px;
  }
  .bss2-stat { display: flex; align-items: center; gap: 8px; }
  .bss2-stat-icon { font-size: 11px; width: 14px; text-align: center; }
  .bss2-stat-name {
    font-size: 9px; font-weight: 600; color: #3A3530;
    width: 70px; flex-shrink: 0;
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  .bss2-stat-bar {
    flex: 1; height: 6px; border-radius: 3px;
    background: rgba(255,255,255,0.04); overflow: hidden;
  }
  .bss2-stat-fill {
    height: 100%; border-radius: 3px;
    transition: width 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .bss2-stat-fill::after {
    content: ''; display: block; width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15));
    border-radius: inherit;
  }
  .bss2-fill-intel { background: linear-gradient(90deg, #92400E, #FBBF24); }
  .bss2-fill-speed { background: linear-gradient(90deg, #065F46, #34D399); }
  .bss2-fill-qual  { background: linear-gradient(90deg, #5B21B6, #A78BFA); }
  .bss2-fill-size  { background: linear-gradient(90deg, #1E3A5F, #60A5FA); }
  .bss2-stat-val {
    font-size: 9px; font-weight: 600; color: #5A4D40;
    width: 50px; text-align: right; flex-shrink: 0;
    font-family: 'SF Mono', 'JetBrains Mono', monospace;
  }

  /* VRAM warning */
  .bss2-vram-warn {
    font-size: 10px; color: #F59E0B; font-weight: 600;
    margin: 0 0 8px; padding: 6px 10px;
    border-radius: 6px; background: rgba(245,158,11,0.06);
  }

  /* Confirm */
  .bss2-confirm {
    width: 100%; padding: 12px;
    border-radius: 12px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 13px; font-weight: 800;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 20px rgba(245,158,11,0.2);
    transition: all 0.3s;
  }
  .bss2-confirm:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(245,158,11,0.35);
  }

  /* Responsive */
  @media (max-width: 600px) {
    .bss2-cat-grid { grid-template-columns: 1fr; max-width: 320px; }
  }
`;

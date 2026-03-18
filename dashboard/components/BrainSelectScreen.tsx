"use client";

import { useState, useMemo, useEffect } from "react";

/* ═══════════════════════════════════════════════════════════════════
   Brain Select — Premium Two-Screen RPG Flow
   Screen 1: Three category cards with generated card art + glow effects
   Screen 2: 3-column model grid + slide-out detail panel + mascot guide
   Ported from design_preview.html prototype
   ═══════════════════════════════════════════════════════════════════ */

// ── Data ──

interface QuantDef {
  label: string;
  bits: string;
  intel: number;
  spd: number;
  sizeGB: number;
  size: string;
}

interface ModelDef {
  id: string;
  name: string;
  family: string;
  params: string;
  speed: string;
  category: "speed" | "power" | "specialist";
  tags: string[];
  recommended: boolean;
  desc: string;
  quants: QuantDef[];
}

const MODELS: ModelDef[] = [
  // ── Speed ──
  {
    id: "phi-3-mini", name: "Phi-3 Mini", family: "Microsoft",
    params: "3.8B", speed: "~80 tok/s", category: "speed",
    tags: ["compact", "efficient"], recommended: false,
    desc: "Microsoft\u2019s ultra-compact model. Surprisingly capable for its size \u2014 trained on high-quality textbook data. Great for quick Q&A and simple tasks when you need instant responses.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 25, spd: 95, sizeGB: 2.2, size: "2.2 GB" },
      { label: "Medium", bits: "6-bit", intel: 30, spd: 90, sizeGB: 2.9, size: "2.9 GB" },
      { label: "High", bits: "8-bit", intel: 32, spd: 80, sizeGB: 3.8, size: "3.8 GB" },
    ],
  },
  {
    id: "llama-3.1-8b", name: "Llama 3.1 8B", family: "Meta",
    params: "8B", speed: "~45 tok/s", category: "speed",
    tags: ["general", "reliable"], recommended: true,
    desc: "Meta\u2019s open-source workhorse. Llama 3.1 set the standard for open models \u2014 reliable across every task from writing to analysis. The 8B version is the sweet spot of speed and smarts.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 45, spd: 70, sizeGB: 4.9, size: "4.9 GB" },
      { label: "Medium", bits: "6-bit", intel: 50, spd: 60, sizeGB: 6.6, size: "6.6 GB" },
      { label: "High", bits: "8-bit", intel: 55, spd: 50, sizeGB: 8.5, size: "8.5 GB" },
      { label: "Ultra", bits: "16-bit", intel: 58, spd: 35, sizeGB: 16, size: "16 GB" },
    ],
  },
  {
    id: "qwen-3.5-7b", name: "Qwen 3.5 7B", family: "Alibaba",
    params: "7B", speed: "~50 tok/s", category: "speed",
    tags: ["versatile", "thinking"], recommended: false,
    desc: "Alibaba\u2019s latest thinking model. Qwen 3.5 introduced hybrid reasoning \u2014 it can \u2018think step by step\u2019 for hard problems or respond instantly for simple ones. Multilingual powerhouse.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 50, spd: 75, sizeGB: 4.4, size: "4.4 GB" },
      { label: "Medium", bits: "6-bit", intel: 55, spd: 65, sizeGB: 5.6, size: "5.6 GB" },
      { label: "High", bits: "8-bit", intel: 60, spd: 55, sizeGB: 7.5, size: "7.5 GB" },
    ],
  },
  {
    id: "gemma-2-9b", name: "Gemma 2 9B", family: "Google",
    params: "9B", speed: "~40 tok/s", category: "speed",
    tags: ["balanced", "modern"], recommended: false,
    desc: "Google\u2019s open model built on Gemini research. Clean, balanced, and efficient. Punches above its weight on benchmarks. Great all-rounder with strong instruction following.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 50, spd: 65, sizeGB: 5.5, size: "5.5 GB" },
      { label: "Medium", bits: "6-bit", intel: 55, spd: 55, sizeGB: 7.0, size: "7.0 GB" },
      { label: "High", bits: "8-bit", intel: 58, spd: 45, sizeGB: 9.1, size: "9.1 GB" },
    ],
  },
  // ── Power ──
  {
    id: "qwen-2.5-14b", name: "Qwen 2.5 14B", family: "Alibaba",
    params: "14B", speed: "~25 tok/s", category: "power",
    tags: ["deep", "reasoning"], recommended: true,
    desc: "The thinking powerhouse. Alibaba\u2019s 14B model rivals GPT-4 on many benchmarks at a fraction of the size. Exceptional at reasoning, math, and complex multi-step tasks.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 70, spd: 50, sizeGB: 9.0, size: "9.0 GB" },
      { label: "Medium", bits: "6-bit", intel: 75, spd: 40, sizeGB: 11.4, size: "11.4 GB" },
      { label: "High", bits: "8-bit", intel: 80, spd: 30, sizeGB: 14.5, size: "14.5 GB" },
      { label: "Ultra", bits: "16-bit", intel: 85, spd: 18, sizeGB: 28, size: "28 GB" },
    ],
  },
  {
    id: "llama-3.1-70b", name: "Llama 3.1 70B", family: "Meta",
    params: "70B", speed: "~8 tok/s", category: "power",
    tags: ["frontier", "powerful"], recommended: false,
    desc: "Meta\u2019s flagship open model. 70 billion parameters of raw intelligence. Closest thing to GPT-4 you can run locally \u2014 if you have the VRAM. Slow but brilliant.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 90, spd: 18, sizeGB: 40, size: "40 GB" },
      { label: "Medium", bits: "6-bit", intel: 93, spd: 10, sizeGB: 55, size: "55 GB" },
    ],
  },
  {
    id: "command-r-35b", name: "Command R 35B", family: "Cohere",
    params: "35B", speed: "~15 tok/s", category: "power",
    tags: ["RAG", "enterprise"], recommended: false,
    desc: "Built by Cohere specifically for enterprise RAG workflows. Excels at grounded generation \u2014 citing sources accurately and following complex instructions in business contexts.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 78, spd: 30, sizeGB: 20, size: "20 GB" },
      { label: "Medium", bits: "6-bit", intel: 82, spd: 22, sizeGB: 27, size: "27 GB" },
      { label: "High", bits: "8-bit", intel: 85, spd: 15, sizeGB: 35, size: "35 GB" },
    ],
  },
  {
    id: "cloud-gpt4", name: "GPT-4o (Cloud)", family: "OpenAI",
    params: "~200B+", speed: "~60 tok/s", category: "power",
    tags: ["cloud", "best"], recommended: false,
    desc: "OpenAI\u2019s multimodal flagship. The gold standard in AI \u2014 handles text, vision, and audio. Requires an API key and internet connection. Unmatched quality, but data leaves your machine.",
    quants: [
      { label: "Cloud", bits: "API", intel: 98, spd: 85, sizeGB: 0, size: "0 GB" },
    ],
  },
  // ── Specialist ──
  {
    id: "qwen-2.5-coder-14b", name: "Qwen 2.5 Coder 14B", family: "Alibaba",
    params: "14B", speed: "~25 tok/s", category: "specialist",
    tags: ["code", "autocomplete"], recommended: true,
    desc: "Purpose-built for developers. Alibaba\u2019s coding specialist handles autocomplete, code review, debugging, and generation across 90+ languages. Top-tier on coding benchmarks.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 72, spd: 50, sizeGB: 9.0, size: "9.0 GB" },
      { label: "Medium", bits: "6-bit", intel: 78, spd: 40, sizeGB: 11.4, size: "11.4 GB" },
      { label: "High", bits: "8-bit", intel: 82, spd: 30, sizeGB: 14.5, size: "14.5 GB" },
    ],
  },
  {
    id: "deepseek-coder-v2", name: "DeepSeek Coder V2", family: "DeepSeek",
    params: "16B", speed: "~22 tok/s", category: "specialist",
    tags: ["code", "math", "reasoning"], recommended: false,
    desc: "DeepSeek\u2019s coding + math hybrid. Uses Mixture-of-Experts architecture for efficiency. Exceptional at mathematical reasoning and complex code generation. Strong open-source contender.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 75, spd: 45, sizeGB: 9.5, size: "9.5 GB" },
      { label: "Medium", bits: "6-bit", intel: 80, spd: 35, sizeGB: 12, size: "12 GB" },
      { label: "High", bits: "8-bit", intel: 85, spd: 25, sizeGB: 16, size: "16 GB" },
    ],
  },
];

const CATEGORIES = [
  { id: "speed" as const, img: "/hub/card_speed.png", label: "Speed", color: "#F59E0B", subtitle: "Fast responses, lighter models" },
  { id: "power" as const, img: "/hub/card_power.png", label: "Power", color: "#A78BFA", subtitle: "Deep intelligence, larger models" },
  { id: "specialist" as const, img: "/hub/card_specialist.png", label: "Specialist", color: "#34D399", subtitle: "Code, math, creative writing" },
];

const CAT_LABELS: Record<string, string> = { speed: "\u26A1 SPEED", power: "\uD83E\uDDE0 POWER", specialist: "\uD83D\uDD27 SPECIALIST" };

const MASCOT_MESSAGES: Record<string, string> = {
  categories: "Hey there! Pick a path that fits your style \u2728",
  models: "Click any model card to see the details! \u2605 means I recommend it \uD83E\uDD8A",
  detail: "Try different quality levels! Higher quality = smarter but slower \uD83E\uDDE0",
};

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
  const [search, setSearch] = useState("");
  const [detailModel, setDetailModel] = useState<number | null>(null);
  const [detailQuant, setDetailQuant] = useState(0);
  const [mascotText, setMascotText] = useState(MASCOT_MESSAGES.categories);

  const catColor = CATEGORIES.find(c => c.id === category)?.color || "#F59E0B";

  const filteredModels = useMemo(() => {
    let list = MODELS.filter(m => m.category === category);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(m =>
        m.name.toLowerCase().includes(q) ||
        m.family.toLowerCase().includes(q) ||
        m.tags.some(t => t.includes(q))
      );
    }
    return list;
  }, [category, search]);

  const pickCategory = (cat: typeof category) => {
    setCategory(cat);
    setScreen("models");
    setSearch("");
    setDetailModel(null);
    setMascotText(MASCOT_MESSAGES.models);
  };

  const openDetail = (idx: number) => {
    setDetailModel(idx);
    setDetailQuant(0);
    setMascotText(MASCOT_MESSAGES.detail);
  };

  const closeDetail = () => {
    setDetailModel(null);
    setMascotText(MASCOT_MESSAGES.models);
  };

  const confirmModel = (model: ModelDef, quant: QuantDef) => {
    const label = `${model.name} (${quant.bits})`;
    onSelect(model.id, label, quant.size, quant.bits);
  };

  // Reset mascot when returning to categories
  useEffect(() => {
    if (screen === "categories") setMascotText(MASCOT_MESSAGES.categories);
  }, [screen]);

  const detailModelData = detailModel !== null ? filteredModels[detailModel] : null;
  const detailQuantData = detailModelData ? detailModelData.quants[detailQuant] : null;

  return (
    <div className={`bs-root ${fullscreen ? "bs-fullscreen" : ""}`} style={{ "--cat-color": catColor } as React.CSSProperties}>
      <style>{css}</style>

      {/* ═══ SCREEN 1: CATEGORIES ═══ */}
      {screen === "categories" && (
        <div className="bs-categories">
          <h2 className="bs-title">Choose Your Path</h2>
          <p className="bs-sub">What matters most to you?</p>
          <div className="bs-cat-grid">
            {CATEGORIES.map((cat, i) => (
              <button
                key={cat.id}
                className={`bs-card bs-card-${cat.id}`}
                onClick={() => pickCategory(cat.id)}
                style={{ animationDelay: `${i * 0.12}s, ${i * 0.5}s` }}
              >
                <div className="bs-shimmer" />
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="bs-card-icon" src={cat.img} alt={cat.label} />
                <span className="bs-card-label">{cat.label}</span>
                <span className="bs-card-desc">{cat.subtitle}</span>
                <span className="bs-card-count">
                  {MODELS.filter(m => m.category === cat.id).length} MODELS
                </span>
              </button>
            ))}
          </div>
          <div className="bs-hint">Click a card to begin →</div>
          {onBack && (
            <button className="bs-back-link" onClick={onBack}>
              ← Back to recommended
            </button>
          )}
        </div>
      )}

      {/* ═══ SCREEN 2: MODEL GRID ═══ */}
      {screen === "models" && (
        <div className="bs-models">
          {/* Header */}
          <div className="bs-models-header">
            <button className="bs-s2-back" onClick={() => { setScreen("categories"); closeDetail(); }}>
              ← Back
            </button>
            <span className="bs-cat-badge" style={{ color: catColor, borderColor: catColor + "4D", background: catColor + "14" }}>
              {CAT_LABELS[category]}
            </span>
            {detectedVram > 0 && (
              <span className="bs-vram-badge">🖥 {detectedVram} GB VRAM</span>
            )}
          </div>

          {/* Search */}
          <div className="bs-search-wrap">
            <span className="bs-search-icon">🔍</span>
            <input
              className="bs-search"
              placeholder="Search models..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          {/* Model grid */}
          <div className="bs-model-grid">
            {filteredModels.length === 0 && (
              <p className="bs-empty">No models found. Try a different search.</p>
            )}
            {filteredModels.map((model, i) => {
              const defaultQ = model.quants[0];
              const overVram = defaultQ.sizeGB > detectedVram && detectedVram > 0 && defaultQ.bits !== "API";
              const isSelected = detailModel === i;
              return (
                <button
                  key={model.id}
                  className={`bs-model-card ${overVram ? "bs-dim-vram" : ""} ${isSelected ? "bs-selected" : ""}`}
                  onClick={() => openDetail(i)}
                  style={{ animationDelay: `${i * 0.07}s` }}
                >
                  {model.recommended && <div className="bs-rec-badge">★ Best Pick</div>}
                  <span className="bs-mc-name">{model.name}</span>
                  <span className="bs-mc-family">{model.family}</span>
                  <div className="bs-mc-badges">
                    <span className="bs-mc-badge">{model.params}</span>
                    <span className="bs-mc-badge">{model.speed}</span>
                  </div>
                  <div className="bs-mc-stats">
                    <div className="bs-mc-stat">
                      <span className="bs-mc-stat-label">🧠</span>
                      <div className="bs-mc-stat-bar"><div className="bs-mc-stat-fill bs-fill-intel" style={{ width: `${defaultQ.intel}%` }} /></div>
                    </div>
                    <div className="bs-mc-stat">
                      <span className="bs-mc-stat-label">⚡</span>
                      <div className="bs-mc-stat-bar"><div className="bs-mc-stat-fill bs-fill-speed" style={{ width: `${defaultQ.spd}%` }} /></div>
                    </div>
                    <div className="bs-mc-stat">
                      <span className="bs-mc-stat-label">💾</span>
                      <div className="bs-mc-stat-bar"><div className="bs-mc-stat-fill bs-fill-size" style={{ width: `${Math.min(100, defaultQ.sizeGB / 40 * 100)}%` }} /></div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══ DETAIL OVERLAY + SLIDE-OUT PANEL ═══ */}
      {detailModel !== null && detailModelData && detailQuantData && (
        <>
          <div className="bs-detail-overlay" onClick={closeDetail} />
          <div className="bs-detail-panel">
            <button className="bs-dp-close" onClick={closeDetail}>✕ Close</button>
            <div className="bs-dp-name">{detailModelData.name}</div>
            <div className="bs-dp-family">{detailModelData.family} · {detailModelData.params} · {detailModelData.speed}</div>
            <div className="bs-dp-tags">
              {detailModelData.tags.map(t => (
                <span key={t} className="bs-dp-tag">{t}</span>
              ))}
            </div>
            <div className="bs-dp-desc">{detailModelData.desc}</div>

            <div className="bs-dp-section-title">Quality</div>
            <div className="bs-dp-quant-pills">
              {detailModelData.quants.map((qo, j) => (
                <button
                  key={j}
                  className={`bs-dp-qpill ${j === detailQuant ? "bs-dp-qpill-active" : ""}`}
                  onClick={() => setDetailQuant(j)}
                >
                  <span>{qo.label}</span>
                  <span className="bs-dp-qpill-bits">{qo.bits}</span>
                </button>
              ))}
            </div>

            <div className="bs-dp-section-title">Stats</div>
            <div className="bs-dp-stats">
              <div className="bs-dp-stat-row">
                <span className="bs-dp-stat-icon">🧠</span>
                <span className="bs-dp-stat-name">Intelligence</span>
                <div className="bs-dp-stat-bar-bg"><div className="bs-dp-stat-fill bs-dp-intel" style={{ width: `${detailQuantData.intel}%` }} /></div>
                <span className="bs-dp-stat-value">{detailModelData.params}</span>
              </div>
              <div className="bs-dp-stat-row">
                <span className="bs-dp-stat-icon">⚡</span>
                <span className="bs-dp-stat-name">Speed</span>
                <div className="bs-dp-stat-bar-bg"><div className="bs-dp-stat-fill bs-dp-speed" style={{ width: `${detailQuantData.spd}%` }} /></div>
                <span className="bs-dp-stat-value">{detailModelData.speed}</span>
              </div>
              <div className="bs-dp-stat-row">
                <span className="bs-dp-stat-icon">💾</span>
                <span className="bs-dp-stat-name">Size</span>
                <div className="bs-dp-stat-bar-bg"><div className="bs-dp-stat-fill bs-dp-size" style={{ width: `${Math.min(100, detailQuantData.sizeGB / 40 * 100)}%` }} /></div>
                <span className="bs-dp-stat-value">{detailQuantData.size}</span>
              </div>
            </div>

            {/* VRAM warning */}
            {detectedVram > 0 && detailQuantData.sizeGB > detectedVram && detailQuantData.bits !== "API" && (
              <p className="bs-dp-vram-warn">
                ⚠ Needs ~{detailQuantData.sizeGB} GB VRAM (you have {detectedVram} GB)
              </p>
            )}

            <button className="bs-dp-select" onClick={() => confirmModel(detailModelData, detailQuantData)}>
              Select {detailModelData.name} · {detailQuantData.bits} →
            </button>
          </div>
        </>
      )}

      {/* ═══ MASCOT GUIDE ═══ */}
      <div className="bs-mascot">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="bs-mascot-img" src="/hub/mascot_fox.png" alt="Fox Guide" />
        <div className="bs-mascot-bubble">{mascotText}</div>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
// CSS — ported from design_preview.html
// ════════════════════════════════════════════════════════════════════

const css = `
  .bs-root {
    width: 100%; min-height: 100%;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    color: #F0DCC8;
    background: #060609;
    position: relative;
  }
  .bs-fullscreen {
    position: fixed; inset: 0; z-index: 100;
    background: #060609;
    overflow-y: auto;
  }

  /* ═══ SCREEN 1: CATEGORIES ═══ */
  .bs-categories {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 40px 24px; min-height: 100vh; width: 100%;
    animation: bsFadeUp 0.5s ease forwards;
  }
  @keyframes bsFadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .bs-title {
    font-size: 32px; font-weight: 900; margin: 0 0 6px;
    background: linear-gradient(135deg, #F0DCC8 0%, #FBBF24 50%, #D97706 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .bs-sub { font-size: 14px; color: #4A3D30; margin: 0 0 48px; }
  .bs-cat-grid {
    display: grid; grid-template-columns: repeat(3, 200px);
    gap: 28px;
  }
  .bs-hint {
    margin-top: 48px; font-size: 11px; color: #2A2520;
    letter-spacing: 1px; text-transform: uppercase;
    animation: bsFadeIn 1s 0.8s both;
  }
  @keyframes bsFadeIn { from { opacity: 0; } to { opacity: 1; } }
  .bs-back-link {
    margin-top: 16px;
    background: none; border: none; cursor: pointer;
    color: #5A4D40; font-size: 12px; font-family: inherit;
    transition: color 0.2s;
  }
  .bs-back-link:hover { color: #F0DCC8; }

  /* Card */
  .bs-card {
    position: relative; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 16px;
    padding: 48px 24px 40px; border-radius: 22px; aspect-ratio: 3 / 4;
    cursor: pointer; font-family: inherit;
    background: radial-gradient(ellipse at 50% 25%, var(--glow-soft) 0%, rgba(8,8,14,0.98) 55%);
    border: 2px solid var(--border-idle);
    box-shadow: 0 0 35px var(--shadow-outer), 0 0 15px var(--shadow-diffuse), inset 0 0 25px rgba(0,0,0,0.3);
    transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    animation: bsCardIn 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) both, bsBorderPulse 3s ease-in-out infinite alternate;
  }
  @keyframes bsCardIn { from { opacity: 0; transform: translateY(50px) scale(0.8); } to { opacity: 1; transform: translateY(0) scale(1); } }
  @keyframes bsBorderPulse { 0% { border-color: var(--border-idle); } 100% { border-color: var(--border-glow); box-shadow: 0 0 45px var(--shadow-outer), 0 0 20px var(--shadow-diffuse); } }

  .bs-card::before {
    content: ''; position: absolute; top: -30px; left: 50%; width: 220px; height: 220px;
    transform: translateX(-50%); border-radius: 50%;
    background: radial-gradient(circle, var(--glow-strong) 0%, var(--glow-mid) 35%, transparent 65%);
    z-index: -1; pointer-events: none; animation: bsOuterGlow 3.5s ease-in-out infinite alternate; opacity: 0.6;
  }
  @keyframes bsOuterGlow { 0% { opacity: 0.4; transform: translateX(-50%) scale(0.85); } 100% { opacity: 0.8; transform: translateX(-50%) scale(1.1); } }

  .bs-card:hover {
    transform: translateY(-12px) scale(1.06);
    border-color: var(--border-hover);
    box-shadow: 0 30px 80px var(--shadow-outer), 0 0 120px var(--shadow-diffuse), 0 0 40px var(--shadow-outer);
  }
  .bs-card:hover::before { opacity: 1; width: 280px; height: 280px; }
  .bs-card:hover .bs-card-icon { filter: drop-shadow(0 0 50px var(--glow-strong)); transform: translateY(-4px) scale(1.1); }

  .bs-shimmer { position: absolute; inset: 0; border-radius: 22px; overflow: hidden; pointer-events: none; }
  .bs-shimmer::after {
    content: ''; position: absolute; inset: -50% -50%;
    background: linear-gradient(105deg, transparent 30%, var(--shimmer-color) 50%, transparent 100%);
    animation: bsSweep 6s ease-in-out infinite;
  }
  @keyframes bsSweep { 0% { left: -100%; } 35%, 100% { left: 250%; } }

  .bs-card-icon {
    width: 140px; height: 140px; object-fit: contain;
    position: relative; z-index: 2;
    filter: drop-shadow(0 0 30px var(--glow-strong));
    animation: bsIconBreathe 5s ease-in-out infinite;
    mix-blend-mode: screen;
    -webkit-mask-image: radial-gradient(circle, white 35%, transparent 70%);
    mask-image: radial-gradient(circle, white 35%, transparent 70%);
  }
  @keyframes bsIconBreathe { 0%, 100% { transform: translateY(0) scale(1); } 50% { transform: translateY(-7px) scale(1.04); } }
  .bs-card-label {
    font-size: 18px; font-weight: 900; color: var(--accent);
    text-transform: uppercase; letter-spacing: 4px;
    position: relative; z-index: 2;
    text-shadow: 0 0 30px var(--glow-strong);
  }
  .bs-card-desc {
    font-size: 12px; color: #5A4D40; text-align: center; line-height: 1.5;
    position: relative; z-index: 2; max-width: 140px;
  }
  .bs-card-count {
    font-size: 9px; color: #3A3530; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.5px;
    position: relative; z-index: 2;
  }

  /* Card color variants */
  .bs-card-speed { --accent: #F59E0B; --glow-strong: rgba(245,158,11,0.25); --glow-mid: rgba(217,119,6,0.10); --glow-soft: rgba(245,158,11,0.06); --border-idle: rgba(245,158,11,0.30); --border-hover: rgba(245,158,11,0.85); --border-glow: rgba(245,158,11,0.55); --border-glow-dim: rgba(245,158,11,0.25); --shadow-outer: rgba(245,158,11,0.12); --shadow-diffuse: rgba(245,158,11,0.06); --shimmer-color: rgba(245,158,11,0.04); }
  .bs-card-power { --accent: #A78BFA; --glow-strong: rgba(167,139,250,0.25); --glow-mid: rgba(139,92,246,0.10); --glow-soft: rgba(167,139,250,0.06); --border-idle: rgba(167,139,250,0.30); --border-hover: rgba(167,139,250,0.85); --border-glow: rgba(167,139,250,0.55); --border-glow-dim: rgba(167,139,250,0.25); --shadow-outer: rgba(167,139,250,0.12); --shadow-diffuse: rgba(167,139,250,0.06); --shimmer-color: rgba(167,139,250,0.04); }
  .bs-card-specialist { --accent: #34D399; --glow-strong: rgba(52,211,153,0.25); --glow-mid: rgba(16,185,129,0.10); --glow-soft: rgba(52,211,153,0.06); --border-idle: rgba(52,211,153,0.30); --border-hover: rgba(52,211,153,0.85); --border-glow: rgba(52,211,153,0.55); --border-glow-dim: rgba(52,211,153,0.25); --shadow-outer: rgba(52,211,153,0.12); --shadow-diffuse: rgba(52,211,153,0.06); --shimmer-color: rgba(52,211,153,0.04); }

  /* ═══ SCREEN 2: MODEL GRID ═══ */
  .bs-models {
    width: 100%; max-width: 960px;
    min-height: 100vh; padding: 28px 24px;
    margin: 0 auto;
    animation: bsFadeUp 0.4s ease forwards;
  }
  .bs-models-header {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 20px;
  }
  .bs-s2-back {
    padding: 8px 16px; border-radius: 10px;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    color: #8A7A6A; font-size: 13px; font-weight: 600;
    cursor: pointer; font-family: inherit; transition: all 0.3s;
  }
  .bs-s2-back:hover { background: rgba(255,255,255,0.08); color: #F0DCC8; }
  .bs-cat-badge {
    padding: 6px 16px; border-radius: 8px;
    font-size: 12px; font-weight: 800;
    text-transform: uppercase; letter-spacing: 2px;
    border: 1px solid;
  }
  .bs-vram-badge {
    margin-left: auto; padding: 6px 14px; border-radius: 8px;
    font-size: 11px; color: #6A5A4A; font-weight: 600;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  }

  /* Search */
  .bs-search-wrap { position: relative; margin-bottom: 16px; }
  .bs-search-icon {
    position: absolute; left: 18px; top: 50%; transform: translateY(-50%);
    font-size: 16px; pointer-events: none; opacity: 0.6;
  }
  .bs-search {
    width: 100%; padding: 16px 20px 16px 48px; border-radius: 16px;
    border: 1.5px solid rgba(245,158,11,0.12);
    background: rgba(245,158,11,0.03);
    color: #F0DCC8; font-size: 15px; font-family: inherit; outline: none;
    transition: all 0.3s; box-shadow: 0 0 20px rgba(245,158,11,0.04);
  }
  .bs-search:focus {
    border-color: color-mix(in srgb, var(--cat-color) 50%, transparent);
    box-shadow: 0 0 40px color-mix(in srgb, var(--cat-color) 12%, transparent);
    background: rgba(245,158,11,0.05);
  }
  .bs-search::placeholder { color: #4A3D30; font-weight: 500; }

  /* Model grid */
  .bs-model-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
  }
  .bs-empty { color: #3A3530; text-align: center; font-size: 13px; padding: 40px 0; grid-column: 1/-1; }

  .bs-model-card {
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015));
    border: 1.5px solid rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
    padding: 20px; cursor: pointer; font-family: inherit;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    animation: bsCardSlide 0.4s ease both;
    display: flex; flex-direction: column; gap: 12px;
    position: relative; text-align: left; color: inherit;
  }
  @keyframes bsCardSlide { from { opacity: 0; transform: translateY(20px) scale(0.95); } to { opacity: 1; transform: translateY(0) scale(1); } }
  .bs-model-card:hover {
    transform: translateY(-6px) scale(1.02);
    border-color: color-mix(in srgb, var(--cat-color) 35%, transparent);
    box-shadow: 0 12px 40px color-mix(in srgb, var(--cat-color) 8%, transparent), 0 0 20px color-mix(in srgb, var(--cat-color) 5%, transparent);
  }
  .bs-selected {
    border-color: color-mix(in srgb, var(--cat-color) 50%, transparent);
    box-shadow: 0 0 30px color-mix(in srgb, var(--cat-color) 12%, transparent);
  }
  .bs-dim-vram { opacity: 0.35; pointer-events: none; }

  .bs-rec-badge {
    position: absolute; top: -6px; right: -6px;
    padding: 3px 10px; border-radius: 8px;
    font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A;
    box-shadow: 0 2px 12px rgba(245,158,11,0.4);
    animation: bsRecPulse 2s ease-in-out infinite alternate;
  }
  @keyframes bsRecPulse { 0% { box-shadow: 0 2px 12px rgba(245,158,11,0.3); } 100% { box-shadow: 0 4px 20px rgba(245,158,11,0.6); } }

  .bs-mc-name { font-size: 15px; font-weight: 700; }
  .bs-mc-family { font-size: 11px; color: #5A4D40; }
  .bs-mc-badges { display: flex; gap: 6px; margin-top: 2px; }
  .bs-mc-badge {
    padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: 700;
    color: #6A5A4A; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06);
  }
  .bs-mc-stats { display: flex; flex-direction: column; gap: 6px; margin-top: auto; }
  .bs-mc-stat { display: flex; align-items: center; gap: 6px; }
  .bs-mc-stat-label { font-size: 9px; font-weight: 700; color: #4A3D30; width: 16px; text-align: center; }
  .bs-mc-stat-bar { flex: 1; height: 5px; border-radius: 3px; background: rgba(255,255,255,0.04); overflow: hidden; }
  .bs-mc-stat-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
  .bs-fill-intel { background: linear-gradient(90deg, #DB2777, #F472B6); }
  .bs-fill-speed { background: linear-gradient(90deg, #10B981, #34D399); }
  .bs-fill-size { background: linear-gradient(90deg, #3B82F6, #60A5FA); }

  /* ═══ DETAIL PANEL ═══ */
  .bs-detail-overlay {
    position: fixed; inset: 0; z-index: 50;
    background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);
    animation: bsFadeIn 0.2s ease;
  }
  .bs-detail-panel {
    position: fixed; top: 0; right: 0; bottom: 0; z-index: 51;
    width: 400px;
    background: linear-gradient(180deg, #0C0C14 0%, #080810 100%);
    border-left: 1.5px solid rgba(255,255,255,0.08);
    box-shadow: -20px 0 60px rgba(0,0,0,0.5);
    padding: 28px 24px; overflow-y: auto;
    animation: bsSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes bsSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }

  .bs-dp-close {
    position: absolute; top: 16px; right: 16px;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 6px 12px; color: #6A5A4A;
    font-size: 12px; cursor: pointer; font-family: inherit; transition: all 0.2s;
  }
  .bs-dp-close:hover { background: rgba(255,255,255,0.1); color: #F0DCC8; }

  .bs-dp-name { font-size: 22px; font-weight: 800; margin-bottom: 4px; }
  .bs-dp-family { font-size: 13px; color: #5A4D40; margin-bottom: 16px; }
  .bs-dp-tags { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
  .bs-dp-tag {
    padding: 4px 12px; border-radius: 6px; font-size: 10px;
    font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
    color: var(--cat-color);
    background: color-mix(in srgb, var(--cat-color) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--cat-color) 15%, transparent);
  }
  .bs-dp-desc {
    font-size: 13px; color: #8A7A6A; line-height: 1.7; margin-bottom: 20px;
    padding: 14px 16px; border-radius: 12px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
  }
  .bs-dp-section-title {
    font-size: 10px; font-weight: 700; color: #5A4D40;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;
  }
  .bs-dp-quant-pills { display: flex; gap: 6px; margin-bottom: 24px; }
  .bs-dp-qpill {
    flex: 1; padding: 10px 8px; border-radius: 12px; cursor: pointer;
    background: rgba(255,255,255,0.03); border: 1.5px solid rgba(255,255,255,0.08);
    color: #6A5A4A; font-family: inherit; font-size: 13px; font-weight: 700;
    display: flex; flex-direction: column; align-items: center; gap: 3px; transition: all 0.3s;
  }
  .bs-dp-qpill:hover { background: rgba(255,255,255,0.06); border-color: color-mix(in srgb, var(--cat-color) 30%, transparent); }
  .bs-dp-qpill-active {
    background: color-mix(in srgb, var(--cat-color) 15%, transparent);
    border-color: var(--cat-color); color: var(--cat-color);
    box-shadow: 0 0 25px color-mix(in srgb, var(--cat-color) 15%, transparent);
  }
  .bs-dp-qpill-bits { font-size: 10px; font-weight: 600; opacity: 0.5; }

  .bs-dp-stats { display: flex; flex-direction: column; gap: 14px; margin-bottom: 24px; }
  .bs-dp-stat-row { display: flex; align-items: center; gap: 10px; }
  .bs-dp-stat-icon { font-size: 15px; width: 22px; text-align: center; filter: saturate(1.4); }
  .bs-dp-stat-name { font-size: 11px; font-weight: 700; color: #6A5A4A; text-transform: uppercase; width: 85px; letter-spacing: 0.5px; }
  .bs-dp-stat-bar-bg {
    flex: 1; height: 12px; border-radius: 6px;
    background: rgba(255,255,255,0.04); overflow: hidden;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.4);
  }
  .bs-dp-stat-fill {
    height: 100%; border-radius: 6px; position: relative; overflow: hidden;
    transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .bs-dp-stat-fill::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 50%;
    border-radius: 6px 6px 0 0;
    background: linear-gradient(180deg, rgba(255,255,255,0.3), transparent);
  }
  .bs-dp-stat-fill::after {
    content: ''; position: absolute; top: 0; left: -100%; width: 60%; height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    animation: bsBarShine 3s ease-in-out infinite;
  }
  @keyframes bsBarShine { 0% { left: -100%; } 50%, 100% { left: 200%; } }
  .bs-dp-intel { background: linear-gradient(90deg, #9D174D, #DB2777, #EC4899, #F472B6); box-shadow: 0 0 12px rgba(236,72,153,0.35); }
  .bs-dp-speed { background: linear-gradient(90deg, #047857, #059669, #10B981, #34D399); box-shadow: 0 0 12px rgba(16,185,129,0.35); }
  .bs-dp-size { background: linear-gradient(90deg, #1D4ED8, #2563EB, #3B82F6, #60A5FA); box-shadow: 0 0 12px rgba(59,130,246,0.35); }
  .bs-dp-stat-value { font-size: 11px; color: #6A5A4A; width: 65px; text-align: right; font-weight: 700; }

  .bs-dp-vram-warn {
    font-size: 11px; color: #EF4444; font-weight: 600;
    margin: 0 0 12px; padding: 8px 12px; border-radius: 8px;
    background: rgba(239,68,68,0.06); border: 1px solid rgba(239,68,68,0.15);
  }

  .bs-dp-select {
    width: 100%; padding: 16px; border-radius: 14px; border: none;
    cursor: pointer; font-family: inherit; font-size: 15px; font-weight: 800;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; box-shadow: 0 4px 24px rgba(245,158,11,0.25);
    transition: all 0.3s;
  }
  .bs-dp-select:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(245,158,11,0.4); }

  /* ═══ MASCOT ═══ */
  .bs-mascot {
    position: fixed; bottom: 16px; left: 20px; z-index: 40;
    display: flex; align-items: flex-end; gap: 0;
    pointer-events: none;
  }
  .bs-mascot-img {
    width: 180px; height: 180px; object-fit: contain;
    filter: drop-shadow(0 4px 30px rgba(245,158,11,0.4));
    animation: bsMascotBob 4s ease-in-out infinite;
    mix-blend-mode: screen;
    -webkit-mask-image: radial-gradient(circle, white 30%, transparent 60%);
    mask-image: radial-gradient(circle, white 30%, transparent 60%);
  }
  @keyframes bsMascotBob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
  .bs-mascot-bubble {
    position: relative; bottom: 50px;
    background: rgba(20,18,28,0.92); border: 1.5px solid rgba(245,158,11,0.20);
    border-radius: 14px 14px 14px 4px;
    padding: 10px 14px; max-width: 220px;
    font-size: 12px; color: #C4A882; line-height: 1.5;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    pointer-events: auto;
  }

  /* ═══ Responsive ═══ */
  @media (max-width: 700px) {
    .bs-cat-grid { grid-template-columns: 1fr; max-width: 240px; }
    .bs-model-grid { grid-template-columns: 1fr; }
    .bs-detail-panel { width: 100%; }
    .bs-mascot { display: none; }
  }
`;

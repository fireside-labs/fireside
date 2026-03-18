"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { useToast } from "@/components/Toast";
import { browsePlugins, installPlugin, uninstallPlugin, API_BASE } from "@/lib/api";
import { DiscoveryCard } from "@/components/GuidedTour";

/* ═══════════════════════════════════════════════════════════════════
   Skills Marketplace — RPG-style skill shop
   Two tabs: Equipped (installed) · Marketplace (browse + install)
   Category filtering, rarity tiers, power levels
   ═══════════════════════════════════════════════════════════════════ */

interface SkillPlugin {
  name: string;
  version: string;
  description: string;
  author: string;
  category: string;
  rarity: string;
  installed: boolean;
  routes?: { method: string; path: string }[];
  tags?: string[];
}

// ── User-friendly display names ──
const SKILL_DISPLAY: Record<string, { icon: string; label: string; color: string }> = {
  "adaptive-thinking": { icon: "💭", label: "Deep Thinking", color: "#60A5FA" },
  "agent_profiles": { icon: "👤", label: "Agent Profiles", color: "#6A5A4A" },
  "alerts": { icon: "🔔", label: "Smart Alerts", color: "#FBBF24" },
  "belief-shadows": { icon: "🌑", label: "Belief Shadows", color: "#A78BFA" },
  "brain-installer": { icon: "🧪", label: "Brain Installer", color: "#6A5A4A" },
  "browse": { icon: "🌐", label: "Web Browsing", color: "#38BDF8" },
  "companion": { icon: "🦊", label: "Companion Core", color: "#F59E0B" },
  "consumer-api": { icon: "🔌", label: "Consumer API", color: "#6A5A4A" },
  "context-compactor": { icon: "📦", label: "Context Compactor", color: "#34D399" },
  "crucible": { icon: "🔥", label: "The Crucible", color: "#EF4444" },
  "event-bus": { icon: "📡", label: "Event Bus", color: "#6A5A4A" },
  "hydra": { icon: "🐙", label: "Hydra Resilience", color: "#F472B6" },
  "hypotheses": { icon: "💡", label: "Hypothesis Engine", color: "#FBBF24" },
  "marketplace": { icon: "🏪", label: "Marketplace", color: "#6A5A4A" },
  "model-router": { icon: "🔀", label: "Smart Router", color: "#60A5FA" },
  "model-switch": { icon: "🔄", label: "Model Switch", color: "#38BDF8" },
  "payments": { icon: "💳", label: "Payments", color: "#6A5A4A" },
  "personality": { icon: "💫", label: "Soul Evolution", color: "#F59E0B" },
  "philosopher-stone": { icon: "📜", label: "Philosopher's Stone", color: "#FBBF24" },
  "pipeline": { icon: "⚡", label: "Task Pipeline", color: "#F97316" },
  "predictions": { icon: "🔮", label: "Predictions", color: "#A78BFA" },
  "self-model": { icon: "🪞", label: "Self-Awareness", color: "#34D399" },
  "socratic": { icon: "🗣️", label: "Socratic Debate", color: "#A78BFA" },
  "task-persistence": { icon: "💾", label: "Task Persistence", color: "#60A5FA" },
  "telegram": { icon: "✈️", label: "Telegram Bot", color: "#818CF8" },
  "terminal": { icon: "💻", label: "Terminal Access", color: "#22D3EE" },
  "voice": { icon: "🎙️", label: "Voice Mode", color: "#F472B6" },
  "watchdog": { icon: "🐕", label: "Watchdog", color: "#34D399" },
  "working-memory": { icon: "🧠", label: "Working Memory", color: "#A78BFA" },
};

const CATEGORIES = [
  { id: "all", label: "All", icon: "✦" },
  { id: "intelligence", label: "Intelligence", icon: "⚔️" },
  { id: "communication", label: "Communication", icon: "💬" },
  { id: "automation", label: "Automation", icon: "🔧" },
  { id: "connectivity", label: "Connectivity", icon: "🌐" },
  { id: "memory", label: "Memory", icon: "🧠" },
];

const RARITY_CONFIG: Record<string, { label: string; color: string; bg: string; glow: string }> = {
  legendary: { label: "Legendary", color: "#F59E0B", bg: "rgba(245,158,11,0.08)", glow: "0 0 20px rgba(245,158,11,0.15)" },
  rare: { label: "Rare", color: "#A78BFA", bg: "rgba(167,139,250,0.08)", glow: "0 0 16px rgba(167,139,250,0.1)" },
  uncommon: { label: "Uncommon", color: "#34D399", bg: "rgba(52,211,153,0.08)", glow: "0 0 12px rgba(52,211,153,0.08)" },
  common: { label: "Common", color: "#6A5A4A", bg: "rgba(106,90,74,0.08)", glow: "none" },
};

// Infrastructure plugins — hidden from UI entirely
const HIDDEN_PLUGINS = new Set([
  "event-bus", "marketplace", "payments", "consumer-api", "brain-installer", "agent_profiles",
]);

// Core experience plugins — always on, toggle locked
const CORE_PLUGINS = new Set([
  "working-memory", "personality", "self-model", "adaptive-thinking", "companion",
]);

const POWER_MAP: Record<string, number> = {
  legendary: 25, rare: 15, uncommon: 8, common: 5,
};

// Full plugin list — used when backend is offline (no platform plugins)
const ALL_PLUGINS: SkillPlugin[] = [
  { name: "adaptive-thinking", version: "1.0.0", description: "Breaks hard questions into smaller steps before answering. Takes longer but gets tricky problems right.", author: "valhalla-core", category: "intelligence", rarity: "rare", installed: true },
  { name: "alerts", version: "1.0.0", description: "Your AI pings you when something needs attention — like a reminder or a finished task. Works via dashboard and Telegram.", author: "valhalla-core", category: "communication", rarity: "common", installed: false },
  { name: "belief-shadows", version: "1.0.0", description: "Flags when your AI isn't sure about something instead of guessing. Shows confidence levels on answers.", author: "valhalla-core", category: "intelligence", rarity: "legendary", installed: false },
  { name: "browse", version: "1.0.0", description: "Lets your AI read any webpage, search the web, and pull current information. All done locally.", author: "valhalla-core", category: "connectivity", rarity: "common", installed: true },
  { name: "companion", version: "1.0.0", description: "The core companion system — your AI's personality, mood, and chat. This is what makes your companion feel alive.", author: "valhalla-core", category: "communication", rarity: "rare", installed: true },
  { name: "context-compactor", version: "1.0.0", description: "Compresses long conversations so your AI remembers more without slowing down. Great for deep research sessions.", author: "valhalla-core", category: "memory", rarity: "rare", installed: false },
  { name: "crucible", version: "1.0.0", description: "Stress-tests your AI overnight — finds bad habits and fixes them. Like a sparring partner that makes it sharper.", author: "valhalla-core", category: "automation", rarity: "legendary", installed: false },
  { name: "hydra", version: "1.0.0", description: "If one of your devices goes offline, another picks up the work automatically. Keeps your mesh running 24/7.", author: "valhalla-core", category: "connectivity", rarity: "legendary", installed: false },
  { name: "hypotheses", version: "1.0.0", description: "Your AI generates theories while you sleep, based on what it has learned. Surfaces insights you didn't ask for.", author: "valhalla-core", category: "intelligence", rarity: "legendary", installed: false },
  { name: "model-router", version: "1.0.0", description: "Automatically picks the best AI model for each task — fast model for chat, smart model for research.", author: "valhalla-core", category: "connectivity", rarity: "rare", installed: false },
  { name: "model-switch", version: "1.0.0", description: "Switch between AI models mid-conversation. Type 'use gpt4' or 'use local' to change on the fly.", author: "valhalla-core", category: "connectivity", rarity: "common", installed: true },
  { name: "personality", version: "1.0.0", description: "Your companion develops unique personality traits over time based on how you interact. No two are alike.", author: "valhalla-core", category: "memory", rarity: "rare", installed: true },
  { name: "philosopher-stone", version: "1.0.0", description: "Runs nightly — distills everything your AI learned into a concentrated wisdom prompt. Makes it smarter each day.", author: "valhalla-core", category: "intelligence", rarity: "legendary", installed: false },
  { name: "pipeline", version: "1.0.0", description: "Run multi-step tasks like 'research competitors then write a report'. Chains steps together automatically.", author: "valhalla-core", category: "automation", rarity: "rare", installed: true },
  { name: "predictions", version: "1.0.0", description: "Learns your patterns and starts preparing answers before you ask. Gets faster the more you use it.", author: "valhalla-core", category: "intelligence", rarity: "rare", installed: false },
  { name: "self-model", version: "1.0.0", description: "Your AI tracks what it's good and bad at, and adjusts. If it keeps getting math wrong, it slows down on math.", author: "valhalla-core", category: "intelligence", rarity: "legendary", installed: true },
  { name: "socratic", version: "1.0.0", description: "Before giving an answer, your AI debates itself from multiple angles. Catches mistakes before you see them.", author: "valhalla-core", category: "automation", rarity: "legendary", installed: false },
  { name: "task-persistence", version: "1.0.0", description: "If your computer crashes mid-task, it picks up exactly where it left off. No lost work.", author: "valhalla-core", category: "automation", rarity: "rare", installed: false },
  { name: "telegram", version: "1.0.0", description: "Chat with your AI from Telegram. Ask questions, get alerts, run commands — all from your phone.", author: "valhalla-core", category: "communication", rarity: "uncommon", installed: false },
  { name: "terminal", version: "1.0.0", description: "Lets your AI run commands on your computer — create files, install software, run scripts. Always asks permission first.", author: "valhalla-core", category: "automation", rarity: "rare", installed: false },
  { name: "voice", version: "1.0.0", description: "Talk to your AI and hear it talk back. Uses Whisper for listening and Kokoro for speaking — all local, no cloud.", author: "valhalla-core", category: "communication", rarity: "rare", installed: false },
  { name: "watchdog", version: "1.0.0", description: "Monitors all your connected devices and alerts you if something goes down. Auto-restarts crashed services.", author: "valhalla-core", category: "connectivity", rarity: "uncommon", installed: true },
  { name: "working-memory", version: "1.0.0", description: "Remembers your past conversations, preferences, and context. The more you chat, the better it knows you.", author: "valhalla-core", category: "memory", rarity: "rare", installed: true },
];

export default function SkillsPage() {
  const { toast } = useToast();
  const [tab, setTab] = useState<"equipped" | "marketplace">("equipped");
  const [activeCategory, setActiveCategory] = useState("all");
  const [allPlugins, setAllPlugins] = useState<SkillPlugin[]>(ALL_PLUGINS);
  const [loading, setLoading] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);

  // Try to fetch live data from API (overrides fallback if backend is online)
  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(API_BASE + "/api/v1/plugins/browse");
        if (res.ok) {
          const data = await res.json();
          if (data.plugins && data.plugins.length > 0) {
            // Filter out hidden infrastructure plugins from API results too
            setAllPlugins(data.plugins.filter((p: SkillPlugin) => !HIDDEN_PLUGINS.has(p.name)));
          }
        }
      } catch {
        // Backend offline — use fallback (already set as initial state)
      }
    }
    load();
  }, []);

  const equipped = useMemo(() => allPlugins.filter(p => p.installed), [allPlugins]);
  const available = useMemo(() => {
    let list = allPlugins;
    if (tab === "marketplace" && activeCategory !== "all") {
      list = list.filter(p => p.category === activeCategory);
    }
    return list;
  }, [allPlugins, tab, activeCategory]);

  // Power level
  const powerXP = useMemo(() => {
    return equipped.reduce((sum, p) => sum + (POWER_MAP[p.rarity] || 5) * 50, 0);
  }, [equipped]);
  const powerTier = powerXP >= 4000 ? "🌟 Ascended" : powerXP >= 3000 ? "🔥 Mythic" : powerXP >= 2000 ? "⚡ Legendary" : powerXP >= 1000 ? "💪 Strong" : powerXP >= 500 ? "🌿 Solid" : "🌱 Basic";
  const powerColor = powerXP >= 4000 ? "#FBBF24" : powerXP >= 3000 ? "#F59E0B" : powerXP >= 2000 ? "#A78BFA" : powerXP >= 1000 ? "#60A5FA" : powerXP >= 500 ? "#34D399" : "#5A4D40";
  const tierSize = 500;
  const tierProgress = ((powerXP % tierSize) / tierSize) * 100;

  const togglePlugin = async (name: string) => {
    const plugin = allPlugins.find(p => p.name === name);
    if (!plugin || CORE_PLUGINS.has(name)) return;

    const display = SKILL_DISPLAY[name]?.label || name;
    setToggling(name);

    try {
      if (plugin.installed) {
        await uninstallPlugin(name);
        toast(`${display} disabled`, "success");
      } else {
        await installPlugin(name);
        toast(`${display} enabled — restart to activate`, "success");
      }
      setAllPlugins(prev =>
        prev.map(p => p.name === name ? { ...p, installed: !p.installed } : p)
      );
    } catch {
      toast(`Failed to toggle ${display}`, "error");
    }
    setToggling(null);
  };

  return (
    <div className="sk-root">
      <style>{css}</style>

      <div className="sk-topbar">
        <Link href="/" className="sk-back-link">🔥 Hub</Link>
        <span className="sk-topbar-title">Skills</span>
      </div>

      <DiscoveryCard pageKey="/skills" />

      <h1 className="sk-page-title">✦ Skills Marketplace</h1>
      <p className="sk-page-sub">Equip your AI with abilities. Toggle skills on and off anytime.</p>

      {/* Skills count summary — clean, no XP */}
      <div className="sk-power-card">
        <div className="sk-power-header">
          <span className="sk-power-label">{equipped.length} skills active</span>
          <span style={{ fontSize: 11, color: '#5A4D40' }}>{allPlugins.length} available</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="sk-tabs">
        <button className={`sk-tab ${tab === "equipped" ? "active" : ""}`} onClick={() => setTab("equipped")}>
          ⚔️ Equipped <span className="sk-tab-count">{equipped.length}</span>
        </button>
        <button className={`sk-tab ${tab === "marketplace" ? "active" : ""}`} onClick={() => setTab("marketplace")}>
          🛒 Marketplace <span className="sk-tab-count">{allPlugins.length}</span>
        </button>
      </div>

      {/* Category filters (marketplace only) */}
      {tab === "marketplace" && (
        <div className="sk-filters">
          {CATEGORIES.map(c => (
            <button
              key={c.id}
              className={`sk-filter ${activeCategory === c.id ? "active" : ""}`}
              onClick={() => setActiveCategory(c.id)}
            >
              {c.icon} {c.label}
            </button>
          ))}
        </div>
      )}

      {/* Skills Grid */}
      {loading ? (
        <div className="sk-loading">Loading skills...</div>
      ) : (
        <div className="sk-list">
          {(tab === "equipped" ? equipped : available).length === 0 && (
            <div className="sk-empty">
              {tab === "equipped" ? "No skills equipped yet. Browse the marketplace to add some!" : "No skills in this category."}
            </div>
          )}
          {(tab === "equipped" ? equipped : available).map((plugin, i) => {
            const display = SKILL_DISPLAY[plugin.name] || { icon: "⚙️", label: plugin.name, color: "#6A5A4A" };
            const rConf = RARITY_CONFIG[plugin.rarity] || RARITY_CONFIG.common;
            const isRequired = CORE_PLUGINS.has(plugin.name);
            const isToggling = toggling === plugin.name;
            const catInfo = CATEGORIES.find(c => c.id === plugin.category);

            return (
              <div
                key={plugin.name}
                className={`sk-card ${plugin.rarity}`}
                style={{
                  "--sk-color": display.color,
                  "--sk-rarity": rConf.color,
                  animationDelay: `${i * 0.04}s`,
                } as React.CSSProperties}
              >
                <div className="sk-card-left">
                  <span className="sk-icon">{display.icon}</span>
                  <div className="sk-info">
                    <div className="sk-name-row">
                      <span className="sk-name">{display.label}</span>
                      <span className="sk-version">v{plugin.version}</span>
                      <span className="sk-rarity-tag" style={{ color: rConf.color, background: rConf.bg }}>{rConf.label}</span>
                    </div>
                    <div className="sk-desc">{plugin.description}</div>
                    <div className="sk-meta-row">
                      {catInfo && <span className="sk-cat-tag">{catInfo.icon} {catInfo.label}</span>}
                      {plugin.routes && <span className="sk-route-count">{plugin.routes.length} endpoints</span>}
                      {isRequired && <span className="sk-required-tag">REQUIRED</span>}
                    </div>
                  </div>
                </div>
                <button
                  className={`sk-toggle ${plugin.installed ? "sk-on" : "sk-off"} ${isRequired ? "sk-locked" : ""} ${isToggling ? "sk-toggling" : ""}`}
                  onClick={() => !isRequired && togglePlugin(plugin.name)}
                  disabled={isRequired || isToggling}
                  title={isRequired ? "System plugin — always active" : plugin.installed ? "Disable skill" : "Enable skill"}
                >
                  {isRequired ? (
                    <span className="sk-lock-icon">🔒</span>
                  ) : (
                    <span className="sk-toggle-knob" />
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&display=swap');

  .sk-root {
    max-width: 720px; margin: 0 auto; padding: 20px 28px 60px;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    color: #F0DCC8; min-height: 100vh;
  }

  .sk-topbar {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 0; margin-bottom: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
  }
  .sk-back-link {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 16px; border-radius: 10px;
    font-size: 13px; font-weight: 800; color: #C4A882;
    text-decoration: none; transition: all 0.2s;
    background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.12);
    font-family: 'Outfit', system-ui;
  }
  .sk-back-link:hover { background: rgba(245,158,11,0.12); color: #F59E0B; border-color: rgba(245,158,11,0.25); }
  .sk-topbar-title { font-size: 12px; color: #3A3530; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }

  .sk-page-title {
    font-size: 28px; font-weight: 900; margin: 0 0 6px;
    background: linear-gradient(135deg, #F0DCC8, #FBBF24);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-family: 'Outfit';
  }
  .sk-page-sub { font-size: 14px; color: #5A4D40; margin-bottom: 20px; }

  /* Power Level */
  .sk-power-card {
    padding: 20px 24px; border-radius: 18px; margin-bottom: 24px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  }
  .sk-power-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .sk-power-label { font-size: 14px; font-weight: 800; color: #F0DCC8; }
  .sk-power-value { font-size: 13px; font-weight: 700; }
  .sk-power-bar { width: 100%; height: 8px; border-radius: 4px; background: rgba(255,255,255,0.04); overflow: hidden; }
  .sk-power-fill {
    height: 100%; border-radius: 4px;
    transition: width 0.5s cubic-bezier(0.16, 1, 0.3, 1), background 0.5s;
    box-shadow: 0 0 12px rgba(245,158,11,0.15);
  }
  .sk-power-stats { display: flex; justify-content: space-between; margin-top: 8px; font-size: 10px; color: #4A3D30; font-weight: 600; }

  /* Tabs */
  .sk-tabs { display: flex; gap: 4px; margin-bottom: 16px; }
  .sk-tab {
    flex: 1; padding: 12px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.04);
    background: rgba(255,255,255,0.02); color: #6A5A4A; font-size: 13px; font-weight: 700;
    cursor: pointer; font-family: 'Outfit'; transition: all 0.2s;
    display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  .sk-tab:hover { background: rgba(255,255,255,0.04); color: #C4A882; }
  .sk-tab.active {
    background: rgba(245,158,11,0.06); border-color: rgba(245,158,11,0.15);
    color: #F0DCC8; box-shadow: 0 0 16px rgba(245,158,11,0.04);
  }
  .sk-tab-count {
    font-size: 10px; font-weight: 800; padding: 2px 7px; border-radius: 6px;
    background: rgba(255,255,255,0.06); color: #5A4D40;
  }
  .sk-tab.active .sk-tab-count { background: rgba(245,158,11,0.1); color: #F59E0B; }

  /* Category Filters */
  .sk-filters {
    display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px;
    animation: skFadeIn 0.3s ease;
  }
  @keyframes skFadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
  .sk-filter {
    padding: 6px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.04);
    background: rgba(255,255,255,0.02); color: #5A4D40; font-size: 11px; font-weight: 700;
    cursor: pointer; font-family: 'Outfit'; transition: all 0.2s;
  }
  .sk-filter:hover { background: rgba(255,255,255,0.04); color: #C4A882; }
  .sk-filter.active {
    background: rgba(245,158,11,0.06); border-color: rgba(245,158,11,0.12);
    color: #F59E0B;
  }

  /* Skill Cards */
  .sk-list { display: flex; flex-direction: column; gap: 8px; }
  .sk-loading { text-align: center; padding: 40px; color: #4A3D30; font-size: 13px; }
  .sk-empty { text-align: center; padding: 40px; color: #3A3530; font-size: 13px; border: 1px dashed rgba(255,255,255,0.06); border-radius: 14px; }

  .sk-card {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 20px; border-radius: 16px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);
    transition: all 0.3s;
    animation: skCardIn 0.3s ease both;
  }
  @keyframes skCardIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
  .sk-card:hover { background: rgba(255,255,255,0.04); border-color: color-mix(in srgb, var(--sk-color) 15%, transparent); }
  .sk-card.legendary { border-color: rgba(245,158,11,0.08); box-shadow: 0 0 20px rgba(245,158,11,0.04); }
  .sk-card.legendary:hover { border-color: rgba(245,158,11,0.15); box-shadow: 0 0 28px rgba(245,158,11,0.08); }

  .sk-card-left { display: flex; align-items: flex-start; gap: 14px; flex: 1; min-width: 0; }
  .sk-icon { font-size: 26px; flex-shrink: 0; margin-top: 2px; filter: drop-shadow(0 0 6px color-mix(in srgb, var(--sk-color) 30%, transparent)); }
  .sk-info { flex: 1; min-width: 0; }
  .sk-name-row { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; flex-wrap: wrap; }
  .sk-name { font-size: 14px; font-weight: 700; color: var(--sk-color); }
  .sk-version { font-size: 9px; color: #3A3530; font-weight: 600; }
  .sk-rarity-tag {
    font-size: 8px; font-weight: 800; padding: 1px 6px; border-radius: 4px;
    text-transform: uppercase; letter-spacing: 0.5px; flex-shrink: 0;
  }
  .sk-desc { font-size: 12px; color: #6A5A4A; line-height: 1.5; margin-bottom: 4px; }

  .sk-meta-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .sk-cat-tag {
    font-size: 9px; color: #4A3D30; font-weight: 600;
    padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.03);
  }
  .sk-route-count { font-size: 9px; color: #3A3530; font-weight: 500; }
  .sk-required-tag {
    font-size: 8px; font-weight: 900; color: #F59E0B; letter-spacing: 0.5px;
    padding: 1px 6px; border-radius: 4px; background: rgba(245,158,11,0.06);
  }

  /* Toggle */
  .sk-toggle {
    width: 48px; height: 26px; border-radius: 13px; border: none;
    cursor: pointer; flex-shrink: 0; position: relative; transition: all 0.3s;
    margin-left: 14px;
  }
  .sk-on { background: color-mix(in srgb, var(--sk-color) 25%, #060609); box-shadow: 0 0 12px color-mix(in srgb, var(--sk-color) 15%, transparent); }
  .sk-off { background: rgba(255,255,255,0.06); }
  .sk-toggle-knob {
    position: absolute; top: 3px; width: 20px; height: 20px; border-radius: 50%;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); display: block;
  }
  .sk-on .sk-toggle-knob { left: 25px; background: var(--sk-color); box-shadow: 0 0 8px var(--sk-color); }
  .sk-off .sk-toggle-knob { left: 3px; background: #4A3D30; }
  .sk-locked {
    background: rgba(245,158,11,0.04) !important;
    cursor: not-allowed; opacity: 0.7;
  }
  .sk-lock-icon { font-size: 12px; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }
  .sk-toggling { opacity: 0.5; pointer-events: none; }
`;

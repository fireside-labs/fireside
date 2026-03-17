"use client";

import { useState, useMemo, useEffect } from "react";
import { useToast } from "@/components/Toast";
import { getPlugins, installPlugin, uninstallPlugin } from "@/lib/api";

interface Skill {
    id: string; name: string; description: string; warning: string;
    icon: string; color: string; defaultOn: boolean;
    category: "core" | "enhancement" | "integration";
    rarity: "legendary" | "rare" | "common";
    power: number; // contribution to power level (out of 100)
}

const SKILLS: Skill[] = [
    { id: "working-memory", name: "Long-Term Memory", description: "Remembers past conversations and learns your preferences over time.", warning: "Disabling resets your AI to a stranger each session.", icon: "🧠", color: "#A78BFA", defaultOn: true, category: "core", rarity: "legendary", power: 20 },
    { id: "personality", name: "Soul Evolution", description: "Personality adapts based on interactions, developing unique traits.", warning: "Disable for a static, neutral assistant.", icon: "💫", color: "#F59E0B", defaultOn: true, category: "core", rarity: "legendary", power: 15 },
    { id: "self-model", name: "Self-Awareness", description: "Reflects on its own strengths and weaknesses for calibrated responses.", warning: "Without this, your AI won't know its limitations.", icon: "🪞", color: "#34D399", defaultOn: true, category: "core", rarity: "legendary", power: 15 },
    { id: "adaptive-thinking", name: "Deep Thinking", description: "Chain-of-thought reasoning. Slower but significantly smarter on hard questions.", warning: "Disabling makes responses faster but less thorough.", icon: "💭", color: "#60A5FA", defaultOn: true, category: "core", rarity: "legendary", power: 20 },
    { id: "voice", name: "Voice Mode", description: "Talk to your AI with voice (Whisper + Kokoro).", warning: "Requires microphone access. Uses ~200MB additional RAM.", icon: "🎙", color: "#F472B6", defaultOn: false, category: "enhancement", rarity: "rare", power: 8 },
    { id: "browse", name: "Web Browsing", description: "Read and summarize web pages, search for current information.", warning: "Requires internet. AI will make outbound requests.", icon: "🌐", color: "#38BDF8", defaultOn: false, category: "enhancement", rarity: "rare", power: 8 },
    { id: "alerts", name: "Smart Alerts", description: "Proactive notifications. Your AI reaches out when it has something for you.", warning: "May send desktop notifications.", icon: "🔔", color: "#FBBF24", defaultOn: false, category: "enhancement", rarity: "rare", power: 5 },
    { id: "terminal", name: "Terminal Access", description: "Run commands on your computer. Create files, install software, run scripts.", warning: "Always asks permission before executing.", icon: "💻", color: "#22D3EE", defaultOn: false, category: "enhancement", rarity: "rare", power: 6 },
    { id: "telegram", name: "Telegram Bot", description: "Chat with your AI from Telegram on the go.", warning: "Requires a Telegram Bot Token.", icon: "✈", color: "#818CF8", defaultOn: false, category: "integration", rarity: "common", power: 3 },
];

const RARITY_CONFIG = {
    legendary: { label: "Legendary", color: "#F59E0B", bg: "rgba(245,158,11,0.08)" },
    rare: { label: "Rare", color: "#A78BFA", bg: "rgba(167,139,250,0.08)" },
    common: { label: "Common", color: "#6A5A4A", bg: "rgba(106,90,74,0.08)" },
};

export default function SkillsPage() {
    const { toast } = useToast();
    const [enabledSkills, setEnabledSkills] = useState<Record<string, boolean>>(() => {
        // Start with defaults, then override from localStorage (instant), then API (async)
        const init: Record<string, boolean> = {};
        SKILLS.forEach(s => { init[s.id] = s.defaultOn; });
        if (typeof window !== "undefined") {
            const saved = localStorage.getItem("fireside_skills");
            if (saved) try { Object.assign(init, JSON.parse(saved)); } catch {}
        }
        return init;
    });

    // Load from backend on mount (overrides localStorage if backend is online)
    useEffect(() => {
        getPlugins().then(plugins => {
            if (plugins.length > 0) {
                const backendState: Record<string, boolean> = {};
                SKILLS.forEach(s => { backendState[s.id] = false; });
                plugins.forEach(p => {
                    if (p.name in backendState) backendState[p.name] = true;
                });
                setEnabledSkills(backendState);
            }
        });
    }, []);

    const toggleSkill = async (id: string) => {
        const wasEnabled = enabledSkills[id];
        const newState = !wasEnabled;
        const skillName = SKILLS.find(s => s.id === id)?.name || id;

        // Optimistic update
        setEnabledSkills(prev => {
            const next = { ...prev, [id]: newState };
            localStorage.setItem("fireside_skills", JSON.stringify(next));
            return next;
        });

        toast(`${newState ? "Enabling" : "Disabling"} ${skillName}...`, "success");

        // Call backend
        const result = newState ? await installPlugin(id) : await uninstallPlugin(id);
        if (result.status === "installed" || result.status === "uninstalled") {
            // Mock fallback — backend offline
        }
    };

    // Power Level calculation
    const powerLevel = useMemo(() => {
        return SKILLS.reduce((sum, s) => sum + (enabledSkills[s.id] ? s.power : 0), 0);
    }, [enabledSkills]);

    const powerLabel = powerLevel >= 80 ? "🔥 Maxed Out" : powerLevel >= 60 ? "⚡ Strong" : powerLevel >= 40 ? "💪 Solid" : "🌱 Basic";
    const powerColor = powerLevel >= 80 ? "#F59E0B" : powerLevel >= 60 ? "#A78BFA" : powerLevel >= 40 ? "#34D399" : "#5A4D40";

    const coreSkills = SKILLS.filter(s => s.category === "core");
    const enhancementSkills = SKILLS.filter(s => s.category === "enhancement");
    const integrationSkills = SKILLS.filter(s => s.category === "integration");

    return (
        <div className="max-w-2xl mx-auto">
            <style>{css}</style>

            <div className="mb-6">
                <h1 className="sk-page-title">✦ Skills</h1>
                <p className="sk-page-sub">Equip your AI with new abilities — toggle on or off anytime.</p>
            </div>

            {/* Power Level Bar */}
            <div className="sk-power-card">
                <div className="sk-power-header">
                    <span className="sk-power-label">Power Level</span>
                    <span className="sk-power-value" style={{ color: powerColor }}>{powerLabel} · {powerLevel}/100</span>
                </div>
                <div className="sk-power-bar">
                    <div className="sk-power-fill" style={{ width: `${powerLevel}%`, background: `linear-gradient(90deg, ${powerColor}44, ${powerColor})` }} />
                </div>
                <div className="sk-power-stats">
                    <span>{SKILLS.filter(s => enabledSkills[s.id]).length}/{SKILLS.length} skills active</span>
                    <span>{SKILLS.filter(s => enabledSkills[s.id] && s.rarity === "legendary").length} legendary</span>
                </div>
            </div>

            <div className="space-y-8">
                <div>
                    <h3 className="sk-group-label">🔥 Core Skills <span className="sk-rarity-badge" style={{ color: RARITY_CONFIG.legendary.color, background: RARITY_CONFIG.legendary.bg }}>Legendary</span></h3>
                    <p className="sk-group-desc">These make your AI feel alive. Enabled by default.</p>
                    <div className="sk-list">
                        {coreSkills.map(skill => (
                            <SkillCard key={skill.id} skill={skill} enabled={enabledSkills[skill.id]} onToggle={() => toggleSkill(skill.id)} />
                        ))}
                    </div>
                </div>

                <div>
                    <h3 className="sk-group-label">✨ Enhancements <span className="sk-rarity-badge" style={{ color: RARITY_CONFIG.rare.color, background: RARITY_CONFIG.rare.bg }}>Rare</span></h3>
                    <p className="sk-group-desc">Add new capabilities to your AI.</p>
                    <div className="sk-list">
                        {enhancementSkills.map(skill => (
                            <SkillCard key={skill.id} skill={skill} enabled={enabledSkills[skill.id]} onToggle={() => toggleSkill(skill.id)} />
                        ))}
                    </div>
                </div>

                <div>
                    <h3 className="sk-group-label">🔌 Integrations <span className="sk-rarity-badge" style={{ color: RARITY_CONFIG.common.color, background: RARITY_CONFIG.common.bg }}>Common</span></h3>
                    <p className="sk-group-desc">Connect your AI to external services.</p>
                    <div className="sk-list">
                        {integrationSkills.map(skill => (
                            <SkillCard key={skill.id} skill={skill} enabled={enabledSkills[skill.id]} onToggle={() => toggleSkill(skill.id)} />
                        ))}
                    </div>
                </div>

                <div className="sk-browse">
                    <p className="sk-browse-text">🛒 Community skills marketplace coming soon</p>
                </div>
            </div>
        </div>
    );
}

function SkillCard({ skill, enabled, onToggle }: { skill: Skill; enabled: boolean; onToggle: () => void }) {
    const rConf = RARITY_CONFIG[skill.rarity];
    return (
        <div className="sk-card" style={{ "--sk-color": skill.color } as React.CSSProperties}>
            <div className="sk-card-left">
                <span className="sk-icon">{skill.icon}</span>
                <div className="sk-info">
                    <div className="sk-name-row">
                        <span className="sk-name">{skill.name}</span>
                        <span className="sk-rarity-tag" style={{ color: rConf.color, background: rConf.bg }}>{rConf.label}</span>
                        <span className="sk-power-tag">+{skill.power}</span>
                    </div>
                    <div className="sk-desc">{skill.description}</div>
                    {!enabled && skill.category === "core" && <div className="sk-warning">⚠ {skill.warning}</div>}
                    {enabled && skill.category !== "core" && <div className="sk-active-note">Active · {skill.warning}</div>}
                </div>
            </div>
            <button className={`sk-toggle ${enabled ? "sk-on" : "sk-off"}`} onClick={onToggle} style={{ "--sk-color": skill.color } as React.CSSProperties}>
                <span className="sk-toggle-knob" />
            </button>
        </div>
    );
}

const css = `
  .sk-page-title {
    font-size: 28px; font-weight: 900; margin: 0 0 6px;
    background: linear-gradient(135deg, #F0DCC8, #FBBF24);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-family: 'Outfit', system-ui;
  }
  .sk-page-sub { font-size: 14px; color: #5A4D40; }

  /* Power Level Bar */
  .sk-power-card {
    padding: 20px 24px; border-radius: 18px; margin-bottom: 28px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  }
  .sk-power-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .sk-power-label { font-size: 14px; font-weight: 800; color: #F0DCC8; font-family: 'Outfit'; }
  .sk-power-value { font-size: 13px; font-weight: 700; font-family: 'Outfit'; }
  .sk-power-bar {
    width: 100%; height: 8px; border-radius: 4px;
    background: rgba(255,255,255,0.04); overflow: hidden;
  }
  .sk-power-fill {
    height: 100%; border-radius: 4px;
    transition: width 0.5s cubic-bezier(0.16, 1, 0.3, 1), background 0.5s;
    box-shadow: 0 0 12px rgba(245,158,11,0.15);
  }
  .sk-power-stats {
    display: flex; justify-content: space-between; margin-top: 8px;
    font-size: 10px; color: #4A3D30; font-weight: 600;
  }

  /* Rarity badges */
  .sk-rarity-badge {
    font-size: 9px; font-weight: 800; padding: 2px 8px; border-radius: 6px;
    margin-left: 8px; text-transform: uppercase; letter-spacing: 0.5px;
  }
  .sk-rarity-tag {
    font-size: 8px; font-weight: 800; padding: 1px 6px; border-radius: 4px;
    text-transform: uppercase; letter-spacing: 0.5px; flex-shrink: 0;
  }
  .sk-power-tag {
    font-size: 9px; font-weight: 700; color: #5A4D40; flex-shrink: 0;
  }

  .sk-group-label { font-size: 16px; font-weight: 800; color: #F0DCC8; margin-bottom: 4px; font-family: 'Outfit'; display: flex; align-items: center; }
  .sk-group-desc { font-size: 11px; color: #4A3D30; margin-bottom: 12px; }
  .sk-list { display: flex; flex-direction: column; gap: 8px; }
  .sk-card {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 20px; border-radius: 16px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    transition: all 0.3s;
  }
  .sk-card:hover { background: rgba(255,255,255,0.05); border-color: color-mix(in srgb, var(--sk-color) 20%, transparent); }
  .sk-card-left { display: flex; align-items: flex-start; gap: 14px; flex: 1; min-width: 0; }
  .sk-icon { font-size: 28px; flex-shrink: 0; margin-top: 2px; filter: drop-shadow(0 0 8px color-mix(in srgb, var(--sk-color) 40%, transparent)); }
  .sk-info { flex: 1; min-width: 0; }
  .sk-name-row { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; flex-wrap: wrap; }
  .sk-name { font-size: 15px; font-weight: 700; color: var(--sk-color); font-family: 'Outfit'; }
  .sk-desc { font-size: 12px; color: #6A5A4A; line-height: 1.5; }
  .sk-warning { font-size: 10px; color: #F59E0B; margin-top: 4px; font-weight: 600; }
  .sk-active-note { font-size: 10px; color: #34D399; margin-top: 4px; font-weight: 500; }
  .sk-toggle { width: 48px; height: 26px; border-radius: 13px; border: none; cursor: pointer; flex-shrink: 0; position: relative; transition: all 0.3s; margin-left: 14px; }
  .sk-on { background: color-mix(in srgb, var(--sk-color) 30%, #060609); box-shadow: 0 0 14px color-mix(in srgb, var(--sk-color) 20%, transparent); }
  .sk-off { background: rgba(255,255,255,0.06); }
  .sk-toggle-knob { position: absolute; top: 3px; width: 20px; height: 20px; border-radius: 50%; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
  .sk-on .sk-toggle-knob { left: 25px; background: var(--sk-color); box-shadow: 0 0 10px var(--sk-color); }
  .sk-off .sk-toggle-knob { left: 3px; background: #4A3D30; }
  .sk-browse { text-align: center; padding: 20px; border: 1px dashed rgba(255,255,255,0.06); border-radius: 14px; }
  .sk-browse-text { font-size: 12px; color: #3A3530; }
`;

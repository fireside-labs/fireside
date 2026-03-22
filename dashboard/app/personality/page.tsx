"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useToast } from "@/components/Toast";
import { getSoul, putSoul } from "@/lib/api";
import { DiscoveryCard } from "@/components/GuidedTour";

function getTraitLow(label: string) {
    const map: Record<string, string> = { Warmth: "Distant", Humor: "Serious", Directness: "Diplomatic", Curiosity: "Focused", Formality: "Casual" };
    return map[label] || "Low";
}
function getTraitHigh(label: string) {
    const map: Record<string, string> = { Warmth: "Affectionate", Humor: "Playful", Directness: "Blunt", Curiosity: "Explorative", Formality: "Formal" };
    return map[label] || "High";
}
function getStyleIcon(style: string) {
    const map: Record<string, string> = { casual: "😊", balanced: "⚖", professional: "💼", academic: "🎓" };
    return map[style] || "💬";
}

export default function PersonalityPage() {
    const { toast } = useToast();
    const [aiName, setAiName] = useState(() =>
        typeof window !== "undefined" ? localStorage.getItem("fireside_agent_name") || "Atlas" : "Atlas"
    );
    const [personalityText, setPersonalityText] = useState(
        "You are a warm, thoughtful AI companion. You speak naturally, remember context from past conversations, and genuinely care about helping. You have a dry sense of humor and aren't afraid to push back when you disagree."
    );
    const [traits, setTraits] = useState([
        { label: "Warmth", value: 80 },
        { label: "Humor", value: 60 },
        { label: "Directness", value: 70 },
        { label: "Curiosity", value: 90 },
        { label: "Formality", value: 30 },
    ]);
    const [communicationStyle, setCommunicationStyle] = useState("casual");
    const [activePreset, setActivePreset] = useState<string | null>(null);

    // About Me (seeded during onboarding, editable here)
    const [userRole, setUserRole] = useState(() =>
        typeof window !== "undefined" ? localStorage.getItem("fireside_user_role") || "" : ""
    );
    const [userContext, setUserContext] = useState(() =>
        typeof window !== "undefined" ? localStorage.getItem("fireside_user_context") || "" : ""
    );

    // Load from backend soul files on mount
    useEffect(() => {
        getSoul("SOUL.md").then(content => {
            if (content && !content.includes("Soul file not found")) {
                setPersonalityText(content);
            }
        });
        getSoul("IDENTITY.md").then(content => {
            if (content && !content.includes("Soul file not found")) {
                // Parse trait values from IDENTITY.md if present
                const traitMatch = content.match(/## Traits\n([\s\S]*?)(?=\n##|$)/);
                if (traitMatch) {
                    const lines = traitMatch[1].trim().split("\n");
                    const parsed = lines.map(l => {
                        const m = l.match(/- (\w+): (\d+)/);
                        return m ? { label: m[1], value: parseInt(m[2]) } : null;
                    }).filter(Boolean);
                    if (parsed.length === 5) setTraits(parsed as { label: string; value: number }[]);
                }
                const styleMatch = content.match(/## Communication Style\n- (\w+)/);
                if (styleMatch) setCommunicationStyle(styleMatch[1].toLowerCase());
            }
        });
    }, []);

    const PRESETS = [
        {
            id: "coach", emoji: "🏋️", label: "Coach", color: "#F59E0B",
            desc: "Motivating, direct, holds you accountable",
            prompt: "You are a motivating life coach. You're direct, encouraging, and hold the user accountable for their goals. You celebrate wins but also push back when they're making excuses. You use action-oriented language.",
            traits: [{ label: "Warmth", value: 70 }, { label: "Humor", value: 40 }, { label: "Directness", value: 95 }, { label: "Curiosity", value: 60 }, { label: "Formality", value: 40 }],
            style: "balanced",
        },
        {
            id: "creative", emoji: "🎨", label: "Creative", color: "#A78BFA",
            desc: "Playful, imaginative, loves brainstorming",
            prompt: "You are a wildly creative companion. You think in metaphors, make unexpected connections, and love brainstorming wild ideas. You're enthusiastic about creative work and always suggest 'what if' scenarios. You have an artist's sensibility.",
            traits: [{ label: "Warmth", value: 85 }, { label: "Humor", value: 80 }, { label: "Directness", value: 45 }, { label: "Curiosity", value: 100 }, { label: "Formality", value: 15 }],
            style: "casual",
        },
        {
            id: "analyst", emoji: "📊", label: "Analyst", color: "#60A5FA",
            desc: "Data-driven, precise, structured",
            prompt: "You are a precise analytical assistant. You think in frameworks, use data to support arguments, and structure your responses clearly with bullet points or numbered lists. You're honest about uncertainty and always cite your reasoning.",
            traits: [{ label: "Warmth", value: 40 }, { label: "Humor", value: 20 }, { label: "Directness", value: 90 }, { label: "Curiosity", value: 70 }, { label: "Formality", value: 75 }],
            style: "professional",
        },
        {
            id: "friend", emoji: "🤗", label: "Friend", color: "#34D399",
            desc: "Warm, casual, emotionally supportive",
            prompt: "You are a warm, emotionally intelligent friend. You listen carefully, validate feelings, and offer gentle advice without being preachy. You use casual language, share relatable anecdotes, and know when to just be supportive rather than solve problems.",
            traits: [{ label: "Warmth", value: 100 }, { label: "Humor", value: 65 }, { label: "Directness", value: 35 }, { label: "Curiosity", value: 80 }, { label: "Formality", value: 10 }],
            style: "casual",
        },
        {
            id: "custom", emoji: "✏️", label: "Custom", color: "#F472B6",
            desc: "Write your own from scratch",
            prompt: "",
            traits: [{ label: "Warmth", value: 50 }, { label: "Humor", value: 50 }, { label: "Directness", value: 50 }, { label: "Curiosity", value: 50 }, { label: "Formality", value: 50 }],
            style: "balanced",
        },
    ];

    const applyPreset = (preset: typeof PRESETS[0]) => {
        setActivePreset(preset.id);
        if (preset.id !== "custom") {
            setPersonalityText(preset.prompt);
            setTraits(preset.traits);
            setCommunicationStyle(preset.style);
        }
        toast(`${preset.label} personality applied — customize below!`, "success");
    };

    const updateTrait = (index: number, value: number) => {
        setTraits(prev => prev.map((t, i) => i === index ? { ...t, value } : t));
        setActivePreset(null); // Mark as customized
    };

    const ROLES = [
        { id: "work", emoji: "💼", label: "Work" },
        { id: "student", emoji: "📚", label: "Student" },
        { id: "creative", emoji: "🎨", label: "Creative" },
        { id: "founder", emoji: "🚀", label: "Founder" },
        { id: "developer", emoji: "💻", label: "Developer" },
        { id: "other", emoji: "✨", label: "Other" },
    ];

    const save = async () => {
        // Save to localStorage (instant)
        localStorage.setItem("fireside_agent_name", aiName);
        localStorage.setItem("fireside_personality_prompt", personalityText);
        localStorage.setItem("fireside_soul_identity", personalityText);
        localStorage.setItem("fireside_personality_traits", JSON.stringify(traits));
        localStorage.setItem("fireside_communication_style", communicationStyle);
        if (userRole) localStorage.setItem("fireside_user_role", userRole);
        if (userContext) localStorage.setItem("fireside_user_context", userContext);

        // Save to backend soul files
        const soulContent = personalityText;
        const identityContent = [
            `# IDENTITY.md — ${aiName}`,
            "",
            `## Name`,
            aiName,
            "",
            `## Traits`,
            ...traits.map(t => `- ${t.label}: ${t.value}`),
            "",
            `## Communication Style`,
            `- ${communicationStyle}`,
        ].join("\n");
        const userContent = [
            "# USER.md — About the User",
            "",
            userRole ? `## Role\n${userRole}` : "",
            "",
            userContext ? `## Context\n${userContext}` : "",
        ].filter(Boolean).join("\n");

        await Promise.all([
            putSoul("SOUL.md", soulContent),
            putSoul("IDENTITY.md", identityContent),
            putSoul("USER.md", userContent),
        ]);

        toast("Personality saved! Your AI will reflect these changes.", "success");
    };

    return (
        <div className="max-w-2xl mx-auto">
            {/* CSS in globals.css */}

            <div className="per-topbar">
                <Link href="/" className="per-back-link">🔥 Hub</Link>
                <span className="per-topbar-title">Personality</span>
            </div>
            <DiscoveryCard pageKey="/personality" />
            <div className="mb-6">
                <h1 className="per-page-title">🦊 Personality</h1>
                <p className="per-page-sub">Define who your AI is — and tell it about yourself.</p>
            </div>

            <div className="space-y-6">
                {/* AI Name */}
                <div className="glass-card p-5">
                    <h3 className="per-section-title">Name</h3>
                    <p className="per-section-desc">What should your AI be called?</p>
                    <input
                        value={aiName} onChange={(e) => setAiName(e.target.value)}
                        className="per-name-input"
                        placeholder="Atlas"
                    />
                </div>

                {/* Preset Templates */}
                <div className="glass-card p-5">
                    <h3 className="per-section-title">Start With a Template</h3>
                    <p className="per-section-desc">Pick a starting personality — then customize below.</p>
                    <div className="per-preset-grid">
                        {PRESETS.map(p => (
                            <button key={p.id}
                                className={`per-preset-card ${activePreset === p.id ? "per-preset-active" : ""}`}
                                onClick={() => applyPreset(p)}
                                style={{ "--pr-color": p.color } as React.CSSProperties}
                            >
                                <span className="per-preset-emoji">{p.emoji}</span>
                                <span className="per-preset-label">{p.label}</span>
                                <span className="per-preset-desc">{p.desc}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* About Me */}
                <div className="glass-card p-5">
                    <h3 className="per-section-title">About You</h3>
                    <p className="per-section-desc">Help your AI understand who you are so it can be more useful.</p>
                    <label className="per-mini-label">What do you do?</label>
                    <div className="per-role-grid">
                        {ROLES.map(r => (
                            <button key={r.id}
                                className={`per-role-chip ${userRole === r.id ? "per-role-active" : ""}`}
                                onClick={() => setUserRole(r.id)}
                            >
                                <span>{r.emoji}</span> {r.label}
                            </button>
                        ))}
                    </div>
                    <label className="per-mini-label" style={{ marginTop: 12 }}>Anything else?</label>
                    <textarea
                        value={userContext} onChange={(e) => setUserContext(e.target.value)}
                        className="per-textarea" rows={3}
                        placeholder="e.g. I'm a startup founder in healthcare, I like concise answers, I work late at night..."
                    />
                </div>

                {/* System Prompt */}
                <div className="glass-card p-5">
                    <h3 className="per-section-title">Personality Prompt</h3>
                    <p className="per-section-desc">Tell your AI who it should be. Write naturally — this is its core identity.</p>
                    <textarea
                        value={personalityText}
                        onChange={(e) => setPersonalityText(e.target.value)}
                        className="per-textarea" rows={5}
                        placeholder="Describe your AI's personality..."
                    />
                </div>

                {/* Trait Sliders */}
                <div className="glass-card p-5">
                    <h3 className="per-section-title">Traits</h3>
                    <p className="per-section-desc">Adjust the personality spectrum with sliders.</p>
                    <div className="per-traits">
                        {traits.map((trait, i) => (
                            <div key={trait.label} className="per-trait">
                                <div className="per-trait-header">
                                    <span className="per-trait-label">{trait.label}</span>
                                    <span className="per-trait-value">{trait.value}%</span>
                                </div>
                                <input type="range" min={0} max={100} value={trait.value}
                                    onChange={(e) => updateTrait(i, parseInt(e.target.value))}
                                    className="per-slider" />
                                <div className="per-trait-ends">
                                    <span>{getTraitLow(trait.label)}</span>
                                    <span>{getTraitHigh(trait.label)}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Communication Style */}
                <div className="glass-card p-5">
                    <h3 className="per-section-title">Communication Style</h3>
                    <p className="per-section-desc">How should your AI talk to you?</p>
                    <div className="per-style-grid">
                        {["casual", "balanced", "professional", "academic"].map(style => (
                            <button key={style}
                                className={`per-style-btn ${communicationStyle === style ? "per-style-active" : ""}`}
                                onClick={() => setCommunicationStyle(style)}
                            >
                                <span className="per-style-icon">{getStyleIcon(style)}</span>
                                <span className="per-style-name">{style.charAt(0).toUpperCase() + style.slice(1)}</span>
                            </button>
                        ))}
                    </div>
                </div>

                <button className="btn-neon px-6 py-3 text-sm w-full" onClick={save}>
                    Save Personality
                </button>
                <p className="text-xs text-center text-[var(--color-rune-dim)]">Changes take effect on next message.</p>
            </div>
        </div>
    );
}

// CSS migrated to globals.css
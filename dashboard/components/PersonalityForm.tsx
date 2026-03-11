"use client";

import { useState } from "react";

const TONE_OPTIONS = [
    { id: "casual", label: "Casual", desc: "Relaxed, conversational" },
    { id: "friendly", label: "Friendly", desc: "Warm, chatty, uses emoji" },
    { id: "professional", label: "Professional", desc: "Polite, proper, no slang" },
    { id: "direct", label: "Direct", desc: "Short, no fluff, gets to the point" },
    { id: "playful", label: "Playful", desc: "Fun, witty, lighthearted" },
];

const SKILL_PRESETS = [
    "Writing & editing",
    "Answering research questions",
    "Writing code",
    "Sales & outreach",
    "Data analysis",
];

interface PersonalityFormProps {
    initialValues?: {
        name: string;
        role: string;
        tone: string;
        skills: string[];
        boundaries: string[];
    };
    onSave: (values: { name: string; role: string; tone: string; skills: string[]; boundaries: string[] }) => void;
}

export default function PersonalityForm({ initialValues, onSave }: PersonalityFormProps) {
    const [name, setName] = useState(initialValues?.name || "Odin");
    const [role, setRole] = useState(initialValues?.role || "assistant");
    const [tone, setTone] = useState(initialValues?.tone || "friendly");
    const [skills, setSkills] = useState<string[]>(initialValues?.skills || ["Writing & editing", "Answering research questions"]);
    const [boundaries, setBoundaries] = useState<string[]>(initialValues?.boundaries || ["Don't share my personal information", "Always ask before deleting files"]);
    const [customSkill, setCustomSkill] = useState("");
    const [newRule, setNewRule] = useState("");
    const [showAdvanced, setShowAdvanced] = useState(false);

    const toggleSkill = (skill: string) => {
        setSkills(prev => prev.includes(skill) ? prev.filter(s => s !== skill) : [...prev, skill]);
    };

    const addCustomSkill = () => {
        if (customSkill.trim() && !skills.includes(customSkill.trim())) {
            setSkills([...skills, customSkill.trim()]);
            setCustomSkill("");
        }
    };

    const addRule = () => {
        if (newRule.trim()) {
            setBoundaries([...boundaries, newRule.trim()]);
            setNewRule("");
        }
    };

    const removeRule = (i: number) => {
        setBoundaries(boundaries.filter((_, idx) => idx !== i));
    };

    return (
        <div className="space-y-6">
            {/* Name & Identity */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-4">Name & Identity</h3>
                <div className="space-y-3">
                    <div>
                        <label htmlFor="personality-name" className="text-xs text-[var(--color-rune-dim)] mb-1 block">Name</label>
                        <input
                            id="personality-name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors"
                        />
                    </div>
                    <div>
                        <label htmlFor="personality-role" className="text-xs text-[var(--color-rune-dim)] mb-1 block">Role</label>
                        <select
                            id="personality-role"
                            value={role}
                            onChange={(e) => setRole(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none"
                        >
                            <option value="assistant">Your main assistant</option>
                            <option value="researcher">Research specialist</option>
                            <option value="writer">Writing assistant</option>
                            <option value="coder">Coding assistant</option>
                            <option value="analyst">Data analyst</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Tone */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-1">Tone</h3>
                <p className="text-xs text-[var(--color-rune-dim)] mb-4">How should your AI talk to you?</p>
                <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Tone selection">
                    {TONE_OPTIONS.map((t) => (
                        <button
                            key={t.id}
                            onClick={() => setTone(t.id)}
                            role="radio"
                            aria-checked={tone === t.id}
                            className="px-4 py-2 rounded-lg text-sm transition-all"
                            style={{
                                background: tone === t.id ? "var(--color-neon-glow)" : "var(--color-glass)",
                                color: tone === t.id ? "var(--color-neon)" : "var(--color-rune)",
                                border: `1px solid ${tone === t.id ? "var(--color-neon)" : "var(--color-glass-border)"}`,
                            }}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Skills */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-1">What it's good at</h3>
                <p className="text-xs text-[var(--color-rune-dim)] mb-4">Select the skills your AI should focus on.</p>
                <div className="space-y-2">
                    {SKILL_PRESETS.map((skill) => (
                        <label key={skill} className="flex items-center gap-3 cursor-pointer group min-h-[44px]">
                            <div
                                className="w-5 h-5 rounded border-2 flex items-center justify-center transition-colors"
                                role="checkbox"
                                aria-checked={skills.includes(skill)}
                                tabIndex={0}
                                onKeyDown={(e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); toggleSkill(skill); } }}
                                style={{
                                    borderColor: skills.includes(skill) ? "var(--color-neon)" : "var(--color-glass-border)",
                                    background: skills.includes(skill) ? "var(--color-neon-glow)" : "transparent",
                                }}
                                onClick={() => toggleSkill(skill)}
                            >
                                {skills.includes(skill) && <span className="text-xs text-[var(--color-neon)]">✓</span>}
                            </div>
                            <span className="text-sm text-[var(--color-rune)] group-hover:text-white transition-colors">{skill}</span>
                        </label>
                    ))}
                    {/* Custom skills */}
                    {skills.filter(s => !SKILL_PRESETS.includes(s)).map((skill) => (
                        <label key={skill} className="flex items-center gap-3">
                            <div
                                className="w-5 h-5 rounded border-2 flex items-center justify-center"
                                style={{ borderColor: "var(--color-neon)", background: "var(--color-neon-glow)" }}
                                onClick={() => toggleSkill(skill)}
                            >
                                <span className="text-xs text-[var(--color-neon)]">✓</span>
                            </div>
                            <span className="text-sm text-[var(--color-rune)]">{skill}</span>
                        </label>
                    ))}
                    <div className="flex gap-2 mt-2">
                        <input
                            value={customSkill}
                            onChange={(e) => setCustomSkill(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && addCustomSkill()}
                            placeholder="Add a custom skill..."
                            className="flex-1 px-3 py-1.5 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)]"
                        />
                        <button onClick={addCustomSkill} className="text-sm text-[var(--color-neon)] hover:underline min-h-[44px] min-w-[44px]">+ Add</button>
                    </div>
                </div>
            </div>

            {/* Boundaries */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-1">Boundaries</h3>
                <p className="text-xs text-[var(--color-rune-dim)] mb-4">Things your AI should NEVER do.</p>
                <div className="space-y-2">
                    {boundaries.map((rule, i) => (
                        <div key={i} className="flex items-center gap-2 group">
                            <span className="text-xs text-[var(--color-danger)]">🚫</span>
                            <span className="text-sm text-[var(--color-rune)] flex-1">{rule}</span>
                            <button
                                onClick={() => removeRule(i)}
                                className="text-xs text-[var(--color-rune-dim)] opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                ✕
                            </button>
                        </div>
                    ))}
                    <div className="flex gap-2 mt-2">
                        <input
                            value={newRule}
                            onChange={(e) => setNewRule(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && addRule()}
                            placeholder="Add a rule..."
                            className="flex-1 px-3 py-1.5 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)]"
                        />
                        <button onClick={addRule} className="text-sm text-[var(--color-neon)] hover:underline min-h-[44px] min-w-[44px]">+ Add rule</button>
                    </div>
                </div>
            </div>

            {/* Advanced */}
            <div className="glass-card p-5">
                <button
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="text-sm text-[var(--color-rune-dim)] hover:text-[var(--color-rune)] transition-colors"
                >
                    {showAdvanced ? "▾" : "▸"} Edit raw personality files
                </button>
                {showAdvanced && (
                    <p className="text-xs text-[var(--color-rune-dim)] mt-2">
                        For power users — edit the SOUL, IDENTITY, and USER files directly in markdown.
                        <br />
                        <a href="/soul" className="text-[var(--color-neon)] hover:underline mt-1 inline-block">Open raw editor →</a>
                    </p>
                )}
            </div>

            {/* Save */}
            <button
                onClick={() => onSave({ name, role, tone, skills, boundaries })}
                className="btn-neon px-6 py-3 text-sm w-full"
            >
                Save Changes
            </button>
        </div>
    );
}

"use client";

import { useState, useEffect } from "react";
import GuildHallAgent from "@/components/GuildHallAgent";
import type { Activity } from "@/components/GuildHallAgent";
import { useRouter } from "next/navigation";

interface GuildHallProps {
    theme: string;
}

// Activity zones — where agents go based on what they're doing
const ACTIVITY_ZONES: Record<Activity, { x: number; y: number }> = {
    writing: { x: 20, y: 75 },   // desk area
    researching: { x: 75, y: 70 },   // bookshelf area
    building: { x: 35, y: 60 },   // forge/workbench
    reviewing: { x: 60, y: 80 },   // reading area
    debating: { x: 50, y: 55 },   // center (face-to-face)
    running_task: { x: 40, y: 70 },   // workstation
    idle: { x: 15, y: 85 },   // lounge corner
    sleeping: { x: 88, y: 92 },   // far corner
    crucible: { x: 25, y: 55 },   // forge/cauldron
    chatting: { x: 50, y: 75 },   // center stage
};

const DUST_PARTICLES = Array.from({ length: 15 }).map((_, i) => ({
    id: i,
    left: Math.random() * 100,
    top: Math.random() * 100,
    size: 2 + Math.random() * 2,
    duration: 15 + Math.random() * 20,
    delay: Math.random() * 10,
}));

const THEME_COLORS: Record<string, { bg: string; floor: string; accent: string }> = {
    valhalla: { bg: "#1a1520", floor: "#2a1f1a", accent: "#c0820a" },
    office: { bg: "#1a1a24", floor: "#2a2a35", accent: "#4488aa" },
    space: { bg: "#0a0a1a", floor: "#151528", accent: "#6644cc" },
    cozy: { bg: "#1f1a15", floor: "#2f2520", accent: "#cc8844" },
    dungeon: { bg: "#12100e", floor: "#221e1a", accent: "#886622" },
};

const THEME_ELEMENTS: Record<string, { emoji: string; label: string; x: number; y: number }[]> = {
    valhalla: [
        { emoji: "🔥", label: "Forge", x: 28, y: 50 },
        { emoji: "📜", label: "Scroll Table", x: 18, y: 70 },
        { emoji: "📚", label: "Rune Library", x: 72, y: 60 },
        { emoji: "🍺", label: "Mead Hall", x: 82, y: 80 },
        { emoji: "⚔️", label: "Weapon Rack", x: 10, y: 55 },
    ],
    office: [
        { emoji: "💻", label: "Desk", x: 18, y: 70 },
        { emoji: "📋", label: "Whiteboard", x: 32, y: 50 },
        { emoji: "🗄️", label: "Files", x: 72, y: 60 },
        { emoji: "☕", label: "Coffee", x: 82, y: 80 },
        { emoji: "🪑", label: "Meeting", x: 50, y: 50 },
    ],
    space: [
        { emoji: "🖥️", label: "Console", x: 18, y: 70 },
        { emoji: "🔧", label: "Workshop", x: 32, y: 50 },
        { emoji: "🌀", label: "Hologram", x: 72, y: 60 },
        { emoji: "🛸", label: "Viewport", x: 50, y: 40 },
        { emoji: "💺", label: "Bridge", x: 82, y: 80 },
    ],
    cozy: [
        { emoji: "🛋️", label: "Couch", x: 55, y: 75 },
        { emoji: "📖", label: "Bookshelf", x: 72, y: 60 },
        { emoji: "🍳", label: "Kitchen", x: 25, y: 55 },
        { emoji: "🪴", label: "Plants", x: 85, y: 65 },
        { emoji: "🐱", label: "Cat", x: 65, y: 88 },
    ],
    dungeon: [
        { emoji: "⚒️", label: "Anvil", x: 28, y: 50 },
        { emoji: "🗡️", label: "Armory", x: 10, y: 55 },
        { emoji: "📦", label: "Chests", x: 72, y: 60 },
        { emoji: "🔥", label: "Campfire", x: 82, y: 85 },
        { emoji: "🧪", label: "Cauldron", x: 22, y: 50 },
    ],
};

/** Style → avatar config mapping for the AI agent */
const STYLE_AVATARS: Record<string, { hairStyle: number; hairColor: string; skinTone: string; outfit: "warrior" | "artist" | "guardian" | "crown"; accessory: "none" | "glasses" }> = {
    analytical: { hairStyle: 0, hairColor: "#1A1A2E", skinTone: "#D4A574", outfit: "guardian", accessory: "glasses" },
    creative: { hairStyle: 2, hairColor: "#F4D03F", skinTone: "#FAD7A0", outfit: "artist", accessory: "none" },
    direct: { hairStyle: 4, hairColor: "#8B4513", skinTone: "#F5CBA7", outfit: "warrior", accessory: "none" },
    warm: { hairStyle: 3, hairColor: "#C0392B", skinTone: "#FBEEE6", outfit: "crown", accessory: "none" },
};

const SPECIES_EMOJI: Record<string, string> = {
    cat: "🐱", dog: "🐶", penguin: "🐧", fox: "🦊", owl: "🦉", dragon: "🐉",
};

interface GuildAgent {
    name: string;
    avatar: { style: "pixel"; hairStyle: number; hairColor: string; skinTone: string; outfit: "warrior" | "artist" | "guardian" | "crown" | "cat" | "dog" | "penguin" | "fox" | "owl" | "dragon" | "developer" | "scholar"; accessory: "none" | "glasses" };
    activity: Activity;
    status: "online" | "offline";
    taskLabel: string | null;
    type: "ai" | "companion";
}

// Build agents dynamically from localStorage
function getLocalAgents(): GuildAgent[] {
    if (typeof window === "undefined") return [];
    const agents: GuildAgent[] = [];

    // AI agent from onboarding
    const agentName = localStorage.getItem("fireside_agent_name") || "Atlas";
    const agentStyle = localStorage.getItem("fireside_agent_style") || "analytical";
    const avatarConfig = STYLE_AVATARS[agentStyle] || STYLE_AVATARS.analytical;
    agents.push({
        name: agentName,
        avatar: { style: "pixel" as const, ...avatarConfig },
        activity: "idle" as Activity, status: "online" as const, taskLabel: null, type: "ai" as const,
    });

    // Companion from onboarding
    try {
        const companionRaw = localStorage.getItem("fireside_companion");
        if (companionRaw) {
            const companion = JSON.parse(companionRaw);
            if (companion.name && companion.species) {
                agents.push({
                    name: companion.name,
                    avatar: { style: "pixel" as const, hairStyle: 0, hairColor: "#333", skinTone: "#fad7a0", outfit: companion.species as "warrior", accessory: "none" as const },
                    activity: "idle" as Activity, status: "online" as const, taskLabel: null, type: "ai" as const,
                });
            }
        }
    } catch { /* ignore */ }

    return agents;
}

interface GuildHallAgentData {
    name: string;
    type: "ai" | "companion";
    style?: string;
    species?: string;
    activity: string;
    status: string;
    taskLabel?: string | null;
}

export default function GuildHall({ theme }: GuildHallProps) {
    const router = useRouter();
    const themeColors = THEME_COLORS[theme] || THEME_COLORS.cozy;
    const elements = THEME_ELEMENTS[theme] || THEME_ELEMENTS.cozy;
    const [agents, setAgents] = useState<GuildAgent[]>([]);

    // Sprint 15: Load agents from localStorage, then try API
    useEffect(() => {
        const local = getLocalAgents();
        if (local.length > 0) setAgents(local);
        (async () => {
            try {
                const res = await fetch("http://127.0.0.1:8765/api/v1/guildhall/agents");
                if (res.ok) {
                    const data = await res.json();
                    const mapped = (data.agents || []).map((a: GuildHallAgentData) => {
                        const styleKey = a.style || "analytical";
                        const avatarConfig = STYLE_AVATARS[styleKey] || STYLE_AVATARS.analytical;
                        return {
                            name: a.name,
                            type: a.type,
                            species: a.species,
                            avatar: { style: "pixel" as const, ...avatarConfig },
                            activity: (a.activity || "idle") as Activity,
                            status: (a.status || "online") as "online" | "busy" | "offline",
                            taskLabel: a.taskLabel || null,
                        };
                    });
                    if (mapped.length > 0) setAgents(mapped);
                }
            } catch {
                // API unavailable — use fallback
            }
        })();
    }, []);

    return (
        <div
            className="relative w-full rounded-xl overflow-hidden"
            style={{
                aspectRatio: "16/9",
                background: `#120e0a`,
                border: `1px solid ${themeColors.accent}33`,
                boxShadow: `0 8px 32px rgba(0,0,0,0.5)`,
            }}
        >
            {/* Background Texture / Planks */}
            <div className="absolute inset-x-0 top-0 h-[60%] bg-[#1a1510] border-b border-[#2a2520]" />
            <div className="absolute inset-x-0 bottom-0 h-[40%] bg-[#251e18]" />
            <div className="absolute inset-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'linear-gradient(rgba(0,0,0,0.3) 1px, transparent 1px)', backgroundSize: '100% 12px' }} />

            {/* Ambient Rays */}
            <div className="absolute inset-0 opacity-30 pointer-events-none bg-gradient-to-br from-white/10 to-transparent mix-blend-overlay" />
            {/* Deep Vignette */}
            <div className="absolute inset-0 pointer-events-none z-0" style={{
                background: "radial-gradient(circle at 50% 50%, transparent 20%, rgba(0,0,0,0.6) 100%)"
            }} />

            {/* Ambient Dust */}
            {DUST_PARTICLES.map(d => (
                <div
                    key={d.id}
                    className="absolute rounded-full bg-white/20 blur-[1px] animate-[pulse_3s_ease-in-out_infinite]"
                    style={{
                        left: `${d.left}%`,
                        top: `${d.top}%`,
                        width: d.size,
                        height: d.size,
                        animationDelay: `${d.delay}s`,
                    }}
                />
            ))}

            {/* Intense Fireplace/Light source glow */}
            <div
                className="absolute pointer-events-none"
                style={{
                    left: "78%", top: "55%",
                    width: 300, height: 300,
                    transform: "translate(-50%, -50%)",
                    background: `radial-gradient(circle, ${themeColors.accent}33 0%, ${themeColors.accent}10 40%, transparent 70%)`,
                    animation: "pulse 3s ease-in-out infinite",
                    mixBlendMode: "screen"
                }}
            />

            {/* Floor surface with subtle depth line */}
            <div
                className="absolute inset-x-0"
                style={{
                    top: "50%", height: 3,
                    background: `linear-gradient(90deg, transparent 5%, ${themeColors.accent}25 20%, ${themeColors.accent}40 50%, ${themeColors.accent}25 80%, transparent 95%)`,
                    boxShadow: `0 2px 10px ${themeColors.accent}20`
                }}
            />

            {/* Back Wall line */}
            <div
                className="absolute inset-x-0"
                style={{ top: "35%", height: "2px", background: `linear-gradient(90deg, transparent, ${themeColors.accent}15, transparent)` }}
            />

            {/* Theme elements (furniture/objects) — larger and more visible */}
            {elements.map((el) => (
                <div
                    key={el.label}
                    className="absolute transition-transform hover:scale-110"
                    style={{ left: `${el.x}%`, top: `${el.y}%`, transform: "translate(-50%, -50%)" }}
                >
                    <div className="text-center">
                        <span className="text-3xl block" style={{ opacity: 0.65, filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.3))" }}>{el.emoji}</span>
                        <span className="text-[8px] text-[var(--color-rune-dim)] opacity-50">{el.label}</span>
                    </div>
                </div>
            ))}

            {/* Agents — Sprint 10: AI agent at activity zone, companion near fire */}
            {agents.map((agent: GuildAgent, idx: number) => {
                // Companion sits near the fire, AI agent goes to activity zone
                const isCompanion = (agent as any).type === "companion";
                const zone = isCompanion
                    ? { x: 75, y: 88 }  // curled up near fire
                    : ACTIVITY_ZONES[(agent.activity as Activity)] || ACTIVITY_ZONES.idle;
                const offset = idx * 3;

                return (
                    <div key={agent.name}>
                        {/* Companion species emoji overlay */}
                        {isCompanion && (
                            <div
                                className="absolute text-center"
                                style={{
                                    left: `${zone.x}%`,
                                    top: `${zone.y}%`,
                                    transform: "translate(-50%, -50%)",
                                    zIndex: 10,
                                }}
                            >
                                <span className="text-3xl block animate-pulse">
                                    {SPECIES_EMOJI[(agent as any).species] || "🐱"}
                                </span>
                                <span className="text-[9px] text-[var(--color-neon)] font-medium block mt-0.5">
                                    {agent.name}
                                </span>
                            </div>
                        )}

                        {/* AI agent as GuildHallAgent component */}
                        {!isCompanion && (
                            <GuildHallAgent
                                name={agent.name}
                                avatar={agent.avatar}
                                activity={agent.activity}
                                status={agent.status}
                                taskLabel={agent.taskLabel ?? undefined}
                                position={{ x: zone.x + offset, y: zone.y }}
                                theme={theme}
                                onClick={() => { }}
                                onDoubleClick={() => router.push(`/agents/${agent.name}`)}
                            />
                        )}
                    </div>
                );
            })}

            {/* Theme watermark */}
            <div className="absolute bottom-2 right-3 text-[10px] text-[var(--color-rune-dim)] opacity-30 uppercase tracking-widest">
                {theme}
            </div>
        </div>
    );
}


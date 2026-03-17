"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { API_BASE } from "../lib/api";
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

const DUST_PARTICLES = Array.from({ length: 20 }).map((_, i) => ({
    id: i,
    left: Math.random() * 100,
    top: 10 + Math.random() * 50,
    size: 1 + Math.random() * 2,
    duration: 12 + Math.random() * 18,
    delay: Math.random() * 10,
}));

const FIRE_EMBERS = Array.from({ length: 10 }).map((_, i) => ({
    id: i,
    left: 74 + Math.random() * 12,
    delay: Math.random() * 3,
    size: 2 + Math.random() * 3,
    duration: 2 + Math.random() * 2,
}));

const THEME_COLORS: Record<string, { bg: string; floor: string; accent: string }> = {
    valhalla: { bg: "#1a1520", floor: "#2a1f1a", accent: "#c0820a" },
    office: { bg: "#1a1a24", floor: "#2a2a35", accent: "#4488aa" },
    space: { bg: "#0a0a1a", floor: "#151528", accent: "#4488ff" },
    cozy: { bg: "#1f1a15", floor: "#2f2520", accent: "#cc8844" },
    dungeon: { bg: "#12100e", floor: "#221e1a", accent: "#886622" },
    "japanese-garden": { bg: "#1a1520", floor: "#1f1a25", accent: "#e88db4" },
    "space-station": { bg: "#0a0a1a", floor: "#151528", accent: "#4488ff" },
    "anime-cafe": { bg: "#1a121f", floor: "#221828", accent: "#ff69b4" },
};

// Environment elements — emoji only (sprites are placeholder for future store packs)
interface EnvElement {
    emoji: string;
    label: string;
    x: number;
    y: number;
    layer: "bg" | "mid" | "fg";
}

const THEME_ELEMENTS: Record<string, EnvElement[]> = {
    valhalla: [
        { emoji: "🔥", label: "Forge", x: 80, y: 70, layer: "mid" },
        { emoji: "⚒️", label: "Anvil", x: 30, y: 65, layer: "mid" },
        { emoji: "🗺️", label: "War Table", x: 50, y: 60, layer: "mid" },
        { emoji: "🍺", label: "Mead Barrels", x: 88, y: 80, layer: "fg" },
        { emoji: "🎣", label: "Fishing", x: 10, y: 82, layer: "fg" },
        { emoji: "🔮", label: "Rune Stones", x: 65, y: 48, layer: "bg" },
        { emoji: "📚", label: "Scrolls", x: 45, y: 46, layer: "bg" },
    ],
    office: [
        { emoji: "💻", label: "Desk", x: 18, y: 72, layer: "mid" },
        { emoji: "💻", label: "Desk 2", x: 55, y: 72, layer: "mid" },
        { emoji: "📋", label: "Whiteboard", x: 35, y: 42, layer: "bg" },
        { emoji: "📚", label: "Bookshelf", x: 65, y: 42, layer: "bg" },
        { emoji: "☕", label: "Coffee", x: 88, y: 78, layer: "fg" },
        { emoji: "🌿", label: "Plant", x: 8, y: 65, layer: "fg" },
        { emoji: "🛋️", label: "Lounge", x: 78, y: 55, layer: "mid" },
        { emoji: "🖨️", label: "Printer", x: 45, y: 55, layer: "mid" },
        { emoji: "🗄️", label: "Files", x: 92, y: 45, layer: "bg" },
        { emoji: "🖼️", label: "Art", x: 15, y: 38, layer: "bg" },
    ],
    space: [
        { emoji: "🖥️", label: "Console", x: 18, y: 72, layer: "mid" },
        { emoji: "🌀", label: "Hologram", x: 50, y: 55, layer: "mid" },
        { emoji: "🪟", label: "Viewport", x: 45, y: 35, layer: "bg" },
        { emoji: "⚡", label: "Reactor", x: 80, y: 65, layer: "mid" },
        { emoji: "❄️", label: "Cryo Pod", x: 90, y: 80, layer: "fg" },
    ],
    "space-station": [
        { emoji: "🖥️", label: "Command", x: 20, y: 72, layer: "mid" },
        { emoji: "🌀", label: "Hologram", x: 50, y: 55, layer: "mid" },
        { emoji: "🪟", label: "Viewport", x: 42, y: 32, layer: "bg" },
        { emoji: "⚡", label: "Reactor", x: 82, y: 65, layer: "mid" },
        { emoji: "❄️", label: "Cryo Pod", x: 92, y: 82, layer: "fg" },
    ],
    cozy: [
        { emoji: "🔥", label: "Fireplace", x: 78, y: 68, layer: "mid" },
        { emoji: "📖", label: "Bookshelf", x: 55, y: 50, layer: "bg" },
        { emoji: "🍳", label: "Kitchen", x: 20, y: 70, layer: "mid" },
        { emoji: "🪴", label: "Plants", x: 90, y: 60, layer: "bg" },
        { emoji: "🛋️", label: "Couch", x: 42, y: 80, layer: "fg" },
    ],
    dungeon: [
        { emoji: "🔥", label: "Campfire", x: 80, y: 75, layer: "mid" },
        { emoji: "⚒️", label: "Anvil", x: 28, y: 55, layer: "mid" },
        { emoji: "🗡️", label: "Armory", x: 10, y: 48, layer: "bg" },
        { emoji: "📦", label: "Chests", x: 60, y: 55, layer: "bg" },
        { emoji: "🧪", label: "Cauldron", x: 22, y: 55, layer: "mid" },
    ],
    "japanese-garden": [
        { emoji: "⛩️", label: "Torii Gate", x: 50, y: 42, layer: "bg" },
        { emoji: "🌸", label: "Sakura", x: 78, y: 55, layer: "bg" },
        { emoji: "🐟", label: "Koi Pond", x: 35, y: 78, layer: "mid" },
        { emoji: "🏮", label: "Lantern", x: 15, y: 65, layer: "mid" },
        { emoji: "🎋", label: "Bamboo", x: 92, y: 45, layer: "bg" },
        { emoji: "🏮", label: "Lantern 2", x: 65, y: 80, layer: "fg" },
    ],
    "anime-cafe": [
        { emoji: "☕", label: "Counter", x: 25, y: 68, layer: "mid" },
        { emoji: "📺", label: "カフェ", x: 50, y: 30, layer: "bg" },
        { emoji: "💺", label: "Booth", x: 75, y: 72, layer: "mid" },
        { emoji: "🥤", label: "Vending", x: 92, y: 60, layer: "bg" },
        { emoji: "🌃", label: "Window", x: 50, y: 38, layer: "bg" },
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
                    activity: "idle" as Activity, status: "online" as const, taskLabel: null, type: "companion" as const,
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
    const containerRef = useRef<HTMLDivElement>(null);
    const [parallax, setParallax] = useState({ x: 0, y: 0 });

    // F6: Parallax depth on mouse hover
    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (!containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const cx = (e.clientX - rect.left) / rect.width - 0.5;  // -0.5 to 0.5
        const cy = (e.clientY - rect.top) / rect.height - 0.5;
        setParallax({ x: cx * 8, y: cy * 4 });  // max 4px/2px shift
    }, []);

    const layerOffset = (layer: string) => {
        if (layer === "bg") return { transform: `translate(${parallax.x * 0.5}px, ${parallax.y * 0.5}px)` };
        if (layer === "fg") return { transform: `translate(${parallax.x * -1}px, ${parallax.y * -0.5}px)` };
        return {};  // mid = static
    };

    // Sprint 15: Load agents from localStorage, then try API
    useEffect(() => {
        const local = getLocalAgents();
        if (local.length > 0) setAgents(local);
        (async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/guildhall/agents`);
                if (res.ok) {
                    const data = await res.json();
                    const mapped = (data.agents || []).map((a: GuildHallAgentData) => {
                        const styleKey = a.style || "analytical";
                        const avatarConfig = STYLE_AVATARS[styleKey] || STYLE_AVATARS.analytical;
                        return {
                            name: a.name,
                            type: a.type,
                            species: a.species,
                            avatar: { style: styleKey, ...avatarConfig },
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

    // F1: Poll agent status every 5s for live status effects
    useEffect(() => {
        const poll = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/status/agent`);
                if (res.ok) {
                    const data = await res.json();
                    // Update agent activities from backend
                    if (data.status) {
                        setAgents(prev => prev.map(a => {
                            if (a.type === "companion") return a;
                            return {
                                ...a,
                                activity: (data.activity || a.activity) as Activity,
                                status: (data.status === "error" ? "hurt" : a.status) as "online" | "offline",
                                taskLabel: data.task_label || a.taskLabel,
                            };
                        }));
                    }
                }
            } catch { /* backend offline — keep local state */ }
        };
        const interval = setInterval(poll, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div
            ref={containerRef}
            className="relative w-full rounded-xl overflow-hidden"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setParallax({ x: 0, y: 0 })}
            style={{
                aspectRatio: "16/9",
                background: `#120e0a`,
                border: `1px solid ${themeColors.accent}33`,
                boxShadow: `0 8px 32px rgba(0,0,0,0.5)`,
            }}
        >
            {/* ── BACKGROUND LAYER (parallax: slow) ── */}
            <div className="absolute inset-0 transition-transform duration-300 ease-out" style={layerOffset("bg")}>
                {/* Wall — tilemap texture */}
                <div className="absolute inset-x-0 top-0 h-[55%]" style={{
                    backgroundColor: themeColors.bg,
                }} />
                {/* Wall darkening overlay for depth */}
                <div className="absolute inset-x-0 top-0 h-[55%] bg-gradient-to-b from-black/30 to-transparent pointer-events-none" />
                {/* Back wall line */}
                <div className="absolute inset-x-0" style={{ top: "35%", height: "2px", background: `linear-gradient(90deg, transparent, ${themeColors.accent}15, transparent)` }} />
                {/* Background elements */}
                {elements.filter(e => e.layer === "bg").map((el) => (
                    <div
                        key={el.label}
                        className="absolute transition-transform duration-300 hover:scale-105"
                        style={{ left: `${el.x}%`, top: `${el.y}%`, transform: "translate(-50%, -100%)" }}
                    >
                        <span className="text-3xl block" style={{ opacity: 0.55, filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.4))" }}>{el.emoji}</span>
                        <span className="text-[7px] text-[var(--color-rune-dim)] opacity-40 block text-center mt-0.5">{el.label}</span>
                    </div>
                ))}
            </div>

            {/* ── MIDGROUND LAYER (parallax: none — characters + furniture) ── */}
            <div className="absolute inset-0">
                {/* Floor — tilemap texture */}
                <div className="absolute inset-x-0 bottom-0 h-[45%]" style={{
                    backgroundColor: themeColors.floor,
                }} />
                {/* Floor depth gradient */}
                <div className="absolute inset-x-0 bottom-0 h-[45%] bg-gradient-to-t from-black/20 to-transparent pointer-events-none" />
                {/* Floor/wall boundary */}
                <div className="absolute inset-x-0" style={{
                    top: "55%", height: 3,
                    background: `linear-gradient(90deg, transparent 5%, ${themeColors.accent}25 20%, ${themeColors.accent}40 50%, ${themeColors.accent}25 80%, transparent 95%)`,
                    boxShadow: `0 2px 10px ${themeColors.accent}20`
                }} />

                {/* Mid-layer elements (furniture with sprites) */}
                {elements.filter(e => e.layer === "mid").map((el) => (
                    <div
                        key={el.label}
                        className="absolute transition-transform duration-300 hover:scale-110 z-[5]"
                        style={{ left: `${el.x}%`, top: `${el.y}%`, transform: "translate(-50%, -100%)" }}
                    >
                        <span className="text-4xl block" style={{ opacity: 0.75, filter: "drop-shadow(0 3px 8px rgba(0,0,0,0.4))" }}>{el.emoji}</span>
                        <span className="text-[7px] text-[var(--color-rune-dim)] opacity-50 block text-center mt-0.5">{el.label}</span>
                    </div>
                ))}

                {/* Agents — ALL rendered through GuildHallAgent with pixel sprites */}
                {agents.map((agent: GuildAgent, idx: number) => {
                    const isCompanion = (agent as any).type === "companion";
                    const zone = isCompanion
                        ? { x: 72, y: 85 }
                        : ACTIVITY_ZONES[(agent.activity as Activity)] || ACTIVITY_ZONES.idle;
                    const offset = idx * 3;

                    return (
                        <GuildHallAgent
                            key={agent.name}
                            name={agent.name}
                            avatar={{ style: isCompanion ? undefined : (localStorage.getItem("fireside_agent_style") || "analytical"), ...(({ style: _s, ...rest }) => rest)(agent.avatar as any) }}
                            activity={agent.activity}
                            status={agent.status}
                            taskLabel={agent.taskLabel ?? undefined}
                            position={{ x: zone.x + (isCompanion ? 0 : offset), y: zone.y }}
                            theme={theme}
                            species={isCompanion ? ((agent as any).species || localStorage.getItem("fireside_companion_species") || "fox") : undefined}
                            onClick={() => { }}
                            onDoubleClick={() => !isCompanion ? router.push(`/agents/${agent.name}`) : undefined}
                        />
                    );
                })}
            </div>

            {/* ── FOREGROUND LAYER (parallax: fast — particles + effects) ── */}
            <div className="absolute inset-0 pointer-events-none z-10 transition-transform duration-300 ease-out" style={layerOffset("fg")}>
                {/* Foreground elements */}
                {elements.filter(e => e.layer === "fg").map((el) => (
                    <div
                        key={el.label}
                        className="absolute"
                        style={{ left: `${el.x}%`, top: `${el.y}%`, transform: "translate(-50%, -100%)" }}
                    >
                        <span className="text-4xl block" style={{ opacity: 0.8, filter: "drop-shadow(0 4px 10px rgba(0,0,0,0.5))" }}>{el.emoji}</span>
                    </div>
                ))}

                {/* F7: Fire embers rising */}
                {FIRE_EMBERS.map(e => (
                    <div
                        key={e.id}
                        className="absolute rounded-full"
                        style={{
                            left: `${e.left}%`,
                            bottom: "15%",
                            width: e.size,
                            height: e.size,
                            background: "#f59e0b",
                            boxShadow: "0 0 4px #f59e0b, 0 0 8px rgba(245,158,11,0.5)",
                            animation: `emberRise ${e.duration}s ease-out infinite`,
                            animationDelay: `${e.delay}s`,
                        }}
                    />
                ))}

                {/* Dust motes in light rays */}
                {DUST_PARTICLES.map(d => (
                    <div
                        key={d.id}
                        className="absolute rounded-full bg-white/15 blur-[0.5px]"
                        style={{
                            left: `${d.left}%`,
                            top: `${d.top}%`,
                            width: d.size,
                            height: d.size,
                            animation: `dustFloat ${d.duration}s ease-in-out infinite`,
                            animationDelay: `${d.delay}s`,
                        }}
                    />
                ))}
            </div>

            {/* Fire glow */}
            <div className="absolute pointer-events-none z-[3]" style={{
                left: "80%", top: "60%",
                width: 250, height: 250,
                transform: "translate(-50%, -50%)",
                background: `radial-gradient(circle, ${themeColors.accent}40 0%, ${themeColors.accent}15 30%, transparent 65%)`,
                animation: "pulse 3s ease-in-out infinite",
                mixBlendMode: "screen"
            }} />

            {/* Deep vignette */}
            <div className="absolute inset-0 pointer-events-none z-20" style={{
                background: "radial-gradient(ellipse at 50% 50%, transparent 30%, rgba(0,0,0,0.7) 100%)"
            }} />

            {/* Theme watermark */}
            <div className="absolute bottom-2 right-3 text-[10px] text-[var(--color-rune-dim)] opacity-25 uppercase tracking-[0.3em] z-30">
                {theme}
            </div>

            {/* Ember + Dust keyframes */}
            <style>{`
                @keyframes emberRise {
                    0% { transform: translateY(0) scale(1); opacity: 0.9; }
                    50% { transform: translateY(-80px) translateX(${Math.random() > 0.5 ? '' : '-'}8px) scale(0.6); opacity: 0.6; }
                    100% { transform: translateY(-160px) scale(0.2); opacity: 0; }
                }
                @keyframes dustFloat {
                    0%, 100% { transform: translate(0, 0); opacity: 0.2; }
                    25% { transform: translate(5px, -3px); opacity: 0.4; }
                    50% { transform: translate(-3px, 2px); opacity: 0.15; }
                    75% { transform: translate(2px, -5px); opacity: 0.35; }
                }
            `}</style>
        </div>
    );
}


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
    idle: { x: 80, y: 85 },   // lounge
    sleeping: { x: 85, y: 90 },   // far corner
    crucible: { x: 25, y: 55 },   // forge/cauldron
    chatting: { x: 55, y: 75 },   // center stage
};

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

// Fallback mock agents when API is unavailable
const FALLBACK_AGENTS = [
    {
        name: "Atlas",
        avatar: { style: "pixel" as const, ...STYLE_AVATARS.analytical },
        activity: "idle" as Activity, status: "online" as const, taskLabel: null as string | null, type: "ai" as const,
    },
];

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
    const themeColors = THEME_COLORS[theme] || THEME_COLORS.valhalla;
    const elements = THEME_ELEMENTS[theme] || THEME_ELEMENTS.valhalla;
    const [agents, setAgents] = useState(FALLBACK_AGENTS);

    // Sprint 10: Fetch real agent data
    useEffect(() => {
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
                background: `linear-gradient(180deg, ${themeColors.bg} 0%, ${themeColors.floor} 60%, ${themeColors.floor} 100%)`,
                border: `1px solid ${themeColors.accent}33`,
            }}
        >
            {/* Floor line */}
            <div
                className="absolute inset-x-0"
                style={{ top: "45%", height: "1px", background: `${themeColors.accent}22` }}
            />

            {/* Theme elements (furniture/objects) */}
            {elements.map((el) => (
                <div
                    key={el.label}
                    className="absolute"
                    style={{ left: `${el.x}%`, top: `${el.y}%`, transform: "translate(-50%, -50%)" }}
                >
                    <div className="text-center opacity-40">
                        <span className="text-2xl block">{el.emoji}</span>
                        <span className="text-[8px] text-[var(--color-rune-dim)]">{el.label}</span>
                    </div>
                </div>
            ))}

            {/* Agents — Sprint 10: AI agent at activity zone, companion near fire */}
            {agents.map((agent, idx) => {
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
                                taskLabel={agent.taskLabel}
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


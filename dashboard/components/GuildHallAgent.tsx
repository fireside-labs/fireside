"use client";

/**
 * 🎮 GuildHallAgent — Sprint 18 Upgrade.
 *
 * Now renders actual pixel art sprites instead of SVG avatars.
 * Includes Kairosoft-style status effect overlays.
 */

import SpriteCharacter, { AGENT_SHEETS, COMPANION_SHEETS } from "@/components/SpriteCharacter";
import type { SpriteAction } from "@/components/SpriteCharacter";
import StatusOverlay from "@/components/StatusOverlay";
import type { StatusEffect } from "@/components/StatusOverlay";

type Activity = "writing" | "researching" | "building" | "reviewing" | "debating" | "running_task" | "idle" | "sleeping" | "crucible" | "chatting";

interface GuildHallAgentProps {
    name: string;
    avatar: { style?: string; outfit?: string; [key: string]: unknown };
    activity: Activity;
    status: "online" | "busy" | "offline" | "hurt";
    taskLabel?: string;
    progress?: number;
    position: { x: number; y: number };
    theme: string;
    onClick?: () => void;
    onDoubleClick?: () => void;
    /** Optional companion species (renders companion sprite instead) */
    species?: string;
    /** Backend-driven status effect */
    statusEffect?: StatusEffect;
}

// Map activity → sprite action
const ACTIVITY_TO_ACTION: Record<Activity, SpriteAction> = {
    writing: "work",
    researching: "work",
    building: "work",
    reviewing: "work",
    debating: "chat",
    running_task: "work",
    idle: "idle",
    sleeping: "sleep",
    crucible: "work",
    chatting: "chat",
};

const ACTIVITY_LABELS: Record<Activity, Record<string, string>> = {
    writing: { valhalla: "Inscribing runes", office: "Writing at desk", space: "Logging data", cozy: "Writing on couch", dungeon: "Carving runes" },
    researching: { valhalla: "Consulting scrolls", office: "Browsing files", space: "Scanning hologram", cozy: "Reading a book", dungeon: "Searching chests" },
    building: { valhalla: "Forging at anvil", office: "At the whiteboard", space: "Welding hull", cozy: "Fixing at kitchen table", dungeon: "Crafting armor" },
    reviewing: { valhalla: "Studying runes", office: "In meeting room", space: "Analyzing scans", cozy: "On the couch with laptop", dungeon: "Inspecting loot" },
    debating: { valhalla: "Arguing in hall", office: "In heated meeting", space: "Bridge debate", cozy: "Kitchen discussion", dungeon: "Dueling words" },
    running_task: { valhalla: "At the war table", office: "Working hard", space: "At the console", cozy: "In the zone", dungeon: "On a quest" },
    idle: { valhalla: "Drinking mead", office: "Coffee break", space: "Zero-G floating", cozy: "Napping", dungeon: "Campfire rest" },
    sleeping: { valhalla: "Dreaming of glory", office: "Out for the night", space: "In cryo-sleep", cozy: "Under the blanket", dungeon: "Resting at camp" },
    crucible: { valhalla: "Testing at the forge", office: "Running tests", space: "Stress testing", cozy: "Experimenting", dungeon: "At the cauldron" },
    chatting: { valhalla: "Speaking to you", office: "On a call", space: "Comms open", cozy: "Chatting", dungeon: "Tavern talk" },
};

const HURT_LABELS: Record<string, string> = {
    valhalla: "Wounded in battle",
    office: "Out sick — paper cut",
    space: "Suit malfunction",
    cozy: "Under the weather",
    dungeon: "Knocked out — HP: 0",
};

export default function GuildHallAgent({
    name,
    avatar,
    activity,
    status,
    taskLabel,
    progress,
    position,
    theme,
    onClick,
    onDoubleClick,
    species,
    statusEffect,
}: GuildHallAgentProps) {
    const isHurt = status === "hurt";
    const label = isHurt
        ? HURT_LABELS[theme] || "Wounded"
        : ACTIVITY_LABELS[activity]?.[theme] || activity;

    const spriteAction = ACTIVITY_TO_ACTION[activity] || "idle";

    // Determine which sprite sheet to use
    const agentStyle = (avatar.style as string) || "analytical";
    const isCompanion = !!species;
    const sheet = isCompanion
        ? COMPANION_SHEETS[species] || COMPANION_SHEETS.fox
        : AGENT_SHEETS[agentStyle] || AGENT_SHEETS.analytical;

    const scale = isCompanion ? 2 : 3;

    // Map status to effect
    const effectiveStatus: StatusEffect = statusEffect
        || (isHurt ? "burned_out" : null)
        || (activity === "sleeping" ? "sleeping" : null)
        || (activity === "running_task" ? "on_a_roll" : null)
        || (activity === "chatting" ? "lightbulb" : null);

    return (
        <div
            className="absolute cursor-pointer group"
            style={{
                left: `${position.x}%`,
                top: `${position.y}%`,
                transform: "translate(-50%, -100%)",
                transition: "left 0.7s ease-in-out, top 0.7s ease-in-out",
            }}
            onClick={onClick}
            onDoubleClick={onDoubleClick}
        >
            {/* Status Effect Overlay */}
            <div className="relative">
                <StatusOverlay status={effectiveStatus} size={isCompanion ? 16 : 20} />

                {/* Pixel Art Sprite */}
                <div style={{ opacity: isHurt ? 0.5 : 1, filter: isHurt ? "saturate(0.3)" : undefined }}>
                    <SpriteCharacter
                        sheet={sheet}
                        action={spriteAction}
                        scale={scale}
                    />
                </div>
            </div>

            {/* Name plate */}
            <div className="text-center mt-1">
                <span className="text-[10px] text-white font-bold px-2 py-0.5 rounded-md bg-black/60 capitalize tracking-wide border border-white/10">
                    {name}
                </span>
            </div>

            {/* Progress bar (for running tasks) */}
            {progress !== undefined && !isHurt && (
                <div className="w-16 h-1.5 rounded-full bg-black/40 mt-1 mx-auto overflow-hidden">
                    <div
                        className="h-full rounded-full bg-[var(--color-neon)] transition-all duration-500"
                        style={{ width: `${progress}%`, boxShadow: "0 0 6px rgba(245,158,11,0.5)" }}
                    />
                </div>
            )}

            {/* Hover tooltip — premium glass panel */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-50">
                <div className="glass-card px-4 py-3 text-center whitespace-nowrap" style={{ minWidth: 120 }}>
                    <p className="text-xs text-white font-bold capitalize tracking-tight">{name}</p>
                    <p className="text-[10px] text-[var(--color-rune-dim)] mt-0.5">{label}</p>
                    {taskLabel && !isHurt && (
                        <p className="text-[10px] text-[var(--color-neon)] mt-1 font-medium">{taskLabel}</p>
                    )}
                </div>
            </div>
        </div>
    );
}

export type { Activity };

"use client";

import AvatarSprite from "@/components/AvatarSprite";
import type { AvatarConfig } from "@/components/AvatarSprite";

type Activity = "writing" | "researching" | "building" | "reviewing" | "debating" | "running_task" | "idle" | "sleeping" | "crucible" | "chatting";

interface GuildHallAgentProps {
    name: string;
    avatar: AvatarConfig;
    activity: Activity;
    status: "online" | "busy" | "offline" | "hurt";
    taskLabel?: string;
    progress?: number;
    position: { x: number; y: number };
    theme: string;
    onClick?: () => void;
    onDoubleClick?: () => void;
}

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

const ACTIVITY_ANIMATIONS: Record<Activity, string> = {
    writing: "animate-[bobble_3s_ease-in-out_infinite]",
    researching: "animate-[sway_4s_ease-in-out_infinite]",
    building: "animate-[hammer_1s_ease-in-out_infinite]",
    reviewing: "",
    debating: "animate-[shake_0.5s_ease-in-out_infinite]",
    running_task: "animate-[pulse_2s_ease-in-out_infinite]",
    idle: "",
    sleeping: "animate-[breathe_4s_ease-in-out_infinite]",
    crucible: "animate-[glow_2s_ease-in-out_infinite]",
    chatting: "animate-[bobble_2s_ease-in-out_infinite]",
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
}: GuildHallAgentProps) {
    const isHurt = status === "hurt";
    const label = isHurt
        ? HURT_LABELS[theme] || "Wounded"
        : ACTIVITY_LABELS[activity]?.[theme] || activity;
    const animation = isHurt ? "animate-[wobble_2s_ease-in-out_infinite]" : ACTIVITY_ANIMATIONS[activity];

    return (
        <div
            className={`absolute cursor-pointer group transition-all duration-700 ${animation}`}
            style={{ left: `${position.x}%`, top: `${position.y}%`, transform: "translate(-50%, -100%)" }}
            onClick={onClick}
            onDoubleClick={onDoubleClick}
        >
            {/* Avatar */}
            <AvatarSprite config={avatar} size={64} status={status} />

            {/* Name plate */}
            <div className="text-center mt-1">
                <span className="text-[10px] text-white font-bold px-1.5 py-0.5 rounded bg-black/50 capitalize">{name}</span>
            </div>

            {/* Sleeping ZZZ */}
            {activity === "sleeping" && !isHurt && (
                <div className="absolute -top-3 -right-2 text-sm animate-[float_2s_ease-in-out_infinite]">💤</div>
            )}

            {/* Hurt bandage icon */}
            {isHurt && (
                <div className="absolute -top-2 -right-1 text-sm animate-[pulse_1.5s_ease-in-out_infinite]">🩹</div>
            )}

            {/* Progress bar (for running tasks) */}
            {progress !== undefined && !isHurt && (
                <div className="w-14 h-1 rounded-full bg-black/30 mt-0.5 mx-auto">
                    <div className="h-1 rounded-full bg-[var(--color-neon)]" style={{ width: `${progress}%` }} />
                </div>
            )}

            {/* Hover tooltip */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                <div className="glass-card px-3 py-2 text-center whitespace-nowrap">
                    <p className="text-xs text-white font-semibold capitalize">{name}</p>
                    <p className="text-[10px] text-[var(--color-rune-dim)]">{label}</p>
                    {taskLabel && !isHurt && (
                        <p className="text-[10px] text-[var(--color-neon)] mt-0.5">{taskLabel}</p>
                    )}
                </div>
            </div>
        </div>
    );
}

export type { Activity };

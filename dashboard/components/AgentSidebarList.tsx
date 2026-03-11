"use client";

import AvatarSprite from "@/components/AvatarSprite";
import Link from "next/link";
import type { AvatarConfig } from "@/components/AvatarSprite";

interface AgentSidebarItem {
    name: string;
    avatar: AvatarConfig;
    status: "online" | "busy" | "offline" | "hurt";
    currentTask?: string;
    progress?: number; // 0-100
}

const AGENTS: AgentSidebarItem[] = [
    {
        name: "Thor",
        avatar: { style: "pixel", hairStyle: 4, hairColor: "#8B4513", skinTone: "#F5CBA7", outfit: "warrior", accessory: "none" },
        status: "online", currentTask: "Building...", progress: 65,
    },
    {
        name: "Freya",
        avatar: { style: "pixel", hairStyle: 2, hairColor: "#F4D03F", skinTone: "#FAD7A0", outfit: "artist", accessory: "glasses" },
        status: "busy", currentTask: "Designing UI",
    },
    {
        name: "Heimdall",
        avatar: { style: "pixel", hairStyle: 0, hairColor: "#1A1A2E", skinTone: "#D4A574", outfit: "guardian", accessory: "none" },
        status: "online", currentTask: "Watching",
    },
    {
        name: "Valkyrie",
        avatar: { style: "pixel", hairStyle: 3, hairColor: "#C0392B", skinTone: "#FBEEE6", outfit: "crown", accessory: "none" },
        status: "online", currentTask: "Writing docs",
    },
];

export default function AgentSidebarList() {
    return (
        <div className="space-y-1">
            {AGENTS.map((agent) => (
                <Link
                    key={agent.name}
                    href={`/agents/${agent.name.toLowerCase()}`}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-[var(--color-glass-hover)] transition-colors group"
                >
                    <AvatarSprite config={agent.avatar} size={28} status={agent.status} />
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                            <span className="text-xs text-white font-medium truncate">{agent.name}</span>
                        </div>
                        {agent.currentTask && (
                            <div className="flex items-center gap-1.5">
                                <span className="text-[10px] text-[var(--color-rune-dim)] truncate">
                                    {agent.status === "hurt" ? "🩹 Recovering..." : agent.currentTask}
                                </span>
                                {agent.progress !== undefined && (
                                    <div className="w-12 h-1 rounded-full bg-[var(--color-glass)] flex-shrink-0">
                                        <div
                                            className="h-1 rounded-full bg-[var(--color-neon)]"
                                            style={{ width: `${agent.progress}%` }}
                                        />
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </Link>
            ))}
        </div>
    );
}

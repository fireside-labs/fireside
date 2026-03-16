"use client";

import AvatarSprite from "@/components/AvatarSprite";
import Link from "next/link";
import type { AvatarConfig } from "@/components/AvatarSprite";
import { useEffect, useState } from "react";

interface AgentSidebarItem {
    name: string;
    avatar: AvatarConfig;
    status: "online" | "busy" | "offline" | "hurt";
    currentTask?: string;
    progress?: number;
}

const DEFAULT_AVATAR: AvatarConfig = {
    style: "pixel", hairStyle: 1, hairColor: "#6B7280",
    skinTone: "#D4A574", outfit: "scholar", accessory: "none",
};

function getAgentsFromConfig(): AgentSidebarItem[] {
    if (typeof window === "undefined") return [];

    try {
        // Read agent name from onboarding data in localStorage
        const onboarding = localStorage.getItem("fireside_onboarding");
        if (onboarding) {
            const data = JSON.parse(onboarding);
            const agentName = data.agent?.name || data.agent_name || "Atlas";
            return [{
                name: agentName,
                avatar: DEFAULT_AVATAR,
                status: "online",
                currentTask: "Ready",
            }];
        }

        // Fallback: check companion state
        const companion = localStorage.getItem("fireside_companion");
        if (companion) {
            const data = JSON.parse(companion);
            return [{
                name: data.agent?.name || "Atlas",
                avatar: DEFAULT_AVATAR,
                status: "online",
                currentTask: "Ready",
            }];
        }
    } catch {
        // ignore parse errors
    }

    // No config found — show empty state
    return [];
}

export default function AgentSidebarList() {
    const [agents, setAgents] = useState<AgentSidebarItem[]>([]);

    useEffect(() => {
        setAgents(getAgentsFromConfig());
    }, []);

    if (agents.length === 0) {
        return (
            <div className="px-3 py-2">
                <p className="text-[10px] text-[var(--color-rune-dim)] italic">
                    No agents configured yet
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-1">
            {agents.map((agent) => (
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

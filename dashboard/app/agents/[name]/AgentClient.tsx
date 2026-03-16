"use client";

import AgentProfile from "@/components/AgentProfile";
import { useParams } from "next/navigation";

// Mock data — would come from GET /api/v1/agents/{name}/profile
const AGENT_DATA: Record<string, {
    level: number; xp: number; xpToNext: number;
    avatar: { style: "pixel" | "minimal" | "emoji"; emoji?: string; hairStyle: number; hairColor: string; skinTone: string; outfit: "warrior" | "developer" | "artist" | "guardian" | "scholar" | "crown"; accessory: "none" | "glasses" | "headphones" | "hat" };
    stats: { tasks_completed: number; knowledge_count: number; accuracy: number; crucible_survival: number; streak: number; skills: Record<string, number> };
    personality: Record<string, number>;
    achievements: { id: string; name: string; desc: string; earned: boolean; date?: string }[];
    status: "online" | "busy" | "offline" | "hurt";
}> = {
    thor: {
        level: 14, xp: 2840, xpToNext: 3500,
        avatar: { style: "pixel", hairStyle: 4, hairColor: "#8B4513", skinTone: "#F5CBA7", outfit: "warrior", accessory: "none" },
        stats: { tasks_completed: 47, knowledge_count: 247, accuracy: 0.94, crucible_survival: 0.89, streak: 12, skills: { python: 5, architecture: 4, testing: 4, writing: 3, devops: 3 } },
        personality: { creative_precise: 0.3, verbose_concise: 0.4, bold_cautious: 0.8, warm_formal: 0.5 },
        achievements: [
            { id: "streak_10", name: "Unstoppable", desc: "10 tasks without failure", earned: true, date: "Mar 8" },
            { id: "crucible_100", name: "Forged in Fire", desc: "100% knowledge check score", earned: false },
            { id: "debate_win_3", name: "Silver Tongue", desc: "Won 3 Socratic debates", earned: true, date: "Mar 6" },
            { id: "tasks_50", name: "Workhorse", desc: "50 tasks completed", earned: false },
            { id: "first_task", name: "First Steps", desc: "Completed first task", earned: true, date: "Feb 20" },
            { id: "night_owl", name: "Night Owl", desc: "Learned something overnight", earned: true, date: "Mar 2" },
        ],
        status: "online",
    },
    freya: {
        level: 11, xp: 1680, xpToNext: 2000,
        avatar: { style: "pixel", hairStyle: 2, hairColor: "#F4D03F", skinTone: "#FAD7A0", outfit: "artist", accessory: "glasses" },
        stats: { tasks_completed: 32, knowledge_count: 189, accuracy: 0.91, crucible_survival: 0.85, streak: 5, skills: { design: 5, css: 5, react: 4, ux: 4, writing: 3 } },
        personality: { creative_precise: 0.8, verbose_concise: 0.5, bold_cautious: 0.6, warm_formal: 0.8 },
        achievements: [
            { id: "streak_10", name: "Unstoppable", desc: "10 tasks without failure", earned: false },
            { id: "first_task", name: "First Steps", desc: "Completed first task", earned: true, date: "Feb 22" },
            { id: "level_10", name: "Double Digits", desc: "Reached level 10", earned: true, date: "Mar 5" },
        ],
        status: "busy",
    },
    heimdall: {
        level: 9, xp: 1200, xpToNext: 1500,
        avatar: { style: "pixel", hairStyle: 0, hairColor: "#1A1A2E", skinTone: "#D4A574", outfit: "guardian", accessory: "none" },
        stats: { tasks_completed: 28, knowledge_count: 156, accuracy: 0.97, crucible_survival: 0.95, streak: 8, skills: { security: 5, auditing: 5, testing: 4, python: 3, docs: 3 } },
        personality: { creative_precise: 0.15, verbose_concise: 0.3, bold_cautious: 0.2, warm_formal: 0.25 },
        achievements: [
            { id: "crucible_100", name: "Forged in Fire", desc: "100% knowledge check score", earned: true, date: "Mar 7" },
            { id: "first_task", name: "First Steps", desc: "Completed first task", earned: true, date: "Feb 23" },
        ],
        status: "online",
    },
    valkyrie: {
        level: 12, xp: 2100, xpToNext: 2500,
        avatar: { style: "pixel", hairStyle: 3, hairColor: "#C0392B", skinTone: "#FBEEE6", outfit: "crown", accessory: "none" },
        stats: { tasks_completed: 38, knowledge_count: 210, accuracy: 0.96, crucible_survival: 0.92, streak: 15, skills: { writing: 5, ux: 5, strategy: 4, research: 4, testing: 3 } },
        personality: { creative_precise: 0.6, verbose_concise: 0.7, bold_cautious: 0.5, warm_formal: 0.65 },
        achievements: [
            { id: "streak_10", name: "Unstoppable", desc: "10 tasks without failure", earned: true, date: "Mar 9" },
            { id: "debate_win_3", name: "Silver Tongue", desc: "Won 3 Socratic debates", earned: true, date: "Mar 7" },
            { id: "first_task", name: "First Steps", desc: "Completed first task", earned: true, date: "Feb 21" },
            { id: "team_player", name: "Team Player", desc: "Collaborated on 10 tasks", earned: true, date: "Mar 4" },
        ],
        status: "online",
    },
};

export default function AgentClient({ agentName }: { agentName: string }) {
    const data = AGENT_DATA[agentName.toLowerCase()];

    if (!data) {
        return (
            <div className="max-w-2xl mx-auto text-center py-16">
                <span className="text-5xl block mb-4">🔍</span>
                <h1 className="text-xl text-white font-bold mb-2">Agent not found</h1>
                <p className="text-sm text-[var(--color-rune-dim)]">
                    No agent named &quot;{agentName}&quot; in this mesh.
                </p>
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto">
            <AgentProfile
                name={agentName}
                level={data.level}
                xp={data.xp}
                xpToNext={data.xpToNext}
                avatar={data.avatar}
                stats={data.stats}
                personality={data.personality}
                achievements={data.achievements}
                status={data.status}
                onPersonalityChange={(id, val) => console.log(`Personality ${id} → ${val}`)}
            />
        </div>
    );
}

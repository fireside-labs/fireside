"use client";

import { useState } from "react";
import GuildHall from "@/components/GuildHall";
import ThemePicker from "@/components/ThemePicker";

export default function GuildHallPage() {
    const [theme, setTheme] = useState("valhalla");

    return (
        <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <span>🏰</span> Guild Hall
                    </h1>
                    <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                        Watch your AI team work in real time. Double-click an agent to view their profile.
                    </p>
                </div>
            </div>

            {/* Guild Hall Scene */}
            <GuildHall theme={theme} />

            {/* Theme Picker */}
            <div className="mt-4 flex items-center gap-3">
                <span className="text-xs text-[var(--color-rune-dim)]">Theme:</span>
                <ThemePicker selected={theme} onSelect={setTheme} />
            </div>

            {/* Legend */}
            <div className="mt-4 glass-card p-4">
                <p className="text-xs text-[var(--color-rune-dim)] mb-2 font-semibold">What they&apos;re doing:</p>
                <div className="flex flex-wrap gap-x-6 gap-y-1 text-[10px] text-[var(--color-rune-dim)]">
                    <span>📝 Writing</span>
                    <span>📚 Researching</span>
                    <span>🔨 Building</span>
                    <span>🔍 Reviewing</span>
                    <span>💬 Chatting</span>
                    <span>🗣️ Debating</span>
                    <span>⚡ Running Task</span>
                    <span>🧪 Testing</span>
                    <span>😴 Sleeping</span>
                    <span>☕ Idle</span>
                    <span>🩹 Wounded</span>
                </div>
            </div>
        </div>
    );
}

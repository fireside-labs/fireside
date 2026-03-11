"use client";

import { useState, useEffect } from "react";

interface AchievementToastProps {
    agentName: string;
    achievementName: string;
    achievementDesc: string;
    emoji?: string;
    levelUp?: { from: number; to: number };
    onDismiss: () => void;
}

export default function AchievementToast({
    agentName,
    achievementName,
    achievementDesc,
    emoji = "🏆",
    levelUp,
    onDismiss,
}: AchievementToastProps) {
    const [visible, setVisible] = useState(false);
    const [hiding, setHiding] = useState(false);

    useEffect(() => {
        // Slide in
        requestAnimationFrame(() => setVisible(true));
        // Auto-dismiss after 5s
        const hideTimer = setTimeout(() => setHiding(true), 4500);
        const removeTimer = setTimeout(onDismiss, 5000);
        return () => {
            clearTimeout(hideTimer);
            clearTimeout(removeTimer);
        };
    }, [onDismiss]);

    return (
        <div
            className="fixed top-6 right-6 z-[300] transition-all duration-500"
            style={{
                transform: visible && !hiding ? "translateX(0)" : "translateX(120%)",
                opacity: hiding ? 0 : 1,
            }}
        >
            <div
                className="glass-card p-4 pr-6 min-w-[320px]"
                style={{
                    borderColor: "var(--color-neon)",
                    borderWidth: 2,
                    boxShadow: "0 0 30px var(--color-neon-glow-strong), 0 4px 20px rgba(0,0,0,0.4)",
                }}
            >
                <div className="flex items-start gap-3">
                    <span className="text-3xl">{emoji}</span>
                    <div>
                        <p className="text-sm text-white font-semibold">
                            {agentName} earned &quot;{achievementName}&quot;!
                        </p>
                        <p className="text-xs text-[var(--color-rune-dim)] mt-0.5">{achievementDesc}</p>
                        {levelUp && (
                            <p className="text-xs text-[var(--color-neon)] mt-1 font-bold">
                                ⬆️ Level {levelUp.from} → Level {levelUp.to}
                            </p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

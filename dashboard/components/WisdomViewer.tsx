"use client";

import type { WisdomPrompt } from "@/lib/api";

export default function WisdomViewer({
    wisdom,
    onRebuild,
}: {
    wisdom: WisdomPrompt;
    onRebuild: () => void;
}) {
    const lastRebuilt = new Date(wisdom.last_rebuilt).toLocaleString();

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h3 className="text-white font-semibold">💎 Philosopher&apos;s Stone</h3>
                    <p className="text-xs text-[var(--color-rune-dim)] mt-0.5">
                        {wisdom.section_count} sections · {wisdom.word_count} words · Last rebuilt {lastRebuilt}
                    </p>
                </div>
                <button onClick={onRebuild} className="btn-neon text-xs px-3 py-1.5">
                    Rebuild Now
                </button>
            </div>

            {/* Rendered wisdom prompt */}
            <div className="text-sm text-[var(--color-rune)] space-y-3 max-h-64 overflow-y-auto">
                {wisdom.content.split("\n").map((line, i) => {
                    if (line.startsWith("## "))
                        return <h2 key={i} className="text-lg font-bold text-white mt-3">{line.replace("## ", "")}</h2>;
                    if (line.startsWith("### "))
                        return <h3 key={i} className="text-sm font-semibold text-[var(--color-neon)] mt-2">{line.replace("### ", "")}</h3>;
                    if (line.startsWith("- "))
                        return <p key={i} className="text-xs pl-3 relative"><span className="absolute left-0">•</span>{line.replace("- ", "")}</p>;
                    if (line.trim() === "") return <div key={i} className="h-1" />;
                    return <p key={i} className="text-xs">{line}</p>;
                })}
            </div>
        </div>
    );
}

"use client";

export default function ConsensusMeter({ value, max }: { value: number; max?: number }) {
    const pct = Math.min(value * 100, 100);
    const threshold = (max || 0.7) * 100;
    const passed = pct >= threshold;

    return (
        <div>
            <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-[var(--color-rune-dim)]">Consensus</span>
                <span className="text-xs font-bold" style={{ color: passed ? "var(--color-neon)" : "var(--color-warning)" }}>
                    {Math.round(pct)}%
                </span>
            </div>
            <div className="h-2 rounded-full bg-[var(--color-void-lighter)] overflow-hidden relative">
                {/* Threshold marker */}
                <div
                    className="absolute top-0 bottom-0 w-px bg-[var(--color-rune-dim)]"
                    style={{ left: `${threshold}%` }}
                />
                {/* Fill */}
                <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                        width: `${pct}%`,
                        background: passed
                            ? "linear-gradient(90deg, var(--color-neon-dim), var(--color-neon))"
                            : "linear-gradient(90deg, var(--color-warning), #ffcc44)",
                    }}
                />
            </div>
            <p className="text-[10px] text-[var(--color-rune-dim)] mt-0.5">
                Threshold: {Math.round(threshold)}%
            </p>
        </div>
    );
}

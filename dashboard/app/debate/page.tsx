"use client";

export default function ComingSoonPage() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            <div className="glass-card p-12 max-w-md w-full relative overflow-hidden">
                {/* Background ambient glow */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--color-neon)] opacity-5 blur-3xl rounded-full translate-x-1/2 -translate-y-1/2" />

                <span className="text-6xl block mb-6 animate-[float_3s_ease-in-out_infinite]">🚧</span>
                <h1 className="text-2xl font-bold text-white mb-2 tracking-wide">Coming Soon</h1>
                <p className="text-sm text-[var(--color-rune-dim)] mb-8 leading-relaxed">
                    The architects of Valhalla are still constructing this chamber. Check back in a future update.
                </p>

                {/* Animated progress bar */}
                <div className="w-16 h-1 bg-[var(--color-glass-border)] mx-auto rounded-full overflow-hidden relative">
                    <div className="absolute top-0 left-0 w-full h-full bg-[var(--color-neon)] opacity-80 rounded-full animate-[wobble_2s_ease-in-out_infinite]" style={{ transformOrigin: "left" }} />
                </div>
            </div>
        </div>
    );
}

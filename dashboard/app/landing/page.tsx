"use client";

import Link from "next/link";

const FEATURES = [
    {
        emoji: "🔥",
        title: "Always by Your Side",
        desc: "Your AI companion runs on your computer. Always available. Always private. Always yours.",
    },
    {
        emoji: "🧠",
        title: "It Remembers You",
        desc: "Learns from every conversation. Remembers your preferences, projects, and writing style.",
    },
    {
        emoji: "🏰",
        title: "Guild Hall",
        desc: "Watch your AI team work in a 2D scene. 5 themes from Norse hall to space station.",
    },
    {
        emoji: "👤",
        title: "Agent Profiles",
        desc: "Level up your AI. Track stats, earn achievements, tune personality with sliders.",
    },
    {
        emoji: "🎤",
        title: "Voice Chat",
        desc: "Talk to your AI. Speech-to-text + text-to-speech. 5 voices. All processed locally.",
    },
    {
        emoji: "📱",
        title: "Chat from Your Phone",
        desc: "QR code to connect. Talk from anywhere through your home PC. PWA — no app store needed.",
    },
    {
        emoji: "🏪",
        title: "Marketplace",
        desc: "Community-built agents, themes, voices. Creators earn 70% of each sale.",
    },
    {
        emoji: "🔒",
        title: "Truly Private",
        desc: "Zero telemetry. No data leaves your network. Voice processed on-device. You own everything.",
    },
];

const STATS = [
    { value: "$0", label: "Inference Cost" },
    { value: "5MB", label: "Download Size" },
    { value: "45", label: "Letters/sec" },
    { value: "100%", label: "Private" },
];

export default function LandingPage() {
    return (
        <div className="min-h-screen" style={{ background: "var(--color-void)" }}>
            {/* Hero */}
            <div className="max-w-5xl mx-auto px-6 pt-16 pb-12 text-center">
                <div className="inline-block mb-4 px-4 py-1.5 rounded-full text-xs font-medium" style={{ background: "var(--color-neon-glow)", color: "var(--color-neon)", border: "1px solid rgba(0,255,136,0.15)" }}>
                    🔥 Now Available — Free Forever
                </div>
                <h1 className="text-5xl md:text-6xl font-bold text-white leading-tight mb-4">
                    Your AI companion,{" "}
                    <span style={{ color: "var(--color-neon)" }}>always by your side</span>
                </h1>
                <p className="text-lg text-[var(--color-rune)] max-w-2xl mx-auto mb-8">
                    Fireside is a private AI assistant that runs entirely on your hardware.
                    No cloud. No subscription. No data leaves your network. Ever.
                </p>
                <div className="flex justify-center gap-3 mb-12">
                    <Link href="/" className="btn-neon px-8 py-3 text-base font-semibold">
                        🔥 Start a Fireside →
                    </Link>
                    <Link href="/guildhall" className="px-8 py-3 text-base rounded-lg border border-[var(--color-glass-border)] text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)] transition-colors">
                        🏰 See Guild Hall
                    </Link>
                </div>

                {/* Stats bar */}
                <div className="flex justify-center gap-8 md:gap-16">
                    {STATS.map((s) => (
                        <div key={s.label} className="text-center">
                            <div className="text-2xl md:text-3xl font-bold text-white">{s.value}</div>
                            <div className="text-xs text-[var(--color-rune-dim)]">{s.label}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Features Grid */}
            <div className="max-w-5xl mx-auto px-6 py-12">
                <h2 className="text-2xl font-bold text-white text-center mb-2">Everything you need</h2>
                <p className="text-sm text-[var(--color-rune-dim)] text-center mb-8">
                    Built across 11 sprints. From raw terminal to your personal AI companion.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {FEATURES.map((f) => (
                        <div key={f.title} className="glass-card p-5 hover:scale-[1.02] transition-transform">
                            <span className="text-2xl block mb-2">{f.emoji}</span>
                            <h3 className="text-sm text-white font-semibold mb-1">{f.title}</h3>
                            <p className="text-xs text-[var(--color-rune-dim)] leading-relaxed">{f.desc}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* How it works */}
            <div className="max-w-3xl mx-auto px-6 py-12">
                <h2 className="text-2xl font-bold text-white text-center mb-8">How it works</h2>
                <div className="space-y-4">
                    {[
                        { step: "1", title: "Download", desc: "One command. 5MB. Mac, Windows, or Linux.", emoji: "⬇️" },
                        { step: "2", title: "Pick a brain", desc: "Choose an AI model that fits your hardware. Free local or bring-your-own cloud key.", emoji: "🧠" },
                        { step: "3", title: "Start a Fireside", desc: "Chat, assign tasks, customize personality. Your AI learns and remembers.", emoji: "🔥" },
                    ].map((s) => (
                        <div key={s.step} className="glass-card p-5 flex items-center gap-4">
                            <span className="text-3xl">{s.emoji}</span>
                            <div>
                                <h3 className="text-sm text-white font-semibold">{s.title}</h3>
                                <p className="text-xs text-[var(--color-rune-dim)]">{s.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Business model callout */}
            <div className="max-w-3xl mx-auto px-6 py-8">
                <div className="glass-card p-6 text-center" style={{ borderColor: "var(--color-neon)", borderWidth: 1 }}>
                    <h3 className="text-white font-bold text-lg mb-2">💡 Free forever. Really.</h3>
                    <p className="text-sm text-[var(--color-rune)] leading-relaxed">
                        Fireside runs on <strong className="text-white">your</strong> hardware — your MacBook, your gaming PC, your home server.
                        Our total infrastructure cost is ~$20/month. We make money from the community marketplace.
                        <strong className="text-white"> We never run a GPU. You never pay for inference.</strong>
                    </p>
                </div>
            </div>

            {/* CTA */}
            <div className="max-w-3xl mx-auto px-6 py-8 text-center">
                <h2 className="text-2xl font-bold text-white mb-3">Ready?</h2>
                <p className="text-sm text-[var(--color-rune-dim)] mb-6">
                    Your AI is waiting. No sign-up. No credit card. Just download and start talking.
                </p>
                <Link href="/" className="btn-neon px-10 py-3 text-base font-semibold inline-block">
                    🔥 Start a Fireside →
                </Link>
            </div>

            {/* Footer */}
            <div className="max-w-5xl mx-auto px-6 py-8 text-center border-t border-[var(--color-glass-border)]">
                <p className="text-sm text-white font-semibold mb-1">🔥 Fireside</p>
                <p className="text-xs text-[var(--color-rune-dim)]">
                    Your AI companion, always by your side · getfireside.ai
                </p>
                <p className="text-[10px] text-[var(--color-rune-dim)] mt-2 opacity-50">
                    Built with 🔥 by the Fireside team
                </p>
            </div>
        </div>
    );
}

"use client";

import Link from "next/link";

const FEATURES = [
    {
        emoji: "🧠",
        title: "Your Own AI",
        desc: "Runs on your computer. No cloud. No subscription. Your data stays yours.",
    },
    {
        emoji: "🏰",
        title: "Guild Hall",
        desc: "Watch your AI team work in a 2D scene. 5 swappable themes from Norse hall to space station.",
    },
    {
        emoji: "👤",
        title: "Agent Profiles",
        desc: "Level up your AI. Track stats, earn achievements, customize personality with sliders.",
    },
    {
        emoji: "🎤",
        title: "Voice Chat",
        desc: "Talk to your AI. Speech-to-text + text-to-speech. 5 voice options. All processed locally.",
    },
    {
        emoji: "📱",
        title: "Mobile App",
        desc: "Chat from your phone through your home PC. QR code to connect. Works anywhere.",
    },
    {
        emoji: "🏪",
        title: "Marketplace",
        desc: "Buy and sell agents, themes, voice packs. Creators earn 70% of each sale.",
    },
    {
        emoji: "🔒",
        title: "Private & Secure",
        desc: "Zero telemetry. No data leaves your network. Voice processed on-device. You own everything.",
    },
    {
        emoji: "💻",
        title: "Desktop App",
        desc: "One-click install. Mac, Windows, Linux. 5MB download. Auto-updates.",
    },
];

const PRICING = [
    {
        name: "Free",
        price: "$0",
        period: "forever",
        features: [
            "Unlimited AI chat",
            "1 local brain (7B model)",
            "Full personality customization",
            "Guild Hall (2 free themes)",
            "Basic agent profiles",
            "Telegram notifications",
        ],
        cta: "Download Free",
        highlighted: false,
    },
    {
        name: "Pro",
        price: "$9",
        period: "/month",
        features: [
            "Everything in Free",
            "All 5 Guild Hall themes",
            "Voice chat (5 voices)",
            "Mobile PWA access",
            "Priority brain downloads",
            "Premium avatar packs",
            "Community marketplace access",
        ],
        cta: "Start Free Trial",
        highlighted: true,
    },
    {
        name: "Enterprise",
        price: "$500",
        period: "/month",
        features: [
            "Everything in Pro",
            "Multi-user team support",
            "Custom agent training",
            "Priority support",
            "Custom integrations",
            "SLA guarantee",
            "On-prem deployment",
        ],
        cta: "Contact Sales",
        highlighted: false,
    },
];

const STATS = [
    { value: "0", label: "Inference Cost", suffix: "" },
    { value: "5", label: "MB Download", suffix: "MB" },
    { value: "45", label: "Letters/sec", suffix: "" },
    { value: "100%", label: "Private", suffix: "" },
];

export default function LandingPage() {
    return (
        <div className="min-h-screen" style={{ background: "var(--color-void)" }}>
            {/* Hero */}
            <div className="max-w-5xl mx-auto px-6 pt-16 pb-12 text-center">
                <div className="inline-block mb-4 px-4 py-1.5 rounded-full text-xs font-medium" style={{ background: "var(--color-neon-glow)", color: "var(--color-neon)", border: "1px solid rgba(0,255,136,0.15)" }}>
                    ✨ Now in Open Beta
                </div>
                <h1 className="text-5xl md:text-6xl font-bold text-white leading-tight mb-4">
                    Your AI runs on{" "}
                    <span style={{ color: "var(--color-neon)" }}>your computer</span>
                </h1>
                <p className="text-lg text-[var(--color-rune)] max-w-2xl mx-auto mb-8">
                    Valhalla is a private AI assistant that runs entirely on your hardware.
                    No cloud API keys. No monthly GPU bills. No data leaves your network. Ever.
                </p>
                <div className="flex justify-center gap-3 mb-12">
                    <Link href="/" className="btn-neon px-8 py-3 text-base font-semibold">
                        ⚡ Download Free
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
                    Built across 9 sprints. From raw terminal to consumer product.
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

            {/* Pricing */}
            <div className="max-w-4xl mx-auto px-6 py-12">
                <h2 className="text-2xl font-bold text-white text-center mb-2">Simple pricing</h2>
                <p className="text-sm text-[var(--color-rune-dim)] text-center mb-8">
                    You never pay for inference. Your hardware, your compute, your savings.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {PRICING.map((plan) => (
                        <div
                            key={plan.name}
                            className="glass-card p-6 flex flex-col"
                            style={{
                                borderColor: plan.highlighted ? "var(--color-neon)" : undefined,
                                borderWidth: plan.highlighted ? 2 : undefined,
                            }}
                        >
                            {plan.highlighted && (
                                <span className="text-[9px] px-2 py-0.5 rounded-full bg-[var(--color-neon-glow)] text-[var(--color-neon)] font-bold mb-3 self-start">
                                    MOST POPULAR
                                </span>
                            )}
                            <h3 className="text-lg text-white font-bold">{plan.name}</h3>
                            <div className="flex items-baseline gap-1 mt-1 mb-4">
                                <span className="text-3xl text-white font-bold">{plan.price}</span>
                                <span className="text-sm text-[var(--color-rune-dim)]">{plan.period}</span>
                            </div>
                            <ul className="space-y-2 flex-1 mb-5">
                                {plan.features.map((f) => (
                                    <li key={f} className="flex items-start gap-2 text-xs text-[var(--color-rune)]">
                                        <span className="text-[var(--color-neon)] mt-0.5">✓</span>
                                        {f}
                                    </li>
                                ))}
                            </ul>
                            <button
                                className={`w-full py-2.5 rounded-lg text-sm font-medium transition-colors ${plan.highlighted
                                        ? "btn-neon"
                                        : "border border-[var(--color-glass-border)] text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)]"
                                    }`}
                            >
                                {plan.cta}
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Business model callout */}
            <div className="max-w-3xl mx-auto px-6 py-8">
                <div className="glass-card p-6 text-center" style={{ borderColor: "var(--color-neon)", borderWidth: 1 }}>
                    <h3 className="text-white font-bold text-lg mb-2">💡 How is this possible?</h3>
                    <p className="text-sm text-[var(--color-rune)] leading-relaxed">
                        Traditional AI apps charge you for GPU time. Valhalla runs on <strong className="text-white">your</strong> hardware —
                        your MacBook, your gaming PC, your home server. Our total infrastructure cost is ~$20/month for CDN hosting.
                        We make money from the marketplace (30% cut on community sales) and premium customization.
                        <strong className="text-white"> We never run a GPU. Ever.</strong>
                    </p>
                </div>
            </div>

            {/* Footer */}
            <div className="max-w-5xl mx-auto px-6 py-8 text-center border-t border-[var(--color-glass-border)]">
                <p className="text-xs text-[var(--color-rune-dim)]">
                    Built with ⚡ by Odin · Thor · Freya · Heimdall · Valkyrie
                </p>
            </div>
        </div>
    );
}

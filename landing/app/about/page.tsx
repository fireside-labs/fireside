import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "About — Fireside",
    description: "The story behind Fireside. Built by a solo developer who believes your AI should get smarter every day it runs.",
};

export default function AboutPage() {
    return (
        <main className="bg-grid min-h-screen">
            {/* ─── NAV ─── */}
            <nav className="fixed top-0 w-full z-50 border-b border-[var(--color-border)] bg-[var(--color-background)]/85 backdrop-blur-xl">
                <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                    <a href="/" className="flex items-center gap-2.5">
                        <span className="text-xl">🔥</span>
                        <span className="font-[var(--font-display)] font-bold text-lg tracking-tight">
                            Fireside
                        </span>
                    </a>
                    <div className="hidden md:flex items-center gap-8 text-sm text-[var(--color-text-muted)]">
                        <a href="/#features" className="hover:text-[var(--color-foreground)] transition-colors">Features</a>
                        <a href="/docs" className="hover:text-[var(--color-foreground)] transition-colors">Docs</a>
                        <a href="/about" className="text-[var(--color-foreground)]">About</a>
                        <a href="/privacy" className="hover:text-[var(--color-foreground)] transition-colors">Privacy</a>
                    </div>
                </div>
            </nav>

            {/* ─── CONTENT ─── */}
            <section className="pt-36 pb-24 px-6">
                <div className="max-w-3xl mx-auto">
                    <h1 className="font-[var(--font-serif)] text-4xl md:text-6xl font-bold leading-tight mb-8">
                        One developer.{" "}
                        <span className="gradient-text">One stubborn vision.</span>
                    </h1>

                    <div className="space-y-8 text-[var(--color-text-muted)] text-lg leading-relaxed">
                        <p>
                            Fireside started as a weekend project in early 2025. The idea was simple:
                            what if an AI could actually <em>learn</em> from experience, the way humans do —
                            not by training on bigger datasets, but by replaying its day, finding patterns,
                            and waking up smarter?
                        </p>

                        <p>
                            Every major AI company is racing to build bigger brains.
                            Fireside is building the learning that happens <em>after school</em>.
                            Dream consolidation. Procedural memory. Gut instinct.
                            Things that emerge from experience, not parameters.
                        </p>

                        <div className="glass p-8">
                            <h2 className="font-[var(--font-display)] text-xl font-bold mb-4 text-[var(--color-foreground)]">
                                Why open source?
                            </h2>
                            <p>
                                Because if your AI is going to learn <em>about you</em>, you should be able to
                                read every line of code that does it. No black boxes.
                                No &ldquo;trust us, your data is safe.&rdquo; Verify it yourself.
                            </p>
                        </div>

                        <div className="glass p-8">
                            <h2 className="font-[var(--font-display)] text-xl font-bold mb-4 text-[var(--color-foreground)]">
                                Why local-first?
                            </h2>
                            <p>
                                Cloud inference is a subscription. Local inference is ownership.
                                Your GPU is sitting there, 23 hours a day, doing nothing.
                                Fireside puts it to work — for you, not for OpenAI&apos;s quarterly earnings.
                            </p>
                        </div>

                        <p>
                            This project is built by one person with a laptop, a stubborn belief in
                            personal AI sovereignty, and too much coffee. No VC funding. No growth hacks.
                            Just code that works and gets better every day.
                        </p>

                        <p className="text-[var(--color-text-dim)] text-base">
                            If you believe AI should work for people — not the other way around —{" "}
                            <a href="/#waitlist" className="text-[var(--color-amber)] hover:underline">join the waitlist</a>.
                        </p>
                    </div>
                </div>
            </section>

            {/* ─── FOOTER ─── */}
            <footer className="py-12 px-6">
                <div className="divider max-w-6xl mx-auto mb-12" />
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-2.5">
                        <span className="text-lg">🔥</span>
                        <span className="font-[var(--font-display)] font-bold tracking-tight">Fireside</span>
                    </div>
                    <div className="flex items-center gap-6 text-sm text-[var(--color-text-dim)]">
                        <a href="/#features" className="hover:text-[var(--color-text-muted)] transition-colors">Features</a>
                        <a href="/docs" className="hover:text-[var(--color-text-muted)] transition-colors">Docs</a>
                        <a href="/privacy" className="hover:text-[var(--color-text-muted)] transition-colors">Privacy</a>
                    </div>
                </div>
            </footer>
        </main>
    );
}

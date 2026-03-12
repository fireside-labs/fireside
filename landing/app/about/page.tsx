import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "About — Fireside",
    description: "The story behind Fireside. Built by a solo developer who wanted AI to be easier for everyone.",
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
                        <a href="/about" className="text-[var(--color-amber)]">About</a>
                    </div>
                </div>
            </nav>

            {/* ─── CONTENT ─── */}
            <div className="pt-32 pb-24 px-6">
                <div className="max-w-3xl mx-auto">
                    <h1 className="fade-up font-[var(--font-display)] text-4xl md:text-5xl font-bold mb-4">
                        About Fireside
                    </h1>
                    <p className="fade-up fade-up-delay-1 text-[var(--color-text-muted)] text-lg mb-16">
                        Built by a solo developer. Backed by zero VCs and one stubborn vision.
                    </p>

                    {/* Story */}
                    <div className="mb-16">
                        <h2 className="font-[var(--font-display)] text-2xl font-bold mb-6">The story</h2>
                        <div className="space-y-6 text-[var(--color-text-muted)] leading-relaxed">
                            <p>
                                I wanted to give my grandma an AI she could actually use.
                            </p>
                            <p>
                                Not a command line. Not a chat window with a blinking cursor and no personality.
                                Not a $20/month subscription that sends her data to a server farm in Virginia.
                                Just a friendly companion that runs on her computer, learns her preferences,
                                and never makes her feel stupid for asking a question.
                            </p>
                            <p>
                                Every AI product I tried was built by engineers, for engineers. The interfaces
                                assumed you knew what a &ldquo;prompt&rdquo; was. The setup guides assumed you
                                had Docker installed. The pricing assumed you had a corporate card.
                            </p>
                            <p>
                                So I built Fireside.
                            </p>
                            <p>
                                It&apos;s an AI companion that lives on your own hardware. You pick a pet —
                                a cat, a penguin, a dragon — and it becomes your interface to AI. Not a widget.
                                Not a chatbot. A companion with personality, memory, and mood. It learns from
                                every conversation, dreams about what it learned overnight, and greets you
                                smarter every morning.
                            </p>
                            <p>
                                The technology under the hood is serious: procedural memory systems, dream
                                consolidation cycles inspired by neuroscience, adversarial stress-testing of
                                new knowledge, multi-node mesh networking. But my grandma doesn&apos;t need to
                                know any of that. She just needs to double-click an icon and say hello.
                            </p>
                        </div>
                    </div>

                    {/* Principles */}
                    <div className="mb-16">
                        <h2 className="font-[var(--font-display)] text-2xl font-bold mb-6">Principles</h2>
                        <div className="space-y-4">
                            <div className="glass p-6">
                                <h3 className="font-[var(--font-display)] font-bold mb-2">Your data never leaves your machine.</h3>
                                <p className="text-[var(--color-text-muted)] text-sm leading-relaxed">
                                    No cloud. No telemetry. No analytics. The AI runs on your hardware,
                                    the data stays on your disk, and nobody — including me — can see your conversations.
                                </p>
                            </div>
                            <div className="glass p-6">
                                <h3 className="font-[var(--font-display)] font-bold mb-2">Complexity is my problem, not yours.</h3>
                                <p className="text-[var(--color-text-muted)] text-sm leading-relaxed">
                                    If the install takes more than 2 minutes, that&apos;s a bug. If you need to
                                    read documentation to use a feature, that&apos;s a design failure. Technology
                                    should disappear behind the experience.
                                </p>
                            </div>
                            <div className="glass p-6">
                                <h3 className="font-[var(--font-display)] font-bold mb-2">Learning is the moat.</h3>
                                <p className="text-[var(--color-text-muted)] text-sm leading-relaxed">
                                    Day 1, Fireside follows instructions. Day 90, it has instinct. Even if someone
                                    copies every line of code, they start at Day 0. The accumulated intelligence
                                    specific to you is what makes Fireside yours.
                                </p>
                            </div>
                            <div className="glass p-6">
                                <h3 className="font-[var(--font-display)] font-bold mb-2">Free means free.</h3>
                                <p className="text-[var(--color-text-muted)] text-sm leading-relaxed">
                                    Fireside is open source and free to use. No trial periods. No feature gates.
                                    No &ldquo;upgrade to Pro to remember more than 10 conversations.&rdquo;
                                    Your hardware, your AI, your rules.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Numbers */}
                    <div className="mb-16">
                        <h2 className="font-[var(--font-display)] text-2xl font-bold mb-6">By the numbers</h2>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="glass p-5 text-center">
                                <div className="font-[var(--font-display)] text-3xl font-bold text-[var(--color-amber)] mb-1">29</div>
                                <div className="text-[var(--color-text-dim)] text-xs">Plugins</div>
                            </div>
                            <div className="glass p-5 text-center">
                                <div className="font-[var(--font-display)] text-3xl font-bold text-[var(--color-amber)] mb-1">6</div>
                                <div className="text-[var(--color-text-dim)] text-xs">Companion species</div>
                            </div>
                            <div className="glass p-5 text-center">
                                <div className="font-[var(--font-display)] text-3xl font-bold text-[var(--color-amber)] mb-1">200</div>
                                <div className="text-[var(--color-text-dim)] text-xs">Languages translated</div>
                            </div>
                            <div className="glass p-5 text-center">
                                <div className="font-[var(--font-display)] text-3xl font-bold text-[var(--color-amber)] mb-1">$0</div>
                                <div className="text-[var(--color-text-dim)] text-xs">Monthly cost</div>
                            </div>
                        </div>
                    </div>

                    {/* Contact */}
                    <div>
                        <h2 className="font-[var(--font-display)] text-2xl font-bold mb-6">Get in touch</h2>
                        <div className="glass p-6">
                            <p className="text-[var(--color-text-muted)] leading-relaxed mb-4">
                                Fireside is built in public. Follow the journey, report bugs, or just say hi.
                            </p>
                            <div className="flex flex-wrap gap-3">
                                <a href="https://github.com/JordanFableFur/valhalla-mesh" className="cta-outline !text-sm !py-2.5 !px-5 !rounded-full border border-[var(--color-border)]">
                                    GitHub →
                                </a>
                                <a href="mailto:hello@getfireside.ai" className="cta-outline !text-sm !py-2.5 !px-5 !rounded-full border border-[var(--color-border)]">
                                    hello@getfireside.ai
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* ─── FOOTER ─── */}
            <footer className="py-12 px-6">
                <div className="divider max-w-6xl mx-auto mb-12" />
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-2.5">
                        <span className="text-lg">🔥</span>
                        <span className="font-[var(--font-display)] font-bold tracking-tight">Fireside</span>
                    </div>
                    <div className="flex items-center gap-6 text-sm text-[var(--color-text-dim)]">
                        <a href="/docs" className="hover:text-[var(--color-text-muted)] transition-colors">Docs</a>
                        <a href="/about" className="text-[var(--color-amber)]">About</a>
                        <a href="/privacy" className="hover:text-[var(--color-text-muted)] transition-colors">Privacy</a>
                    </div>
                </div>
            </footer>
        </main>
    );
}

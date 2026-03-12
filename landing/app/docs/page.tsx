import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Quick Start — Fireside",
    description: "Install Fireside in under 2 minutes. One command. Any GPU.",
};

export default function DocsPage() {
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
                        <a href="/docs" className="text-[var(--color-amber)]">Docs</a>
                        <a href="/about" className="hover:text-[var(--color-foreground)] transition-colors">About</a>
                    </div>
                </div>
            </nav>

            {/* ─── CONTENT ─── */}
            <div className="pt-32 pb-24 px-6">
                <div className="max-w-3xl mx-auto">
                    <h1 className="fade-up font-[var(--font-display)] text-4xl md:text-5xl font-bold mb-4">
                        Quick Start
                    </h1>
                    <p className="fade-up fade-up-delay-1 text-[var(--color-text-muted)] text-lg mb-16">
                        From zero to running AI companion in under 2 minutes.
                    </p>

                    {/* Step 1 */}
                    <div className="mb-16">
                        <div className="flex items-center gap-3 mb-4">
                            <span className="w-8 h-8 rounded-full bg-[var(--color-amber)] text-[var(--color-background)] font-bold text-sm flex items-center justify-center">1</span>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold">Install</h2>
                        </div>

                        <div className="glass p-6 mb-4">
                            <p className="text-[var(--color-text-muted)] mb-4 text-sm">
                                <strong className="text-[var(--color-foreground)]">Option A:</strong> Desktop app (no terminal)
                            </p>
                            <p className="text-[var(--color-text-muted)] text-sm mb-2">
                                Download the installer for your platform. Double-click. Done.
                            </p>
                            <div className="flex gap-3 mt-4">
                                <a href="#" className="cta !text-xs !py-2.5 !px-5">macOS (Apple Silicon)</a>
                                <a href="#" className="cta-outline !text-xs !py-2.5 !px-5 !rounded-full border border-[var(--color-border)]">Windows</a>
                            </div>
                        </div>

                        <div className="glass p-6">
                            <p className="text-[var(--color-text-muted)] mb-4 text-sm">
                                <strong className="text-[var(--color-foreground)]">Option B:</strong> One command (developers)
                            </p>
                            <div className="code-block">
                                <div><span className="prompt">$</span> curl -fsSL getfireside.ai/install | bash</div>
                            </div>
                            <p className="text-[var(--color-text-dim)] text-xs mt-3">
                                Works on macOS (Apple Silicon), Linux (NVIDIA GPU), and Windows (WSL2).
                            </p>
                        </div>
                    </div>

                    {/* Step 2 */}
                    <div className="mb-16">
                        <div className="flex items-center gap-3 mb-4">
                            <span className="w-8 h-8 rounded-full bg-[var(--color-amber)] text-[var(--color-background)] font-bold text-sm flex items-center justify-center">2</span>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold">Set Up</h2>
                        </div>
                        <p className="text-[var(--color-text-muted)] leading-relaxed mb-6">
                            The installer auto-detects your hardware and downloads the right model.
                            When it finishes, your browser opens to the onboarding wizard:
                        </p>

                        <div className="grid md:grid-cols-3 gap-4">
                            <div className="glass p-5 text-center">
                                <div className="text-2xl mb-2">👤</div>
                                <h4 className="font-[var(--font-display)] font-bold text-sm mb-1">Your Name</h4>
                                <p className="text-[var(--color-text-dim)] text-xs">So your companion knows what to call you</p>
                            </div>
                            <div className="glass p-5 text-center">
                                <div className="text-2xl mb-2">🧠</div>
                                <h4 className="font-[var(--font-display)] font-bold text-sm mb-1">Pick a Brain</h4>
                                <p className="text-[var(--color-text-dim)] text-xs">Smart & Fast (7B) or Deep Thinker (35B)</p>
                            </div>
                            <div className="glass p-5 text-center">
                                <div className="text-2xl mb-2">🐧</div>
                                <h4 className="font-[var(--font-display)] font-bold text-sm mb-1">Choose a Pet</h4>
                                <p className="text-[var(--color-text-dim)] text-xs">Cat, Dog, Penguin, Fox, Owl, or Dragon</p>
                            </div>
                        </div>
                    </div>

                    {/* Step 3 */}
                    <div className="mb-16">
                        <div className="flex items-center gap-3 mb-4">
                            <span className="w-8 h-8 rounded-full bg-[var(--color-amber)] text-[var(--color-background)] font-bold text-sm flex items-center justify-center">3</span>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold">Start a Fireside</h2>
                        </div>
                        <p className="text-[var(--color-text-muted)] leading-relaxed mb-6">
                            That&apos;s it. Start chatting. Your companion remembers everything,
                            learns from every conversation, and dreams about what it learned overnight.
                        </p>

                        <div className="code-block glow-amber">
                            <div><span className="success">✔</span> Engine &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; running</div>
                            <div><span className="success">✔</span> Dashboard &nbsp;&nbsp;&nbsp; http://localhost:3000</div>
                            <div><span className="success">✔</span> Companion &nbsp;&nbsp;&nbsp; 🐧 Sir Wadsworth is ready</div>
                            <div className="mt-3"><span className="comment"># Open dashboard and say hello!</span></div>
                        </div>
                    </div>

                    {/* What's Next */}
                    <div className="mb-16">
                        <h2 className="font-[var(--font-display)] text-2xl font-bold mb-6">What happens next</h2>

                        <div className="space-y-4">
                            <div className="glass p-5 flex items-start gap-4">
                                <span className="text-xl">💬</span>
                                <div>
                                    <h4 className="font-[var(--font-display)] font-bold text-sm mb-1">Chat naturally</h4>
                                    <p className="text-[var(--color-text-muted)] text-sm">Ask questions, give tasks, have conversations. Your companion learns from each one.</p>
                                </div>
                            </div>
                            <div className="glass p-5 flex items-start gap-4">
                                <span className="text-xl">🐾</span>
                                <div>
                                    <h4 className="font-[var(--font-display)] font-bold text-sm mb-1">Walk your pet</h4>
                                    <p className="text-[var(--color-text-muted)] text-sm">Take your companion for walks. 10% chance of an adventure — riddle guardians, treasure chests, and more.</p>
                                </div>
                            </div>
                            <div className="glass p-5 flex items-start gap-4">
                                <span className="text-xl">💡</span>
                                <div>
                                    <h4 className="font-[var(--font-display)] font-bold text-sm mb-1">Teach it things</h4>
                                    <p className="text-[var(--color-text-muted)] text-sm">&ldquo;Remember: I&apos;m allergic to shellfish.&rdquo; Your companion stores facts and uses them in future conversations.</p>
                                </div>
                            </div>
                            <div className="glass p-5 flex items-start gap-4">
                                <span className="text-xl">🌙</span>
                                <div>
                                    <h4 className="font-[var(--font-display)] font-bold text-sm mb-1">Sleep</h4>
                                    <p className="text-[var(--color-text-muted)] text-sm">Overnight, your companion replays the day, extracts patterns, and stress-tests new knowledge. Wake up to a morning briefing.</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Requirements */}
                    <div>
                        <h2 className="font-[var(--font-display)] text-2xl font-bold mb-6">Requirements</h2>
                        <div className="glass p-6">
                            <table className="w-full text-sm">
                                <tbody>
                                    <tr className="border-b border-[var(--color-border)]">
                                        <td className="py-3 font-medium text-[var(--color-foreground)]">macOS</td>
                                        <td className="py-3 text-[var(--color-text-muted)]">Apple Silicon (M1/M2/M3/M4) · 16GB+ RAM recommended</td>
                                    </tr>
                                    <tr className="border-b border-[var(--color-border)]">
                                        <td className="py-3 font-medium text-[var(--color-foreground)]">Linux</td>
                                        <td className="py-3 text-[var(--color-text-muted)]">NVIDIA GPU (8GB+ VRAM) · CUDA 12+ · 16GB RAM</td>
                                    </tr>
                                    <tr className="border-b border-[var(--color-border)]">
                                        <td className="py-3 font-medium text-[var(--color-foreground)]">Windows</td>
                                        <td className="py-3 text-[var(--color-text-muted)]">WSL2 + NVIDIA GPU · Desktop app coming soon</td>
                                    </tr>
                                    <tr>
                                        <td className="py-3 font-medium text-[var(--color-foreground)]">Disk</td>
                                        <td className="py-3 text-[var(--color-text-muted)]">~10GB for model + plugins</td>
                                    </tr>
                                </tbody>
                            </table>
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
                        <a href="/docs" className="text-[var(--color-amber)]">Docs</a>
                        <a href="/about" className="hover:text-[var(--color-text-muted)] transition-colors">About</a>
                        <a href="/privacy" className="hover:text-[var(--color-text-muted)] transition-colors">Privacy</a>
                    </div>
                </div>
            </footer>
        </main>
    );
}

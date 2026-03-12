import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Privacy — Fireside",
    description: "Fireside runs on your hardware. Your data never leaves your machine. Here's exactly how.",
};

export default function PrivacyPage() {
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
                        <a href="/about" className="hover:text-[var(--color-foreground)] transition-colors">About</a>
                        <a href="/privacy" className="text-[var(--color-foreground)]">Privacy</a>
                    </div>
                </div>
            </nav>

            {/* ─── CONTENT ─── */}
            <section className="pt-36 pb-24 px-6">
                <div className="max-w-3xl mx-auto">
                    <h1 className="font-[var(--font-serif)] text-4xl md:text-6xl font-bold leading-tight mb-4">
                        Privacy
                    </h1>
                    <p className="text-[var(--color-text-dim)] text-sm mb-12">
                        Last updated: March 2026
                    </p>

                    <div className="space-y-10 text-[var(--color-text-muted)] text-lg leading-relaxed">

                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                The short version
                            </h2>
                            <div className="glass p-8">
                                <p className="text-xl font-bold text-[var(--color-foreground)] mb-3">
                                    Zero data leaves your machine.
                                </p>
                                <p>
                                    Fireside runs entirely on your hardware. Your conversations, memories,
                                    dream cycles, and companion data are stored locally on your device.
                                    We cannot see them. We cannot access them. They are yours.
                                </p>
                            </div>
                        </div>

                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                What we collect
                            </h2>
                            <div className="glass p-6">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="text-[var(--color-text-dim)]">
                                            <th className="text-left py-2 font-medium">Data</th>
                                            <th className="text-left py-2 font-medium">Collected?</th>
                                            <th className="text-left py-2 font-medium">Details</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-[var(--color-text-muted)]">
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3">Your conversations</td>
                                            <td className="py-3 text-green-400">No</td>
                                            <td className="py-3">Stored locally only</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3">AI memories & dreams</td>
                                            <td className="py-3 text-green-400">No</td>
                                            <td className="py-3">Stored locally only</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3">Companion data</td>
                                            <td className="py-3 text-green-400">No</td>
                                            <td className="py-3">Stored locally only</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3">Email (waitlist)</td>
                                            <td className="py-3 text-[var(--color-amber)]">Only if you opt in</td>
                                            <td className="py-3">Used only to notify you when Fireside is ready</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3">Analytics / telemetry</td>
                                            <td className="py-3 text-green-400">No</td>
                                            <td className="py-3">No tracking. No cookies. No analytics scripts.</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                Local models
                            </h2>
                            <p>
                                When you run Fireside with a local model (Ollama, oMLX, or any GGUF-compatible runtime),
                                inference happens entirely on your GPU. No API calls. No cloud. The model weights
                                live on your disk and run on your silicon.
                            </p>
                        </div>

                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                Cloud model option
                            </h2>
                            <p>
                                If you <em>choose</em> to configure a cloud model (e.g., NVIDIA API, OpenAI),
                                your prompts are sent to that provider under <em>their</em> privacy policy,
                                not ours. Fireside clearly marks which model is active in the dashboard.
                                Local models show a lock icon. Cloud models show a cloud icon. You always know.
                            </p>
                        </div>

                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                Open source
                            </h2>
                            <p>
                                Fireside is open source. You can audit every line of code. If you don&apos;t trust
                                this page, trust the repo. Read what the software does. Verify our claims.
                                That&apos;s the point.
                            </p>
                        </div>

                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                Contact
                            </h2>
                            <p>
                                Questions about privacy? Open an issue on{" "}
                                <a
                                    href="https://github.com/JordanFableFur/valhalla-mesh"
                                    className="text-[var(--color-amber)] hover:underline"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    GitHub
                                </a>
                                {" "}or reach out directly. We&apos;ll answer honestly, because there&apos;s nothing to hide.
                            </p>
                        </div>
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
                        <a href="/about" className="hover:text-[var(--color-text-muted)] transition-colors">About</a>
                    </div>
                </div>
            </footer>
        </main>
    );
}

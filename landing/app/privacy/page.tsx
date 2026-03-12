import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Privacy — Fireside",
    description: "Your data never leaves your machine. No cloud. No telemetry. No exceptions.",
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
                    </div>
                </div>
            </nav>

            {/* ─── CONTENT ─── */}
            <div className="pt-32 pb-24 px-6">
                <div className="max-w-3xl mx-auto">
                    <h1 className="fade-up font-[var(--font-display)] text-4xl md:text-5xl font-bold mb-4">
                        Privacy
                    </h1>
                    <p className="fade-up fade-up-delay-1 text-[var(--color-text-muted)] text-lg mb-4">
                        Your data never leaves your machine. No exceptions.
                    </p>
                    <p className="fade-up fade-up-delay-2 text-[var(--color-text-dim)] text-sm mb-16">
                        Last updated: March 12, 2026
                    </p>

                    {/* TL;DR */}
                    <div className="glass p-8 glow-amber mb-16">
                        <h2 className="font-[var(--font-display)] text-xl font-bold mb-4 text-[var(--color-amber)]">
                            TL;DR
                        </h2>
                        <ul className="space-y-3 text-[var(--color-text-muted)] leading-relaxed">
                            <li className="flex items-start gap-3">
                                <span className="text-[var(--color-amber)] mt-0.5">✔</span>
                                <span>All AI processing happens on your hardware. Nothing is sent to any server.</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-[var(--color-amber)] mt-0.5">✔</span>
                                <span>Your conversations, memories, and companion data are stored locally on your disk.</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-[var(--color-amber)] mt-0.5">✔</span>
                                <span>No analytics, no telemetry, no tracking, no cookies on the dashboard.</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-[var(--color-amber)] mt-0.5">✔</span>
                                <span>No account required. No email required to use the product.</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-[var(--color-amber)] mt-0.5">✔</span>
                                <span>Open source. You can audit every line of code.</span>
                            </li>
                        </ul>
                    </div>

                    {/* Sections */}
                    <div className="space-y-12 text-[var(--color-text-muted)] leading-relaxed">
                        <section>
                            <h2 className="font-[var(--font-display)] text-xl font-bold mb-4 text-[var(--color-foreground)]">
                                1. What Fireside stores
                            </h2>
                            <p className="mb-4">Everything Fireside stores lives in a single folder on your machine:</p>
                            <div className="code-block text-sm mb-4">
                                <div><span className="comment"># macOS</span></div>
                                <div>~/.valhalla/</div>
                                <div className="mt-2"><span className="comment"># Contains:</span></div>
                                <div>&nbsp;&nbsp;companion_state.json &nbsp;&nbsp;<span className="comment"># Your pet&apos;s stats</span></div>
                                <div>&nbsp;&nbsp;procedural_memory/ &nbsp;&nbsp;&nbsp;&nbsp;<span className="comment"># What your AI has learned</span></div>
                                <div>&nbsp;&nbsp;conversations/ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="comment"># Chat history</span></div>
                                <div>&nbsp;&nbsp;inventory.json &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="comment"># Adventure loot</span></div>
                                <div>&nbsp;&nbsp;config.json &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="comment"># Your preferences</span></div>
                            </div>
                            <p>
                                Delete this folder and everything is gone. No hidden copies. No cloud backups.
                                No &ldquo;we retain data for 30 days after deletion.&rdquo; It&apos;s your disk. You control it.
                            </p>
                        </section>

                        <section>
                            <h2 className="font-[var(--font-display)] text-xl font-bold mb-4 text-[var(--color-foreground)]">
                                2. What Fireside does NOT do
                            </h2>
                            <div className="space-y-3">
                                <div className="glass p-4 flex items-start gap-3">
                                    <span className="text-red-400 font-bold">✗</span>
                                    <span>Send your data to any server, API, or cloud service</span>
                                </div>
                                <div className="glass p-4 flex items-start gap-3">
                                    <span className="text-red-400 font-bold">✗</span>
                                    <span>Track your usage, clicks, or behavior</span>
                                </div>
                                <div className="glass p-4 flex items-start gap-3">
                                    <span className="text-red-400 font-bold">✗</span>
                                    <span>Install cookies, pixels, or analytics scripts</span>
                                </div>
                                <div className="glass p-4 flex items-start gap-3">
                                    <span className="text-red-400 font-bold">✗</span>
                                    <span>Phone home, check for updates silently, or make network requests you didn&apos;t ask for</span>
                                </div>
                                <div className="glass p-4 flex items-start gap-3">
                                    <span className="text-red-400 font-bold">✗</span>
                                    <span>Share, sell, or monetize your data in any way</span>
                                </div>
                            </div>
                        </section>

                        <section>
                            <h2 className="font-[var(--font-display)] text-xl font-bold mb-4 text-[var(--color-foreground)]">
                                3. Network requests Fireside makes
                            </h2>
                            <p className="mb-4">
                                By default, Fireside makes <strong className="text-[var(--color-foreground)]">zero</strong> network
                                requests after installation. The only exceptions are features you explicitly enable:
                            </p>
                            <div className="glass p-6">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-[var(--color-border)]">
                                            <th className="text-left py-2 font-medium text-[var(--color-foreground)]">Feature</th>
                                            <th className="text-left py-2 font-medium text-[var(--color-foreground)]">What it fetches</th>
                                            <th className="text-left py-2 font-medium text-[var(--color-foreground)]">When</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr className="border-b border-[var(--color-border)]">
                                            <td className="py-3">Browse plugin</td>
                                            <td className="py-3 text-[var(--color-text-dim)]">Web pages you ask it to read</td>
                                            <td className="py-3 text-[var(--color-text-dim)]">Only when you ask</td>
                                        </tr>
                                        <tr className="border-b border-[var(--color-border)]">
                                            <td className="py-3">Cloud model (optional)</td>
                                            <td className="py-3 text-[var(--color-text-dim)]">API calls to OpenAI/Anthropic</td>
                                            <td className="py-3 text-[var(--color-text-dim)]">Only if you add an API key</td>
                                        </tr>
                                        <tr className="border-b border-[var(--color-border)]">
                                            <td className="py-3">Mesh sync (optional)</td>
                                            <td className="py-3 text-[var(--color-text-dim)]">Encrypted data between your own nodes</td>
                                            <td className="py-3 text-[var(--color-text-dim)]">Only between your devices</td>
                                        </tr>
                                        <tr>
                                            <td className="py-3">Translation model</td>
                                            <td className="py-3 text-[var(--color-text-dim)]">One-time 600MB model download</td>
                                            <td className="py-3 text-[var(--color-text-dim)]">First translation only</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </section>

                        <section>
                            <h2 className="font-[var(--font-display)] text-xl font-bold mb-4 text-[var(--color-foreground)]">
                                4. The Teach Me feature
                            </h2>
                            <p className="mb-4">
                                When you teach your companion a fact (&ldquo;Remember: I&apos;m allergic to shellfish&rdquo;),
                                that fact is stored in a local JSON file. It never leaves your machine.
                            </p>
                            <p>
                                As a safety measure, the Teach Me system will warn you (but not block you) if you
                                attempt to store sensitive information like credit card numbers, social security numbers,
                                or passwords. This detection happens locally — no data is sent anywhere to check.
                            </p>
                        </section>

                        <section>
                            <h2 className="font-[var(--font-display)] text-xl font-bold mb-4 text-[var(--color-foreground)]">
                                5. This website
                            </h2>
                            <p className="mb-4">
                                This landing page (<code className="text-[var(--color-amber)]">getfireside.ai</code>) is
                                a static site. It does not use cookies, analytics, or tracking scripts.
                            </p>
                            <p>
                                If you join the waitlist, we store your email address for the sole purpose of
                                notifying you when Fireside is ready. We will never share it, sell it, or use
                                it for anything else. One email, then we delete it.
                            </p>
                        </section>

                        <section>
                            <h2 className="font-[var(--font-display)] text-xl font-bold mb-4 text-[var(--color-foreground)]">
                                6. Open source
                            </h2>
                            <p>
                                Fireside is open source. Every claim on this page can be verified by reading
                                the code. Trust is earned by transparency, not by policy documents.
                            </p>
                            <div className="mt-4">
                                <a href="https://github.com/JordanFableFur/valhalla-mesh" className="cta-outline !text-sm !py-2.5 !px-5 !rounded-full border border-[var(--color-border)]">
                                    View Source on GitHub →
                                </a>
                            </div>
                        </section>
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
                        <a href="/about" className="hover:text-[var(--color-text-muted)] transition-colors">About</a>
                        <a href="/privacy" className="text-[var(--color-amber)]">Privacy</a>
                    </div>
                </div>
            </footer>
        </main>
    );
}

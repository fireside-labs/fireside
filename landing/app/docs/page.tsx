import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Docs — Fireside Quickstart",
    description: "Get Fireside running in 5 minutes. Clone, install, start. That's it.",
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
                        <a href="/docs" className="text-[var(--color-foreground)]">Docs</a>
                        <a href="/about" className="hover:text-[var(--color-foreground)] transition-colors">About</a>
                        <a href="/privacy" className="hover:text-[var(--color-foreground)] transition-colors">Privacy</a>
                    </div>
                </div>
            </nav>

            {/* ─── CONTENT ─── */}
            <section className="pt-36 pb-24 px-6">
                <div className="max-w-3xl mx-auto">
                    <h1 className="font-[var(--font-serif)] text-4xl md:text-6xl font-bold leading-tight mb-4">
                        Quickstart
                    </h1>
                    <p className="text-[var(--color-text-muted)] text-lg mb-12">
                        Running in 5 minutes. For real.
                    </p>

                    {/* Prerequisites */}
                    <div className="space-y-12">
                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                Prerequisites
                            </h2>
                            <div className="glass p-6">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="text-[var(--color-text-dim)]">
                                            <th className="text-left py-2 font-medium">What</th>
                                            <th className="text-left py-2 font-medium">Why</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-[var(--color-text-muted)]">
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3 font-medium text-[var(--color-foreground)]">Python 3.11+</td>
                                            <td className="py-3">Bifrost backend</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3 font-medium text-[var(--color-foreground)]">Node.js 18+</td>
                                            <td className="py-3">Dashboard (Next.js)</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3 font-medium text-[var(--color-foreground)]">Ollama or oMLX</td>
                                            <td className="py-3">Local inference (or an NVIDIA API key for cloud)</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* Step 1 */}
                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                1 — Clone
                            </h2>
                            <div className="code-block glow-amber">
                                <div><span className="prompt">$</span> git clone https://github.com/openclaw/valhalla-mesh-v2.git</div>
                                <div><span className="prompt">$</span> cd valhalla-mesh-v2</div>
                            </div>
                        </div>

                        {/* Step 2 */}
                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                2 — Install dependencies
                            </h2>
                            <div className="code-block glow-amber">
                                <div><span className="comment"># Backend</span></div>
                                <div><span className="prompt">$</span> pip install fastapi uvicorn pyyaml pydantic</div>
                                <div className="mt-3"><span className="comment"># Dashboard</span></div>
                                <div><span className="prompt">$</span> cd dashboard &amp;&amp; npm install &amp;&amp; cd ..</div>
                            </div>
                        </div>

                        {/* Step 3 */}
                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                3 — Start
                            </h2>
                            <p className="text-[var(--color-text-muted)] mb-4">Two terminals:</p>
                            <div className="grid md:grid-cols-2 gap-4">
                                <div>
                                    <p className="text-sm font-medium text-[var(--color-foreground)] mb-2">Terminal 1 — Backend</p>
                                    <div className="code-block glow-amber">
                                        <div><span className="prompt">$</span> python bifrost.py</div>
                                        <div className="mt-2"><span className="success">✔</span> Bifrost on 0.0.0.0:8765</div>
                                    </div>
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-[var(--color-foreground)] mb-2">Terminal 2 — Dashboard</p>
                                    <div className="code-block glow-amber">
                                        <div><span className="prompt">$</span> cd dashboard &amp;&amp; npm run dev</div>
                                        <div className="mt-2"><span className="success">✔</span> http://localhost:3000</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Step 4 */}
                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                4 — What you see
                            </h2>
                            <p className="text-[var(--color-text-muted)] mb-4">
                                The dashboard has six pages:
                            </p>
                            <div className="glass p-6">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="text-[var(--color-text-dim)]">
                                            <th className="text-left py-2 font-medium">Page</th>
                                            <th className="text-left py-2 font-medium">What it does</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-[var(--color-text-muted)]">
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3 font-medium text-[var(--color-foreground)]">Nodes</td>
                                            <td className="py-3">Live mesh node cards — name, role, status, model, uptime</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3 font-medium text-[var(--color-foreground)]">Models</td>
                                            <td className="py-3">Current model + alias buttons — click to switch</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3 font-medium text-[var(--color-foreground)]">Soul Editor</td>
                                            <td className="py-3">Edit your agent&apos;s identity, personality, and user profile</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3 font-medium text-[var(--color-foreground)]">Config</td>
                                            <td className="py-3">Full valhalla.yaml in a code editor with syntax highlighting</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3 font-medium text-[var(--color-foreground)]">Plugins</td>
                                            <td className="py-3">Installed plugins with status toggles</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3 font-medium text-[var(--color-foreground)]">War Room</td>
                                            <td className="py-3">Hypotheses, predictions, self-model (Sprint 2)</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* Step 5 */}
                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                5 — Try things
                            </h2>
                            <div className="space-y-4">
                                <div className="glass p-6">
                                    <h3 className="font-[var(--font-display)] font-bold mb-2">Switch models</h3>
                                    <div className="code-block">
                                        <div><span className="prompt">$</span> curl -X POST http://localhost:8765/api/v1/model-switch \</div>
                                        <div>&nbsp;&nbsp;-H &apos;Content-Type: application/json&apos; \</div>
                                        <div>&nbsp;&nbsp;-d &apos;{'\"alias\": \"hugs\"'}&apos;</div>
                                    </div>
                                </div>
                                <div className="glass p-6">
                                    <h3 className="font-[var(--font-display)] font-bold mb-2">Check node status</h3>
                                    <div className="code-block">
                                        <div><span className="prompt">$</span> curl http://localhost:8765/api/v1/status</div>
                                        <div className="mt-1"><span className="comment"># → {'{"node":"odin","role":"orchestrator","model":"Qwen3.5-35B",...}'}</span></div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Step 6 */}
                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                6 — Add a second node
                            </h2>
                            <p className="text-[var(--color-text-muted)] mb-4">
                                Got another machine? One command:
                            </p>
                            <div className="code-block glow-amber">
                                <div><span className="prompt">$</span> valhalla join odin@&lt;your-ip&gt;:8765</div>
                            </div>
                            <p className="text-[var(--color-text-dim)] text-sm mt-3">
                                The node appears in the dashboard automatically.
                            </p>
                        </div>

                        {/* Troubleshooting */}
                        <div>
                            <h2 className="font-[var(--font-display)] text-2xl font-bold mb-4 text-[var(--color-foreground)]">
                                Troubleshooting
                            </h2>
                            <div className="glass p-6">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="text-[var(--color-text-dim)]">
                                            <th className="text-left py-2 font-medium">Problem</th>
                                            <th className="text-left py-2 font-medium">Fix</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-[var(--color-text-muted)]">
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3">ModuleNotFoundError: fastapi</td>
                                            <td className="py-3">pip install fastapi uvicorn pyyaml pydantic</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3">Dashboard shows &quot;Failed to fetch&quot;</td>
                                            <td className="py-3">Is Bifrost running? Check Terminal 1.</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3">Model switch says &quot;Unknown alias&quot;</td>
                                            <td className="py-3">Check models.aliases in valhalla.yaml</td>
                                        </tr>
                                        <tr className="border-t border-[var(--color-border)]">
                                            <td className="py-3">Port 8765 in use</td>
                                            <td className="py-3">python bifrost.py --port 8766</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
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
                        <a href="/about" className="hover:text-[var(--color-text-muted)] transition-colors">About</a>
                        <a href="/privacy" className="hover:text-[var(--color-text-muted)] transition-colors">Privacy</a>
                    </div>
                </div>
            </footer>
        </main>
    );
}

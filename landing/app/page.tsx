export default function LandingPage() {
  return (
    <main className="bg-grid min-h-screen">
      {/* ─── NAV ─── */}
      <nav className="fixed top-0 w-full z-50 border-b border-[var(--color-border)] bg-[var(--color-background)]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚡</span>
            <span className="font-[var(--font-display)] font-bold text-lg tracking-tight">
              Valhalla
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-zinc-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#compare" className="hover:text-white transition-colors">Compare</a>
            <a href="#quickstart" className="hover:text-white transition-colors">Quick Start</a>
            <a href="https://github.com/openclaw/valhalla-mesh-v2" className="cta-outline !py-2 !px-4 !text-sm !rounded-lg">GitHub</a>
          </div>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section className="pt-40 pb-24 px-6 text-center relative">
        {/* Subtle radial glow behind heading */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-[radial-gradient(ellipse,rgba(0,255,136,0.06),transparent_70%)] pointer-events-none" />

        <div className="max-w-4xl mx-auto relative">
          <p className="fade-up text-sm font-medium tracking-widest uppercase text-[var(--color-neon)] mb-6">
            Open Source &middot; Run Locally &middot; Own Your Data
          </p>

          <h1 className="fade-up fade-up-delay-1 font-[var(--font-display)] text-5xl md:text-7xl font-extrabold leading-[1.08] tracking-tight mb-6">
            AI that runs on{" "}
            <span className="gradient-text">your hardware</span>,<br />
            learns from your work,<br />
            and <span className="text-glow text-[var(--color-neon)]">never forgets</span>.
          </h1>

          <p className="fade-up fade-up-delay-2 text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Deploy persistent AI agents that use your tools, remember what works,
            and get smarter every day — and nothing ever leaves your network.
          </p>

          <div className="fade-up fade-up-delay-3 flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="#quickstart" className="cta">
              Get Started <span className="text-lg">→</span>
            </a>
            <a href="https://github.com/openclaw/valhalla-mesh-v2" className="cta cta-outline">
              View on GitHub
            </a>
          </div>
        </div>
      </section>

      {/* ─── VALUE PROPS ─── */}
      <section className="py-20 px-6" id="features">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6">
          <div className="glass p-8 fade-up transition-all duration-300">
            <div className="text-3xl mb-4">🧠</div>
            <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Agents That Learn</h3>
            <p className="text-zinc-400 leading-relaxed">
              Procedural memory ranks what worked and what didn&apos;t.
              Dream cycles consolidate knowledge overnight.
              Day 1 it&apos;s generic. Day 90 it has instinct about your codebase.
            </p>
          </div>

          <div className="glass p-8 fade-up fade-up-delay-1 transition-all duration-300">
            <div className="text-3xl mb-4">🔒</div>
            <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Your Hardware, Your Data</h3>
            <p className="text-zinc-400 leading-relaxed">
              Runs on any GPU — RTX, Apple Silicon, cloud. No API keys
              required for local models. Zero data leaves your machine
              unless you want it to.
            </p>
          </div>

          <div className="glass p-8 fade-up fade-up-delay-2 transition-all duration-300">
            <div className="text-3xl mb-4">⚡</div>
            <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Real Work, Not Suggestions</h3>
            <p className="text-zinc-400 leading-relaxed">
              Agents read files, write code, run tests, make commits.
              Watch tool usage in real time on the dashboard.
              This isn&apos;t a chatbot — it&apos;s a coworker.
            </p>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section className="py-20 px-6 border-t border-[var(--color-border)]">
        <div className="max-w-4xl mx-auto text-center mb-16">
          <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
            From install to <span className="gradient-text">running agent</span> in 2 minutes
          </h2>
          <p className="text-zinc-400 text-lg">No Docker. No virtual environments. No 14-step guide.</p>
        </div>

        <div className="max-w-2xl mx-auto">
          <div className="code-block glow-neon">
            <div><span className="comment"># Install</span></div>
            <div><span className="prompt">$</span> brew install valhalla</div>
            <div className="mt-4"><span className="comment"># Initialize (auto-detects your GPU and model)</span></div>
            <div><span className="prompt">$</span> valhalla init</div>
            <div className="mt-4"><span className="comment"># Launch — dashboard opens automatically</span></div>
            <div><span className="prompt">$</span> valhalla start</div>
            <div className="mt-2"><span className="success">✔</span> Bifrost &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; http://localhost:8765</div>
            <div><span className="success">✔</span> Dashboard &nbsp;&nbsp;&nbsp; http://localhost:3000</div>
            <div><span className="success">✔</span> Model &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; llama3.1:8b (local)</div>
            <div><span className="success">✔</span> Plugins &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 3 loaded</div>
          </div>
        </div>
      </section>

      {/* ─── FEATURES DEEP DIVE ─── */}
      <section className="py-20 px-6 border-t border-[var(--color-border)]">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
              What no other framework has
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="glass p-8">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">🌙</span>
                <h3 className="font-[var(--font-display)] text-lg font-bold">Dream Consolidation</h3>
              </div>
              <p className="text-zinc-400 leading-relaxed">
                Nightly SVD compression collides semantically similar experiences
                to extract generalized principles. Not backup — active knowledge synthesis.
                The system literally sleeps and learns.
              </p>
            </div>

            <div className="glass p-8">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">🛡️</span>
                <h3 className="font-[var(--font-display)] text-lg font-bold">Adaptive Immunity</h3>
              </div>
              <p className="text-zinc-400 leading-relaxed">
                One node detects an attack. Within 60 seconds, all nodes have
                updated deny-lists. No human in the loop. No restart.
                Every attack makes every node stronger.
              </p>
            </div>

            <div className="glass p-8">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">💓</span>
                <h3 className="font-[var(--font-display)] text-lg font-bold">Somatic Gating</h3>
              </div>
              <p className="text-zinc-400 leading-relaxed">
                Based on Damasio&apos;s Somatic Marker Hypothesis. Before high-stakes actions,
                agents check emotional valence from past experiences. Bad gut feeling?
                Action blocked before the LLM even reasons.
              </p>
            </div>

            <div className="glass p-8">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">🌐</span>
                <h3 className="font-[var(--font-display)] text-lg font-bold">Distributed Cognition</h3>
              </div>
              <p className="text-zinc-400 leading-relaxed">
                Agents model what their peers believe. &ldquo;Freya already knows X,
                so I only need to tell her Y.&rdquo; Multi-node consensus
                for critical decisions. Theory of mind, not just message passing.
              </p>
            </div>

            <div className="glass p-8">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">🧬</span>
                <h3 className="font-[var(--font-display)] text-lg font-bold">Agent Souls</h3>
              </div>
              <p className="text-zinc-400 leading-relaxed">
                Every agent has an identity, personality, and relationship context.
                Change the soul file, change the behavior. Same model, same tools —
                completely different agent.
              </p>
            </div>

            <div className="glass p-8">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">🔌</span>
                <h3 className="font-[var(--font-display)] text-lg font-bold">Plugin Ecosystem</h3>
              </div>
              <p className="text-zinc-400 leading-relaxed">
                Every capability is a plugin: two-file manifest + handler.
                Install from the marketplace or build your own.
                Hot-reload — no restarts.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── COMPARISON ─── */}
      <section className="py-20 px-6 border-t border-[var(--color-border)]" id="compare">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
              How Valhalla compares
            </h2>
            <p className="text-zinc-400 text-lg">
              The industry builds bigger brains. We build the learning that happens after school.
            </p>
          </div>

          <div className="glass overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)]">
                  <th className="text-left p-4 text-zinc-500 font-medium"></th>
                  <th className="text-center p-4 text-zinc-400 font-medium">ChatGPT / Claude</th>
                  <th className="text-center p-4 text-zinc-400 font-medium">CrewAI / LangChain</th>
                  <th className="text-center p-4 text-[var(--color-neon)] font-bold">Valhalla</th>
                </tr>
              </thead>
              <tbody className="text-zinc-400">
                <tr className="border-b border-[var(--color-border)]/50">
                  <td className="p-4 font-medium text-zinc-300">Runs locally</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center">Partial</td>
                  <td className="p-4 text-center text-[var(--color-neon)]">✔ Any GPU</td>
                </tr>
                <tr className="border-b border-[var(--color-border)]/50">
                  <td className="p-4 font-medium text-zinc-300">Remembers across sessions</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center text-[var(--color-neon)]">✔ Procedural memory</td>
                </tr>
                <tr className="border-b border-[var(--color-border)]/50">
                  <td className="p-4 font-medium text-zinc-300">Learns from failures</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center text-[var(--color-neon)]">✔ Dream cycles</td>
                </tr>
                <tr className="border-b border-[var(--color-border)]/50">
                  <td className="p-4 font-medium text-zinc-300">Real execution (not just text)</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center">Partial</td>
                  <td className="p-4 text-center text-[var(--color-neon)]">✔ 23+ tools</td>
                </tr>
                <tr className="border-b border-[var(--color-border)]/50">
                  <td className="p-4 font-medium text-zinc-300">Multi-agent mesh</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center">Text-only</td>
                  <td className="p-4 text-center text-[var(--color-neon)]">✔ Distributed cognition</td>
                </tr>
                <tr className="border-b border-[var(--color-border)]/50">
                  <td className="p-4 font-medium text-zinc-300">Immune system</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center text-[var(--color-neon)]">✔ Cross-node defense</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium text-zinc-300">Dashboard</td>
                  <td className="p-4 text-center">Web UI</td>
                  <td className="p-4 text-center text-zinc-600">✗</td>
                  <td className="p-4 text-center text-[var(--color-neon)]">✔ Real-time</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ─── MOAT / QUOTE ─── */}
      <section className="py-24 px-6 border-t border-[var(--color-border)]">
        <div className="max-w-3xl mx-auto text-center">
          <blockquote className="text-2xl md:text-3xl font-[var(--font-display)] font-bold leading-relaxed mb-6">
            &ldquo;Day 1, it follows instructions.<br />
            Day 90, it has <span className="text-[var(--color-neon)] text-glow">instinct</span>.&rdquo;
          </blockquote>
          <p className="text-zinc-500 text-lg leading-relaxed max-w-xl mx-auto">
            Even if a competitor copies every line of code, they start at Day 0.
            The accumulated operational intelligence specific to your business
            is the moat — and it deepens every day the system runs.
          </p>
        </div>
      </section>

      {/* ─── QUICK START ─── */}
      <section className="py-20 px-6 border-t border-[var(--color-border)]" id="quickstart">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
            Ready?
          </h2>
          <p className="text-zinc-400 text-lg mb-10">
            Three commands. Two minutes. Your first agent is live.
          </p>

          <div className="max-w-xl mx-auto mb-10">
            <div className="code-block text-left glow-neon">
              <div><span className="prompt">$</span> brew install valhalla</div>
              <div><span className="prompt">$</span> valhalla init</div>
              <div><span className="prompt">$</span> valhalla start</div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="https://github.com/openclaw/valhalla-mesh-v2" className="cta">
              View on GitHub <span className="text-lg">→</span>
            </a>
            <a href="https://github.com/openclaw/valhalla-mesh-v2/blob/main/docs/quickstart.md" className="cta cta-outline">
              Read the Docs
            </a>
          </div>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer className="py-12 px-6 border-t border-[var(--color-border)]">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <span className="text-lg">⚡</span>
            <span className="font-[var(--font-display)] font-bold tracking-tight">Valhalla Mesh</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-zinc-500">
            <a href="https://github.com/openclaw/valhalla-mesh-v2" className="hover:text-zinc-300 transition-colors">GitHub</a>
            <a href="https://github.com/openclaw/valhalla-mesh-v2/blob/main/docs/quickstart.md" className="hover:text-zinc-300 transition-colors">Docs</a>
            <a href="https://github.com/openclaw" className="hover:text-zinc-300 transition-colors">OpenClaw</a>
          </div>
          <p className="text-sm text-zinc-600">
            MIT License &middot; Built by{" "}
            <a href="https://github.com/openclaw" className="text-zinc-400 hover:text-white transition-colors">
              OpenClaw
            </a>
          </p>
        </div>
      </footer>
    </main>
  );
}

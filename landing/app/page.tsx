export default function LandingPage() {
  return (
    <main className="bg-grid min-h-screen">
      {/* ─── EMBER PARTICLES (CSS animated) ─── */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className="ember-particle"
            style={{
              left: `${8 + i * 8}%`,
              animationDuration: `${8 + (i % 5) * 3}s`,
              animationDelay: `${(i * 1.3) % 7}s`,
              opacity: 0,
              bottom: '-20px',
            }}
          />
        ))}
      </div>

      {/* ─── NAV ─── */}
      <nav className="fixed top-0 w-full z-50 border-b border-[var(--color-border)] bg-[var(--color-background)]/85 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🔥</span>
            <span className="font-[var(--font-display)] font-bold text-lg tracking-tight">
              Fireside
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-[var(--color-text-muted)]">
            <a href="#features" className="hover:text-[var(--color-foreground)] transition-colors">Features</a>
            <a href="#how" className="hover:text-[var(--color-foreground)] transition-colors">How It Works</a>
            <a href="#compare" className="hover:text-[var(--color-foreground)] transition-colors">Compare</a>
            <a href="#waitlist" className="cta-outline !py-2 !px-5 !text-sm !rounded-full">
              Get Early Access
            </a>
          </div>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section className="pt-44 pb-28 px-6 text-center relative">
        <div className="hero-glow" />

        <div className="max-w-4xl mx-auto relative z-10">
          <p className="fade-up text-sm font-medium tracking-[0.2em] uppercase text-[var(--color-amber)] mb-8">
            Your Hardware &middot; Your Data &middot; Your AI
          </p>

          <h1 className="fade-up fade-up-delay-1 font-[var(--font-serif)] text-5xl md:text-7xl font-bold leading-[1.1] tracking-tight mb-8">
            Your AI that learns{" "}
            <span className="gradient-text">while you sleep</span>
          </h1>

          <p className="fade-up fade-up-delay-2 text-lg md:text-xl text-[var(--color-text-muted)] max-w-2xl mx-auto mb-12 leading-relaxed">
            Deploy persistent AI agents on your own hardware.
            They use your tools, remember what works, dream about what
            they&apos;ve learned, and wake up smarter every morning.
          </p>

          <div className="fade-up fade-up-delay-3 flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="#waitlist" className="cta">
              Get Early Access <span className="text-lg">→</span>
            </a>
            <a href="#how" className="cta cta-outline">
              See How It Works
            </a>
          </div>
        </div>
      </section>

      {/* ─── VALUE PROPS ─── */}
      <section className="py-24 px-6" id="features">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
              What makes Fireside <span className="gradient-text">different</span>
            </h2>
            <p className="text-[var(--color-text-muted)] text-lg max-w-xl mx-auto">
              Not another chatbot wrapper. A cognitive architecture grounded in neuroscience.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <div className="glass p-8 fade-up">
              <div className="feature-icon">🌙</div>
              <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Dream Consolidation</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed">
                Every night, your agents replay the day&apos;s work in compressed bursts —
                colliding similar experiences to extract generalized knowledge. Not backup.
                Active learning while you sleep.
              </p>
            </div>

            <div className="glass p-8 fade-up fade-up-delay-1">
              <div className="feature-icon">🔒</div>
              <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Runs on Your Hardware</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed">
                RTX, Apple Silicon, or cloud — your choice. No API keys required
                for local models. Zero data leaves your machine. Your inference,
                your rules.
              </p>
            </div>

            <div className="glass p-8 fade-up fade-up-delay-2">
              <div className="feature-icon">🧠</div>
              <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Procedural Memory</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed">
                Agents remember what worked and what didn&apos;t. Successful approaches are
                ranked by confidence and recency. Day 1 it follows instructions.
                Day 90 it has instinct.
              </p>
            </div>

            <div className="glass p-8 fade-up">
              <div className="feature-icon">🛡️</div>
              <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Adaptive Immunity</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed">
                One node detects an attack. Within 60 seconds, every node in your mesh
                has the defense. No human in the loop. Every attack makes the system stronger.
              </p>
            </div>

            <div className="glass p-8 fade-up fade-up-delay-1">
              <div className="feature-icon">💓</div>
              <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Gut Instinct</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed">
                Before high-stakes actions, agents check their &ldquo;somatic markers&rdquo; —
                compressed past experiences that flag danger before reasoning even starts.
                Bad feeling? Action blocked.
              </p>
            </div>

            <div className="glass p-8 fade-up fade-up-delay-2">
              <div className="feature-icon">🔌</div>
              <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Plugin Ecosystem</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed">
                Every capability is a plugin — two files, hot-reloadable, no restarts.
                Install from the marketplace or build your own. The mesh grows with you.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section className="py-24 px-6" id="how">
        <div className="divider max-w-6xl mx-auto mb-24" />

        <div className="max-w-4xl mx-auto text-center mb-16">
          <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
            From install to <span className="gradient-text">running agent</span> in 2 minutes
          </h2>
          <p className="text-[var(--color-text-muted)] text-lg">
            No Docker. No virtual environments. No 14-step guide.
          </p>
        </div>

        <div className="max-w-2xl mx-auto">
          <div className="code-block glow-amber">
            <div><span className="comment"># Install</span></div>
            <div><span className="prompt">$</span> brew install fireside</div>
            <div className="mt-4"><span className="comment"># Initialize — auto-detects your GPU and downloads the right model</span></div>
            <div><span className="prompt">$</span> fireside init</div>
            <div className="mt-4"><span className="comment"># Launch — dashboard opens automatically</span></div>
            <div><span className="prompt">$</span> fireside start</div>
            <div className="mt-3"><span className="success">✔</span> Engine &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; http://localhost:8765</div>
            <div><span className="success">✔</span> Dashboard &nbsp;&nbsp;&nbsp; http://localhost:3000</div>
            <div><span className="success">✔</span> Model &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Qwen 3.5 35B (local, free)</div>
            <div><span className="success">✔</span> Plugins &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 8 loaded</div>
          </div>
        </div>
      </section>

      {/* ─── THE OVERNIGHT LOOP ─── */}
      <section className="py-24 px-6">
        <div className="divider max-w-6xl mx-auto mb-24" />

        <div className="max-w-4xl mx-auto text-center mb-16">
          <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
            The <span className="gradient-text-rose">overnight learning loop</span>
          </h2>
          <p className="text-[var(--color-text-muted)] text-lg max-w-2xl mx-auto">
            While you sleep, your agents dream. Not a metaphor — a real cognitive cycle
            that makes them measurably smarter every morning.
          </p>
        </div>

        <div className="max-w-3xl mx-auto grid md:grid-cols-4 gap-4 text-center">
          <div className="glass p-6">
            <div className="text-2xl mb-3">📋</div>
            <h4 className="font-[var(--font-display)] font-bold mb-2 text-sm">Day&apos;s Work</h4>
            <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">Tasks completed, tools used, outcomes logged</p>
          </div>
          <div className="glass p-6">
            <div className="text-2xl mb-3">🌙</div>
            <h4 className="font-[var(--font-display)] font-bold mb-2 text-sm">Dream Cycle</h4>
            <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">Memory collision, pattern extraction, SVD compression</p>
          </div>
          <div className="glass p-6">
            <div className="text-2xl mb-3">⚔️</div>
            <h4 className="font-[var(--font-display)] font-bold mb-2 text-sm">Crucible Test</h4>
            <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">New knowledge stress-tested against adversarial edge cases</p>
          </div>
          <div className="glass p-6">
            <div className="text-2xl mb-3">☀️</div>
            <h4 className="font-[var(--font-display)] font-bold mb-2 text-sm">Morning Brief</h4>
            <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">New instincts ready. Agent is faster and more reliable.</p>
          </div>
        </div>
      </section>

      {/* ─── COMPARISON ─── */}
      <section className="py-24 px-6" id="compare">
        <div className="divider max-w-6xl mx-auto mb-24" />

        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
              How Fireside compares
            </h2>
            <p className="text-[var(--color-text-muted)] text-lg">
              The industry builds bigger brains. We build the learning that happens after school.
            </p>
          </div>

          <div className="glass overflow-hidden">
            <table className="compare-table">
              <thead>
                <tr>
                  <th className="text-[var(--color-text-dim)] font-medium"></th>
                  <th className="text-center text-[var(--color-text-muted)] font-medium">ChatGPT / Claude</th>
                  <th className="text-center text-[var(--color-text-muted)] font-medium">CrewAI / LangChain</th>
                  <th className="text-center text-[var(--color-amber)] font-bold">Fireside</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Runs locally</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center">Partial</td>
                  <td className="text-center compare-check">✔ Any GPU</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Remembers across sessions</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-check">✔ Procedural memory</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Learns from failures</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-check">✔ Dream cycles</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Overnight learning loop</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-check">✔ Crucible-tested</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Multi-agent mesh</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center">Text-only</td>
                  <td className="text-center compare-check">✔ Distributed cognition</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Immune system</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-check">✔ Cross-node defense</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Dashboard</td>
                  <td className="text-center">Web UI</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-check">✔ Real-time + themes</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Monthly cost</td>
                  <td className="text-center">$20+/mo</td>
                  <td className="text-center">API costs</td>
                  <td className="text-center compare-check">$0 (your hardware)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ─── MOAT QUOTE ─── */}
      <section className="py-28 px-6">
        <div className="divider max-w-6xl mx-auto mb-28" />

        <div className="max-w-3xl mx-auto text-center">
          <blockquote className="text-2xl md:text-4xl font-[var(--font-serif)] font-bold leading-relaxed mb-8">
            &ldquo;Day 1, it follows instructions.<br />
            Day 90, it has <span className="gradient-text text-glow">instinct</span>.&rdquo;
          </blockquote>
          <p className="text-[var(--color-text-dim)] text-lg leading-relaxed max-w-xl mx-auto">
            Even if a competitor copies every line of code, they start at Day 0.
            The accumulated intelligence specific to your business
            is the moat — and it deepens every day the system runs.
          </p>
        </div>
      </section>

      {/* ─── WAITLIST CTA ─── */}
      <section className="py-24 px-6" id="waitlist">
        <div className="divider max-w-6xl mx-auto mb-24" />

        <div className="max-w-3xl mx-auto text-center">
          <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
            Get early access
          </h2>
          <p className="text-[var(--color-text-muted)] text-lg mb-10 max-w-lg mx-auto">
            We&apos;re opening Fireside to a small group of early users.
            Join the waitlist and be first to try it.
          </p>

          <form
            className="flex flex-col sm:flex-row items-center justify-center gap-3"
            onSubmit={(e) => e.preventDefault()}
          >
            <input
              type="email"
              placeholder="you@example.com"
              className="waitlist-input"
              required
            />
            <button type="submit" className="cta whitespace-nowrap">
              Join Waitlist <span>→</span>
            </button>
          </form>
          <p className="text-[var(--color-text-dim)] text-xs mt-4">
            No spam, ever. We&apos;ll email you once when it&apos;s ready.
          </p>
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
            <a href="#features" className="hover:text-[var(--color-text-muted)] transition-colors">Features</a>
            <a href="#compare" className="hover:text-[var(--color-text-muted)] transition-colors">Compare</a>
            <a href="#waitlist" className="hover:text-[var(--color-text-muted)] transition-colors">Early Access</a>
          </div>
          <p className="text-sm text-[var(--color-text-dim)]">
            Built with 🔥 by the Fireside team
          </p>
        </div>
      </footer>
    </main>
  );
}

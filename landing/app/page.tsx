'use client';

import { useState, useEffect } from 'react';

export default function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [detectedOS, setDetectedOS] = useState<'windows' | 'mac' | 'linux'>('windows');

  useEffect(() => {
    const ua = navigator.userAgent.toLowerCase();
    if (ua.includes('mac')) setDetectedOS('mac');
    else if (ua.includes('linux')) setDetectedOS('linux');
    else setDetectedOS('windows');
  }, []);

  const tools = [
    '🎙️ Voice Input',
    '📊 Presentations',
    '📚 Knowledge Base',
    '📄 PDF Converter',
    '🌍 Translator',
    '🛡️ Message Guardian',
    '🔍 Web Search',
    '💻 Code Runner',
    '📁 File Manager',
    '🎨 Style Learning',
    '🧮 Calculator',
    '📝 Notes',
    '📧 Email Drafter',
    '🗂️ Task Planner',
    '🔗 Link Extractor',
    '📋 Clipboard',
    '🧠 Memory',
    '🌙 Dream Learning',
    '🐧 Companion',
    '⚡ Pipelines',
    '🔄 Format Converter',
    '🗃️ Smart Search',
  ];

  return (
    <main className="bg-grid min-h-screen">
      {/* ─── EMBER PARTICLES ─── */}
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

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-8 text-sm text-[var(--color-text-muted)]">
            <a href="#features" className="hover:text-[var(--color-foreground)] transition-colors">Features</a>
            <a href="#how" className="hover:text-[var(--color-foreground)] transition-colors">How It Works</a>
            <a href="#compare" className="hover:text-[var(--color-foreground)] transition-colors">Compare</a>
            <a href="#download" className="cta !py-2 !px-5 !text-sm !rounded-full">
              Download Free
            </a>
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden flex flex-col gap-1.5 p-2"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            <span className={`block w-5 h-0.5 bg-[var(--color-foreground)] transition-transform duration-200 ${mobileMenuOpen ? 'rotate-45 translate-y-2' : ''}`} />
            <span className={`block w-5 h-0.5 bg-[var(--color-foreground)] transition-opacity duration-200 ${mobileMenuOpen ? 'opacity-0' : ''}`} />
            <span className={`block w-5 h-0.5 bg-[var(--color-foreground)] transition-transform duration-200 ${mobileMenuOpen ? '-rotate-45 -translate-y-2' : ''}`} />
          </button>
        </div>

        {/* Mobile menu dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[var(--color-border)] bg-[var(--color-background)] px-6 py-4 flex flex-col gap-4 text-sm">
            <a href="#features" onClick={() => setMobileMenuOpen(false)} className="text-[var(--color-text-muted)] hover:text-[var(--color-foreground)]">Features</a>
            <a href="#how" onClick={() => setMobileMenuOpen(false)} className="text-[var(--color-text-muted)] hover:text-[var(--color-foreground)]">How It Works</a>
            <a href="#compare" onClick={() => setMobileMenuOpen(false)} className="text-[var(--color-text-muted)] hover:text-[var(--color-foreground)]">Compare</a>
            <a href="#download" onClick={() => setMobileMenuOpen(false)} className="cta !text-sm !py-3 text-center">Download Free</a>
          </div>
        )}
      </nav>

      {/* ─── HERO ─── */}
      <section className="pt-44 pb-28 px-6 text-center relative">
        <div className="hero-glow" />

        <div className="max-w-4xl mx-auto relative z-10">
          <div className="fade-up flex items-center justify-center gap-3 mb-8">
            <span className="badge badge-free">✦ Free for everyone</span>
          </div>

          <h1 className="fade-up fade-up-delay-1 font-[var(--font-serif)] text-5xl md:text-7xl font-bold leading-[1.1] tracking-tight mb-8">
            A personal AI that{" "}
            <span className="gradient-text">actually does the work</span>
          </h1>

          <p className="fade-up fade-up-delay-2 text-lg md:text-xl text-[var(--color-text-muted)] max-w-2xl mx-auto mb-12 leading-relaxed">
            Create presentations, search your files, draft emails, and talk to it
            with your voice — completely private, no subscription, no cloud.
          </p>

          <div className="fade-up fade-up-delay-3 flex flex-col sm:flex-row items-center justify-center gap-4 mb-6">
            {detectedOS === 'windows' ? (
              <a href="#download" className="cta-download">
                ⬇ Download for Windows <span className="text-lg">→</span>
              </a>
            ) : detectedOS === 'mac' ? (
              <a href="#download" className="cta-download">
                ⬇ Download for Mac <span className="text-lg">→</span>
              </a>
            ) : (
              <a href="#download" className="cta-download">
                ⬇ Install for Linux <span className="text-lg">→</span>
              </a>
            )}
            <a href="#how" className="cta cta-outline">
              See How It Works
            </a>
          </div>
          <p className="fade-up fade-up-delay-4 text-[var(--color-text-dim)] text-sm">
            Works on Windows, Mac, and Linux · No account needed
          </p>
        </div>
      </section>

      {/* ─── STATS BAR ─── */}
      <section className="py-10 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="stat-item">
            <div className="stat-value gradient-text">22</div>
            <div className="stat-label">Built-in Tools</div>
          </div>
          <div className="stat-item">
            <div className="stat-value gradient-text">$0</div>
            <div className="stat-label">Always Free</div>
          </div>
          <div className="stat-item">
            <div className="stat-value gradient-text">2 min</div>
            <div className="stat-label">Setup Time</div>
          </div>
          <div className="stat-item">
            <div className="stat-value gradient-text">100%</div>
            <div className="stat-label">Private &amp; Offline</div>
          </div>
        </div>
      </section>

      {/* ─── KEY FEATURES ─── */}
      <section className="py-24 px-6" id="features">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
              What can Fireside <span className="gradient-text">do for you?</span>
            </h2>
            <p className="text-[var(--color-text-muted)] text-lg max-w-xl mx-auto">
              Real tools that create, remember, and get things done — not just chat.
            </p>
          </div>

          {/* Primary features — large cards, outcome-focused */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div className="glass feature-card-lg p-8 fade-up">
              <div className="feature-icon">🎙️</div>
              <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Talk to It</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed">
                Just speak — it types what you say. No internet needed, no recordings
                sent anywhere. Your voice stays on your computer.
              </p>
            </div>

            <div className="glass feature-card-lg p-8 fade-up fade-up-delay-1">
              <div className="feature-icon">📊</div>
              <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Create Presentations</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed">
                Tell it what you need, get polished PowerPoint slides in seconds.
                It can even learn your company&apos;s style from an existing file.
              </p>
            </div>

            <div className="glass feature-card-lg p-8 fade-up fade-up-delay-2">
              <div className="feature-icon">📚</div>
              <h3 className="font-[var(--font-display)] text-xl font-bold mb-3">Ask About Your Files</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed">
                Upload documents and your AI reads and remembers them.
                Ask questions about your own files and get instant answers.
              </p>
            </div>
          </div>

          {/* Secondary features — simpler language */}
          <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="glass p-6 fade-up">
              <div className="feature-icon">🌍</div>
              <h3 className="font-[var(--font-display)] text-sm font-bold mb-2">Translate Anything</h3>
              <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">
                Real-time translation in any language. Understands context, not just words.
              </p>
            </div>

            <div className="glass p-6 fade-up fade-up-delay-1">
              <div className="feature-icon">📄</div>
              <h3 className="font-[var(--font-display)] text-sm font-bold mb-2">Convert Documents</h3>
              <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">
                Turn Word, PowerPoint, and Excel files into PDFs in one click.
              </p>
            </div>

            <div className="glass p-6 fade-up fade-up-delay-2">
              <div className="feature-icon">📧</div>
              <h3 className="font-[var(--font-display)] text-sm font-bold mb-2">Draft Emails</h3>
              <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">
                Tell it what you want to say. It writes a polished email in your tone.
              </p>
            </div>

            <div className="glass p-6 fade-up">
              <div className="feature-icon">🧠</div>
              <h3 className="font-[var(--font-display)] text-sm font-bold mb-2">Remembers Everything</h3>
              <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">
                It remembers your past conversations and learns what works best for you.
              </p>
            </div>

            <div className="glass p-6 fade-up fade-up-delay-1">
              <div className="feature-icon">🌙</div>
              <h3 className="font-[var(--font-display)] text-sm font-bold mb-2">Gets Smarter Overnight</h3>
              <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">
                While you sleep, it reviews everything from the day and improves itself.
              </p>
            </div>

            <div className="glass p-6 fade-up fade-up-delay-2">
              <div className="feature-icon">🐧</div>
              <h3 className="font-[var(--font-display)] text-sm font-bold mb-2">AI Companion</h3>
              <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">
                Pick a pet that lives in your AI. It levels up and grows alongside you.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── TOOLS MARQUEE ─── */}
      <section className="py-16 px-6" id="tools">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
              22 tools, <span className="gradient-text">one app</span>
            </h2>
            <p className="text-[var(--color-text-muted)] text-lg max-w-xl mx-auto">
              Everything you need in one place — no extra subscriptions or accounts.
            </p>
          </div>

          <div className="marquee-container py-4">
            <div className="marquee-track">
              {[...tools, ...tools].map((tool, i) => (
                <span key={i} className="marquee-pill">{tool}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section className="py-24 px-6" id="how">
        <div className="divider max-w-6xl mx-auto mb-24" />

        <div className="max-w-4xl mx-auto text-center mb-16">
          <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
            Up and running in <span className="gradient-text">2 minutes</span>
          </h2>
          <p className="text-[var(--color-text-muted)] text-lg">
            No technical knowledge required. Download, open, start chatting.
          </p>
        </div>

        <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-6">
          <div className="glass p-8 text-center">
            <div className="text-3xl mb-4">1️⃣</div>
            <h3 className="font-[var(--font-display)] text-lg font-bold mb-3">Download</h3>
            <p className="text-[var(--color-text-muted)] leading-relaxed text-sm">
              Click the download button. It works on Windows, Mac, and Linux.
            </p>
          </div>
          <div className="glass p-8 text-center">
            <div className="text-3xl mb-4">2️⃣</div>
            <h3 className="font-[var(--font-display)] text-lg font-bold mb-3">Open</h3>
            <p className="text-[var(--color-text-muted)] leading-relaxed text-sm">
              Double-click to install. It sets everything up automatically —
              no folders to find, no settings to configure.
            </p>
          </div>
          <div className="glass p-8 text-center">
            <div className="text-3xl mb-4">3️⃣</div>
            <h3 className="font-[var(--font-display)] text-lg font-bold mb-3">Start Chatting</h3>
            <p className="text-[var(--color-text-muted)] leading-relaxed text-sm">
              Ask it anything — type or use your voice. It&apos;s ready to help
              immediately.
            </p>
          </div>
        </div>
      </section>

      {/* ─── SMARTER OVER TIME ─── */}
      <section className="py-24 px-6">
        <div className="divider max-w-6xl mx-auto mb-24" />

        <div className="max-w-4xl mx-auto text-center mb-16">
          <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
            The more you use it, the <span className="gradient-text-rose">smarter it gets</span>
          </h2>
          <p className="text-[var(--color-text-muted)] text-lg max-w-2xl mx-auto">
            Most AI tools forget everything between conversations.
            Fireside remembers, learns from experience, and improves every day.
          </p>
        </div>

        <div className="max-w-3xl mx-auto grid md:grid-cols-3 gap-6 text-center">
          <div className="glass p-6">
            <div className="text-2xl mb-3">📋</div>
            <h4 className="font-[var(--font-display)] font-bold mb-2 text-sm">Day 1</h4>
            <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">
              It follows your instructions and does what you ask.
            </p>
          </div>
          <div className="glass p-6">
            <div className="text-2xl mb-3">🌙</div>
            <h4 className="font-[var(--font-display)] font-bold mb-2 text-sm">Each Night</h4>
            <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">
              While you sleep, it reviews everything and learns what works best.
            </p>
          </div>
          <div className="glass p-6">
            <div className="text-2xl mb-3">☀️</div>
            <h4 className="font-[var(--font-display)] font-bold mb-2 text-sm">Day 90</h4>
            <p className="text-[var(--color-text-dim)] text-xs leading-relaxed">
              It knows your preferences, your writing style, and how you work.
            </p>
          </div>
        </div>
      </section>

      {/* ─── COMPANION (compact) ─── */}
      <section className="py-16 px-6" id="companions">
        <div className="max-w-4xl mx-auto">
          <div className="glass p-8 glow-amber">
            <div className="text-center mb-6">
              <h3 className="font-[var(--font-display)] text-2xl font-bold mb-2">
                Pick a <span className="gradient-text">companion</span>
              </h3>
              <p className="text-[var(--color-text-muted)] text-sm max-w-md mx-auto">
                Your AI comes with a virtual pet that grows with you.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-6">
              {[
                { emoji: '🐱', name: 'Cat' },
                { emoji: '🐶', name: 'Dog' },
                { emoji: '🐧', name: 'Penguin' },
                { emoji: '🦊', name: 'Fox' },
                { emoji: '🦉', name: 'Owl' },
                { emoji: '🐉', name: 'Dragon' },
              ].map((c) => (
                <div key={c.name} className="text-center group cursor-default">
                  <div className="text-3xl group-hover:scale-110 transition-transform duration-300 mb-1">{c.emoji}</div>
                  <p className="text-xs text-[var(--color-text-dim)] font-medium">{c.name}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── MOBILE APP ─── */}
      <section className="py-16 px-6" id="mobile">
        <div className="max-w-5xl mx-auto">
          <div className="glass p-10 glow-amber">
            <div className="flex flex-col md:flex-row items-center gap-10">
              <div className="flex-1 text-center md:text-left">
                <span className="badge badge-free mb-4 inline-block">Available Now</span>
                <h3 className="font-[var(--font-display)] text-2xl md:text-3xl font-bold mb-3">
                  On your computer <span className="gradient-text">&amp; your phone.</span>
                </h3>
                <p className="text-[var(--color-text-muted)] leading-relaxed max-w-lg mb-4">
                  Take your AI with you. Get morning briefings on the go,
                  chat from anywhere, and keep everything synced between your
                  desktop and mobile.
                </p>
                <p className="text-sm text-[var(--color-text-dim)]">
                  Available on iOS &amp; Android
                </p>
              </div>
              <div className="phone-frame">
                <span className="text-4xl mb-3">🐧</span>
                <p className="text-xs text-[var(--color-text-dim)] text-center mt-2">
                  Fireside Mobile
                </p>
                <div className="mt-4 flex flex-col gap-2 w-full">
                  <div className="h-2 rounded-full bg-[var(--color-surface-2)] w-full"></div>
                  <div className="h-2 rounded-full bg-[var(--color-surface-2)] w-3/4"></div>
                  <div className="h-2 rounded-full bg-[var(--color-surface-2)] w-1/2"></div>
                </div>
              </div>
            </div>
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
              You might already use AI tools. Here&apos;s how Fireside is different.
            </p>
          </div>

          <div className="glass overflow-hidden overflow-x-auto">
            <table className="compare-table">
              <thead>
                <tr>
                  <th className="text-[var(--color-text-dim)] font-medium"></th>
                  <th className="text-center text-[var(--color-text-muted)] font-medium">ChatGPT / Gemini</th>
                  <th className="text-center text-[var(--color-text-muted)] font-medium">Microsoft Copilot</th>
                  <th className="text-center text-[var(--color-amber)] font-bold">Fireside</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Works without internet</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-check">✔ Fully offline</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Your data stays private</td>
                  <td className="text-center compare-no">Sent to cloud</td>
                  <td className="text-center compare-no">Sent to cloud</td>
                  <td className="text-center compare-check">✔ Never leaves your device</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Voice input</td>
                  <td className="text-center">Cloud only</td>
                  <td className="text-center">Cloud only</td>
                  <td className="text-center compare-check">✔ Works offline</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Creates presentations</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center">With 365 license</td>
                  <td className="text-center compare-check">✔ Built in, free</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Searches your own files</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center">Limited</td>
                  <td className="text-center compare-check">✔ Full knowledge base</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Remembers past conversations</td>
                  <td className="text-center compare-no">✗ Resets each chat</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-check">✔ Permanent memory</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Learns your style over time</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-no">✗</td>
                  <td className="text-center compare-check">✔ Gets smarter daily</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Desktop app</td>
                  <td className="text-center compare-no">Browser only</td>
                  <td className="text-center">In Office apps</td>
                  <td className="text-center compare-check">✔ Standalone app</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Mobile app</td>
                  <td className="text-center">✔</td>
                  <td className="text-center">✔</td>
                  <td className="text-center compare-check">✔ Synced to desktop</td>
                </tr>
                <tr>
                  <td className="font-medium text-[var(--color-foreground)]">Monthly cost</td>
                  <td className="text-center">$20/mo</td>
                  <td className="text-center">$30/mo</td>
                  <td className="text-center compare-check">Free</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ─── QUOTE ─── */}
      <section className="py-28 px-6">
        <div className="divider max-w-6xl mx-auto mb-28" />

        <div className="max-w-3xl mx-auto text-center">
          <blockquote className="text-2xl md:text-4xl font-[var(--font-serif)] font-bold leading-relaxed mb-8">
            &ldquo;Day 1, it follows instructions.<br />
            Day 90, it <span className="gradient-text text-glow">knows how you work</span>.&rdquo;
          </blockquote>
          <p className="text-[var(--color-text-dim)] text-lg leading-relaxed max-w-xl mx-auto">
            The longer you use Fireside, the better it understands you.
            That&apos;s something no cloud AI can offer — because they forget you
            the moment you close the tab.
          </p>
        </div>
      </section>

      {/* ─── ABOUT / TRUST ─── */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="glass p-10">
            <p className="text-lg md:text-xl text-[var(--color-text-muted)] leading-relaxed mb-6">
              Independent. Open source. Community-supported.
            </p>
            <p className="text-[var(--color-text-dim)] text-sm leading-relaxed max-w-lg mx-auto">
              Fireside is an open-source project built on the belief that your data
              should stay yours and your AI should get smarter every day. The code
              is public, the community is growing, and the product is free.
            </p>
          </div>
        </div>
      </section>

      {/* ─── DOWNLOAD CTA ─── */}
      <section className="py-24 px-6" id="download">
        <div className="divider max-w-6xl mx-auto mb-24" />

        <div className="max-w-4xl mx-auto text-center">
          <h2 className="font-[var(--font-display)] text-3xl md:text-5xl font-bold mb-4">
            Ready to try it?
          </h2>
          <p className="text-[var(--color-text-muted)] text-lg mb-10 max-w-lg mx-auto">
            Download Fireside and start chatting with your own AI in 2 minutes.
          </p>

          <div className="grid sm:grid-cols-2 gap-6 max-w-2xl mx-auto">
            <div className="download-card">
              <div className="text-4xl mb-4">🖥️</div>
              <h3 className="font-[var(--font-display)] text-lg font-bold mb-2">Windows</h3>
              <p className="text-[var(--color-text-dim)] text-sm mb-6">
                Download the installer. Double-click and you&apos;re running.
              </p>
              <a href="#" className="cta !text-sm !py-3 !px-6 w-full justify-center">
                ⬇ Download for Windows
              </a>
            </div>

            <div className="download-card">
              <div className="text-4xl mb-4">🍎</div>
              <h3 className="font-[var(--font-display)] text-lg font-bold mb-2">Mac &amp; Linux</h3>
              <p className="text-[var(--color-text-dim)] text-sm mb-6">
                Run one command in your terminal to install and get started.
              </p>
              <div className="code-block !rounded-xl !p-4 !text-xs text-left">
                <div><span className="prompt">$</span> curl -fsSL getfireside.ai/install | bash</div>
              </div>
            </div>
          </div>

          <p className="text-[var(--color-text-dim)] text-sm mt-8">
            Free for individuals and small teams · Enterprise plans coming soon
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
            <a href="/privacy" className="hover:text-[var(--color-text-muted)] transition-colors">Privacy</a>
            <a href="#download" className="hover:text-[var(--color-text-muted)] transition-colors">Download</a>
          </div>
          <p className="text-sm text-[var(--color-text-dim)]">
            Built with 🔥 by the Fireside team
          </p>
        </div>
      </footer>
    </main>
  );
}

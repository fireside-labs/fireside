"use client";

import { useState } from "react";
import Link from "next/link";

const DISCOVERIES = [
    { text: "Your emails are usually shorter on Fridays", confidence: 82, daysAgo: 2 },
    { text: "Your spreadsheets always have headers in row 1", confidence: 97, daysAgo: 5 },
    { text: "You prefer bullet points over paragraphs", confidence: 71, daysAgo: 1 },
    { text: "Code reviews take you longer on Mondays", confidence: 65, daysAgo: 3 },
];

const OVERNIGHT = [
    { icon: "🌙", text: "Your AI reviewed yesterday's work at 3:00 AM" },
    { icon: "🧪", text: "Tested 247 things it knows — 16 were weak, so it studied more." },
    { icon: "💎", text: 'Updated its "big picture" understanding of how you work.' },
];

export default function LearningPage() {
    const [showAdvanced, setShowAdvanced] = useState(false);

    return (
        <div className="max-w-3xl mx-auto">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <span>📊</span> How It&apos;s Learning
                </h1>
                <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                    Your AI learns from every task. Here&apos;s what it knows and how reliable that knowledge is.
                </p>
            </div>

            {/* Overview stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="glass-card p-5 text-center">
                    <span className="text-2xl mb-2 block">🧠</span>
                    <p className="text-3xl font-bold text-white mb-1">247</p>
                    <p className="text-xs text-[var(--color-rune-dim)]">Things it knows</p>
                </div>
                <div className="glass-card p-5 text-center">
                    <span className="text-2xl mb-2 block">✅</span>
                    <p className="text-3xl font-bold text-[var(--color-neon)] mb-1">94%</p>
                    <p className="text-xs text-[var(--color-rune-dim)]">Reliable knowledge</p>
                </div>
                <div className="glass-card p-5 text-center">
                    <span className="text-2xl mb-2 block">📈</span>
                    <p className="text-lg font-bold text-white mb-1">Yes — +12%</p>
                    <p className="text-xs text-[var(--color-rune-dim)]">Getting smarter this week</p>
                </div>
            </div>

            {/* Recent discoveries */}
            <div className="glass-card p-5 mb-6">
                <h3 className="text-white font-semibold mb-4">Recent discoveries</h3>
                <div className="space-y-4">
                    {DISCOVERIES.map((d, i) => (
                        <div key={i}>
                            <div className="flex items-start gap-3 mb-1.5">
                                <span className="text-lg mt-0.5">💡</span>
                                <div className="flex-1">
                                    <p className="text-sm text-[var(--color-rune)]">&quot;{d.text}&quot;</p>
                                    <div className="flex items-center gap-3 mt-1.5">
                                        {/* Confidence bar */}
                                        <div className="flex-1 h-2 rounded-full bg-[var(--color-glass)] max-w-[120px]">
                                            <div
                                                className="h-2 rounded-full transition-all"
                                                style={{
                                                    width: `${d.confidence}%`,
                                                    background: d.confidence >= 90
                                                        ? "var(--color-neon)"
                                                        : d.confidence >= 70
                                                            ? "var(--color-warning)"
                                                            : "var(--color-rune-dim)",
                                                }}
                                            />
                                        </div>
                                        <span className="text-xs text-[var(--color-rune-dim)]">{d.confidence}%</span>
                                        <span className="text-xs text-[var(--color-rune-dim)]">· {d.daysAgo}d ago</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Last night's learning */}
            <div className="glass-card p-5 mb-6">
                <h3 className="text-white font-semibold mb-4">Last night&apos;s learning</h3>
                <div className="space-y-3">
                    {OVERNIGHT.map((item, i) => (
                        <div key={i} className="flex items-start gap-3">
                            <span className="text-lg">{item.icon}</span>
                            <p className="text-sm text-[var(--color-rune)]">{item.text}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Advanced links */}
            <div className="glass-card p-5">
                <button
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="text-sm text-[var(--color-rune-dim)] hover:text-[var(--color-rune)] transition-colors"
                >
                    {showAdvanced ? "▾" : "▸"} Advanced — detailed views
                </button>
                {showAdvanced && (
                    <div className="mt-3 grid grid-cols-2 gap-2">
                        <Link href="/warroom" className="glass-card p-3 text-center text-sm text-[var(--color-rune)] hover:text-white transition-colors">
                            📊 View discoveries
                        </Link>
                        <Link href="/crucible" className="glass-card p-3 text-center text-sm text-[var(--color-rune)] hover:text-white transition-colors">
                            🧪 View knowledge tests
                        </Link>
                        <Link href="/debate" className="glass-card p-3 text-center text-sm text-[var(--color-rune)] hover:text-white transition-colors">
                            🗣️ View debates
                        </Link>
                        <Link href="/warroom" className="glass-card p-3 text-center text-sm text-[var(--color-rune)] hover:text-white transition-colors">
                            📄 View raw data
                        </Link>
                    </div>
                )}
            </div>
        </div>
    );
}

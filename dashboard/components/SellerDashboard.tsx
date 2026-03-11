"use client";

import { useState } from "react";

const EARNINGS_DATA = [
    { day: "Mon", amount: 12 },
    { day: "Tue", amount: 8 },
    { day: "Wed", amount: 22 },
    { day: "Thu", amount: 15 },
    { day: "Fri", amount: 31 },
    { day: "Sat", amount: 18 },
    { day: "Sun", amount: 25 },
];

const SALES = [
    { item: "Code Warrior Agent", type: "Agent", sales: 14, revenue: 69.86, emoji: "⚔️" },
    { item: "Neon Theme Pack", type: "Theme", sales: 8, revenue: 27.44, emoji: "🌈" },
    { item: "Calm Voice Pack", type: "Voice", sales: 5, revenue: 17.47, emoji: "🎤" },
];

export default function SellerDashboard() {
    const [period, setPeriod] = useState<"week" | "month" | "all">("week");
    const [stripeConnected, setStripeConnected] = useState(false);

    const totalRevenue = SALES.reduce((sum, s) => sum + s.revenue, 0);
    const platformFee = totalRevenue * 0.3;
    const yourEarnings = totalRevenue - platformFee;
    const maxAmount = Math.max(...EARNINGS_DATA.map((d) => d.amount));

    if (!stripeConnected) {
        return (
            <div className="glass-card p-6 text-center">
                <span className="text-5xl block mb-4">💳</span>
                <h3 className="text-white font-semibold mb-2">Connect Stripe to start selling</h3>
                <p className="text-xs text-[var(--color-rune-dim)] mb-4">
                    Create and sell agents, themes, voice packs, and more. You earn 70% of each sale.
                </p>
                <button onClick={() => setStripeConnected(true)} className="btn-neon px-6 py-2.5 text-sm">
                    Connect Stripe →
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Revenue Summary */}
            <div className="grid grid-cols-3 gap-3">
                <div className="glass-card p-4 text-center">
                    <p className="text-xs text-[var(--color-rune-dim)]">Total Revenue</p>
                    <p className="text-2xl text-white font-bold mt-1">${totalRevenue.toFixed(2)}</p>
                </div>
                <div className="glass-card p-4 text-center">
                    <p className="text-xs text-[var(--color-rune-dim)]">Platform Fee (30%)</p>
                    <p className="text-2xl text-[var(--color-warning)] font-bold mt-1">-${platformFee.toFixed(2)}</p>
                </div>
                <div className="glass-card p-4 text-center">
                    <p className="text-xs text-[var(--color-rune-dim)]">Your Earnings</p>
                    <p className="text-2xl text-[var(--color-neon)] font-bold mt-1">${yourEarnings.toFixed(2)}</p>
                </div>
            </div>

            {/* Earnings Chart */}
            <div className="glass-card p-5">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-white font-semibold">Earnings</h3>
                    <div className="flex gap-1">
                        {(["week", "month", "all"] as const).map((p) => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={`px-2.5 py-1 rounded text-[10px] transition-colors ${period === p
                                        ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)]"
                                        : "text-[var(--color-rune-dim)] hover:text-white"
                                    }`}
                            >
                                {p === "week" ? "7d" : p === "month" ? "30d" : "All"}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Bar chart */}
                <div className="flex items-end gap-2 h-32">
                    {EARNINGS_DATA.map((d) => (
                        <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                            <span className="text-[9px] text-[var(--color-rune-dim)]">${d.amount}</span>
                            <div
                                className="w-full rounded-t transition-all"
                                style={{
                                    height: `${(d.amount / maxAmount) * 100}%`,
                                    background: "linear-gradient(180deg, var(--color-neon), var(--color-neon-dim))",
                                    opacity: 0.8,
                                    minHeight: 4,
                                }}
                            />
                            <span className="text-[9px] text-[var(--color-rune-dim)]">{d.day}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Sales Table */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-3">Sales by Item</h3>
                <div className="space-y-2">
                    {SALES.map((s) => (
                        <div key={s.item} className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--color-glass)]">
                            <div className="flex items-center gap-2.5">
                                <span className="text-xl">{s.emoji}</span>
                                <div>
                                    <p className="text-sm text-white">{s.item}</p>
                                    <p className="text-[10px] text-[var(--color-rune-dim)]">{s.type}</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-sm text-white font-medium">${s.revenue.toFixed(2)}</p>
                                <p className="text-[10px] text-[var(--color-rune-dim)]">{s.sales} sales</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Create Listing */}
            <button className="btn-neon w-full py-3 text-sm">
                + Create New Listing
            </button>
        </div>
    );
}

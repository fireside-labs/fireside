"use client";

interface Purchase {
    id: string;
    name: string;
    emoji: string;
    type: string;
    price: number;
    date: string;
    installed: boolean;
}

const MOCK_PURCHASES: Purchase[] = [
    { id: "1", name: "Smart & Fast", emoji: "⚡", type: "Brain", price: 0, date: "Mar 8", installed: true },
    { id: "2", name: "Valhalla Theme", emoji: "🏰", type: "Theme", price: 0, date: "Mar 8", installed: true },
    { id: "3", name: "Office Theme", emoji: "🏢", type: "Theme", price: 0, date: "Mar 10", installed: false },
];

export default function PurchaseHistory() {
    return (
        <div className="glass-card p-5">
            <h3 className="text-white font-semibold mb-3">My Purchases</h3>
            {MOCK_PURCHASES.length === 0 ? (
                <p className="text-xs text-[var(--color-rune-dim)]">No purchases yet.</p>
            ) : (
                <div className="space-y-2">
                    {MOCK_PURCHASES.map((p) => (
                        <div key={p.id} className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--color-glass)]">
                            <div className="flex items-center gap-2.5">
                                <span className="text-xl">{p.emoji}</span>
                                <div>
                                    <p className="text-sm text-white">{p.name}</p>
                                    <p className="text-[10px] text-[var(--color-rune-dim)]">{p.type} · {p.date}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-[var(--color-rune-dim)]">
                                    {p.price === 0 ? "Free" : `$${p.price.toFixed(2)}`}
                                </span>
                                {p.installed ? (
                                    <span className="text-[10px] text-[var(--color-neon)]">✅ Installed</span>
                                ) : (
                                    <button className="text-[10px] text-[var(--color-neon)] hover:underline">Install</button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

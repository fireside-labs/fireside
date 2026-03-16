"use client";

import { useState, useEffect } from "react";

interface Purchase {
    plugin_id: string;
    plugin_name: string;
    price: number;
    purchased_at: string;
    icon?: string;
}

export default function PurchaseHistory() {
    const [purchases, setPurchases] = useState<Purchase[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://127.0.0.1:8765/api/v1/store/purchases")
            .then(res => res.ok ? res.json() : { purchases: [] })
            .then(data => {
                const items = data.purchases || data || [];
                setPurchases(Array.isArray(items) ? items : []);
            })
            .catch(() => setPurchases([]))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="glass-card p-5">
            <h3 className="text-white font-semibold mb-3">My Purchases</h3>
            {loading ? (
                <div className="space-y-2">
                    {[1, 2].map(i => (
                        <div key={i} className="h-12 rounded-lg bg-[var(--color-glass)] animate-pulse" />
                    ))}
                </div>
            ) : purchases.length === 0 ? (
                <div className="text-center py-8">
                    <span className="text-3xl block mb-2">🛒</span>
                    <p className="text-sm text-[var(--color-rune-dim)]">No purchases yet. Browse the store to find useful add-ons.</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {purchases.map((p) => (
                        <div key={p.plugin_id} className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--color-glass)]">
                            <div className="flex items-center gap-2.5">
                                <span className="text-xl">{p.icon || "📦"}</span>
                                <div>
                                    <p className="text-sm text-white">{p.plugin_name}</p>
                                    <p className="text-[10px] text-[var(--color-rune-dim)]">Plugin · {new Date(p.purchased_at).toLocaleDateString()}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-[var(--color-rune-dim)]">
                                    {p.price === 0 ? "Free" : `$${p.price.toFixed(2)}`}
                                </span>
                                <span className="text-[10px] text-[var(--color-neon)]">✅ Installed</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

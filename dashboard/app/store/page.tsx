"use client";

import { useState, useEffect } from "react";
import StoreTabs from "@/components/StoreTabs";
import ItemCard from "@/components/ItemCard";
import PurchaseHistory from "@/components/PurchaseHistory";

type StoreItem = {
    id: string;
    name: string;
    version: string;
    creator: string;
    description: string;
    emoji: string;
    price: number;
    downloads: number;
    category: string;
    purchased: boolean;
};

const CATEGORY_META: Record<string, { label: string, emoji: string }> = {
    productivity: { label: "Productivity", emoji: "📈" },
    integration: { label: "Integration", emoji: "🔗" },
    ops: { label: "Ops", emoji: "⚙️" },
    interface: { label: "Interface", emoji: "🖥️" },
    analytics: { label: "Analytics", emoji: "📊" },
    intelligence: { label: "Intelligence", emoji: "🧠" },
    agents: { label: "Agents", emoji: "🤖" },
    themes: { label: "Themes", emoji: "🏰" },
};

export default function StorePage() {
    const [tab, setTab] = useState("productivity");
    const [showPurchases, setShowPurchases] = useState(false);
    const [storeItems, setStoreItems] = useState<Record<string, StoreItem[]>>({});
    const [loading, setLoading] = useState(true);

    // F4 / F1: Load from real backend.
    useEffect(() => {
        fetch("http://127.0.0.1:8765/api/v1/store/plugins")
            .then(res => res.ok ? res.json() : { plugins: [] })
            .then(data => {
                const grouped: Record<string, StoreItem[]> = {};
                const plugins = data.plugins || [];
                plugins.forEach((p: any) => {
                    const cat = p.category || "plugins";
                    if (!grouped[cat]) grouped[cat] = [];
                    grouped[cat].push({
                        id: p.id,
                        name: p.name,
                        version: p.version,
                        creator: p.author || "creator",
                        description: p.description || "",
                        emoji: p.icon || "🧩",
                        price: p.price || 0,
                        downloads: p.downloads || 0,
                        category: cat,
                        purchased: p.purchased || false,
                    });
                });
                setStoreItems(grouped);
                const firstCat = Object.keys(grouped)[0];
                if (firstCat && !grouped[tab]) setTab(firstCat);
            })
            .catch(() => { /* error handling */ })
            .finally(() => setLoading(false));
    }, []);

    const items = storeItems[tab] || [];
    const tabCounts = Object.fromEntries(Object.entries(storeItems).map(([k, v]) => [k, v.length]));

    const dynamicTabs = Object.keys(storeItems).map(cat => ({
        id: cat,
        label: CATEGORY_META[cat]?.label || cat.charAt(0).toUpperCase() + cat.slice(1),
        emoji: CATEGORY_META[cat]?.emoji || "🧩"
    }));

    return (
        <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <span>🏪</span> Store
                    </h1>
                    <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                        Plugins, agents, themes and more. Created by the community.
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setShowPurchases(!showPurchases)}
                        className="text-xs text-[var(--color-neon)] hover:underline"
                    >
                        {showPurchases ? "← Back to Store" : "My Purchases"}
                    </button>
                    <a href="/store/sell" className="text-xs px-3 py-1.5 rounded-lg border border-[var(--color-glass-border)] text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)] transition-colors">
                        💰 Sell
                    </a>
                </div>
            </div>

            {showPurchases ? (
                <PurchaseHistory />
            ) : (
                <>
                    {/* Tabs */}
                    {!loading && dynamicTabs.length > 0 && (
                        <StoreTabs tabs={dynamicTabs} selected={tab} onSelect={setTab} counts={tabCounts} />
                    )}

                    {/* Items Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
                        {items.map((item) => (
                            <ItemCard
                                key={item.id}
                                id={item.id}
                                name={item.name}
                                creator={item.creator}
                                description={item.description}
                                emoji={item.emoji}
                                price={item.price}
                                rating={5} // Placeholder since plugins endpoint doesn't return rating
                                reviews={item.downloads}
                                purchased={item.purchased}
                            />
                        ))}
                    </div>

                    {/* Loading / No items */}
                    {loading && (
                        <div className="text-center py-12">
                            <span className="text-4xl block mb-3 animate-pulse">⏳</span>
                            <p className="text-sm text-[var(--color-rune-dim)]">Loading store...</p>
                        </div>
                    )}
                    {!loading && items.length === 0 && (
                        <div className="text-center py-12">
                            <span className="text-4xl block mb-3">🔍</span>
                            <p className="text-sm text-[var(--color-rune-dim)]">No items here yet.</p>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

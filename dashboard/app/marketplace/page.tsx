"use client";

import { useEffect, useState } from "react";
import {
    getMarketplaceAgents,
    getInstalledAgents,
    installAgent,
    exportAgent,
    MarketplaceAgent,
    AgentCategory,
} from "@/lib/api";
import AgentCard from "@/components/AgentCard";
import { useToast } from "@/components/Toast";
import { SkeletonCard } from "@/components/LoadingSkeleton";

const CATEGORIES: { value: AgentCategory | "all"; label: string }[] = [
    { value: "all", label: "All" },
    { value: "sales", label: "Sales & Marketing" },
    { value: "coding", label: "Code & Engineering" },
    { value: "research", label: "Research & Analysis" },
    { value: "creative", label: "Creative" },
    { value: "operations", label: "Operations" },
    { value: "domain", label: "Domain Expert" },
];

const SORT_OPTIONS = [
    { value: "rating", label: "Top Rated" },
    { value: "installs", label: "Most Installed" },
    { value: "crucible", label: "Most Reliable" },
    { value: "price-low", label: "Price: Low → High" },
    { value: "price-high", label: "Price: High → Low" },
];

export default function MarketplacePage() {
    const [agents, setAgents] = useState<MarketplaceAgent[]>([]);
    const [installed, setInstalled] = useState<MarketplaceAgent[]>([]);
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState<"browse" | "mine">("browse");
    const [category, setCategory] = useState<AgentCategory | "all">("all");
    const [search, setSearch] = useState("");
    const [sort, setSort] = useState("rating");
    const { toast } = useToast();

    useEffect(() => {
        Promise.all([getMarketplaceAgents(), getInstalledAgents()]).then(
            ([all, mine]) => {
                setAgents(all);
                setInstalled(mine);
                setLoading(false);
            }
        );
    }, []);

    const handleExport = async (name: string) => {
        await exportAgent(name);
        toast(`Exported ${name}.valhalla — download starting`, "success");
    };

    const handleRemove = (name: string) => {
        setInstalled((prev) => prev.filter((a) => a.name !== name));
        toast(`${name} removed from your devices`, "info");
    };

    // Filter and sort
    let filtered = agents;
    if (category !== "all") filtered = filtered.filter((a) => a.category === category);
    if (search) {
        const q = search.toLowerCase();
        filtered = filtered.filter(
            (a) =>
                a.name.toLowerCase().includes(q) ||
                a.description.toLowerCase().includes(q) ||
                a.personality_traits.some((t) => t.toLowerCase().includes(q))
        );
    }

    switch (sort) {
        case "rating": filtered = [...filtered].sort((a, b) => b.rating - a.rating); break;
        case "installs": filtered = [...filtered].sort((a, b) => b.installs - a.installs); break;
        case "crucible": filtered = [...filtered].sort((a, b) => b.crucible_survival - a.crucible_survival); break;
        case "price-low": filtered = [...filtered].sort((a, b) => a.price - b.price); break;
        case "price-high": filtered = [...filtered].sort((a, b) => b.price - a.price); break;
    }

    return (
        <div className="page-enter max-w-6xl">
            {/* Header */}
            <div className="mb-6 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold mb-1">
                        <span className="text-[var(--color-neon)]">🏪</span> Store
                    </h1>
                    <p className="text-sm text-[var(--color-rune-dim)]">
                        Pre-trained AI assistants ready to use.
                    </p>
                </div>
                <button className="btn-neon px-4 py-2 text-sm">📤 Publish Agent</button>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-6 mb-6 border-b border-[var(--color-glass-border)]">
                <button
                    onClick={() => setTab("browse")}
                    className="text-sm font-medium pb-3 transition-colors"
                    style={{
                        color: tab === "browse" ? "var(--color-neon)" : "var(--color-rune-dim)",
                        borderBottom: tab === "browse" ? "2px solid var(--color-neon)" : "2px solid transparent",
                    }}
                >
                    Browse ({agents.length})
                </button>
                <button
                    onClick={() => setTab("mine")}
                    className="text-sm font-medium pb-3 transition-colors"
                    style={{
                        color: tab === "mine" ? "var(--color-neon)" : "var(--color-rune-dim)",
                        borderBottom: tab === "mine" ? "2px solid var(--color-neon)" : "2px solid transparent",
                    }}
                >
                    My Agents ({installed.length})
                </button>
            </div>

            {/* Browse Tab */}
            {tab === "browse" && (
                <>
                    {/* Filters */}
                    <div className="flex flex-wrap items-center gap-3 mb-6">
                        <input
                            type="text"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Search agents..."
                            className="flex-1 min-w-[200px] px-4 py-2 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white placeholder-[var(--color-rune-dim)] text-sm outline-none focus:border-[var(--color-neon)] transition-colors"
                        />
                        <select
                            value={category}
                            onChange={(e) => setCategory(e.target.value as AgentCategory | "all")}
                            className="px-3 py-2 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none"
                        >
                            {CATEGORIES.map((c) => (
                                <option key={c.value} value={c.value}>{c.label}</option>
                            ))}
                        </select>
                        <select
                            value={sort}
                            onChange={(e) => setSort(e.target.value)}
                            className="px-3 py-2 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none"
                        >
                            {SORT_OPTIONS.map((s) => (
                                <option key={s.value} value={s.value}>{s.label}</option>
                            ))}
                        </select>
                    </div>

                    {/* Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 stagger-in">
                        {loading ? (
                            <>
                                <SkeletonCard />
                                <SkeletonCard />
                                <SkeletonCard />
                            </>
                        ) : filtered.length === 0 ? (
                            <div className="col-span-full text-center py-20 text-[var(--color-rune-dim)]">
                                No agents match your search. Try adjusting filters.
                            </div>
                        ) : (
                            filtered.map((a) => <AgentCard key={a.id} agent={a} />)
                        )}
                    </div>
                </>
            )}

            {/* My Agents Tab */}
            {tab === "mine" && (
                <div className="space-y-3">
                    {installed.length === 0 ? (
                        <div className="text-center py-20 text-[var(--color-rune-dim)]">
                            <p className="text-lg mb-2">No agents installed yet</p>
                            <p className="text-sm">Browse the marketplace to find agents that match your needs.</p>
                        </div>
                    ) : (
                        installed.map((a) => (
                            <div key={a.id} className="glass-card p-5 flex items-center gap-4">
                                <span className="text-3xl">{a.avatar}</span>
                                <div className="flex-1 min-w-0">
                                    <h3 className="text-white font-semibold">{a.name}</h3>
                                    <p className="text-xs text-[var(--color-rune-dim)]">
                                        Knows {a.procedures.toLocaleString()} things · {a.crucible_survival}% reliable · {Math.round(a.days_evolved / 30)} months trained
                                    </p>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => handleExport(a.name)}
                                        className="text-xs px-3 py-1.5 rounded border border-[var(--color-glass-border)] text-[var(--color-rune)] hover:text-white transition-colors"
                                    >
                                        📤 Export
                                    </button>
                                    <button
                                        onClick={() => handleRemove(a.name)}
                                        className="text-xs px-3 py-1.5 rounded border border-[var(--color-danger)] text-[var(--color-danger)] hover:bg-[rgba(255,68,102,0.12)] transition-colors"
                                    >
                                        Remove
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}

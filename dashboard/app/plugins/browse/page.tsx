"use client";

import { useState, useEffect } from "react";
import { MarketplacePlugin, browsePlugins, installPlugin, uninstallPlugin } from "@/lib/api";
import { useToast } from "@/components/Toast";

export default function PluginMarketplace() {
    const [plugins, setPlugins] = useState<MarketplacePlugin[]>([]);
    const [search, setSearch] = useState("");
    const [category, setCategory] = useState("all");
    const [loading, setLoading] = useState<string | null>(null);
    const { toast } = useToast();

    useEffect(() => {
        browsePlugins().then(setPlugins);
    }, []);

    const categories = ["all", ...Array.from(new Set(plugins.map((p) => p.category)))];

    const filtered = plugins.filter((p) => {
        const matchesSearch = p.name.includes(search.toLowerCase()) || p.description.toLowerCase().includes(search.toLowerCase());
        const matchesCategory = category === "all" || p.category === category;
        return matchesSearch && matchesCategory;
    });

    const handleInstall = async (name: string) => {
        setLoading(name);
        try {
            await installPlugin(name);
            setPlugins((prev) =>
                prev.map((p) => (p.name === name ? { ...p, installed: true } : p))
            );
            toast("Installed " + name, "success");
        } catch {
            toast("Failed to install " + name, "error");
        }
        setLoading(null);
    };

    const handleUninstall = async (name: string) => {
        setLoading(name);
        try {
            await uninstallPlugin(name);
            setPlugins((prev) =>
                prev.map((p) => (p.name === name ? { ...p, installed: false } : p))
            );
            toast("Uninstalled " + name, "warning");
        } catch {
            toast("Failed to uninstall " + name, "error");
        }
        setLoading(null);
    };

    const categoryIcons: Record<string, string> = {
        all: "📦",
        productivity: "📋",
        integration: "🔗",
        analytics: "📊",
        intelligence: "🧠",
        ops: "⚙",
        security: "🛡",
        interface: "🖥",
    };

    return (
        <div className="page-enter max-w-5xl">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-3xl font-bold mb-1">
                    <span className="text-[var(--color-neon)]">🏪</span> Plugin Marketplace
                </h1>
                <p className="text-sm text-[var(--color-rune-dim)]">
                    Browse, install, and manage community plugins · {plugins.length} available
                </p>
            </div>

            {/* Search + Filter */}
            <div className="flex gap-3 mb-6">
                <input
                    type="text"
                    placeholder="Search plugins..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="flex-1 px-4 py-2.5 rounded-xl text-sm bg-[var(--color-void)] border border-[var(--color-glass-border)] text-white placeholder-[var(--color-rune-dim)] outline-none focus:border-[var(--color-neon)] transition-colors"
                />
                <div className="flex gap-1.5">
                    {categories.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setCategory(cat)}
                            className={"px-3 py-2 rounded-lg text-xs font-medium transition-all " + (
                                category === cat
                                    ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)] border border-[var(--color-neon)]"
                                    : "bg-[var(--color-glass)] text-[var(--color-rune-dim)] border border-[var(--color-glass-border)] hover:text-white"
                            )}
                        >
                            {categoryIcons[cat] || "📦"} {cat}
                        </button>
                    ))}
                </div>
            </div>

            {/* Plugin Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filtered.map((plugin) => (
                    <div key={plugin.name} className="glass-card p-5">
                        <div className="flex items-start justify-between mb-3">
                            <div>
                                <h3 className="text-white font-semibold text-sm">{plugin.name}</h3>
                                <span className="text-xs text-[var(--color-rune-dim)]">
                                    v{plugin.version} · by {plugin.author}
                                </span>
                            </div>
                            <span className="text-xs text-[var(--color-rune-dim)] font-mono">
                                ↓ {plugin.downloads}
                            </span>
                        </div>

                        <p className="text-xs text-[var(--color-rune-dim)] mb-4 leading-relaxed">
                            {plugin.description}
                        </p>

                        <div className="flex items-center justify-between">
                            <span
                                className="text-xs px-2 py-1 rounded-full"
                                style={{
                                    background: "var(--color-glass)",
                                    border: "1px solid var(--color-glass-border)",
                                    color: "var(--color-rune-dim)",
                                }}
                            >
                                {categoryIcons[plugin.category] || "📦"} {plugin.category}
                            </span>

                            {plugin.installed ? (
                                <button
                                    onClick={() => handleUninstall(plugin.name)}
                                    disabled={loading === plugin.name}
                                    className="text-xs px-3 py-1.5 rounded-lg border border-[var(--color-danger)] text-[var(--color-danger)] hover:bg-[rgba(255,68,102,0.1)] transition-colors"
                                    style={{ opacity: loading === plugin.name ? 0.5 : 1 }}
                                >
                                    {loading === plugin.name ? "..." : "Uninstall"}
                                </button>
                            ) : (
                                <button
                                    onClick={() => handleInstall(plugin.name)}
                                    disabled={loading === plugin.name}
                                    className="btn-neon text-xs px-3 py-1.5"
                                    style={{ opacity: loading === plugin.name ? 0.5 : 1 }}
                                >
                                    {loading === plugin.name ? "Installing..." : "Install"}
                                </button>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {filtered.length === 0 && (
                <div className="text-center py-12 text-[var(--color-rune-dim)]">
                    No plugins match your search.
                </div>
            )}
        </div>
    );
}

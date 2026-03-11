"use client";

import { useEffect, useState } from "react";
import { getPlugins } from "@/lib/api";
import type { PluginInfo } from "@/lib/api";

export default function PluginsPage() {
    const [plugins, setPlugins] = useState<PluginInfo[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getPlugins().then((data) => {
            setPlugins(data);
            setLoading(false);
        });
    }, []);

    return (
        <div className="page-enter max-w-5xl">
            {/* ─── Header ─── */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2">
                    <span className="text-[var(--color-neon)]">⬢</span> Plugins
                </h1>
                <p className="text-[var(--color-rune-dim)]">
                    {loading ? "Loading plugins..." : `${plugins.length} plugins installed`}
                </p>
            </div>

            {/* ─── Plugin List ─── */}
            <div className="space-y-4">
                {plugins.map((plugin) => (
                    <div key={plugin.name} className="glass-card p-6">
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <h3 className="text-white text-lg font-semibold">{plugin.name}</h3>
                                    <span className="text-xs font-mono text-[var(--color-rune-dim)] bg-[var(--color-void)] px-2 py-0.5 rounded">
                                        v{plugin.version}
                                    </span>
                                    <span
                                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${plugin.enabled
                                                ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)]"
                                                : "bg-[rgba(255,68,102,0.1)] text-[var(--color-danger)]"
                                            }`}
                                    >
                                        {plugin.enabled ? "Enabled" : "Disabled"}
                                    </span>
                                </div>
                                <p className="text-sm text-[var(--color-rune-dim)] mb-3">{plugin.description}</p>
                                <div className="flex gap-2">
                                    {plugin.routes.map((route) => (
                                        <span
                                            key={route.path}
                                            className="text-xs font-mono text-[var(--color-info)] bg-[rgba(68,170,255,0.1)] px-2 py-1 rounded"
                                        >
                                            {route.method} {route.path}
                                        </span>
                                    ))}
                                </div>
                            </div>
                            <span className="text-xs text-[var(--color-rune-dim)]">by {plugin.author}</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* ─── Marketplace Coming Soon ─── */}
            <div className="glass-card p-8 mt-8 text-center">
                <span className="text-4xl mb-4 block">🏪</span>
                <h3 className="text-white text-xl font-semibold mb-2">Plugin Marketplace</h3>
                <p className="text-sm text-[var(--color-rune-dim)] max-w-md mx-auto">
                    Browse, install, and manage third-party plugins from the community. Coming in Sprint 2.
                </p>
            </div>
        </div>
    );
}

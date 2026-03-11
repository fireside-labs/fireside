"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
    getMarketplaceAgent,
    installAgent,
    MarketplaceAgent,
} from "@/lib/api";
import { useToast } from "@/components/Toast";

function StarRating({ rating, size = "sm" }: { rating: number; size?: "sm" | "lg" }) {
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.3;
    return (
        <span className={`text-amber-400 ${size === "lg" ? "text-lg" : "text-sm"}`}>
            {"★".repeat(full)}
            {half && "½"}
            {"☆".repeat(5 - full - (half ? 1 : 0))}
        </span>
    );
}

export default function AgentDetailPage() {
    const { id } = useParams<{ id: string }>();
    const [agent, setAgent] = useState<MarketplaceAgent | null>(null);
    const [loading, setLoading] = useState(true);
    const [installing, setInstalling] = useState(false);
    const [showTryChat, setShowTryChat] = useState(false);
    const { toast } = useToast();

    useEffect(() => {
        if (id) {
            getMarketplaceAgent(id).then((data) => {
                setAgent(data);
                setLoading(false);
            });
        }
    }, [id]);

    const handleInstall = async () => {
        if (!id) return;
        setInstalling(true);
        await installAgent(id);
        toast(`🎉 ${agent?.name} installed. It has ${agent?.procedures} procedures and ${agent?.days_evolved} days of experience.`, "success");
        setInstalling(false);
    };

    if (loading) {
        return (
            <div className="page-enter max-w-4xl">
                <div className="glass-card p-8 animate-pulse">
                    <div className="h-8 w-64 bg-[var(--color-void-lighter)] rounded mb-4" />
                    <div className="h-4 w-96 bg-[var(--color-void-lighter)] rounded" />
                </div>
            </div>
        );
    }

    if (!agent) {
        return (
            <div className="page-enter max-w-4xl text-center py-20">
                <p className="text-[var(--color-rune-dim)]">Agent not found</p>
            </div>
        );
    }

    return (
        <div className="page-enter max-w-4xl">
            {/* Back link */}
            <Link href="/marketplace" className="text-sm text-[var(--color-rune-dim)] hover:text-[var(--color-neon)] transition-colors mb-4 inline-block">
                ← Back to Marketplace
            </Link>

            {/* Header */}
            <div className="glass-card p-6 mb-6">
                <div className="flex items-start gap-4">
                    <div className="w-16 h-16 rounded-xl bg-[var(--color-glass)] flex items-center justify-center text-4xl">
                        {agent.avatar}
                    </div>
                    <div className="flex-1">
                        <h1 className="text-2xl font-bold text-white">{agent.name}</h1>
                        <p className="text-sm text-[var(--color-rune-dim)]">
                            by {agent.author} · <StarRating rating={agent.rating} /> ({agent.review_count} reviews) · {agent.installs} installs
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-2xl font-bold text-white mb-2">
                            {agent.price === 0 ? (
                                <span className="text-[var(--color-neon)]">Free</span>
                            ) : (
                                `$${agent.price.toFixed(2)}`
                            )}
                        </p>
                        <button
                            onClick={handleInstall}
                            disabled={installing}
                            className="btn-neon px-6 py-2 text-sm"
                            style={{ opacity: installing ? 0.5 : 1 }}
                        >
                            {installing ? "Installing..." : "🔒 Install to My Mesh"}
                        </button>
                    </div>
                </div>
            </div>

            {/* Content grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main content */}
                <div className="lg:col-span-2 space-y-6">
                    {/* About */}
                    <div className="glass-card p-5">
                        <h2 className="text-white font-semibold mb-3">About</h2>
                        <div className="text-sm text-[var(--color-rune)] leading-relaxed whitespace-pre-line">
                            {agent.long_description}
                        </div>
                    </div>

                    {/* Try Before Buy */}
                    {agent.sample_conversation && agent.sample_conversation.length > 0 && (
                        <div className="glass-card p-5">
                            <h2 className="text-white font-semibold mb-3">Try Before Buy</h2>
                            <p className="text-xs text-[var(--color-rune-dim)] mb-3">
                                3 free messages to see the personality in action.
                            </p>
                            {!showTryChat ? (
                                <button
                                    onClick={() => setShowTryChat(true)}
                                    className="btn-neon px-4 py-2 text-sm w-full"
                                >
                                    💬 Talk to {agent.name} →
                                </button>
                            ) : (
                                <div className="space-y-3">
                                    {agent.sample_conversation.map((msg, i) => (
                                        <div
                                            key={i}
                                            className="rounded-lg p-3"
                                            style={{
                                                background: msg.role === "user" ? "var(--color-glass)" : "var(--color-neon-glow)",
                                                marginLeft: msg.role === "user" ? "2rem" : 0,
                                                marginRight: msg.role === "assistant" ? "2rem" : 0,
                                            }}
                                        >
                                            <p className="text-[10px] text-[var(--color-rune-dim)] mb-1">
                                                {msg.role === "user" ? "You" : agent.name}
                                            </p>
                                            <p className="text-sm text-[var(--color-rune)] whitespace-pre-line">{msg.content}</p>
                                        </div>
                                    ))}
                                    <p className="text-xs text-center text-[var(--color-rune-dim)] pt-2">
                                        Like what you see? Install for full access.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Reviews */}
                    <div className="glass-card p-5">
                        <h2 className="text-white font-semibold mb-3">Reviews</h2>
                        <div className="space-y-3">
                            {agent.reviews.map((r, i) => (
                                <div key={i} className="pb-3 border-b border-[var(--color-glass-border)] last:border-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <StarRating rating={r.rating} />
                                        <span className="text-xs text-[var(--color-rune-dim)]">{r.author}</span>
                                        <span className="text-xs text-[var(--color-rune-dim)]">· {r.date}</span>
                                        {r.verified && (
                                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-neon-glow)] text-[var(--color-neon)]">
                                                ☑ Verified
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-sm text-[var(--color-rune)]">{r.text}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Sidebar */}
                <div className="space-y-4">
                    {/* Stats */}
                    <div className="glass-card p-5">
                        <h3 className="text-sm text-[var(--color-rune-dim)] uppercase tracking-wider mb-3">Stats</h3>
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-[var(--color-rune)]">Procedures</span>
                                <span className="text-sm text-white font-bold">{agent.procedures.toLocaleString()}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-[var(--color-rune)]">Crucible Survival</span>
                                <span className="text-sm font-bold" style={{
                                    color: agent.crucible_survival >= 95 ? "var(--color-neon)" : agent.crucible_survival >= 85 ? "var(--color-info)" : "var(--color-warning)"
                                }}>
                                    {agent.crucible_survival}%
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-[var(--color-rune)]">Days Evolved</span>
                                <span className="text-sm text-white font-bold">{agent.days_evolved}</span>
                            </div>
                        </div>
                    </div>

                    {/* Personality */}
                    <div className="glass-card p-5">
                        <h3 className="text-sm text-[var(--color-rune-dim)] uppercase tracking-wider mb-3">Personality</h3>
                        <div className="flex flex-wrap gap-2">
                            {agent.personality_traits.map((t) => (
                                <span key={t} className="text-xs px-2 py-1 rounded-full bg-[var(--color-glass)] text-[var(--color-rune)]">
                                    {t}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Requirements */}
                    <div className="glass-card p-5">
                        <h3 className="text-sm text-[var(--color-rune-dim)] uppercase tracking-wider mb-3">Requirements</h3>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-[var(--color-rune)]">GPU Memory</span>
                                <span className="text-xs text-white">{agent.model_requirements.gpu_vram}GB+ VRAM</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-[var(--color-rune)]">RAM</span>
                                <span className="text-xs text-white">{agent.model_requirements.ram}GB+</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-[var(--color-rune)]">Model Size</span>
                                <span className="text-xs text-white">{agent.model_requirements.min_params}+ params</span>
                            </div>
                            <div className="mt-2 p-2 rounded bg-[var(--color-neon-glow)] text-center">
                                <span className="text-xs text-[var(--color-neon)]">✅ Compatible with your setup</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

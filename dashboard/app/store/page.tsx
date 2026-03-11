"use client";

import { useState } from "react";
import StoreTabs from "@/components/StoreTabs";
import ItemCard from "@/components/ItemCard";
import PurchaseHistory from "@/components/PurchaseHistory";

const STORE_ITEMS: Record<string, { id: string; name: string; creator: string; description: string; emoji: string; price: number; rating: number; reviews: number; featured?: boolean }[]> = {
    agents: [
        { id: "a1", name: "Code Warrior", creator: "OdinApps", description: "Full-stack developer agent. Writes Python, JS, and deploys to prod.", emoji: "⚔️", price: 4.99, rating: 4.8, reviews: 24, featured: true },
        { id: "a2", name: "Researcher", creator: "AcademiaAI", description: "Academic research agent. Reads papers, summarizes findings, builds bibliographies.", emoji: "📚", price: 3.99, rating: 4.5, reviews: 12 },
        { id: "a3", name: "Content Writer", creator: "WordSmith", description: "Writes blogs, social posts, and newsletters in your voice.", emoji: "✍️", price: 0, rating: 4.2, reviews: 31 },
    ],
    themes: [
        { id: "t1", name: "Valhalla", creator: "Fireside Team", description: "Norse great hall with forge, mead hall, and rune bookshelves.", emoji: "🏰", price: 0, rating: 5, reviews: 89, featured: true },
        { id: "t2", name: "Office", creator: "Fireside Team", description: "Modern workspace with desks, whiteboard, and coffee machine.", emoji: "🏢", price: 0, rating: 4.6, reviews: 45 },
        { id: "t3", name: "Space Station", creator: "CosmicDesigns", description: "Sci-fi space station with hologram displays and zero-G lounge.", emoji: "🚀", price: 2.99, rating: 4.9, reviews: 18 },
        { id: "t4", name: "Cozy Cabin", creator: "HomeVibes", description: "Warm living room with bookshelf, cat, and crackling fireplace.", emoji: "🏡", price: 2.99, rating: 4.7, reviews: 22 },
        { id: "t5", name: "Pixel Dungeon", creator: "RetroGuild", description: "8-bit RPG dungeon with treasure chests and campfire.", emoji: "⚔️", price: 3.99, rating: 4.8, reviews: 14 },
    ],
    avatars: [
        { id: "av1", name: "Pixel Warriors Pack", creator: "PixelForge", description: "12 warrior-themed pixel avatars with animations.", emoji: "🗡️", price: 1.99, rating: 4.6, reviews: 8 },
        { id: "av2", name: "Minimal Pro Pack", creator: "CleanDesign", description: "6 minimalist SVG avatars for a sleek look.", emoji: "✨", price: 0.99, rating: 4.3, reviews: 5 },
    ],
    voices: [
        { id: "v1", name: "Calm & Clear", creator: "VoiceLab", description: "Soothing, calm voice. Perfect for reading and long responses.", emoji: "🧘", price: 2.99, rating: 4.9, reviews: 33, featured: true },
        { id: "v2", name: "Energetic", creator: "VoiceLab", description: "Upbeat and energetic. Great for task updates and alerts.", emoji: "⚡", price: 2.99, rating: 4.4, reviews: 11 },
        { id: "v3", name: "Storyteller", creator: "NarrativeAI", description: "Rich, dramatic voice for when your AI tells stories.", emoji: "📖", price: 3.99, rating: 4.7, reviews: 7 },
    ],
    personalities: [
        { id: "p1", name: "Startup Founder", creator: "HustleMode", description: "Bold, action-oriented. Moves fast, breaks things, ships daily.", emoji: "🚀", price: 1.99, rating: 4.5, reviews: 19 },
        { id: "p2", name: "Gentle Teacher", creator: "EduAI", description: "Patient, encouraging. Explains step by step, never judges.", emoji: "🍎", price: 0, rating: 4.8, reviews: 42 },
        { id: "p3", name: "Stoic Philosopher", creator: "DeepThink", description: "Thoughtful, measured. References Marcus Aurelius unironically.", emoji: "🏛️", price: 1.99, rating: 4.6, reviews: 15 },
    ],
};

const TAB_COUNTS: Record<string, number> = {
    agents: 3, themes: 5, avatars: 2, voices: 3, personalities: 3,
};

export default function StorePage() {
    const [tab, setTab] = useState("agents");
    const [showPurchases, setShowPurchases] = useState(false);

    const items = STORE_ITEMS[tab] || [];

    return (
        <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <span>🏪</span> Store
                    </h1>
                    <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                        Agents, themes, voices, and more. Created by the community.
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
                    <StoreTabs selected={tab} onSelect={setTab} counts={TAB_COUNTS} />

                    {/* Items Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
                        {items.map((item) => (
                            <ItemCard key={item.id} {...item} />
                        ))}
                    </div>

                    {/* No items */}
                    {items.length === 0 && (
                        <div className="text-center py-12">
                            <span className="text-4xl block mb-3">🔍</span>
                            <p className="text-sm text-[var(--color-rune-dim)]">No items in this category yet.</p>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

"use client";

import { useState } from "react";

interface ItemCardProps {
    id: string;
    name: string;
    creator: string;
    description: string;
    emoji: string;
    price: number; // 0 = free
    rating: number; // 0-5
    reviews: number;
    purchased?: boolean;
    featured?: boolean;
    onBuy?: () => void;
}

export default function ItemCard({
    name,
    creator,
    description,
    emoji,
    price,
    rating,
    reviews,
    purchased,
    featured,
    onBuy,
}: ItemCardProps) {
    const [buying, setBuying] = useState(false);
    const [owned, setOwned] = useState(purchased);

    const handleBuy = () => {
        if (price === 0) {
            setOwned(true);
            onBuy?.();
            return;
        }
        setBuying(true);
        // Simulate Stripe checkout
        setTimeout(() => {
            setBuying(false);
            setOwned(true);
            onBuy?.();
        }, 1500);
    };

    return (
        <div
            className="glass-card p-4 transition-all hover:scale-[1.02]"
            style={{
                borderColor: featured ? "var(--color-neon)" : undefined,
                borderWidth: featured ? 1 : undefined,
            }}
        >
            {featured && (
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-[var(--color-neon-glow)] text-[var(--color-neon)] font-bold mb-2 inline-block">
                    ⭐ FEATURED
                </span>
            )}

            <div className="flex items-start gap-3">
                <span className="text-3xl">{emoji}</span>
                <div className="flex-1 min-w-0">
                    <h4 className="text-sm text-white font-semibold truncate">{name}</h4>
                    <p className="text-[10px] text-[var(--color-rune-dim)]">by {creator}</p>
                    <p className="text-xs text-[var(--color-rune)] mt-1 line-clamp-2">{description}</p>

                    {/* Rating */}
                    <div className="flex items-center gap-1 mt-1.5">
                        <span className="text-[10px] text-[var(--color-neon)]">
                            {"★".repeat(Math.round(rating))}{"☆".repeat(5 - Math.round(rating))}
                        </span>
                        <span className="text-[9px] text-[var(--color-rune-dim)]">({reviews})</span>
                    </div>
                </div>
            </div>

            {/* Price + Buy */}
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-[var(--color-glass-border)]">
                <span className="text-sm font-bold text-white">
                    {price === 0 ? "Free" : `$${price.toFixed(2)}`}
                </span>
                {owned ? (
                    <span className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-neon-glow)] text-[var(--color-neon)] font-medium">
                        ✅ Owned
                    </span>
                ) : (
                    <button
                        onClick={handleBuy}
                        disabled={buying}
                        className="btn-neon px-4 py-1.5 text-xs disabled:opacity-50"
                    >
                        {buying ? "Processing..." : price === 0 ? "Install" : "Buy"}
                    </button>
                )}
            </div>
        </div>
    );
}

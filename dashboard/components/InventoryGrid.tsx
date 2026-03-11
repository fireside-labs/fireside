"use client";

import { useState } from "react";

interface InventoryItem {
    item: string;
    count: number;
    emoji: string;
    equipped?: boolean;
    consumable?: boolean;
    description?: string;
    rare?: boolean;
}

const MOCK_INVENTORY: InventoryItem[] = [
    { item: "golden_treat", count: 3, emoji: "🍬✨", consumable: true, description: "+30 happiness" },
    { item: "tiny_hat", count: 1, emoji: "🎩", equipped: true, description: "Looks adorable" },
    { item: "story_fragment", count: 7, emoji: "📜", description: "7/10 collected" },
    { item: "moonpetal", count: 2, emoji: "🌿", consumable: true, description: "+25 happiness when used" },
    { item: "friendship_badge", count: 1, emoji: "🤝", description: "Helped a lost pet" },
    { item: "cave_crystal", count: 1, emoji: "💎", rare: true, description: "Found in a storm shelter" },
    { item: "ancient_compass", count: 1, emoji: "🧭", description: "Won from a riddle guardian" },
];

const MAX_SLOTS = 20;

interface InventoryGridProps {
    petName: string;
    onUseItem?: (item: InventoryItem) => void;
    onEquipItem?: (item: InventoryItem) => void;
}

export default function InventoryGrid({ petName, onUseItem, onEquipItem }: InventoryGridProps) {
    const [items] = useState<InventoryItem[]>(MOCK_INVENTORY);
    const [selected, setSelected] = useState<InventoryItem | null>(null);

    const emptySlots = MAX_SLOTS - items.reduce((acc, i) => acc + 1, 0);

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-white font-semibold text-sm">🎒 {petName}&apos;s Inventory</h3>
                <span className="text-[9px] text-[var(--color-rune-dim)]">{items.length}/{MAX_SLOTS} slots</span>
            </div>

            {/* Grid */}
            <div className="grid grid-cols-5 gap-1.5 mb-3">
                {items.map((item) => (
                    <button
                        key={item.item}
                        onClick={() => setSelected(selected?.item === item.item ? null : item)}
                        className="relative p-2 rounded-lg text-center transition-all"
                        style={{
                            background: selected?.item === item.item ? "var(--color-neon-glow)" : "var(--color-glass)",
                            borderLeft: item.rare ? "2px solid gold" : selected?.item === item.item ? "2px solid var(--color-neon)" : "2px solid transparent",
                        }}
                    >
                        <span className="text-lg block">{item.emoji}</span>
                        {item.count > 1 && (
                            <span className="absolute bottom-0.5 right-1 text-[8px] text-white bg-[rgba(0,0,0,0.5)] rounded px-0.5">
                                ×{item.count}
                            </span>
                        )}
                        {item.equipped && (
                            <span className="absolute top-0 right-0.5 text-[8px]">✅</span>
                        )}
                    </button>
                ))}
                {/* Empty slots */}
                {Array.from({ length: Math.min(emptySlots, 6) }).map((_, i) => (
                    <div key={`empty-${i}`} className="p-2 rounded-lg bg-[var(--color-glass)] opacity-30 text-center">
                        <span className="text-lg block text-[var(--color-rune-dim)]">·</span>
                    </div>
                ))}
            </div>

            {/* Selected item detail */}
            {selected && (
                <div className="p-3 rounded-lg bg-[var(--color-glass)] border-l-2 border-[var(--color-neon)]">
                    <div className="flex items-center justify-between mb-1">
                        <p className="text-xs text-white font-medium">
                            {selected.emoji} {selected.item.replace(/_/g, " ")}
                            {selected.rare && <span className="text-[9px] text-yellow-400 ml-1">★ RARE</span>}
                        </p>
                        <span className="text-[9px] text-[var(--color-rune-dim)]">×{selected.count}</span>
                    </div>
                    {selected.description && (
                        <p className="text-[10px] text-[var(--color-rune-dim)] mb-2">{selected.description}</p>
                    )}
                    <div className="flex gap-2">
                        {selected.consumable && (
                            <button
                                onClick={() => { onUseItem?.(selected); setSelected(null); }}
                                className="btn-neon px-3 py-1 text-[10px] flex-1"
                            >
                                Use
                            </button>
                        )}
                        {selected.equipped !== undefined && !selected.consumable && (
                            <button
                                onClick={() => { onEquipItem?.(selected); setSelected(null); }}
                                className="btn-neon px-3 py-1 text-[10px] flex-1"
                            >
                                {selected.equipped ? "Unequip" : "Equip"}
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

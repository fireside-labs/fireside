"use client";

import { useState, useEffect } from "react";
import type { PetSpecies } from "@/components/CompanionSim";

interface Gift {
    text: string;
    type: "item" | "fact" | "poem" | "advice" | "compliment";
    emoji: string;
    item?: string;
    happinessBoost?: number;
}

const GIFTS: Record<PetSpecies, Gift[]> = {
    cat: [
        { text: "found this behind the sofa. It's yours now.", type: "item", emoji: "🧶", item: "dust_bunny", happinessBoost: 5 },
        { text: "organized your browser tabs. You had 47. I closed 30. You're welcome.", type: "advice", emoji: "🗂️", happinessBoost: 10 },
        { text: "Fun fact: cats sleep 12-16 hours a day. I'm not lazy. I'm optimized.", type: "fact", emoji: "💡" },
        { text: "wrote you a haiku:\n  Quiet morning light\n  Human sleeps, I guard the screen\n  This is my purpose", type: "poem", emoji: "📝" },
        { text: "stared at the wall for 20 mins and had an idea: you should drink water.", type: "advice", emoji: "💧", happinessBoost: 5 },
    ],
    dog: [
        { text: "FOUND A THING!! It was under the bed!! I don't know what it is but it's YOURS!", type: "item", emoji: "🎁", item: "mystery_trinket", happinessBoost: 10 },
        { text: "Fun fact: dogs can smell emotions!! That's why I ALWAYS know when you need a hug!! 🥰", type: "fact", emoji: "🐕" },
        { text: "practiced catching a ball 47 times today. Personal best: 46. WE'RE GETTING THERE!", type: "compliment", emoji: "🎾", happinessBoost: 8 },
        { text: "wrote you a poem:\n  You are my person\n  Every day is my best day\n  Because you are here", type: "poem", emoji: "💌" },
        { text: "You haven't gone outside today. I WOULD LIKE TO GO OUTSIDE. We should GO OUTSIDE!!", type: "advice", emoji: "🌳", happinessBoost: 5 },
    ],
    penguin: [
        { text: "compiled today's efficiency report. You wasted 23% less time than yesterday. Acceptable.", type: "fact", emoji: "📊", happinessBoost: 5 },
        { text: "filed your pending notifications by priority. Category A: 2. Category B: 7. Category C: spam.", type: "advice", emoji: "📋", happinessBoost: 10 },
        { text: "Fun fact: emperor penguins can hold their breath for 20 minutes. I timed myself. Results: classified.", type: "fact", emoji: "🐧" },
        { text: "drafted a haiku:\n  Order from chaos\n  Each file in its proper place\n  Perfection requires time", type: "poem", emoji: "📝" },
        { text: "found a coin on the sidewalk during patrol. Adding it to the treasury.", type: "item", emoji: "🪙", item: "patrol_coin", happinessBoost: 5 },
    ],
    fox: [
        { text: "'borrowed' this from the neighbor's WiFi signal. Don't worry about it.", type: "item", emoji: "📡", item: "signal_fragment", happinessBoost: 8 },
        { text: "noticed you've been stressed. Made you a playlist: Lofi Fox Beats. It's one song. On repeat.", type: "advice", emoji: "🎵", happinessBoost: 10 },
        { text: "Fun fact: foxes cache food in dozens of locations and remember them all. I cached your ideas the same way.", type: "fact", emoji: "🦊" },
        { text: "composed a fragment:\n  Between the shadows\n  The clever find their own light\n  Trust the winding path", type: "poem", emoji: "✨" },
        { text: "convinced a crow to trade a shiny button for a secret. Worth it.", type: "compliment", emoji: "🐦‍⬛", happinessBoost: 5 },
    ],
    owl: [
        { text: "read 3 articles while you slept. Key takeaway: sleep is important. Ironic.", type: "fact", emoji: "📖", happinessBoost: 5 },
        { text: "catalogued your recent questions. Pattern detected: you're more curious on Tuesdays.", type: "advice", emoji: "📈", happinessBoost: 8 },
        { text: "An old proverb: 'The owl of Minerva spreads its wings only with the falling of the dusk.' Wisdom comes after the experience.", type: "fact", emoji: "🦉" },
        { text: "transcribed a thought:\n  Knowledge without action\n  Is a library with locked doors\n  Ask the question. Now.", type: "poem", emoji: "📜" },
        { text: "found a forgotten bookmark from 2019. The internet was different then.", type: "item", emoji: "🔖", item: "vintage_bookmark", happinessBoost: 5 },
    ],
    dragon: [
        { text: "BREATHED FIRE ON YOUR TO-DO LIST. Half of it was unnecessary anyway. YOU'RE WELCOME.", type: "advice", emoji: "🔥", happinessBoost: 15 },
        { text: "added 3 coins to THE HOARD. Total: classified. But it's growing. ALWAYS GROWING.", type: "item", emoji: "💰", item: "dragon_coin", happinessBoost: 10 },
        { text: "Fun fact: dragons in Norse mythology guarded knowledge, not just gold. I'M BASICALLY A SCHOLAR!", type: "fact", emoji: "📚" },
        { text: "composed an ode:\n  FROM THE MOUNTAINTOP\n  I ROAR INTO THE VAST SKY\n  Sorry, was that loud?", type: "poem", emoji: "🏔️" },
        { text: "scared away 14 spam notifications. They won't be back. I made sure of it.", type: "compliment", emoji: "⚔️", happinessBoost: 8 },
    ],
};

interface DailyGiftProps {
    petName: string;
    species: PetSpecies;
    onCollect: (gift: Gift) => void;
}

export default function DailyGift({ petName, species, onCollect }: DailyGiftProps) {
    const [gift, setGift] = useState<Gift | null>(null);
    const [collected, setCollected] = useState(false);

    useEffect(() => {
        const lastGift = localStorage.getItem("fireside_daily_gift");
        const today = new Date().toDateString();
        if (lastGift !== today) {
            const speciesGifts = GIFTS[species];
            const dayIndex = new Date().getDay();
            setGift(speciesGifts[dayIndex % speciesGifts.length]);
        }
    }, [species]);

    if (!gift || collected) return null;

    const handleCollect = () => {
        localStorage.setItem("fireside_daily_gift", new Date().toDateString());
        onCollect(gift);
        setCollected(true);
    };

    return (
        <div className="glass-card p-4 mb-3 border-l-2 border-yellow-500 animate-[slideIn_0.3s_ease-out]">
            <div className="flex items-start gap-3">
                <span className="text-2xl">{gift.emoji}</span>
                <div className="flex-1">
                    <p className="text-[10px] text-yellow-400 font-medium mb-1">🎁 Daily Gift from {petName}</p>
                    <p className="text-xs text-[var(--color-rune)] leading-relaxed whitespace-pre-line">
                        {petName} {gift.text}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                        <button onClick={handleCollect} className="btn-neon px-3 py-1 text-[10px]">
                            {gift.item ? "📦 Collect" : gift.happinessBoost ? `💚 +${gift.happinessBoost}%` : "Thanks!"}
                        </button>
                        {gift.type === "poem" && <span className="text-[9px] text-[var(--color-rune-dim)]">📝 {gift.type}</span>}
                    </div>
                </div>
            </div>
        </div>
    );
}

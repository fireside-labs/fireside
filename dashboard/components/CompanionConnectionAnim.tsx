"use client";

import { useState, useEffect } from "react";
import type { PetSpecies } from "@/components/CompanionSim";

type ConnectionState = "connecting" | "failed" | "connected" | "offline";

interface CompanionConnectionAnimProps {
    species: PetSpecies;
    petName: string;
    connectionState: ConnectionState;
}

const ANIM_TEXT: Record<PetSpecies, Record<Exclude<ConnectionState, "connected">, { text: string; emoji: string }>> = {
    cat: {
        connecting: { text: "Trying to reach your PC... hold on.", emoji: "🧶" },
        failed: { text: "Your PC isn't answering. Typical.", emoji: "😾" },
        offline: { text: "Airplane mode? Fine. I'll handle it myself.", emoji: "✈️" },
    },
    dog: {
        connecting: { text: "CALLING HOME!! CALLING HOME!!", emoji: "📞" },
        failed: { text: "I can't reach home... 🥺 I'll keep trying!", emoji: "🐕" },
        offline: { text: "No signal?! That's okay I STILL LOVE YOU!", emoji: "✈️" },
    },
    penguin: {
        connecting: { text: "Establishing uplink to base...", emoji: "📡" },
        failed: { text: "The pigeon mail service is on strike. Standing by.", emoji: "🪧" },
        offline: { text: "Offline operations engaged. Formally.", emoji: "✈️" },
    },
    fox: {
        connecting: { text: "Ringing your home PC...", emoji: "📱" },
        failed: { text: "Line's dead. Guess it's just you and me 😏", emoji: "📵" },
        offline: { text: "Off the grid? I know a few tricks offline...", emoji: "✈️" },
    },
    owl: {
        connecting: { text: "Searching the ether...", emoji: "🔮" },
        failed: { text: "The great brain sleeps. We wait.", emoji: "😔" },
        offline: { text: "The sky is dark. But wisdom needs no signal.", emoji: "✈️" },
    },
    dragon: {
        connecting: { text: "SUMMONING THE MAIN BRAIN!", emoji: "🔥" },
        failed: { text: "THE SIGNAL... has failed. This is unprecedented.", emoji: "💨" },
        offline: { text: "NO SIGNAL?! A dragon needs no tower.", emoji: "✈️" },
    },
};

const RECONNECT_TEXT: Record<PetSpecies, string> = {
    cat: "Oh. Your PC is back. How nice for you.",
    dog: "THEY'RE BACK!! YOUR PC IS BACK!! 🎉🎉🎉",
    penguin: "Connection restored. The mail pigeons have ended their strike.",
    fox: "Look who finally showed up. Syncing now...",
    owl: "The great brain awakens. Your tasks are being processed.",
    dragon: "THE BRAIN LIVES! Sending your queued missions NOW!",
};

export default function CompanionConnectionAnim({ species, petName, connectionState }: CompanionConnectionAnimProps) {
    const [showReconnect, setShowReconnect] = useState(false);
    const [prevState, setPrevState] = useState<ConnectionState>(connectionState);

    useEffect(() => {
        if (prevState !== "connected" && connectionState === "connected") {
            setShowReconnect(true);
            setTimeout(() => setShowReconnect(false), 4000);
        }
        setPrevState(connectionState);
    }, [connectionState, prevState]);

    if (connectionState === "connected" && !showReconnect) return null;

    if (showReconnect) {
        return (
            <div className="p-3 rounded-lg bg-[var(--color-neon-glow)] border border-[rgba(0,255,136,0.15)] animate-[slideIn_0.3s_ease-out] mb-3">
                <p className="text-xs text-[var(--color-neon)] font-medium">
                    🟢 {petName}: {RECONNECT_TEXT[species]}
                </p>
            </div>
        );
    }

    const anim = ANIM_TEXT[species][connectionState as Exclude<ConnectionState, "connected">];
    const isConnecting = connectionState === "connecting";

    return (
        <div
            className="p-3 rounded-lg border mb-3"
            style={{
                background: connectionState === "failed" ? "rgba(255,68,102,0.05)" : "var(--color-glass)",
                borderColor: connectionState === "failed" ? "rgba(255,68,102,0.15)" : "var(--color-glass-border)",
            }}
        >
            <div className="flex items-center gap-2.5">
                <span className={`text-xl ${isConnecting ? "animate-spin" : connectionState === "failed" ? "animate-[wobble_2s_ease-in-out_infinite]" : ""}`}>
                    {anim.emoji}
                </span>
                <div>
                    <p className="text-xs text-white font-medium">{petName}</p>
                    <p className="text-[10px] text-[var(--color-rune-dim)] italic">{anim.text}</p>
                </div>
            </div>
            {connectionState === "failed" && (
                <p className="text-[9px] text-[var(--color-rune-dim)] mt-2">
                    I&apos;ll handle what I can with my own little brain. Complex tasks queued for when we&apos;re back.
                </p>
            )}
        </div>
    );
}

export type { ConnectionState };

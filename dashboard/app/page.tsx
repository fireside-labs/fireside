"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface CompanionState {
    species: string;
    name: string;
    owner: string;
    happiness: number;
    xp: number;
    level: number;
    streak: number;
}

const SPECIES_EMOJI: Record<string, string> = {
    cat: "🐱", dog: "🐶", penguin: "🐧",
    fox: "🦊", owl: "🦉", dragon: "🐉",
};

const SUGGESTED_PROMPTS = [
    "Take me for a walk",
    "Remember: I like my coffee black",
    "Translate 'good morning' to Japanese",
];

export default function ChatHomePage() {
    const [message, setMessage] = useState("");
    const [userName, setUserName] = useState("");
    const [companion, setCompanion] = useState<CompanionState | null>(null);
    const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);

    useEffect(() => {
        const name = localStorage.getItem("fireside_user_name") || "";
        setUserName(name);
        // Load companion state
        try {
            const stored = localStorage.getItem("fireside_companion");
            if (stored) setCompanion(JSON.parse(stored));
        } catch { /* no companion yet */ }
    }, []);

    const handleSend = async () => {
        if (!message.trim()) return;
        const userMessage = message.trim();
        setChatHistory(prev => [...prev, { role: "user", content: userMessage }]);
        setMessage("");

        try {
            const res = await fetch("http://127.0.0.1:8765/api/v1/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMessage, stream: false }),
            });

            if (!res.ok) throw new Error(`API error: ${res.status}`);
            const data = await res.json();
            setChatHistory(prev => [...prev, {
                role: "assistant",
                content: data.response || data.content || "I received your message but couldn't generate a response.",
            }]);
        } catch {
            setChatHistory(prev => [...prev, {
                role: "assistant",
                content: "I'm not connected to a brain yet. Go to Settings → Brain to install one, or check that your inference server is running.",
            }]);
        }
    };

    const handlePrompt = (prompt: string) => {
        setMessage(prompt);
    };

    const petEmoji = companion ? (SPECIES_EMOJI[companion.species] || "🐾") : "🔥";
    const happinessLabel = companion
        ? companion.happiness > 70 ? "Happy" : companion.happiness > 30 ? "Content" : "Needs attention"
        : null;

    return (
        <div className="max-w-2xl mx-auto">
            {/* Greeting */}
            <div className="text-center mb-10 pt-12 animate-enter">
                <h1 className="text-4xl font-black text-white mb-3 tracking-tight">
                    Hi{userName ? ` ${userName}` : " there"} <span className="text-[var(--color-neon)]">🔥</span>
                </h1>
                <p className="text-sm text-[var(--color-rune-dim)] font-medium uppercase tracking-[0.2em]">System Ready • Logic Engaged</p>
            </div>

            {/* Companion Widget */}
            {companion && (
                <Link href="/companion">
                    <div className="glass-card p-5 mb-8 flex items-center gap-5 hover:bg-[var(--color-glass-hover)] group cursor-pointer" style={{ borderLeft: "4px solid var(--color-neon)" }}>
                        <div className="text-4xl group-hover:scale-110 transition-transform duration-300">
                            {petEmoji}
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="text-white font-bold text-base tracking-tight">{companion.name}</span>
                                    <span className="px-1.5 py-0.5 rounded bg-[var(--color-void-lighter)] text-[9px] text-[var(--color-rune-dim)] font-bold uppercase">LVL {companion.level}</span>
                                </div>
                                <span className="text-[10px] text-[var(--color-neon)] font-bold uppercase tracking-wider">Companion Status</span>
                            </div>
                            <div className="flex items-center gap-3 mt-3">
                                <div className="flex-1 h-2 rounded-full bg-[var(--color-void-lighter)] p-0.5 border border-white/5">
                                    <div
                                        className="h-full rounded-full transition-all duration-1000 shadow-[0_0_8px_var(--glow)]"
                                        style={{
                                            width: `${companion.happiness}%`,
                                            backgroundColor: companion.happiness > 70 ? "var(--color-neon)" : companion.happiness > 30 ? "#f59e0b" : "#ef4444",
                                            '--glow': companion.happiness > 70 ? "rgba(245,158,11,0.4)" : "rgba(239,68,68,0.2)",
                                        } as any}
                                    />
                                </div>
                                <span className="text-[11px] text-[var(--color-rune)] font-medium min-w-[60px] text-right">{happinessLabel}</span>
                            </div>
                        </div>
                    </div>
                </Link>
            )}

            {/* Chat messages */}
            {chatHistory.length > 0 && (
                <div className="mb-6 space-y-3 max-h-96 overflow-y-auto">
                    {chatHistory.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${msg.role === "user"
                                ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)] border border-[rgba(0,255,136,0.15)]"
                                : "glass-card text-[var(--color-rune)]"
                                }`}>
                                {msg.content}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Chat input */}
            <div className="glass-card p-2 mb-6" style={{ borderColor: "var(--color-glass-border)" }}>
                <div className="flex items-center gap-2">
                    <input
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                        placeholder="Type a message..."
                        className="flex-1 px-4 py-3 bg-transparent text-white outline-none text-sm placeholder-[var(--color-rune-dim)]"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!message.trim()}
                        className="btn-neon px-5 py-2.5 text-sm font-medium"
                        style={{ opacity: message.trim() ? 1 : 0.4 }}
                    >
                        Send
                    </button>
                </div>
            </div>

            {/* Suggested prompts */}
            {chatHistory.length === 0 && (
                <div className="mb-10">
                    <p className="text-xs text-[var(--color-rune-dim)] mb-3">Try asking:</p>
                    <div className="space-y-2">
                        {SUGGESTED_PROMPTS.map((prompt) => (
                            <button
                                key={prompt}
                                onClick={() => handlePrompt(prompt)}
                                className="block w-full text-left px-4 py-3 rounded-lg text-sm text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)] transition-all border border-[var(--color-glass-border)]"
                            >
                                &ldquo;{prompt}&rdquo;
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Welcome card for fresh installs / status for returning users */}
            {chatHistory.length === 0 && (
                <div className="glass-card p-5">
                    <h3 className="text-sm text-[var(--color-rune-dim)] font-semibold mb-4">
                        {companion ? `${petEmoji} ${companion.name} is here` : "🔥 Welcome to Fireside"}
                    </h3>
                    <div className="space-y-3">
                        <div className="flex items-center gap-3">
                            <span className="text-lg">🧠</span>
                            <span className="text-sm text-[var(--color-rune)]">
                                {companion ? "I remember everything we talk about" : "Your AI runs locally — nothing leaves this machine"}
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="text-lg">🌙</span>
                            <span className="text-sm text-[var(--color-rune)]">
                                {companion ? "Tonight I'll dream about what I learned today" : "I learn while you sleep and get smarter every morning"}
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="text-lg">💬</span>
                            <span className="text-sm text-[var(--color-rune)]">
                                {companion ? "Say hello! I'm ready to chat" : "Start a conversation — I'm listening"}
                            </span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

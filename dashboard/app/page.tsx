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
            <div className="text-center mb-6 pt-8">
                <h1 className="text-3xl font-bold text-white mb-2">
                    Hi{userName ? ` ${userName}` : " there"} 👋
                </h1>
                <p className="text-[var(--color-rune-dim)]">Your AI is ready. What can I help you with?</p>
            </div>

            {/* Companion Widget */}
            {companion && (
                <Link href="/companion">
                    <div className="glass-card p-4 mb-6 flex items-center gap-4 hover:bg-[var(--color-glass-hover)] transition-all cursor-pointer" style={{ borderColor: "var(--color-neon)", borderWidth: 1 }}>
                        <span className="text-3xl">{petEmoji}</span>
                        <div className="flex-1">
                            <div className="flex items-center gap-2">
                                <span className="text-white font-semibold text-sm">{companion.name}</span>
                                <span className="text-[10px] text-[var(--color-rune-dim)]">Lv. {companion.level}</span>
                            </div>
                            <div className="flex items-center gap-2 mt-1.5">
                                <div className="flex-1 h-1.5 rounded-full bg-[var(--color-glass)]">
                                    <div
                                        className="h-full rounded-full transition-all"
                                        style={{
                                            width: `${companion.happiness}%`,
                                            background: companion.happiness > 70 ? "var(--color-neon)" : companion.happiness > 30 ? "#f59e0b" : "#ef4444",
                                        }}
                                    />
                                </div>
                                <span className="text-[10px] text-[var(--color-rune-dim)]">{happinessLabel}</span>
                            </div>
                        </div>
                        <span className="text-[var(--color-rune-dim)] text-xs">→</span>
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

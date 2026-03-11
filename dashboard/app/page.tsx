"use client";

import { useState, useEffect } from "react";

const SUGGESTED_PROMPTS = [
    "Summarize my emails from this week",
    "Help me write a thank-you letter",
    "What files did I work on yesterday?",
];

const ACTIVITY = [
    { icon: "✅", text: "Answered 12 questions" },
    { icon: "📁", text: "Read 3 files" },
    { icon: "🧠", text: "Learned 2 new things" },
];

export default function ChatHomePage() {
    const [message, setMessage] = useState("");
    const [userName, setUserName] = useState("");
    const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);

    useEffect(() => {
        const name = localStorage.getItem("valhalla_user_name") || "";
        setUserName(name);
    }, []);

    const handleSend = () => {
        if (!message.trim()) return;
        setChatHistory([...chatHistory, { role: "user", content: message.trim() }]);
        // Mock AI response
        setTimeout(() => {
            setChatHistory(prev => [...prev, {
                role: "assistant",
                content: `I'd be happy to help with that! Let me work on "${message.trim()}" for you. This is a mock response — connect a real model to get started.`
            }]);
        }, 800);
        setMessage("");
    };

    const handlePrompt = (prompt: string) => {
        setMessage(prompt);
    };

    return (
        <div className="max-w-2xl mx-auto">
            {/* Greeting */}
            <div className="text-center mb-8 pt-8">
                <h1 className="text-3xl font-bold text-white mb-2">
                    Hi{userName ? ` ${userName}` : " there"} 👋
                </h1>
                <p className="text-[var(--color-rune-dim)]">Your AI is ready. What can I help you with?</p>
            </div>

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

            {/* What your AI did today */}
            <div className="glass-card p-5">
                <h3 className="text-sm text-[var(--color-rune-dim)] font-semibold mb-4">What your AI did today</h3>
                <div className="space-y-3">
                    {ACTIVITY.map((item, i) => (
                        <div key={i} className="flex items-center gap-3">
                            <span className="text-lg">{item.icon}</span>
                            <span className="text-sm text-[var(--color-rune)]">{item.text}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

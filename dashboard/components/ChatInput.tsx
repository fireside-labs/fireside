"use client";

import { useState, useRef, useEffect } from "react";
import { useToast } from "@/components/Toast";

interface Message {
    role: "user" | "assistant";
    content: string;
    tools?: string[];
}

const GHOST_PROMPTS = [
    'Try: "Read my last 3 git commits and tell me what I was working on"',
    'Try: "What files did I change today?"',
    'Try: "Summarize the current state of this project"',
    'Try: "Find any TODO comments in the codebase"',
];

export default function ChatInput() {
    const [input, setInput] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [streaming, setStreaming] = useState(false);
    const [ghostIdx] = useState(() => Math.floor(Math.random() * GHOST_PROMPTS.length));
    const inputRef = useRef<HTMLInputElement>(null);
    const chatRef = useRef<HTMLDivElement>(null);
    const { toast } = useToast();

    useEffect(() => {
        if (chatRef.current) {
            chatRef.current.scrollTop = chatRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || streaming) return;

        const userMsg: Message = { role: "user", content: input.trim() };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setStreaming(true);

        // Simulate streaming response with tool usage
        await new Promise((r) => setTimeout(r, 800));

        const tools = ["file_read", "git_log"];
        const response: Message = {
            role: "assistant",
            content: "Based on your recent activity, you've been working on the Fireside dashboard — specifically the Guild Hall, agent profiles, and the marketplace. The latest commits show Sprint 11 completion with the rebrand finished.",
            tools,
        };

        setMessages((prev) => [...prev, response]);
        setStreaming(false);
        toast("Your agent used " + tools.length + " tools. Everything ran locally.", "info");
    };

    return (
        <div className="glass-card p-0 overflow-hidden">
            {/* Chat Messages */}
            {messages.length > 0 && (
                <div ref={chatRef} className="max-h-64 overflow-y-auto p-5 space-y-3 border-b border-[var(--color-glass-border)]">
                    {messages.map((msg, i) => (
                        <div key={i} className={"chat-message " + (msg.role === "user" ? "chat-user" : "chat-assistant")}>
                            {msg.tools && (
                                <div className="flex gap-2 mb-2">
                                    {msg.tools.map((t) => (
                                        <span key={t} className="text-xs px-2 py-0.5 rounded bg-[var(--color-neon-glow)] text-[var(--color-neon)] font-mono">
                                            🔧 {t}
                                        </span>
                                    ))}
                                </div>
                            )}
                            <p className="text-sm leading-relaxed">{msg.content}</p>
                        </div>
                    ))}
                    {streaming && (
                        <div className="chat-message chat-assistant">
                            <div className="flex gap-1.5">
                                <span className="typing-dot" />
                                <span className="typing-dot" style={{ animationDelay: "0.15s" }} />
                                <span className="typing-dot" style={{ animationDelay: "0.3s" }} />
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Input */}
            <div className="p-4 flex gap-3">
                <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    placeholder={GHOST_PROMPTS[ghostIdx]}
                    className="flex-1 bg-transparent text-white placeholder-[var(--color-rune-dim)] text-sm outline-none"
                    disabled={streaming}
                />
                <button
                    onClick={handleSend}
                    disabled={!input.trim() || streaming}
                    className="btn-neon text-xs px-4 py-2"
                    style={{ opacity: !input.trim() || streaming ? 0.4 : 1 }}
                >
                    {streaming ? "⏳" : input.trim() ? "Send" : "Start a Fireside →"}
                </button>
            </div>
        </div>
    );
}
